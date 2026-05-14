from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from secrets import compare_digest
from typing import Any
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.orm import Session, selectinload

from app.models.enums import JobStatus, JobType, PlaylistStatus
from app.models.job import Job
from app.models.playlist import Playlist, PlaylistItem
from app.services.background_worker import (
    _playlist_track_ids,
    _rendered_snapshot_matches_current_tracks,
    _utcnow,
)
from app.utils.youtube_localizations import (
    DEFAULT_YOUTUBE_LANGUAGE,
    ensure_playlist_localization_title_prefix,
    ensure_playlist_title_prefix,
    normalize_youtube_language,
    normalize_youtube_localizations,
)


EXTERNAL_RENDER_SOURCE_PREFIX = "external-render-worker"


class RenderWorkerAuthError(ValueError):
    pass


class RenderWorkerJobError(ValueError):
    pass


def validate_worker_shared_token(configured_token: str, supplied_token: str | None) -> None:
    configured = str(configured_token or "").strip()
    if not configured:
        return
    supplied = str(supplied_token or "").strip()
    if not supplied or not compare_digest(configured, supplied):
        raise RenderWorkerAuthError("Invalid render worker token.")


def reset_stale_external_video_jobs(db: Session, *, stale_seconds: int) -> int:
    cutoff = _utcnow() - timedelta(seconds=max(int(stale_seconds or 0), 60))
    stale_count = 0
    jobs = db.scalars(
        select(Job)
        .options(selectinload(Job.playlist))
        .where(Job.type == JobType.build_video, Job.status == JobStatus.running)
    ).all()
    for job in jobs:
        if not _is_external_render_job(job):
            continue
        last_activity = _external_render_last_activity(job)
        if last_activity and last_activity > cutoff:
            continue

        result = dict(job.result_json or {})
        payload = dict(job.payload_json or {})
        stale_count += 1
        result["external_render_stale_reset_at"] = _utcnow().isoformat()
        result["external_render_stale_worker_id"] = (
            result.get("external_render_worker_id")
            or payload.get("external_render_worker_id")
            or job.external_id
        )
        result["external_render_stale_last_activity_at"] = (
            last_activity.isoformat() if last_activity else None
        )
        result.pop("external_render_lease_token", None)
        job.status = JobStatus.queued
        job.started_at = None
        job.finished_at = None
        job.error_text = None
        job.external_id = None
        job.source = f"{EXTERNAL_RENDER_SOURCE_PREFIX}:requeued-stale"
        job.result_json = result

        playlist = job.playlist
        if playlist:
            meta = dict(playlist.metadata_json or {})
            meta["workflow_state"] = "video_queued"
            meta["note"] = (
                "External render worker did not heartbeat within the timeout; "
                "video render was requeued."
            )
            meta["video_render_progress"] = {
                **dict(meta.get("video_render_progress") or {}),
                "stage": "video_render",
                "status": "queued",
                "message": meta["note"],
                "updated_at": _utcnow().isoformat(),
            }
            playlist.status = PlaylistStatus.building
            playlist.metadata_json = meta
            db.add(playlist)
        db.add(job)
    if stale_count:
        db.commit()
    return stale_count


