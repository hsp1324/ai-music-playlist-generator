from __future__ import annotations

import hashlib
import re
import secrets
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.models.enums import JobStatus, JobType, PlaylistStatus
from app.models.job import Job
from app.models.playlist import Playlist, PlaylistItem
from app.services.registry import ServiceRegistry
from app.utils.local_video_cleanup import cleanup_public_uploaded_local_videos
from app.utils.ops_notifications import (
    notify_render_worker_claimed,
    notify_render_worker_completed,
    notify_render_worker_timeout_requeued,
)
from app.utils.render_worker_registry import record_render_worker_seen, render_worker_display_name
from app.utils.youtube_metadata_state import apply_generated_youtube_metadata, has_youtube_metadata
from app.utils.youtube_localizations import ensure_playlist_title_prefix

router = APIRouter(prefix="/render-worker", tags=["render-worker"])

CONTENT_RANGE_RE = re.compile(r"^bytes\s+(\d+)-(\d+)/(\d+|\*)$")


class RenderWorkerClaimRequest(BaseModel):
    worker_id: str = Field(min_length=1, max_length=128)
    hostname: str = ""
    capabilities: dict[str, Any] = Field(default_factory=dict)


class RenderWorkerProgressRequest(BaseModel):
    worker_id: str = Field(min_length=1, max_length=128)
    progress: dict[str, Any] = Field(default_factory=dict)
    message: str = ""


class RenderWorkerCompleteRequest(BaseModel):
    worker_id: str = Field(min_length=1, max_length=128)
    size_bytes: int | None = None
    sha256: str | None = None
    message: str = "External video render completed."


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def get_services(request: Request) -> ServiceRegistry:
    return request.app.state.services


def _run_public_video_cleanup(db: Session, services: ServiceRegistry) -> None:
    cleanup_public_uploaded_local_videos(db, services.settings)


def _request_token(
    authorization: str | None = Header(default=None),
    x_render_worker_token: str | None = Header(default=None),
) -> str:
    if x_render_worker_token:
        return x_render_worker_token.strip()
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return ""


def _require_render_worker_token(services: ServiceRegistry, token: str) -> None:
    expected = services.settings.render_worker_shared_token.strip()
    if not expected:
        raise HTTPException(status_code=503, detail="Render worker token is not configured.")
    if not secrets.compare_digest(token, expected):
        raise HTTPException(status_code=403, detail="Invalid render worker token.")


def _require_external_mode(services: ServiceRegistry) -> None:
    if services.settings.video_render_execution_mode != "external":
        raise HTTPException(
            status_code=409,
            detail="External video rendering is disabled. Set AIMP_VIDEO_RENDER_EXECUTION_MODE=external.",
        )


def _playlist_track_ids(playlist: Playlist) -> list[str]:
    return [
        item.track_id
        for item in sorted(playlist.items, key=lambda item: item.order_index)
        if item.track_id
    ]


def _load_render_job(db: Session, job_id: str) -> tuple[Job, Playlist]:
    job = db.get(Job, job_id)
    if not job or job.type != JobType.build_video:
        raise HTTPException(status_code=404, detail="Render job not found.")
    playlist = db.scalars(
        select(Playlist)
        .options(selectinload(Playlist.items).selectinload(PlaylistItem.track))
        .where(Playlist.id == job.playlist_id)
    ).first()
    if not playlist:
        raise HTTPException(status_code=404, detail="Release not found for render job.")
    return job, playlist


def _asset_path(playlist: Playlist, kind: str) -> Path:
    meta = dict(playlist.metadata_json or {})
    if kind == "audio":
        path = playlist.output_audio_path
    elif kind == "cover":
        path = meta.get("cover_image_path")
    elif kind == "loop-video":
        path = meta.get("loop_video_path")
    else:
        raise HTTPException(status_code=404, detail="Unknown render asset.")
    if not path:
        raise HTTPException(status_code=404, detail=f"{kind} asset is not available.")
    resolved = Path(str(path))
    if not resolved.exists() or not resolved.is_file():
        raise HTTPException(status_code=404, detail=f"{kind} asset is missing on disk.")
    return resolved


def _upload_paths(services: ServiceRegistry, job_id: str) -> tuple[Path, Path]:
    directory = services.settings.temp_dir / "render-worker"
    directory.mkdir(parents=True, exist_ok=True)
    part_path = directory / f"{job_id}.mp4.part"
    meta_path = directory / f"{job_id}.json"
    return part_path, meta_path


