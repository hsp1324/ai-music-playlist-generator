from __future__ import annotations

import re
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.utils.timeline import timeline_from_track_dicts


SECTION_LINE_RE = re.compile(r"^\s*\[[^\]]+\]\s*$")
LEADING_MARKER_RE = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+")
INSTRUMENTAL_HINT_RE = re.compile(
    r"^\s*(?:instrumental|instrumental only|no vocals?|without lyrics|interlude|intro|outro)\s*$",
    re.IGNORECASE,
)
LYRIC_TOKEN_RE = re.compile(
    r"[a-z0-9]+(?:'[a-z0-9]+)?|[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]",
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


def build_word_aligned_line_lyric_cues(
    tracks: list[dict[str, Any]],
    rendered_timeline: list[dict[str, Any]] | None,
    *,
    audio_path: str | Path,
    model_size: str = "tiny",
    language: str | None = None,
    min_score: float = 0.34,
    max_end_seconds: float | None = None,
) -> list[dict[str, Any]]:
    """Build line lyric cues by aligning stored lyrics to ASR word timestamps.

    The external algorithm is faster-whisper. It transcribes the final rendered
    audio with word timestamps, then this module maps those words back to the
    stored lyrics line by line. If the dependency/model is missing, callers get a
    clear error instead of silently producing misleading timeline-spaced lyrics.
    """

    words = transcribe_words_with_faster_whisper(
        audio_path,
        model_size=model_size,
        language=language,
    )
    if not words:
        return []

    cues: list[dict[str, Any]] = []
    rows = timeline_from_track_dicts(tracks, rendered_timeline or [])
    for row in rows:
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
        track_words = [
            word
            for word in words
            if _positive_float(word.get("end")) >= track_start - 1.5
            and _positive_float(word.get("start")) <= track_end + 1.5
        ]
        cues.extend(
            _align_lines_to_words(
                lines,
                track_words,
                track_start=track_start,
                track_end=track_end,
                track_id=row.get("track_id"),
                track_title=row.get("title"),
                min_score=min_score,
            )
        )
    return _dedupe_and_order_cues(cues, max_end_seconds=max_end_seconds)


def transcribe_words_with_faster_whisper(
    audio_path: str | Path,
    *,
    model_size: str = "tiny",
    language: str | None = None,
    device: str = "cpu",
    compute_type: str = "int8",
) -> list[dict[str, Any]]:
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError(
            "faster-whisper is required for lyric ASR alignment. "
            "Install the lyrics extra: uv pip install -e '.[lyrics]'"
        ) from exc

    path = Path(audio_path)
    if not path.exists():
        raise FileNotFoundError(f"Lyric alignment audio does not exist: {path}")

    model = _faster_whisper_model(str(model_size or "tiny"), device, compute_type, WhisperModel)
    transcribe_kwargs: dict[str, Any] = {
        "word_timestamps": True,
        "vad_filter": False,
        "beam_size": 5,
        "condition_on_previous_text": False,
    }
    if language:
        transcribe_kwargs["language"] = str(language).strip().lower()
    segments, _info = model.transcribe(str(path), **transcribe_kwargs)

    words: list[dict[str, Any]] = []
    for segment in segments:
        for raw_word in getattr(segment, "words", None) or []:
            text = str(getattr(raw_word, "word", "") or "").strip()
            start = _positive_float(getattr(raw_word, "start", None))
            end = _positive_float(getattr(raw_word, "end", None))
            if not text or end <= start:
                continue
            for token in _tokens_from_text(text):
                words.append({"token": token, "text": text, "start": start, "end": end})
    return words


@lru_cache(maxsize=3)
def _faster_whisper_model(model_size: str, device: str, compute_type: str, model_cls: Any) -> Any:
    return model_cls(model_size, device=device, compute_type=compute_type)


def _align_lines_to_words(
    lines: list[str],
    words: list[dict[str, Any]],
    *,
    track_start: float,
    track_end: float,
    track_id: Any,
    track_title: Any,
    min_score: float,
) -> list[dict[str, Any]]:
    cues: list[dict[str, Any]] = []
    if not lines or not words:
        return cues

    tokens = [str(word.get("token") or "") for word in words]
    cursor = 0
    for line_index, line in enumerate(lines, start=1):
        line_tokens = _tokens_from_text(line)
        if not line_tokens:
            continue
        match = _best_line_window(line_tokens, tokens, cursor)
        if not match or match["score"] < min_score:
            continue
        start_index = int(match["start"])
        end_index = int(match["end"])
        if end_index < start_index or start_index >= len(words):
            continue
        start = max(_positive_float(words[start_index].get("start")) - 0.12, track_start)
        end = min(_positive_float(words[min(end_index, len(words) - 1)].get("end")) + 0.25, track_end)
        if end - start < 0.55:
            end = min(start + 0.9, track_end)
        if end <= start:
            continue
        cues.append(
            {
                "start": round(start, 3),
                "end": round(end, 3),
                "text": line,
                "track_id": track_id,
                "track_title": track_title,
                "line_index": line_index,
                "alignment": "faster-whisper",
                "alignment_score": round(float(match["score"]), 3),
            }
        )
        cursor = max(end_index + 1, cursor)
    return _smooth_overlaps(cues)


def _best_line_window(line_tokens: list[str], tokens: list[str], cursor: int) -> dict[str, float | int] | None:
    if not line_tokens or not tokens:
        return None
    start_at = max(cursor - 2, 0)
    line_len = len(line_tokens)
    min_window = max(1, min(line_len, int(line_len * 0.45)))
    max_window = min(len(tokens), max(line_len * 2 + 4, line_len + 8, 6))
    best: dict[str, float | int] | None = None
    for start in range(start_at, len(tokens)):
        if start < cursor - 2:
            continue
        if best and start > cursor + max(60, line_len * 8) and float(best["score"]) >= 0.5:
            break
        for end_exclusive in range(start + min_window, min(len(tokens), start + max_window) + 1):
            window = tokens[start:end_exclusive]
            matcher = SequenceMatcher(None, line_tokens, window, autojunk=False)
            blocks = matcher.get_matching_blocks()
            matched = sum(block.size for block in blocks)
            if matched <= 0:
                continue
            line_coverage = matched / max(len(line_tokens), 1)
            window_coverage = matched / max(len(window), 1)
            score = (matcher.ratio() * 0.55) + (line_coverage * 0.35) + (window_coverage * 0.10)
            if start < cursor:
                score -= 0.08
            if best is None or score > float(best["score"]):
                best = {"start": start, "end": end_exclusive - 1, "score": score}
    return best


def _smooth_overlaps(cues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered = sorted(cues, key=lambda cue: (float(cue["start"]), float(cue["end"])))
    smoothed: list[dict[str, Any]] = []
    for cue in ordered:
        if smoothed and float(cue["start"]) < float(smoothed[-1]["end"]):
            previous = dict(smoothed[-1])
            previous["end"] = round(max(float(cue["start"]) - 0.05, float(previous["start"]) + 0.5), 3)
            smoothed[-1] = previous
        if float(cue["end"]) - float(cue["start"]) >= 0.45:
            smoothed.append(cue)
    return smoothed


def _dedupe_and_order_cues(cues: list[dict[str, Any]], *, max_end_seconds: float | None = None) -> list[dict[str, Any]]:
    ordered = _smooth_overlaps(cues)
    if max_end_seconds is None:
        return ordered
    clipped: list[dict[str, Any]] = []
    for cue in ordered:
        if float(cue["start"]) >= max_end_seconds:
            continue
        clipped.append({**cue, "end": round(min(float(cue["end"]), max_end_seconds), 3)})
    return clipped


def _tokens_from_text(text: str) -> list[str]:
    return [match.group(0).lower() for match in LYRIC_TOKEN_RE.finditer(str(text or ""))]


def _line_weight(line: str) -> float:
    ascii_count = sum(1 for char in line if ord(char) < 128)
    non_ascii_count = max(len(line) - ascii_count, 0)
    return (ascii_count * 1.0) + (non_ascii_count * 1.4)


def _positive_float(value: Any) -> float:
    try:
        return max(float(value or 0), 0.0)
    except (TypeError, ValueError):
        return 0.0
