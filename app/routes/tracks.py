import shutil
import subprocess
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.enums import DecisionSource, DecisionValue, JobStatus, JobType, TrackStatus
from app.models.job import Job
from app.models.playlist import Playlist
from app.models.track import Track
from app.schemas.common import MessageResponse
from app.schemas.track import TrackCreateRequest, TrackDecisionRequest, TrackRead, TrackReturnToReviewRequest
from app.services.registry import ServiceRegistry
from app.workflows.approvals import apply_track_decision
from app.workflows.playlist_automation import assign_track_to_playlist, maybe_build_auto_playlist, return_track_to_workspace_queue
from app.workflows.review_dispatch import dispatch_track_review, post_track_review_to_slack
from app.workflows.slack_sync import sync_slack_review_decision, sync_slack_review_request

router = APIRouter(prefix="/tracks", tags=["tracks"])


def get_services(request: Request) -> ServiceRegistry:
    return request.app.state.services


def _create_track_record(
    db: Session,
    payload: TrackCreateRequest,
) -> Track:
    metadata = dict(payload.metadata or {})
    pending_workspace_id = metadata.get("pending_workspace_id")
    if pending_workspace_id and not metadata.get("pending_workspace_title"):
        playlist = db.get(Playlist, pending_workspace_id)
        if playlist:
            metadata["pending_workspace_title"] = playlist.title

    track = Track(
        title=payload.title,
        prompt=payload.prompt,
        duration_seconds=payload.duration_seconds,
        audio_path=payload.audio_path,
        preview_url=payload.preview_url,
        source_track_id=payload.source_track_id,
        metadata_json=metadata,
    )
    db.add(track)
    db.flush()

    job = Job(
        type=JobType.generate_track,
        status=JobStatus.succeeded,
        payload_json=payload.model_dump(),
        result_json={"track_id": track.id},
        source="api",
        track=track,
    )
    db.add(job)
    db.commit()
    db.refresh(track)
    return track


def _queue_slack_review_job(db: Session, track: Track, *, source: str) -> None:
    db.add(
        Job(
            type=JobType.sync_slack,
            status=JobStatus.queued,
            source=source,
            payload_json={"track_id": track.id, "action": "dispatch_review"},
            track=track,
        )
    )
    db.commit()


def _probe_duration_seconds(audio_path: str | None) -> int | None:
    if not audio_path:
        return None
    if audio_path.startswith(("http://", "https://")):
        return None

    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                audio_path,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        value = float(result.stdout.strip())
    except (OSError, subprocess.SubprocessError, ValueError):
        return None

    return max(1, round(value))


def _extract_embedded_cover(audio_path: str | None, covers_dir: Path) -> str | None:
    if not audio_path or audio_path.startswith(("http://", "https://")):
        return None

    source = Path(audio_path)
    if not source.exists():
        return None

    covers_dir.mkdir(parents=True, exist_ok=True)
    destination = _resolve_upload_destination(covers_dir, f"{source.stem}-cover.jpg")
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-v",
                "error",
                "-i",
                str(source),
                "-map",
                "0:v:0",
                "-an",
                "-frames:v",
                "1",
                "-c:v",
                "mjpeg",
                "-q:v",
                "2",
                str(destination),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    return str(destination) if destination.exists() and destination.stat().st_size > 0 else None


def _resolve_upload_destination(tracks_dir: Path, original_name: str) -> Path:
    tracks_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(original_name).name.strip()
    if not safe_name:
        safe_name = "upload.mp3"

    stem = Path(safe_name).stem.strip() or "upload"
    suffix = Path(safe_name).suffix or ".mp3"
    candidate = tracks_dir / f"{stem}{suffix}"
    index = 2

    while candidate.exists():
        candidate = tracks_dir / f"{stem}-{index}{suffix}"
        index += 1

    return candidate


