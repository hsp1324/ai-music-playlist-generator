import asyncio
import json
import shutil
import subprocess
import threading
import time
from datetime import datetime, timezone
from urllib.parse import unquote, urlparse
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from sqlalchemy import String, bindparam, cast, func, select, text
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.models.enums import DecisionSource, DecisionValue, JobStatus, JobType, TrackStatus
from app.models.job import Job
from app.models.playlist import Playlist
from app.models.track import Track
from app.models.track_reuse import TrackReuseEvent
from app.schemas.common import MessageResponse
from app.schemas.track import (
    TrackCreateRequest,
    TrackDecisionRequest,
    TrackRatingRequest,
    TrackRead,
    TrackReuseEventRead,
    TrackReuseSummaryRead,
    TrackReturnToReviewRequest,
    TrackSuggestionRead,
)
from app.services.registry import ServiceRegistry
from app.workflows.approvals import apply_track_decision
from app.workflows.playlist_automation import (
    assign_track_to_playlist,
    maybe_archive_rejected_single_workspace,
    maybe_build_auto_playlist,
    return_track_to_workspace_queue,
)
from app.workflows.review_dispatch import dispatch_track_review, post_track_review_to_slack
from app.workflows.slack_sync import sync_slack_review_decision, sync_slack_review_request
from app.utils.short_track_observations import annotate_short_track_metadata
from app.utils.bulsong_source import (
    append_bulsong_quality_warning,
    bulsong_quality_monitoring_enabled,
    make_bulsong_quality_warning,
    validate_bulsong_source_map,
)
from app.utils.genre_tokens import update_track_genre_token_metadata
from app.utils.track_search import (
    best_track_match_text,
    normalize_track_search_terms,
    search_track_ids,
    sync_track_search_document,
    track_matches_terms,
    user_rating_filter_expression,
)

router = APIRouter(prefix="/tracks", tags=["tracks"])
ALLOWED_COVER_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
REMOTE_AUDIO_TIMEOUT_SECONDS = 180.0
FFPROBE_TIMEOUT_SECONDS = 30.0
COVER_EXTRACTION_TIMEOUT_SECONDS = 30.0
TRACK_REUSE_SUMMARY_CACHE_TTL_SECONDS = 30.0
_track_reuse_summary_cache_lock = threading.Lock()
_track_reuse_summary_cache: dict[tuple[int, bool, str, str], tuple[float, list[TrackReuseSummaryRead]]] = {}


def get_services(request: Request) -> ServiceRegistry:
    return request.app.state.services


def _create_track_record(
    db: Session,
    payload: TrackCreateRequest,
) -> Track:
    metadata = dict(payload.metadata or {})
    metadata["lyrics"] = str(payload.lyrics if payload.lyrics is not None else metadata.get("lyrics") or "")
    metadata["style"] = str(payload.style if payload.style is not None else metadata.get("style") or "")
    metadata["exclude_style"] = str(
        payload.exclude_style if payload.exclude_style is not None else metadata.get("exclude_style") or ""
    )
    pending_workspace_id = metadata.get("pending_workspace_id")
    if pending_workspace_id and not metadata.get("pending_workspace_title"):
        playlist = db.get(Playlist, pending_workspace_id)
        if playlist:
            metadata["pending_workspace_title"] = playlist.title
    metadata = annotate_short_track_metadata(
        metadata,
        duration_seconds=payload.duration_seconds,
        title=payload.title,
        prompt=payload.prompt,
        style=metadata.get("style"),
        exclude_style=metadata.get("exclude_style"),
        tags=metadata.get("tags"),
        lyrics=metadata.get("lyrics"),
        source=metadata.get("source") or "track-create",
        context="track_intake",
        extra={
            "pending_workspace_id": pending_workspace_id,
            "pending_workspace_title": metadata.get("pending_workspace_title"),
        },
    )
    metadata = update_track_genre_token_metadata(metadata, title=payload.title, prompt=payload.prompt)

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
    sync_track_search_document(db, track)

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


def _is_remote_url(value: str | None) -> bool:
    return bool(value and value.startswith(("http://", "https://")))


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


