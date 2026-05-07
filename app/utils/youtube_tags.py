from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any


DISALLOWED_YOUTUBE_TAG_KEYS = {
    "ai",
    "aimusic",
    "aimusicplaylist",
    "aimusicvideo",
    "aigenerated",
    "aigeneratedmusic",
    "aigeneratedsong",
    "aisong",
    "aisongs",
    "aivideo",
    "aivisualizer",
    "artificialintelligence",
    "generativeai",
    "machinelearningmusic",
    "openclaw",
    "codex",
    "suno",
}


def youtube_tag_key(value: Any) -> str:
    return re.sub(r"[^0-9a-z]+", "", str(value or "").strip().lstrip("#").lower())


def is_disallowed_youtube_tag(value: Any) -> bool:
    return youtube_tag_key(value) in DISALLOWED_YOUTUBE_TAG_KEYS


def _tag_candidates(tags: list[str] | str | Iterable[Any]) -> list[Any]:
    if isinstance(tags, str):
        return tags.split(",")
    return list(tags or [])


def normalize_youtube_tags(tags: list[str] | str | Iterable[Any], *, limit: int = 15) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for tag in _tag_candidates(tags):
        value = str(tag).strip().lstrip("#").strip()
        if not value or is_disallowed_youtube_tag(value):
            continue
        key = youtube_tag_key(value)
        if not key or key in seen:
            continue
        seen.add(key)
        normalized.append(value)
        if len(normalized) >= limit:
            break
    return normalized


def hashtag_from_youtube_tag(tag: Any) -> str | None:
    value = "".join(character for character in str(tag).strip().lstrip("#") if character.isalnum() or character == "_")
    if not value or is_disallowed_youtube_tag(value):
        return None
    return f"#{value}"


def sanitize_description_hashtags(description: str) -> str:
    lines: list[str] = []
    for line in str(description or "").splitlines():
        tokens = line.split()
        if not any(token.startswith("#") for token in tokens):
            lines.append(line)
            continue

        kept_tokens: list[str] = []
        removed_disallowed = False
        for token in tokens:
            bare_token = token.strip().strip("([{\"'")
            bare_token = bare_token.rstrip(".,;:!?)]}\"'")
            if bare_token.startswith("#") and is_disallowed_youtube_tag(bare_token):
                removed_disallowed = True
                continue
            kept_tokens.append(token)

        if kept_tokens or not removed_disallowed:
            lines.append(" ".join(kept_tokens))

    return "\n".join(lines).strip()
