from __future__ import annotations

import json
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import PlaylistStatus
from app.models.playlist import Playlist

OPENCLAW_RUNTIME_STATE_FILE = "openclaw-runtime-state.json"
OPENCLAW_AUTO_LOOP_STATE_FILE = "openclaw-auto-loop-state.json"

MANUAL_ONLY_CHANNEL_TITLES = {"MusicSun"}
RETIRED_CHANNEL_TITLES = {"Signal Room Radio", "Signal Desk Radio", "Midnight Cue Radio", "AI썰전", "AnimeMix"}

BACKLOG_WORKFLOW_STATES = {
    "collecting",
    "pending_audio_render",
    "render_queued",
    "rendering",
    "audio_ready",
    "rendered",
    "video_required",
    "video_queued",
    "video_rendering",
    "metadata_review",
    "publish_ready",
    "publish_queued",
    "youtube_upload_failed",
    "youtube_upload_deferred_verification",
    "ready_for_youtube_auth",
}
FINISHABLE_WORKFLOW_STATES = {
    "metadata_review",
    "publish_ready",
    "publish_queued",
    "youtube_upload_failed",
}
DEFERRED_WORKFLOW_STATES = {
    "youtube_upload_deferred_verification",
    "ready_for_youtube_auth",
}
FAILED_REPAIR_WORKFLOW_STATES = {
    "render_failed",
    "video_build_failed",
}
NON_RETRYABLE_YOUTUBE_AUTH_ERROR_PATTERNS = (
    "stored youtube channel token expired or was revoked",
    "connect this channel again",
    "invalid_grant",
    "token has been expired or revoked",
    "token expired or was revoked",
)
OPENCLAW_MANUAL_BLOCKER_PATTERNS = (
    "hcaptcha",
    "captcha challenge",
    "manual verification",
    "stored youtube channel token expired",
    "token expired or was revoked",
    "connect this channel again",
)

_STATE_LOCK = threading.Lock()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None = None) -> str:
    return (value or _utcnow()).isoformat()


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _openclaw_manual_blocker(
    state: dict[str, Any],
    *,
    now: datetime,
    backoff_seconds: int,
) -> dict[str, Any] | None:
    last_finished_lock = dict(state.get("last_finished_lock") or {})
    if str(last_finished_lock.get("finish_status") or "").strip().lower() != "blocked":
        return None

    finished_at = _parse_datetime(last_finished_lock.get("finished_at"))
    if not finished_at:
        return None
    backoff = max(int(backoff_seconds or 0), 0)
    retry_after = finished_at + timedelta(seconds=backoff)

    blocker_text = " ".join(
        str(last_finished_lock.get(key) or "")
        for key in ("finish_message", "message", "operation", "channel_title")
    ).lower()
    if not any(pattern in blocker_text for pattern in OPENCLAW_MANUAL_BLOCKER_PATTERNS):
        return None

    return {
        "last_finished_lock": last_finished_lock,
        "manual_blocker_backoff_seconds": backoff,
        "manual_blocker_within_backoff": retry_after > now,
        "manual_blocker_retry_after": retry_after.isoformat(),
    }


def runtime_state_path(storage_root: Path) -> Path:
    return Path(storage_root) / OPENCLAW_RUNTIME_STATE_FILE