def _validate_pending_workspace_upload(db: Session, pending_workspace_id: str | None) -> None:
    if not pending_workspace_id:
        return
    playlist = db.get(Playlist, pending_workspace_id)
    if not playlist:
        raise HTTPException(status_code=400, detail="Pending workspace does not exist.")
    meta = dict(playlist.metadata_json or {})
    if meta.get("hidden"):
        raise HTTPException(status_code=400, detail="Pending workspace is archived. Restore it before uploading.")
    if meta.get("workspace_mode") != "single_track_video":
        return
    candidate_count = 0
    tracks = db.scalars(select(Track)).all()
    for track in tracks:
        if (
            (track.metadata_json or {}).get("pending_workspace_id") == pending_workspace_id
            and track.status in {TrackStatus.pending_review, TrackStatus.held}
        ):
            candidate_count += 1
    if len(playlist.items) + candidate_count >= 2:
        raise HTTPException(status_code=400, detail="Single release can hold at most two review candidates.")


def _probe_duration_seconds(audio_path: str | None) -> int | None:
    if not audio_path:
        return None
    if _is_remote_url(audio_path):
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
            timeout=FFPROBE_TIMEOUT_SECONDS,
        )
        value = float(result.stdout.strip())
    except (OSError, subprocess.SubprocessError, ValueError):
        return None

    if value <= 0:
        return None
    return max(1, round(value))


def _resolve_audio_duration_seconds(audio_path: str | None, supplied_duration_seconds: int) -> int:
    inferred_duration = _probe_duration_seconds(audio_path)
    if inferred_duration is not None:
        return inferred_duration

    if audio_path and not _is_remote_url(audio_path):
        source = Path(audio_path)
        if source.exists() and source.stat().st_size == 0:
            raise HTTPException(status_code=400, detail="Uploaded audio file is empty or unreadable.")

    return max(supplied_duration_seconds, 0)


def _extract_embedded_cover(audio_path: str | None, covers_dir: Path) -> str | None:
    if not audio_path or _is_remote_url(audio_path):
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
            timeout=COVER_EXTRACTION_TIMEOUT_SECONDS,
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


def _filename_from_remote_audio_url(audio_url: str, fallback_title: str) -> str:
    parsed_name = Path(unquote(urlparse(audio_url).path)).name
    if parsed_name and Path(parsed_name).suffix:
        return parsed_name
    safe_title = "".join(
        char if char.isalnum() or char in {" ", "-", "_", "."} else "-"
        for char in fallback_title
    ).strip(" .-_")
    return f"{safe_title or 'remote-audio'}.mp3"


def _cache_remote_audio_url(audio_url: str, tracks_dir: Path, *, title: str) -> str:
    destination = _resolve_upload_destination(tracks_dir, _filename_from_remote_audio_url(audio_url, title))
    try:
        with httpx.Client(timeout=REMOTE_AUDIO_TIMEOUT_SECONDS, follow_redirects=True) as client:
            with client.stream("GET", audio_url) as response:
                response.raise_for_status()
                with destination.open("wb") as output:
                    for chunk in response.iter_bytes():
                        if chunk:
                            output.write(chunk)
    except httpx.HTTPError as exc:
        if destination.exists():
            destination.unlink()
        raise HTTPException(status_code=400, detail=f"Could not download remote audio URL: {exc}") from exc

    if not destination.exists() or destination.stat().st_size == 0:
        if destination.exists():
            destination.unlink()
        raise HTTPException(status_code=400, detail="Downloaded remote audio is empty.")

    return str(destination)


def _cache_payload_remote_audio(payload: TrackCreateRequest, tracks_dir: Path) -> TrackCreateRequest:
    if not _is_remote_url(payload.audio_path):
        return payload

    remote_audio_url = payload.audio_path
    cached_audio_path = _cache_remote_audio_url(remote_audio_url, tracks_dir, title=payload.title)
    metadata = dict(payload.metadata or {})
    metadata.setdefault("source_audio_url", remote_audio_url)
    metadata.setdefault("audio_source", "remote-url-cache")
    return payload.model_copy(
        update={
            "audio_path": cached_audio_path,
            "metadata": metadata,
        }
    )


def _remote_audio_cache_disabled_metadata(payload: TrackCreateRequest) -> TrackCreateRequest:
    if not _is_remote_url(payload.audio_path):
        return payload
    metadata = dict(payload.metadata or {})
    metadata.setdefault("source_audio_url", payload.audio_path)
    metadata.setdefault("audio_source", "remote-url")
    return payload.model_copy(update={"metadata": metadata})


def _prepare_track_create_payload(
    payload: TrackCreateRequest,
    *,
    cache_remote_audio: bool,
    tracks_dir: Path,
) -> TrackCreateRequest:
    prepared = (
        _cache_payload_remote_audio(payload, tracks_dir)
        if cache_remote_audio
        else _remote_audio_cache_disabled_metadata(payload)
    )
    return prepared.model_copy(
        update={
            "duration_seconds": _resolve_audio_duration_seconds(
                prepared.audio_path,
                prepared.duration_seconds,
            )
        }
    )


