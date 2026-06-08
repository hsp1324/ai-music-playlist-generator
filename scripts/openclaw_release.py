#!/usr/bin/env python3
"""OpenClaw-friendly helper for uploading generated release assets.

This script is intended to run on the VM next to the FastAPI app. It uses the
local API by default, bypassing public Google OAuth protection.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from app.utils.track_titles import clean_track_display_title, display_track_titles, upload_track_title
from app.utils.timeline import timeline_from_track_dicts


DEFAULT_API_BASE = "http://127.0.0.1:8000/api"
KNOWN_OAUTH_PUBLIC_HOSTS = {"ai-music.168.107.34.175.sslip.io"}
MAX_AUDIO_UPLOAD_ATTEMPTS = 3
DEFAULT_MIN_PLAYLIST_TRACK_SECONDS = 60
DEFAULT_MAX_PLAYLIST_TRACK_SECONDS = 0
DEFAULT_GENERAL_PLAYLIST_TARGET_SECONDS = 10 * 60
DEFAULT_SCRIPTURE_PLAYLIST_TARGET_SECONDS = 40 * 60
MIN_NORMAL_LOOP_VIDEO_SECONDS = 1.0
LOOP_VIDEO_PROVIDERS = ("gemini", "dreamina", "seedance", "manual", "unknown")
OPENCLAW_PROVIDER_VIDEO_WAIT_SECONDS = 20 * 60
OPENCLAW_PROVIDER_VIDEO_STATE_PATH = "storage/openclaw-provider-video-state.json"
DEFAULT_YOUTUBE_CHANNEL_TITLE = "Soft Hour Radio"
JAPAN_YOUTUBE_CHANNEL_TITLE = "Tokyo Daydream Radio"
SUNDAZE_YOUTUBE_CHANNEL_TITLE = "sundaze"
SOLWAVE_YOUTUBE_CHANNEL_TITLE = "Solwave Radio"
HARUHARU_YOUTUBE_CHANNEL_TITLE = "HaruHaru"
STORYLIGHT_YOUTUBE_CHANNEL_TITLE = "Storylight OST"
CINEMATIC_PULSE_YOUTUBE_CHANNEL_TITLE = "Cinematic Pulse"
CLUB_BLOOM_YOUTUBE_CHANNEL_TITLE = "Club Bloom"
OLD_VERSE_YOUTUBE_CHANNEL_TITLE = "BibliaCanto"
NEW_VERSE_YOUTUBE_CHANNEL_TITLE = "불송"
SIGNAL_ROOM_YOUTUBE_CHANNEL_TITLE = "Signal Room Radio"
SIGNAL_DESK_LEGACY_CHANNEL_TITLE = "Signal Desk Radio"
MIDNIGHT_CUE_LEGACY_CHANNEL_TITLE = "Midnight Cue Radio"
LONG_PLAYLIST_TRACK_ALLOWED_CHANNEL_TITLES = {
    DEFAULT_YOUTUBE_CHANNEL_TITLE,
    CINEMATIC_PULSE_YOUTUBE_CHANNEL_TITLE,
}
SCRIPTURE_PLAYLIST_CHANNEL_TITLES = {
    OLD_VERSE_YOUTUBE_CHANNEL_TITLE,
    NEW_VERSE_YOUTUBE_CHANNEL_TITLE,
}
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
    OLD_VERSE_YOUTUBE_CHANNEL_TITLE: (
        "The Old Verse",
        "Old Verse",
        "Biblia Canto",
    ),
    NEW_VERSE_YOUTUBE_CHANNEL_TITLE: (
        "The New Verse",
        "New Verse",
        "Bulsong",
    ),
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
STILL_IMAGE_LYRICS_OVERLAY_CHANNEL_TITLES = {
    HARUHARU_YOUTUBE_CHANNEL_TITLE,
    SUNDAZE_YOUTUBE_CHANNEL_TITLE,
    SOLWAVE_YOUTUBE_CHANNEL_TITLE,
}
STILL_IMAGE_RENDER_DEFAULT_CHANNEL_TITLES = {
    HARUHARU_YOUTUBE_CHANNEL_TITLE,
    SUNDAZE_YOUTUBE_CHANNEL_TITLE,
    SOLWAVE_YOUTUBE_CHANNEL_TITLE,
    CLUB_BLOOM_YOUTUBE_CHANNEL_TITLE,
}
TOKYO_PHOTO_STILL_IMAGE_LANE_HINTS = (
    "japanese hip-hop",
    "japanese hip hop",
    "j-hip-hop",
    "j hip hop",
    "japanese rap",
    "j-rap",
    "j rap",
    "tokyo rap",
    "shibuya rap",
    "japanese r&b",
    "japanese rnb",
    "j-r&b",
    "j r&b",
    "j-rnb",
    "j rnb",
    "tokyo r&b",
    "tokyo rnb",
    "neo-soul",
    "neo soul",
    "trap-soul",
    "trap soul",
    "boom bap",
    "street-pop",
    "street pop",
    "hip-hop",
    "hiphop",
    "rap",
    "r&b",
    "rnb",
    "일본 힙합",
    "일본 랩",
    "일본 r&b",
    "일본 알앤비",
    "제이힙합",
    "제이랩",
    "도쿄 힙합",
    "시부야 힙합",
    "도쿄 r&b",
    "ヒップホップ",
    "ラップ",
)
TOKYO_ANIMATED_MOVING_LANE_HINTS = (
    "anime",
    "anime-pop",
    "anime pop",
    "anime opening",
    "anime ending",
    "arcade",
    "game-center",
    "game center",
    "city pop",
    "citypop",
    "dance-pop",
    "dance pop",
    "synth-pop",
    "synth pop",
    "pop-rock",
    "pop rock",
    "j-pop",
    "j pop",
    "jpop",
    "애니",
    "애니메이션",
    "시티팝",
    "댄스팝",
    "신스팝",
    "アニメ",
    "シティポップ",
)
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
    "tr",
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
    "japanese hip-hop",
    "japanese hip hop",
    "japanese rap",
    "japanese r&b",
    "japanese rnb",
    "j-hip-hop",
    "j hip hop",
    "j-rap",
    "j rap",
    "j-r&b",
    "j r&b",
    "j-rnb",
    "j rnb",
    "tokyo r&b",
    "tokyo rnb",
    "tokyo rap",
    "shibuya rap",
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
    "일본 힙합",
    "일본 랩",
    "일본 r&b",
    "일본 알앤비",
    "제이힙합",
    "제이랩",
    "도쿄 힙합",
    "시부야 힙합",
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
    "acoustic pop",
    "adult contemporary pop",
    "afrobeats",
    "afro pop",
    "afropop",
    "amapiano",
    "amapiano pop",
    "americana",
    "americana pop",
    "american pop",
    "alt-pop",
    "alt pop",
    "bedroom pop",
    "country pop",
    "disco pop",
    "english pop",
    "english vocal",
    "folk pop",
    "folk-pop",
    "funk pop",
    "indie pop",
    "mainstream pop",
    "pop punk",
    "pop-punk",
    "pop rock",
    "pop-rock",
    "pop song",
    "pop vocal",
    "recession pop",
    "singer-songwriter pop",
    "soft rock",
    "sundaze",
    "uk pop",
    "us pop",
    "y2k pop",
    "western pop",
    "아프로팝",
    "아프로비츠",
    "아메리카나",
    "컨트리 팝",
    "컨트리팝",
    "미국 팝",
    "미국팝",
    "인디 팝",
    "영어 팝",
    "영어팝",
    "팝 록",
    "팝펑크",
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
    "new testament",
    "genesis",
    "matthew",
    "mark",
    "luke",
    "john",
    "acts of the apostles",
    "epistles",
    "revelation",
    "exodus",
    "leviticus",
    "numbers",
    "deuteronomy",
    "psalms",
    "proverbs",
    "isaiah",
    "jeremiah",
    "bible verse music",
    "scripture-inspired songs",
    "ancient biblical music",
    "genesis songs",
    "psalms music",
    "구약",
    "구약성서",
    "신약",
    "신약성서",
    "복음",
    "복음서",
    "마태복음",
    "예수",
    "은혜",
    "찬양곡",
    "워십",
    "창세기",
    "출애굽",
    "시편",
    "잠언",
    "성경 기반",
    "성경 음악",
)
NEW_VERSE_CHANNEL_KEYWORDS = (
    "the new verse",
    "buddhist",
    "buddhism",
    "buddhist scripture",
    "buddhist sutra",
    "sutra song",
    "sutra songs",
    "dhammapada",
    "lotus sutra",
    "heart sutra",
    "prajnaparamita",
    "zen",
    "meditation sutra",
    "mindfulness song",
    "buddhist hip hop",
    "불경",
    "불교",
    "불교 경전",
    "불교 음악",
    "불교 노래",
    "부처",
    "부처님",
    "법구경",
    "금강경",
    "반야심경",
    "화엄경",
    "묘법연화경",
    "선불교",
    "명상",
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
    "acoustic pop",
    "adult contemporary pop",
    "afrobeats",
    "afro pop",
    "afropop",
    "amapiano",
    "amapiano pop",
    "anime pop",
    "anime-pop",
    "anime opening",
    "americana pop",
    "american pop",
    "alt-pop",
    "alt pop",
    "bachata",
    "bedroom pop",
    "country pop",
    "disco pop",
    "english pop",
    "english vocal",
    "folk pop",
    "folk-pop",
    "funk pop",
    "indie pop",
    "j-pop",
    "jpop",
    "japanese pop",
    "k-pop",
    "kpop",
    "korean pop",
    "latin pop",
    "latino pop",
    "mainstream pop",
    "pop punk",
    "pop-punk",
    "pop rock",
    "pop-rock",
    "pop latino",
    "pop song",
    "pop vocal",
    "recession pop",
    "singer-songwriter pop",
    "soft rock",
    "reggaeton",
    "reggaetón",
    "spanish pop",
    "spanish vocal",
    "uk pop",
    "urbano latino",
    "us pop",
    "western pop",
    "y2k pop",
    "아프로팝",
    "아프로비츠",
    "컨트리 팝",
    "컨트리팝",
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


def api_base_needs_browser_cookie(base_url: str) -> bool:
    parsed = urlparse(base_url)
    public_base = os.environ.get("AIMP_PUBLIC_BASE_URL", "").strip()
    public_host = urlparse(public_base).hostname if public_base else ""
    host = parsed.hostname or ""
    return bool(host and (host == public_host or host in KNOWN_OAUTH_PUBLIC_HOSTS))


def validate_api_base_auth(base_url: str, headers: dict[str, str]) -> None:
    if api_base_needs_browser_cookie(base_url) and not headers.get("Cookie"):
        raise RuntimeError(
            "AIMP_LOCAL_API_BASE points at the public Google-login protected URL, but AIMP_API_COOKIE is unset. "
            "Use a direct VM/tunnel API base such as http://127.0.0.1:8000/api on the VM, or set AIMP_API_COOKIE "
            "from a logged-in browser session if you intentionally use the public URL."
        )


def print_json(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def request_json(client: httpx.Client, method: str, path: str, **kwargs) -> Any:
    response = client.request(method, path, **kwargs)
    try:
        payload = response.json()
    except ValueError:
        payload = response.text
    if isinstance(payload, str):
        content_type = response.headers.get("content-type", "")
        trimmed = payload.strip().lower()
        if "text/html" in content_type or trimmed.startswith("<!doctype html") or trimmed.startswith("<html"):
            raise RuntimeError(
                "API returned HTML instead of JSON. AIMP_LOCAL_API_BASE is probably pointing at the public "
                "Google-login protected URL without a valid AIMP_API_COOKIE; use the VM direct/tunnel API."
            )
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


def list_release_summaries(client: httpx.Client) -> list[dict[str, Any]]:
    return request_json(client, "GET", "/playlists/workspaces", params={"compact": "true"})


def list_releases(client: httpx.Client, _args: argparse.Namespace) -> dict[str, Any]:
    releases = list_release_summaries(client)
    return {
        "releases": [
            {
                "id": release["id"],
                "title": release["title"],
                "type": "single" if release["workspace_mode"] == "single_track_video" else "playlist",
                "workflow_state": release["workflow_state"],
                "archived": release.get("hidden", False),
                "tracks": int(release.get("track_count") or len(release.get("tracks") or [])),
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

    youtube_channel_title = getattr(args, "youtube_channel_title", "")
    target_seconds = (
        default_playlist_target_seconds_for_channel(youtube_channel_title)
        if workspace_mode == "playlist" and int(args.target_seconds or 0) <= 0
        else args.target_seconds
    )
    release = request_json(
        client,
        "POST",
        "/playlists/workspaces",
        json={
            "title": args.release_title,
            "target_duration_seconds": target_seconds,
            "workspace_mode": workspace_mode,
            "auto_publish_when_ready": False,
            "description": args.description,
            "cover_prompt": "",
            "dreamina_prompt": "",
            "target_youtube_channel_title": youtube_channel_title,
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
    releases = list_release_summaries(client)
    matches = [release for release in releases if release["title"] == title]
    if not matches:
        raise RuntimeError(f"No release found with exact title: {title}")
    if len(matches) > 1:
        ids = ", ".join(release["id"] for release in matches)
        raise RuntimeError(f"Multiple releases share title {title!r}. Use --release-id. Matches: {ids}")
    return get_release(client, matches[0]["id"])


def resolve_release(client: httpx.Client, *, release_id: str = "", release_title: str = "") -> dict[str, Any]:
    if release_id:
        return get_release(client, release_id)
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


def _release_channel_title(release: dict[str, Any] | None) -> str:
    if not release:
        return ""
    meta = release.get("metadata_json") if isinstance(release.get("metadata_json"), dict) else {}
    return str(
        release.get("target_youtube_channel_title")
        or release.get("youtube_channel_title")
        or meta.get("target_youtube_channel_title")
        or meta.get("youtube_channel_title")
        or meta.get("openclaw_lock_channel_title")
        or ""
    ).strip()


def playlist_track_max_duration_exempt(
    args: argparse.Namespace,
    *,
    release: dict[str, Any] | None = None,
) -> bool:
    explicit_channel = str(getattr(args, "youtube_channel_title", "") or "").strip()
    release_channel = _release_channel_title(release)
    channel_title = explicit_channel or release_channel
    if not channel_title and release is None:
        channel_title = infer_youtube_channel_title(args)
    return channel_title in LONG_PLAYLIST_TRACK_ALLOWED_CHANNEL_TITLES


def min_playlist_track_seconds(args: argparse.Namespace) -> int:
    return max(int(getattr(args, "min_track_seconds", DEFAULT_MIN_PLAYLIST_TRACK_SECONDS) or 0), 0)


def require_playlist_track_duration(
    track: dict[str, Any],
    *,
    args: argparse.Namespace,
    context: str,
    release: dict[str, Any] | None = None,
) -> None:
    duration_seconds = int(track.get("duration_seconds") or 0)
    if duration_seconds <= 0:
        return
    title = track.get("title") or track.get("id") or "unknown track"

    min_seconds = min_playlist_track_seconds(args)
    if not bool(getattr(args, "allow_short_track", False)) and min_seconds > 0 and duration_seconds < min_seconds:
        raise RuntimeError(
            f"{context} rejected `{title}` because its duration is {format_timestamp(duration_seconds)}. "
            f"The configured minimum accepted playlist track length is {format_timestamp(min_seconds)}. "
            "Use --allow-short-track only when the human explicitly accepts a shorter track."
        )

    max_seconds = max_playlist_track_seconds(args)
    if (
        not playlist_track_max_duration_exempt(args, release=release)
        and not bool(getattr(args, "allow_long_track", False))
        and max_seconds > 0
        and duration_seconds > max_seconds
    ):
        raise RuntimeError(
            f"{context} rejected `{title}` because its duration is {format_timestamp(duration_seconds)}. "
            f"Playlist tracks must be {format_timestamp(max_seconds)} or shorter because --max-track-seconds was set. "
            "Regenerate a shorter Suno track or pass --allow-long-track only when the human explicitly accepts that cap override."
        )


def require_release_playlist_track_durations(
    release: dict[str, Any],
    *,
    args: argparse.Namespace,
    context: str,
) -> None:
    for track in release.get("tracks") or []:
        require_playlist_track_duration(track, args=args, context=context, release=release)


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
        release = get_release(client, args.release_id)
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
            require_playlist_track_duration(
                track,
                args=args,
                context="upload-audio playlist auto-approval",
                release=release,
            )
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
    target_duration_seconds: int | None = None,
    description: str = "",
    youtube_channel_title: str = "",
) -> dict[str, Any]:
    resolved_target_duration_seconds = (
        target_duration_seconds
        if target_duration_seconds and target_duration_seconds > 0
        else default_playlist_target_seconds_for_channel(youtube_channel_title)
    )
    return request_json(
        client,
        "POST",
        "/playlists/workspaces",
        json={
            "title": title,
            "target_duration_seconds": resolved_target_duration_seconds,
            "workspace_mode": "playlist",
            "auto_publish_when_ready": False,
            "description": description or "Automatic private playlist release created by OpenClaw.",
            "cover_prompt": "",
            "dreamina_prompt": "",
            "target_youtube_channel_title": youtube_channel_title,
        },
    )


def get_release(client: httpx.Client, release_id: str) -> dict[str, Any]:
    try:
        return request_json(client, "GET", f"/playlists/workspaces/{release_id}")
    except RuntimeError as exc:
        if str(exc).startswith("404 "):
            raise RuntimeError(f"No release found with id: {release_id}") from exc
        raise


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
        for canonical_title, aliases in CHANNEL_TITLE_ALIASES.items():
            if explicit_title == canonical_title or explicit_title.lower() in {alias.lower() for alias in aliases}:
                return canonical_title
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


def is_bulsong_channel_title(value: str | None) -> bool:
    title = str(value or "").strip()
    if not title:
        return False
    aliases = {NEW_VERSE_YOUTUBE_CHANNEL_TITLE.lower()}
    aliases.update(alias.lower() for alias in CHANNEL_TITLE_ALIASES.get(NEW_VERSE_YOUTUBE_CHANNEL_TITLE, ()))
    return title.lower() in aliases


def is_scripture_playlist_channel_title(value: str | None) -> bool:
    title = str(value or "").strip()
    if not title:
        return False
    aliases = {channel.lower() for channel in SCRIPTURE_PLAYLIST_CHANNEL_TITLES}
    for channel in SCRIPTURE_PLAYLIST_CHANNEL_TITLES:
        aliases.update(alias.lower() for alias in CHANNEL_TITLE_ALIASES.get(channel, ()))
    return title.lower() in aliases


def default_playlist_target_seconds_for_channel(value: str | None) -> int:
    if is_scripture_playlist_channel_title(value):
        return DEFAULT_SCRIPTURE_PLAYLIST_TARGET_SECONDS
    return DEFAULT_GENERAL_PLAYLIST_TARGET_SECONDS


def is_storylight_channel_title(value: str | None) -> bool:
    title = str(value or "").strip()
    if not title:
        return False
    aliases = {STORYLIGHT_YOUTUBE_CHANNEL_TITLE.lower()}
    aliases.update(alias.lower() for alias in CHANNEL_TITLE_ALIASES.get(STORYLIGHT_YOUTUBE_CHANNEL_TITLE, ()))
    return title.lower() in aliases


def is_still_image_lyrics_overlay_channel_title(value: str | None) -> bool:
    title = str(value or "").strip()
    if not title:
        return False
    aliases = {channel.lower() for channel in STILL_IMAGE_LYRICS_OVERLAY_CHANNEL_TITLES}
    for channel in STILL_IMAGE_LYRICS_OVERLAY_CHANNEL_TITLES:
        aliases.update(alias.lower() for alias in CHANNEL_TITLE_ALIASES.get(channel, ()))
    return title.lower() in aliases


def is_still_image_render_default_channel_title(value: str | None) -> bool:
    title = str(value or "").strip()
    if not title:
        return False
    aliases = {channel.lower() for channel in STILL_IMAGE_RENDER_DEFAULT_CHANNEL_TITLES}
    for channel in STILL_IMAGE_RENDER_DEFAULT_CHANNEL_TITLES:
        aliases.update(alias.lower() for alias in CHANNEL_TITLE_ALIASES.get(channel, ()))
    return title.lower() in aliases


def is_tokyo_daydream_channel_title(value: str | None) -> bool:
    title = str(value or "").strip()
    if not title:
        return False
    return title.lower() == JAPAN_YOUTUBE_CHANNEL_TITLE.lower()


def release_youtube_channel_title(release: dict[str, Any], fallback: str = "") -> str:
    meta = release.get("metadata_json") if isinstance(release.get("metadata_json"), dict) else {}
    return str(
        release.get("target_youtube_channel_title")
        or release.get("youtube_channel_title")
        or meta.get("target_youtube_channel_title")
        or meta.get("youtube_channel_title")
        or fallback
        or ""
    ).strip()


def release_search_values(args: argparse.Namespace, release: dict[str, Any] | None = None) -> list[str]:
    values = [
        getattr(args, "release_title", ""),
        getattr(args, "description", ""),
        getattr(args, "prompt", ""),
        getattr(args, "style", ""),
        getattr(args, "tags", ""),
        getattr(args, "youtube_channel_title", ""),
    ]
    if release:
        meta = release.get("metadata_json") if isinstance(release.get("metadata_json"), dict) else {}
        values.extend(
            [
                release.get("title", ""),
                release.get("description", ""),
                release.get("youtube_title", ""),
                release.get("youtube_channel_title", ""),
                release.get("target_youtube_channel_title", ""),
                meta.get("description", ""),
                meta.get("youtube_title", ""),
                meta.get("youtube_channel_title", ""),
                meta.get("target_youtube_channel_title", ""),
                meta.get("channel_style_lane", ""),
                meta.get("channel_broad_genre", ""),
            ]
        )
        for track in release.get("tracks") or []:
            if not isinstance(track, dict):
                continue
            track_meta = track.get("metadata_json") if isinstance(track.get("metadata_json"), dict) else {}
            values.extend(
                [
                    track.get("title", ""),
                    track.get("prompt", ""),
                    track_meta.get("style", ""),
                    track_meta.get("tags", ""),
                    track_meta.get("genre", ""),
                    track_meta.get("genre_tokens", ""),
                    track_meta.get("ai_genre_tokens", ""),
                ]
            )
    return [str(value or "") for value in values]


def should_use_tokyo_photo_still_image_render(
    args: argparse.Namespace,
    *,
    release: dict[str, Any] | None = None,
    channel_title: str = "",
) -> bool:
    title = release_youtube_channel_title(release, fallback=channel_title) if release else channel_title
    if not is_tokyo_daydream_channel_title(title):
        return False
    haystack = " ".join(release_search_values(args, release)).lower()
    if not haystack:
        return False
    if any(hint in haystack for hint in TOKYO_PHOTO_STILL_IMAGE_LANE_HINTS):
        return True
    return False


def normalize_render_source_mode_arg(args: argparse.Namespace) -> str:
    mode = str(getattr(args, "video_render_source_mode", "auto") or "auto").strip().lower().replace("-", "_")
    if mode in {"still", "image", "cover"}:
        return "still_image"
    if mode in {"loop", "video"}:
        return "loop_video"
    if mode in {"auto", "loop_video", "still_image"}:
        return mode
    return "auto"


def should_use_still_image_render(
    args: argparse.Namespace,
    *,
    release: dict[str, Any] | None = None,
    channel_title: str = "",
) -> bool:
    mode = normalize_render_source_mode_arg(args)
    if mode == "loop_video":
        return False
    if mode == "still_image" or bool(getattr(args, "allow_still_image_video", False)):
        return True
    title = release_youtube_channel_title(release, fallback=channel_title) if release else channel_title
    return is_still_image_render_default_channel_title(title) or should_use_tokyo_photo_still_image_render(
        args,
        release=release,
        channel_title=title,
    )


def effective_video_render_source_mode(
    args: argparse.Namespace,
    *,
    release: dict[str, Any] | None = None,
    channel_title: str = "",
) -> str:
    mode = normalize_render_source_mode_arg(args)
    if mode == "auto" and should_use_still_image_render(args, release=release, channel_title=channel_title):
        return "still_image"
    return mode


def release_youtube_channel_id(release: dict[str, Any]) -> str:
    meta = release.get("metadata_json") if isinstance(release.get("metadata_json"), dict) else {}
    return str(release.get("youtube_channel_id") or meta.get("youtube_channel_id") or "").strip()


def require_video_render_source_allowed(
    *,
    release: dict[str, Any],
    channel_title: str,
    args: argparse.Namespace,
) -> None:
    render_source_mode = normalize_render_source_mode_arg(args)
    still_image_requested = bool(getattr(args, "allow_still_image_video", False) or render_source_mode == "still_image")
    if still_image_requested and is_storylight_channel_title(release_youtube_channel_title(release, fallback=channel_title)):
        raise RuntimeError(
            "Storylight OST requires a provider-generated loop video. "
            "Upload the loop video first and render with --video-render-source-mode loop_video or auto."
        )


def should_enable_lyrics_overlay_for_release(
    args: argparse.Namespace,
    *,
    release: dict[str, Any],
    channel_title: str = "",
) -> bool:
    return bool(
        getattr(args, "lyrics_overlay", False)
        or should_use_tokyo_photo_still_image_render(args, release=release, channel_title=channel_title)
        or is_still_image_lyrics_overlay_channel_title(
            release_youtube_channel_title(release, fallback=channel_title)
        )
    )


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
        "rule": "Pick the channel first, then read that channel's concept_doc for next-release planning and profile_doc for cover, thumbnail, loop-video, and still-image render visuals. Do not mix signatures across channels.",
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


def track_reuse_summary(track: dict[str, Any]) -> dict[str, Any]:
    meta = track.get("metadata_json") if isinstance(track.get("metadata_json"), dict) else {}
    return {
        "id": track.get("id"),
        "title": track.get("title"),
        "status": track.get("status"),
        "duration_seconds": track.get("duration_seconds"),
        "user_rating": track.get("user_rating") or meta.get("user_rating") or "",
        "style": track.get("style") or meta.get("style") or "",
        "tags": meta.get("tags") or "",
        "reuse_count": meta.get("playlist_reuse_count") or 0,
        "reused_seconds": meta.get("playlist_reused_seconds") or 0,
        "last_reused_in_playlist_id": meta.get("playlist_last_reused_in_playlist_id") or "",
        "audio_path": track.get("audio_path"),
        "created_at": track.get("created_at"),
        "updated_at": track.get("updated_at"),
    }


def track_duration_seconds_value(track: dict[str, Any]) -> int:
    try:
        return int(track.get("duration_seconds") or 0)
    except (TypeError, ValueError):
        return 0


def search_tracks(client: httpx.Client, args: argparse.Namespace) -> dict[str, Any]:
    requested_limit = max(int(args.limit or 0), 0)
    min_track_seconds = max(int(getattr(args, "min_track_seconds", 0) or 0), 0)
    filter_short_tracks = bool(min_track_seconds and not getattr(args, "allow_short_track", False))
    api_limit = min(max(requested_limit * 4, requested_limit), 1000) if filter_short_tracks and requested_limit else requested_limit
    params: dict[str, Any] = {
        "limit": api_limit,
        "compact": str(not args.full).lower(),
    }
    if args.q:
        params["q"] = args.q
    if args.status_filter:
        params["status_filter"] = args.status_filter
    if args.user_rating:
        params["user_rating"] = args.user_rating
    tracks = request_json(client, "GET", "/tracks", params=params)
    if filter_short_tracks:
        tracks = [track for track in tracks if track_duration_seconds_value(track) >= min_track_seconds]
    if requested_limit:
        tracks = tracks[:requested_limit]
    return {
        "ok": True,
        "action": "search-tracks",
        "query": args.q,
        "status_filter": args.status_filter,
        "count": len(tracks),
        "tracks": tracks if args.full else [track_reuse_summary(track) for track in tracks],
        "next": "Attach selected existing tracks with `scripts/openclaw-release reuse-track --release-id RELEASE_ID --track-id TRACK_ID`.",
    }


def reuse_track(client: httpx.Client, args: argparse.Namespace) -> dict[str, Any]:
    release = resolve_release(client, release_id=args.release_id, release_title=args.release_title)
    if release.get("workspace_mode") != "playlist":
        raise RuntimeError("reuse-track requires a Playlist Release.")

    attached_tracks = []
    for track_id in args.track_id:
        track = approve_track_to_playlist(
            client,
            track_id=track_id,
            release_id=release["id"],
            actor=args.actor,
        )
        attached_tracks.append(track_reuse_summary(track))

    release = get_release(client, release["id"])
    return {
        "ok": True,
        "action": "reuse-track",
        "release": {
            "id": release["id"],
            "title": release["title"],
            "workflow_state": release["workflow_state"],
            "track_count": int(release.get("track_count") or len(release.get("tracks") or [])),
            "actual_duration_seconds": release.get("actual_duration_seconds", 0),
            "target_duration_seconds": release.get("target_duration_seconds", 0),
            "target_youtube_channel_title": release.get("target_youtube_channel_title"),
        },
        "tracks": attached_tracks,
        "next": "After enough same-lane tracks are attached, upload visuals, render audio, approve cover, and render video.",
    }


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

    explicit_channel_title = str(getattr(args, "youtube_channel_title", "") or "").strip()
    release_channel_title = release_youtube_channel_title(release)
    youtube_channel_title = (
        infer_youtube_channel_title(args)
        if explicit_channel_title or not release_channel_title
        else release_channel_title
    )
    channel_id = resolve_youtube_channel_id(
        client,
        title=youtube_channel_title,
        channel_id=args.youtube_channel_id or release_youtube_channel_id(release),
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
            "allow_reupload": args.allow_reupload,
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


def openclaw_scripture_status(client: httpx.Client, _args: argparse.Namespace) -> dict[str, Any]:
    return request_json(client, "GET", "/openclaw/scripture/status")


def youtube_status(client: httpx.Client, _args: argparse.Namespace) -> dict[str, Any]:
    return request_json(client, "GET", "/youtube/status", headers={"Accept": "application/json"})


def _provider_video_state_path() -> Path:
    return Path(
        os.environ.get("AIMP_OPENCLAW_PROVIDER_VIDEO_STATE_PATH")
        or OPENCLAW_PROVIDER_VIDEO_STATE_PATH
    ).expanduser().resolve()


def _provider_video_now() -> tuple[float, str]:
    now = time.time()
    return now, datetime.fromtimestamp(now, tz=timezone.utc).isoformat()


def _read_provider_video_state() -> dict[str, Any]:
    path = _provider_video_state_path()
    if not path.exists():
        return {"jobs": {}}
    try:
        with path.open("r", encoding="utf-8") as handle:
            state = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {"jobs": {}}
    if not isinstance(state, dict):
        return {"jobs": {}}
    jobs = state.get("jobs")
    if not isinstance(jobs, dict):
        state["jobs"] = {}
    return state


def _write_provider_video_state(state: dict[str, Any]) -> None:
    path = _provider_video_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    with temporary_path.open("w", encoding="utf-8") as handle:
        json.dump(state, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    temporary_path.replace(path)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _provider_video_reference(args: argparse.Namespace) -> dict[str, Any]:
    release_id = str(args.release_id or "").strip()
    if not release_id:
        raise ValueError("--release-id is required.")
    first_frame_path = Path(args.first_frame).expanduser().resolve()
    if not first_frame_path.exists() or not first_frame_path.is_file():
        raise ValueError(f"--first-frame does not exist: {first_frame_path}")
    first_frame_sha256 = _file_sha256(first_frame_path)
    key = f"{release_id}:{first_frame_sha256}"
    return {
        "key": key,
        "release_id": release_id,
        "first_frame_path": str(first_frame_path),
        "first_frame_sha256": first_frame_sha256,
    }


def _provider_video_active_job(
    state: dict[str, Any],
    key: str,
    *,
    now: float,
) -> tuple[dict[str, Any] | None, int, int]:
    job = dict((state.get("jobs") or {}).get(key) or {})
    if str(job.get("status") or "") != "running":
        return None, 0, 0
    try:
        started_at_epoch = float(job.get("started_at_epoch") or 0)
    except (TypeError, ValueError):
        started_at_epoch = 0
    elapsed_seconds = max(int(now - started_at_epoch), 0) if started_at_epoch else 0
    wait_seconds = max(int(job.get("wait_seconds") or OPENCLAW_PROVIDER_VIDEO_WAIT_SECONDS), 1)
    remaining_seconds = max(wait_seconds - elapsed_seconds, 0)
    return job, elapsed_seconds, remaining_seconds


def provider_video_start(_client: httpx.Client, args: argparse.Namespace) -> dict[str, Any]:
    reference = _provider_video_reference(args)
    provider = str(args.provider or "").strip().lower()
    if provider not in {"gemini", "dreamina", "seedance"}:
        raise ValueError("--provider must be gemini, dreamina, or seedance.")
    now, now_iso = _provider_video_now()
    state = _read_provider_video_state()
    jobs = state.setdefault("jobs", {})
    active_job, elapsed_seconds, remaining_seconds = _provider_video_active_job(
        state,
        reference["key"],
        now=now,
    )
    previous_job = None
    if active_job and remaining_seconds > 0 and not args.force:
        active_provider = active_job.get("provider")
        raise RuntimeError(
            "Provider video generation is already running for this release and first frame: "
            f"{active_provider} started {elapsed_seconds}s ago. Wait {remaining_seconds}s more "
            "before starting Dreamina/Seedance or another provider."
        )
    if active_job and remaining_seconds <= 0:
        previous_job = {
            **active_job,
            "status": "timed_out",
            "timed_out_at": now_iso,
            "elapsed_seconds": elapsed_seconds,
            "timeout_reason": "fallback_provider_started_after_wait",
        }

    job = {
        **reference,
        "provider": provider,
        "status": "running",
        "started_at": now_iso,
        "started_at_epoch": now,
        "wait_seconds": OPENCLAW_PROVIDER_VIDEO_WAIT_SECONDS,
        "note": str(args.note or "").strip(),
    }
    if previous_job:
        job["previous_timed_out_job"] = previous_job
    jobs[reference["key"]] = job
    state["updated_at"] = now_iso
    _write_provider_video_state(state)
    return {
        "ok": True,
        "action": "provider-video-start",
        "job": job,
        "previous_timed_out_job": previous_job,
        "state_path": str(_provider_video_state_path()),
    }


def provider_video_status(_client: httpx.Client, args: argparse.Namespace) -> dict[str, Any]:
    reference = _provider_video_reference(args)
    now, now_iso = _provider_video_now()
    state = _read_provider_video_state()
    job = dict((state.get("jobs") or {}).get(reference["key"]) or {})
    active_job, elapsed_seconds, remaining_seconds = _provider_video_active_job(
        state,
        reference["key"],
        now=now,
    )
    return {
        "ok": True,
        "action": "provider-video-status",
        "checked_at": now_iso,
        "release_id": reference["release_id"],
        "first_frame_sha256": reference["first_frame_sha256"],
        "job": job or None,
        "running": active_job is not None,
        "elapsed_seconds": elapsed_seconds,
        "wait_remaining_seconds": remaining_seconds,
        "fallback_allowed": active_job is None or remaining_seconds <= 0,
    }


def provider_video_finish(_client: httpx.Client, args: argparse.Namespace) -> dict[str, Any]:
    reference = _provider_video_reference(args)
    status = str(args.status or "").strip().lower()
    if status not in {"succeeded", "failed", "timed_out", "cancelled"}:
        raise ValueError("--status must be succeeded, failed, timed_out, or cancelled.")
    provider = str(args.provider or "").strip().lower()
    if provider not in {"gemini", "dreamina", "seedance"}:
        raise ValueError("--provider must be gemini, dreamina, or seedance.")
    now, now_iso = _provider_video_now()
    state = _read_provider_video_state()
    jobs = state.setdefault("jobs", {})
    job = dict(jobs.get(reference["key"]) or reference)
    if job.get("provider") and job.get("provider") != provider and not args.force:
        raise RuntimeError(
            f"Active provider video job is for {job.get('provider')}, not {provider}. "
            "Pass --force only if you are intentionally correcting stale state."
        )
    try:
        started_at_epoch = float(job.get("started_at_epoch") or now)
    except (TypeError, ValueError):
        started_at_epoch = now
    job.update(
        {
            **reference,
            "provider": provider,
            "status": status,
            "finished_at": now_iso,
            "elapsed_seconds": max(int(now - started_at_epoch), 0),
            "output_video_path": str(Path(args.output_video).expanduser().resolve())
            if args.output_video
            else str(job.get("output_video_path") or ""),
            "note": str(args.note or job.get("note") or "").strip(),
        }
    )
    jobs[reference["key"]] = job
    state["updated_at"] = now_iso
    _write_provider_video_state(state)
    return {
        "ok": True,
        "action": "provider-video-finish",
        "job": job,
        "state_path": str(_provider_video_state_path()),
    }


def openclaw_backlog_request(client: httpx.Client, args: argparse.Namespace) -> dict[str, Any]:
    return request_json(
        client,
        "POST",
        "/openclaw/backlog/request",
        json={"reason": args.reason, "prompt": args.prompt},
    )


def openclaw_scripture_reserve(client: httpx.Client, args: argparse.Namespace) -> dict[str, Any]:
    return request_json(
        client,
        "POST",
        "/openclaw/scripture/reserve",
        json={
            "channel_title": args.channel_title,
            "release_id": args.release_id,
            "title": args.title,
            "notes": args.notes,
            "passage_range": args.passage_range,
        },
    )


def openclaw_scripture_complete(client: httpx.Client, args: argparse.Namespace) -> dict[str, Any]:
    return request_json(
        client,
        "POST",
        "/openclaw/scripture/complete",
        json={
            "channel_title": args.channel_title,
            "passage_range": args.passage_range,
            "status": args.status,
            "release_id": args.release_id,
            "youtube_video_id": args.youtube_video_id,
            "title": args.title,
            "notes": args.notes,
            "next_start": args.next_start,
        },
    )


def openclaw_scripture_fail(client: httpx.Client, args: argparse.Namespace) -> dict[str, Any]:
    return request_json(
        client,
        "POST",
        "/openclaw/scripture/fail",
        json={
            "channel_title": args.channel_title,
            "passage_range": args.passage_range,
            "release_id": args.release_id,
            "title": args.title,
            "reason": args.reason,
        },
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
    youtube_channel_title = infer_youtube_channel_title(args)
    allow_cover_as_thumbnail = bool(args.allow_cover_as_thumbnail or is_bulsong_channel_title(youtube_channel_title))
    if not cover_path and not args.release_id and not args.allow_generated_draft_cover:
        raise RuntimeError(
            "auto-publish-playlist requires --cover when creating a new Playlist Release. "
            "Generate a final 16:9 cover image first, then pass --cover ABSOLUTE_FINAL_COVER_IMAGE_PATH."
        )
    if not thumbnail_path and not args.release_id and not allow_cover_as_thumbnail:
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
    still_image_render = should_use_still_image_render(args, channel_title=youtube_channel_title)
    if not loop_video_path and not args.release_id and not still_image_render:
        raise RuntimeError(
            "auto-publish-playlist requires --loop-video when creating a new moving-video Playlist Release. "
            "Generate and download the short Gemini/Dreamina/Seedance MP4 first, then pass --loop-video ABSOLUTE_LOOP_VIDEO_MP4. "
            "Pass --allow-still-image-video only for HaruHaru/sundaze/Solwave Radio/Tokyo Daydream photorealistic hip-hop/R&B/Club Bloom still-image renders or when the human explicitly accepts a still-image fallback video."
        )
    require_normal_loop_video_duration(loop_video_path, args, context="auto-publish-playlist")

    release = (
        get_release(client, args.release_id)
        if args.release_id
        else create_playlist_release(
            client,
            title=args.release_title or file_stem(audio_paths[0]),
            target_duration_seconds=args.target_seconds if int(args.target_seconds or 0) > 0 else None,
            description=args.description,
            youtube_channel_title=youtube_channel_title,
        )
    )
    if release["workspace_mode"] != "playlist":
        raise RuntimeError("auto-publish-playlist requires a Playlist Release, not a Single Release.")
    release_channel_title = release_youtube_channel_title(release, fallback=youtube_channel_title)
    still_image_render = should_use_still_image_render(args, release=release, channel_title=release_channel_title)
    video_render_source_mode = effective_video_render_source_mode(args, release=release, channel_title=release_channel_title)
    allow_cover_as_thumbnail = bool(allow_cover_as_thumbnail or is_bulsong_channel_title(release_channel_title))
    require_reupload_confirmation(args, release, action="auto-publish-playlist")
    if not cover_path and not release_has_uploaded_cover(release) and not args.allow_generated_draft_cover:
        raise RuntimeError(
            "auto-publish-playlist requires a final 16:9 cover image before YouTube upload. "
            "Pass --cover ABSOLUTE_FINAL_COVER_IMAGE_PATH, or upload a final cover to the release first. "
            "Only pass --allow-generated-draft-cover if the human explicitly accepts a placeholder cover."
        )
    if not thumbnail_path and not release_has_uploaded_thumbnail(release) and not allow_cover_as_thumbnail:
        raise RuntimeError(
            "auto-publish-playlist requires a YouTube thumbnail image before YouTube upload. "
            "Pass --thumbnail ABSOLUTE_THUMBNAIL_IMAGE_PATH, or upload a final thumbnail to the release first. "
            "Only pass --allow-cover-as-thumbnail if the human explicitly wants to reuse the video cover as the YouTube thumbnail."
        )
    if not loop_video_path and not release_has_uploaded_loop_video(release) and not still_image_render:
        raise RuntimeError(
            "auto-publish-playlist requires an uploaded loop video before video render for moving-video releases. "
            "Pass --loop-video ABSOLUTE_LOOP_VIDEO_MP4, or upload a loop video to the release first. "
            "Pass --allow-still-image-video only for HaruHaru/sundaze/Solwave Radio/Tokyo Daydream photorealistic hip-hop/R&B/Club Bloom still-image renders or when the human explicitly accepts a still-image fallback video."
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
            require_playlist_track_duration(track, args=args, context="auto-publish-playlist", release=release)
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
    elif allow_cover_as_thumbnail:
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
    require_video_render_source_allowed(
        release=release,
        channel_title=release_channel_title,
        args=args,
    )
    release = request_json(
        client,
        "POST",
        f"/playlists/{release['id']}/video/render",
        json={
            "actor": args.actor,
            "allow_still_image_fallback": still_image_render,
            "video_spectrum_overlay_style": args.video_spectrum_overlay_style,
            "video_render_resolution": args.video_render_resolution,
            "video_render_source_mode": video_render_source_mode,
            "video_lyrics_overlay_enabled": should_enable_lyrics_overlay_for_release(
                args,
                release=release,
                channel_title=release_channel_title,
            ),
            "video_lyrics_overlay_style": getattr(args, "lyrics_overlay_style", "auto"),
            "video_lyrics_alignment_mode": getattr(args, "lyrics_alignment_mode", "whisper"),
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
            "allow_reupload": args.allow_reupload,
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
    youtube_channel_title = infer_youtube_channel_title(args)
    allow_cover_as_thumbnail = bool(args.allow_cover_as_thumbnail or is_bulsong_channel_title(youtube_channel_title))
    if not cover_path and not args.release_id and not args.allow_generated_draft_cover:
        raise RuntimeError(
            "auto-publish-single requires --cover when creating a new Single Release. "
            "Generate a final 16:9 cover/first-frame image without channel names or logos first, then pass --cover ABSOLUTE_FINAL_COVER_IMAGE_PATH."
        )
    if not thumbnail_path and not args.release_id and not allow_cover_as_thumbnail:
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
    still_image_render = should_use_still_image_render(args, channel_title=youtube_channel_title)
    if not loop_video_path and not args.release_id and not still_image_render:
        raise RuntimeError(
            "auto-publish-single requires --loop-video when creating a new moving-video Single Release. "
            "Generate and download the short Gemini/Dreamina/Seedance MP4 first, then pass --loop-video ABSOLUTE_LOOP_VIDEO_MP4. "
            "For HaruHaru/sundaze/Solwave Radio/Tokyo Daydream photorealistic hip-hop/R&B/Club Bloom still-image renders, pass --allow-still-image-video --video-render-source-mode still_image instead."
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
    release_channel_title = release_youtube_channel_title(release, fallback=youtube_channel_title)
    still_image_render = should_use_still_image_render(args, release=release, channel_title=release_channel_title)
    video_render_source_mode = effective_video_render_source_mode(args, release=release, channel_title=release_channel_title)
    allow_cover_as_thumbnail = bool(allow_cover_as_thumbnail or is_bulsong_channel_title(release_channel_title))
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
    if not thumbnail_path and not release_has_uploaded_thumbnail(release) and not allow_cover_as_thumbnail:
        raise RuntimeError(
            "auto-publish-single requires a YouTube thumbnail image before YouTube upload. "
            "Pass --thumbnail ABSOLUTE_THUMBNAIL_IMAGE_PATH, or upload a final thumbnail to the release first."
        )
    if not loop_video_path and not release_has_uploaded_loop_video(release) and not still_image_render:
        raise RuntimeError(
            "auto-publish-single requires an uploaded loop video before video render for moving-video releases. "
            "Pass --loop-video ABSOLUTE_LOOP_VIDEO_MP4, or upload a loop video to the release first. "
            "Pass --allow-still-image-video only for HaruHaru/sundaze/Solwave Radio/Tokyo Daydream photorealistic hip-hop/R&B/Club Bloom still-image renders or when the human explicitly accepts a still-image fallback video."
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
    elif allow_cover_as_thumbnail:
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
    require_video_render_source_allowed(
        release=release,
        channel_title=release_channel_title,
        args=args,
    )
    release = request_json(
        client,
        "POST",
        f"/playlists/{release['id']}/video/render",
        json={
            "actor": args.actor,
            "allow_still_image_fallback": still_image_render,
            "video_spectrum_overlay_style": args.video_spectrum_overlay_style,
            "video_render_resolution": args.video_render_resolution,
            "video_render_source_mode": video_render_source_mode,
            "video_lyrics_overlay_enabled": should_enable_lyrics_overlay_for_release(
                args,
                release=release,
                channel_title=release_channel_title,
            ),
            "video_lyrics_overlay_style": getattr(args, "lyrics_overlay_style", "auto"),
            "video_lyrics_alignment_mode": getattr(args, "lyrics_alignment_mode", "whisper"),
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
            "allow_reupload": args.allow_reupload,
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
    release_channel_title = release_youtube_channel_title(
        release,
        fallback=str(getattr(args, "youtube_channel_title", "") or ""),
    )
    still_image_render = should_use_still_image_render(args, release=release, channel_title=release_channel_title)
    video_render_source_mode = effective_video_render_source_mode(
        args,
        release=release,
        channel_title=release_channel_title,
    )
    require_video_render_source_allowed(
        release=release,
        channel_title=release_channel_title,
        args=args,
    )
    release = request_json(
        client,
        "POST",
        f"/playlists/{release['id']}/video/render",
        json={
            "actor": args.actor,
            "allow_still_image_fallback": still_image_render,
            "video_spectrum_overlay_style": args.video_spectrum_overlay_style,
            "video_render_resolution": args.video_render_resolution,
            "video_render_source_mode": video_render_source_mode,
            "video_lyrics_overlay_enabled": should_enable_lyrics_overlay_for_release(
                args,
                release=release,
                channel_title=release_channel_title,
            ),
            "video_lyrics_overlay_style": getattr(args, "lyrics_overlay_style", "auto"),
            "video_lyrics_alignment_mode": getattr(args, "lyrics_alignment_mode", "whisper"),
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
            "video_render_resolution": release.get("video_render_resolution"),
            "video_render_source_mode": release.get("video_render_source_mode"),
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
            "For Japan/J-pop/Tokyo Daydream Radio releases, write localized timeline rows as follows: Korean description uses Japanese title plus Korean translation in parentheses, Japanese description uses Japanese title only, and English, Spanish, Vietnamese, Thai, Hindi, Filipino, Indonesian, Turkish, Brazilian Portuguese, European Portuguese, French, German, Arabic, Simplified Chinese, and Traditional Chinese descriptions use translated title text only. For Tokyo Daydream titles, name the truthful lane when useful, including Japanese hip-hop, J-rap, Tokyo R&B, city-pop, anime-pop, synth-pop, dance-pop, or pop-rock; do not over-emphasize Japanese language labels. "
            "For every localized video title, use natural transcreation for that language rather than literal translation. If direct translation sounds awkward, weak, too long, or less clickable, change the wording, order, or exact hook while keeping the release identity, genre/lane, and use case truthful. For sundaze/English/American pop playlist releases, localized video titles may be adapted per language; keep English track titles in every localized timestamped timeline row and translate only the surrounding prose, use-case text, and hashtags. sundaze titles must name one clear release-level genre lane when accurate, such as Pop R&B, pop hip-hop, dance-pop, synth-pop, pop-rock, country pop, Americana pop, indie pop, bedroom pop, alt-pop, singer-songwriter pop, folk-pop, soft rock, pop-punk, Y2K/recession pop, disco/funk pop, Afrobeats, Afropop, or Amapiano-pop, instead of generic English pop wording. "
            "For HaruHaru/K-pop releases, write original Korean titles and Korean lyrics by default. Localized descriptions may translate track titles naturally, but timestamps and row order must stay exactly the same. HaruHaru Korean/default titles should be click-led: [playlist] SHORT_KOREAN_HOOK | SITUATION에 듣기 좋은 GENRE 노래모음. Lead with a tasteful emotional line or question, such as 나랑 데이트 할래?, 오늘 좀 예뻐 보이고 싶어, 전남친이 후회하게, 너도 나 좋아하잖아, 오늘은 내가 주인공, then name the truthful listening situation and one clear release-level genre lane, preferably K-pop hip-hop, rap-pop, K-pop trap, boom bap K-pop, Korean R&B, neo-soul pop, or dark street-pop instead of generic K-pop wording. The hook must match the thumbnail/cover mood and must not be explicit, misleading, or unrelated to the music. Do not use city-pop/city pop/시티팝 for new HaruHaru metadata by default unless the human explicitly requested that lane or the uploaded/reused track set is already clearly city-pop. If the HaruHaru release is city-pop, keep metadata and any backfill city-pop-related; if it is not city-pop, do not mix city-pop wording or tracks into it. "
            "For Solwave Radio releases, write Spanish default metadata and name one clear release-level genre lane when accurate, such as Pop Latino, reggaeton pop, urbano latino, bachata pop, salsa pop, cumbia pop, Latin R&B, Spanish R&B, or Latin soul, instead of generic Latin pop wording. "
            "For Soft Hour Radio releases, write Korean default metadata that clearly signals piano/solo piano and a real listening use case. Use natural clickable wording such as 조용히 집중하고 싶을 때 듣는 피아노 BGM, 공부와 작업을 위한 솔로 피아노, 잠들기 전 틀어놓는 잔잔한 피아노, 비 오는 밤 책 읽을 때 좋은 피아노 연주곡, or equivalent localized transcreations. Do not describe Soft Hour as lofi beats, guitar, jazz trio, Rhodes, strings, pads, or generic mixed-instrument BGM unless the human explicitly changed the channel direction. "
            "For Storylight OST BGM releases, write English default metadata and position it as no-vocal playful Japanese arcade-game, fantasy-game, anime-game, and anime-OST-style music for gaming, reading, light focus, and fun background listening. "
            "For Cinematic Pulse releases, write English default metadata and position it as no-vocal large-scale cinematic orchestra, movie OST, film score, trailer, final battle scene, orchestral battle, emotional film score, mystery-tension, dark fantasy, sci-fi, heroic, or epic scene music. Do not use juvenile game-menu title wording such as Boss BGM, Final Boss Music, Final Boss Focus Music, 보스, 보스전, or bare BGM. Rotate among varied cinematic title lanes such as final battle, dark fantasy, heroic trailer, emotional score, sci-fi action, mystery tension, grand journey, orchestral battle, writing music, and movie OST focus; examples are style references, not fixed templates to repeat. For Club Bloom releases, write English default metadata and position it as no-vocal instrumental club music in one selected style lane, such as deep house, tech house, melodic techno, trance, bass house, UK garage, liquid DnB, tropical house, Afro house, synthwave club, workout EDM, night drive, gaming, party warmup, or club listening. Club Bloom titles must put the exact genre, subgenre, or genre fusion immediately after [playlist] using mainstream mix language such as Progressive Trance x EDM Mix, Tech House Workout Mix, Hype Trap x EDM Mix, Melodic Techno Night Drive, Bass House Club Mix, or Festival EDM Mix; put only one or two public use cases after the separator and avoid awkward lists like Progressive Trance for Night Roads, Gaming Focus and Club Drive. "
            "For BibliaCanto scripture releases, write English default metadata for either Old Testament scripture-inspired music from Genesis onward or New Testament scripture-inspired music from Matthew onward. New Testament scripture releases now upload to BibliaCanto too, not 불송. Include the selected passage range in the main title, every localized title, and the description. Include whether it is Old Testament or New Testament. Include the selected release-level music lane in the title/description and keep the whole release in one coherent modern lane, rotating across uploads; lanes can include scripture hip-hop, Bible R&B, K-pop-inspired scripture pop, scripture rap-pop, trap-soul scripture songs, boom-bap Bible rap, alt-R&B scripture songs, neo-soul scripture songs, Afropop/Amapiano-pop scripture songs, dark street-pop scripture, or synth-pop scripture songs. Never position BibliaCanto as Gospel music, worship, holy worship, church choir, hymns, praise band, CCM, congregational music, or prayer-ballad worship. "
            "For 불송 Buddhist releases, write Korean default metadata and position it as Buddhist scripture-inspired Korean hip-hop/rap vocal music by default. Name the Buddhist source or theme carefully, such as Dhammapada-inspired, Heart Sutra-inspired, Diamond Sutra-inspired, Lotus Sutra-inspired, or Buddhist wisdom-inspired, and do not claim exact chapter/verse coverage unless verified. Include the exact verified Buddhist source/chapter/section in the public title when known, and otherwise include the verified Buddhist theme directly in the title; do not use generic 불경 wording alone when a source/theme is available. Korean/default titles should not waste title space on redundant language labels such as 한국어 랩 or 한국어 힙합; use source/theme plus the real lane instead, such as 반야심경 랩, 금강경 힙합, 법구경 힙합, 정어와 구업 힙합, 불교 힙합, or 불경 힙합. By default, name one coherent Buddhist hip-hop/rap lane such as 불교 힙합, 불경 힙합, mindful hip-hop, Korean Buddhist rap, mellow boom bap, Buddhist hip-hop soul, or restrained Buddhist trap-soul. Use a non-hip-hop Buddhist lane only when the human explicitly asks or when finishing an already-started release in that lane. Do not relabel an already-rendered non-hip-hop 불송 video as hip-hop if the audio and burned-in visual text already say Dharma pop, 다르마팝, acoustic Dharma songs, or 다르마송. Avoid trot, ppongjjak, old Korean cabaret-pop, trot vocal ornaments, and accordion/brass trot cliches unless the human explicitly asks for that sound. State that lyrics are original paraphrases inspired by Buddhist teaching, not direct scripture recitation. "
            "Use each track's style and exclude_style fields as Suno generation context for later thumbnails, loop video or still-image visual, and metadata. "
            "Write tags as comma-separated plain tags without # symbols, and never use AI/process/tool tags such as AIMusic, AI music, AI generated, AI visualizer, Suno, OpenClaw, or Codex. "
            "For Tokyo/J-pop/Japan, HaruHaru/K-pop/Korean pop, Storylight OST/game-anime OST, Cinematic Pulse/movie OST, Club Bloom/EDM, BibliaCanto/Bible scripture, 불송/Buddhist scripture, sundaze/English-American pop playlist, and Solwave/Latin/Spanish pop releases, write Korean, Japanese, English, Spanish, Vietnamese, Thai, Hindi, Filipino, Indonesian, Turkish, Brazilian Portuguese, European Portuguese, French, German, Arabic suitable for Arabic/Egyptian audiences, Simplified Chinese, and Traditional Chinese title/description versions and pass them to approve-metadata. "
            "Use --default-language ko for HaruHaru and 불송, --default-language es for Solwave Radio, and --default-language en for sundaze, Storylight OST, Cinematic Pulse, Club Bloom, and BibliaCanto."
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
        "tr": {
            "title": read_optional_text(getattr(args, "tr_title", ""), "", label="Turkish title"),
            "description": read_optional_text(
                getattr(args, "tr_description", ""),
                getattr(args, "tr_description_file", ""),
                label="Turkish description",
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
    create_parser.add_argument("--target-seconds", type=int, default=0, help="Playlist target duration. Default: auto by channel: 600 seconds for normal channels, 2400 seconds for BibliaCanto/불송. Ignored for single releases.")
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

    search_tracks_parser = subparsers.add_parser(
        "search-tracks",
        help="Search existing app tracks so OpenClaw can reuse them in playlist releases.",
    )
    search_tracks_parser.add_argument("--q", default="", help="Search text matched against title, prompt, style, tags, and metadata.")
    search_tracks_parser.add_argument(
        "--status-filter",
        choices=["pending_review", "approved", "rejected", "held", "uploaded", "failed"],
        default="approved",
        help="Track status filter. Default: approved.",
    )
    search_tracks_parser.add_argument("--user-rating", default="", help="Optional user rating filter: like, dislike, or none.")
    search_tracks_parser.add_argument("--limit", type=int, default=20, help="Maximum tracks to return.")
    search_tracks_parser.add_argument("--min-track-seconds", type=int, default=0, help="Optional minimum duration filter. Default: 0, show existing tracks even when they are short.")
    search_tracks_parser.add_argument("--allow-short-track", action="store_true", help="Ignore --min-track-seconds and show short tracks.")
    search_tracks_parser.add_argument("--full", action="store_true", help="Return full track payloads instead of compact search payloads.")
    search_tracks_parser.set_defaults(func=search_tracks)

    reuse_track_parser = subparsers.add_parser(
        "reuse-track",
        help="Attach one or more existing approved tracks to a Playlist Release.",
    )
    reuse_track_parser.add_argument("--release-id", default="", help="Existing Playlist Release id.")
    reuse_track_parser.add_argument("--release-title", default="", help="Existing Playlist Release title.")
    reuse_track_parser.add_argument("--track-id", action="append", required=True, help="Existing track id to attach. Repeat in final playlist order.")
    reuse_track_parser.add_argument("--actor", default="openclaw:reuse-track", help="Actor name recorded in histories.")
    reuse_track_parser.set_defaults(func=reuse_track)

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
    audio_parser.add_argument("--min-track-seconds", type=int, default=DEFAULT_MIN_PLAYLIST_TRACK_SECONDS, help="Minimum auto-approved Playlist Release track length. Default: 60 seconds.")
    audio_parser.add_argument("--max-track-seconds", type=int, default=DEFAULT_MAX_PLAYLIST_TRACK_SECONDS, help="Maximum auto-approved Playlist Release track length. Default: 0, no maximum.")
    audio_parser.add_argument("--allow-short-track", action="store_true", help="Allow a playlist track shorter than --min-track-seconds. Use only with explicit human approval.")
    audio_parser.add_argument("--allow-long-track", action="store_true", help="Allow a playlist track longer than --max-track-seconds when an explicit maximum is configured.")
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
    auto_playlist_parser.add_argument("--thumbnail", default="", help="Required YouTube thumbnail image unless an uploaded thumbnail already exists on the release. Most channels need readable title/use-case text; HaruHaru should normally be text-free; Tokyo Daydream photorealistic hip-hop/R&B should use a friend-taken Japanese street/lifestyle look, text-free or with one integrated lane phrase when useful; sundaze/Solwave Radio should use a friend-taken phone-photo look with one integrated lane phrase when useful; Club Bloom should use premium nightlife still imagery with one integrated club lane phrase when useful; for 불송, use the same contemporary Buddhist first-frame image or pass --allow-cover-as-thumbnail.")
    auto_playlist_parser.add_argument("--loop-video", default="", help="Required short visual clip generated by Gemini/Dreamina/Seedance for moving-video renders unless an uploaded loop video already exists on the release. Omit for HaruHaru/sundaze/Solwave Radio/Tokyo Daydream photorealistic hip-hop/R&B/Club Bloom still-image renders.")
    auto_playlist_parser.add_argument("--loop-video-provider", choices=LOOP_VIDEO_PROVIDERS, default="", help="Provider that created --loop-video. Use gemini, dreamina, or seedance for generated clips.")
    auto_playlist_parser.add_argument("--hard-loop-video", action="store_true", help="Use direct clip reuse instead of the default smoothed render.")
    auto_playlist_parser.add_argument("--allow-still-image-video", action="store_true", help="Allow rendering from the still cover image without a loop video. Use for HaruHaru/sundaze/Solwave Radio/Tokyo Daydream photorealistic hip-hop/R&B/Club Bloom still-image renders or a human-approved fallback.")
    auto_playlist_parser.add_argument("--allow-short-loop-video", action="store_true", help="Allow a loop video shorter than the normal loop-video target. Use only when the human explicitly accepts a non-standard clip.")
    auto_playlist_parser.add_argument("--allow-generated-draft-cover", action="store_true", help="Explicitly allow the app's placeholder draft cover. Do not use unless the human accepts it.")
    auto_playlist_parser.add_argument("--allow-cover-as-thumbnail", action="store_true", help="Reuse the video cover as the YouTube thumbnail. Do not use unless the human accepts one image for both roles; 불송 can use the same contemporary Buddhist first-frame image for both.")
    auto_playlist_parser.add_argument("--release-id", default="", help="Existing Playlist Release id. If omitted, a new release is created.")
    auto_playlist_parser.add_argument("--release-title", default="", help="New Playlist Release title. Defaults to first audio filename stem.")
    auto_playlist_parser.add_argument("--description", default="", help="Release description used for metadata generation.")
    auto_playlist_parser.add_argument("--prompt", default="", help="Prompt or generation note shared by uploaded tracks.")
    auto_playlist_parser.add_argument("--style", action="append", default=[], help="Suno style/settings. Repeat once per --audio, or provide one shared value.")
    auto_playlist_parser.add_argument("--exclude-style", action="append", default=[], help="Suno excluded style/negative tags. Repeat once per --audio, or provide one shared value.")
    auto_playlist_parser.add_argument("--tags", default="", help="Comma-separated tags shared by uploaded tracks.")
    auto_playlist_parser.add_argument("--lyrics", action="append", default=[], help="Optional lyrics/content notes. Repeat once per --audio, or provide one shared value.")
    auto_playlist_parser.add_argument("--lyrics-file", action="append", default=[], help="Optional UTF-8 lyrics file. Repeat once per --audio, or provide one shared file.")
    auto_playlist_parser.add_argument("--target-seconds", type=int, default=0, help="Playlist target duration. Default: auto by channel: 600 seconds for normal channels, 2400 seconds for BibliaCanto/불송.")
    auto_playlist_parser.add_argument("--min-track-seconds", type=int, default=DEFAULT_MIN_PLAYLIST_TRACK_SECONDS, help="Minimum allowed duration for each playlist track. Default: 60 seconds.")
    auto_playlist_parser.add_argument("--max-track-seconds", type=int, default=DEFAULT_MAX_PLAYLIST_TRACK_SECONDS, help="Maximum allowed duration for each playlist track. Default: 0, no maximum.")
    auto_playlist_parser.add_argument("--allow-short-track", action="store_true", help="Allow playlist tracks shorter than --min-track-seconds. Use only with explicit human approval.")
    auto_playlist_parser.add_argument("--allow-long-track", action="store_true", help="Allow playlist tracks longer than --max-track-seconds when an explicit maximum is configured.")
    auto_playlist_parser.add_argument("--randomize-order", action="store_true", help="Shuffle approved playlist track order before audio render. Metadata timestamps will use the rendered order. Soft Hour Radio keeps reused back-half tracks after the fresh solo-piano lead block.")
    auto_playlist_parser.add_argument("--youtube-channel-title", default="", help="Connected YouTube channel title. Default: inferred from release; J-pop/Tokyo uses Tokyo Daydream Radio, K-pop uses HaruHaru, playful Japanese game/anime OST and arcade/fantasy-game BGM use Storylight OST, large-scale cinematic orchestra/movie OST/film score uses Cinematic Pulse, no-vocal EDM/house/techno/trance club music uses Club Bloom, Old Testament and New Testament Bible scripture music use BibliaCanto, Buddhist scripture music uses 불송, English/American pop playlist lanes use sundaze, Latin/Spanish pop uses Solwave Radio, and solo-piano BGM uses Soft Hour Radio.")
    auto_playlist_parser.add_argument("--youtube-channel-id", default="", help="Optional explicit YouTube channel id. Overrides title lookup.")
    auto_playlist_parser.add_argument(
        "--video-spectrum-overlay-style",
        choices=["bars", "mirror-bars", "calm-bars", "none"],
        default="bars",
        help="App-rendered audio visualizer preset. OpenClaw should choose this per release; omitted fallback is bars. Use none for fastest render without spectrum overlay.",
    )
    auto_playlist_parser.add_argument(
        "--video-render-resolution",
        choices=["720p", "1080p", "2k"],
        default="720p",
        help="Final MP4 render resolution. Use 1080p for HaruHaru/sundaze/Solwave Radio/Tokyo Daydream photorealistic hip-hop/R&B/Club Bloom still-image renders.",
    )
    auto_playlist_parser.add_argument(
        "--video-render-source-mode",
        choices=["auto", "loop_video", "still_image"],
        default="auto",
        help="Final render visual source. Use still_image for HaruHaru/sundaze/Solwave Radio/Tokyo Daydream photorealistic hip-hop/R&B/Club Bloom still-image renders.",
    )
    auto_playlist_parser.add_argument(
        "--lyrics-overlay",
        action="store_true",
        help="Burn approximate line-level lyric subtitles into the rendered video. Use for vocal lyric releases.",
    )
    auto_playlist_parser.add_argument(
        "--lyrics-overlay-style",
        choices=["auto", "soft-bottom-fade", "editorial-lower-left", "center-breath-serif"],
        default="auto",
        help="Burned lyric subtitle style. auto uses center-breath-serif for 불송 and editorial-lower-left for HaruHaru/sundaze/Solwave Radio/Tokyo Daydream photorealistic hip-hop/R&B.",
    )
    auto_playlist_parser.add_argument(
        "--lyrics-alignment-mode",
        choices=["whisper", "timeline"],
        default="whisper",
        help="Line lyric timing source. whisper uses faster-whisper ASR word timestamps; timeline is only a rough fallback.",
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
    auto_single_parser.add_argument("--cover", default="", help="Required final 16:9 cover/first-frame image without channel names or logos unless an uploaded final cover already exists on the release.")
    auto_single_parser.add_argument("--thumbnail", default="", help="Required YouTube thumbnail image unless an uploaded thumbnail already exists on the release. Most channels need readable text; HaruHaru should normally be text-free; Tokyo Daydream photorealistic hip-hop/R&B should use a friend-taken Japanese street/lifestyle look, text-free or with one integrated lane phrase when useful; sundaze/Solwave Radio should use a friend-taken phone-photo look with one integrated lane phrase when useful; Club Bloom should use premium nightlife still imagery with one integrated club lane phrase when useful; for 불송, use the same contemporary Buddhist first-frame image or pass --allow-cover-as-thumbnail.")
    auto_single_parser.add_argument("--loop-video", default="", help="Required short visual clip generated by Gemini/Dreamina/Seedance for moving-video renders unless an uploaded loop video already exists on the release. Omit for HaruHaru/sundaze/Solwave Radio/Tokyo Daydream photorealistic hip-hop/R&B/Club Bloom still-image renders.")
    auto_single_parser.add_argument("--loop-video-provider", choices=LOOP_VIDEO_PROVIDERS, default="", help="Provider that created --loop-video. Use gemini, dreamina, or seedance for generated clips.")
    auto_single_parser.add_argument("--hard-loop-video", action="store_true", help="Use direct clip reuse instead of the default smoothed render.")
    auto_single_parser.add_argument("--allow-still-image-video", action="store_true", help="Allow rendering from the still cover image without a loop video. Use for HaruHaru/sundaze/Solwave Radio/Tokyo Daydream photorealistic hip-hop/R&B/Club Bloom still-image renders or a human-approved fallback.")
    auto_single_parser.add_argument("--allow-short-loop-video", action="store_true", help="Allow a loop video shorter than the normal loop-video target. Use only when the human explicitly accepts a non-standard clip.")
    auto_single_parser.add_argument("--allow-generated-draft-cover", action="store_true", help="Explicitly allow the app's placeholder draft cover. Do not use unless the human accepts it.")
    auto_single_parser.add_argument("--allow-cover-as-thumbnail", action="store_true", help="Reuse the video cover as the YouTube thumbnail. Do not use unless the human accepts one image for both roles; 불송 can use the same contemporary Buddhist first-frame image for both.")
    auto_single_parser.add_argument("--release-id", default="", help="Existing Single Release id. If omitted, a new release is created.")
    auto_single_parser.add_argument("--release-title", default="", help="New Single Release title. Defaults to first audio filename stem.")
    auto_single_parser.add_argument("--description", default="", help="Release description used for metadata generation.")
    auto_single_parser.add_argument("--prompt", default="", help="Prompt or generation note shared by uploaded tracks.")
    auto_single_parser.add_argument("--style", action="append", default=[], help="Suno style/settings for this final song. Provide one value.")
    auto_single_parser.add_argument("--exclude-style", action="append", default=[], help="Suno excluded style/negative tags for this final song. Provide one value.")
    auto_single_parser.add_argument("--tags", default="", help="Comma-separated tags shared by uploaded tracks.")
    auto_single_parser.add_argument("--lyrics", action="append", default=[], help="Optional lyrics/content notes. Repeat once per --audio, or provide one shared value.")
    auto_single_parser.add_argument("--lyrics-file", action="append", default=[], help="Optional UTF-8 lyrics file. Repeat once per --audio, or provide one shared file.")
    auto_single_parser.add_argument("--youtube-channel-title", default="", help="Connected YouTube channel title. Default: inferred from release; J-pop/Tokyo uses Tokyo Daydream Radio, K-pop uses HaruHaru, playful Japanese game/anime OST and arcade/fantasy-game BGM use Storylight OST, large-scale cinematic orchestra/movie OST/film score uses Cinematic Pulse, no-vocal EDM/house/techno/trance club music uses Club Bloom, Old Testament and New Testament Bible scripture music use BibliaCanto, Buddhist scripture music uses 불송, English/American pop playlist lanes use sundaze, Latin/Spanish pop uses Solwave Radio, and solo-piano BGM uses Soft Hour Radio.")
    auto_single_parser.add_argument("--youtube-channel-id", default="", help="Optional explicit YouTube channel id. Overrides title lookup.")
    auto_single_parser.add_argument(
        "--video-spectrum-overlay-style",
        choices=["bars", "mirror-bars", "calm-bars", "none"],
        default="bars",
        help="App-rendered audio visualizer preset. OpenClaw should choose this per release; omitted fallback is bars. Use none for fastest render without spectrum overlay.",
    )
    auto_single_parser.add_argument(
        "--video-render-resolution",
        choices=["720p", "1080p", "2k"],
        default="720p",
        help="Final MP4 render resolution. Use 1080p for HaruHaru/sundaze/Solwave Radio/Tokyo Daydream photorealistic hip-hop/R&B/Club Bloom still-image renders.",
    )
    auto_single_parser.add_argument(
        "--video-render-source-mode",
        choices=["auto", "loop_video", "still_image"],
        default="auto",
        help="Final render visual source. Use still_image for HaruHaru/sundaze/Solwave Radio/Tokyo Daydream photorealistic hip-hop/R&B/Club Bloom still-image renders.",
    )
    auto_single_parser.add_argument(
        "--lyrics-overlay",
        action="store_true",
        help="Burn approximate line-level lyric subtitles into the rendered video. Use for vocal lyric releases.",
    )
    auto_single_parser.add_argument(
        "--lyrics-overlay-style",
        choices=["auto", "soft-bottom-fade", "editorial-lower-left", "center-breath-serif"],
        default="auto",
        help="Burned lyric subtitle style. auto uses center-breath-serif for 불송 and editorial-lower-left for HaruHaru/sundaze/Solwave Radio/Tokyo Daydream photorealistic hip-hop/R&B.",
    )
    auto_single_parser.add_argument(
        "--lyrics-alignment-mode",
        choices=["whisper", "timeline"],
        default="whisper",
        help="Line lyric timing source. whisper uses faster-whisper ASR word timestamps; timeline is only a rough fallback.",
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
    render_audio_parser.add_argument("--randomize-order", action="store_true", help="Shuffle approved playlist track order before audio render. Soft Hour Radio keeps reused back-half tracks after the fresh solo-piano lead block.")
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
    render_video_parser.add_argument("--allow-still-image-video", action="store_true", help="Allow rendering from the still cover image without a loop video. Use for HaruHaru/sundaze/Solwave Radio/Tokyo Daydream photorealistic hip-hop/R&B/Club Bloom still-image renders or a human-approved fallback.")
    render_video_parser.add_argument(
        "--video-spectrum-overlay-style",
        choices=["bars", "mirror-bars", "calm-bars", "none"],
        default="bars",
        help="App-rendered audio visualizer preset. OpenClaw should choose this per release.",
    )
    render_video_parser.add_argument(
        "--video-render-resolution",
        choices=["720p", "1080p", "2k"],
        default="720p",
        help="Final MP4 render resolution. Use 1080p for HaruHaru/sundaze/Solwave Radio/Tokyo Daydream photorealistic hip-hop/R&B/Club Bloom still-image renders.",
    )
    render_video_parser.add_argument(
        "--video-render-source-mode",
        choices=["auto", "loop_video", "still_image"],
        default="auto",
        help="Final render visual source. Use still_image for HaruHaru/sundaze/Solwave Radio/Tokyo Daydream photorealistic hip-hop/R&B/Club Bloom still-image renders.",
    )
    render_video_parser.add_argument(
        "--lyrics-overlay",
        action="store_true",
        help="Burn approximate line-level lyric subtitles into the rendered video. Use for vocal lyric releases.",
    )
    render_video_parser.add_argument(
        "--lyrics-overlay-style",
        choices=["auto", "soft-bottom-fade", "editorial-lower-left", "center-breath-serif"],
        default="auto",
        help="Burned lyric subtitle style. auto uses center-breath-serif for 불송 and editorial-lower-left for HaruHaru/sundaze/Solwave Radio/Tokyo Daydream photorealistic hip-hop/R&B.",
    )
    render_video_parser.add_argument(
        "--lyrics-alignment-mode",
        choices=["whisper", "timeline"],
        default="whisper",
        help="Line lyric timing source. whisper uses faster-whisper ASR word timestamps; timeline is only a rough fallback.",
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
    metadata_parser.add_argument("--tr-title", default="", help="Turkish localized YouTube title.")
    metadata_parser.add_argument("--tr-description", default="", help="Turkish localized YouTube description. Prefer --tr-description-file for multiline copy.")
    metadata_parser.add_argument("--tr-description-file", default="", help="UTF-8 Turkish description file.")
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
    metadata_parser.add_argument("--default-language", default="ko", help="Default upload metadata language: ko, ja, en, es, vi, th, hi, fil, id, tr, pt-BR, pt-PT, fr, de, ar, zh-CN, or zh-TW.")
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

    scripture_status_parser = subparsers.add_parser("openclaw-scripture-status", help="Show app-side BibliaCanto scripture sequence state.")
    scripture_status_parser.set_defaults(func=openclaw_scripture_status)

    scripture_reserve_parser = subparsers.add_parser("openclaw-scripture-reserve", help="Reserve the next app-owned Bible scripture passage for BibliaCanto.")
    scripture_reserve_parser.add_argument("--channel-title", required=True, help='Use "BibliaCanto" for Old Testament or "New Testament" for the New Testament branch.')
    scripture_reserve_parser.add_argument("--release-id", default="", help="Release id to associate with the reserved passage.")
    scripture_reserve_parser.add_argument("--title", default="", help="Release title to store on the passage ledger.")
    scripture_reserve_parser.add_argument("--notes", default="", help="Optional ledger notes.")
    scripture_reserve_parser.add_argument("--passage-range", default="", help="Optional explicit passage override. Omit for the app-managed next passage.")
    scripture_reserve_parser.set_defaults(func=openclaw_scripture_reserve)

    scripture_complete_parser = subparsers.add_parser("openclaw-scripture-complete", help="Mark an app-owned scripture passage scheduled or published.")
    scripture_complete_parser.add_argument("--channel-title", required=True, help='Use "BibliaCanto" for Old Testament or "New Testament" for the New Testament branch.')
    scripture_complete_parser.add_argument("--passage-range", required=True, help="Passage range returned by openclaw-scripture-reserve.")
    scripture_complete_parser.add_argument("--status", choices=["scheduled", "published"], default="scheduled")
    scripture_complete_parser.add_argument("--release-id", default="", help="Release id associated with this passage.")
    scripture_complete_parser.add_argument("--youtube-video-id", default="", help="YouTube video id after upload/scheduling.")
    scripture_complete_parser.add_argument("--title", default="", help="Final release/YouTube title to store on the ledger.")
    scripture_complete_parser.add_argument("--notes", default="", help="Optional ledger notes.")
    scripture_complete_parser.add_argument("--next-start", default="", help="Optional next canonical start override. Normally omit and let the app use its configured sequence.")
    scripture_complete_parser.set_defaults(func=openclaw_scripture_complete)

    scripture_fail_parser = subparsers.add_parser("openclaw-scripture-fail", help="Mark a reserved scripture passage failed so it can be retried later.")
    scripture_fail_parser.add_argument("--channel-title", required=True, help='Use "BibliaCanto" for Old Testament or "New Testament" for the New Testament branch.')
    scripture_fail_parser.add_argument("--passage-range", required=True, help="Passage range returned by openclaw-scripture-reserve.")
    scripture_fail_parser.add_argument("--release-id", default="", help="Release id associated with this passage.")
    scripture_fail_parser.add_argument("--title", default="", help="Release title to store on the ledger.")
    scripture_fail_parser.add_argument("--reason", required=True, help="Failure reason.")
    scripture_fail_parser.set_defaults(func=openclaw_scripture_fail)

    youtube_status_parser = subparsers.add_parser("youtube-status", help="Show connected YouTube status/channels as JSON.")
    youtube_status_parser.set_defaults(func=youtube_status)

    provider_start_parser = subparsers.add_parser(
        "provider-video-start",
        help="Record a Gemini/Dreamina/Seedance loop-video generation attempt before clicking Generate.",
    )
    provider_start_parser.add_argument("--release-id", required=True, help="Release id that will receive the loop video.")
    provider_start_parser.add_argument("--first-frame", required=True, help="Absolute cover/first-frame image path used for provider video generation.")
    provider_start_parser.add_argument("--provider", choices=["gemini", "dreamina", "seedance"], required=True)
    provider_start_parser.add_argument("--note", default="", help="Optional short generation note.")
    provider_start_parser.add_argument("--force", action="store_true", help="Override the 20 minute same-image provider wait only for manual correction.")
    provider_start_parser.set_defaults(func=provider_video_start)

    provider_status_parser = subparsers.add_parser(
        "provider-video-status",
        help="Check whether a same-release/same-first-frame provider video generation is still inside the 20 minute wait window.",
    )
    provider_status_parser.add_argument("--release-id", required=True, help="Release id being checked.")
    provider_status_parser.add_argument("--first-frame", required=True, help="Absolute cover/first-frame image path used for provider video generation.")
    provider_status_parser.set_defaults(func=provider_video_status)

    provider_finish_parser = subparsers.add_parser(
        "provider-video-finish",
        help="Mark a provider loop-video attempt succeeded, failed, timed out, or cancelled.",
    )
    provider_finish_parser.add_argument("--release-id", required=True, help="Release id that will receive the loop video.")
    provider_finish_parser.add_argument("--first-frame", required=True, help="Absolute cover/first-frame image path used for provider video generation.")
    provider_finish_parser.add_argument("--provider", choices=["gemini", "dreamina", "seedance"], required=True)
    provider_finish_parser.add_argument("--status", choices=["succeeded", "failed", "timed_out", "cancelled"], required=True)
    provider_finish_parser.add_argument("--output-video", default="", help="Downloaded MP4 path when status=succeeded.")
    provider_finish_parser.add_argument("--note", default="", help="Optional short result note.")
    provider_finish_parser.add_argument("--force", action="store_true", help="Override provider mismatch only for stale-state correction.")
    provider_finish_parser.set_defaults(func=provider_video_finish)

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
        base_url = api_base(args.api_base)
        validate_api_base_auth(base_url, headers)
        with httpx.Client(base_url=base_url, timeout=120.0, headers=headers) as client:
            result = args.func(client, args)
        print_json(result)
        return 0
    except Exception as exc:  # noqa: BLE001
        print_json({"ok": False, "error": str(exc)})
        return 1


if __name__ == "__main__":
    sys.exit(main())