def claim_external_video_job(
    db: Session,
    services,
    *,
    worker_id: str,
    capabilities: list[str] | None = None,
) -> dict[str, Any] | None:
    reset_stale_external_video_jobs(
        db,
        stale_seconds=services.settings.render_worker_stale_seconds,
    )
    candidate_ids = db.scalars(
        select(Job.id)
        .where(Job.type == JobType.build_video, Job.status == JobStatus.queued)
        .order_by(Job.created_at.asc())
        .limit(10)
    ).all()
    for candidate_id in candidate_ids:
        claimed_at = _utcnow()
        update_result = db.execute(
            update(Job)
            .where(Job.id == candidate_id, Job.status == JobStatus.queued)
            .values(
                status=JobStatus.running,
                started_at=claimed_at,
                source=f"{EXTERNAL_RENDER_SOURCE_PREFIX}:{worker_id}",
                external_id=worker_id,
            )
        )
        db.commit()
        if update_result.rowcount != 1:
            continue

        job = _load_job_with_playlist(db, candidate_id)
        if not job or not job.playlist:
            continue
        try:
            render_inputs = _validated_render_inputs(job.playlist, job)
        except Exception as exc:  # noqa: BLE001
            mark_external_video_job_failed(db, job, str(exc))
            continue

        lease_token = uuid4().hex
        attempts = _coerce_int((job.result_json or {}).get("external_render_attempts")) + 1
        video_track_ids = _playlist_track_ids(job.playlist)
        payload = dict(job.payload_json or {})
        payload["external_render_worker_id"] = worker_id
        payload["external_render_capabilities"] = list(capabilities or [])
        payload["external_render_claimed_at"] = claimed_at.isoformat()
        result = dict(job.result_json or {})
        result.update(
            {
                "external_render_worker_id": worker_id,
                "external_render_lease_token": lease_token,
                "external_render_claimed_at": claimed_at.isoformat(),
                "external_render_heartbeat_at": claimed_at.isoformat(),
                "external_render_attempts": attempts,
                "rendered_video_track_ids": video_track_ids,
                "loop_video_render_mode": render_inputs["render_mode"],
            }
        )
        progress = {
            "stage": "video_render",
            "progress_ratio": 0.0,
            "percent": 0.0,
            "processed_seconds": 0.0,
            "total_seconds": render_inputs["total_duration_seconds"],
            "eta_seconds": None,
            "status": "claimed",
            "message": f"External render worker {worker_id} claimed this video render.",
            "updated_at": claimed_at.isoformat(),
        }
        result["progress"] = progress
        job.payload_json = payload
        job.result_json = result

        playlist = job.playlist
        meta = dict(playlist.metadata_json or {})
        meta["workflow_state"] = "video_rendering"
        meta["note"] = progress["message"]
        meta["video_render_progress"] = progress
        meta.pop("video_build_error", None)
        playlist.status = PlaylistStatus.building
        playlist.metadata_json = meta
        db.add(job)
        db.add(playlist)
        db.commit()
        db.refresh(job)
        db.refresh(playlist)
        return _build_claim_manifest(job, playlist, render_inputs, lease_token)
    return None


def get_render_worker_asset_path(
    db: Session,
    *,
    job_id: str,
    lease_token: str,
    asset_name: str,
) -> Path:
    job = load_external_running_job(db, job_id=job_id, lease_token=lease_token)
    if not job.playlist:
        raise RenderWorkerJobError("Playlist not found for render worker job.")
    render_inputs = _validated_render_inputs(job.playlist, job)
    if asset_name == "audio":
        return render_inputs["audio_path"]
    if asset_name == "cover":
        return render_inputs["cover_image_path"]
    if asset_name == "loop-video":
        loop_video_path = render_inputs.get("loop_video_path")
        if not loop_video_path:
            raise RenderWorkerJobError("This render job does not have a loop video asset.")
        return loop_video_path
    raise RenderWorkerJobError("Unknown render asset.")


def load_external_running_job(db: Session, *, job_id: str, lease_token: str) -> Job:
    job = _load_job_with_playlist(db, job_id)
    if not job:
        raise RenderWorkerJobError("Render job not found.")
    if job.type != JobType.build_video:
        raise RenderWorkerJobError("Render job is not a video render job.")
    if job.status != JobStatus.running:
        raise RenderWorkerJobError("Render job is not currently leased.")
    result = dict(job.result_json or {})
    expected = str(result.get("external_render_lease_token") or "")
    if not expected or not compare_digest(expected, str(lease_token or "")):
        raise RenderWorkerAuthError("Invalid render worker lease token.")
    return job