def _public_api_url(services: ServiceRegistry, path: str) -> str:
    return f"{services.settings.public_base_url.rstrip('/')}{services.settings.api_prefix}{path}"


def _file_info(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "filename": path.name,
        "size_bytes": stat.st_size,
        "updated_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
    }


def _recover_stale_external_render_jobs(db: Session, services: ServiceRegistry) -> int:
    timeout_seconds = max(int(services.settings.render_worker_claim_timeout_seconds or 0), 60)
    cutoff = _utcnow() - timedelta(seconds=timeout_seconds)
    recovered = 0
    notifications: list[dict[str, Any]] = []
    jobs = db.scalars(
        select(Job)
        .options(selectinload(Job.playlist))
        .where(Job.type == JobType.build_video, Job.status == JobStatus.running)
    ).all()
    for job in jobs:
        result = dict(job.result_json or {})
        worker = result.get("external_render_worker")
        if not isinstance(worker, dict):
            continue
        heartbeat_raw = str(worker.get("heartbeat_at") or worker.get("claimed_at") or "")
        try:
            heartbeat = datetime.fromisoformat(heartbeat_raw)
        except ValueError:
            heartbeat = job.started_at or job.created_at
        if heartbeat and heartbeat.tzinfo is None:
            heartbeat = heartbeat.replace(tzinfo=timezone.utc)
        if heartbeat and heartbeat > cutoff:
            continue

        now = _utcnow()
        heartbeat_for_notification = heartbeat or job.started_at or job.created_at
        worker["stale_detected_at"] = now.isoformat()
        worker["stale_reason"] = f"No heartbeat for {timeout_seconds} seconds."
        result["external_render_worker"] = worker
        job.status = JobStatus.queued
        job.started_at = None
        job.finished_at = None
        job.error_text = None
        job.result_json = result
        if job.playlist:
            meta = dict(job.playlist.metadata_json or {})
            meta["workflow_state"] = "video_queued"
            meta["note"] = "External video render worker timed out; render job was requeued."
            meta["video_render_progress"] = {
                **dict(meta.get("video_render_progress") or {}),
                "stage": "video_render",
                "status": "queued",
                "message": meta["note"],
                "updated_at": now.isoformat(),
            }
            job.playlist.status = PlaylistStatus.building
            job.playlist.metadata_json = meta
            db.add(job.playlist)
            notifications.append(
                {
                    "playlist_title": job.playlist.title,
                    "job_id": job.id,
                    "worker": dict(worker),
                    "timeout_seconds": timeout_seconds,
                    "heartbeat_at": heartbeat_for_notification,
                    "cover_image_path": str(meta.get("cover_image_path") or ""),
                    "now": now,
                }
            )
        db.add(job)
        recovered += 1
    if recovered:
        db.commit()
        for notification in notifications:
            notify_render_worker_timeout_requeued(db, services, **notification)
    return recovered


def _render_job_payload(job: Job, playlist: Playlist, services: ServiceRegistry) -> dict[str, Any]:
    meta = dict(playlist.metadata_json or {})
    audio_path = _asset_path(playlist, "audio")
    cover_path = _asset_path(playlist, "cover")
    loop_video_path = Path(str(meta.get("loop_video_path") or "")) if meta.get("loop_video_path") else None
    has_loop_video = bool(loop_video_path and loop_video_path.exists())
    allow_still_image_fallback = bool((job.payload_json or {}).get("allow_still_image_fallback"))
    if not has_loop_video and not allow_still_image_fallback:
        raise HTTPException(status_code=409, detail="Loop video is required before external video render.")

    assets = {
        "audio": {
            **_file_info(audio_path),
            "url": _public_api_url(services, f"/render-worker/jobs/{job.id}/assets/audio"),
        },
        "cover": {
            **_file_info(cover_path),
            "url": _public_api_url(services, f"/render-worker/jobs/{job.id}/assets/cover"),
        },
    }
    if has_loop_video and loop_video_path:
        assets["loop_video"] = {
            **_file_info(loop_video_path),
            "url": _public_api_url(services, f"/render-worker/jobs/{job.id}/assets/loop-video"),
        }

    style = str(
        (job.payload_json or {}).get("video_spectrum_overlay_style")
        or meta.get("video_spectrum_overlay_style")
        or "bars"
    )
    return {
        "id": job.id,
        "type": job.type.value,
        "status": job.status.value,
        "playlist_id": playlist.id,
        "title": playlist.title,
        "assets": assets,
        "render": {
            "mode": "loop_video" if has_loop_video else "still_image",
            "smooth_loop": bool(meta.get("loop_video_smooth", True)),
            "allow_still_image_fallback": allow_still_image_fallback,
            "video_spectrum_overlay_style": style,
            "total_duration_seconds": int(playlist.actual_duration_seconds or 0) or None,
            "track_ids": _playlist_track_ids(playlist),
            "output_filename": f"{playlist.id}.mp4",
        },
        "upload": {
            "status_url": _public_api_url(services, f"/render-worker/jobs/{job.id}/upload-status"),
            "chunk_url": _public_api_url(services, f"/render-worker/jobs/{job.id}/upload"),
            "complete_url": _public_api_url(services, f"/render-worker/jobs/{job.id}/complete"),
            "recommended_chunk_bytes": services.settings.render_worker_upload_chunk_bytes,
        },
    }


