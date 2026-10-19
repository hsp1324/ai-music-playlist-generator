from __future__ import annotations

import hashlib
import math
from typing import Any

from app.utils.lyric_subtitles import lyric_lines_from_text


CINEMATIC_PULSE_CHANNEL_TITLE = "cinematic pulse"
CINEMATIC_PULSE_ORCHESTRA_LANE = "orchestra"
CINEMATIC_PULSE_CUTE_GAME_LANE = "cute_game"
STORYLIGHT_OST_CHANNEL_TITLE = "storylight ost"
LYRIC_CENTER_CHANNEL_TITLES = {
    "불송",
    "the new verse",
    "bulsong",
}
LYRIC_EDITORIAL_CHANNEL_TITLES = {
    "haruharu",
    "tokyo daydream radio",
    "sundaze",
    "solwave radio",
}
STILL_IMAGE_RENDER_DEFAULT_CHANNEL_TITLES = {
    "haruharu",
    "sundaze",
    "solwave radio",
    "club bloom",
    "불송",
    "the new verse",
    "bulsong",
}
LYRIC_SOFT_CHANNEL_TITLES = {
    "soft hour radio",
    "storylight ost",
    "cinematic pulse",
    "club bloom",
    "bibliacanto",
    "the old verse",
}
VOCAL_RELEASE_CHANNEL_TITLES = {
    "불송",
    "the new verse",
    "new verse",
    "bulsong",
    "bibliacanto",
    "biblia canto",
    "the old verse",
    "old verse",
    "old testament",
    "new testament",
    "haruharu",
    "tokyo daydream radio",
    "sundaze",
    "solwave radio",
}
INSTRUMENTAL_RELEASE_CHANNEL_TITLES = {
    "soft hour radio",
    "storylight ost",
    "cinematic pulse",
    "club bloom",
}
RELEASE_VOCAL_MODE_ALIASES = {
    "": "unknown",
    "unknown": "unknown",
    "auto": "unknown",
    "vocal": "vocal",
    "vocals": "vocal",
    "lyric": "vocal",
    "lyrics": "vocal",
    "singing": "vocal",
    "sung": "vocal",
    "instrumental": "instrumental",
    "no vocal": "instrumental",
    "no vocals": "instrumental",
    "no-vocal": "instrumental",
    "no-vocals": "instrumental",
    "no lyrics": "instrumental",
    "no-lyrics": "instrumental",
    "bgm": "instrumental",
}
VIDEO_LYRICS_OVERLAY_STYLE_ALIASES = {
    "": "auto",
    "auto": "auto",
    "1": "soft_bottom_fade",
    "01": "soft_bottom_fade",
    "soft": "soft_bottom_fade",
    "soft-bottom": "soft_bottom_fade",
    "soft-bottom-fade": "soft_bottom_fade",
    "soft_bottom": "soft_bottom_fade",
    "soft_bottom_fade": "soft_bottom_fade",
    "4": "editorial_lower_left",
    "04": "editorial_lower_left",
    "editorial": "editorial_lower_left",
    "editorial-lower-left": "editorial_lower_left",
    "editorial_lower_left": "editorial_lower_left",
    "lower-left": "editorial_lower_left",
    "lower_left": "editorial_lower_left",
    "9": "center_breath_serif",
    "09": "center_breath_serif",
    "center": "center_breath_serif",
    "center-breath": "center_breath_serif",
    "center-breath-serif": "center_breath_serif",
    "center_breath_serif": "center_breath_serif",
}
LYRIC_EDITORIAL_TEXT_HINTS = (
    "j-pop",
    "jpop",
    "k-pop",
    "kpop",
    "pop latino",
    "latin pop",
    "spanish pop",
    "reggaeton",
    "bachata",
    "r&b",
    "rnb",
    "hip-hop",
    "hiphop",
    "rap",
    "dance pop",
    "synth-pop",
    "city pop",
    "vocal",
    "보컬",
    "케이팝",
    "제이팝",
    "힙합",
    "알앤비",
    "라틴",
)
LYRIC_SOFT_TEXT_HINTS = (
    "bgm",
    "lofi",
    "lo-fi",
    "study",
    "sleep",
    "focus",
    "reading",
    "cafe",
    "piano",
    "ost",
    "game",
    "arcade",
    "cinematic",
    "orchestra",
    "film score",
    "trailer",
    "edm",
    "house",
    "techno",
    "trance",
    "instrumental",
    "no vocal",
    "no-vocal",
    "scripture",
    "gospel",
    "worship",
    "bible",
    "성경",
    "찬양",
    "연주곡",
    "보컬 없는",
    "가사 없는",
)