def _auto_loop_state_path(storage_root: Path) -> Path:
    return Path(storage_root) / OPENCLAW_AUTO_LOOP_STATE_FILE


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(f"{path.suffix}.tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    tmp_path.replace(path)


def read_runtime_state(storage_root: Path) -> dict[str, Any]:
    with _STATE_LOCK:
        return _read_json(runtime_state_path(storage_root))


def _lock_is_active(lock: dict[str, Any], *, now: datetime | None = None) -> bool:
    if not lock:
        return False
    expires_at = _parse_datetime(lock.get("expires_at"))
    return bool(expires_at and expires_at > (now or _utcnow()))


def get_openclaw_lock_status(storage_root: Path) -> dict[str, Any]:
    state = read_runtime_state(storage_root)
    lock = dict(state.get("lock") or {})
    active = _lock_is_active(lock)
    return {
        "active": active,
        "lock": lock if active else {},
        "state_path": str(runtime_state_path(storage_root)),
    }


def acquire_openclaw_lock(
    *,
    storage_root: Path,
    ttl_seconds: int,
    owner: str,
    run_id: str = "",
    operation: str = "",
    channel_title: str = "",
    release_id: str = "",
    message: str = "",
) -> dict[str, Any]:
    now = _utcnow()
    ttl = max(int(ttl_seconds or 0), 60)
    normalized_run_id = (run_id or "").strip() or str(uuid4())
    normalized_owner = (owner or "").strip() or "openclaw"
    with _STATE_LOCK:
        path = runtime_state_path(storage_root)
        state = _read_json(path)
        existing = dict(state.get("lock") or {})
        existing_active = _lock_is_active(existing, now=now)
        same_lock = (
            existing_active
            and existing.get("run_id") == normalized_run_id
            and existing.get("owner") == normalized_owner
        )
        if existing_active and not same_lock:
            return {
                "ok": False,
                "locked": True,
                "reason": "openclaw_lock_active",
                "lock": existing,
                "state_path": str(path),
            }

        lock = {
            "owner": normalized_owner,
            "run_id": normalized_run_id,
            "operation": operation,
            "channel_title": channel_title,
            "release_id": release_id,
            "message": message,
            "started_at": existing.get("started_at") if same_lock else _iso(now),
            "heartbeat_at": _iso(now),
            "expires_at": _iso(now + timedelta(seconds=ttl)),
        }
        state["lock"] = lock
        state["updated_at"] = _iso(now)
        _write_json(path, state)
    return {
        "ok": True,
        "locked": False,
        "lock": lock,
        "state_path": str(path),
    }


def heartbeat_openclaw_lock(
    *,
    storage_root: Path,
    ttl_seconds: int,
    owner: str,
    run_id: str,
    operation: str = "",
    channel_title: str = "",
    release_id: str = "",
    message: str = "",
) -> dict[str, Any]:
    now = _utcnow()
    ttl = max(int(ttl_seconds or 0), 60)
    normalized_owner = (owner or "").strip() or "openclaw"
    normalized_run_id = (run_id or "").strip()
    with _STATE_LOCK:
        path = runtime_state_path(storage_root)
        state = _read_json(path)
        lock = dict(state.get("lock") or {})
        if not _lock_is_active(lock, now=now):
            return {"ok": False, "reason": "openclaw_lock_missing_or_expired", "state_path": str(path)}
        if lock.get("owner") != normalized_owner or lock.get("run_id") != normalized_run_id:
            return {"ok": False, "reason": "openclaw_lock_mismatch", "lock": lock, "state_path": str(path)}

        if operation:
            lock["operation"] = operation
        if channel_title:
            lock["channel_title"] = channel_title
        if release_id:
            lock["release_id"] = release_id
        if message:
            lock["message"] = message
        lock["heartbeat_at"] = _iso(now)
        lock["expires_at"] = _iso(now + timedelta(seconds=ttl))
        state["lock"] = lock
        state["updated_at"] = _iso(now)
        _write_json(path, state)
    return {"ok": True, "lock": lock, "state_path": str(path)}


def finish_openclaw_lock(
    *,
    storage_root: Path,
    owner: str,
    run_id: str,
    status: str = "completed",
    message: str = "",
) -> dict[str, Any]:
    normalized_owner = (owner or "").strip() or "openclaw"
    normalized_run_id = (run_id or "").strip()
    now = _utcnow()
    with _STATE_LOCK:
        path = runtime_state_path(storage_root)
        state = _read_json(path)
        lock = dict(state.get("lock") or {})
        if lock and (lock.get("owner") != normalized_owner or lock.get("run_id") != normalized_run_id):
            return {"ok": False, "reason": "openclaw_lock_mismatch", "lock": lock, "state_path": str(path)}
        completed = {
            **lock,
            "finished_at": _iso(now),
            "finish_status": status,
            "finish_message": message,
        }
        if lock:
            state["last_finished_lock"] = completed
        state.pop("lock", None)
        state["updated_at"] = _iso(now)
        _write_json(path, state)
    return {"ok": True, "finished": completed, "state_path": str(path)}


def _playlist_channel_title(playlist: Playlist) -> str:
    meta = dict(playlist.metadata_json or {})
    return str(
        meta.get("target_youtube_channel_title")
        or meta.get("youtube_channel_title")
        or meta.get("youtube_channel_id")
        or ""
    ).strip()


def _playlist_uploaded_channel_title(playlist: Playlist) -> str:
    meta = dict(playlist.metadata_json or {})
    return str(
        meta.get("youtube_channel_title")
        or meta.get("target_youtube_channel_title")
        or meta.get("youtube_channel_id")
        or ""
    ).strip()


def _playlist_is_archived(meta: dict[str, Any]) -> bool:
    return bool(meta.get("archived_at") or meta.get("hidden"))


def _playlist_scheduled_public_at(playlist: Playlist, *, now: datetime) -> datetime | None:
    if not playlist.youtube_video_id:
        return None
    meta = dict(playlist.metadata_json or {})
    response = meta.get("youtube_response") if isinstance(meta.get("youtube_response"), dict) else {}
    status = response.get("status") if isinstance(response.get("status"), dict) else {}
    scheduled_values = [
        _parse_datetime(value)
        for value in (
            meta.get("youtube_scheduled_publish_at"),
            meta.get("youtube_publish_at"),
            status.get("publishAt"),
        )
    ]
    future_values = sorted(value for value in scheduled_values if value and value >= now)
    return future_values[0] if future_values else None


def _playlist_counts_as_backlog(playlist: Playlist) -> bool:
    meta = dict(playlist.metadata_json or {})
    workflow_state = str(meta.get("workflow_state") or "").strip()
    if _playlist_is_archived(meta):
        return False
    if str(meta.get("workspace_mode") or "playlist") != "playlist":
        return False
    if playlist.status == PlaylistStatus.uploaded or playlist.youtube_video_id or workflow_state == "uploaded":
        return False
    if workflow_state in FAILED_REPAIR_WORKFLOW_STATES:
        return False
    return workflow_state in BACKLOG_WORKFLOW_STATES or not workflow_state


def _youtube_channel_reconnected_after_failure(
    *,
    channel_status: dict[str, Any] | None,
    failed_at: datetime | None,
) -> bool:
    if not channel_status or not failed_at:
        return False
    if failed_at.tzinfo is None:
        failed_at = failed_at.replace(tzinfo=timezone.utc)
    reconnect_times = [
        _parse_datetime(channel_status.get("connected_at")),
        _parse_datetime(channel_status.get("refreshed_at")),
    ]
    latest_reconnect = max((value for value in reconnect_times if value), default=None)
    return bool(latest_reconnect and latest_reconnect > failed_at)


def _youtube_upload_failure_needs_auth(
    meta: dict[str, Any],
    *,
    channel_status: dict[str, Any] | None = None,
    failed_at: datetime | None = None,
) -> bool:
    if str(meta.get("workflow_state") or "").strip() != "youtube_upload_failed":
        return False
    error_text = str(meta.get("youtube_upload_error") or meta.get("note") or "").lower()
    if not any(pattern in error_text for pattern in NON_RETRYABLE_YOUTUBE_AUTH_ERROR_PATTERNS):
        return False
    return not _youtube_channel_reconnected_after_failure(
        channel_status=channel_status,
        failed_at=failed_at,
    )


def _playlist_is_finishable(
    workflow_state: str,
    meta: dict[str, Any],
    *,
    channel_status: dict[str, Any] | None = None,
    failed_at: datetime | None = None,
) -> bool:
    if workflow_state == "youtube_upload_failed" and _youtube_upload_failure_needs_auth(
        meta,
        channel_status=channel_status,
        failed_at=failed_at,
    ):
        return False
    return workflow_state in FINISHABLE_WORKFLOW_STATES


def _playlist_is_deferred(
    workflow_state: str,
    meta: dict[str, Any],
    *,
    channel_status: dict[str, Any] | None = None,
    failed_at: datetime | None = None,
) -> bool:
    return workflow_state in DEFERRED_WORKFLOW_STATES or _youtube_upload_failure_needs_auth(
        meta,
        channel_status=channel_status,
        failed_at=failed_at,
    )


def _active_youtube_channel_statuses(services) -> dict[str, dict[str, Any]]:
    status = services.youtube.get_status()
    if not status.get("ready"):
        return {}
    channels = {}
    for channel in status.get("channels") or []:
        title = str(channel.get("title") or "").strip()
        if not title or title in MANUAL_ONLY_CHANNEL_TITLES or title in RETIRED_CHANNEL_TITLES:
            continue
        channels[title] = dict(channel)
    return channels


def _active_youtube_channel_titles(services) -> list[str]:
    return sorted(_active_youtube_channel_statuses(services), key=str.lower)


def build_openclaw_backlog_summary(db: Session, services) -> dict[str, Any]:
    channel_statuses = _active_youtube_channel_statuses(services)
    channel_titles = sorted(channel_statuses, key=str.lower)
    target = max(1, int(services.settings.openclaw_backlog_target_per_channel or 1))
    maximum = max(target, int(services.settings.openclaw_backlog_max_per_channel or target))
    lock_status = get_openclaw_lock_status(services.settings.storage_root)
    active_lock = dict(lock_status.get("lock") or {}) if lock_status.get("active") else {}
    lock_release_id = str(active_lock.get("release_id") or "").strip()
    lock_channel_title = str(active_lock.get("channel_title") or "").strip()
    channels = {
        title: {
            "count": 0,
            "finishable": 0,
            "deferred": 0,
            "auth_blocked": 0,
            "youtube_uploaded_count": 0,
            "youtube_scheduled_public_count": 0,
            "next_youtube_scheduled_public_at": None,
            "releases": [],
        }
        for title in channel_titles
    }
    unknown_channel_releases: list[dict[str, Any]] = []

    playlists = db.scalars(select(Playlist).order_by(Playlist.updated_at.desc())).all()
    now = _utcnow()
    for playlist in playlists:
        uploaded_channel_title = _playlist_uploaded_channel_title(playlist)
        if uploaded_channel_title in channels and playlist.youtube_video_id and not _playlist_is_archived(
            dict(playlist.metadata_json or {})
        ):
            channels[uploaded_channel_title]["youtube_uploaded_count"] += 1
            scheduled_at = _playlist_scheduled_public_at(playlist, now=now)
            if scheduled_at:
                channels[uploaded_channel_title]["youtube_scheduled_public_count"] += 1
                scheduled_at_iso = scheduled_at.isoformat()
                existing_scheduled_at = channels[uploaded_channel_title]["next_youtube_scheduled_public_at"]
                if not existing_scheduled_at or scheduled_at_iso < existing_scheduled_at:
                    channels[uploaded_channel_title]["next_youtube_scheduled_public_at"] = scheduled_at_iso
        if not _playlist_counts_as_backlog(playlist):
            continue
        meta = dict(playlist.metadata_json or {})
        channel_title = _playlist_channel_title(playlist)
        if not channel_title and playlist.id == lock_release_id:
            channel_title = lock_channel_title
        workflow_state = str(meta.get("workflow_state") or "collecting").strip() or "collecting"
        release_payload = {
            "id": playlist.id,
            "title": playlist.title,
            "workflow_state": workflow_state,
            "updated_at": playlist.updated_at.isoformat() if playlist.updated_at else None,
        }
        if channel_title not in channels:
            unknown_channel_releases.append({**release_payload, "channel_title": channel_title or None})
            continue
        channel_status = channel_statuses.get(channel_title)
        failure_at = _parse_datetime(meta.get("youtube_upload_failed_at")) or playlist.updated_at
        auth_blocked = _youtube_upload_failure_needs_auth(
            meta,
            channel_status=channel_status,
            failed_at=failure_at,
        )
        channels[channel_title]["count"] += 1
        channels[channel_title]["releases"].append(release_payload)
        if _playlist_is_finishable(
            workflow_state,
            meta,
            channel_status=channel_status,
            failed_at=failure_at,
        ):
            channels[channel_title]["finishable"] += 1
        if _playlist_is_deferred(
            workflow_state,
            meta,
            channel_status=channel_status,
            failed_at=failure_at,
        ):
            channels[channel_title]["deferred"] += 1
        if auth_blocked:
            channels[channel_title]["auth_blocked"] += 1

    return {
        "channels": channels,
        "unknown_channel_releases": unknown_channel_releases,
        "active_channel_titles": channel_titles,
        "target_per_channel": target,
        "max_per_channel": maximum,
    }


def _auto_loop_allows_request(
    *,
    storage_root: Path,
    max_uploads: int,
) -> dict[str, Any]:
    state = _read_json(_auto_loop_state_path(storage_root))
    if state.get("stopped"):
        return {
            "ok": False,
            "reason": "auto_loop_stopped",
            "stop_requested_at": state.get("stop_requested_at"),
            "stop_requested_by": state.get("stop_requested_by"),
        }
    normalized_max = max(0, int(max_uploads or 0))
    counted = [item for item in state.get("counted_uploads") or [] if isinstance(item, dict)]
    if normalized_max > 0 and len(counted) >= normalized_max:
        return {
            "ok": False,
            "reason": "max_uploads_reached",
            "completed_uploads": len(counted),
            "max_uploads": normalized_max,
        }
    return {
        "ok": True,
        "reason": "allowed",
        "completed_uploads": len(counted),
        "max_uploads": normalized_max,
    }


def evaluate_openclaw_backlog_scheduler(db: Session, services) -> dict[str, Any]:
    settings = services.settings
    if not settings.openclaw_backlog_scheduler_enabled:
        return {"should_request": False, "reason": "scheduler_disabled"}
    if not settings.openclaw_slack_channel_id.strip():
        return {"should_request": False, "reason": "openclaw_slack_channel_id_missing"}

    loop_gate = _auto_loop_allows_request(
        storage_root=settings.storage_root,
        max_uploads=settings.openclaw_auto_request_next_max_uploads,
    )
    if not loop_gate.get("ok"):
        return {"should_request": False, "reason": loop_gate.get("reason"), "loop_gate": loop_gate}

    lock_status = get_openclaw_lock_status(settings.storage_root)
    if lock_status.get("active"):
        return {"should_request": False, "reason": "openclaw_lock_active", "lock": lock_status.get("lock")}

    now = _utcnow()
    state = read_runtime_state(settings.storage_root)
    scheduler_state = dict(state.get("scheduler") or {})
    last_request_at = _parse_datetime(scheduler_state.get("last_request_at"))
    cooldown_seconds = max(int(settings.openclaw_backlog_request_cooldown_seconds or 0), 0)
    if last_request_at and cooldown_seconds and last_request_at + timedelta(seconds=cooldown_seconds) > now:
        return {
            "should_request": False,
            "reason": "backlog_request_cooldown",
            "last_request_at": last_request_at.isoformat(),
            "cooldown_seconds": cooldown_seconds,
        }

    summary = build_openclaw_backlog_summary(db, services)
    channel_data = summary["channels"]
    if not channel_data:
        return {"should_request": False, "reason": "no_active_youtube_channels", "summary": summary}

    target = max(1, int(settings.openclaw_backlog_target_per_channel or 1))
    maximum = max(target, int(settings.openclaw_backlog_max_per_channel or target))
    finishable_channels = [
        title for title, payload in channel_data.items() if int(payload.get("finishable") or 0) > 0
    ]
    raw_underfilled_channels = [
        title for title, payload in channel_data.items() if int(payload.get("count") or 0) < target
    ]
    auth_blocked_channels = [
        title for title, payload in channel_data.items() if int(payload.get("auth_blocked") or 0) > 0
    ]
    underfilled_channels = [
        title
        for title in raw_underfilled_channels
        if int(channel_data.get(title, {}).get("auth_blocked") or 0) <= 0
    ]
    overfull_channels = [
        title for title, payload in channel_data.items() if int(payload.get("count") or 0) >= maximum
    ]
    manual_blocker = _openclaw_manual_blocker(
        state,
        now=now,
        backoff_seconds=settings.openclaw_manual_blocker_backoff_seconds,
    )
    if manual_blocker:
        summary = {**summary, "manual_blocker": manual_blocker}

    if finishable_channels:
        return {
            "should_request": True,
            "reason": "finishable_releases",
            "target_per_channel": target,
            "max_per_channel": maximum,
            "finishable_channels": finishable_channels,
            "underfilled_channels": underfilled_channels,
            "auth_blocked_channels": auth_blocked_channels,
            "overfull_channels": overfull_channels,
            "summary": summary,
        }
    if manual_blocker and manual_blocker.get("manual_blocker_within_backoff"):
        return {
            "should_request": False,
            "reason": "recent_openclaw_manual_blocker",
            "target_per_channel": target,
            "max_per_channel": maximum,
            "finishable_channels": finishable_channels,
            "underfilled_channels": underfilled_channels,
            "auth_blocked_channels": auth_blocked_channels,
            "overfull_channels": overfull_channels,
            "summary": summary,
            **manual_blocker,
        }
    if manual_blocker and underfilled_channels:
        return {
            "should_request": True,
            "reason": "resume_openclaw_manual_blocker",
            "target_per_channel": target,
            "max_per_channel": maximum,
            "finishable_channels": finishable_channels,
            "underfilled_channels": underfilled_channels,
            "auth_blocked_channels": auth_blocked_channels,
            "overfull_channels": overfull_channels,
            "summary": summary,
            **manual_blocker,
        }
    if underfilled_channels:
        return {
            "should_request": True,
            "reason": "underfilled_backlog",
            "target_per_channel": target,
            "max_per_channel": maximum,
            "finishable_channels": finishable_channels,
            "underfilled_channels": underfilled_channels,
            "auth_blocked_channels": auth_blocked_channels,
            "overfull_channels": overfull_channels,
            "summary": summary,
        }
    if raw_underfilled_channels and auth_blocked_channels:
        return {
            "should_request": False,
            "reason": "underfilled_channels_need_youtube_reconnect",
            "target_per_channel": target,
            "max_per_channel": maximum,
            "finishable_channels": finishable_channels,
            "underfilled_channels": underfilled_channels,
            "auth_blocked_channels": auth_blocked_channels,
            "overfull_channels": overfull_channels,
            "summary": summary,
        }
    return {
        "should_request": False,
        "reason": "backlog_satisfied",
        "target_per_channel": target,
        "max_per_channel": maximum,
        "auth_blocked_channels": auth_blocked_channels,
        "summary": summary,
    }


def record_openclaw_backlog_scheduler_request(
    *,
    storage_root: Path,
    result: dict[str, Any],
) -> dict[str, Any]:
    now = _utcnow()
    with _STATE_LOCK:
        path = runtime_state_path(storage_root)
        state = _read_json(path)
        scheduler_state = dict(state.get("scheduler") or {})
        scheduler_state.update(
            {
                "last_request_at": _iso(now),
                "last_reason": result.get("reason"),
                "last_result": result,
            }
        )
        state["scheduler"] = scheduler_state
        state["updated_at"] = _iso(now)
        _write_json(path, state)
    return scheduler_state