def _prepare_manual_upload_media(
    *,
    audio_file: UploadFile | None,
    cover_file: UploadFile | None,
    audio_url: str | None,
    image_url: str | None,
    title: str,
    duration_seconds: int,
    cache_remote_audio: bool,
    tracks_dir: Path,
    covers_dir: Path,
) -> tuple[str | None, int, str | None, str | None]:
    audio_path = audio_url
    inferred_duration_seconds = duration_seconds
    if audio_file and audio_file.filename:
        destination = _resolve_upload_destination(tracks_dir, audio_file.filename)
        with destination.open("wb") as handle:
            shutil.copyfileobj(audio_file.file, handle)
        audio_path = str(destination)
        if not destination.exists() or destination.stat().st_size == 0:
            destination.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail="Uploaded audio file is empty.")
        inferred_duration_seconds = _resolve_audio_duration_seconds(audio_path, inferred_duration_seconds)
    elif audio_url and cache_remote_audio:
        audio_path = _cache_remote_audio_url(audio_url, tracks_dir, title=title)
        inferred_duration_seconds = _resolve_audio_duration_seconds(audio_path, inferred_duration_seconds)
    else:
        inferred_duration_seconds = _resolve_audio_duration_seconds(audio_path, inferred_duration_seconds)

    uploaded_cover_path = _store_cover_upload(cover_file, covers_dir)
    resolved_image_url = uploaded_cover_path or image_url or _extract_embedded_cover(audio_path, covers_dir)
    return audio_path, inferred_duration_seconds, uploaded_cover_path, resolved_image_url


def _pending_workspace_upload_meta(db: Session, pending_workspace_id: str | None) -> dict:
    try:
        _validate_pending_workspace_upload(db, pending_workspace_id)
        playlist = db.get(Playlist, pending_workspace_id) if pending_workspace_id else None
        return dict(playlist.metadata_json or {}) if playlist else {}
    finally:
        # Do not hold a read transaction while media is copied or probed.
        db.rollback()


def _create_and_dispatch_track(db: Session, services: ServiceRegistry, payload: TrackCreateRequest) -> TrackRead:
    track = _create_track_record(db, payload)
    track = asyncio.run(dispatch_track_review(db, services, track))
    return TrackRead.model_validate(track)


def _finish_manual_upload(
    db: Session,
    payload: TrackCreateRequest,
    *,
    pending_workspace_id: str | None,
    bulsong_warnings: list[dict],
    dispatch_review: bool,
) -> TrackRead:
    track = _create_track_record(db, payload)
    if pending_workspace_id and bulsong_warnings:
        pending_workspace = db.get(Playlist, pending_workspace_id)
        if pending_workspace is not None:
            pending_meta = dict(pending_workspace.metadata_json or {})
            for warning in bulsong_warnings:
                release_warning = {
                    **warning,
                    "track_id": track.id,
                    "track_title": track.title,
                }
                append_bulsong_quality_warning(pending_meta, release_warning)
            pending_workspace.metadata_json = pending_meta
            db.add(pending_workspace)
            db.commit()
    if dispatch_review:
        _queue_slack_review_job(db, track, source="manual-upload")
    db.refresh(track)
    return TrackRead.model_validate(track)


def _store_cover_upload(upload: UploadFile | None, covers_dir: Path) -> str | None:
    if not upload or not upload.filename:
        return None

    suffix = Path(upload.filename).suffix.lower()
    if suffix not in ALLOWED_COVER_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Cover image must be jpg, png, or webp.")
    if upload.content_type and not upload.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Cover upload must be an image file.")

    destination = _resolve_upload_destination(covers_dir, upload.filename)
    with destination.open("wb") as handle:
        shutil.copyfileobj(upload.file, handle)
    if not destination.exists() or destination.stat().st_size == 0:
        raise HTTPException(status_code=400, detail="Uploaded cover image is empty.")
    return str(destination)