def update_external_video_heartbeat(
    db: Session,
    *,
    job_id: str,
    lease_token: str,
    worker_id: str,
    progress: dict[str, Any] | None = None,
    message: str | None = None,
) -> dict[str, Any]:
    job = load_external_running_job(db, job_id=job_id, lease_token=lease_token)
    playlist = job.playlist
    if not playlist:
        raise RenderWorkerJobError("Playlist not found for render worker job.")
    now = _utcnow()
    payload = dict(progress or {})
    payload["stage"] = payload.get("stage") or "video_render"
    payload["status"] = payload.get("status") or "running"
    payload["message"] = message or payload.get("message") or "External render worker is rendering video."
    payload["updated_at"] = now.isoformat()
    result = dict(job.result_json or {})
    result["external_render_worker_id"] = worker_id or result.get("external_render_worker_id")
    result["external_render_heartbeat_at"] = now.isoformat()
    result["progress"] = payload
    job.result_json = result
    job.external_id = worker_id or job.external_id

    meta = dict(playlist.metadata_json or {})
    meta["workflow_state"] = "video_rendering"
    meta["note"] = payload["message"]
    meta["video_render_progress"] = payload
    playlist.status = PlaylistStatus.building
    playlist.metadata_json = meta
    db.add(job)
    db.add(playlist)
    db.commit()
    return payload


def complete_external_video_job(
    db: Session,
    services,
    *,
    job_id: str,
    lease_token: str,
    worker_id: str,
    rendered_video_path: Path,
) -> dict[str, Any]:
    job = load_external_running_job(db, job_id=job_id, lease_token=lease_token)
    playlist = _load_playlist_with_tracks(db, job.playlist_id)
    if not playlist:
        raise RenderWorkerJobError("Playlist not found for render worker job.")
    if not rendered_video_path.exists() or rendered_video_path.stat().st_size == 0:
        raise RenderWorkerJobError("Rendered video upload is empty.")

    result = dict(job.result_json or {})
    video_track_ids = list(result.get("rendered_video_track_ids") or _playlist_track_ids(playlist))
    current_track_ids = _playlist_track_ids(playlist)
    if current_track_ids != video_track_ids:
        meta = dict(playlist.metadata_json or {})
        meta["metadata_approved"] = False
        meta["publish_approved"] = False
        meta["workflow_state"] = "pending_audio_render"
        meta["note"] = "Track list changed while an external worker rendered video. Re-render before publishing."
        meta["stale_video_render"] = {
            "rendered_track_ids": video_track_ids,
            "current_track_ids": current_track_ids,
            "detected_at": _utcnow().isoformat(),
        }
        meta.pop("rendered_video_track_ids", None)
        meta.pop("rendered_video_track_count", None)
        playlist.output_video_path = None
        playlist.status = PlaylistStatus.ready
        playlist.metadata_json = meta
        result.update(
            {
                "playlist_id": playlist.id,
                "stale_output_video_path": str(rendered_video_path),
                "rendered_track_ids": video_track_ids,
                "current_track_ids": current_track_ids,
                "external_render_completed_at": _utcnow().isoformat(),
            }
        )
        _finish_job_success(job, result)
        db.add(playlist)
        db.add(job)
        db.commit()
        return {
            "ok": True,
            "playlist_id": playlist.id,
            "workflow_state": meta["workflow_state"],
            "output_video_path": None,
        }

    meta = dict(playlist.metadata_json or {})
    cover_image_path = meta.get("cover_image_path")
    if not cover_image_path:
        raise RenderWorkerJobError("Approved cover image is missing from playlist metadata.")
    render_meta = {
        **meta,
        "loop_video_render_mode": result.get("loop_video_render_mode") or meta.get("loop_video_render_mode"),
        "video_spectrum_overlay_style": (
            (job.payload_json or {}).get("video_spectrum_overlay_style")
            or meta.get("video_spectrum_overlay_style")
            or "bars"
        ),
    }
    playlist.output_video_path = str(rendered_video_path)
    tracks = [
        item.track
        for item in sorted(playlist.items, key=lambda item: item.order_index)
        if item.track is not None
    ]
    youtube_metadata = services.release_metadata.build_youtube_metadata(playlist, tracks)
    meta = dict(playlist.metadata_json or {})
    for key in (
        "dreamina_job_id",
        "dreamina_video_url",
        "loop_video_path",
        "loop_video_render_mode",
        "loop_video_smooth",
        "loop_video_source",
        "video_spectrum_overlay_style",
    ):
        if render_meta.get(key) is not None:
            meta[key] = render_meta[key]
    is_playlist_release = str(meta.get("workspace_mode") or "playlist") != "single_track_video"
    meta["youtube_title"] = ensure_playlist_title_prefix(
        youtube_metadata.title,
        is_playlist=is_playlist_release,
    )
    meta["youtube_description"] = youtube_metadata.description
    meta["youtube_tags"] = youtube_metadata.tags
    meta["youtube_default_language"] = normalize_youtube_language(
        getattr(youtube_metadata, "default_language", DEFAULT_YOUTUBE_LANGUAGE)
    )
    meta["youtube_localizations"] = ensure_playlist_localization_title_prefix(
        normalize_youtube_localizations(
            getattr(youtube_metadata, "localizations", {}),
            default_title=meta["youtube_title"],
            default_description=youtube_metadata.description,
            default_language=meta["youtube_default_language"],
        ),
        is_playlist=is_playlist_release,
    )
    meta["metadata_approved"] = False
    meta["publish_approved"] = False
    meta["rendered_video_track_ids"] = video_track_ids
    meta["rendered_video_track_count"] = len(video_track_ids)
    meta.pop("stale_video_render", None)
    meta["workflow_state"] = "metadata_review"
    meta["note"] = f"External render worker {worker_id} completed video render."
    meta["video_render_progress"] = {
        **dict(meta.get("video_render_progress") or {}),
        "stage": "video_render",
        "progress_ratio": 1.0,
        "percent": 100.0,
        "eta_seconds": 0,
        "status": "end",
        "message": meta["note"],
        "updated_at": _utcnow().isoformat(),
    }
    playlist.metadata_json = meta
    playlist.status = PlaylistStatus.ready

    result.update(
        {
            "playlist_id": playlist.id,
            "cover_image_path": cover_image_path,
            "output_video_path": playlist.output_video_path,
            "youtube_title": meta["youtube_title"],
            "progress": meta["video_render_progress"],
            "external_render_completed_at": _utcnow().isoformat(),
            "external_render_worker_id": worker_id or result.get("external_render_worker_id"),
        }
    )
    _finish_job_success(job, result)
    db.add(playlist)
    db.add(job)
    db.commit()
    return {
        "ok": True,
        "playlist_id": playlist.id,
        "workflow_state": meta["workflow_state"],
        "output_video_path": playlist.output_video_path,
    }


