from __future__ import annotations

import asyncio
import threading
from datetime import datetime, timezone
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
    if nickname and worker_id and nickname != worker_id:
        return f"{nickname} ({worker_id})"
    return nickname or worker_id or hostname or "unknown-worker"


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


def post_ops_message(db: Session, services, *, text: str) -> dict[str, Any]:
    try:
        installation = services.slack_installations.get_active_installation(db)
        token = installation.bot_token if installation else services.settings.slack_bot_token
        result = _run_async(lambda: services.slack.post_ops_message(token=token, text=text))
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
        f"Video render queued: {_inline(playlist.title)}. "
        f"job_id: `{job.id}`; mode: `{mode}`; visualizer: `{visualizer}`; queued_by: `{actor}`."
    )
    result = post_ops_message(db, services, text=text)
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
        f"Render worker claimed video job: {_inline(playlist.title)}. "
        f"worker: `{_worker_label(worker)}`; job_id: `{job.id}`; queued_for: `{queue_elapsed}`."
    )
    return post_ops_message(db, services, text=text)


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
    size = ""
    output_path = str(playlist.output_video_path or "").strip()
    if output_path:
        size = f"; output: `{output_path}`"
    text = (
        f"Render worker completed video job: {_inline(playlist.title)}. "
        f"worker: `{_worker_label(worker)}`; job_id: `{job.id}`; elapsed: `{elapsed}`{size}."
    )
    return post_ops_message(db, services, text=text)


def notify_render_worker_timeout_requeued(
    db: Session,
    services,
    *,
    playlist_title: str,
    job_id: str,
    worker: dict[str, Any],
    timeout_seconds: int,
    heartbeat_at: Any,
    now: datetime | None = None,
) -> dict[str, Any]:
    current = now or _utcnow()
    elapsed = _elapsed_since(heartbeat_at, now=current)
    text = (
        f"Render worker heartbeat timed out; video job requeued: {_inline(playlist_title)}. "
        f"worker: `{_worker_label(worker)}`; job_id: `{job_id}`; "
        f"timeout: `{_format_duration(timeout_seconds)}`; no_heartbeat_for: `{elapsed}`."
    )
    return post_ops_message(db, services, text=text)


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
        f"YouTube publish completed: {_inline(playlist.title)}. "
        f"channel: `{channel}`; video: {youtube_link}{schedule}."
    )
    return post_ops_message(db, services, text=text)
