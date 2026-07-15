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


def _mrkdwn(value: Any) -> str:
    return (
        str(value or "")
        .strip()
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        or "Untitled"
    )


def _short(value: Any, limit: int = 240) -> str:
    text = " ".join(str(value or "").split()).strip()
    if len(text) <= limit:
        return text
    return f"{text[: limit - 1].rstrip()}..."


def _worker_label(worker: dict[str, Any] | None) -> str:
    payload = worker or {}
    nickname = str(payload.get("nickname") or "").strip()
    worker_id = str(payload.get("worker_id") or "").strip()
    hostname = str(payload.get("hostname") or "").strip()
    return nickname or worker_id or hostname or "unknown-worker"


def _release_title_label(value: Any) -> str:
    text = _short(value, 260)
    if text.lower().startswith("[playlist]"):
        text = text[len("[playlist]") :].strip()
    if "|" in text:
        text = text.split("|", 1)[0].strip()
    return text or "Untitled"


def _artwork_title(value: Any) -> str:
    return f"{_short(_release_title_label(value), 80)} 아트워크"


def _local_asset_path(services, path_value: Any) -> str:
    raw = str(path_value or "").strip()
    if not raw or raw.startswith(("http://", "https://")):
        return ""

    storage_root = Path(services.settings.storage_root).resolve()
    candidate = Path(raw)
    path: Path | None = None
    try:
        if candidate.is_absolute():
            resolved = candidate.resolve()
            resolved.relative_to(storage_root)
            path = resolved
        elif candidate.parts and candidate.parts[0] == "storage":
            path = storage_root / Path(*candidate.parts[1:])
        elif candidate.parts and candidate.parts[0] in {"playlists", "tracks", "covers", "tmp", "browser"}:
            path = storage_root / candidate
    except (OSError, ValueError):
        path = None
    if path is None or not path.exists() or not path.is_file():
        return ""
    return str(path)


def _playlist_image_path(services, playlist: Playlist) -> str:
    meta = dict(playlist.metadata_json or {})
    for value in (meta.get("youtube_thumbnail_path"), meta.get("cover_image_path")):
        path = _local_asset_path(services, value)
        if path:
            return path
    return ""


def _ops_text(*, title: str, release_title: str, fields: list[tuple[str, Any]]) -> str:
    lines = [f"*{title}*", f"제목: {_release_title_label(release_title)}"]
    details = [f"{label}: {_short(value, 180)}" for label, value in fields if str(value or "").strip()]
    if details:
        lines.append(" | ".join(details))
    return "\n".join(lines)


def _ops_blocks(
    *,
    title: str,
    release_title: str,
    fields: list[tuple[str, Any]],
) -> list[dict[str, Any]]:
    section: dict[str, Any] = {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"*{_mrkdwn(title)}*\n제목: {_mrkdwn(_release_title_label(release_title))}",
        },
    }

    blocks = [section]
    field_blocks = [
        {
            "type": "mrkdwn",
            "text": f"*{_mrkdwn(label)}*\n{_mrkdwn(_short(value, 180))}",
        }
        for label, value in fields
        if str(value or "").strip()
    ]
    if field_blocks:
        blocks.append({"type": "section", "fields": field_blocks[:10]})
    return blocks


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
    image_path: str = "",
    image_title: str = "",
) -> dict[str, Any]:
    try:
        installation = services.slack_installations.get_active_installation(db)
        token = installation.bot_token if installation else services.settings.slack_bot_token
        target_channel = services.settings.slack_ops_channel_id or services.settings.slack_review_channel_id
        if image_path and token and target_channel:
            upload_result = _run_async(
                lambda: services.slack.upload_local_file(
                    file_path=image_path,
                    title=image_title or "릴리스 아트워크",
                    token=token,
                    channel=target_channel,
                    initial_comment=text,
                )
            )
            if bool(getattr(upload_result, "ok", False)):
                return {
                    "ok": True,
                    "channel": getattr(upload_result, "channel", None),
                    "ts": getattr(upload_result, "ts", None),
                    "file_id": getattr(upload_result, "file_id", None),
                    "raw": getattr(upload_result, "raw", None),
                    "mode": "file_upload",
                }
        result = _run_async(lambda: services.slack.post_ops_message(token=token, text=text, blocks=blocks))
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
    title = "비디오 렌더 대기"
    fields = [
        ("모드", mode),
        ("비주얼라이저", visualizer),
        ("요청자", actor),
    ]
    text = _ops_text(title=title, release_title=playlist.title, fields=fields)
    blocks = _ops_blocks(
        title=title,
        release_title=playlist.title,
        fields=fields,
    )
    result = post_ops_message(
        db,
        services,
        text=text,
        blocks=blocks,
        image_path=_playlist_image_path(services, playlist),
        image_title=_artwork_title(playlist.title),
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
    worker_label = _worker_label(worker)
    title = "렌더 작업자 점유"
    fields = [
        ("작업자", worker_label),
        ("큐 대기", queue_elapsed),
    ]
    text = _ops_text(title=title, release_title=playlist.title, fields=fields)
    blocks = _ops_blocks(
        title=title,
        release_title=playlist.title,
        fields=fields,
    )
    return post_ops_message(
        db,
        services,
        text=text,
        blocks=blocks,
        image_path=_playlist_image_path(services, playlist),
        image_title=_artwork_title(playlist.title),
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
    worker_label = _worker_label(worker)
    title = "렌더 작업자 완료"
    fields = [
        ("작업자", worker_label),
        ("경과", elapsed),
        ("결과", "MP4가 메인 VM에 업로드됨"),
    ]
    text = _ops_text(title=title, release_title=playlist.title, fields=fields)
    blocks = _ops_blocks(
        title=title,
        release_title=playlist.title,
        fields=fields,
    )
    return post_ops_message(
        db,
        services,
        text=text,
        blocks=blocks,
        image_path=_playlist_image_path(services, playlist),
        image_title=_artwork_title(playlist.title),
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
    worker_label = _worker_label(worker)
    title = "렌더 작업자 시간 초과, 작업 재큐"
    fields = [
        ("작업자", worker_label),
        ("타임아웃", _format_duration(timeout_seconds)),
        ("하트비트 없음", elapsed),
    ]
    text = _ops_text(title=title, release_title=playlist_title, fields=fields)
    blocks = _ops_blocks(
        title=title,
        release_title=playlist_title,
        fields=fields,
    )
    return post_ops_message(
        db,
        services,
        text=text,
        blocks=blocks,
        image_path=_local_asset_path(services, cover_image_path),
        image_title=_artwork_title(playlist_title),
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
    title = "YouTube 게시 완료"
    fields = [
        ("채널", channel),
        ("영상", youtube_link),
    ]
    if scheduled_publish_at:
        fields.append(("예약", scheduled_publish_at))
    text = _ops_text(title=title, release_title=playlist.title, fields=fields)
    blocks = _ops_blocks(
        title=title,
        release_title=playlist.title,
        fields=fields,
    )
    return post_ops_message(
        db,
        services,
        text=text,
        blocks=blocks,
        image_path=_playlist_image_path(services, playlist),
        image_title=_artwork_title(playlist.title),
    )