def _clean_title(value: Any) -> str:
    return str(value or "").strip().lower()


def _release_channel_titles(meta: dict[str, Any]) -> set[str]:
    titles = {
        _clean_title(meta.get("youtube_channel_title")),
        _clean_title(meta.get("target_youtube_channel_title")),
        _clean_title(meta.get("scripture_channel_title")),
    }
    upload_channel = meta.get("upload_channel")
    if isinstance(upload_channel, dict):
        titles.add(_clean_title(upload_channel.get("title")))
    return {title for title in titles if title}


def _optional_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    clean = str(value).strip().lower()
    if clean in {"1", "true", "yes", "y", "on"}:
        return True
    if clean in {"0", "false", "no", "n", "off"}:
        return False
    return None


def normalize_release_vocal_mode(value: Any) -> str:
    key = str(value or "").strip().lower().replace("_", "-")
    return RELEASE_VOCAL_MODE_ALIASES.get(key, "unknown")


def infer_release_vocal_mode(meta: dict[str, Any], tracks: list[dict[str, Any]] | None = None) -> tuple[str, str]:
    """Return (mode, source) for whether a release should be treated as lyric/vocal work."""

    stored_source = str(meta.get("release_vocal_mode_source") or "").strip().lower()
    stored_mode = normalize_release_vocal_mode(meta.get("release_vocal_mode"))
    if stored_mode != "unknown" and stored_source in {"explicit", "manual", "user"}:
        return stored_mode, stored_source

    stored_has_lyrics = _optional_bool(meta.get("release_has_singable_lyrics"))
    if stored_has_lyrics is not None and stored_source in {"explicit", "manual", "user"}:
        return ("vocal" if stored_has_lyrics else "instrumental"), stored_source

    for key in ("lyrics_release", "has_vocals", "vocal_release"):
        value = _optional_bool(meta.get(key))
        if value is not None:
            return ("vocal" if value else "instrumental"), "explicit"

    for key in ("instrumental_release", "no_vocals", "no_vocal", "no_lyrics"):
        value = _optional_bool(meta.get(key))
        if value is not None:
            return ("instrumental" if value else "vocal"), "explicit"

    titles = _release_channel_titles(meta)
    if titles & VOCAL_RELEASE_CHANNEL_TITLES:
        return "vocal", "channel"
    if titles & INSTRUMENTAL_RELEASE_CHANNEL_TITLES:
        return "instrumental", "channel"

    if tracks is not None and track_dicts_have_singable_lyrics(tracks):
        return "vocal", "tracks"

    return "unknown", "unknown"


def release_has_singable_lyrics(meta: dict[str, Any], tracks: list[dict[str, Any]] | None = None) -> bool:
    mode, _source = infer_release_vocal_mode(meta, tracks)
    return mode == "vocal"


