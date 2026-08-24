from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


ORCHESTRAL_VOCAL = "orchestral"
PIANO_ONLY_VOCAL = "piano_only"
ACOUSTIC_GUITAR_ONLY_VOCAL = "acoustic_guitar_only"
MIXED_VOCAL_ARRANGEMENT = "mixed"

VOCAL_ARRANGEMENT_PATTERNS: dict[str, tuple[str, ...]] = {
    ORCHESTRAL_VOCAL: (
        "themed large-scale orchestral vocal",
        "large scale orchestral vocal",
        "cinematic orchestral vocal",
        "orchestral vocal song",
        "symphonic vocal song",
        "full symphony orchestra with vocals",
        "full symphony orchestra, prominent intelligible lead vocal",
    ),
    PIANO_ONLY_VOCAL: (
        "piano-only vocal",
        "piano only vocal",
        "solo piano vocal",
        "piano accompaniment only",
        "voice and piano only",
        "piano plus voice only",
    ),
    ACOUSTIC_GUITAR_ONLY_VOCAL: (
        "acoustic-guitar-only vocal",
        "acoustic guitar only vocal",
        "acoustic guitar accompaniment only",
        "voice and acoustic guitar only",
        "acoustic guitar plus voice only",
    ),
}

ORCHESTRAL_THEME_PATTERNS: dict[str, tuple[str, ...]] = {
    "epic_heroic": ("epic", "heroic"),
    "majestic_ceremonial": ("majestic", "ceremonial"),
    "lyrical_tender": ("lyrical", "tender", "emotionally sweeping"),
    "nordic": ("nordic", "fjord", "runic", "winter orchestral"),
    "medieval": ("medieval", "castle", "bardic", "pilgrimage orchestral"),
    "dark_fantasy": ("dark fantasy", "gothic", "tragic orchestral"),
    "mythic": ("mythic", "legendary", "ancient-world", "ancient world"),
    "romantic": ("romantic", "bittersweet", "tearful film-score", "tearful film score"),
    "celestial": ("celestial", "starlight orchestral", "creation orchestral"),
    "adventure": ("adventure", "battle-march", "battle march", "victory", "homecoming"),
}


def _text_values(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for nested in value.values():
            yield from _text_values(nested)
    elif isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray)):
        for nested in value:
            yield from _text_values(nested)


def _haystack(values: Iterable[Any]) -> str:
    return " ".join(
        text.casefold().replace("_", " ").replace("-", " ")
        for value in values
        for text in _text_values(value)
    )


def infer_vocal_arrangement_family(values: Iterable[Any]) -> str | None:
    flat_values = [text for value in values for text in _text_values(value)]
    explicit = {
        text.casefold().strip().replace("-", "_").replace(" ", "_")
        for text in flat_values
    } & {
        ORCHESTRAL_VOCAL,
        PIANO_ONLY_VOCAL,
        ACOUSTIC_GUITAR_ONLY_VOCAL,
    }
    text = _haystack(flat_values)
    matched = {
        family
        for family, patterns in VOCAL_ARRANGEMENT_PATTERNS.items()
        if any(
            pattern.casefold().replace("_", " ").replace("-", " ") in text
            for pattern in patterns
        )
    }
    matched.update(explicit)
    if len(matched) == 1:
        return next(iter(matched))
    if len(matched) > 1:
        return MIXED_VOCAL_ARRANGEMENT
    return None


def infer_orchestral_theme(values: Iterable[Any]) -> str | None:
    text = _haystack(values)
    matched = {
        theme
        for theme, patterns in ORCHESTRAL_THEME_PATTERNS.items()
        if any(
            pattern.casefold().replace("_", " ").replace("-", " ") in text
            for pattern in patterns
        )
    }
    return next(iter(matched)) if len(matched) == 1 else None