def mark_external_video_job_failed(db: Session, job: Job, error_text: str) -> None:
    playlist = job.playlist or (db.get(Playlist, job.playlist_id) if job.playlist_id else None)
    if playlist:
        meta = dict(playlist.metadata_json or {})
        meta["workflow_state"] = "video_build_failed"
        meta["video_build_error"] = error_text
        meta["note"] = f"External video render failed: {error_text}"
        meta["video_render_progress"] = {
            **dict(meta.get("video_render_progress") or {}),
            "status": "failed",
            "message": meta["note"],
            "updated_at": _utcnow().isoformat(),
        }
        playlist.status = PlaylistStatus.ready
        playlist.metadata_json = meta
        db.add(playlist)
    result = dict(job.result_json or {})
    result["external_render_failed_at"] = _utcnow().isoformat()
    result["external_render_error"] = error_text
    result.pop("external_render_lease_token", None)
    job.result_json = result
    job.status = JobStatus.failed
    job.error_text = error_text
    job.finished_at = _utcnow()
    db.add(job)
    db.commit()


def _load_job_with_playlist(db: Session, job_id: str) -> Job | None:
    return db.scalars(
        select(Job)
        .options(selectinload(Job.playlist).selectinload(Playlist.items).selectinload(PlaylistItem.track))
        .where(Job.id == job_id)
    ).first()


def _load_playlist_with_tracks(db: Session, playlist_id: str | None) -> Playlist | None:
    if not playlist_id:
        return None
    return db.scalars(
        select(Playlist)
        .options(selectinload(Playlist.items).selectinload(PlaylistItem.track))
        .where(Playlist.id == playlist_id)
    ).first()


