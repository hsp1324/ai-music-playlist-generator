from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Mapping

DEFAULT_LOOP_VIDEO_CROSSFADE_SECONDS = 1.5
GEMINI_LOOP_VIDEO_CROSSFADE_SECONDS = 2.0

LOOP_VIDEO_PROVIDER_ALIASES = {
    "gemini": "gemini",
    "google-gemini": "gemini",
    "google gemini": "gemini",
    "veo": "gemini",
    "gemini-veo": "gemini",
    "gemini veo": "gemini",
    "dreamina": "dreamina",
    "capcut-dreamina": "dreamina",
    "capcut dreamina": "dreamina",
    "seedance": "seedance",
    "sea-dance": "seedance",
    "sea dance": "seedance",
    "dreamina-seedance": "seedance",
    "dreamina/seedance": "seedance",
    "manual": "manual",
    "human": "manual",
    "unknown": "unknown",
}


def normalize_loop_video_provider(value: str | None) -> str | None:
    normalized = re.sub(r"\s+", " ", str(value or "").strip().lower().replace("_", "-"))
    if not normalized:
        return None
    return LOOP_VIDEO_PROVIDER_ALIASES.get(normalized, "other")


def loop_video_crossfade_seconds_for_provider(provider: str | None) -> float:
    if normalize_loop_video_provider(provider) == "gemini":
        return GEMINI_LOOP_VIDEO_CROSSFADE_SECONDS
    return DEFAULT_LOOP_VIDEO_CROSSFADE_SECONDS


def coerce_loop_video_crossfade_seconds(value: Any, *, provider: str | None = None) -> float:
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return loop_video_crossfade_seconds_for_provider(provider)
    if seconds <= 0:
        return loop_video_crossfade_seconds_for_provider(provider)
    return seconds


def loop_video_provider_from_meta(meta: Mapping[str, Any]) -> str | None:
    loop_video_path = meta.get("loop_video_path")
    if not loop_video_path:
        return None
    provider = normalize_loop_video_provider(meta.get("loop_video_provider"))
    if provider:
        return provider
    for entry in reversed(list(meta.get("loop_video_history") or [])):
        if entry.get("loop_video_path") == loop_video_path:
            provider = normalize_loop_video_provider(entry.get("provider"))
            if provider:
                return provider
    return None


def loop_video_crossfade_seconds_from_meta(meta: Mapping[str, Any]) -> float:
    provider = loop_video_provider_from_meta(meta)
    return coerce_loop_video_crossfade_seconds(
        meta.get("loop_video_crossfade_seconds"),
        provider=provider,
    )


def loop_video_file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
