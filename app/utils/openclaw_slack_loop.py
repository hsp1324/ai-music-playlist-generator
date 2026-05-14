from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.models.playlist import Playlist

OPENCLAW_AUTO_LOOP_STATE_FILE = "openclaw-auto-loop-state.json"

_AUTO_LOOP_STOP_COMMANDS = {
    "openclaw_stop",
    "openclaw loop stop",
    "openclaw_loop_stop",
    "stop openclaw loop",
    "stop_openclaw_loop",
    "auto_loop_stop",
    "automation_stop",
}
_AUTO_LOOP_START_COMMANDS = {
    "openclaw_start",
    "openclaw loop start",
    "openclaw_loop_start",
    "start openclaw loop",
    "start_openclaw_loop",
    "auto_loop_start",
    "automation_start",
}
_AUTO_LOOP_SUBJECT_RE = re.compile(r"(openclaw|open\s*claw|오픈\s*클로|오픈클로|자동화|무한\s*반복|auto\s*loop)", re.I)
_AUTO_LOOP_STOP_RE = re.compile(r"(멈춰|멈추|중지|정지|그만|꺼줘|종료|stop|pause|halt)", re.I)
_AUTO_LOOP_START_RE = re.compile(r"(시작|재개|다시\s*돌|다시\s*시작|켜줘|resume|start|continue)", re.I)


def _with_trigger_prefix(text: str, trigger_prefix: str | None) -> str:
    stripped_text = text.strip()
    prefix = (trigger_prefix or "").strip()
    if not prefix or stripped_text.startswith(prefix):
        return stripped_text
    return f"{prefix}\n{stripped_text}"


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _auto_loop_session_key(
    *,
    channel_id: str,
    trigger_prefix: str,
    max_uploads: int,
) -> str:
    return f"channel={channel_id.strip()}|trigger={trigger_prefix.strip()}|max_uploads={max_uploads}"


def _read_auto_loop_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_auto_loop_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(f"{path.suffix}.tmp")
    tmp_path.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    tmp_path.replace(path)


def _auto_loop_state_path(storage_root: Path) -> Path:
    return Path(storage_root) / OPENCLAW_AUTO_LOOP_STATE_FILE


def parse_auto_loop_control_message(text: str) -> str | None:
    """Return 'stop'/'start' when a human Slack message controls the OpenClaw loop."""

    normalized = re.sub(r"[\s:：!！.,，]+", " ", str(text or "").strip()).lower()
    compact = normalized.replace(" ", "_")
    candidates = {normalized, compact}
    if candidates & _AUTO_LOOP_STOP_COMMANDS:
        return "stop"
    if candidates & _AUTO_LOOP_START_COMMANDS:
        return "start"
    if _AUTO_LOOP_SUBJECT_RE.search(normalized) and _AUTO_LOOP_STOP_RE.search(normalized):
        return "stop"
    if _AUTO_LOOP_SUBJECT_RE.search(normalized) and _AUTO_LOOP_START_RE.search(normalized):
        return "start"
    return None


def set_auto_loop_stopped(
    *,
    storage_root: Path,
    stopped: bool,
    reason: str,
    user_id: str = "",
    channel_id: str = "",
    message_ts: str = "",
) -> dict[str, Any]:
    state_path = _auto_loop_state_path(storage_root)
    state = _read_auto_loop_state(state_path)
    now = _utcnow_iso()
    if stopped:
        state.update(
            {
                "stopped": True,
                "stop_reason": reason,
                "stop_requested_at": now,
                "stop_requested_by": user_id,
                "stop_channel_id": channel_id,
                "stop_message_ts": message_ts,
                "updated_at": now,
            }
        )
    else:
        state["stopped"] = False
        state["resume_reason"] = reason
        state["resume_requested_at"] = now
        state["resume_requested_by"] = user_id
        state["resume_channel_id"] = channel_id
        state["resume_message_ts"] = message_ts
        state.pop("stop_reason", None)
        state.pop("stop_requested_at", None)
        state.pop("stop_requested_by", None)
        state.pop("stop_channel_id", None)
        state.pop("stop_message_ts", None)
        state["updated_at"] = now
    _write_auto_loop_state(state_path, state)
    return {
        "ok": True,
        "action": "stop" if stopped else "start",
        "stopped": stopped,
        "state_path": str(state_path),
        "updated_at": now,
    }