def _validated_render_inputs(playlist: Playlist, job: Job) -> dict[str, Any]:
    meta = dict(playlist.metadata_json or {})
    if not playlist.output_audio_path:
        raise RenderWorkerJobError("Playlist audio has not been rendered yet.")
    audio_path = Path(playlist.output_audio_path)
    if not audio_path.exists():
        raise RenderWorkerJobError("Rendered playlist audio file is missing on disk.")
    cover_image_path_text = str(meta.get("cover_image_path") or "").strip()
    cover_image_path = Path(cover_image_path_text) if cover_image_path_text else None
    if not cover_image_path or not cover_image_path.exists():
        raise RenderWorkerJobError("Approved cover image is missing on disk.")
    if not meta.get("cover_approved"):
        raise RenderWorkerJobError("Cover image must be approved before video render.")
    if not _rendered_snapshot_matches_current_tracks(playlist, "rendered_track_ids"):
        raise RenderWorkerJobError("Rendered audio is stale because the track list changed.")

    loop_video_path_text = str(meta.get("loop_video_path") or "").strip()
    loop_video_path = Path(loop_video_path_text) if loop_video_path_text else None
    allow_still_image_fallback = bool((job.payload_json or {}).get("allow_still_image_fallback"))
    use_loop_video = bool(loop_video_path and loop_video_path.exists())
    if use_loop_video:
        render_mode = "smooth-forward-crossfade" if meta.get("loop_video_smooth", True) else "hard-loop"
    elif allow_still_image_fallback:
        render_mode = "still-image-fallback"
        loop_video_path = None
    else:
        raise RenderWorkerJobError("Uploaded loop video is required before video render.")

    return {
        "audio_path": audio_path,
        "cover_image_path": cover_image_path,
        "loop_video_path": loop_video_path if use_loop_video else None,
        "use_loop_video": use_loop_video,
        "render_mode": render_mode,
        "smooth_loop": bool(meta.get("loop_video_smooth", True)),
        "spectrum_overlay_style": str(
            (job.payload_json or {}).get("video_spectrum_overlay_style")
            or meta.get("video_spectrum_overlay_style")
            or "bars"
        ),
        "total_duration_seconds": max(float(playlist.actual_duration_seconds or 0), 0.0) or None,
    }


def _build_claim_manifest(
    job: Job,
    playlist: Playlist,
    render_inputs: dict[str, Any],
    lease_token: str,
) -> dict[str, Any]:
    assets = {
        "audio": _asset_manifest(job.id, "audio", render_inputs["audio_path"]),
        "cover": _asset_manifest(job.id, "cover", render_inputs["cover_image_path"]),
    }
    if render_inputs.get("loop_video_path"):
        assets["loop_video"] = _asset_manifest(job.id, "loop-video", render_inputs["loop_video_path"])
    return {
        "has_job": True,
        "job_id": job.id,
        "lease_token": lease_token,
        "playlist_id": playlist.id,
        "title": playlist.title,
        "assets": assets,
        "render": {
            "use_loop_video": render_inputs["use_loop_video"],
            "smooth_loop": render_inputs["smooth_loop"],
            "spectrum_overlay_style": render_inputs["spectrum_overlay_style"],
            "total_duration_seconds": render_inputs["total_duration_seconds"],
            "output_filename": f"{playlist.id}.mp4",
        },
    }


def _asset_manifest(job_id: str, asset_name: str, path: Path) -> dict[str, Any]:
    return {
        "path": f"/render-worker/jobs/{job_id}/assets/{asset_name}",
        "filename": path.name,
        "size_bytes": path.stat().st_size,
    }


def _finish_job_success(job: Job, result: dict[str, Any]) -> None:
    result.pop("external_render_lease_token", None)
    job.result_json = result
    job.status = JobStatus.succeeded
    job.error_text = None
    job.finished_at = _utcnow()


def _is_external_render_job(job: Job) -> bool:
    source = str(job.source or "")
    payload = dict(job.payload_json or {})
    result = dict(job.result_json or {})
    return (
        source.startswith(EXTERNAL_RENDER_SOURCE_PREFIX)
        or bool(job.external_id)
        or bool(payload.get("external_render_worker_id"))
        or bool(result.get("external_render_worker_id"))
    )


def _external_render_last_activity(job: Job) -> datetime | None:
    result = dict(job.result_json or {})
    candidates = [
        _parse_datetime(result.get("external_render_heartbeat_at")),
        _parse_datetime(result.get("external_render_claimed_at")),
        _as_utc(job.started_at),
    ]
    candidates = [candidate for candidate in candidates if candidate is not None]
    return max(candidates) if candidates else None


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return _as_utc(value)
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return _as_utc(parsed)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _coerce_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0
