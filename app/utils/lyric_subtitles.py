from __future__ import annotations

import re
from typing import Any

from app.utils.timeline import timeline_from_track_dicts


SECTION_LINE_RE = re.compile(r"^\s*\[[^\]]+\]\s*$")
LEADING_MARKER_RE = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+")
INSTRUMENTAL_HINT_RE = re.compile(
    r"^\s*(?:instrumental|instrumental only|no vocals?|without lyrics|interlude|intro|outro)\s*$",
    re.IGNORECASE,
)


def lyric_lines_from_text(lyrics: str) -> list[str]:
    """Return singable lyric lines, skipping section headers and control notes."""

    lines: list[str] = []
    for raw_line in str(lyrics or "").replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = LEADING_MARKER_RE.sub("", raw_line.strip())
        if not line:
            continue
        if SECTION_LINE_RE.match(line):
            continue
        if INSTRUMENTAL_HINT_RE.match(line):
            continue
        lines.append(re.sub(r"\s+", " ", line))
    return lines


def build_line_lyric_cues(
    tracks: list[dict[str, Any]],
    rendered_timeline: list[dict[str, Any]] | None = None,
    *,
    max_end_seconds: float | None = None,
) -> list[dict[str, Any]]:
    """Build approximate line-level lyric cues on the rendered playlist timeline.

    This uses the app's known track order and exact rendered track durations. It does
    not perform vocal forced-alignment; the cue shape is intentionally isolated so a
    future ASR/forced-alignment provider can replace only timing generation.
    """

    cues: list[dict[str, Any]] = []
    for row in timeline_from_track_dicts(tracks, rendered_timeline or []):
        track_start = _positive_float(row.get("start_seconds_exact"))
        if track_start <= 0:
            track_start = _positive_float(row.get("start_seconds"))
        track_duration = _positive_float(row.get("duration_seconds_exact"))
        if track_duration <= 0:
            track_duration = _positive_float(row.get("duration_seconds"))
        if track_duration <= 0:
            continue
        track_end = track_start + track_duration
        if max_end_seconds is not None:
            if track_start >= max_end_seconds:
                continue
            track_end = min(track_end, max_end_seconds)
        lines = lyric_lines_from_text(str(row.get("lyrics") or ""))
        if not lines:
            continue

        track_duration = max(track_end - track_start, 0)
        lead_in = min(max(track_duration * 0.07, 1.2), 8.0)
        outro = min(max(track_duration * 0.05, 0.8), 6.0)
        cue_start = track_start + lead_in
        cue_end = track_end - outro
        if cue_end - cue_start < max(len(lines) * 1.1, 4.0):
            cue_start = track_start + min(0.5, track_duration * 0.05)
            cue_end = track_end - min(0.5, track_duration * 0.05)
        if cue_end <= cue_start:
            continue

        available = cue_end - cue_start
        gap = min(0.28, max(0.08, available * 0.003))
        text_time = max(available - (gap * max(len(lines) - 1, 0)), available * 0.9)
        weights = [max(_line_weight(line), 8.0) for line in lines]
        total_weight = sum(weights) or float(len(lines))

        cursor = cue_start
        for index, (line, weight) in enumerate(zip(lines, weights), start=1):
            line_duration = max(text_time * (weight / total_weight), 1.1)
            end = min(cursor + line_duration, cue_end)
            if end - cursor >= 0.6:
                cues.append(
                    {
                        "start": round(cursor, 3),
                        "end": round(end, 3),
                        "text": line,
                        "track_id": row.get("track_id"),
                        "track_title": row.get("title"),
                        "line_index": index,
                    }
                )
            cursor = end + gap
            if cursor >= cue_end:
                break
    return cues


def _line_weight(line: str) -> float:
    ascii_count = sum(1 for char in line if ord(char) < 128)
    non_ascii_count = max(len(line) - ascii_count, 0)
    return (ascii_count * 1.0) + (non_ascii_count * 1.4)


def _positive_float(value: Any) -> float:
    try:
        return max(float(value or 0), 0.0)
    except (TypeError, ValueError):
        return 0.0
