from __future__ import annotations

import re
from typing import Any


LEGACY_VARIANT_SUFFIXES: dict[str, int] = {
    "morning": 1,
    "evening": 2,
    "warm": 1,
    "soft": 2,
    "quiet": 1,
    "deep": 2,
    "linen": 1,
    "amber": 2,
    "dawn": 1,
    "dusk": 2,
    "gentle": 1,
    "still": 2,
}

GENERIC_TITLE_TOKENS = {
    "a",
    "b",
    "audio",
    "beat",
    "candidate",
    "chord",
    "chords",
    "keys",
    "melody",
    "music",
    "part",
    "piano",
    "song",
    "sonata",
    "suno",
    "take",
    "track",
    "version",
    "waltz",
}

NATURAL_SUFFIXES = (
    "Afterglow",
    "Current",
    "Horizon",
    "Cadence",
    "Lantern",
    "Drift",
    "Avenue",
    "Pulse",
    "Bloom",
    "Runway",
    "Skyline",
    "Mosaic",
    "Lift",
    "Ripple",
    "Motion",
    "Signal",
    "Ember",
    "Orbit",
    "Pathway",
    "Arcade",
    "Coast",
    "Glowline",
    "Distance",
    "Silverline",
)

FALLBACK_TITLES = (
    "Sunlit Avenue",
    "Amber Current",
    "Velvet Horizon",
    "Silver Motion",
    "Crystal Runway",
    "Open Air Cadence",
    "Blue Lantern",
    "Golden Drift",
    "Clear Momentum",
    "Neon Breeze",
    "Starlit Pulse",
    "Fresh Skyline",
)


def clean_track_display_title(title: str) -> str:
    base, _variant_index = split_variant_title(title)
    return base or str(title or "Untitled Track").strip() or "Untitled Track"


def upload_track_title(title: str) -> str:
    base, variant_index = split_variant_title(title)
    if variant_index is not None:
        return natural_track_title(base, variant_index)
    return base


def display_track_titles(tracks: list[dict[str, Any]]) -> list[str]:
    preferred_titles = [
        upload_track_title(str(track.get("title") or f"Track {index}"))
        for index, track in enumerate(tracks, start=1)
    ]
    counts: dict[str, int] = {}
    for title in preferred_titles:
        counts[title.lower()] = counts.get(title.lower(), 0) + 1

    seen: dict[str, int] = {}
    display_titles = []
    for title in preferred_titles:
        key = title.lower()
        seen[key] = seen.get(key, 0) + 1
        if counts[key] > 1:
            display_titles.append(natural_track_title(title, seen[key]))
        else:
            display_titles.append(title)
    return display_titles


def split_variant_title(title: str) -> tuple[str, int | None]:
    cleaned = normalize_title_text(title)

    legacy_match = re.match(
        r"^(?P<base>.+?)\s+-\s+(?P<label>morning|evening|warm|soft|quiet|deep|linen|amber|dawn|dusk|gentle|still)$",
        cleaned,
        flags=re.IGNORECASE,
    )
    if legacy_match:
        base = normalize_title_text(legacy_match.group("base"))
        return base, LEGACY_VARIANT_SUFFIXES[legacy_match.group("label").lower()]

    letter_match = re.match(
        r"^(?P<base>.+?)(?:\s*[-_]\s*|\s+)\(?(?P<label>[AB])\)?$",
        cleaned,
        flags=re.IGNORECASE,
    )
    if letter_match:
        base = normalize_title_text(letter_match.group("base"))
        label = letter_match.group("label").upper()
        return base, 1 if label == "A" else 2

    number_match = re.match(
        r"^(?P<base>.+?)(?:\s*[-_]\s*|\s+)\(?(?P<label>0?[12])\)?$",
        cleaned,
        flags=re.IGNORECASE,
    )
    if number_match:
        base = normalize_title_text(number_match.group("base"))
        return base, int(number_match.group("label"))

    return cleaned, None


def normalize_title_text(title: str) -> str:
    cleaned = str(title or "").strip() or "Untitled Track"
    cleaned = re.sub(r"\.[a-z0-9]{2,5}$", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^\s*\d{1,3}\s*[-_.]\s*", "", cleaned)
    cleaned = cleaned.replace("_", " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -_")
    return cleaned or "Untitled Track"


def natural_track_title(base_title: str, occurrence_index: int) -> str:
    base = normalize_title_text(base_title)
    keyword = title_keyword(base)
    suffix = NATURAL_SUFFIXES[(stable_offset(base) + max(occurrence_index, 1) - 1) % len(NATURAL_SUFFIXES)]
    if keyword:
        return f"{keyword} {suffix}"
    return FALLBACK_TITLES[(stable_offset(base) + max(occurrence_index, 1) - 1) % len(FALLBACK_TITLES)]


def title_keyword(title: str) -> str:
    tokens = re.findall(r"[A-Za-z가-힣][A-Za-z가-힣']*", normalize_title_text(title))
    meaningful = [token for token in tokens if token.lower() not in GENERIC_TITLE_TOKENS and len(token) > 1]
    if not meaningful:
        return ""
    return meaningful[-1].strip("'").title()


def stable_offset(value: str) -> int:
    return sum(ord(char) for char in value.lower())
