from __future__ import annotations

import hashlib
from typing import Any

from app.utils.lyric_subtitles import lyric_lines_from_text


CINEMATIC_PULSE_CHANNEL_TITLE = "cinematic pulse"
STORYLIGHT_OST_CHANNEL_TITLE = "storylight ost"
LOW_MOTION_SPECTRUM_CHANNEL_TITLES = {
    "불송",
    "the new verse",
    "bulsong",
}
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
LYRIC_SOFT_CHANNEL_TITLES = {
    "soft hour radio",
    "storylight ost",
    "cinematic pulse",
    "club bloom",
    "bibliacanto",
    "the old verse",
}
RELIGIOUS_NO_SPECTRUM_CHANNEL_TITLES = {
    "bibliacanto",
    "the old verse",
    "old testament",
    "new testament",
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
RELIGIOUS_TITLE_HINTS = (
    "genesis",
    "old testament",
    "new testament",
    "bible",
    "biblical",
    "scripture",
    "gospel",
    "worship",
    "psalm",
    "dhammapada",
    "heart sutra",
    "diamond sutra",
    "lotus sutra",
    "buddhist",
    "dharma",
    "sutra",
    "창세기",
    "성경",
    "구약",
    "신약",
    "복음",
    "찬양",
    "시편",
    "불교",
    "불경",
    "법구경",
    "반야심경",
)
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


def is_storylight_ost_release(meta: dict[str, Any]) -> bool:
    return STORYLIGHT_OST_CHANNEL_TITLE in _release_channel_titles(meta)


def is_bulsong_release(meta: dict[str, Any]) -> bool:
    return bool(_release_channel_titles(meta) & LYRIC_CENTER_CHANNEL_TITLES)


def is_religious_no_spectrum_release(meta: dict[str, Any], *, title: str = "") -> bool:
    titles = _release_channel_titles(meta)
    if titles & RELIGIOUS_NO_SPECTRUM_CHANNEL_TITLES:
        return True
    if str(meta.get("scripture_passage_range") or "").strip():
        return True
    haystack = " ".join(
        str(value or "")
        for value in (
            title,
            meta.get("youtube_title"),
            meta.get("description"),
            meta.get("youtube_description"),
        )
    ).lower()
    return any(hint in haystack for hint in RELIGIOUS_TITLE_HINTS)


def apply_video_spectrum_channel_policy(
    style: str,
    meta: dict[str, Any],
    *,
    title: str = "",
) -> str:
    if _release_channel_titles(meta) & LOW_MOTION_SPECTRUM_CHANNEL_TITLES:
        return "calm-bars"
    if is_religious_no_spectrum_release(meta, title=title):
        return "none"
    if is_cinematic_pulse_release(meta):
        return "bars"
    return style


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
    titles = _release_channel_titles(meta)
    if titles & LYRIC_EDITORIAL_CHANNEL_TITLES:
        return "editorial_lower_left"
    if titles & LYRIC_SOFT_CHANNEL_TITLES:
        return "soft_bottom_fade"

    haystack = _lyrics_style_haystack(meta, title=title)
    editorial_score = sum(1 for hint in LYRIC_EDITORIAL_TEXT_HINTS if hint in haystack)
    soft_score = sum(1 for hint in LYRIC_SOFT_TEXT_HINTS if hint in haystack)
    if editorial_score > soft_score:
        return "editorial_lower_left"
    if soft_score > editorial_score:
        return "soft_bottom_fade"
    return _stable_lyrics_style_choice(meta, title=title)


def resolve_video_lyrics_overlay_style(value: Any, meta: dict[str, Any], *, title: str = "") -> str:
    style = normalize_video_lyrics_overlay_style(value)
    if style == "auto":
        return default_video_lyrics_overlay_style(meta, title=title)
    if is_bulsong_release(meta):
        return "center_breath_serif"
    return style


def track_dicts_have_singable_lyrics(tracks: list[dict[str, Any]]) -> bool:
    for track in tracks:
        if lyric_lines_from_text(str(track.get("lyrics") or "")):
            return True
    return False


def should_auto_enable_video_lyrics_overlay(meta: dict[str, Any], tracks: list[dict[str, Any]]) -> bool:
    if bool(meta.get("video_lyrics_overlay_disabled")):
        return False
    return release_has_singable_lyrics(meta, tracks)