def _update_video_progress(db: Session, job: Job, playlist: Playlist, progress: dict[str, Any]) -> None:
    now = _utcnow().isoformat()
    payload = {
        **progress,
        "updated_at": now,
    }
    if "message" not in payload:
        payload["message"] = "External video render in progress."
    result = dict(job.result_json or {})
    worker = dict(result.get("external_render_worker") or {})
    worker["heartbeat_at"] = now
    result["external_render_worker"] = worker
    result["progress"] = payload
    job.result_json = result
    meta = dict(playlist.metadata_json or {})
    meta["video_render_progress"] = payload
    meta["note"] = str(payload.get("message") or "External video render in progress.")
    playlist.metadata_json = meta
    db.add(job)
    db.add(playlist)
    db.commit()


@router.get("/status")
def render_worker_status(
    services: ServiceRegistry = Depends(get_services),
    token: str = Depends(_request_token),
    db: Session = Depends(get_db),
) -> dict:
    _require_render_worker_token(services, token)
    active_jobs = db.scalars(
        select(Job).where(Job.type == JobType.build_video, Job.status.in_([JobStatus.queued, JobStatus.running]))
    ).all()
    return {
        "ok": True,
        "mode": services.settings.video_render_execution_mode,
        "queued_or_running_video_jobs": len(active_jobs),
        "claim_timeout_seconds": services.settings.render_worker_claim_timeout_seconds,
    }


