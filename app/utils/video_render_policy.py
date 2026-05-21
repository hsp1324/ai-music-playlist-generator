from __future__ import annotations

from typing import Any

from app.utils.lyric_subtitles import lyric_lines_from_text


CINEMATIC_PULSE_CHANNEL_TITLE = "cinematic pulse"
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
RELIGIOUS_NO_SPECTRUM_CHANNEL_TITLES = {
    "bibliacanto",
    "the old verse",
    "old testament",
    "new testament",
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


def is_cinematic_pulse_release(meta: dict[str, Any]) -> bool:
    return CINEMATIC_PULSE_CHANNEL_TITLE in _release_channel_titles(meta)


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


def default_video_lyrics_overlay_style(meta: dict[str, Any]) -> str:
    if is_bulsong_release(meta):
        return "center_breath_serif"
    return "soft_bottom_fade"


def resolve_video_lyrics_overlay_style(value: Any, meta: dict[str, Any]) -> str:
    style = normalize_video_lyrics_overlay_style(value)
    if style == "auto":
        return default_video_lyrics_overlay_style(meta)
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
    return track_dicts_have_singable_lyrics(tracks)
