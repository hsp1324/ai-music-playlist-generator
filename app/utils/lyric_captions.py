from __future__ import annotations

import re
from typing import Any


def build_srt_from_lyric_cues(lyric_cues: list[dict[str, Any]]) -> str:
    blocks: list[str] = []
    index = 1
    for cue in sorted(lyric_cues, key=lambda item: (float(item.get("start") or 0), float(item.get("end") or 0))):
        try:
            start = max(float(cue.get("start")), 0.0)
            end = max(float(cue.get("end")), 0.0)
        except (TypeError, ValueError):
            continue
        text = sanitize_srt_caption_text(cue.get("text"))
        if not text or end - start < 0.2:
            continue
        blocks.append(
            "\n".join(
                [
                    str(index),
                    f"{format_srt_timestamp(start)} --> {format_srt_timestamp(end)}",
                    text,
                ]
            )
        )
        index += 1
    return "\n\n".join(blocks) + ("\n" if blocks else "")


def cue_texts(lyric_cues: list[dict[str, Any]]) -> list[str]:
    return [sanitize_srt_caption_text(cue.get("text")).replace("\n", " ") for cue in lyric_cues]


def lyric_cues_with_translated_texts(lyric_cues: list[dict[str, Any]], translations: list[str]) -> list[dict[str, Any]]:
    translated: list[dict[str, Any]] = []
    for cue, text in zip(lyric_cues, translations):
        cleaned = sanitize_srt_caption_text(text).replace("\n", " ")
        if not cleaned:
            cleaned = sanitize_srt_caption_text(cue.get("text")).replace("\n", " ")
        translated.append({**cue, "text": cleaned})
    return translated


def format_srt_timestamp(seconds: float) -> str:
    total_ms = max(int(round(float(seconds) * 1000)), 0)
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def sanitize_srt_caption_text(value: Any) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"<[^>\n]{1,64}>", "", text)
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.split("\n")]
    return "\n".join(line for line in lines if line).strip()
