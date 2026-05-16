from __future__ import annotations

import asyncio
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.models.enums import JobStatus
from app.models.job import Job
from app.models.playlist import Playlist


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _coerce_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str) and value.strip():
        try:
            dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _format_duration(seconds: float | int | None) -> str:
    if seconds is None:
        return "unknown"
    total_seconds = max(int(round(float(seconds))), 0)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes}m {secs}s"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def _elapsed_since(value: Any, *, now: datetime | None = None) -> str:
    started_at = _coerce_datetime(value)
    if started_at is None:
        return "unknown"
    current = now or _utcnow()
    return _format_duration((current - started_at).total_seconds())


def _inline(value: Any) -> str:
    text = str(value or "").strip() or "Untitled"
    sanitized = text.replace("`", "'")
    return f"`{sanitized}`"


def _worker_label(worker: dict[str, Any] | None) -> str:
    payload = worker or {}
    nickname = str(payload.get("nickname") or "").strip()
    worker_id = str(payload.get("worker_id") or "").strip()
    hostname = str(payload.get("hostname") or "").strip()
    return nickname or worker_id or hostname or "unknown-worker"


def _ops_blocks(text: str, *, image_url: str | None = None, alt_text: str = "Cover") -> list[dict[str, Any]]:
    section: dict[str, Any] = {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": text[:2900],
        },
    }
    if image_url:
        section["accessory"] = {
            "type": "image",
            "image_url": image_url,
            "alt_text": alt_text[:200] or "Cover",
        }
    return [section]


def _playlist_cover_path(playlist: Playlist) -> str | None:
    meta = dict(playlist.metadata_json or {})
    for key in ("cover_image_path", "youtube_thumbnail_path"):
        value = str(meta.get(key) or "").strip()
        if value:
            return value
    return None


def _run_async(factory: Callable[[], Any]) -> Any:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(factory())

    result: dict[str, Any] = {}

    def runner() -> None:
        try:
            result["value"] = asyncio.run(factory())
        except Exception as exc:  # noqa: BLE001
            result["error"] = exc

    thread = threading.Thread(target=runner, name="aimp-ops-slack", daemon=True)
    thread.start()
    thread.join(timeout=15)
    if thread.is_alive():
        return {"ok": False, "error": "ops_slack_post_timeout"}
    if "error" in result:
        raise result["error"]
    return result.get("value")