@router.post("/jobs/claim")
def claim_render_job(
    payload: RenderWorkerClaimRequest,
    services: ServiceRegistry = Depends(get_services),
    token: str = Depends(_request_token),
    db: Session = Depends(get_db),
) -> dict:
    _require_render_worker_token(services, token)
    _require_external_mode(services)
    recovered = _recover_stale_external_render_jobs(db, services)
    now = _utcnow()
    registry_worker = record_render_worker_seen(
        services.settings.storage_root,
        worker_id=payload.worker_id,
        hostname=payload.hostname,
        capabilities=payload.capabilities,
        claimed_at=now.isoformat(),
    )
    server_nickname = str(registry_worker.get("nickname") or "").strip()

    existing = db.scalars(
        select(Job)
        .where(Job.type == JobType.build_video, Job.status == JobStatus.running)
        .order_by(Job.started_at.asc())
    ).all()
    for job in existing:
        result = dict(job.result_json or {})
        worker = result.get("external_render_worker")
        if isinstance(worker, dict) and worker.get("worker_id") == payload.worker_id:
            job, playlist = _load_render_job(db, job.id)
            worker = dict(worker)
            worker["hostname"] = payload.hostname or worker.get("hostname") or ""
            worker["capabilities"] = payload.capabilities or worker.get("capabilities") or {}
            if server_nickname:
                worker["nickname"] = server_nickname
            else:
                worker.pop("nickname", None)
            result["external_render_worker"] = worker
            job.result_json = result
            db.add(job)
            db.commit()
            _update_video_progress(
                db,
                job,
                playlist,
                {
                    **dict((job.result_json or {}).get("progress") or {}),
                    "stage": "video_render",
                    "status": "running",
                    "message": "External render worker resumed its existing claim.",
                },
            )
            return {"ok": True, "job": _render_job_payload(job, playlist, services), "recovered_stale_jobs": recovered}

    candidate_ids = db.scalars(
        select(Job.id)
        .where(Job.type == JobType.build_video, Job.status == JobStatus.queued)
        .order_by(Job.created_at.asc())
        .limit(10)
    ).all()
    claimed_id = None
    for candidate_id in candidate_ids:
        update_result = db.execute(
            update(Job)
            .where(Job.id == candidate_id, Job.status == JobStatus.queued)
            .values(status=JobStatus.running, started_at=now)
        )
        db.commit()
        if update_result.rowcount == 1:
            claimed_id = candidate_id
            break

    if not claimed_id:
        return {"ok": True, "job": None, "recovered_stale_jobs": recovered}

    job, playlist = _load_render_job(db, claimed_id)
    track_ids = _playlist_track_ids(playlist)
    result = dict(job.result_json or {})
    worker_meta = {
        "worker_id": payload.worker_id,
        "hostname": payload.hostname,
        "capabilities": payload.capabilities,
        "claimed_at": now.isoformat(),
        "heartbeat_at": now.isoformat(),
        "rendered_track_ids": track_ids,
    }
    if server_nickname:
        worker_meta["nickname"] = server_nickname
    result["external_render_worker"] = worker_meta
    job.result_json = result
    meta = dict(playlist.metadata_json or {})
    meta["workflow_state"] = "video_rendering"
    worker_label = render_worker_display_name(worker_meta)
    meta["note"] = f"External render worker claimed the video job: {worker_label}."
    meta["video_render_progress"] = {
        "stage": "video_render",
        "progress_ratio": 0.0,
        "percent": 0.0,
        "processed_seconds": 0.0,
        "total_seconds": playlist.actual_duration_seconds or None,
        "eta_seconds": None,
        "status": "claimed",
        "message": meta["note"],
        "updated_at": now.isoformat(),
    }
    playlist.status = PlaylistStatus.building
    playlist.metadata_json = meta
    db.add(job)
    db.add(playlist)
    db.commit()
    notify_render_worker_claimed(db, services, playlist=playlist, job=job, worker=worker_meta, now=now)

    services.worker._request_openclaw_for_video_event(
        playlist_id=playlist.id,
        job_id=job.id,
        event="video_render_started",
        reason="external_video_render_started",
    )
    return {"ok": True, "job": _render_job_payload(job, playlist, services), "recovered_stale_jobs": recovered}


@router.get("/jobs/{job_id}/assets/{kind}", name="render_worker_download_asset")
def download_render_asset(
    job_id: str,
    kind: str,
    services: ServiceRegistry = Depends(get_services),
    token: str = Depends(_request_token),
    db: Session = Depends(get_db),
) -> FileResponse:
    _require_render_worker_token(services, token)
    job, playlist = _load_render_job(db, job_id)
    if job.status not in {JobStatus.queued, JobStatus.running, JobStatus.succeeded}:
        raise HTTPException(status_code=409, detail="Render job is not available for asset download.")
    path = _asset_path(playlist, kind)
    return FileResponse(path, filename=path.name)


@router.post("/jobs/{job_id}/progress")
def update_render_progress(
    job_id: str,
    payload: RenderWorkerProgressRequest,
    services: ServiceRegistry = Depends(get_services),
    token: str = Depends(_request_token),
    db: Session = Depends(get_db),
) -> dict:
    _require_render_worker_token(services, token)
    job, playlist = _load_render_job(db, job_id)
    if job.status != JobStatus.running:
        raise HTTPException(status_code=409, detail="Render job is not running.")
    progress = dict(payload.progress or {})
    if payload.message:
        progress["message"] = payload.message
    _update_video_progress(db, job, playlist, progress)
    return {"ok": True}


@router.get("/jobs/{job_id}/upload-status")
def render_upload_status(
    job_id: str,
    services: ServiceRegistry = Depends(get_services),
    token: str = Depends(_request_token),
    db: Session = Depends(get_db),
) -> dict:
    _require_render_worker_token(services, token)
    job, _playlist = _load_render_job(db, job_id)
    if job.status not in {JobStatus.running, JobStatus.succeeded}:
        raise HTTPException(status_code=409, detail="Render job is not running.")
    part_path, _meta_path = _upload_paths(services, job_id)
    received = part_path.stat().st_size if part_path.exists() else 0
    progress = dict((job.result_json or {}).get("progress") or {})
    return {
        "ok": True,
        "job_id": job_id,
        "received_bytes": received,
        "complete": bool(progress.get("upload_complete")),
        "status": job.status.value,
    }


