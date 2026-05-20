from __future__ import annotations

from typing import Any


CINEMATIC_PULSE_CHANNEL_TITLE = "cinematic pulse"
LOW_MOTION_SPECTRUM_CHANNEL_TITLES = {
    "불송",
    "the new verse",
}
RELIGIOUS_NO_SPECTRUM_CHANNEL_TITLES = {
    "bibliacanto",
    "the old verse",
    "old testament",
    "new testament",
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
