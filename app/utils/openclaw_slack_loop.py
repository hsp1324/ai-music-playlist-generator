from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.models.playlist import Playlist

OPENCLAW_AUTO_LOOP_STATE_FILE = "openclaw-auto-loop-state.json"


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
    if normalized_max_uploads <= 0:
        return {
            "enabled": True,
            "limited": False,
            "max_uploads": 0,
            "completed_uploads": None,
            "remaining_uploads": None,
            "should_request_next": True,
            "reason": "unlimited",
        }

    state_path = Path(storage_root) / OPENCLAW_AUTO_LOOP_STATE_FILE
    session_key = _auto_loop_session_key(
        channel_id=channel_id,
        trigger_prefix=trigger_prefix,
        max_uploads=normalized_max_uploads,
    )
    state = _read_auto_loop_state(state_path)
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
    state["remaining_uploads"] = max(normalized_max_uploads - len(counted_uploads), 0)
    state["updated_at"] = _utcnow_iso()
    _write_auto_loop_state(state_path, state)

    should_request_next = len(counted_uploads) < normalized_max_uploads
    return {
        "enabled": True,
        "limited": True,
        "max_uploads": normalized_max_uploads,
        "completed_uploads": len(counted_uploads),
        "remaining_uploads": max(normalized_max_uploads - len(counted_uploads), 0),
        "should_request_next": should_request_next,
        "reason": "under_limit" if should_request_next else "max_uploads_reached",
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
        "OpenClaw Next Release Planner Skill을 실행해줘.",
        "목표: 다음에 만들 1시간 Playlist Release의 채널과 컨셉을 결정하고, private YouTube publish까지 진행해줘.",
        "",
        "이전 publish 완료 정보:",
        f"- release: {playlist.title}",
        f"- youtube: {youtube_link}",
    ]
    if channel_title:
        previous_context.append(f"- channel: {channel_title}")

    previous_context.extend(
        [
            "",
            "작업 기준:",
            "- OpenClaw 런타임의 repo는 보통 ~/repos/ai-music-playlist-generator 입니다. 없으면 ~/repos/ai리포 또는 현재 checkout을 사용해줘.",
            "- 최신 main을 pull 해줘.",
            "- AIMP_LOCAL_API_BASE는 배포된 Oracle VM 앱 API 또는 그 API로 연결되는 터널이어야 합니다. OpenClaw 로컬 dev API를 사용하지 마세요.",
            "- /youtube/status가 configured=false, authenticated=false, ready=false, channels=[]이면 잘못된 API를 보고 있는 것이므로 audio/Suno/Dreamina/publish를 시작하지 말고 중단 사유를 알려줘.",
            "- 먼저 docs/openclaw-next-release-planner.md를 읽고 그대로 따라줘.",
            "- 그 다음 docs/openclaw-skills.md, docs/openclaw-channel-concepts/README.md, docs/openclaw-channel-profiles/README.md, docs/openclaw-youtube-metadata.md를 따라줘.",
            "- 현재 활성 채널을 순서대로 번갈아 운영하되, 기존에 만들지 않았던 새 컨셉을 선택해줘.",
            "- 선택한 채널/컨셉으로 audio 생성, cover, thumbnail, 10s loop video, metadata, private publish까지 완료해줘.",
            "- 완료하거나 막히면 이 Slack 채널에 release id, YouTube video id, 실패 원인을 알려줘.",
        ]
    )
    return _with_trigger_prefix("\n".join(previous_context), trigger_prefix)


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