@router.put("/jobs/{job_id}/upload")
async def upload_render_chunk(
    job_id: str,
    request: Request,
    content_range: str | None = Header(default=None, alias="Content-Range"),
    services: ServiceRegistry = Depends(get_services),
    token: str = Depends(_request_token),
    db: Session = Depends(get_db),
) -> dict:
    _require_render_worker_token(services, token)
    job, playlist = _load_render_job(db, job_id)
    if job.status != JobStatus.running:
        raise HTTPException(status_code=409, detail="Render job is not running.")
    if not content_range:
        raise HTTPException(status_code=411, detail="Content-Range header is required for resumable upload.")
    match = CONTENT_RANGE_RE.match(content_range.strip())
    if not match:
        raise HTTPException(status_code=400, detail="Invalid Content-Range header.")
    start = int(match.group(1))
    end = int(match.group(2))
    total = None if match.group(3) == "*" else int(match.group(3))
    if end < start:
        raise HTTPException(status_code=400, detail="Invalid upload byte range.")

    part_path, _meta_path = _upload_paths(services, job_id)
    current_size = part_path.stat().st_size if part_path.exists() else 0
    if start == 0 and current_size > 0:
        part_path.unlink()
        current_size = 0
    if start != current_size:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"expected_offset": current_size, "received_start": start},
        )

    bytes_written = 0
    mode = "ab" if start else "wb"
    with part_path.open(mode) as handle:
        async for chunk in request.stream():
            if not chunk:
                continue
            handle.write(chunk)
            bytes_written += len(chunk)

    expected = end - start + 1
    if bytes_written != expected:
        raise HTTPException(
            status_code=400,
            detail=f"Uploaded chunk size mismatch: got {bytes_written}, expected {expected}.",
        )

    received = part_path.stat().st_size
    progress = dict((job.result_json or {}).get("progress") or {})
    upload_ratio = (received / total) if total and total > 0 else None
    progress.update(
        {
            "stage": "video_upload",
            "status": "uploading",
            "upload_received_bytes": received,
            "upload_total_bytes": total,
            "upload_percent": round(upload_ratio * 100, 1) if upload_ratio is not None else None,
            "message": "External render worker is uploading the rendered video.",
        }
    )
    if total and received >= total:
        progress["upload_complete"] = True
        progress["message"] = "External render worker upload complete; awaiting finalize."
    _update_video_progress(db, job, playlist, progress)
    _run_public_video_cleanup(db, services)
    return {"ok": True, "received_bytes": received, "complete": bool(total and received >= total)}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@router.post("/jobs/{job_id}/complete")
