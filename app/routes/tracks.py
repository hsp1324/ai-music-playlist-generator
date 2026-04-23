import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.enums import DecisionSource, DecisionValue, JobStatus, JobType, TrackStatus
from app.models.job import Job
from app.models.track import Track
from app.schemas.common import MessageResponse
from app.schemas.track import TrackCreateRequest, TrackDecisionRequest, TrackRead
from app.services.registry import ServiceRegistry
from app.workflows.approvals import apply_track_decision
from app.workflows.playlist_automation import assign_track_to_playlist, maybe_build_auto_playlist
from app.workflows.review_dispatch import dispatch_track_review

router = APIRouter(prefix="/tracks", tags=["tracks"])


def get_services(request: Request) -> ServiceRegistry:
    return request.app.state.services


def _create_track_record(
    db: Session,
    payload: TrackCreateRequest,
) -> Track:
    track = Track(
        title=payload.title,
        prompt=payload.prompt,
        duration_seconds=payload.duration_seconds,
        audio_path=payload.audio_path,
        preview_url=payload.preview_url,
        source_track_id=payload.source_track_id,
        metadata_json=payload.metadata,
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
    audio_file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
) -> TrackRead:
    services = get_services(request)
    audio_path = audio_url
    if not audio_file and not audio_url:
        raise HTTPException(status_code=400, detail="Either audio_file or audio_url is required.")

    if audio_file and audio_file.filename:
        suffix = Path(audio_file.filename).suffix or ".mp3"
        stored_name = f"{uuid4()}{suffix}"
        destination = services.settings.tracks_dir / stored_name
        with destination.open("wb") as handle:
            shutil.copyfileobj(audio_file.file, handle)
        audio_path = str(destination)

    payload = TrackCreateRequest(
        title=title,
        prompt=prompt,
        duration_seconds=duration_seconds,
        audio_path=audio_path,
        preview_url=preview_url,
        source_track_id=source_track_id,
        metadata={
            "source": "manual-upload",
            **({"image_url": image_url} if image_url else {}),
            **({"tags": tags} if tags else {}),
            **({"model_score": model_score} if model_score is not None else {}),
        },
    )
    track = _create_track_record(db, payload)
    track = await dispatch_track_review(db, services, track)
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
    if payload.decision == DecisionValue.approve and payload.playlist_id:
        try:
            await assign_track_to_playlist(
                db,
                services,
                track=track,
                playlist_id=payload.playlist_id,
                actor=payload.actor,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    elif payload.decision == DecisionValue.approve:
        await maybe_build_auto_playlist(db, services, trigger=f"manual-decision:{track.id}")
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

    blocks = services.slack.build_track_review_blocks(track)
    installation = services.slack_installations.get_active_installation(db)
    post_result = await services.slack.post_review_message(
        track,
        token=installation.bot_token if installation else services.settings.slack_bot_token,
        channel=services.settings.slack_review_channel_id,
    )

    if post_result.ok:
        track.slack_channel_id = post_result.channel
        track.slack_message_ts = post_result.ts
        db.add(track)
        db.commit()
        db.refresh(track)

    return {
        "track_id": track.id,
        "posted": post_result.ok,
        "channel": post_result.channel,
        "ts": post_result.ts,
        "blocks": blocks,
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