def handle_auto_loop_control_message(
    *,
    storage_root: Path,
    text: str,
    user_id: str = "",
    channel_id: str = "",
    message_ts: str = "",
) -> dict[str, Any] | None:
    action = parse_auto_loop_control_message(text)
    if action == "stop":
        return set_auto_loop_stopped(
            storage_root=storage_root,
            stopped=True,
            reason="slack_control_message",
            user_id=user_id,
            channel_id=channel_id,
            message_ts=message_ts,
        )
    if action == "start":
        return set_auto_loop_stopped(
            storage_root=storage_root,
            stopped=False,
            reason="slack_control_message",
            user_id=user_id,
            channel_id=channel_id,
            message_ts=message_ts,
        )
    return None


def get_auto_loop_control_state(*, storage_root: Path) -> dict[str, Any]:
    """Return the persisted human stop/resume state for OpenClaw automation."""

    state = _read_auto_loop_state(_auto_loop_state_path(storage_root))
    return {
        "stopped": bool(state.get("stopped")),
        "stop_reason": state.get("stop_reason"),
        "stop_requested_at": state.get("stop_requested_at"),
        "stop_requested_by": state.get("stop_requested_by"),
        "resume_requested_at": state.get("resume_requested_at"),
        "state_path": str(_auto_loop_state_path(storage_root)),
    }


def record_auto_loop_upload(
    *,
    storage_root: Path,
    max_uploads: int,
    channel_id: str,
    trigger_prefix: str,
    playlist_id: str,
    youtube_video_id: str,
) -> dict[str, Any]:
    """Record a successful upload and decide whether the loop may request another release."""

    normalized_max_uploads = max(0, int(max_uploads or 0))
    state_path = _auto_loop_state_path(storage_root)
    existing_state = _read_auto_loop_state(state_path)
    if existing_state.get("stopped"):
        return {
            "enabled": True,
            "limited": normalized_max_uploads > 0,
            "max_uploads": normalized_max_uploads,
            "completed_uploads": existing_state.get("completed_uploads"),
            "remaining_uploads": existing_state.get("remaining_uploads"),
            "should_request_next": False,
            "reason": "auto_loop_stopped",
            "stop_requested_at": existing_state.get("stop_requested_at"),
            "stop_requested_by": existing_state.get("stop_requested_by"),
            "state_path": str(state_path),
        }

    session_key = _auto_loop_session_key(
        channel_id=channel_id,
        trigger_prefix=trigger_prefix,
        max_uploads=normalized_max_uploads,
    )
    state = existing_state
    if state.get("session_key") != session_key:
        state = {
            "session_key": session_key,
            "max_uploads": normalized_max_uploads,
            "channel_id": channel_id,
            "trigger_prefix": trigger_prefix,
            "started_at": _utcnow_iso(),
            "counted_uploads": [],
        }

    counted_uploads = state.get("counted_uploads")
    if not isinstance(counted_uploads, list):
        counted_uploads = []
    upload_key = youtube_video_id.strip() or playlist_id
    if upload_key and not any(item.get("upload_key") == upload_key for item in counted_uploads if isinstance(item, dict)):
        counted_uploads.append(
            {
                "upload_key": upload_key,
                "playlist_id": playlist_id,
                "youtube_video_id": youtube_video_id,
                "counted_at": _utcnow_iso(),
            }
        )

    state["counted_uploads"] = counted_uploads
    state["completed_uploads"] = len(counted_uploads)
    state["remaining_uploads"] = (
        max(normalized_max_uploads - len(counted_uploads), 0) if normalized_max_uploads > 0 else None
    )
    state["updated_at"] = _utcnow_iso()
    _write_auto_loop_state(state_path, state)

    should_request_next = normalized_max_uploads <= 0 or len(counted_uploads) < normalized_max_uploads
    return {
        "enabled": True,
        "limited": normalized_max_uploads > 0,
        "max_uploads": normalized_max_uploads,
        "completed_uploads": len(counted_uploads),
        "remaining_uploads": max(normalized_max_uploads - len(counted_uploads), 0)
        if normalized_max_uploads > 0
        else None,
        "should_request_next": should_request_next,
        "reason": (
            "unlimited"
            if normalized_max_uploads <= 0
            else "under_limit"
            if should_request_next
            else "max_uploads_reached"
        ),
        "state_path": str(state_path),
    }