def complete_render_job(
    job_id: str,
    payload: RenderWorkerCompleteRequest,
    services: ServiceRegistry = Depends(get_services),
    token: str = Depends(_request_token),
    db: Session = Depends(get_db),
) -> dict:
    _require_render_worker_token(services, token)
    job, playlist = _load_render_job(db, job_id)
    if job.status == JobStatus.succeeded and playlist.output_video_path and Path(playlist.output_video_path).exists():
        return {"ok": True, "playlist_id": playlist.id, "output_video_path": playlist.output_video_path}
    if job.status != JobStatus.running:
        raise HTTPException(status_code=409, detail="Render job is not running.")

    part_path, _meta_path = _upload_paths(services, job_id)
    if not part_path.exists() or part_path.stat().st_size == 0:
        raise HTTPException(status_code=400, detail="Rendered video upload is empty or missing.")
    if payload.size_bytes is not None and part_path.stat().st_size != payload.size_bytes:
        raise HTTPException(status_code=400, detail="Rendered video size does not match uploaded bytes.")
    if payload.sha256 and _sha256_file(part_path).lower() != payload.sha256.lower():
        raise HTTPException(status_code=400, detail="Rendered video checksum mismatch.")

    result = dict(job.result_json or {})
    worker = dict(result.get("external_render_worker") or {})
    rendered_track_ids = list(worker.get("rendered_track_ids") or [])
    current_track_ids = _playlist_track_ids(playlist)
    now = _utcnow()
    if rendered_track_ids and current_track_ids != rendered_track_ids:
        part_path.unlink(missing_ok=True)
        meta = dict(playlist.metadata_json or {})
        meta["metadata_approved"] = False
        meta["publish_approved"] = False
        meta["workflow_state"] = "pending_audio_render"
        meta["note"] = "Track list changed while external video was rendering. Re-render audio/video before publishing."
        meta["stale_video_render"] = {
            "rendered_track_ids": rendered_track_ids,
            "current_track_ids": current_track_ids,
            "detected_at": now.isoformat(),
        }
        meta.pop("rendered_video_track_ids", None)
        meta.pop("rendered_video_track_count", None)
        playlist.output_video_path = None
        playlist.status = PlaylistStatus.ready
        playlist.metadata_json = meta
        job.status = JobStatus.succeeded
        job.finished_at = now
        result["stale_output_discarded"] = True
        result["rendered_track_ids"] = rendered_track_ids
        result["current_track_ids"] = current_track_ids
        job.result_json = result
        db.add(playlist)
        db.add(job)
        db.commit()
        return {"ok": True, "stale": True, "playlist_id": playlist.id}

    output_path = services.settings.playlists_dir / f"{playlist.id}.mp4"
    output_path.unlink(missing_ok=True)
    shutil.move(str(part_path), output_path)

    meta = dict(playlist.metadata_json or {})
    render_meta = dict(meta)
    for key in (
        "dreamina_job_id",
        "dreamina_video_url",
        "loop_video_path",
        "loop_video_render_mode",
        "loop_video_smooth",
        "loop_video_source",
        "video_spectrum_overlay_style",
    ):
        if key in render_meta:
            meta[key] = render_meta[key]

    playlist.output_video_path = str(output_path)
    is_playlist_release = str(meta.get("workspace_mode") or "playlist") != "single_track_video"
    if has_youtube_metadata(meta):
        meta["youtube_metadata_preserved_after_video_render"] = True
    else:
        tracks = [item.track for item in sorted(playlist.items, key=lambda item: item.order_index) if item.track]
        youtube_metadata = services.release_metadata.build_youtube_metadata(playlist, tracks)
        apply_generated_youtube_metadata(meta, youtube_metadata, is_playlist_release=is_playlist_release)
        meta["youtube_title"] = ensure_playlist_title_prefix(
            meta["youtube_title"],
            is_playlist=is_playlist_release,
        )
        meta["youtube_metadata_preserved_after_video_render"] = False
    meta["metadata_approved"] = False
    meta["publish_approved"] = False
    meta["rendered_video_track_ids"] = current_track_ids
    meta["rendered_video_track_count"] = len(current_track_ids)
    meta.pop("stale_video_render", None)
    meta.pop("video_build_error", None)
    meta["workflow_state"] = "metadata_review"
    meta["note"] = payload.message or "External video render completed. Review YouTube metadata next."
    meta["video_render_progress"] = {
        **dict(meta.get("video_render_progress") or {}),
        "stage": "video_render",
        "progress_ratio": 1.0,
        "percent": 100.0,
        "eta_seconds": 0,
        "status": "end",
        "message": "External video render completed.",
        "updated_at": now.isoformat(),
    }
    playlist.metadata_json = meta
    playlist.status = PlaylistStatus.ready

    result.update(
        {
            "playlist_id": playlist.id,
            "output_video_path": playlist.output_video_path,
            "youtube_title": meta.get("youtube_title"),
            "progress": meta["video_render_progress"],
        }
    )
    job.status = JobStatus.succeeded
    job.finished_at = now
    job.result_json = result
    db.add(playlist)
    db.add(job)
    db.commit()
    _run_public_video_cleanup(db, services)
    notify_render_worker_completed(db, services, playlist=playlist, job=job, worker=worker, now=now)

    services.worker._request_openclaw_for_video_event(
        playlist_id=playlist.id,
        job_id=job.id,
        event="video_render_completed",
        reason="external_video_render_completed",
    )
    return {
        "ok": True,
        "playlist_id": playlist.id,
        "output_video_path": playlist.output_video_path,
        "workflow_state": meta["workflow_state"],
    }