def post_ops_message(
    db: Session,
    services,
    *,
    text: str,
    blocks: list[dict[str, Any]] | None = None,
    cover_image_path: str | None = None,
    cover_title: str | None = None,
) -> dict[str, Any]:
    try:
        installation = services.slack_installations.get_active_installation(db)
        token = installation.bot_token if installation else services.settings.slack_bot_token
        target_channel = services.settings.slack_ops_channel_id or services.settings.slack_review_channel_id
        rendered_blocks = blocks or _ops_blocks(text)
        cover_path = str(cover_image_path or "").strip()
        if cover_path.startswith(("http://", "https://")):
            rendered_blocks = _ops_blocks(text, image_url=cover_path, alt_text=cover_title or "Cover")
        elif cover_path and Path(cover_path).exists() and token and target_channel:
            upload_result = _run_async(
                lambda: services.slack.upload_local_file(
                    file_path=cover_path,
                    title=f"{cover_title or 'Release'} cover",
                    token=token,
                    channel=target_channel,
                    blocks=rendered_blocks,
                )
            )
            if bool(getattr(upload_result, "ok", False)):
                return {
                    "ok": True,
                    "channel": getattr(upload_result, "channel", None),
                    "ts": getattr(upload_result, "ts", None),
                    "file_id": getattr(upload_result, "file_id", None),
                    "raw": getattr(upload_result, "raw", None),
                    "mode": "file_with_blocks",
                }

        result = _run_async(lambda: services.slack.post_ops_message(token=token, text=text, blocks=rendered_blocks))
        return {
            "ok": bool(getattr(result, "ok", False)),
            "channel": getattr(result, "channel", None),
            "ts": getattr(result, "ts", None),
            "raw": getattr(result, "raw", None),
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


def notify_video_render_queued(db: Session, services, *, playlist: Playlist, job: Job | None) -> dict[str, Any]:
    if job is None or job.status != JobStatus.queued:
        return {"ok": False, "skipped": True, "reason": "video_job_not_queued"}
    result_json = dict(job.result_json or {})
    if result_json.get("ops_video_queued_notification"):
        return {"ok": False, "skipped": True, "reason": "already_notified"}

    payload = dict(job.payload_json or {})
    visualizer = str(payload.get("video_spectrum_overlay_style") or "bars")
    actor = str(payload.get("actor") or "unknown")
    mode = services.settings.video_render_execution_mode
    text = (
        f"Video render queued: {_inline(playlist.title)}.\n"
        f"mode: `{mode}`; visualizer: `{visualizer}`; queued_by: `{actor}`."
    )
    result = post_ops_message(
        db,
        services,
        text=text,
        cover_image_path=_playlist_cover_path(playlist),
        cover_title=playlist.title,
    )
    result_json["ops_video_queued_notification"] = {
        **result,
        "sent_at": _utcnow().isoformat(),
    }
    job.result_json = result_json
    db.add(job)
    db.commit()
    return result


def notify_render_worker_claimed(
    db: Session,
    services,
    *,
    playlist: Playlist,
    job: Job,
    worker: dict[str, Any],
    now: datetime | None = None,
) -> dict[str, Any]:
    current = now or _utcnow()
    queue_elapsed = _elapsed_since(job.created_at, now=current)
    text = (
        f"Render worker claimed video: {_inline(playlist.title)}.\n"
        f"worker: `{_worker_label(worker)}`; queued_for: `{queue_elapsed}`."
    )
    return post_ops_message(
        db,
        services,
        text=text,
        cover_image_path=_playlist_cover_path(playlist),
        cover_title=playlist.title,
    )


def notify_render_worker_completed(
    db: Session,
    services,
    *,
    playlist: Playlist,
    job: Job,
    worker: dict[str, Any],
    now: datetime | None = None,
) -> dict[str, Any]:
    current = now or _utcnow()
    elapsed = _elapsed_since(worker.get("claimed_at") or job.started_at, now=current)
    text = (
        f"Render worker completed video: {_inline(playlist.title)}.\n"
        f"worker: `{_worker_label(worker)}`; elapsed: `{elapsed}`."
    )
    return post_ops_message(
        db,
        services,
        text=text,
        cover_image_path=_playlist_cover_path(playlist),
        cover_title=playlist.title,
    )


def notify_render_worker_timeout_requeued(
    db: Session,
    services,
    *,
    playlist_title: str,
    job_id: str,
    worker: dict[str, Any],
    timeout_seconds: int,
    heartbeat_at: Any,
    cover_image_path: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    current = now or _utcnow()
    elapsed = _elapsed_since(heartbeat_at, now=current)
    text = (
        f"Render worker heartbeat timed out; video requeued: {_inline(playlist_title)}.\n"
        f"worker: `{_worker_label(worker)}`; timeout: `{_format_duration(timeout_seconds)}`; "
        f"no_heartbeat_for: `{elapsed}`."
    )
    return post_ops_message(
        db,
        services,
        text=text,
        cover_image_path=cover_image_path,
        cover_title=playlist_title,
    )


def notify_youtube_publish_completed(
    db: Session,
    services,
    *,
    playlist: Playlist,
    youtube_video_id: str,
    channel_title: str | None = None,
    scheduled_publish_at: str | None = None,
) -> dict[str, Any]:
    channel = str(channel_title or "").strip() or "unknown channel"
    youtube_link = f"https://youtu.be/{youtube_video_id}" if youtube_video_id else "missing video id"
    schedule = f"; scheduled: `{scheduled_publish_at}`" if scheduled_publish_at else ""
    text = (
        f"YouTube publish completed: {_inline(playlist.title)}.\n"
        f"channel: `{channel}`; video: {youtube_link}{schedule}."
    )
    return post_ops_message(
        db,
        services,
        text=text,
        cover_image_path=_playlist_cover_path(playlist),
        cover_title=playlist.title,
    )