def build_next_playlist_request_message(
    playlist: Playlist,
    *,
    prompt_override: str | None = None,
    trigger_prefix: str | None = "OPENCLAW_RUN:",
) -> str:
    meta = dict(playlist.metadata_json or {})
    channel_title = str(meta.get("youtube_channel_title") or "").strip() or str(meta.get("youtube_channel_id") or "").strip()
    youtube_link = f"https://youtu.be/{playlist.youtube_video_id}" if playlist.youtube_video_id else "not uploaded yet"
    if prompt_override and prompt_override.strip():
        return _with_trigger_prefix(prompt_override, trigger_prefix)

    previous_context = [
        "OpenClaw Next Release Publisher Skill을 실행해줘.",
        "최신 main을 pull한 뒤 docs/openclaw-backlog-queue.md를 먼저 읽고 그대로 진행해줘.",
        "필요하면 docs/openclaw-next-release-planner.md, docs/openclaw-skills.md, docs/openclaw-youtube-metadata.md도 참고해줘.",
        "",
        "이전 자동화 완료 정보:",
        f"- release: {playlist.title}",
        f"- youtube: {youtube_link}",
    ]
    if channel_title:
        previous_context.append(f"- channel: {channel_title}")

    previous_context.extend(["", "완료/중단 시 release id, YouTube video id, blocker만 간단히 보고해줘."])
    return _with_trigger_prefix("\n".join(previous_context), trigger_prefix)


def build_backlog_queue_request_message(
    *,
    reason: str,
    backlog_summary: dict[str, Any] | None = None,
    trigger_prefix: str | None = "OPENCLAW_RUN:",
    prompt_override: str | None = None,
) -> str:
    if prompt_override and prompt_override.strip():
        return _with_trigger_prefix(prompt_override, trigger_prefix)

    summary = backlog_summary or {}
    channel_payload = summary.get("channels") if isinstance(summary, dict) else {}
    lines = [
        "OpenClaw Next Release Publisher Skill을 실행해줘.",
        f"scheduler_reason: {reason}",
        "",
        "최신 main을 pull한 뒤 docs/openclaw-backlog-queue.md를 먼저 읽고 그대로 진행해줘.",
        "필요하면 docs/openclaw-next-release-planner.md, docs/openclaw-skills.md, docs/openclaw-youtube-metadata.md도 참고해줘.",
        "완료/중단 시 release id, YouTube video id, blocker만 간단히 보고해줘.",
    ]
    if isinstance(channel_payload, dict) and channel_payload:
        lines.extend(["", "현재 웹앱 backlog snapshot:"])
        for title, payload in sorted(channel_payload.items()):
            lines.append(
                f"- {title}: {payload.get('count', 0)} unfinished"
                f", {payload.get('finishable', 0)} finishable"
                f", {payload.get('deferred', 0)} deferred"
            )
    return _with_trigger_prefix("\n".join(lines), trigger_prefix)


async def post_backlog_queue_request(
    db: Session,
    services,
    *,
    reason: str,
    backlog_summary: dict[str, Any] | None = None,
    prompt_override: str | None = None,
) -> dict[str, Any]:
    channel_id = services.settings.openclaw_slack_channel_id.strip()
    if not channel_id:
        return {"ok": False, "error": "openclaw_slack_channel_id_missing"}

    installation = services.slack_installations.get_active_installation(db)
    token = installation.bot_token if installation else services.settings.slack_bot_token
    if not token:
        return {"ok": False, "error": "slack_bot_token_missing", "channel": channel_id}

    text = build_backlog_queue_request_message(
        reason=reason,
        backlog_summary=backlog_summary,
        prompt_override=prompt_override or services.settings.openclaw_next_playlist_prompt,
        trigger_prefix=services.settings.openclaw_slack_trigger_prefix,
    )
    result = await services.slack.post_plain_message(
        text=text,
        token=token,
        channel=channel_id,
    )
    return {
        "ok": result.ok,
        "channel": result.channel or channel_id,
        "ts": result.ts,
        "text": text,
        "raw": result.raw,
    }


async def post_next_playlist_request(
    db: Session,
    services,
    playlist: Playlist,
    *,
    prompt_override: str | None = None,
) -> dict[str, Any]:
    channel_id = services.settings.openclaw_slack_channel_id.strip()
    if not channel_id:
        return {"ok": False, "error": "openclaw_slack_channel_id_missing"}

    installation = services.slack_installations.get_active_installation(db)
    token = installation.bot_token if installation else services.settings.slack_bot_token
    if not token:
        return {"ok": False, "error": "slack_bot_token_missing", "channel": channel_id}

    text = build_next_playlist_request_message(
        playlist,
        prompt_override=prompt_override or services.settings.openclaw_next_playlist_prompt,
        trigger_prefix=services.settings.openclaw_slack_trigger_prefix,
    )
    result = await services.slack.post_plain_message(
        text=text,
        token=token,
        channel=channel_id,
    )
    return {
        "ok": result.ok,
        "channel": result.channel or channel_id,
        "ts": result.ts,
        "text": text,
        "raw": result.raw,
    }