@router.post("", response_model=TrackRead, status_code=status.HTTP_201_CREATED)
async def create_track(
    payload: TrackCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TrackRead:
    services = get_services(request)
    async with request.app.state.track_media_limiter:
        payload = await asyncio.to_thread(
            _prepare_track_create_payload,
            payload,
            cache_remote_audio=services.settings.cache_remote_audio_on_intake,
            tracks_dir=services.settings.tracks_dir,
        )
    return await asyncio.to_thread(_create_and_dispatch_track, db, services, payload)


@router.post("/manual-upload", response_model=TrackRead, status_code=status.HTTP_201_CREATED)
async def manual_upload_track(
    request: Request,
    title: str = Form(...),
    prompt: str = Form(""),
    lyrics: str = Form(""),
    style: str = Form(""),
    exclude_style: str = Form(""),
    duration_seconds: int = Form(0),
    preview_url: str | None = Form(None),
    audio_url: str | None = Form(None),
    source_track_id: str | None = Form(None),
    image_url: str | None = Form(None),
    tags: str | None = Form(None),
    model_score: float | None = Form(None),
    pending_workspace_id: str | None = Form(None),
    bulsong_source_map_json: str | None = Form(None),
    dispatch_review: bool = Form(True),
    audio_file: UploadFile | None = File(None),
    cover_file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
) -> TrackRead:
    services = get_services(request)
    bulsong_source_map = None
    bulsong_warnings: list[dict] = []
    if bulsong_source_map_json:
        try:
            bulsong_source_map = validate_bulsong_source_map(json.loads(bulsong_source_map_json))
        except (json.JSONDecodeError, ValueError) as exc:
            bulsong_warnings.append(
                make_bulsong_quality_warning(
                    code="bulsong_source_map_invalid",
                    stage="audio_upload",
                    message=f"Uploaded audio has an invalid Bulsong source map: {exc}",
                    track_title=title,
                )
            )
    pending_meta = await asyncio.to_thread(_pending_workspace_upload_meta, db, pending_workspace_id)
    if pending_workspace_id:
        if (
            bulsong_quality_monitoring_enabled(pending_meta)
            and bulsong_source_map is None
            and not bulsong_warnings
        ):
            bulsong_warnings.append(
                make_bulsong_quality_warning(
                    code="bulsong_source_map_missing",
                    stage="audio_upload",
                    message=(
                        "Audio was uploaded without a verified scripture-to-lyric source map. "
                        "Upload continued because Bulsong quality checks are warning-only."
                    ),
                    track_title=title,
                )
            )
    if not audio_file and not audio_url:
        raise HTTPException(status_code=400, detail="Either audio_file or audio_url is required.")
    async with request.app.state.track_media_limiter:
        audio_path, inferred_duration_seconds, uploaded_cover_path, resolved_image_url = await asyncio.to_thread(
            _prepare_manual_upload_media,
            audio_file=audio_file,
            cover_file=cover_file,
            audio_url=audio_url,
            image_url=image_url,
            title=title,
            duration_seconds=duration_seconds,
            cache_remote_audio=services.settings.cache_remote_audio_on_intake,
            tracks_dir=services.settings.tracks_dir,
            covers_dir=services.settings.covers_dir,
        )
    payload = TrackCreateRequest(
        title=title,
        prompt=prompt,
        lyrics=lyrics,
        style=style,
        exclude_style=exclude_style,
        duration_seconds=inferred_duration_seconds,
        audio_path=audio_path,
        preview_url=preview_url,
        source_track_id=source_track_id,
        metadata={
            "source": "manual-upload",
            **(
                {
                    "source_audio_url": audio_url,
                    "audio_source": "remote-url-cache" if services.settings.cache_remote_audio_on_intake else "remote-url",
                }
                if audio_url and not audio_file
                else {}
            ),
            **({"image_url": resolved_image_url} if resolved_image_url else {}),
            **({"cover_source": "cover-upload"} if uploaded_cover_path else {}),
            **({"tags": tags} if tags else {}),
            **({"model_score": model_score} if model_score is not None else {}),
            **({"pending_workspace_id": pending_workspace_id} if pending_workspace_id else {}),
            **({"bulsong_source_map": bulsong_source_map} if bulsong_source_map else {}),
            **({"bulsong_quality_warnings": bulsong_warnings} if bulsong_warnings else {}),
        },
    )
    return await asyncio.to_thread(
        _finish_manual_upload,
        db,
        payload,
        pending_workspace_id=pending_workspace_id,
        bulsong_warnings=bulsong_warnings,
        dispatch_review=dispatch_review,
    )


@router.get("", response_model=list[TrackRead])
def list_tracks(
    status_filter: TrackStatus | None = None,
    user_rating: str | None = None,
    single_youtube_uploaded: bool | None = None,
    q: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=0, ge=0, le=1000),
    compact: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> list[TrackRead]:
    query_terms = normalize_track_search_terms(q)
    statement = _filtered_track_statement(
        status_filter=status_filter,
        user_rating=user_rating,
        single_youtube_uploaded=single_youtube_uploaded,
    )
    if query_terms:
        candidate_limit = max((limit or 500) * 8, 500)
        tracks = _search_tracks(
            db,
            statement,
            query=q,
            terms=query_terms,
            limit=limit,
            candidate_limit=candidate_limit,
        )
    else:
        statement = statement.order_by(Track.created_at.desc())
        if limit:
            statement = statement.limit(limit)
        if not compact:
            statement = statement.options(selectinload(Track.approvals))
        tracks = db.scalars(statement).all()
    return [_serialize_track_read(track, compact=compact) for track in tracks]


@router.get("/suggest", response_model=list[TrackSuggestionRead])
def suggest_tracks(
    q: str = Query(default="", max_length=120),
    status_filter: TrackStatus | None = None,
    user_rating: str | None = None,
    single_youtube_uploaded: bool | None = None,
    limit: int = Query(default=8, ge=1, le=20),
    db: Session = Depends(get_db),
) -> list[TrackSuggestionRead]:
    terms = normalize_track_search_terms(q)
    if not terms:
        return []
    statement = _filtered_track_statement(
        status_filter=status_filter,
        user_rating=user_rating,
        single_youtube_uploaded=single_youtube_uploaded,
    )
    tracks = _search_tracks(
        db,
        statement,
        query=q,
        terms=terms,
        limit=limit,
        candidate_limit=max(limit * 12, 80),
    )
    suggestions = []
    for track in tracks[:limit]:
        match_type, matched_text = best_track_match_text(track, q)
        meta = dict(track.metadata_json or {})
        suggestions.append(
            TrackSuggestionRead(
                id=track.id,
                title=track.title,
                status=track.status,
                duration_seconds=track.duration_seconds,
                user_rating=str(meta.get("user_rating") or ""),
                match_type=match_type,
                matched_text=_compact_text(matched_text, 300),
                style=_compact_text(meta.get("style"), 500),
                tags=_compact_text(meta.get("tags"), 500),
            )
        )
    return suggestions


def _filtered_track_statement(
    *,
    status_filter: TrackStatus | None,
    user_rating: str | None,
    single_youtube_uploaded: bool | None = None,
):
    statement = select(Track)
    if status_filter:
        statement = statement.where(Track.status == status_filter)
    rating_expression = user_rating_filter_expression(user_rating)
    if rating_expression is not None:
        statement = statement.where(rating_expression)
    if single_youtube_uploaded is True:
        statement = statement.where(func.json_extract(Track.metadata_json, "$.single_youtube_uploaded") == 1)
    elif single_youtube_uploaded is False:
        statement = statement.where(
            func.coalesce(func.json_extract(Track.metadata_json, "$.single_youtube_uploaded"), 0) == 0
        )
    return statement


def _search_tracks(
    db: Session,
    statement,
    *,
    query: str | None,
    terms: list[str],
    limit: int,
    candidate_limit: int,
) -> list[Track]:
    ranked_ids = search_track_ids(db, query, limit=candidate_limit)
    ordered_tracks: list[Track] = []
    seen_ids: set[str] = set()
    requested_limit = limit or 0
    batch_size = min(max((requested_limit or 60) * 2, 12), 120)
    for index in range(0, len(ranked_ids), batch_size):
        batch_ids = ranked_ids[index:index + batch_size]
        if not batch_ids:
            continue
        indexed_tracks = db.scalars(statement.where(Track.id.in_(batch_ids))).all()
        tracks_by_id = {track.id: track for track in indexed_tracks}
        for track_id in batch_ids:
            track = tracks_by_id.get(track_id)
            if not track or track.id in seen_ids:
                continue
            ordered_tracks.append(track)
            seen_ids.add(track.id)
            if requested_limit and len(ordered_tracks) >= requested_limit:
                break
        if requested_limit and len(ordered_tracks) >= requested_limit:
            break

    if not requested_limit or len(ordered_tracks) < requested_limit:
        fallback_limit = max(candidate_limit, requested_limit * 4, 500)
        fallback_tracks = db.scalars(statement.order_by(Track.created_at.desc()).limit(fallback_limit)).all()
        for track in fallback_tracks:
            if track.id in seen_ids:
                continue
            if track_matches_terms(track, terms):
                ordered_tracks.append(track)
                seen_ids.add(track.id)
                if requested_limit and len(ordered_tracks) >= requested_limit:
                    break

    if requested_limit:
        return ordered_tracks[:requested_limit]
    return ordered_tracks


def _serialize_track_read(track: Track, *, compact: bool) -> TrackRead:
    if not compact:
        return TrackRead.model_validate(track)
    source_metadata = dict(track.metadata_json or {})
    metadata = {
        key: source_metadata.get(key)
        for key in (
            "image_url",
            "source_audio_url",
            "tags",
            "pending_workspace_id",
            "pending_workspace_title",
            "user_rating",
            "style",
            "exclude_style",
        )
        if source_metadata.get(key) not in {None, ""}
    }
    if source_metadata.get("lyrics"):
        metadata["lyrics_present"] = True
    prompt = track.prompt or ""
    if len(prompt) > 500:
        metadata["prompt_truncated"] = True
        prompt = f"{prompt[:500]}..."
    return TrackRead(
        id=track.id,
        source_track_id=track.source_track_id,
        title=track.title,
        prompt=prompt,
        lyrics="",
        style=str(source_metadata.get("style") or ""),
        exclude_style=str(source_metadata.get("exclude_style") or ""),
        duration_seconds=track.duration_seconds,
        audio_path=track.audio_path,
        preview_url=track.preview_url,
        status=track.status,
        metadata_json=metadata,
        user_rating=str(source_metadata.get("user_rating") or ""),
        slack_channel_id=track.slack_channel_id,
        slack_message_ts=track.slack_message_ts,
        created_at=track.created_at,
        updated_at=track.updated_at,
        reviewed_at=track.reviewed_at,
        approvals=[],
    )


def _compact_text(value: object, max_length: int) -> str:
    text_value = str(value or "")
    if len(text_value) <= max_length:
        return text_value
    return f"{text_value[:max_length]}..."


def _safe_int(value: object) -> int:
    try:
        return max(int(value or 0), 0)
    except (TypeError, ValueError):
        return 0


def _track_reuse_event_rollup(db: Session) -> dict[str, dict[str, int]]:
    rows = db.execute(
        select(
            TrackReuseEvent.track_id,
            func.count(),
            func.coalesce(func.sum(TrackReuseEvent.reused_duration_seconds), 0),
        ).group_by(TrackReuseEvent.track_id)
    ).all()
    return {
        str(track_id): {
            "count": _safe_int(count),
            "seconds": _safe_int(seconds),
        }
        for track_id, count, seconds in rows
        if track_id
    }


def _metadata_text(path: str):
    return cast(func.coalesce(func.json_extract(Track.metadata_json, path), ""), String)


def _track_reuse_summary_track_rows(db: Session, track_ids: list[str]):
    if db.bind is not None and db.bind.dialect.name == "sqlite":
        statement = text(
            """
            SELECT
                id,
                title,
                duration_seconds,
                audio_path,
                COALESCE(json_extract(metadata_json, '$.playlist_last_reused_at'), '') AS last_reused_at,
                COALESCE(
                    json_extract(metadata_json, '$.playlist_last_reused_in_playlist_id'),
                    ''
                ) AS last_reused_in_playlist_id,
                COALESCE(json_extract(metadata_json, '$.playlist_last_reused_by'), '') AS last_reused_by
            FROM tracks INDEXED BY idx_tracks_reuse_summary_cover
            WHERE id IN :track_ids
            """
        ).bindparams(bindparam("track_ids", expanding=True))
        return db.execute(statement, {"track_ids": track_ids}).all()

    return db.execute(
        select(
            Track.id,
            Track.title,
            Track.duration_seconds,
            Track.audio_path,
            _metadata_text("$.playlist_last_reused_at").label("last_reused_at"),
            _metadata_text("$.playlist_last_reused_in_playlist_id").label("last_reused_in_playlist_id"),
            _metadata_text("$.playlist_last_reused_by").label("last_reused_by"),
        ).where(Track.id.in_(track_ids))
    ).all()


def _serialize_track_reuse_event(event: TrackReuseEvent) -> TrackReuseEventRead:
    meta = dict(event.metadata_json or {})
    return TrackReuseEventRead(
        id=event.id,
        track_id=event.track_id,
        track_title=str(meta.get("track_title") or (event.track.title if event.track else "")),
        target_playlist_id=event.target_playlist_id,
        target_playlist_title=str(
            meta.get("target_playlist_title")
            or (event.target_playlist.title if event.target_playlist else "")
        ),
        source_playlist_id=event.source_playlist_id,
        source_playlist_title=str(
            meta.get("source_playlist_title")
            or (event.source_playlist.title if event.source_playlist else "")
            or ""
        )
        or None,
        source_youtube_video_id=str(
            meta.get("source_youtube_video_id")
            or (event.source_playlist.youtube_video_id if event.source_playlist else "")
            or ""
        )
        or None,
        actor=event.actor,
        source=event.source,
        reused_duration_seconds=event.reused_duration_seconds,
        source_start_seconds=event.source_start_seconds,
        reuse_count_before=event.reuse_count_before,
        reused_seconds_before=event.reused_seconds_before,
        selection_rank=event.selection_rank,
        metadata_json=meta,
        created_at=event.created_at,
    )


@router.get("/reuse", response_model=list[TrackReuseSummaryRead])
def list_track_reuse_summary(
    limit: int = Query(default=100, ge=1, le=1000),
    reused_only: bool = False,
    sort: str = Query(default="reuse_count"),
    direction: str = Query(default="desc"),
    db: Session = Depends(get_db),
) -> list[TrackReuseSummaryRead]:
    clean_sort = sort.strip().lower()
    clean_direction = direction.strip().lower()
    cache_key = (limit, bool(reused_only), clean_sort, clean_direction)
    now = time.monotonic()
    with _track_reuse_summary_cache_lock:
        cached = _track_reuse_summary_cache.get(cache_key)
        if cached and now - cached[0] < TRACK_REUSE_SUMMARY_CACHE_TTL_SECONDS:
            return cached[1]

    if clean_sort in {"title", "name"} and not reused_only:
        title_expr = func.lower(Track.title)
        track_rows = db.execute(
            select(
                Track.id,
                Track.title,
                Track.duration_seconds,
                Track.audio_path,
                _metadata_text("$.playlist_last_reused_at").label("last_reused_at"),
                _metadata_text("$.playlist_last_reused_in_playlist_id").label("last_reused_in_playlist_id"),
                _metadata_text("$.playlist_last_reused_by").label("last_reused_by"),
            )
            .order_by(title_expr.asc() if clean_direction == "asc" else title_expr.desc())
            .limit(limit)
        ).all()
        event_rollup = {
            str(track_id): {"count": _safe_int(count), "seconds": _safe_int(seconds)}
            for track_id, count, seconds in db.execute(
                select(
                    TrackReuseEvent.track_id,
                    func.count(),
                    func.coalesce(func.sum(TrackReuseEvent.reused_duration_seconds), 0),
                )
                .where(TrackReuseEvent.track_id.in_([row.id for row in track_rows]))
                .group_by(TrackReuseEvent.track_id)
            ).all()
        }
        summaries = [
            TrackReuseSummaryRead(
                track_id=row.id,
                title=row.title,
                duration_seconds=row.duration_seconds,
                audio_path=row.audio_path,
                reuse_count=_safe_int(event_rollup.get(row.id, {}).get("count")),
                reused_seconds=_safe_int(event_rollup.get(row.id, {}).get("seconds")),
                event_count=_safe_int(event_rollup.get(row.id, {}).get("count")),
                last_reused_at=str(row.last_reused_at or "") or None,
                last_reused_in_playlist_id=str(row.last_reused_in_playlist_id or "") or None,
                last_reused_by=str(row.last_reused_by or "") or None,
            )
            for row in track_rows
        ]
        with _track_reuse_summary_cache_lock:
            _track_reuse_summary_cache[cache_key] = (now, summaries)
            if len(_track_reuse_summary_cache) > 16:
                oldest_key = min(_track_reuse_summary_cache, key=lambda key: _track_reuse_summary_cache[key][0])
                _track_reuse_summary_cache.pop(oldest_key, None)
        return summaries

    candidate_limit = max(limit * 4, 100)
    if clean_sort in {"title", "name"}:
        candidate_limit = 10000

    event_count_expr = func.count()
    event_seconds_expr = func.coalesce(func.sum(TrackReuseEvent.reused_duration_seconds), 0)
    if clean_sort in {"reused_seconds", "seconds", "duration"}:
        event_primary_order = event_seconds_expr.asc() if clean_direction == "asc" else event_seconds_expr.desc()
        event_secondary_order = event_count_expr.asc() if clean_direction == "asc" else event_count_expr.desc()
    else:
        event_primary_order = event_count_expr.asc() if clean_direction == "asc" else event_count_expr.desc()
        event_secondary_order = event_seconds_expr.asc() if clean_direction == "asc" else event_seconds_expr.desc()

    event_rows = db.execute(
        select(
            TrackReuseEvent.track_id,
            event_count_expr.label("event_count"),
            event_seconds_expr.label("event_seconds"),
        )
        .where(TrackReuseEvent.track_id.is_not(None))
        .group_by(TrackReuseEvent.track_id)
        .order_by(event_primary_order, event_secondary_order)
        .limit(candidate_limit)
    ).all()

    summary_by_id: dict[str, dict[str, object]] = {}
    for track_id, event_count, event_seconds in event_rows:
        summary_by_id[str(track_id)] = {
            "reuse_count": _safe_int(event_count),
            "reused_seconds": _safe_int(event_seconds),
            "event_count": _safe_int(event_count),
        }

    if not reused_only and len(summary_by_id) < limit:
        existing_ids = set(summary_by_id)
        fallback_rows = db.execute(
            select(Track.id)
            .where(~Track.id.in_(existing_ids) if existing_ids else True)
            .order_by(Track.created_at.desc())
            .limit(limit - len(summary_by_id))
        ).all()
        for row in fallback_rows:
            summary_by_id.setdefault(row.id, {"reuse_count": 0, "reused_seconds": 0, "event_count": 0})

    track_ids = list(summary_by_id)
    if not track_ids:
        summaries: list[TrackReuseSummaryRead] = []
    else:
        track_rows = _track_reuse_summary_track_rows(db, track_ids)
        summaries = []
        for row in track_rows:
            entry = summary_by_id.get(row.id, {})
            reuse_count = _safe_int(entry.get("reuse_count"))
            event_count = _safe_int(entry.get("event_count"))
            if reused_only and not reuse_count and not event_count:
                continue
            summaries.append(
                TrackReuseSummaryRead(
                    track_id=row.id,
                    title=row.title,
                    duration_seconds=row.duration_seconds,
                    audio_path=row.audio_path,
                    reuse_count=reuse_count,
                    reused_seconds=_safe_int(entry.get("reused_seconds")),
                    event_count=event_count,
                    last_reused_at=str(row.last_reused_at or "") or None,
                    last_reused_in_playlist_id=str(row.last_reused_in_playlist_id or "") or None,
                    last_reused_by=str(row.last_reused_by or "") or None,
                )
            )

    ascending = clean_direction == "asc"
    if clean_sort in {"title", "name"}:
        summaries.sort(key=lambda item: item.title.lower(), reverse=not ascending)
    elif clean_sort in {"reused_seconds", "seconds", "duration"}:
        summaries.sort(
            key=lambda item: (
                item.reused_seconds if ascending else -item.reused_seconds,
                item.reuse_count if ascending else -item.reuse_count,
                item.title.lower(),
            )
        )
    else:
        summaries.sort(
            key=lambda item: (
                item.reuse_count if ascending else -item.reuse_count,
                item.reused_seconds if ascending else -item.reused_seconds,
                item.title.lower(),
            )
        )
    summaries = summaries[:limit]
    with _track_reuse_summary_cache_lock:
        _track_reuse_summary_cache[cache_key] = (now, summaries)
        if len(_track_reuse_summary_cache) > 16:
            oldest_key = min(_track_reuse_summary_cache, key=lambda key: _track_reuse_summary_cache[key][0])
            _track_reuse_summary_cache.pop(oldest_key, None)
    return summaries


@router.get("/{track_id}/reuse", response_model=list[TrackReuseEventRead])
def get_track_reuse_events(
    track_id: str,
    db: Session = Depends(get_db),
) -> list[TrackReuseEventRead]:
    track = db.get(Track, track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    events = db.scalars(
        select(TrackReuseEvent)
        .where(TrackReuseEvent.track_id == track_id)
        .options(
            selectinload(TrackReuseEvent.track),
            selectinload(TrackReuseEvent.target_playlist),
            selectinload(TrackReuseEvent.source_playlist),
        )
        .order_by(TrackReuseEvent.created_at.desc())
    ).all()
    return [_serialize_track_reuse_event(event) for event in events]


@router.get("/{track_id}", response_model=TrackRead)
def get_track(track_id: str, db: Session = Depends(get_db)) -> TrackRead:
    track = db.get(Track, track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    return TrackRead.model_validate(track)


@router.post("/{track_id}/rating", response_model=TrackRead)
def rate_track(
    track_id: str,
    payload: TrackRatingRequest,
    db: Session = Depends(get_db),
) -> TrackRead:
    track = db.get(Track, track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    metadata = dict(track.metadata_json or {})
    if payload.rating == "none":
        metadata.pop("user_rating", None)
        metadata.pop("user_rating_actor", None)
        metadata.pop("user_rating_at", None)
    else:
        metadata["user_rating"] = payload.rating
        metadata["user_rating_actor"] = payload.actor
        metadata["user_rating_at"] = datetime.now(timezone.utc).isoformat()
    track.metadata_json = metadata
    db.add(track)
    db.commit()
    db.refresh(track)
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
    elif payload.decision == DecisionValue.reject:
        pending_workspace_id = (track.metadata_json or {}).get("pending_workspace_id")
        maybe_archive_rejected_single_workspace(
            db,
            playlist_id=pending_workspace_id,
            actor=payload.actor,
        )

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