def release_vocal_metadata(meta: dict[str, Any], tracks: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    mode, source = infer_release_vocal_mode(meta, tracks)
    return {
        "release_vocal_mode": mode,
        "release_has_singable_lyrics": mode == "vocal",
        "release_vocal_mode_source": source,
    }


def apply_release_vocal_metadata(
    meta: dict[str, Any],
    tracks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    meta.update(release_vocal_metadata(meta, tracks))
    return meta


def is_cinematic_pulse_release(meta: dict[str, Any]) -> bool:
    return CINEMATIC_PULSE_CHANNEL_TITLE in _release_channel_titles(meta)


def infer_cinematic_pulse_lane(
    meta: dict[str, Any],
    *,
    title: str = "",
    tracks: list[dict[str, Any]] | None = None,
) -> str | None:
    """Classify Cinematic Pulse inventory without merging its two daily lanes."""

    if not is_cinematic_pulse_release(meta):
        return None

    aliases = {
        "orchestra": CINEMATIC_PULSE_ORCHESTRA_LANE,
        "orchestral": CINEMATIC_PULSE_ORCHESTRA_LANE,
        "cinematic-orchestra": CINEMATIC_PULSE_ORCHESTRA_LANE,
        "cinematic-orchestral": CINEMATIC_PULSE_ORCHESTRA_LANE,
        "cinematic-orchestra-lane": CINEMATIC_PULSE_ORCHESTRA_LANE,
        "cinematic-orchestra-slot": CINEMATIC_PULSE_ORCHESTRA_LANE,
        "cute": CINEMATIC_PULSE_CUTE_GAME_LANE,
        "cute-game": CINEMATIC_PULSE_CUTE_GAME_LANE,
        "cute-game-music": CINEMATIC_PULSE_CUTE_GAME_LANE,
        "storylight": CINEMATIC_PULSE_CUTE_GAME_LANE,
        "former-storylight": CINEMATIC_PULSE_CUTE_GAME_LANE,
        "cinematic-cute-game": CINEMATIC_PULSE_CUTE_GAME_LANE,
    }
    for key in (
        "cinematic_pulse_lane",
        "channel_lane",
        "release_lane",
        "youtube_schedule_label",
    ):
        value = str(meta.get(key) or "").strip().lower().replace("_", "-").replace(" ", "-")
        if value in aliases:
            return aliases[value]

    values: list[Any] = [
        title,
        meta.get("title"),
        meta.get("release_title"),
        meta.get("youtube_title"),
        meta.get("description"),
        meta.get("youtube_description"),
        meta.get("music_direction"),
        meta.get("style"),
        meta.get("prompt"),
    ]
    for track in tracks or []:
        values.extend((track.get("title"), track.get("style"), track.get("prompt")))
        track_meta = track.get("metadata_json") or track.get("metadata")
        if isinstance(track_meta, dict):
            values.extend(track_meta.values())
    haystack = " ".join(str(value or "") for value in values).casefold()

    cute_hints = (
        "cute game",
        "cozy game",
        "kawaii",
        "adorable",
        "playful",
        "whimsical",
        "item shop",
        "theme park",
        "amusement park",
        "toy town",
        "fantasy town",
        "storybook",
        "celesta",
        "pizzicato",
        "귀여운",
        "아기자기",
        "게임 음악",
        "게임음악",
    )
    if any(hint in haystack for hint in cute_hints):
        return CINEMATIC_PULSE_CUTE_GAME_LANE

    orchestra_hints = (
        "orchestra",
        "orchestral",
        "chamber music",
        "chamber ensemble",
        "string ensemble",
        "symphonic",
        "symphony",
        "film score",
        "movie score",
        "neoclassical",
        "woodwind",
        "string quartet",
        "오케스트라",
        "관현악",
        "현악",
        "교향곡",
    )
    if any(hint in haystack for hint in orchestra_hints):
        return CINEMATIC_PULSE_ORCHESTRA_LANE
    return None


def is_storylight_ost_release(meta: dict[str, Any]) -> bool:
    return STORYLIGHT_OST_CHANNEL_TITLE in _release_channel_titles(meta)


def is_still_image_render_default_release(meta: dict[str, Any]) -> bool:
    return bool(_release_channel_titles(meta) & STILL_IMAGE_RENDER_DEFAULT_CHANNEL_TITLES)


def is_bulsong_release(meta: dict[str, Any]) -> bool:
    return bool(_release_channel_titles(meta) & LYRIC_CENTER_CHANNEL_TITLES)


def apply_video_spectrum_channel_policy(
    style: str,
    meta: dict[str, Any],
    *,
    title: str = "",
) -> str:
    channel_titles = _release_channel_titles(meta)
    if "club bloom" in channel_titles:
        normalized = str(style or "").strip().lower().replace("_", "-")
        legacy_aliases = {
            "club-neon": "club-floor-cyan",
            "club-mirror": "club-floor-mirror",
            "club-radial": "club-floor-white",
            "crate-notes": "club-crate-notes",
            "club-crate": "club-crate-notes",
        }
        normalized = legacy_aliases.get(normalized, normalized)
        if normalized in {
            "club-floor-white",
            "club-floor-cyan",
            "club-floor-dual",
            "club-floor-amber",
            "club-floor-mirror",
            "club-crate-notes",
        }:
            return normalized
        return "club-floor-cyan"
    return "bars"


def normalize_video_lyrics_overlay_style(value: Any) -> str:
    key = str(value or "").strip().lower().replace("_", "-")
    return VIDEO_LYRICS_OVERLAY_STYLE_ALIASES.get(key, "auto")


def _lyrics_style_haystack(meta: dict[str, Any], *, title: str = "") -> str:
    values: list[Any] = [
        title,
        meta.get("title"),
        meta.get("release_title"),
        meta.get("youtube_title"),
        meta.get("description"),
        meta.get("youtube_description"),
        meta.get("cover_prompt"),
        meta.get("dreamina_prompt"),
        meta.get("video_render_source_mode"),
        meta.get("video_spectrum_overlay_style"),
    ]
    values.extend(_release_channel_titles(meta))
    return " ".join(str(value or "") for value in values).casefold()


def _stable_lyrics_style_choice(meta: dict[str, Any], *, title: str = "") -> str:
    seed = "|".join(
        str(value or "")
        for value in (
            title,
            meta.get("youtube_title"),
            meta.get("release_id"),
            meta.get("id"),
            meta.get("youtube_channel_title"),
            meta.get("target_youtube_channel_title"),
        )
    )
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    return "editorial_lower_left" if digest[0] % 2 else "soft_bottom_fade"


def default_video_lyrics_overlay_style(meta: dict[str, Any], *, title: str = "") -> str:
    if is_bulsong_release(meta):
        return "center_breath_serif"
    return "editorial_lower_left"


def resolve_video_lyrics_overlay_style(value: Any, meta: dict[str, Any], *, title: str = "") -> str:
    if is_bulsong_release(meta):
        return "center_breath_serif"
    return "editorial_lower_left"


def track_dicts_have_singable_lyrics(tracks: list[dict[str, Any]]) -> bool:
    for track in tracks:
        if lyric_lines_from_text(str(track.get("lyrics") or "")):
            return True
    return False


def should_auto_enable_video_lyrics_overlay(meta: dict[str, Any], tracks: list[dict[str, Any]]) -> bool:
    if bool(meta.get("video_lyrics_overlay_disabled")):
        return False
    return release_has_singable_lyrics(meta, tracks)


def resolve_final_video_repeat_count(
    settings: Any,
    meta: dict[str, Any],
    *,
    base_duration_seconds: int | float | None,
) -> int:
    if not bool(getattr(settings, "playlist_final_video_repeat_enabled", False)):
        return 1
    if str(meta.get("workspace_mode") or "playlist").strip().lower() == "single_track_video":
        return 1

    try:
        base_duration = int(float(base_duration_seconds or 0))
    except (TypeError, ValueError):
        base_duration = 0
    if base_duration <= 0:
        return 1

    explicit_count = meta.get("video_final_repeat_count") or meta.get("final_video_repeat_count")
    try:
        configured_count = int(explicit_count or getattr(settings, "playlist_final_video_repeat_count", 3) or 1)
    except (TypeError, ValueError):
        configured_count = 1
    configured_count = max(configured_count, 1)

    try:
        min_base_seconds = int(getattr(settings, "playlist_final_video_repeat_min_base_seconds", 15 * 60) or 0)
    except (TypeError, ValueError):
        min_base_seconds = 15 * 60
    if configured_count <= 1 and base_duration < min_base_seconds:
        return 1
    if not explicit_count and base_duration < min_base_seconds:
        return 1

    try:
        min_final_seconds = int(getattr(settings, "playlist_final_video_min_seconds", 2 * 60 * 60) or 0)
    except (TypeError, ValueError):
        min_final_seconds = 0
    if min_final_seconds > 0 and not explicit_count:
        configured_count = max(configured_count, math.ceil(min_final_seconds / base_duration))

    try:
        max_count = int(getattr(settings, "playlist_final_video_max_repeat_count", 12) or 0)
    except (TypeError, ValueError):
        max_count = 12
    if max_count > 0:
        configured_count = min(configured_count, max_count)
    return max(configured_count, 1)


def final_video_duration_seconds(base_duration_seconds: int | float | None, repeat_count: int) -> int:
    try:
        base_duration = int(float(base_duration_seconds or 0))
    except (TypeError, ValueError):
        base_duration = 0
    return max(base_duration, 0) * max(int(repeat_count or 1), 1)