@router.post("", response_model=TrackRead, status_code=status.HTTP_201_CREATED)
async def create_track(
    payload: TrackCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TrackRead:
    services = get_services(request)
    track = _create_track_record(db, payload)
    track = await dispatch_track_review(db, services, track)
    return TrackRead.model_validate(track)


@router.post("/manual-upload", response_model=TrackRead, status_code=status.HTTP_201_CREATED)
async def manual_upload_track(
    request: Request,
    title: str = Form(...),
    prompt: str = Form(""),
    duration_seconds: int = Form(0),
    preview_url: str | None = Form(None),
    audio_url: str | None = Form(None),
    source_track_id: str | None = Form(None),
    image_url: str | None = Form(None),
    tags: str | None = Form(None),
    model_score: float | None = Form(None),
    pending_workspace_id: str | None = Form(None),
    audio_file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
) -> TrackRead:
    services = get_services(request)
    audio_path = audio_url
    inferred_duration_seconds = duration_seconds
    if not audio_file and not audio_url:
        raise HTTPException(status_code=400, detail="Either audio_file or audio_url is required.")

    if audio_file and audio_file.filename:
        destination = _resolve_upload_destination(services.settings.tracks_dir, audio_file.filename)
        with destination.open("wb") as handle:
            shutil.copyfileobj(audio_file.file, handle)
        audio_path = str(destination)
        if inferred_duration_seconds <= 0:
            inferred_duration_seconds = _probe_duration_seconds(audio_path) or 0
    elif inferred_duration_seconds <= 0:
        inferred_duration_seconds = _probe_duration_seconds(audio_path) or 0

    resolved_image_url = image_url or _extract_embedded_cover(audio_path, services.settings.covers_dir)
    payload = TrackCreateRequest(
        title=title,
        prompt=prompt,
        duration_seconds=inferred_duration_seconds,
        audio_path=audio_path,
        preview_url=preview_url,
        source_track_id=source_track_id,
        metadata={
            "source": "manual-upload",
            **({"image_url": resolved_image_url} if resolved_image_url else {}),
            **({"tags": tags} if tags else {}),
            **({"model_score": model_score} if model_score is not None else {}),
            **({"pending_workspace_id": pending_workspace_id} if pending_workspace_id else {}),
        },
    )
    track = _create_track_record(db, payload)
    _queue_slack_review_job(db, track, source="manual-upload")
    db.refresh(track)
    return TrackRead.model_validate(track)


@router.get("", response_model=list[TrackRead])
def list_tracks(
    status_filter: TrackStatus | None = None,
    db: Session = Depends(get_db),
) -> list[TrackRead]:
    statement = select(Track).order_by(Track.created_at.desc())
    if status_filter:
        statement = statement.where(Track.status == status_filter)
    tracks = db.scalars(statement).all()
    return [TrackRead.model_validate(track) for track in tracks]


@router.get("/{track_id}", response_model=TrackRead)
def get_track(track_id: str, db: Session = Depends(get_db)) -> TrackRead:
    track = db.get(Track, track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    return TrackRead.model_validate(track)


@router.post("/{track_id}/decisions", response_model=TrackRead)
async def decide_track(
    track_id: str,
    payload: TrackDecisionRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TrackRead:
    services = get_services(request)
    track = db.get(Track, track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    apply_track_decision(
        db,
        track,
        decision=payload.decision,
        source=payload.source,
        actor=payload.actor,
        rationale=payload.rationale,
        confidence=payload.confidence,
    )
    db.commit()
    db.refresh(track)
    assigned_workspace_title = None
    if payload.decision == DecisionValue.approve and payload.playlist_id:
        try:
            playlist = await assign_track_to_playlist(
                db,
                services,
                track=track,
                playlist_id=payload.playlist_id,
                actor=payload.actor,
            )
            assigned_workspace_title = playlist.title
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    elif payload.decision == DecisionValue.approve:
        await maybe_build_auto_playlist(db, services, trigger=f"manual-decision:{track.id}")

    await sync_slack_review_decision(
        db,
        services,
        track,
        decision=payload.decision,
        actor=payload.actor,
        workspace_title=assigned_workspace_title,
        note="Decision submitted from the web dashboard.",
    )
    return TrackRead.model_validate(track)


@router.post("/{track_id}/return-to-review", response_model=TrackRead)
async def return_track_to_review(
    track_id: str,
    payload: TrackReturnToReviewRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TrackRead:
    services = get_services(request)
    track = db.get(Track, track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    apply_track_decision(
        db,
        track,
        decision=DecisionValue.hold,
        source=DecisionSource.human,
        actor=payload.actor,
        rationale=payload.rationale or "Returned from approved tracks to awaiting approval.",
    )
    db.commit()
    db.refresh(track)

    try:
        await return_track_to_workspace_queue(
            db,
            services,
            track=track,
            playlist_id=payload.playlist_id,
            actor=payload.actor,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    db.refresh(track)
    await sync_slack_review_request(
        db,
        services,
        track,
    )
    return TrackRead.model_validate(track)


@router.post("/{track_id}/agent-review", response_model=TrackRead)
async def review_track_with_agent(
    track_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> TrackRead:
    services = get_services(request)
    track = db.get(Track, track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    decision = services.decision_engine.review_track(track)
    apply_track_decision(
        db,
        track,
        decision=decision.decision,
        source=DecisionSource.agent,
        actor=decision.actor,
        rationale=decision.rationale,
        confidence=decision.confidence,
    )
    db.commit()
    db.refresh(track)
    await maybe_build_auto_playlist(db, services, trigger=f"agent-review:{track.id}")
    return TrackRead.model_validate(track)


@router.post("/{track_id}/slack-review")
async def create_slack_review(
    track_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    services = get_services(request)
    track = db.get(Track, track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    post_result = await post_track_review_to_slack(db, services, track)

    return {
        "track_id": track.id,
        "posted": post_result.ok,
        "channel": post_result.channel,
        "ts": post_result.ts,
        "blocks": services.slack.build_track_review_blocks(track),
        "raw": post_result.raw,
    }


@router.post("/{track_id}/dispatch-review", response_model=TrackRead)
async def dispatch_review_workflow(
    track_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> TrackRead:
    services = get_services(request)
    track = db.get(Track, track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    track = await dispatch_track_review(db, services, track)
    return TrackRead.model_validate(track)


@router.post("/{track_id}/request-regeneration", response_model=MessageResponse)
def request_regeneration(track_id: str, db: Session = Depends(get_db)) -> MessageResponse:
    track = db.get(Track, track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    job = Job(
        type=JobType.generate_track,
        status=JobStatus.queued,
        source="api",
        payload_json={
            "track_id": track.id,
            "prompt": track.prompt,
            "title": track.title,
        },
        track=track,
    )
    db.add(job)
    db.commit()
    return MessageResponse(message=f"Regeneration queued for track {track.id}")
