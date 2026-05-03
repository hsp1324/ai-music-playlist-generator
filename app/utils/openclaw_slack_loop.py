from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.playlist import Playlist


def _with_trigger_prefix(text: str, trigger_prefix: str | None) -> str:
    stripped_text = text.strip()
    prefix = (trigger_prefix or "").strip()
    if not prefix or stripped_text.startswith(prefix):
        return stripped_text
    return f"{prefix}\n{stripped_text}"


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
            "- /opt/ai-music-playlist-generator 리포에서 최신 main을 pull 해줘.",
            "- 먼저 docs/openclaw-next-release-planner.md를 읽고 그대로 따라줘.",
            "- 그 다음 docs/openclaw-skills.md, docs/openclaw-channel-profiles/README.md, docs/openclaw-youtube-metadata.md를 따라줘.",
            "- 현재 활성 채널을 순서대로 번갈아 운영하되, 기존에 만들지 않았던 새 컨셉을 선택해줘.",
            "- 선택한 채널/컨셉으로 audio 생성, cover, thumbnail, 8s loop video, metadata, private publish까지 완료해줘.",
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
