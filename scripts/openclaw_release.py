#!/usr/bin/env python3
"""OpenClaw-friendly helper for uploading generated release assets.

This script is intended to run on the VM next to the FastAPI app. It uses the
local API by default, bypassing public Google OAuth protection.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import httpx

from app.utils.track_titles import clean_track_display_title, display_track_titles, upload_track_title
from app.utils.timeline import timeline_from_track_dicts


DEFAULT_API_BASE = "http://127.0.0.1:8000/api"
MAX_AUDIO_UPLOAD_ATTEMPTS = 3
DEFAULT_MIN_PLAYLIST_TRACK_SECONDS = 0
DEFAULT_MAX_PLAYLIST_TRACK_SECONDS = 260
MIN_NORMAL_LOOP_VIDEO_SECONDS = 1.0
LOOP_VIDEO_PROVIDERS = ("gemini", "dreamina", "seedance", "manual", "unknown")
DEFAULT_YOUTUBE_CHANNEL_TITLE = "Soft Hour Radio"
JAPAN_YOUTUBE_CHANNEL_TITLE = "Tokyo Daydream Radio"
SUNDAZE_YOUTUBE_CHANNEL_TITLE = "sundaze"
SOLWAVE_YOUTUBE_CHANNEL_TITLE = "Solwave Radio"
HARUHARU_YOUTUBE_CHANNEL_TITLE = "HaruHaru"
STORYLIGHT_YOUTUBE_CHANNEL_TITLE = "Storylight OST"
CINEMATIC_PULSE_YOUTUBE_CHANNEL_TITLE = "Cinematic Pulse"
CLUB_BLOOM_YOUTUBE_CHANNEL_TITLE = "Club Bloom"
OLD_VERSE_YOUTUBE_CHANNEL_TITLE = "The Old Verse"
NEW_VERSE_YOUTUBE_CHANNEL_TITLE = "The New Verse"
SIGNAL_ROOM_YOUTUBE_CHANNEL_TITLE = "Signal Room Radio"
SIGNAL_DESK_LEGACY_CHANNEL_TITLE = "Signal Desk Radio"
MIDNIGHT_CUE_LEGACY_CHANNEL_TITLE = "Midnight Cue Radio"
CHANNEL_PROFILE_DOCS = {
    DEFAULT_YOUTUBE_CHANNEL_TITLE: "docs/openclaw-channel-profiles/soft-hour-radio.md",
    JAPAN_YOUTUBE_CHANNEL_TITLE: "docs/openclaw-channel-profiles/tokyo-daydream-radio.md",
    SUNDAZE_YOUTUBE_CHANNEL_TITLE: "docs/openclaw-channel-profiles/sundaze.md",
    SOLWAVE_YOUTUBE_CHANNEL_TITLE: "docs/openclaw-channel-profiles/solwave-radio.md",
    HARUHARU_YOUTUBE_CHANNEL_TITLE: "docs/openclaw-channel-profiles/haruharu.md",
    STORYLIGHT_YOUTUBE_CHANNEL_TITLE: "docs/openclaw-channel-profiles/storylight-ost.md",
    CINEMATIC_PULSE_YOUTUBE_CHANNEL_TITLE: "docs/openclaw-channel-profiles/cinematic-pulse.md",
    CLUB_BLOOM_YOUTUBE_CHANNEL_TITLE: "docs/openclaw-channel-profiles/club-bloom.md",
    OLD_VERSE_YOUTUBE_CHANNEL_TITLE: "docs/openclaw-channel-profiles/the-old-verse.md",
    NEW_VERSE_YOUTUBE_CHANNEL_TITLE: "docs/openclaw-channel-profiles/the-new-verse.md",
    SIGNAL_ROOM_YOUTUBE_CHANNEL_TITLE: "docs/openclaw-channel-profiles/storylight-ost.md",
    SIGNAL_DESK_LEGACY_CHANNEL_TITLE: "docs/openclaw-channel-profiles/storylight-ost.md",
    MIDNIGHT_CUE_LEGACY_CHANNEL_TITLE: "docs/openclaw-channel-profiles/storylight-ost.md",
}
CHANNEL_CONCEPT_DOCS = {
    DEFAULT_YOUTUBE_CHANNEL_TITLE: "docs/openclaw-channel-concepts/soft-hour-radio.md",
    JAPAN_YOUTUBE_CHANNEL_TITLE: "docs/openclaw-channel-concepts/tokyo-daydream-radio.md",
    SUNDAZE_YOUTUBE_CHANNEL_TITLE: "docs/openclaw-channel-concepts/sundaze.md",
    SOLWAVE_YOUTUBE_CHANNEL_TITLE: "docs/openclaw-channel-concepts/solwave-radio.md",
    HARUHARU_YOUTUBE_CHANNEL_TITLE: "docs/openclaw-channel-concepts/haruharu.md",
    STORYLIGHT_YOUTUBE_CHANNEL_TITLE: "docs/openclaw-channel-concepts/storylight-ost.md",
    CINEMATIC_PULSE_YOUTUBE_CHANNEL_TITLE: "docs/openclaw-channel-concepts/cinematic-pulse.md",
    CLUB_BLOOM_YOUTUBE_CHANNEL_TITLE: "docs/openclaw-channel-concepts/club-bloom.md",
    OLD_VERSE_YOUTUBE_CHANNEL_TITLE: "docs/openclaw-channel-concepts/the-old-verse.md",
    NEW_VERSE_YOUTUBE_CHANNEL_TITLE: "docs/openclaw-channel-concepts/the-new-verse.md",
    SIGNAL_ROOM_YOUTUBE_CHANNEL_TITLE: "docs/openclaw-channel-concepts/storylight-ost.md",
    SIGNAL_DESK_LEGACY_CHANNEL_TITLE: "docs/openclaw-channel-concepts/storylight-ost.md",
    MIDNIGHT_CUE_LEGACY_CHANNEL_TITLE: "docs/openclaw-channel-concepts/storylight-ost.md",
}
CHANNEL_PROFILE_NAMES = {
    DEFAULT_YOUTUBE_CHANNEL_TITLE: "soft-hour-radio",
    JAPAN_YOUTUBE_CHANNEL_TITLE: "tokyo-daydream-radio",
    SUNDAZE_YOUTUBE_CHANNEL_TITLE: "sundaze",
    SOLWAVE_YOUTUBE_CHANNEL_TITLE: "solwave-radio",
    HARUHARU_YOUTUBE_CHANNEL_TITLE: "haruharu",
    STORYLIGHT_YOUTUBE_CHANNEL_TITLE: "storylight-ost",
    CINEMATIC_PULSE_YOUTUBE_CHANNEL_TITLE: "cinematic-pulse",
    CLUB_BLOOM_YOUTUBE_CHANNEL_TITLE: "club-bloom",
    OLD_VERSE_YOUTUBE_CHANNEL_TITLE: "the-old-verse",
    NEW_VERSE_YOUTUBE_CHANNEL_TITLE: "the-new-verse",
    SIGNAL_ROOM_YOUTUBE_CHANNEL_TITLE: "storylight-ost",
    SIGNAL_DESK_LEGACY_CHANNEL_TITLE: "storylight-ost",
    MIDNIGHT_CUE_LEGACY_CHANNEL_TITLE: "storylight-ost",
}
CHANNEL_TITLE_ALIASES = {
    STORYLIGHT_YOUTUBE_CHANNEL_TITLE: (
        SIGNAL_ROOM_YOUTUBE_CHANNEL_TITLE,
        SIGNAL_DESK_LEGACY_CHANNEL_TITLE,
        MIDNIGHT_CUE_LEGACY_CHANNEL_TITLE,
    ),
    SIGNAL_ROOM_YOUTUBE_CHANNEL_TITLE: (
        STORYLIGHT_YOUTUBE_CHANNEL_TITLE,
        SIGNAL_DESK_LEGACY_CHANNEL_TITLE,
        MIDNIGHT_CUE_LEGACY_CHANNEL_TITLE,
    ),
    SIGNAL_DESK_LEGACY_CHANNEL_TITLE: (
        STORYLIGHT_YOUTUBE_CHANNEL_TITLE,
        SIGNAL_ROOM_YOUTUBE_CHANNEL_TITLE,
        MIDNIGHT_CUE_LEGACY_CHANNEL_TITLE,
    ),
    MIDNIGHT_CUE_LEGACY_CHANNEL_TITLE: (
        STORYLIGHT_YOUTUBE_CHANNEL_TITLE,
        SIGNAL_ROOM_YOUTUBE_CHANNEL_TITLE,
        SIGNAL_DESK_LEGACY_CHANNEL_TITLE,
    ),
}
REQUIRED_METADATA_LANGUAGES = (
    "ko",
    "ja",
    "en",
    "es",
    "vi",
    "th",
    "hi",
    "fil",
    "id",
    "pt-BR",
    "pt-PT",
    "fr",
    "de",
    "ar",
    "zh-CN",
    "zh-TW",
)
TIMELINE_ROW_PATTERN = re.compile(r"^\s*\d{1,2}:\d{2}(?::\d{2})?\s+\S+", re.MULTILINE)
JAPAN_CHANNEL_KEYWORDS = (
    "anime",
    "anime pop",
    "anime-pop",
    "city pop",
    "citypop",
    "j-pop",
    "j pop",
    "jpop",
    "japanese pop",
    "japan pop",
    "japanese dance-pop",
    "japanese dance pop",
    "japanese synth-pop",
    "japanese synth pop",
    "japanese pop-rock",
    "japanese pop rock",
    "shibuya",
    "shinjuku",
    "tokyo",
    "vaporwave",
    "アニメ",
    "jポップ",
    "シティポップ",
    "東京",
    "渋谷",
    "新宿",
    "도쿄",
    "시부야",
    "신주쿠",
    "시티팝",
    "애니",
    "애니메이션",
    "제이팝",
)
LATIN_CHANNEL_KEYWORDS = (
    "bachata",
    "cumbia",
    "latin",
    "latin dance",
    "latin pop",
    "latin urban",
    "latino",
    "musica latina",
    "música latina",
    "pop latino",
    "reggaeton",
    "reggaetón",
    "salsa",
    "spanish pop",
    "spanish vocal",
    "urbano latino",
    "verano latino",
    "라틴",
    "라틴팝",
    "레게톤",
    "바차타",
    "살사",
    "스페니쉬",
    "스페인어",
    "스페인 팝",
    "스페인어 팝",
    "スペイン語",
    "ラテン",
    "ラテンポップ",
    "レゲトン",
)
ENGLISH_POP_CHANNEL_KEYWORDS = (
    "american pop",
    "english pop",
    "english vocal",
    "mainstream pop",
    "pop song",
    "pop vocal",
    "sundaze",
    "uk pop",
    "us pop",
    "western pop",
    "미국 팝",
    "미국팝",
    "영어 팝",
    "영어팝",
    "팝송",
    "英語ポップ",
    "洋楽ポップ",
)
KPOP_CHANNEL_KEYWORDS = (
    "haruharu",
    "k-pop",
    "k pop",
    "kpop",
    "korean pop",
    "korean dance-pop",
    "korean dance pop",
    "korean synth-pop",
    "korean synth pop",
    "korean pop-rock",
    "korean pop rock",
    "korean idol pop",
    "idol pop",
    "케이팝",
    "케이 팝",
    "한국 팝",
    "한국어 팝",
    "아이돌 팝",
    "韓国ポップ",
    "韓国語ポップ",
    "ケーポップ",
    "kポップ",
)
STORYLIGHT_CHANNEL_KEYWORDS = (
    "storylight",
    "storylight ost",
    "anime bgm",
    "anime ost",
    "anime game",
    "anime game ost",
    "japanese game ost",
    "japanese game bgm",
    "japanese arcade",
    "arcade game",
    "arcade bgm",
    "arcade ost",
    "8-bit",
    "8bit",
    "chiptune",
    "kawaii game",
    "cute game",
    "playful ost",
    "playful bgm",
    "fantasy ost",
    "fantasy game",
    "fantasy game ost",
    "fantasy game bgm",
    "fairy tale",
    "fairytale",
    "fantasy village",
    "cozy rpg",
    "rpg town",
    "game town",
    "game ost",
    "storybook",
    "story bgm",
    "magical bgm",
    "magic village",
    "forest village",
    "castle town",
    "secret library",
    "fantasy train",
    "아케이드",
    "아케이드 게임",
    "애니 bgm",
    "애니 ost",
    "애니메이션 bgm",
    "애니메이션 ost",
    "일본풍 게임",
    "일본 게임 ost",
    "일본 게임 bgm",
    "동화",
    "판타지 ost",
    "판타지 게임",
    "판타지 게임 ost",
    "판타지 게임 bgm",
    "판타지 브금",
    "판타지 bgm",
    "게임 ost",
    "게임 브금",
    "rpg 마을",
    "마법 마을",
    "숲속 마을",
    "스토리 bgm",
)
CINEMATIC_PULSE_CHANNEL_KEYWORDS = (
    "cinematic pulse",
    "movie ost",
    "movie score",
    "film score",
    "film-score",
    "orchestral score",
    "cinematic orchestra",
    "cinematic orchestral",
    "cinematic music",
    "cinematic bgm",
    "emotional film score",
    "emotional orchestra",
    "mystery tension",
    "orchestral tension",
    "epic orchestral",
    "epic battle",
    "battle music",
    "battle ost",
    "boss battle",
    "final boss",
    "heroic trailer",
    "trailer music",
    "dark fantasy",
    "sci-fi action",
    "sci fi action",
    "war drums",
    "cinematic action",
    "cinematic battle",
    "orchestral battle",
    "영화 ost",
    "영화 음악",
    "영화 스코어",
    "영화 오케스트라",
    "오케스트라 ost",
    "오케스트라 bgm",
    "시네마틱",
    "시네마틱 오케스트라",
    "감정적인 영화",
    "미스터리 긴장감",
    "웅장한",
    "전투 음악",
    "전투 bgm",
    "보스전",
    "최종 보스",
    "트레일러 음악",
    "다크 판타지",
    "히어로ic",
)
CLUB_BLOOM_CHANNEL_KEYWORDS = (
    "club bloom",
    "edm",
    "edm mix",
    "house music",
    "future house",
    "deep house",
    "tech house",
    "progressive house",
    "melodic techno",
    "peak-time techno",
    "peak time techno",
    "techno",
    "trance",
    "progressive trance",
    "big-room",
    "big room",
    "bass house",
    "electro house",
    "uk garage",
    "garage",
    "drum and bass",
    "liquid dnb",
    "dnb",
    "tropical house",
    "afro house",
    "synthwave club",
    "dance music",
    "dance mix",
    "festival edm",
    "club music",
    "club hits",
    "night club",
    "night drive edm",
    "workout edm",
    "gaming dance",
    "rooftop house",
    "rooftop dj",
    "beach club",
    "beach dj",
    "dj booth",
    "dj set",
    "festival stage",
    "concert stage",
    "warehouse rave",
    "pool party edm",
    "일렉트로닉",
    "edm 믹스",
    "하우스",
    "클럽 음악",
    "클럽",
    "댄스 믹스",
    "페스티벌 edm",
    "운동 edm",
    "나이트 드라이브 edm",
)
OLD_VERSE_CHANNEL_KEYWORDS = (
    "the old verse",
    "old testament",
    "genesis",
    "exodus",
    "leviticus",
    "numbers",
    "deuteronomy",
    "psalms",
    "proverbs",
    "isaiah",
    "jeremiah",
    "bible verse music",
    "scripture-inspired worship",
    "ancient biblical music",
    "genesis songs",
    "psalms music",
    "구약",
    "구약성서",
    "창세기",
    "출애굽",
    "시편",
    "잠언",
    "성경 기반",
    "성경 음악",
)
NEW_VERSE_CHANNEL_KEYWORDS = (
    "the new verse",
    "new testament",
    "gospel songs",
    "gospel song",
    "jesus words",
    "jesus music",
    "grace music",
    "scripture worship",
    "bible verse songs",
    "matthew",
    "mark gospel",
    "luke gospel",
    "john gospel",
    "acts of the apostles",
    "revelation",
    "신약",
    "신약성서",
    "복음",
    "복음서",
    "마태복음",
    "예수",
    "은혜",
    "찬양곡",
    "워십",
)
SIGNAL_ROOM_CHANNEL_KEYWORDS = (
    "signal room",
    "signal desk",
    "cue room",
    "briefing room",
    "newsroom bgm",
    "newsroom music",
    "tech newsroom",
    "research bgm",
    "research music",
    "debate bgm",
    "debate prep",
    "ai debate",
    "analysis bgm",
    "analytical focus",
    "fact-checking",
    "fact checking",
    "script notes",
    "script writing",
    "data review",
    "whiteboard focus",
    "citation grid",
    "reference stack",
    "future newsroom",
    "midnight research",
    "tech research",
    "calm debate",
    "mystery bgm",
    "mystery music",
    "documentary bgm",
    "documentary music",
    "storytelling bgm",
    "cinematic bgm",
    "investigation bgm",
    "dark ambient",
    "noir bgm",
    "midnight cue",
    "토론",
    "토론 준비",
    "리서치",
    "대본 정리",
    "자료 분석",
    "팩트체크",
    "분석",
    "뉴스룸",
    "브리핑룸",
    "미래형",
    "미스터리",
    "다큐",
    "다큐멘터리",
    "스토리",
    "시네마틱",
    "느와르",
)
POP_FAMILY_KEYWORDS = (
    "anime pop",
    "anime-pop",
    "anime opening",
    "american pop",
    "bachata",
    "english pop",
    "english vocal",
    "j-pop",
    "jpop",
    "japanese pop",
    "k-pop",
    "kpop",
    "korean pop",
    "latin pop",
    "latino pop",
    "mainstream pop",
    "pop latino",
    "pop song",
    "pop vocal",
    "reggaeton",
    "reggaetón",
    "spanish pop",
    "spanish vocal",
    "uk pop",
    "urbano latino",
    "us pop",
    "western pop",
    "제이팝",
    "일본 팝",
    "케이팝",
    "라틴팝",
    "레게톤",
    "스페인어 팝",
    "팝송",
    "팝 보컬",
    "ポップ",
    "英語ポップ",
    "洋楽ポップ",
    "jポップ",
    "ラテンポップ",
)
INSTRUMENTAL_INTENT_KEYWORDS = (
    "background music",
    "bgm",
    "instrumental",
    "instrumentals",
    "karaoke",
    "lofi",
    "lo-fi",
    "no lyric",
    "no lyrics",
    "no vocal",
    "no vocals",
    "non-vocal",
    "vocal off",
    "without lyrics",
    "without vocals",
    "가사 없는",
    "가사없",
    "보컬 없는",
    "보컬없",
    "연주곡",
    "배경음악",
    "インスト",
    "歌なし",
    "ボーカルなし",
)


def file_stem(path: Path) -> str:
    return path.stem.strip() or "Untitled Release"


def api_base(value: str | None) -> str:
    return (value or os.environ.get("AIMP_LOCAL_API_BASE") or DEFAULT_API_BASE).rstrip("/")


def print_json(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def request_json(client: httpx.Client, method: str, path: str, **kwargs) -> Any:
    response = client.request(method, path, **kwargs)
    try:
        payload = response.json()
    except ValueError:
        payload = response.text
    if response.is_error:
        detail = payload.get("detail") if isinstance(payload, dict) else payload
        raise RuntimeError(f"{response.status_code} {response.reason_phrase}: {detail}")
    return payload


def notify_slack(
    client: httpx.Client,
    text: str,
    *,
    channel_id: str | None = None,
    team_id: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"text": text}
    if channel_id:
        payload["channel_id"] = channel_id
    if team_id:
        payload["team_id"] = team_id
    try:
        return request_json(client, "POST", "/slack/notify", json=payload)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


def slack_notify_command(client: httpx.Client, args: argparse.Namespace) -> dict[str, Any]:
    result = notify_slack(
        client,
        args.text,
        channel_id=args.channel_id or None,
        team_id=args.team_id or None,
    )
    return {
        "action": "slack-notify",
        "ok": bool(result.get("ok")),
        "result": result,
    }


def upload_failure_notice(
    *,
    release: dict[str, Any],
    failures: list[dict[str, str]],
    uploaded_count: int,
    action: str,
) -> str:
    release_title = release.get("title") or release.get("id") or "unknown release"
    lines = [
        "*OpenClaw audio upload problem*",
        f"Release: `{release_title}`",
        f"Action: `{action}`",
        f"Uploaded remaining tracks: `{uploaded_count}`",
        f"Failed after {MAX_AUDIO_UPLOAD_ATTEMPTS} attempts:",
    ]
    for failure in failures[:10]:
        title = failure.get("title") or Path(failure.get("audio_path") or "").name
        audio_name = Path(failure.get("audio_path") or "").name
        error = failure.get("error") or "unknown error"
        lines.append(f"- `{title}` (`{audio_name}`): {error[:300]}")
    if len(failures) > 10:
        lines.append(f"- ...and {len(failures) - 10} more")
    lines.append("Render/publish was stopped. Re-download or re-export the failed source files and upload them again.")
    return "\n".join(lines)


def validate_local_audio_file(audio_path: Path) -> None:
    if not audio_path.exists():
        raise RuntimeError(f"Audio file does not exist: {audio_path}")
    if not audio_path.is_file():
        raise RuntimeError(f"Audio path is not a file: {audio_path}")
    if audio_path.stat().st_size <= 0:
        raise RuntimeError(f"Audio file is empty: {audio_path}")


def list_releases(client: httpx.Client, _args: argparse.Namespace) -> dict[str, Any]:
    releases = request_json(client, "GET", "/playlists/workspaces")
    return {
        "releases": [
            {
                "id": release["id"],
                "title": release["title"],
                "type": "single" if release["workspace_mode"] == "single_track_video" else "playlist",
                "workflow_state": release["workflow_state"],
                "archived": release.get("hidden", False),
                "tracks": len(release["tracks"]),
                "duration_seconds": release.get("actual_duration_seconds", 0),
                "youtube_video_id": release.get("youtube_video_id"),
                "youtube_channel_id": release.get("youtube_channel_id"),
                "youtube_channel_title": release.get("youtube_channel_title"),
                "target_youtube_channel_title": release.get("target_youtube_channel_title"),
                "created_at": release.get("created_at"),
                "updated_at": release.get("updated_at"),
            }
            for release in releases
        ]
    }


def create_release(client: httpx.Client, args: argparse.Namespace) -> dict[str, Any]:
    mode_aliases = {
        "playlist": "playlist",
        "single": "single_track_video",
        "single_track_video": "single_track_video",
    }
    workspace_mode = mode_aliases.get(str(args.workspace_mode).strip().lower())
    if not workspace_mode:
        raise RuntimeError("--workspace-mode must be playlist or single.")

    release = request_json(
        client,
        "POST",
        "/playlists/workspaces",
        json={
            "title": args.release_title,
            "target_duration_seconds": args.target_seconds,
            "workspace_mode": workspace_mode,
            "auto_publish_when_ready": False,
            "description": args.description,
            "cover_prompt": "",
            "dreamina_prompt": "",
            "target_youtube_channel_title": getattr(args, "youtube_channel_title", ""),
        },
    )
    return {
        "ok": True,
        "action": "create-release",
        "release": {
            "id": release["id"],
            "title": release["title"],
            "workspace_mode": release["workspace_mode"],
            "workflow_state": release["workflow_state"],
            "target_duration_seconds": release["target_duration_seconds"],
            "target_youtube_channel_title": release.get("target_youtube_channel_title"),
        },
        "next": (
            "Use this release.id while generating Suno output, then upload every related audio file with --release-id. "
            "Do not create another workspace for the same prompt/run."
        ),
    }


def find_release_by_title(client: httpx.Client, title: str) -> dict[str, Any]:
    releases = request_json(client, "GET", "/playlists/workspaces")
    matches = [release for release in releases if release["title"] == title]
    if not matches:
        raise RuntimeError(f"No release found with exact title: {title}")
    if len(matches) > 1:
        ids = ", ".join(release["id"] for release in matches)
        raise RuntimeError(f"Multiple releases share title {title!r}. Use --release-id. Matches: {ids}")
    return matches[0]


def resolve_release(client: httpx.Client, *, release_id: str = "", release_title: str = "") -> dict[str, Any]:
    if release_id:
        releases = request_json(client, "GET", "/playlists/workspaces")
        release = next((item for item in releases if item["id"] == release_id), None)
        if not release:
            raise RuntimeError(f"No release found with id: {release_id}")
        return release
    if release_title:
        return find_release_by_title(client, release_title)
    raise RuntimeError("Use --release-id or --release-title.")


def format_timestamp(seconds: int, *, force_hours: bool = False) -> str:
    seconds = max(int(seconds or 0), 0)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    remainder = seconds % 60
    if force_hours:
        return f"{hours:02d}:{minutes:02d}:{remainder:02d}"
    if hours:
        return f"{hours}:{minutes:02d}:{remainder:02d}"
    return f"{minutes:02d}:{remainder:02d}"


def read_text_file(value: str | None, *, label: str) -> str:
    if not value:
        return ""
    path = Path(value).expanduser().resolve()
    if not path.exists():
        raise RuntimeError(f"{label} file does not exist: {path}")
    if not path.is_file():
        raise RuntimeError(f"{label} path is not a file: {path}")
    return path.read_text(encoding="utf-8").strip()


def read_single_lyrics(args: argparse.Namespace) -> str:
    inline = str(getattr(args, "lyrics", "") or "")
    file_value = str(getattr(args, "lyrics_file", "") or "")
    if inline and file_value:
        raise RuntimeError("Use either --lyrics or --lyrics-file, not both.")
    return read_text_file(file_value, label="Lyrics") if file_value else inline


def resolve_lyrics_items(audio_count: int, *, lyrics: list[str], lyrics_files: list[str]) -> list[str]:
    if lyrics and lyrics_files:
        raise RuntimeError("Use either --lyrics or --lyrics-file for multi-audio uploads, not both.")
    values = [read_text_file(value, label="Lyrics") for value in lyrics_files] if lyrics_files else list(lyrics or [])
    if not values:
        return [""] * audio_count
    if len(values) == 1:
        return [values[0]] * audio_count
    if len(values) != audio_count:
        raise RuntimeError("When using per-track lyrics, provide either one shared value or exactly one per --audio.")
    return values


def resolve_style_items(audio_count: int, *, styles: list[str]) -> list[str]:
    values = list(styles or [])
    if not values:
        return [""] * audio_count
    if len(values) == 1:
        return [values[0]] * audio_count
    if len(values) != audio_count:
        raise RuntimeError("When using per-track styles, provide either one shared value or exactly one per --audio.")
    return values


def resolve_exclude_style_items(audio_count: int, *, exclude_styles: list[str]) -> list[str]:
    values = list(exclude_styles or [])
    if not values:
        return [""] * audio_count
    if len(values) == 1:
        return [values[0]] * audio_count
    if len(values) != audio_count:
        raise RuntimeError("When using per-track exclude styles, provide either one shared value or exactly one per --audio.")
    return values


def _flatten_text_values(*values: Any) -> str:
    parts: list[str] = []
    for value in values:
        if isinstance(value, (list, tuple, set)):
            parts.extend(str(item or "") for item in value)
        else:
            parts.append(str(value or ""))
    return " ".join(parts).lower()


def is_pop_family_vocal_request(*values: Any) -> bool:
    haystack = _flatten_text_values(*values)
    if any(keyword in haystack for keyword in INSTRUMENTAL_INTENT_KEYWORDS):
        return False
    return any(keyword in haystack for keyword in POP_FAMILY_KEYWORDS)


def require_pop_family_lyrics(*, lyrics_items: list[str], context: str, concept_values: list[Any]) -> None:
    if not is_pop_family_vocal_request(*concept_values):
        return
    missing = [index + 1 for index, lyrics in enumerate(lyrics_items) if not str(lyrics or "").strip()]
    if not missing:
        return
    joined = ", ".join(str(index) for index in missing)
    raise RuntimeError(
        f"{context} looks like a J-pop/K-pop/pop vocal release, so lyrics are required for track(s): {joined}. "
        "Generate or capture original lyrics and pass --lyrics or --lyrics-file for every track. "
        "Only omit lyrics when the human explicitly requested BGM/instrumental/no-vocal music."
    )


def max_playlist_track_seconds(args: argparse.Namespace) -> int:
    return max(int(getattr(args, "max_track_seconds", DEFAULT_MAX_PLAYLIST_TRACK_SECONDS) or 0), 0)


def min_playlist_track_seconds(args: argparse.Namespace) -> int:
    return max(int(getattr(args, "min_track_seconds", DEFAULT_MIN_PLAYLIST_TRACK_SECONDS) or 0), 0)


def require_playlist_track_duration(
    track: dict[str, Any],
    *,
    args: argparse.Namespace,
    context: str,
) -> None:
    duration_seconds = int(track.get("duration_seconds") or 0)
    if duration_seconds <= 0:
        return
    title = track.get("title") or track.get("id") or "unknown track"

    min_seconds = min_playlist_track_seconds(args)
    if not bool(getattr(args, "allow_short_track", False)) and min_seconds > 0 and duration_seconds < min_seconds:
        raise RuntimeError(
            f"{context} rejected `{title}` because its duration is {format_timestamp(duration_seconds)}. "
            f"Playlist tracks should be at least {format_timestamp(min_seconds)}. "
            "Use --allow-short-track only when the human explicitly accepts a shorter track."
        )

    max_seconds = max_playlist_track_seconds(args)
    if not bool(getattr(args, "allow_long_track", False)) and max_seconds > 0 and duration_seconds > max_seconds:
        raise RuntimeError(
            f"{context} rejected `{title}` because its duration is {format_timestamp(duration_seconds)}. "
            f"Playlist tracks must be {format_timestamp(max_seconds)} or shorter. "
            "Regenerate a shorter Suno track or pass --allow-long-track only when the human explicitly accepts a longer track."
        )


def require_release_playlist_track_durations(
    release: dict[str, Any],
    *,
    args: argparse.Namespace,
    context: str,
) -> None:
    for track in release.get("tracks") or []:
        require_playlist_track_duration(track, args=args, context=context)


def release_timeline(release: dict[str, Any]) -> list[dict[str, Any]]:
    tracks = release.get("tracks") or []
    return timeline_from_track_dicts(tracks, release.get("rendered_timeline") or [])


def create_single_release(client: httpx.Client, title: str, description: str = "") -> dict[str, Any]:
    return request_json(
        client,
        "POST",
        "/playlists/workspaces",
        json={
            "title": title,
            "target_duration_seconds": 1,
            "workspace_mode": "single_track_video",
            "auto_publish_when_ready": False,
            "description": description,
            "cover_prompt": "",
            "dreamina_prompt": "",
        },
    )


def upload_audio_file_to_release(
    client: httpx.Client,
    *,
    release_id: str,
    audio_path: Path,
    title: str,
    prompt: str,
    tags: str,
    lyrics: str = "",
    style: str = "",
    exclude_style: str = "",
    cover_path: Path | None = None,
    dispatch_review: bool = True,
    attempts: int = MAX_AUDIO_UPLOAD_ATTEMPTS,
) -> dict[str, Any]:
    validate_local_audio_file(audio_path)
    content_type = mimetypes.guess_type(str(audio_path))[0] or "audio/mpeg"
    last_error: Exception | None = None
    for attempt in range(1, max(attempts, 1) + 1):
        files: dict[str, tuple[str, Any, str]] = {}
        with audio_path.open("rb") as handle:
            files["audio_file"] = (audio_path.name, handle, content_type)
            cover_handle = None
            if cover_path:
                cover_content_type = mimetypes.guess_type(str(cover_path))[0] or "image/png"
                cover_handle = cover_path.open("rb")
                files["cover_file"] = (cover_path.name, cover_handle, cover_content_type)
            try:
                track = request_json(
                    client,
                    "POST",
                    "/tracks/manual-upload",
                    data={
                        "title": title,
                        "prompt": prompt or "OpenClaw generated audio upload",
                        "duration_seconds": "0",
                        "pending_workspace_id": release_id,
                        "tags": tags or "",
                        "lyrics": lyrics or "",
                        "style": style or "",
                        "exclude_style": exclude_style or "",
                        "dispatch_review": str(dispatch_review).lower(),
                    },
                    files=files,
                )
                duration_seconds = int(track.get("duration_seconds") or 0)
                if duration_seconds <= 0:
                    raise RuntimeError(
                        f"Upload returned invalid duration_seconds={track.get('duration_seconds')!r}"
                    )
                return track
            except (RuntimeError, httpx.HTTPError) as exc:
                last_error = exc
                if attempt >= max(attempts, 1):
                    break
                time.sleep(min(2.0 * attempt, 5.0))
            finally:
                if cover_handle:
                    cover_handle.close()
    raise RuntimeError(
        f"Audio upload failed after {max(attempts, 1)} attempts for {audio_path.name}: {last_error}"
    ) from last_error


def resolve_cover_path(value: str | None) -> Path | None:
    return resolve_image_path(value, label="Cover")


def resolve_thumbnail_path(value: str | None) -> Path | None:
    return resolve_image_path(value, label="Thumbnail")


def resolve_loop_video_path(value: str | None) -> Path | None:
    return resolve_image_path(value, label="Loop video")


def infer_loop_video_provider(loop_video_path: Path | None) -> str:
    if not loop_video_path:
        return "unknown"
    haystack = str(loop_video_path).lower()
    if "gemini" in haystack or "veo" in haystack:
        return "gemini"
    if "dreamina" in haystack:
        return "dreamina"
    if "seedance" in haystack or "sea-dance" in haystack:
        return "seedance"
    return "unknown"


def loop_video_provider_value(args: argparse.Namespace, loop_video_path: Path | None) -> str:
    explicit = str(getattr(args, "loop_video_provider", "") or "").strip().lower()
    if explicit:
        return explicit
    return infer_loop_video_provider(loop_video_path)


def probe_media_duration_seconds(media_path: Path) -> float | None:
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
                str(media_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return max(float(result.stdout.strip()), 0.0)
    except (OSError, subprocess.CalledProcessError, ValueError):
        return None


def require_normal_loop_video_duration(loop_video_path: Path | None, args: argparse.Namespace, *, context: str) -> None:
    if not loop_video_path or bool(getattr(args, "allow_short_loop_video", False)):
        return
    duration_seconds = probe_media_duration_seconds(loop_video_path)
    if duration_seconds is None:
        raise RuntimeError(
            f"{context} could not verify loop video duration with ffprobe: {loop_video_path}. "
            "Do not continue with an unverified loop-video clip. Re-download the MP4, verify it locally, "
            "or pass --allow-short-loop-video only when the human explicitly accepts a non-standard clip."
        )
    if duration_seconds < MIN_NORMAL_LOOP_VIDEO_SECONDS:
        raise RuntimeError(
            f"{context} rejected `{loop_video_path.name}` because it is {duration_seconds:.1f}s. "
            "The loop video is too short to use safely. Regenerate or re-download the MP4, then pass that file. "
            "Use --allow-short-loop-video only when the human explicitly "
            "requests or accepts a shorter loop."
        )


def resolve_image_path(value: str | None, *, label: str) -> Path | None:
    if not value:
        return None
    image_path = Path(value).expanduser().resolve()
    if not image_path.exists():
        raise RuntimeError(f"{label} file does not exist: {image_path}")
    if not image_path.is_file():
        raise RuntimeError(f"{label} path is not a file: {image_path}")
    return image_path


def resolve_candidate_covers(values: list[str]) -> list[Path | None]:
    covers = [resolve_cover_path(value) for value in values]
    if len(covers) > 2:
        raise RuntimeError("A single release can accept at most two candidate covers.")
    return covers


def upload_audio(client: httpx.Client, args: argparse.Namespace) -> dict[str, Any]:
    audio_path = Path(args.audio).expanduser().resolve()
    if not audio_path.exists():
        raise RuntimeError(f"Audio file does not exist: {audio_path}")
    if not audio_path.is_file():
        raise RuntimeError(f"Audio path is not a file: {audio_path}")
    cover_path = resolve_cover_path(args.cover)

    title = upload_track_title(args.title or file_stem(audio_path))
    lyrics = read_single_lyrics(args)
    if args.new_single:
        require_pop_family_lyrics(
            lyrics_items=[lyrics],
            context="upload-audio",
            concept_values=[args.release_title, title, args.prompt, args.style, args.tags],
        )
    release: dict[str, Any]
    created_release = False

    if args.new_single:
        release = create_single_release(
            client,
            args.release_title or title,
            description=f"Single release created by OpenClaw from {audio_path.name}.",
        )
        created_release = True
    elif args.release_id:
        release = request_json(client, "GET", "/playlists/workspaces")
        release = next((item for item in release if item["id"] == args.release_id), None)
        if not release:
            raise RuntimeError(f"No release found with id: {args.release_id}")
    elif args.release_title:
        release = find_release_by_title(client, args.release_title)
    else:
        raise RuntimeError("Use --new-single, --release-id, or --release-title.")

    auto_approve_playlist = release["workspace_mode"] == "playlist" and not args.pending_review
    require_pop_family_lyrics(
        lyrics_items=[lyrics],
        context="upload-audio",
        concept_values=[release.get("title"), title, args.prompt, args.style, args.tags],
    )
    try:
        track = upload_audio_file_to_release(
            client,
            release_id=release["id"],
            audio_path=audio_path,
            title=title,
            prompt=args.prompt,
            tags=args.tags,
            lyrics=lyrics,
            style=args.style,
            exclude_style=getattr(args, "exclude_style", ""),
            cover_path=cover_path,
            dispatch_review=not auto_approve_playlist,
        )
        if auto_approve_playlist:
            require_playlist_track_duration(track, args=args, context="upload-audio playlist auto-approval")
            track = approve_track_to_playlist(
                client,
                track_id=track["id"],
                release_id=release["id"],
                actor=args.actor,
            )
            release = get_release(client, release["id"])
    except Exception as exc:  # noqa: BLE001
        notify_slack(
            client,
            upload_failure_notice(
                release=release,
                failures=[{"title": title, "audio_path": str(audio_path), "error": str(exc)}],
                uploaded_count=0,
                action="upload-audio",
            ),
        )
        raise

    return {
        "ok": True,
        "action": "upload-audio",
        "created_release": created_release,
        "auto_approved": auto_approve_playlist,
        "release": {
            "id": release["id"],
            "title": release["title"],
            "workspace_mode": release["workspace_mode"],
            "workflow_state": release["workflow_state"],
        },
        "track": {
            "id": track["id"],
            "title": track["title"],
            "status": track["status"],
            "duration_seconds": track["duration_seconds"],
            "cover_image_path": (track.get("metadata_json") or {}).get("image_url"),
            "lyrics_present": bool((track.get("metadata_json") or {}).get("lyrics")),
            "style": (track.get("metadata_json") or {}).get("style") or "",
            "style_present": bool((track.get("metadata_json") or {}).get("style")),
        },
        "next": (
            "Track uploaded and auto-approved into the playlist."
            if auto_approve_playlist
            else "Review and approve the track in Slack or the web UI."
        ),
    }


def upload_single_candidates(client: httpx.Client, args: argparse.Namespace) -> dict[str, Any]:
    audio_paths = [Path(value).expanduser().resolve() for value in args.audio]
    cover_paths = resolve_candidate_covers(args.cover or [])
    if not 1 <= len(audio_paths) <= 2:
        raise RuntimeError("A single release can accept one or two Suno candidate audio files.")
    if cover_paths and len(cover_paths) not in {1, len(audio_paths)}:
        raise RuntimeError("Use either one shared cover or one cover per candidate audio.")
    for audio_path in audio_paths:
        if not audio_path.exists():
            raise RuntimeError(f"Audio file does not exist: {audio_path}")
        if not audio_path.is_file():
            raise RuntimeError(f"Audio path is not a file: {audio_path}")

    release_title = args.release_title or file_stem(audio_paths[0])
    raw_titles = [
        args.title[index - 1] if args.title and index <= len(args.title) else file_stem(audio_path)
        for index, audio_path in enumerate(audio_paths, start=1)
    ]
    track_titles = display_track_titles(
        [{"title": title, "duration_seconds": 0} for title in raw_titles]
    )
    lyrics_items = resolve_lyrics_items(len(audio_paths), lyrics=args.lyrics or [], lyrics_files=args.lyrics_file or [])
    style_items = resolve_style_items(len(audio_paths), styles=args.style or [])
    exclude_style_items = resolve_exclude_style_items(
        len(audio_paths),
        exclude_styles=getattr(args, "exclude_style", []) or [],
    )
    require_pop_family_lyrics(
        lyrics_items=lyrics_items,
        context="upload-single-candidates",
        concept_values=[release_title, raw_titles, args.prompt, args.style, args.tags],
    )
    if args.release_id:
        release = get_release(client, args.release_id)
        if release["workspace_mode"] != "single_track_video":
            raise RuntimeError("upload-single-candidates with --release-id requires a Single Release workspace.")
        existing_count = len(release.get("tracks") or [])
        if existing_count + len(audio_paths) > 2:
            raise RuntimeError("A Single Release can contain at most two candidate tracks.")
    else:
        release = create_single_release(
            client,
            release_title,
            description=(
                f"Single release candidate set created by OpenClaw from "
                f"{', '.join(path.name for path in audio_paths)}."
            ),
        )

    tracks = []
    failed_uploads: list[dict[str, str]] = []
    for index, audio_path in enumerate(audio_paths, start=1):
        track_title = track_titles[index - 1]
        cover_path = None
        if cover_paths:
            cover_path = cover_paths[index - 1] if len(cover_paths) == len(audio_paths) else cover_paths[0]
        try:
            track = upload_audio_file_to_release(
                client,
                release_id=release["id"],
                audio_path=audio_path,
                title=track_title,
                prompt=args.prompt,
                tags=args.tags,
                lyrics=lyrics_items[index - 1],
                style=style_items[index - 1],
                exclude_style=exclude_style_items[index - 1],
                cover_path=cover_path,
            )
        except Exception as exc:  # noqa: BLE001
            failed_uploads.append(
                {
                    "title": track_title,
                    "audio_path": str(audio_path),
                    "error": str(exc),
                }
            )
            continue
        tracks.append(
            {
                "id": track["id"],
                "title": track["title"],
                "status": track["status"],
                "duration_seconds": track["duration_seconds"],
                "cover_image_path": (track.get("metadata_json") or {}).get("image_url"),
                "lyrics_present": bool((track.get("metadata_json") or {}).get("lyrics")),
                "style": (track.get("metadata_json") or {}).get("style") or "",
                "style_present": bool((track.get("metadata_json") or {}).get("style")),
            }
        )

    if failed_uploads:
        notice = upload_failure_notice(
            release=release,
            failures=failed_uploads,
            uploaded_count=len(tracks),
            action="upload-single-candidates",
        )
        notify_slack(client, notice)
        if not tracks:
            raise RuntimeError(
                f"All candidate audio uploads failed after {MAX_AUDIO_UPLOAD_ATTEMPTS} attempts."
            )

    return {
        "ok": True,
        "action": "upload-single-candidates",
        "release": {
            "id": release["id"],
            "title": release["title"],
            "workspace_mode": release["workspace_mode"],
            "workflow_state": release["workflow_state"],
        },
        "tracks": tracks,
        "failed_uploads": failed_uploads,
        "next": (
            "Human review can approve one candidate. If both candidates are good, approve the second one too; "
            "the app will split it into its own Single Release instead of combining the two songs. "
            "If both candidates are rejected, the release is automatically archived and can be restored from the web UI."
        ),
    }


def create_playlist_release(
    client: httpx.Client,
    *,
    title: str,
    target_duration_seconds: int = 2400,
    description: str = "",
    youtube_channel_title: str = "",
) -> dict[str, Any]:
    return request_json(
        client,
        "POST",
        "/playlists/workspaces",
        json={
            "title": title,
            "target_duration_seconds": target_duration_seconds,
            "workspace_mode": "playlist",
            "auto_publish_when_ready": False,
            "description": description or "Automatic private playlist release created by OpenClaw.",
            "cover_prompt": "",
            "dreamina_prompt": "",
            "target_youtube_channel_title": youtube_channel_title,
        },
    )


def get_release(client: httpx.Client, release_id: str) -> dict[str, Any]:
    releases = request_json(client, "GET", "/playlists/workspaces")
    release = next((item for item in releases if item["id"] == release_id), None)
    if not release:
        raise RuntimeError(f"No release found with id: {release_id}")
    return release


def wait_for_release(
    client: httpx.Client,
    release_id: str,
    *,
    stage: str,
    timeout_seconds: int,
    poll_seconds: float,
    predicate,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    failed_states = {
        "render_failed",
        "video_build_failed",
        "publish_failed",
        "youtube_upload_failed",
    }
    last_release = get_release(client, release_id)
    while time.monotonic() < deadline:
        last_release = get_release(client, release_id)
        workflow_state = str(last_release.get("workflow_state") or "")
        if workflow_state in failed_states:
            raise RuntimeError(f"{stage} failed: {last_release.get('note') or workflow_state}")
        if predicate(last_release):
            return last_release
        time.sleep(poll_seconds)
    raise RuntimeError(
        f"Timed out waiting for {stage}. "
        f"Last state: {last_release.get('workflow_state')} / {last_release.get('note')}"
    )


def infer_youtube_channel_title(args: argparse.Namespace) -> str:
    explicit_title = str(getattr(args, "youtube_channel_title", "") or "").strip()
    if explicit_title:
        if explicit_title in {
            SIGNAL_ROOM_YOUTUBE_CHANNEL_TITLE,
            SIGNAL_DESK_LEGACY_CHANNEL_TITLE,
            MIDNIGHT_CUE_LEGACY_CHANNEL_TITLE,
        }:
            return STORYLIGHT_YOUTUBE_CHANNEL_TITLE
        return explicit_title

    haystack = " ".join(
        str(value or "")
        for value in (
            getattr(args, "release_title", ""),
            getattr(args, "description", ""),
            getattr(args, "prompt", ""),
            getattr(args, "tags", ""),
        )
    ).lower()
    has_instrumental_intent = any(keyword in haystack for keyword in INSTRUMENTAL_INTENT_KEYWORDS)
    if any(keyword.lower() in haystack for keyword in OLD_VERSE_CHANNEL_KEYWORDS):
        return OLD_VERSE_YOUTUBE_CHANNEL_TITLE
    if any(keyword.lower() in haystack for keyword in NEW_VERSE_CHANNEL_KEYWORDS):
        return NEW_VERSE_YOUTUBE_CHANNEL_TITLE
    if any(keyword.lower() in haystack for keyword in LATIN_CHANNEL_KEYWORDS) and not has_instrumental_intent:
        return SOLWAVE_YOUTUBE_CHANNEL_TITLE
    if any(keyword.lower() in haystack for keyword in KPOP_CHANNEL_KEYWORDS) and not has_instrumental_intent:
        return HARUHARU_YOUTUBE_CHANNEL_TITLE
    if any(keyword.lower() in haystack for keyword in CLUB_BLOOM_CHANNEL_KEYWORDS):
        return CLUB_BLOOM_YOUTUBE_CHANNEL_TITLE
    if any(keyword.lower() in haystack for keyword in CINEMATIC_PULSE_CHANNEL_KEYWORDS):
        return CINEMATIC_PULSE_YOUTUBE_CHANNEL_TITLE
    if any(keyword.lower() in haystack for keyword in STORYLIGHT_CHANNEL_KEYWORDS):
        return STORYLIGHT_YOUTUBE_CHANNEL_TITLE
    if any(keyword.lower() in haystack for keyword in JAPAN_CHANNEL_KEYWORDS):
        return JAPAN_YOUTUBE_CHANNEL_TITLE
    if any(keyword.lower() in haystack for keyword in ENGLISH_POP_CHANNEL_KEYWORDS) and not has_instrumental_intent:
        return SUNDAZE_YOUTUBE_CHANNEL_TITLE
    if any(keyword.lower() in haystack for keyword in SIGNAL_ROOM_CHANNEL_KEYWORDS):
        return STORYLIGHT_YOUTUBE_CHANNEL_TITLE
    return DEFAULT_YOUTUBE_CHANNEL_TITLE


def build_channel_profile(args: argparse.Namespace) -> dict[str, Any]:
    title = infer_youtube_channel_title(args)
    profile_doc = CHANNEL_PROFILE_DOCS.get(title, "docs/openclaw-channel-profiles/custom-channel.md")
    concept_doc = CHANNEL_CONCEPT_DOCS.get(title, "docs/openclaw-channel-concepts/custom-channel.md")
    return {
        "youtube_channel_title": title,
        "profile": CHANNEL_PROFILE_NAMES.get(title, "custom-channel"),
        "profile_doc": profile_doc,
        "concept_doc": concept_doc,
        "explicit_channel_requested": bool(str(getattr(args, "youtube_channel_title", "") or "").strip()),
        "metadata_doc": "docs/openclaw-youtube-metadata.md",
        "shared_upload_doc": "docs/openclaw-upload.md",
        "rule": "Pick the channel first, then read that channel's concept_doc for next-release planning and profile_doc for cover, thumbnail, and loop-video visuals. Do not mix signatures across channels.",
    }


def channel_profile(client: httpx.Client, args: argparse.Namespace) -> dict[str, Any]:
    del client
    return build_channel_profile(args)


def resolve_youtube_channel_id(client: httpx.Client, *, title: str, channel_id: str = "") -> str:
    if channel_id:
        return channel_id
    status = request_json(client, "GET", "/youtube/status")
    channels = status.get("channels") or []
    title_candidates = [title, *CHANNEL_TITLE_ALIASES.get(title, ())]
    match = next((channel for channel in channels if channel.get("title") in title_candidates), None)
    if not match:
        available = ", ".join(channel.get("title") or channel.get("id") or "unknown" for channel in channels)
        aliases = ", ".join(title_candidates)
        raise RuntimeError(f"YouTube channel {title!r} is not connected. Tried: {aliases}. Available channels: {available}")
    return str(match["id"])


def approve_track_to_release(
    client: httpx.Client,
    *,
    track_id: str,
    release_id: str,
    actor: str,
    rationale: str,
) -> dict[str, Any]:
    return request_json(
        client,
        "POST",
        f"/tracks/{track_id}/decisions",
        json={
            "decision": "approve",
            "source": "agent",
            "actor": actor,
            "rationale": rationale,
            "playlist_id": release_id,
        },
    )


def approve_track_to_playlist(client: httpx.Client, *, track_id: str, release_id: str, actor: str) -> dict[str, Any]:
    return approve_track_to_release(
        client,
        track_id=track_id,
        release_id=release_id,
        actor=actor,
        rationale="Auto-approved for app-managed playlist publishing.",
    )


def approve_generated_metadata(client: httpx.Client, *, release: dict[str, Any], actor: str) -> dict[str, Any]:
    title = (release.get("youtube_title") or "").strip()
    description = (release.get("youtube_description") or "").strip()
    tags = release.get("youtube_tags") or []
    if not title or not description:
        raise RuntimeError("Generated metadata is missing title or description.")
    if release.get("workspace_mode") == "playlist":
        ensure_playlist_metadata_complete(release)
    return request_json(
        client,
        "POST",
        f"/playlists/{release['id']}/metadata/approve",
        json={
            "actor": actor,
            "title": title,
            "description": description,
            "tags": tags,
            "note": "Auto-approved metadata for app-managed YouTube upload.",
        },
    )


def description_has_timeline(description: str) -> bool:
    return bool(TIMELINE_ROW_PATTERN.search(str(description or "")))


def ensure_playlist_metadata_complete(release: dict[str, Any]) -> None:
    localizations = release.get("youtube_localizations") or {}
    missing_languages = [
        language
        for language in REQUIRED_METADATA_LANGUAGES
        if not (localizations.get(language) or {}).get("title")
        or not (localizations.get(language) or {}).get("description")
    ]
    descriptions = [str(release.get("youtube_description") or "")]
    descriptions.extend(str(copy.get("description") or "") for copy in localizations.values())
    missing_timeline = not descriptions or not all(description_has_timeline(description) for description in descriptions)
    if not missing_languages and not missing_timeline:
        return

    problems = []
    if missing_languages:
        problems.append(f"missing localizations: {', '.join(missing_languages)}")
    if missing_timeline:
        problems.append("missing timestamped tracklist in one or more descriptions")
    raise RuntimeError(
        "Refusing to auto-approve incomplete playlist metadata: "
        + "; ".join(problems)
        + ". Run `scripts/openclaw-release metadata-context --release-id "
        + str(release.get("id") or "RELEASE_ID")
        + "`, write full metadata with timeline and every configured localization, then run "
        + "`scripts/openclaw-release approve-metadata` before publishing."
    )


def require_reupload_confirmation(args: argparse.Namespace, release: dict[str, Any], *, action: str) -> None:
    youtube_video_id = str(release.get("youtube_video_id") or "").strip()
    if not youtube_video_id or bool(getattr(args, "allow_reupload", False)):
        return
    raise RuntimeError(
        f"{action} refuses to re-upload release {release.get('id')} because it already has "
        f"YouTube video id {youtube_video_id}. Create a fresh release for a new upload, or pass "
        "--allow-reupload only when the human explicitly asks to upload this same release again."
    )


def release_has_uploaded_cover(release: dict[str, Any]) -> bool:
    return bool(
        release.get("cover_image_path")
        and release.get("cover_source") == "manual-upload"
    )


def release_has_uploaded_thumbnail(release: dict[str, Any]) -> bool:
    return bool(
        release.get("youtube_thumbnail_path")
        and release.get("youtube_thumbnail_source") == "manual-upload"
    )


def release_has_uploaded_loop_video(release: dict[str, Any]) -> bool:
    return bool(
        release.get("loop_video_path")
        and release.get("loop_video_source") == "manual-upload"
    )


def publish_visibility_summary(release: dict[str, Any]) -> dict[str, str]:
    scheduled_at = str(release.get("youtube_scheduled_publish_at") or "").strip()
    if scheduled_at:
        return {
            "privacy": f"scheduled public at {scheduled_at}",
            "next": "Listen to the scheduled YouTube upload before it goes public if review is needed.",
        }
    return {
        "privacy": "private (from AIMP_YOUTUBE_PRIVACY_STATUS)",
        "next": "Review the uploaded YouTube video in Studio if needed.",
    }


def publish_release(client: httpx.Client, args: argparse.Namespace) -> dict[str, Any]:
    release = resolve_release(client, release_id=args.release_id, release_title=args.release_title)
    require_reupload_confirmation(args, release, action="publish-release")
    if not release.get("output_video_path"):
        raise RuntimeError("publish-release requires a rendered video. Queue/render video first.")
    if not release.get("metadata_approved"):
        raise RuntimeError("publish-release requires approved metadata. Run approve-metadata first.")

    youtube_channel_title = infer_youtube_channel_title(args)
    channel_id = resolve_youtube_channel_id(
        client,
        title=youtube_channel_title,
        channel_id=args.youtube_channel_id,
    )
    release = request_json(
        client,
        "POST",
        f"/playlists/{release['id']}/approve-publish",
        json={
            "actor": args.actor,
            "youtube_channel_id": channel_id,
            "note": args.note or f"Publish release to {youtube_channel_title}.",
            "force_under_target": args.force_under_target,
        },
    )
    if not args.no_wait:
        release = wait_for_release(
            client,
            release["id"],
            stage="YouTube upload",
            timeout_seconds=args.wait_timeout_seconds,
            poll_seconds=args.poll_seconds,
            predicate=lambda item: bool(item.get("youtube_video_id"))
            or item.get("workflow_state") in {"ready_for_youtube_auth", "youtube_upload_deferred_verification"},
        )

    visibility = publish_visibility_summary(release)
    return {
        "ok": True,
        "action": "publish-release",
        "release": {
            "id": release["id"],
            "title": release["title"],
            "workflow_state": release["workflow_state"],
            "youtube_title": release.get("youtube_title"),
            "youtube_video_id": release.get("youtube_video_id"),
            "youtube_channel_id": channel_id,
            "youtube_channel_title": youtube_channel_title,
            "youtube_scheduled_publish_at": release.get("youtube_scheduled_publish_at"),
        },
        **visibility,
    }


def openclaw_lock_start(client: httpx.Client, args: argparse.Namespace) -> dict[str, Any]:
    return request_json(
        client,
        "POST",
        "/openclaw/lock/start",
        json={
            "owner": args.owner,
            "run_id": args.run_id,
            "operation": args.operation,
            "channel_title": args.channel_title,
            "release_id": args.release_id,
            "message": args.message,
        },
    )


def openclaw_lock_heartbeat(client: httpx.Client, args: argparse.Namespace) -> dict[str, Any]:
    return request_json(
        client,
        "POST",
        "/openclaw/lock/heartbeat",
        json={
            "owner": args.owner,
            "run_id": args.run_id,
            "operation": args.operation,
            "channel_title": args.channel_title,
            "release_id": args.release_id,
            "message": args.message,
        },
    )


def openclaw_lock_finish(client: httpx.Client, args: argparse.Namespace) -> dict[str, Any]:
    return request_json(
        client,
        "POST",
        "/openclaw/lock/finish",
        json={
            "owner": args.owner,
            "run_id": args.run_id,
            "status": args.status,
            "message": args.message,
        },
    )


def openclaw_status(client: httpx.Client, _args: argparse.Namespace) -> dict[str, Any]:
    return request_json(client, "GET", "/openclaw/status")


def openclaw_backlog_status(client: httpx.Client, _args: argparse.Namespace) -> dict[str, Any]:
    return request_json(client, "GET", "/openclaw/backlog/status")


def youtube_status(client: httpx.Client, _args: argparse.Namespace) -> dict[str, Any]:
    return request_json(client, "GET", "/youtube/status", headers={"Accept": "application/json"})


def openclaw_backlog_request(client: httpx.Client, args: argparse.Namespace) -> dict[str, Any]:
    return request_json(
        client,
        "POST",
        "/openclaw/backlog/request",
        json={"reason": args.reason, "prompt": args.prompt},
    )


def auto_publish_playlist(client: httpx.Client, args: argparse.Namespace) -> dict[str, Any]:
    audio_paths = [Path(value).expanduser().resolve() for value in args.audio]
    if not audio_paths:
        raise RuntimeError("Use at least one --audio path.")
    for audio_path in audio_paths:
        if not audio_path.exists():
            raise RuntimeError(f"Audio file does not exist: {audio_path}")
        if not audio_path.is_file():
            raise RuntimeError(f"Audio path is not a file: {audio_path}")
    cover_path = resolve_cover_path(args.cover)
    thumbnail_path = resolve_thumbnail_path(args.thumbnail)
    loop_video_path = resolve_loop_video_path(args.loop_video)
    raw_titles = args.title if args.title else [file_stem(path) for path in audio_paths]
    if args.title and len(args.title) != len(audio_paths):
        raise RuntimeError("When using --title, provide exactly one --title per --audio.")
    display_titles = display_track_titles(
        [{"title": title, "duration_seconds": 0} for title in raw_titles]
    )
    lyrics_items = resolve_lyrics_items(len(audio_paths), lyrics=args.lyrics or [], lyrics_files=args.lyrics_file or [])
    style_items = resolve_style_items(len(audio_paths), styles=args.style or [])
    exclude_style_items = resolve_exclude_style_items(
        len(audio_paths),
        exclude_styles=getattr(args, "exclude_style", []) or [],
    )
    if not cover_path and not args.release_id and not args.allow_generated_draft_cover:
        raise RuntimeError(
            "auto-publish-playlist requires --cover when creating a new Playlist Release. "
            "Generate a final 16:9 cover image first, then pass --cover ABSOLUTE_FINAL_COVER_IMAGE_PATH."
        )
    if not thumbnail_path and not args.release_id and not args.allow_cover_as_thumbnail:
        raise RuntimeError(
            "auto-publish-playlist requires --thumbnail when creating a new Playlist Release. "
            "Generate a YouTube thumbnail with readable text first, then pass --thumbnail ABSOLUTE_THUMBNAIL_IMAGE_PATH. "
            "Only pass --allow-cover-as-thumbnail if the human explicitly wants one image for both video and thumbnail."
        )
    if not args.release_id:
        require_pop_family_lyrics(
            lyrics_items=lyrics_items,
            context="auto-publish-playlist",
            concept_values=[
                args.release_title,
                raw_titles,
                args.description,
                args.prompt,
                args.style,
                args.tags,
                args.youtube_channel_title,
            ],
        )
    if not loop_video_path and not args.release_id and not args.allow_still_image_video:
        raise RuntimeError(
            "auto-publish-playlist requires --loop-video when creating a new Playlist Release. "
            "Generate and download the short Gemini/Dreamina/Seedance MP4 first, then pass --loop-video ABSOLUTE_LOOP_VIDEO_MP4. "
            "Only pass --allow-still-image-video if the human explicitly accepts a still-image fallback video."
        )
    require_normal_loop_video_duration(loop_video_path, args, context="auto-publish-playlist")

    youtube_channel_title = infer_youtube_channel_title(args)
    release = (
        get_release(client, args.release_id)
        if args.release_id
        else create_playlist_release(
            client,
            title=args.release_title or file_stem(audio_paths[0]),
            target_duration_seconds=args.target_seconds,
            description=args.description,
            youtube_channel_title=youtube_channel_title,
        )
    )
    if release["workspace_mode"] != "playlist":
        raise RuntimeError("auto-publish-playlist requires a Playlist Release, not a Single Release.")
    require_reupload_confirmation(args, release, action="auto-publish-playlist")
    if not cover_path and not release_has_uploaded_cover(release) and not args.allow_generated_draft_cover:
        raise RuntimeError(
            "auto-publish-playlist requires a final 16:9 cover image before YouTube upload. "
            "Pass --cover ABSOLUTE_FINAL_COVER_IMAGE_PATH, or upload a final cover to the release first. "
            "Only pass --allow-generated-draft-cover if the human explicitly accepts a placeholder cover."
        )
    if not thumbnail_path and not release_has_uploaded_thumbnail(release) and not args.allow_cover_as_thumbnail:
        raise RuntimeError(
            "auto-publish-playlist requires a YouTube thumbnail image before YouTube upload. "
            "Pass --thumbnail ABSOLUTE_THUMBNAIL_IMAGE_PATH, or upload a final thumbnail to the release first. "
            "Only pass --allow-cover-as-thumbnail if the human explicitly wants to reuse the video cover as the YouTube thumbnail."
        )
    if not loop_video_path and not release_has_uploaded_loop_video(release) and not args.allow_still_image_video:
        raise RuntimeError(
            "auto-publish-playlist requires an uploaded loop video before video render. "
            "Pass --loop-video ABSOLUTE_LOOP_VIDEO_MP4, or upload a loop video to the release first. "
            "Only pass --allow-still-image-video if the human explicitly accepts a still-image fallback video."
        )
    require_pop_family_lyrics(
        lyrics_items=lyrics_items,
        context="auto-publish-playlist",
        concept_values=[
            release.get("title"),
            raw_titles,
            args.release_title,
            args.description,
            args.prompt,
            args.style,
            args.tags,
            args.youtube_channel_title,
        ],
    )

    if loop_video_path:
        content_type = mimetypes.guess_type(str(loop_video_path))[0] or "video/mp4"
        loop_video_provider = loop_video_provider_value(args, loop_video_path)
        with loop_video_path.open("rb") as handle:
            release = request_json(
                client,
                "POST",
                f"/playlists/{release['id']}/loop-video/upload",
                data={
                    "actor": args.actor,
                    "smooth_loop": str(not args.hard_loop_video).lower(),
                    "loop_video_provider": loop_video_provider,
                },
                files={"loop_video_file": (loop_video_path.name, handle, content_type)},
            )

    uploaded_tracks = []
    failed_uploads: list[dict[str, str]] = []
    for audio_path, track_title, lyrics, style, exclude_style in zip(
        audio_paths,
        display_titles,
        lyrics_items,
        style_items,
        exclude_style_items,
    ):
        try:
            track = upload_audio_file_to_release(
                client,
                release_id=release["id"],
                audio_path=audio_path,
                title=track_title,
                prompt=args.prompt,
                tags=args.tags,
                lyrics=lyrics,
                style=style,
                exclude_style=exclude_style,
                cover_path=None,
                dispatch_review=False,
            )
            require_playlist_track_duration(track, args=args, context="auto-publish-playlist")
            approved = approve_track_to_playlist(
                client,
                track_id=track["id"],
                release_id=release["id"],
                actor=args.actor,
            )
        except Exception as exc:  # noqa: BLE001
            failed_uploads.append(
                {
                    "title": track_title,
                    "audio_path": str(audio_path),
                    "error": str(exc),
                }
            )
            continue
        uploaded_tracks.append(
            {
                "id": approved["id"],
                "title": approved["title"],
                "status": approved["status"],
                "duration_seconds": approved["duration_seconds"],
                "lyrics_present": bool((approved.get("metadata_json") or {}).get("lyrics")),
                "style": (approved.get("metadata_json") or {}).get("style") or "",
                "style_present": bool((approved.get("metadata_json") or {}).get("style")),
            }
        )

    if failed_uploads:
        notice = upload_failure_notice(
            release=release,
            failures=failed_uploads,
            uploaded_count=len(uploaded_tracks),
            action="auto-publish-playlist",
        )
        slack_result = notify_slack(client, notice)
        raise RuntimeError(
            f"{len(failed_uploads)} audio upload(s) failed after {MAX_AUDIO_UPLOAD_ATTEMPTS} attempts; "
            f"uploaded {len(uploaded_tracks)} remaining track(s); render/publish stopped. "
            f"Slack notified: {bool(slack_result.get('ok'))}."
        )

    release = get_release(client, release["id"])
    require_release_playlist_track_durations(
        release,
        args=args,
        context="auto-publish-playlist existing playlist track check",
    )

    release = request_json(
        client,
        "POST",
        f"/playlists/{release['id']}/render-audio",
        json={"actor": args.actor, "random": bool(getattr(args, "randomize_order", False))},
    )
    release = wait_for_release(
        client,
        release["id"],
        stage="audio render",
        timeout_seconds=args.wait_timeout_seconds,
        poll_seconds=args.poll_seconds,
        predicate=lambda item: bool(item.get("output_audio_path")),
    )

    if cover_path:
        content_type = mimetypes.guess_type(str(cover_path))[0] or "image/png"
        with cover_path.open("rb") as handle:
            release = request_json(
                client,
                "POST",
                f"/playlists/{release['id']}/cover/upload",
                data={"actor": args.actor},
                files={"cover_file": (cover_path.name, handle, content_type)},
            )
    elif release_has_uploaded_cover(release):
        release = get_release(client, release["id"])
    elif args.allow_generated_draft_cover:
        release = request_json(
            client,
            "POST",
            f"/playlists/{release['id']}/cover/generate",
            json={"actor": args.actor, "regenerate": False},
        )
    else:
        raise RuntimeError("Final cover image is required before cover approval.")

    if thumbnail_path:
        content_type = mimetypes.guess_type(str(thumbnail_path))[0] or "image/png"
        with thumbnail_path.open("rb") as handle:
            release = request_json(
                client,
                "POST",
                f"/playlists/{release['id']}/thumbnail/upload",
                data={"actor": args.actor},
                files={"thumbnail_file": (thumbnail_path.name, handle, content_type)},
            )
    elif release_has_uploaded_thumbnail(release):
        release = get_release(client, release["id"])
    elif args.allow_cover_as_thumbnail:
        release = get_release(client, release["id"])
    else:
        raise RuntimeError("Final YouTube thumbnail image is required before cover approval.")

    release = request_json(
        client,
        "POST",
        f"/playlists/{release['id']}/cover/approve",
        json={
            "actor": args.actor,
            "approved": True,
            "note": "Auto-approved cover for private playlist publishing.",
        },
    )
    release = request_json(
        client,
        "POST",
        f"/playlists/{release['id']}/video/render",
        json={
            "actor": args.actor,
            "allow_still_image_fallback": bool(args.allow_still_image_video),
            "video_spectrum_overlay_style": args.video_spectrum_overlay_style,
        },
    )
    release = wait_for_release(
        client,
        release["id"],
        stage="video render",
        timeout_seconds=args.wait_timeout_seconds,
        poll_seconds=args.poll_seconds,
        predicate=lambda item: bool(item.get("output_video_path")) and bool(item.get("youtube_title")),
    )

    if not release.get("youtube_title") or not release.get("youtube_description"):
        release = request_json(
            client,
            "POST",
            f"/playlists/{release['id']}/metadata/generate",
            json={"actor": args.actor},
        )
    release = approve_generated_metadata(client, release=release, actor=args.actor)

    channel_id = resolve_youtube_channel_id(
        client,
        title=youtube_channel_title,
        channel_id=args.youtube_channel_id,
    )
    release = request_json(
        client,
        "POST",
        f"/playlists/{release['id']}/approve-publish",
        json={
            "actor": args.actor,
            "youtube_channel_id": channel_id,
            "note": f"Auto-publish playlist to {youtube_channel_title}.",
            "force_under_target": args.force_under_target,
        },
    )
    release = wait_for_release(
        client,
        release["id"],
        stage="YouTube upload",
        timeout_seconds=args.wait_timeout_seconds,
        poll_seconds=args.poll_seconds,
        predicate=lambda item: bool(item.get("youtube_video_id")) or item.get("workflow_state") == "ready_for_youtube_auth",
    )

    visibility = publish_visibility_summary(release)
    return {
        "ok": True,
        "action": "auto-publish-playlist",
        "release": {
            "id": release["id"],
            "title": release["title"],
            "workflow_state": release["workflow_state"],
            "actual_duration_seconds": release["actual_duration_seconds"],
            "output_audio_path": release.get("output_audio_path"),
            "output_video_path": release.get("output_video_path"),
            "loop_video_path": release.get("loop_video_path"),
            "loop_video_provider": release.get("loop_video_provider"),
            "youtube_thumbnail_path": release.get("youtube_thumbnail_path"),
            "youtube_title": release.get("youtube_title"),
            "youtube_video_id": release.get("youtube_video_id"),
            "youtube_channel_id": channel_id,
            "youtube_channel_title": youtube_channel_title,
            "youtube_scheduled_publish_at": release.get("youtube_scheduled_publish_at"),
        },
        "uploaded_tracks": uploaded_tracks,
        **visibility,
    }


def auto_publish_single(client: httpx.Client, args: argparse.Namespace) -> dict[str, Any]:
    audio_paths = [Path(value).expanduser().resolve() for value in args.audio]
    if len(audio_paths) != 1:
        raise RuntimeError("auto-publish-single publishes exactly one final song. Run it once per good Suno output.")
    for audio_path in audio_paths:
        if not audio_path.exists():
            raise RuntimeError(f"Audio file does not exist: {audio_path}")
        if not audio_path.is_file():
            raise RuntimeError(f"Audio path is not a file: {audio_path}")
    cover_path = resolve_cover_path(args.cover)
    thumbnail_path = resolve_thumbnail_path(args.thumbnail)
    loop_video_path = resolve_loop_video_path(args.loop_video)
    raw_titles = args.title if args.title else [file_stem(path) for path in audio_paths]
    if args.title and len(args.title) != len(audio_paths):
        raise RuntimeError("When using --title, provide exactly one --title per --audio.")
    track_titles = display_track_titles(
        [{"title": title, "duration_seconds": 0} for title in raw_titles]
    )
    lyrics_items = resolve_lyrics_items(len(audio_paths), lyrics=args.lyrics or [], lyrics_files=args.lyrics_file or [])
    style_items = resolve_style_items(len(audio_paths), styles=args.style or [])
    exclude_style_items = resolve_exclude_style_items(
        len(audio_paths),
        exclude_styles=getattr(args, "exclude_style", []) or [],
    )
    if not cover_path and not args.release_id and not args.allow_generated_draft_cover:
        raise RuntimeError(
            "auto-publish-single requires --cover when creating a new Single Release. "
            "Generate a final 16:9 cover image with only the large, readable lower-left channel-name brand label first, then pass --cover ABSOLUTE_FINAL_COVER_IMAGE_PATH."
        )
    if not thumbnail_path and not args.release_id and not args.allow_cover_as_thumbnail:
        raise RuntimeError(
            "auto-publish-single requires --thumbnail when creating a new Single Release. "
            "Generate a YouTube thumbnail with readable text first, then pass --thumbnail ABSOLUTE_THUMBNAIL_IMAGE_PATH."
        )
    if not args.release_id:
        require_pop_family_lyrics(
            lyrics_items=lyrics_items,
            context="auto-publish-single",
            concept_values=[
                args.release_title,
                raw_titles,
                args.description,
                args.prompt,
                args.style,
                args.tags,
                args.youtube_channel_title,
            ],
        )
    if not loop_video_path and not args.release_id and not args.allow_still_image_video:
        raise RuntimeError(
            "auto-publish-single requires --loop-video when creating a new Single Release. "
            "Generate and download the short Gemini/Dreamina/Seedance MP4 first, then pass --loop-video ABSOLUTE_LOOP_VIDEO_MP4."
        )
    require_normal_loop_video_duration(loop_video_path, args, context="auto-publish-single")

    release = (
        get_release(client, args.release_id)
        if args.release_id
        else create_single_release(
            client,
            args.release_title or file_stem(audio_paths[0]),
            description=args.description or "Automatic private single release created by OpenClaw.",
        )
    )
    if release["workspace_mode"] != "single_track_video":
        raise RuntimeError("auto-publish-single requires a Single Release, not a Playlist Release.")
    require_reupload_confirmation(args, release, action="auto-publish-single")
    if release.get("tracks"):
        raise RuntimeError(
            "auto-publish-single requires an empty Single Release because it publishes one final song. "
            "Run without --release-id, or create a fresh Single Release for this Suno output."
        )
    if not cover_path and not release_has_uploaded_cover(release) and not args.allow_generated_draft_cover:
        raise RuntimeError(
            "auto-publish-single requires a final 16:9 cover image before YouTube upload. "
            "Pass --cover ABSOLUTE_FINAL_COVER_IMAGE_PATH, or upload a final cover to the release first."
        )
    if not thumbnail_path and not release_has_uploaded_thumbnail(release) and not args.allow_cover_as_thumbnail:
        raise RuntimeError(
            "auto-publish-single requires a YouTube thumbnail image before YouTube upload. "
            "Pass --thumbnail ABSOLUTE_THUMBNAIL_IMAGE_PATH, or upload a final thumbnail to the release first."
        )
    if not loop_video_path and not release_has_uploaded_loop_video(release) and not args.allow_still_image_video:
        raise RuntimeError(
            "auto-publish-single requires an uploaded loop video before video render. "
            "Pass --loop-video ABSOLUTE_LOOP_VIDEO_MP4, or upload a loop video to the release first. "
            "Only pass --allow-still-image-video if the human explicitly accepts a still-image fallback video."
        )
    require_pop_family_lyrics(
        lyrics_items=lyrics_items,
        context="auto-publish-single",
        concept_values=[
            release.get("title"),
            raw_titles,
            args.release_title,
            args.description,
            args.prompt,
            args.style,
            args.tags,
            args.youtube_channel_title,
        ],
    )

    if loop_video_path:
        content_type = mimetypes.guess_type(str(loop_video_path))[0] or "video/mp4"
        loop_video_provider = loop_video_provider_value(args, loop_video_path)
        with loop_video_path.open("rb") as handle:
            release = request_json(
                client,
                "POST",
                f"/playlists/{release['id']}/loop-video/upload",
                data={
                    "actor": args.actor,
                    "smooth_loop": str(not args.hard_loop_video).lower(),
                    "loop_video_provider": loop_video_provider,
                },
                files={"loop_video_file": (loop_video_path.name, handle, content_type)},
            )

    uploaded_tracks = []
    for audio_path, track_title, lyrics, style, exclude_style in zip(
        audio_paths,
        track_titles,
        lyrics_items,
        style_items,
        exclude_style_items,
    ):
        try:
            track = upload_audio_file_to_release(
                client,
                release_id=release["id"],
                audio_path=audio_path,
                title=track_title,
                prompt=args.prompt,
                tags=args.tags,
                lyrics=lyrics,
                style=style,
                exclude_style=exclude_style,
                cover_path=None,
                dispatch_review=False,
            )
            approved = approve_track_to_release(
                client,
                track_id=track["id"],
                release_id=release["id"],
                actor=args.actor,
                rationale="Auto-approved for private single publishing explicitly requested by the human.",
            )
        except Exception as exc:  # noqa: BLE001
            notify_slack(
                client,
                upload_failure_notice(
                    release=release,
                    failures=[{"title": track_title, "audio_path": str(audio_path), "error": str(exc)}],
                    uploaded_count=0,
                    action="auto-publish-single",
                ),
            )
            raise
        uploaded_tracks.append(
            {
                "id": approved["id"],
                "title": approved["title"],
                "status": approved["status"],
                "duration_seconds": approved["duration_seconds"],
                "lyrics_present": bool((approved.get("metadata_json") or {}).get("lyrics")),
                "style": (approved.get("metadata_json") or {}).get("style") or "",
                "style_present": bool((approved.get("metadata_json") or {}).get("style")),
            }
        )

    release = request_json(
        client,
        "POST",
        f"/playlists/{release['id']}/render-audio",
        json={"actor": args.actor},
    )
    release = wait_for_release(
        client,
        release["id"],
        stage="single audio render",
        timeout_seconds=args.wait_timeout_seconds,
        poll_seconds=args.poll_seconds,
        predicate=lambda item: bool(item.get("output_audio_path")),
    )

    if cover_path:
        content_type = mimetypes.guess_type(str(cover_path))[0] or "image/png"
        with cover_path.open("rb") as handle:
            release = request_json(
                client,
                "POST",
                f"/playlists/{release['id']}/cover/upload",
                data={"actor": args.actor},
                files={"cover_file": (cover_path.name, handle, content_type)},
            )
    elif release_has_uploaded_cover(release):
        release = get_release(client, release["id"])
    elif args.allow_generated_draft_cover:
        release = request_json(
            client,
            "POST",
            f"/playlists/{release['id']}/cover/generate",
            json={"actor": args.actor, "regenerate": False},
        )
    else:
        raise RuntimeError("Final cover image is required before cover approval.")

    if thumbnail_path:
        content_type = mimetypes.guess_type(str(thumbnail_path))[0] or "image/png"
        with thumbnail_path.open("rb") as handle:
            release = request_json(
                client,
                "POST",
                f"/playlists/{release['id']}/thumbnail/upload",
                data={"actor": args.actor},
                files={"thumbnail_file": (thumbnail_path.name, handle, content_type)},
            )
    elif release_has_uploaded_thumbnail(release):
        release = get_release(client, release["id"])
    elif args.allow_cover_as_thumbnail:
        release = get_release(client, release["id"])
    else:
        raise RuntimeError("Final YouTube thumbnail image is required before cover approval.")

    release = request_json(
        client,
        "POST",
        f"/playlists/{release['id']}/cover/approve",
        json={
            "actor": args.actor,
            "approved": True,
            "note": "Auto-approved cover for private single publishing.",
        },
    )
    release = request_json(
        client,
        "POST",
        f"/playlists/{release['id']}/video/render",
        json={
            "actor": args.actor,
            "allow_still_image_fallback": bool(args.allow_still_image_video),
            "video_spectrum_overlay_style": args.video_spectrum_overlay_style,
        },
    )
    release = wait_for_release(
        client,
        release["id"],
        stage="single video render",
        timeout_seconds=args.wait_timeout_seconds,
        poll_seconds=args.poll_seconds,
        predicate=lambda item: bool(item.get("output_video_path")) and bool(item.get("youtube_title")),
    )

    if not release.get("youtube_title") or not release.get("youtube_description"):
        release = request_json(
            client,
            "POST",
            f"/playlists/{release['id']}/metadata/generate",
            json={"actor": args.actor},
        )
    release = approve_generated_metadata(client, release=release, actor=args.actor)

    youtube_channel_title = infer_youtube_channel_title(args)
    channel_id = resolve_youtube_channel_id(
        client,
        title=youtube_channel_title,
        channel_id=args.youtube_channel_id,
    )
    release = request_json(
        client,
        "POST",
        f"/playlists/{release['id']}/approve-publish",
        json={
            "actor": args.actor,
            "youtube_channel_id": channel_id,
            "note": f"Auto-publish single to {youtube_channel_title}.",
        },
    )
    release = wait_for_release(
        client,
        release["id"],
        stage="YouTube single upload",
        timeout_seconds=args.wait_timeout_seconds,
        poll_seconds=args.poll_seconds,
        predicate=lambda item: bool(item.get("youtube_video_id")) or item.get("workflow_state") == "ready_for_youtube_auth",
    )

    visibility = publish_visibility_summary(release)
    return {
        "ok": True,
        "action": "auto-publish-single",
        "release": {
            "id": release["id"],
            "title": release["title"],
            "workflow_state": release["workflow_state"],
            "actual_duration_seconds": release["actual_duration_seconds"],
            "output_audio_path": release.get("output_audio_path"),
            "output_video_path": release.get("output_video_path"),
            "loop_video_path": release.get("loop_video_path"),
            "loop_video_provider": release.get("loop_video_provider"),
            "youtube_thumbnail_path": release.get("youtube_thumbnail_path"),
            "youtube_title": release.get("youtube_title"),
            "youtube_video_id": release.get("youtube_video_id"),
            "youtube_channel_id": channel_id,
            "youtube_channel_title": youtube_channel_title,
            "youtube_scheduled_publish_at": release.get("youtube_scheduled_publish_at"),
        },
        "uploaded_tracks": uploaded_tracks,
        **visibility,
    }


def upload_cover(client: httpx.Client, args: argparse.Namespace) -> dict[str, Any]:
    cover_path = Path(args.cover).expanduser().resolve()
    if not cover_path.exists():
        raise RuntimeError(f"Cover file does not exist: {cover_path}")
    if not cover_path.is_file():
        raise RuntimeError(f"Cover path is not a file: {cover_path}")

    release_id = args.release_id
    if not release_id and args.release_title:
        release_id = find_release_by_title(client, args.release_title)["id"]
    if not release_id:
        raise RuntimeError("Use --release-id or --release-title.")

    content_type = mimetypes.guess_type(str(cover_path))[0] or "image/png"
    with cover_path.open("rb") as handle:
        release = request_json(
            client,
            "POST",
            f"/playlists/{release_id}/cover/upload",
            data={"actor": args.actor},
            files={"cover_file": (cover_path.name, handle, content_type)},
        )

    return {
        "ok": True,
        "action": "upload-cover",
        "release": {
            "id": release["id"],
            "title": release["title"],
            "workflow_state": release["workflow_state"],
            "cover_image_path": release["cover_image_path"],
            "cover_approved": release["cover_approved"],
        },
        "next": "Approve the cover in the web UI, then render video.",
    }


def upload_thumbnail(client: httpx.Client, args: argparse.Namespace) -> dict[str, Any]:
    release = resolve_release(client, release_id=args.release_id, release_title=args.release_title)
    release_id = release["id"]
    thumbnail_path = resolve_thumbnail_path(args.thumbnail)
    if not thumbnail_path:
        raise RuntimeError("Use --thumbnail.")

    content_type = mimetypes.guess_type(str(thumbnail_path))[0] or "image/png"
    with thumbnail_path.open("rb") as handle:
        release = request_json(
            client,
            "POST",
            f"/playlists/{release_id}/thumbnail/upload",
            data={"actor": args.actor},
            files={"thumbnail_file": (thumbnail_path.name, handle, content_type)},
        )
    return {
        "ok": True,
        "action": "upload-thumbnail",
        "release": {
            "id": release["id"],
            "title": release["title"],
            "workflow_state": release["workflow_state"],
            "youtube_thumbnail_path": release.get("youtube_thumbnail_path"),
            "youtube_thumbnail_source": release.get("youtube_thumbnail_source"),
        },
        "next": "Use this thumbnail for the next YouTube publish/re-upload.",
    }


def upload_loop_video(client: httpx.Client, args: argparse.Namespace) -> dict[str, Any]:
    release = resolve_release(client, release_id=args.release_id, release_title=args.release_title)
    release_id = release["id"]
    loop_video_path = resolve_loop_video_path(args.loop_video)
    if not loop_video_path:
        raise RuntimeError("Use --loop-video.")
    require_normal_loop_video_duration(loop_video_path, args, context="upload-loop-video")

    content_type = mimetypes.guess_type(str(loop_video_path))[0] or "video/mp4"
    loop_video_provider = loop_video_provider_value(args, loop_video_path)
    with loop_video_path.open("rb") as handle:
        release = request_json(
            client,
            "POST",
            f"/playlists/{release_id}/loop-video/upload",
            data={
                "actor": args.actor,
                "smooth_loop": str(not args.hard_loop).lower(),
                "loop_video_provider": loop_video_provider,
            },
            files={"loop_video_file": (loop_video_path.name, handle, content_type)},
        )
    return {
        "ok": True,
        "action": "upload-loop-video",
        "release": {
            "id": release["id"],
            "title": release["title"],
            "workflow_state": release["workflow_state"],
            "loop_video_path": release.get("loop_video_path"),
            "loop_video_source": release.get("loop_video_source"),
            "loop_video_provider": release.get("loop_video_provider"),
            "loop_video_smooth": release.get("loop_video_smooth"),
        },
        "next": "This visual clip will be used during the next video render.",
    }


def delete_loop_video(client: httpx.Client, args: argparse.Namespace) -> dict[str, Any]:
    release = resolve_release(client, release_id=args.release_id, release_title=args.release_title)
    release = request_json(
        client,
        "DELETE",
        f"/playlists/{release['id']}/loop-video",
        params={"actor": args.actor},
    )
    return {
        "ok": True,
        "action": "delete-loop-video",
        "release": {
            "id": release["id"],
            "title": release["title"],
            "workflow_state": release["workflow_state"],
            "loop_video_path": release.get("loop_video_path"),
            "loop_video_source": release.get("loop_video_source"),
            "output_video_path": release.get("output_video_path"),
            "youtube_video_id": release.get("youtube_video_id"),
        },
        "next": "Generate and upload the correct Gemini/Dreamina/Seedance loop video, then render video again.",
    }


def render_audio(client: httpx.Client, args: argparse.Namespace) -> dict[str, Any]:
    release = resolve_release(client, release_id=args.release_id, release_title=args.release_title)
    release = request_json(
        client,
        "POST",
        f"/playlists/{release['id']}/render-audio",
        json={"actor": args.actor, "random": bool(args.randomize_order)},
    )
    if not args.no_wait:
        release = wait_for_release(
            client,
            release["id"],
            stage="audio render",
            timeout_seconds=args.wait_timeout_seconds,
            poll_seconds=args.poll_seconds,
            predicate=lambda item: bool(item.get("output_audio_path")),
        )
    return {
        "ok": True,
        "action": "render-audio",
        "release": {
            "id": release["id"],
            "title": release["title"],
            "workflow_state": release["workflow_state"],
            "actual_duration_seconds": release.get("actual_duration_seconds"),
            "output_audio_path": release.get("output_audio_path"),
        },
        "next": "Approve cover and queue video render.",
    }


def approve_cover(client: httpx.Client, args: argparse.Namespace) -> dict[str, Any]:
    release = resolve_release(client, release_id=args.release_id, release_title=args.release_title)
    release = request_json(
        client,
        "POST",
        f"/playlists/{release['id']}/cover/approve",
        json={
            "actor": args.actor,
            "approved": True,
            "note": args.note or "Cover approved from OpenClaw.",
        },
    )
    return {
        "ok": True,
        "action": "approve-cover",
        "release": {
            "id": release["id"],
            "title": release["title"],
            "workflow_state": release["workflow_state"],
            "cover_approved": release.get("cover_approved"),
            "cover_image_path": release.get("cover_image_path"),
        },
        "next": "Queue video render.",
    }


def render_video(client: httpx.Client, args: argparse.Namespace) -> dict[str, Any]:
    release = resolve_release(client, release_id=args.release_id, release_title=args.release_title)
    release = request_json(
        client,
        "POST",
        f"/playlists/{release['id']}/video/render",
        json={
            "actor": args.actor,
            "allow_still_image_fallback": bool(args.allow_still_image_video),
            "video_spectrum_overlay_style": args.video_spectrum_overlay_style,
        },
    )
    if args.wait:
        release = wait_for_release(
            client,
            release["id"],
            stage="video render",
            timeout_seconds=args.wait_timeout_seconds,
            poll_seconds=args.poll_seconds,
            predicate=lambda item: bool(item.get("output_video_path")) and bool(item.get("youtube_title")),
        )
    return {
        "ok": True,
        "action": "render-video",
        "release": {
            "id": release["id"],
            "title": release["title"],
            "workflow_state": release["workflow_state"],
            "output_video_path": release.get("output_video_path"),
            "youtube_title": release.get("youtube_title"),
        },
        "next": "If workflow_state is video_rendering or queued, wait for the VM app background worker to finish before metadata approval and publish.",
    }


def metadata_context(client: httpx.Client, args: argparse.Namespace) -> dict[str, Any]:
    release = resolve_release(client, release_id=args.release_id, release_title=args.release_title)
    timeline = release_timeline(release)
    total_seconds = sum(item["duration_seconds"] for item in timeline)
    timestamp_lines = [f"{item['start']} {item['title']}" for item in timeline]
    display_timestamp_lines = [f"{item['start']} {item['display_title_hint']}" for item in timeline]
    return {
        "ok": True,
        "action": "metadata-context",
        "release": {
            "id": release["id"],
            "title": release["title"],
            "workspace_mode": release["workspace_mode"],
            "workflow_state": release["workflow_state"],
            "target_duration_seconds": release["target_duration_seconds"],
            "actual_duration_seconds": release["actual_duration_seconds"],
            "output_audio_path": release.get("output_audio_path"),
            "output_video_path": release.get("output_video_path"),
            "youtube_title": release.get("youtube_title"),
            "youtube_description": release.get("youtube_description"),
            "youtube_tags": release.get("youtube_tags"),
            "youtube_localizations": release.get("youtube_localizations") or {},
        },
        "timeline": timeline,
        "timestamp_lines": timestamp_lines,
        "display_timestamp_lines": display_timestamp_lines,
        "total_seconds": total_seconds,
        "total_duration": format_timestamp(total_seconds, force_hours=total_seconds >= 3600),
        "instructions": (
            "Use timestamps and row order exactly. Prefer display_timestamp_lines for metadata so A/B suffixes are not shown. "
            "If total_seconds is 3600 or greater, keep every timestamp in HH:MM:SS form such as 00:00:00 and 01:02:03 so YouTube can link chapters past one hour. "
            "If you rewrite a displayed title, keep its timestamp fixed. "
            "For Japan/J-pop/Tokyo Daydream Radio releases, write localized timeline rows as follows: Korean description uses Japanese title plus Korean translation in parentheses, Japanese description uses Japanese title only, and English, Spanish, Vietnamese, Thai, Hindi, Filipino, Indonesian, Brazilian Portuguese, European Portuguese, French, German, Arabic, Simplified Chinese, and Traditional Chinese descriptions use translated title text only. "
            "For every localized video title, use natural transcreation for that language rather than literal translation. If direct translation sounds awkward, weak, too long, or less clickable, change the wording, order, or exact hook while keeping the release identity, genre/lane, and use case truthful. For sundaze/English pop releases, localized video titles may be adapted per language; keep English track titles in every localized timestamped timeline row and translate only the surrounding prose, use-case text, and hashtags. "
            "For HaruHaru/K-pop releases, write original Korean titles and Korean lyrics by default. Localized descriptions may translate track titles naturally, but timestamps and row order must stay exactly the same. "
            "For Storylight OST BGM releases, write English default metadata and position it as no-vocal playful Japanese arcade-game, fantasy-game, anime-game, and anime-OST-style music for gaming, reading, light focus, and fun background listening. "
            "For Cinematic Pulse releases, write English default metadata and position it as no-vocal large-scale cinematic orchestra, movie OST, film score, trailer, final battle scene, orchestral battle, emotional film score, mystery-tension, dark fantasy, sci-fi, heroic, or epic scene music. Do not use juvenile game-menu title wording such as Boss BGM, Final Boss Music, Final Boss Focus Music, 보스, 보스전, or bare BGM. Rotate among varied cinematic title lanes such as final battle, dark fantasy, heroic trailer, emotional score, sci-fi action, mystery tension, grand journey, orchestral battle, writing music, and movie OST focus; examples are style references, not fixed templates to repeat. For Club Bloom releases, write English default metadata and position it as no-vocal instrumental club music in one selected style lane, such as deep house, tech house, melodic techno, trance, bass house, UK garage, liquid DnB, tropical house, Afro house, synthwave club, workout EDM, night drive, gaming, party warmup, or club listening. Club Bloom titles must put the exact genre, subgenre, or genre fusion immediately after [playlist] using mainstream mix language such as Progressive Trance x EDM Mix, Tech House Workout Mix, Hype Trap x EDM Mix, Melodic Techno Night Drive, Bass House Club Mix, or Festival EDM Mix; put only one or two public use cases after the separator and avoid awkward lists like Progressive Trance for Night Roads, Gaming Focus and Club Drive. "
            "For The Old Verse releases, write English default metadata and position it as Old Testament scripture-inspired music that follows the biblical sequence from Genesis onward. Include the selected passage range in the main title, every localized title, and the description. For The New Verse releases, write English default metadata and position it as New Testament scripture-inspired worship music that follows the sequence from Matthew onward. Include the selected passage range in the main title, every localized title, and the description. "
            "Use each track's style and exclude_style fields as Suno generation context for later thumbnails, loop video, and metadata. "
            "Write tags as comma-separated plain tags without # symbols, and never use AI/process/tool tags such as AIMusic, AI music, AI generated, AI visualizer, Suno, OpenClaw, or Codex. "
            "For Tokyo/J-pop/Japan, HaruHaru/K-pop/Korean pop, Storylight OST/game-anime OST, Cinematic Pulse/movie OST, Club Bloom/EDM, The Old Verse/Old Testament, The New Verse/New Testament, sundaze/English pop, and Solwave/Latin/Spanish pop releases, write Korean, Japanese, English, Spanish, Vietnamese, Thai, Hindi, Filipino, Indonesian, Brazilian Portuguese, European Portuguese, French, German, Arabic suitable for Arabic/Egyptian audiences, Simplified Chinese, and Traditional Chinese title/description versions and pass them to approve-metadata. "
            "Use --default-language ko for HaruHaru, --default-language es for Solwave Radio, and --default-language en for sundaze, Storylight OST, Cinematic Pulse, Club Bloom, The Old Verse, and The New Verse."
        ),
    }


def read_description(args: argparse.Namespace) -> str:
    if args.description_file:
        path = Path(args.description_file).expanduser().resolve()
        if not path.exists():
            raise RuntimeError(f"Description file does not exist: {path}")
        if not path.is_file():
            raise RuntimeError(f"Description path is not a file: {path}")
        return path.read_text(encoding="utf-8").strip()
    return (args.description or "").strip()


def read_optional_text(value: str, file_value: str, *, label: str) -> str:
    if file_value:
        path = Path(file_value).expanduser().resolve()
        if not path.exists():
            raise RuntimeError(f"{label} file does not exist: {path}")
        if not path.is_file():
            raise RuntimeError(f"{label} path is not a file: {path}")
        return path.read_text(encoding="utf-8").strip()
    return (value or "").strip()


def metadata_localizations_from_args(args: argparse.Namespace, *, title: str, description: str) -> dict[str, dict[str, str]]:
    localizations = {
        "ko": {
            "title": read_optional_text(getattr(args, "ko_title", ""), "", label="Korean title") or title,
            "description": read_optional_text(
                getattr(args, "ko_description", ""),
                getattr(args, "ko_description_file", ""),
                label="Korean description",
            )
            or description,
        },
        "ja": {
            "title": read_optional_text(getattr(args, "ja_title", ""), "", label="Japanese title"),
            "description": read_optional_text(
                getattr(args, "ja_description", ""),
                getattr(args, "ja_description_file", ""),
                label="Japanese description",
            ),
        },
        "en": {
            "title": read_optional_text(getattr(args, "en_title", ""), "", label="English title"),
            "description": read_optional_text(
                getattr(args, "en_description", ""),
                getattr(args, "en_description_file", ""),
                label="English description",
            ),
        },
        "es": {
            "title": read_optional_text(getattr(args, "es_title", ""), "", label="Spanish title"),
            "description": read_optional_text(
                getattr(args, "es_description", ""),
                getattr(args, "es_description_file", ""),
                label="Spanish description",
            ),
        },
        "vi": {
            "title": read_optional_text(getattr(args, "vi_title", ""), "", label="Vietnamese title"),
            "description": read_optional_text(
                getattr(args, "vi_description", ""),
                getattr(args, "vi_description_file", ""),
                label="Vietnamese description",
            ),
        },
        "th": {
            "title": read_optional_text(getattr(args, "th_title", ""), "", label="Thai title"),
            "description": read_optional_text(
                getattr(args, "th_description", ""),
                getattr(args, "th_description_file", ""),
                label="Thai description",
            ),
        },
        "hi": {
            "title": read_optional_text(getattr(args, "hi_title", ""), "", label="Hindi title"),
            "description": read_optional_text(
                getattr(args, "hi_description", ""),
                getattr(args, "hi_description_file", ""),
                label="Hindi description",
            ),
        },
        "fil": {
            "title": read_optional_text(getattr(args, "fil_title", ""), "", label="Filipino title"),
            "description": read_optional_text(
                getattr(args, "fil_description", ""),
                getattr(args, "fil_description_file", ""),
                label="Filipino description",
            ),
        },
        "id": {
            "title": read_optional_text(getattr(args, "id_title", ""), "", label="Indonesian title"),
            "description": read_optional_text(
                getattr(args, "id_description", ""),
                getattr(args, "id_description_file", ""),
                label="Indonesian description",
            ),
        },
        "pt-BR": {
            "title": read_optional_text(getattr(args, "pt_title", ""), "", label="Brazilian Portuguese title"),
            "description": read_optional_text(
                getattr(args, "pt_description", ""),
                getattr(args, "pt_description_file", ""),
                label="Brazilian Portuguese description",
            ),
        },
        "pt-PT": {
            "title": read_optional_text(getattr(args, "pt_pt_title", ""), "", label="Portuguese Portugal title"),
            "description": read_optional_text(
                getattr(args, "pt_pt_description", ""),
                getattr(args, "pt_pt_description_file", ""),
                label="Portuguese Portugal description",
            ),
        },
        "fr": {
            "title": read_optional_text(getattr(args, "fr_title", ""), "", label="French title"),
            "description": read_optional_text(
                getattr(args, "fr_description", ""),
                getattr(args, "fr_description_file", ""),
                label="French description",
            ),
        },
        "de": {
            "title": read_optional_text(getattr(args, "de_title", ""), "", label="German title"),
            "description": read_optional_text(
                getattr(args, "de_description", ""),
                getattr(args, "de_description_file", ""),
                label="German description",
            ),
        },
        "ar": {
            "title": read_optional_text(getattr(args, "ar_title", ""), "", label="Arabic title"),
            "description": read_optional_text(
                getattr(args, "ar_description", ""),
                getattr(args, "ar_description_file", ""),
                label="Arabic description",
            ),
        },
        "zh-CN": {
            "title": read_optional_text(getattr(args, "zh_title", ""), "", label="Chinese title"),
            "description": read_optional_text(
                getattr(args, "zh_description", ""),
                getattr(args, "zh_description_file", ""),
                label="Chinese description",
            ),
        },
        "zh-TW": {
            "title": read_optional_text(getattr(args, "zh_tw_title", ""), "", label="Traditional Chinese title"),
            "description": read_optional_text(
                getattr(args, "zh_tw_description", ""),
                getattr(args, "zh_tw_description_file", ""),
                label="Traditional Chinese description",
            ),
        },
    }
    return {
        language: payload
        for language, payload in localizations.items()
        if payload["title"] and payload["description"]
    }


def approve_metadata(client: httpx.Client, args: argparse.Namespace) -> dict[str, Any]:
    release_id = args.release_id
    if not release_id and args.release_title:
        release_id = find_release_by_title(client, args.release_title)["id"]
    if not release_id:
        raise RuntimeError("Use --release-id or --release-title.")

    title = (args.title or "").strip()
    description = read_description(args)
    tags = (args.tags or "").strip()
    if not title:
        raise RuntimeError("--title is required.")
    if not description:
        raise RuntimeError("Use --description or --description-file.")
    if not tags:
        raise RuntimeError("--tags is required as a comma-separated string.")
    localizations = metadata_localizations_from_args(args, title=title, description=description)

    release = request_json(
        client,
        "POST",
        f"/playlists/{release_id}/metadata/approve",
        json={
            "actor": args.actor,
            "title": title,
            "description": description,
            "tags": tags,
            "default_language": getattr(args, "default_language", "") or "ko",
            "localizations": localizations,
            "note": args.note or "Metadata approved from OpenClaw.",
        },
    )
    return {
        "ok": True,
        "action": "approve-metadata",
        "release": {
            "id": release["id"],
            "title": release["title"],
            "workflow_state": release["workflow_state"],
            "metadata_approved": release["metadata_approved"],
            "youtube_title": release["youtube_title"],
            "youtube_description": release["youtube_description"],
            "youtube_tags": release["youtube_tags"],
            "youtube_localizations": release.get("youtube_localizations") or {},
        },
        "next": "Human can choose Publish Channel and approve publish/re-upload in the web UI.",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Upload OpenClaw-generated music assets to the local AI Music app.")
    parser.add_argument("--api-base", default=None, help=f"API base URL. Default: {DEFAULT_API_BASE}")

    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list-releases", help="List visible releases and ids.")
    list_parser.set_defaults(func=list_releases)

    create_parser = subparsers.add_parser(
        "create-release",
        help="Create an empty Single or Playlist Release workspace before generating Suno audio.",
    )
    create_parser.add_argument("--release-title", required=True, help="Release/workspace title to create before Suno generation.")
    create_parser.add_argument(
        "--workspace-mode",
        choices=["single", "single_track_video", "playlist"],
        required=True,
        help="Use single for one standalone song candidate set, or playlist for a multi-song mix.",
    )
    create_parser.add_argument("--target-seconds", type=int, default=2400, help="Playlist target duration. Default: 2400 seconds (40 minutes). Ignored for single releases.")
    create_parser.add_argument("--description", default="", help="Short concept description for the release.")
    create_parser.add_argument("--youtube-channel-title", default="", help="Target connected YouTube channel title for backlog accounting.")
    create_parser.set_defaults(func=create_release)

    context_parser = subparsers.add_parser(
        "metadata-context",
        help="Return release context and final-order timestamps for OpenClaw YouTube metadata writing.",
    )
    context_parser.add_argument("--release-id", default="", help="Existing release id.")
    context_parser.add_argument("--release-title", default="", help="Existing release title.")
    context_parser.set_defaults(func=metadata_context)

    profile_parser = subparsers.add_parser(
        "channel-profile",
        help="Infer the target YouTube channel and return the channel-specific OpenClaw visual profile doc.",
    )
    profile_parser.add_argument("--release-title", default="", help="Release title or human request title.")
    profile_parser.add_argument("--description", default="", help="Release concept description.")
    profile_parser.add_argument("--prompt", default="", help="Suno/image/video prompt or concept.")
    profile_parser.add_argument("--tags", default="", help="Comma-separated concept tags.")
    profile_parser.add_argument(
        "--youtube-channel-title",
        default="",
        help="Explicit target channel title. Overrides automatic inference and visual routing.",
    )
    profile_parser.set_defaults(func=channel_profile)

    audio_parser = subparsers.add_parser("upload-audio", help="Upload an audio file to an existing release or new single.")
    audio_parser.add_argument("--audio", required=True, help="Path to generated audio file.")
    audio_parser.add_argument("--title", default="", help="Track title. Defaults to audio filename stem.")
    audio_parser.add_argument("--prompt", default="", help="Prompt or generation note.")
    audio_parser.add_argument("--style", default="", help="Suno style/settings used to generate this audio.")
    audio_parser.add_argument("--exclude-style", default="", help="Suno excluded style/negative tags used to generate this audio.")
    audio_parser.add_argument("--tags", default="", help="Comma-separated tags.")
    audio_parser.add_argument("--lyrics", default="", help="Optional lyrics or content notes for this audio. Empty is allowed.")
    audio_parser.add_argument("--lyrics-file", default="", help="Optional UTF-8 text file containing lyrics or content notes.")
    audio_parser.add_argument("--cover", default="", help="Optional cover image file to upload with this audio.")
    audio_parser.add_argument("--new-single", action="store_true", help="Create a new Single Release from this audio.")
    audio_parser.add_argument("--release-id", default="", help="Existing release id.")
    audio_parser.add_argument("--release-title", default="", help="Existing release title, or new release title with --new-single.")
    audio_parser.add_argument("--pending-review", action="store_true", help="For Playlist Releases only, skip the default auto-approve behavior.")
    audio_parser.add_argument("--min-track-seconds", type=int, default=DEFAULT_MIN_PLAYLIST_TRACK_SECONDS, help="Minimum auto-approved Playlist Release track length. Default: 0 disables the lower bound.")
    audio_parser.add_argument("--max-track-seconds", type=int, default=DEFAULT_MAX_PLAYLIST_TRACK_SECONDS, help="Maximum auto-approved Playlist Release track length. Default: 260.")
    audio_parser.add_argument("--allow-short-track", action="store_true", help="Allow a playlist track shorter than --min-track-seconds. Use only with explicit human approval.")
    audio_parser.add_argument("--allow-long-track", action="store_true", help="Allow a playlist track longer than --max-track-seconds. Use only with explicit human approval.")
    audio_parser.add_argument("--actor", default="openclaw", help="Actor name recorded when playlist uploads are auto-approved.")
    audio_parser.set_defaults(func=upload_audio)

    candidates_parser = subparsers.add_parser(
        "upload-single-candidates",
        help="Create a Single Release and upload one or two Suno candidate tracks.",
    )
    candidates_parser.add_argument("--audio", action="append", required=True, help="Candidate audio path. Repeat up to two times.")
    candidates_parser.add_argument("--title", action="append", default=[], help="Candidate title. Repeat in the same order as --audio.")
    candidates_parser.add_argument("--cover", action="append", default=[], help="Optional candidate cover path. Repeat once for a shared cover or once per --audio.")
    candidates_parser.add_argument("--release-id", default="", help="Existing Single Release workspace id created before Suno generation.")
    candidates_parser.add_argument("--release-title", default="", help="Single release title. Defaults to first audio filename stem.")
    candidates_parser.add_argument("--prompt", default="", help="Prompt or generation note shared by the candidates.")
    candidates_parser.add_argument("--style", action="append", default=[], help="Suno style/settings. Repeat once per --audio, or provide one shared value.")
    candidates_parser.add_argument("--exclude-style", action="append", default=[], help="Suno excluded style/negative tags. Repeat once per --audio, or provide one shared value.")
    candidates_parser.add_argument("--tags", default="", help="Comma-separated tags shared by the candidates.")
    candidates_parser.add_argument("--lyrics", action="append", default=[], help="Optional lyrics/content notes. Repeat once per --audio, or provide one shared value.")
    candidates_parser.add_argument("--lyrics-file", action="append", default=[], help="Optional UTF-8 lyrics file. Repeat once per --audio, or provide one shared file.")
    candidates_parser.set_defaults(func=upload_single_candidates)

    auto_playlist_parser = subparsers.add_parser(
        "auto-publish-playlist",
        help="Upload playlist tracks, auto-approve them, render, generate metadata, and publish through the app to YouTube.",
    )
    auto_playlist_parser.add_argument("--audio", action="append", required=True, help="Generated playlist audio path. Repeat for every track.")
    auto_playlist_parser.add_argument("--title", action="append", default=[], help="Optional track title. Repeat in the same order as --audio.")
    auto_playlist_parser.add_argument("--cover", default="", help="Required final 16:9 playlist cover image unless an uploaded final cover already exists on the release.")
    auto_playlist_parser.add_argument("--thumbnail", default="", help="Required YouTube thumbnail image with readable title/use-case text unless an uploaded thumbnail already exists on the release.")
    auto_playlist_parser.add_argument("--loop-video", default="", help="Required short visual clip generated by Gemini/Dreamina/Seedance for the rendered video unless an uploaded loop video already exists on the release.")
    auto_playlist_parser.add_argument("--loop-video-provider", choices=LOOP_VIDEO_PROVIDERS, default="", help="Provider that created --loop-video. Use gemini, dreamina, or seedance for generated clips.")
    auto_playlist_parser.add_argument("--hard-loop-video", action="store_true", help="Use direct clip reuse instead of the default smoothed render.")
    auto_playlist_parser.add_argument("--allow-still-image-video", action="store_true", help="Explicitly allow rendering from the still cover image without a loop video. Do not use unless the human accepts this fallback.")
    auto_playlist_parser.add_argument("--allow-short-loop-video", action="store_true", help="Allow a loop video shorter than the normal loop-video target. Use only when the human explicitly accepts a non-standard clip.")
    auto_playlist_parser.add_argument("--allow-generated-draft-cover", action="store_true", help="Explicitly allow the app's placeholder draft cover. Do not use unless the human accepts it.")
    auto_playlist_parser.add_argument("--allow-cover-as-thumbnail", action="store_true", help="Reuse the video cover as the YouTube thumbnail. Do not use unless the human accepts one image for both roles.")
    auto_playlist_parser.add_argument("--release-id", default="", help="Existing Playlist Release id. If omitted, a new release is created.")
    auto_playlist_parser.add_argument("--release-title", default="", help="New Playlist Release title. Defaults to first audio filename stem.")
    auto_playlist_parser.add_argument("--description", default="", help="Release description used for metadata generation.")
    auto_playlist_parser.add_argument("--prompt", default="", help="Prompt or generation note shared by uploaded tracks.")
    auto_playlist_parser.add_argument("--style", action="append", default=[], help="Suno style/settings. Repeat once per --audio, or provide one shared value.")
    auto_playlist_parser.add_argument("--exclude-style", action="append", default=[], help="Suno excluded style/negative tags. Repeat once per --audio, or provide one shared value.")
    auto_playlist_parser.add_argument("--tags", default="", help="Comma-separated tags shared by uploaded tracks.")
    auto_playlist_parser.add_argument("--lyrics", action="append", default=[], help="Optional lyrics/content notes. Repeat once per --audio, or provide one shared value.")
    auto_playlist_parser.add_argument("--lyrics-file", action="append", default=[], help="Optional UTF-8 lyrics file. Repeat once per --audio, or provide one shared file.")
    auto_playlist_parser.add_argument("--target-seconds", type=int, default=2400, help="Playlist target duration. Default: 2400 seconds (40 minutes).")
    auto_playlist_parser.add_argument("--min-track-seconds", type=int, default=DEFAULT_MIN_PLAYLIST_TRACK_SECONDS, help="Minimum allowed duration for each playlist track. Default: 0 disables the lower bound.")
    auto_playlist_parser.add_argument("--max-track-seconds", type=int, default=DEFAULT_MAX_PLAYLIST_TRACK_SECONDS, help="Maximum allowed duration for each playlist track. Default: 260.")
    auto_playlist_parser.add_argument("--allow-short-track", action="store_true", help="Allow playlist tracks shorter than --min-track-seconds. Use only with explicit human approval.")
    auto_playlist_parser.add_argument("--allow-long-track", action="store_true", help="Allow playlist tracks longer than --max-track-seconds. Use only with explicit human approval.")
    auto_playlist_parser.add_argument("--randomize-order", action="store_true", help="Shuffle approved playlist track order before audio render. Metadata timestamps will use the rendered order.")
    auto_playlist_parser.add_argument("--youtube-channel-title", default="", help="Connected YouTube channel title. Default: inferred from release; J-pop/Tokyo uses Tokyo Daydream Radio, K-pop uses HaruHaru, playful Japanese game/anime OST and arcade/fantasy-game BGM use Storylight OST, large-scale cinematic orchestra/movie OST/film score uses Cinematic Pulse, no-vocal EDM/house/techno/trance club music uses Club Bloom, Old Testament/Bible sequence uses The Old Verse, New Testament/Gospel/worship uses The New Verse, English pop uses sundaze, Latin/Spanish pop uses Solwave Radio, otherwise Soft Hour Radio.")
    auto_playlist_parser.add_argument("--youtube-channel-id", default="", help="Optional explicit YouTube channel id. Overrides title lookup.")
    auto_playlist_parser.add_argument(
        "--video-spectrum-overlay-style",
        choices=["bars", "multiwave", "thinwave", "mirror-bars", "radial", "pulse", "none"],
        default="bars",
        help="App-rendered audio visualizer preset. OpenClaw should choose this per release; omitted fallback is bars. Use none for fastest render without spectrum overlay.",
    )
    auto_playlist_parser.add_argument("--force-under-target", action="store_true", help="Allow publish even if approved duration is under target.")
    auto_playlist_parser.add_argument("--allow-reupload", action="store_true", help="Allow uploading an existing release that already has a YouTube video id. Use only when the human explicitly requests a duplicate/replacement upload.")
    auto_playlist_parser.add_argument("--actor", default="openclaw:auto-playlist", help="Actor name recorded in histories.")
    auto_playlist_parser.add_argument("--wait-timeout-seconds", type=int, default=21600, help="Max wait per long stage. Default: 6 hours.")
    auto_playlist_parser.add_argument("--poll-seconds", type=float, default=10.0, help="Polling interval while waiting for background jobs.")
    auto_playlist_parser.set_defaults(func=auto_publish_playlist)

    auto_single_parser = subparsers.add_parser(
        "auto-publish-single",
        help="Upload one final single, auto-approve, render, generate metadata, and publish through the app to YouTube.",
    )
    auto_single_parser.add_argument("--audio", action="append", required=True, help="Generated single audio path. Use exactly one; run this command again for a second good Suno output.")
    auto_single_parser.add_argument("--title", action="append", default=[], help="Optional track title. Repeat in the same order as --audio.")
    auto_single_parser.add_argument("--cover", default="", help="Required final 16:9 cover image with only the large, readable lower-left channel-name brand label unless an uploaded final cover already exists on the release.")
    auto_single_parser.add_argument("--thumbnail", default="", help="Required YouTube thumbnail image with readable text unless an uploaded thumbnail already exists on the release.")
    auto_single_parser.add_argument("--loop-video", default="", help="Required short visual clip generated by Gemini/Dreamina/Seedance for the rendered video unless an uploaded loop video already exists on the release.")
    auto_single_parser.add_argument("--loop-video-provider", choices=LOOP_VIDEO_PROVIDERS, default="", help="Provider that created --loop-video. Use gemini, dreamina, or seedance for generated clips.")
    auto_single_parser.add_argument("--hard-loop-video", action="store_true", help="Use direct clip reuse instead of the default smoothed render.")
    auto_single_parser.add_argument("--allow-still-image-video", action="store_true", help="Explicitly allow rendering from the still cover image without a loop video. Do not use unless the human accepts this fallback.")
    auto_single_parser.add_argument("--allow-short-loop-video", action="store_true", help="Allow a loop video shorter than the normal loop-video target. Use only when the human explicitly accepts a non-standard clip.")
    auto_single_parser.add_argument("--allow-generated-draft-cover", action="store_true", help="Explicitly allow the app's placeholder draft cover. Do not use unless the human accepts it.")
    auto_single_parser.add_argument("--allow-cover-as-thumbnail", action="store_true", help="Reuse the video cover as the YouTube thumbnail. Do not use unless the human accepts one image for both roles.")
    auto_single_parser.add_argument("--release-id", default="", help="Existing Single Release id. If omitted, a new release is created.")
    auto_single_parser.add_argument("--release-title", default="", help="New Single Release title. Defaults to first audio filename stem.")
    auto_single_parser.add_argument("--description", default="", help="Release description used for metadata generation.")
    auto_single_parser.add_argument("--prompt", default="", help="Prompt or generation note shared by uploaded tracks.")
    auto_single_parser.add_argument("--style", action="append", default=[], help="Suno style/settings for this final song. Provide one value.")
    auto_single_parser.add_argument("--exclude-style", action="append", default=[], help="Suno excluded style/negative tags for this final song. Provide one value.")
    auto_single_parser.add_argument("--tags", default="", help="Comma-separated tags shared by uploaded tracks.")
    auto_single_parser.add_argument("--lyrics", action="append", default=[], help="Optional lyrics/content notes. Repeat once per --audio, or provide one shared value.")
    auto_single_parser.add_argument("--lyrics-file", action="append", default=[], help="Optional UTF-8 lyrics file. Repeat once per --audio, or provide one shared file.")
    auto_single_parser.add_argument("--youtube-channel-title", default="", help="Connected YouTube channel title. Default: inferred from release; J-pop/Tokyo uses Tokyo Daydream Radio, K-pop uses HaruHaru, playful Japanese game/anime OST and arcade/fantasy-game BGM use Storylight OST, large-scale cinematic orchestra/movie OST/film score uses Cinematic Pulse, no-vocal EDM/house/techno/trance club music uses Club Bloom, Old Testament/Bible sequence uses The Old Verse, New Testament/Gospel/worship uses The New Verse, English pop uses sundaze, Latin/Spanish pop uses Solwave Radio, otherwise Soft Hour Radio.")
    auto_single_parser.add_argument("--youtube-channel-id", default="", help="Optional explicit YouTube channel id. Overrides title lookup.")
    auto_single_parser.add_argument(
        "--video-spectrum-overlay-style",
        choices=["bars", "multiwave", "thinwave", "mirror-bars", "radial", "pulse", "none"],
        default="bars",
        help="App-rendered audio visualizer preset. OpenClaw should choose this per release; omitted fallback is bars. Use none for fastest render without spectrum overlay.",
    )
    auto_single_parser.add_argument("--allow-reupload", action="store_true", help="Allow uploading an existing release that already has a YouTube video id. Use only when the human explicitly requests a duplicate/replacement upload.")
    auto_single_parser.add_argument("--actor", default="openclaw:auto-single", help="Actor name recorded in histories.")
    auto_single_parser.add_argument("--wait-timeout-seconds", type=int, default=21600, help="Max wait per long stage. Default: 6 hours.")
    auto_single_parser.add_argument("--poll-seconds", type=float, default=10.0, help="Polling interval while waiting for background jobs.")
    auto_single_parser.set_defaults(func=auto_publish_single)

    cover_parser = subparsers.add_parser("upload-cover", help="Upload a 16:9 cover image for a release.")
    cover_parser.add_argument("--cover", required=True, help="Path to cover image file: jpg, png, or webp.")
    cover_parser.add_argument("--release-id", default="", help="Existing release id.")
    cover_parser.add_argument("--release-title", default="", help="Existing release title.")
    cover_parser.add_argument("--actor", default="openclaw", help="Actor name recorded in release history.")
    cover_parser.set_defaults(func=upload_cover)

    thumbnail_parser = subparsers.add_parser("upload-thumbnail", help="Upload a YouTube thumbnail image for a release.")
    thumbnail_parser.add_argument("--thumbnail", required=True, help="Path to YouTube thumbnail image: jpg, png, or webp.")
    thumbnail_parser.add_argument("--release-id", default="", help="Existing release id.")
    thumbnail_parser.add_argument("--release-title", default="", help="Existing release title.")
    thumbnail_parser.add_argument("--actor", default="openclaw", help="Actor name recorded in release history.")
    thumbnail_parser.set_defaults(func=upload_thumbnail)

    loop_video_parser = subparsers.add_parser("upload-loop-video", help="Upload a short visual loop clip for a release.")
    loop_video_parser.add_argument("--loop-video", required=True, help="Path to a short loop video: mp4, mov, m4v, or webm.")
    loop_video_parser.add_argument("--loop-video-provider", choices=LOOP_VIDEO_PROVIDERS, default="", help="Provider that created the loop video. Use gemini, dreamina, or seedance for generated clips.")
    loop_video_parser.add_argument("--release-id", default="", help="Existing release id.")
    loop_video_parser.add_argument("--release-title", default="", help="Existing release title.")
    loop_video_parser.add_argument("--hard-loop", action="store_true", help="Use direct clip reuse instead of the default smoothed render.")
    loop_video_parser.add_argument("--allow-short-loop-video", action="store_true", help="Allow a loop video shorter than the normal loop-video target. Use only when the human explicitly accepts a non-standard clip.")
    loop_video_parser.add_argument("--actor", default="openclaw", help="Actor name recorded in release history.")
    loop_video_parser.set_defaults(func=upload_loop_video)

    delete_loop_video_parser = subparsers.add_parser("delete-loop-video", help="Remove the uploaded loop video from a release.")
    delete_loop_video_parser.add_argument("--release-id", default="", help="Existing release id.")
    delete_loop_video_parser.add_argument("--release-title", default="", help="Existing release title.")
    delete_loop_video_parser.add_argument("--actor", default="openclaw", help="Actor name recorded in release history.")
    delete_loop_video_parser.set_defaults(func=delete_loop_video)

    render_audio_parser = subparsers.add_parser("render-audio", help="Render playlist audio for an existing release.")
    render_audio_parser.add_argument("--release-id", default="", help="Existing release id.")
    render_audio_parser.add_argument("--release-title", default="", help="Existing release title.")
    render_audio_parser.add_argument("--randomize-order", action="store_true", help="Shuffle approved playlist track order before audio render.")
    render_audio_parser.add_argument("--no-wait", action="store_true", help="Return immediately after queueing audio render.")
    render_audio_parser.add_argument("--wait-timeout-seconds", type=int, default=21600, help="Max wait for audio render. Default: 6 hours.")
    render_audio_parser.add_argument("--poll-seconds", type=float, default=10.0, help="Polling interval while waiting for audio render.")
    render_audio_parser.add_argument("--actor", default="openclaw", help="Actor name recorded in render history.")
    render_audio_parser.set_defaults(func=render_audio)

    approve_cover_parser = subparsers.add_parser("approve-cover", help="Approve the uploaded final cover for a release.")
    approve_cover_parser.add_argument("--release-id", default="", help="Existing release id.")
    approve_cover_parser.add_argument("--release-title", default="", help="Existing release title.")
    approve_cover_parser.add_argument("--actor", default="openclaw", help="Actor name recorded in cover approval history.")
    approve_cover_parser.add_argument("--note", default="", help="Optional cover approval note.")
    approve_cover_parser.set_defaults(func=approve_cover)

    render_video_parser = subparsers.add_parser("render-video", help="Queue video render for an existing release.")
    render_video_parser.add_argument("--release-id", default="", help="Existing release id.")
    render_video_parser.add_argument("--release-title", default="", help="Existing release title.")
    render_video_parser.add_argument("--allow-still-image-video", action="store_true", help="Explicitly allow rendering from the still cover image without a loop video.")
    render_video_parser.add_argument(
        "--video-spectrum-overlay-style",
        choices=["bars", "multiwave", "thinwave", "mirror-bars", "radial", "pulse", "none"],
        default="bars",
        help="App-rendered audio visualizer preset. OpenClaw should choose this per release.",
    )
    render_video_parser.add_argument("--wait", action="store_true", help="Wait for VM video render completion before continuing to metadata/publish.")
    render_video_parser.add_argument("--wait-timeout-seconds", type=int, default=21600, help="Max wait for video render. Default: 6 hours.")
    render_video_parser.add_argument("--poll-seconds", type=float, default=10.0, help="Polling interval while waiting for video render.")
    render_video_parser.add_argument("--actor", default="openclaw", help="Actor name recorded in video render history.")
    render_video_parser.set_defaults(func=render_video)

    slack_notify_parser = subparsers.add_parser(
        "slack-notify",
        help="Post a plain Slack progress/failure message through the app's configured Slack bot.",
    )
    slack_notify_parser.add_argument("--text", required=True, help="Slack message text to post.")
    slack_notify_parser.add_argument("--channel-id", default="", help="Optional Slack channel id override.")
    slack_notify_parser.add_argument("--team-id", default="", help="Optional Slack team id for installed workspace lookup.")
    slack_notify_parser.set_defaults(func=slack_notify_command)

    metadata_parser = subparsers.add_parser(
        "approve-metadata",
        help="Approve YouTube metadata for a rendered release using OpenClaw-written copy.",
    )
    metadata_parser.add_argument("--release-id", default="", help="Existing release id.")
    metadata_parser.add_argument("--release-title", default="", help="Existing release title.")
    metadata_parser.add_argument("--title", required=True, help="YouTube title.")
    metadata_parser.add_argument("--description", default="", help="YouTube description text. Prefer --description-file for multiline copy.")
    metadata_parser.add_argument("--description-file", default="", help="UTF-8 text file containing the YouTube description.")
    metadata_parser.add_argument("--tags", required=True, help="Comma-separated YouTube tags, for example: Piano,CafePiano,StudyMusic")
    metadata_parser.add_argument("--ko-title", default="", help="Korean localized YouTube title. Defaults to --title.")
    metadata_parser.add_argument("--ko-description", default="", help="Korean localized YouTube description. Defaults to --description.")
    metadata_parser.add_argument("--ko-description-file", default="", help="UTF-8 Korean description file.")
    metadata_parser.add_argument("--ja-title", default="", help="Japanese localized YouTube title.")
    metadata_parser.add_argument("--ja-description", default="", help="Japanese localized YouTube description. Prefer --ja-description-file for multiline copy.")
    metadata_parser.add_argument("--ja-description-file", default="", help="UTF-8 Japanese description file.")
    metadata_parser.add_argument("--en-title", default="", help="English localized YouTube title.")
    metadata_parser.add_argument("--en-description", default="", help="English localized YouTube description. Prefer --en-description-file for multiline copy.")
    metadata_parser.add_argument("--en-description-file", default="", help="UTF-8 English description file.")
    metadata_parser.add_argument("--es-title", default="", help="Spanish localized YouTube title.")
    metadata_parser.add_argument("--es-description", default="", help="Spanish localized YouTube description. Prefer --es-description-file for multiline copy.")
    metadata_parser.add_argument("--es-description-file", default="", help="UTF-8 Spanish description file.")
    metadata_parser.add_argument("--vi-title", default="", help="Vietnamese localized YouTube title.")
    metadata_parser.add_argument("--vi-description", default="", help="Vietnamese localized YouTube description. Prefer --vi-description-file for multiline copy.")
    metadata_parser.add_argument("--vi-description-file", default="", help="UTF-8 Vietnamese description file.")
    metadata_parser.add_argument("--th-title", default="", help="Thai localized YouTube title.")
    metadata_parser.add_argument("--th-description", default="", help="Thai localized YouTube description. Prefer --th-description-file for multiline copy.")
    metadata_parser.add_argument("--th-description-file", default="", help="UTF-8 Thai description file.")
    metadata_parser.add_argument("--hi-title", default="", help="Hindi localized YouTube title.")
    metadata_parser.add_argument("--hi-description", default="", help="Hindi localized YouTube description. Prefer --hi-description-file for multiline copy.")
    metadata_parser.add_argument("--hi-description-file", default="", help="UTF-8 Hindi description file.")
    metadata_parser.add_argument("--fil-title", default="", help="Filipino localized YouTube title.")
    metadata_parser.add_argument("--fil-description", default="", help="Filipino localized YouTube description. Prefer --fil-description-file for multiline copy.")
    metadata_parser.add_argument("--fil-description-file", default="", help="UTF-8 Filipino description file.")
    metadata_parser.add_argument("--id-title", default="", help="Indonesian localized YouTube title.")
    metadata_parser.add_argument("--id-description", default="", help="Indonesian localized YouTube description. Prefer --id-description-file for multiline copy.")
    metadata_parser.add_argument("--id-description-file", default="", help="UTF-8 Indonesian description file.")
    metadata_parser.add_argument("--pt-title", default="", help="Brazilian Portuguese localized YouTube title.")
    metadata_parser.add_argument("--pt-description", default="", help="Brazilian Portuguese localized YouTube description. Prefer --pt-description-file for multiline copy.")
    metadata_parser.add_argument("--pt-description-file", default="", help="UTF-8 Brazilian Portuguese description file.")
    metadata_parser.add_argument("--pt-pt-title", default="", help="Portuguese Portugal localized YouTube title.")
    metadata_parser.add_argument("--pt-pt-description", default="", help="Portuguese Portugal localized YouTube description. Prefer --pt-pt-description-file for multiline copy.")
    metadata_parser.add_argument("--pt-pt-description-file", default="", help="UTF-8 Portuguese Portugal description file.")
    metadata_parser.add_argument("--fr-title", default="", help="French localized YouTube title.")
    metadata_parser.add_argument("--fr-description", default="", help="French localized YouTube description. Prefer --fr-description-file for multiline copy.")
    metadata_parser.add_argument("--fr-description-file", default="", help="UTF-8 French description file.")
    metadata_parser.add_argument("--de-title", default="", help="German localized YouTube title.")
    metadata_parser.add_argument("--de-description", default="", help="German localized YouTube description. Prefer --de-description-file for multiline copy.")
    metadata_parser.add_argument("--de-description-file", default="", help="UTF-8 German description file.")
    metadata_parser.add_argument("--ar-title", default="", help="Arabic localized YouTube title. Use natural Arabic that is understandable to Egyptian Arabic listeners.")
    metadata_parser.add_argument("--ar-description", default="", help="Arabic localized YouTube description. Prefer --ar-description-file for multiline copy.")
    metadata_parser.add_argument("--ar-description-file", default="", help="UTF-8 Arabic description file.")
    metadata_parser.add_argument("--zh-title", default="", help="Simplified Chinese localized YouTube title.")
    metadata_parser.add_argument("--zh-description", default="", help="Simplified Chinese localized YouTube description. Prefer --zh-description-file for multiline copy.")
    metadata_parser.add_argument("--zh-description-file", default="", help="UTF-8 Simplified Chinese description file.")
    metadata_parser.add_argument("--zh-tw-title", default="", help="Traditional Chinese localized YouTube title.")
    metadata_parser.add_argument("--zh-tw-description", default="", help="Traditional Chinese localized YouTube description. Prefer --zh-tw-description-file for multiline copy.")
    metadata_parser.add_argument("--zh-tw-description-file", default="", help="UTF-8 Traditional Chinese description file.")
    metadata_parser.add_argument("--default-language", default="ko", help="Default upload metadata language: ko, ja, en, es, vi, th, hi, fil, id, pt-BR, pt-PT, fr, de, ar, zh-CN, or zh-TW.")
    metadata_parser.add_argument("--actor", default="openclaw", help="Actor name recorded in metadata approval history.")
    metadata_parser.add_argument("--note", default="", help="Optional approval note.")
    metadata_parser.set_defaults(func=approve_metadata)

    publish_parser = subparsers.add_parser(
        "publish-release",
        help="Publish a rendered release with already-approved metadata through the app YouTube API.",
    )
    publish_parser.add_argument("--release-id", default="", help="Existing release id.")
    publish_parser.add_argument("--release-title", default="", help="Existing release title.")
    publish_parser.add_argument("--youtube-channel-title", default="", help="Connected YouTube channel title.")
    publish_parser.add_argument("--youtube-channel-id", default="", help="Optional explicit YouTube channel id.")
    publish_parser.add_argument("--force-under-target", action="store_true", help="Allow publish even if approved duration is under target.")
    publish_parser.add_argument("--allow-reupload", action="store_true", help="Allow uploading an existing release that already has a YouTube video id. Use only when explicitly requested.")
    publish_parser.add_argument("--no-wait", action="store_true", help="Return immediately after queueing the YouTube upload.")
    publish_parser.add_argument("--wait-timeout-seconds", type=int, default=21600, help="Max wait for YouTube upload. Default: 6 hours.")
    publish_parser.add_argument("--poll-seconds", type=float, default=10.0, help="Polling interval while waiting for upload.")
    publish_parser.add_argument("--actor", default="openclaw:publish-release", help="Actor name recorded in publish history.")
    publish_parser.add_argument("--note", default="", help="Optional publish approval note.")
    publish_parser.set_defaults(func=publish_release)

    lock_start_parser = subparsers.add_parser("openclaw-lock-start", help="Acquire the app-side OpenClaw work lock.")
    lock_start_parser.add_argument("--owner", default="openclaw", help="OpenClaw worker/listener name.")
    lock_start_parser.add_argument("--run-id", default="", help="Stable run id for this OpenClaw task. Defaults to a generated id.")
    lock_start_parser.add_argument("--operation", default="", help="Current operation, for example backlog-producer.")
    lock_start_parser.add_argument("--channel-title", default="", help="Current target channel title.")
    lock_start_parser.add_argument("--release-id", default="", help="Current release id.")
    lock_start_parser.add_argument("--message", default="", help="Short status message.")
    lock_start_parser.set_defaults(func=openclaw_lock_start)

    lock_heartbeat_parser = subparsers.add_parser("openclaw-lock-heartbeat", help="Refresh the app-side OpenClaw work lock.")
    lock_heartbeat_parser.add_argument("--owner", default="openclaw", help="OpenClaw worker/listener name.")
    lock_heartbeat_parser.add_argument("--run-id", required=True, help="Run id returned or chosen at lock start.")
    lock_heartbeat_parser.add_argument("--operation", default="", help="Current operation.")
    lock_heartbeat_parser.add_argument("--channel-title", default="", help="Current target channel title.")
    lock_heartbeat_parser.add_argument("--release-id", default="", help="Current release id.")
    lock_heartbeat_parser.add_argument("--message", default="", help="Short status message.")
    lock_heartbeat_parser.set_defaults(func=openclaw_lock_heartbeat)

    lock_finish_parser = subparsers.add_parser("openclaw-lock-finish", help="Release the app-side OpenClaw work lock.")
    lock_finish_parser.add_argument("--owner", default="openclaw", help="OpenClaw worker/listener name.")
    lock_finish_parser.add_argument("--run-id", required=True, help="Run id returned or chosen at lock start.")
    lock_finish_parser.add_argument("--status", default="completed", help="Finish status such as completed, blocked, or failed.")
    lock_finish_parser.add_argument("--message", default="", help="Short finish message.")
    lock_finish_parser.set_defaults(func=openclaw_lock_finish)

    openclaw_status_parser = subparsers.add_parser("openclaw-status", help="Show app-side OpenClaw lock/runtime status.")
    openclaw_status_parser.set_defaults(func=openclaw_status)

    backlog_status_parser = subparsers.add_parser("openclaw-backlog-status", help="Show app-side backlog scheduler evaluation.")
    backlog_status_parser.set_defaults(func=openclaw_backlog_status)

    youtube_status_parser = subparsers.add_parser("youtube-status", help="Show connected YouTube status/channels as JSON.")
    youtube_status_parser.set_defaults(func=youtube_status)

    backlog_request_parser = subparsers.add_parser("openclaw-backlog-request", help="Ask the app to post one OpenClaw backlog Slack request.")
    backlog_request_parser.add_argument("--reason", default="manual", help="Reason recorded in the Slack request.")
    backlog_request_parser.add_argument("--prompt", default="", help="Optional full prompt override.")
    backlog_request_parser.set_defaults(func=openclaw_backlog_request)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    headers: dict[str, str] = {}
    if os.environ.get("AIMP_API_COOKIE"):
        headers["Cookie"] = os.environ["AIMP_API_COOKIE"]
    if os.environ.get("AIMP_OPENCLAW_SHARED_TOKEN"):
        headers["X-OpenClaw-Token"] = os.environ["AIMP_OPENCLAW_SHARED_TOKEN"]
    try:
        with httpx.Client(base_url=api_base(args.api_base), timeout=120.0, headers=headers) as client:
            result = args.func(client, args)
        print_json(result)
        return 0
    except Exception as exc:  # noqa: BLE001
        print_json({"ok": False, "error": str(exc)})
        return 1


if __name__ == "__main__":
    sys.exit(main())
