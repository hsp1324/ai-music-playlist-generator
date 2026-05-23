from __future__ import annotations

import re
import unicodedata
from bisect import bisect_left
from dataclasses import dataclass
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
_DIRECT_MATCH = "faster-whisper"
_GLOBAL_MATCH = "faster-whisper-global"
_INTERPOLATED_MATCH = "faster-whisper-interpolated"
_DIAG = 1
_SKIP_LYRIC = 2
_SKIP_WORD = 3
_LYRIC_GAP_PENALTY = 0.62
_WORD_GAP_PENALTY = 0.28
_MISMATCH_SCORE = -1.10
_MAX_INTERPOLATED_SECONDS_PER_TOKEN = 3.2


@dataclass(frozen=True)
class _TokenMatch:
    lyric_index: int
    word_index: int
    similarity: float


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
    min_score: float = 0.30,
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

    word_tokens = [str(word.get("token") or "") for word in words]
    line_ranges: list[tuple[int, int] | None] = []
    lyric_tokens: list[str] = []
    for line in lines:
        line_tokens = _tokens_from_text(line)
        if not line_tokens:
            line_ranges.append(None)
            continue
        start_index = len(lyric_tokens)
        lyric_tokens.extend(line_tokens)
        line_ranges.append((start_index, len(lyric_tokens)))
    if not lyric_tokens or not word_tokens:
        return cues

    matches = _global_token_alignment(lyric_tokens, word_tokens)
    if not matches:
        return cues
    match_by_lyric = {match.lyric_index: match for match in matches}
    matched_lyric_indexes = sorted(match_by_lyric)
    track_match_ratio = len(matches) / max(len(lyric_tokens), 1)
    allow_interpolation = len(matches) >= 2 and track_match_ratio >= max(0.10, min_score * 0.35)

    for line_index, (line, token_range) in enumerate(zip(lines, line_ranges), start=1):
        if token_range is None:
            continue
        start_token, end_token_exclusive = token_range
        line_token_count = max(end_token_exclusive - start_token, 1)
        line_matches = [
            match_by_lyric[token_index]
            for token_index in range(start_token, end_token_exclusive)
            if token_index in match_by_lyric
        ]
        match_coverage = len(line_matches) / line_token_count
        avg_similarity = (
            sum(match.similarity for match in line_matches) / len(line_matches)
            if line_matches
            else 0.0
        )
        bounds: tuple[float, float] | None = None
        alignment_kind = _DIRECT_MATCH
        strong_direct_match = match_coverage >= min_score and (len(line_matches) >= 2 or line_token_count <= 2)

        if strong_direct_match:
            if allow_interpolation:
                bounds = _bounds_from_lyric_span(
                    start_token,
                    end_token_exclusive - 1,
                    words,
                    match_by_lyric,
                    matched_lyric_indexes,
                )
            if bounds is None:
                word_indexes = [match.word_index for match in line_matches]
                bounds = _bounds_from_word_indexes(words, word_indexes)
        if bounds is None and allow_interpolation:
            span_match_by_lyric = match_by_lyric
            span_matched_lyric_indexes = matched_lyric_indexes
            if line_matches and not strong_direct_match and line_token_count > 2:
                span_match_by_lyric = {
                    index: match
                    for index, match in match_by_lyric.items()
                    if not start_token <= index < end_token_exclusive
                }
                span_matched_lyric_indexes = [
                    index
                    for index in matched_lyric_indexes
                    if not start_token <= index < end_token_exclusive
                ]
            bounds = _bounds_from_lyric_span(
                start_token,
                end_token_exclusive - 1,
                words,
                span_match_by_lyric,
                span_matched_lyric_indexes,
            )
            alignment_kind = _GLOBAL_MATCH if line_matches and strong_direct_match else _INTERPOLATED_MATCH
        if bounds is None and line_matches and match_coverage >= max(0.18, min_score * 0.55):
            word_indexes = [match.word_index for match in line_matches]
            bounds = _bounds_from_word_indexes(words, word_indexes)
            alignment_kind = _GLOBAL_MATCH
        if bounds is None:
            continue
        start, end = _cue_bounds_with_padding(
            bounds[0],
            bounds[1],
            track_start=track_start,
            track_end=track_end,
        )
        if end <= start:
            continue
        if strong_direct_match:
            alignment_kind = _DIRECT_MATCH
        alignment_score = (match_coverage * 0.75) + (avg_similarity * 0.25)
        cues.append(
            {
                "start": round(start, 3),
                "end": round(end, 3),
                "text": line,
                "track_id": track_id,
                "track_title": track_title,
                "line_index": line_index,
                "alignment": alignment_kind,
                "alignment_score": round(alignment_score, 3),
                "alignment_match_coverage": round(match_coverage, 3),
                "alignment_matched_tokens": len(line_matches),
                "alignment_total_tokens": line_token_count,
            }
        )
    return _smooth_overlaps(cues)


def _global_token_alignment(lyric_tokens: list[str], word_tokens: list[str]) -> list[_TokenMatch]:
    if not lyric_tokens or not word_tokens:
        return []

    word_count = len(word_tokens)
    previous = [0.0] * (word_count + 1)
    directions = [bytearray(word_count + 1) for _ in range(len(lyric_tokens) + 1)]
    for word_index in range(1, word_count + 1):
        previous[word_index] = previous[word_index - 1] - _WORD_GAP_PENALTY
        directions[0][word_index] = _SKIP_WORD

    for lyric_index, lyric_token in enumerate(lyric_tokens, start=1):
        current = [0.0] * (word_count + 1)
        current[0] = previous[0] - _LYRIC_GAP_PENALTY
        directions[lyric_index][0] = _SKIP_LYRIC
        for word_index, word_token in enumerate(word_tokens, start=1):
            diagonal = previous[word_index - 1] + _token_alignment_score(lyric_token, word_token)
            skip_lyric = previous[word_index] - _LYRIC_GAP_PENALTY
            skip_word = current[word_index - 1] - _WORD_GAP_PENALTY
            if diagonal >= skip_lyric and diagonal >= skip_word:
                current[word_index] = diagonal
                directions[lyric_index][word_index] = _DIAG
            elif skip_lyric >= skip_word:
                current[word_index] = skip_lyric
                directions[lyric_index][word_index] = _SKIP_LYRIC
            else:
                current[word_index] = skip_word
                directions[lyric_index][word_index] = _SKIP_WORD
        previous = current

    matches: list[_TokenMatch] = []
    lyric_index = len(lyric_tokens)
    word_index = word_count
    while lyric_index > 0 or word_index > 0:
        direction = directions[lyric_index][word_index]
        if direction == _DIAG and lyric_index > 0 and word_index > 0:
            similarity = _token_similarity(lyric_tokens[lyric_index - 1], word_tokens[word_index - 1])
            if similarity > 0:
                matches.append(_TokenMatch(lyric_index - 1, word_index - 1, similarity))
            lyric_index -= 1
            word_index -= 1
        elif direction == _SKIP_WORD and word_index > 0:
            word_index -= 1
        elif lyric_index > 0:
            lyric_index -= 1
        else:
            break
    matches.reverse()
    return matches


def _token_alignment_score(lyric_token: str, word_token: str) -> float:
    similarity = _token_similarity(lyric_token, word_token)
    if similarity >= 0.999:
        return 2.0
    if similarity >= 0.82:
        return similarity * 1.1
    return _MISMATCH_SCORE


def _token_similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    if left == right:
        return 1.0
    if len(left) < 4 or len(right) < 4:
        return 0.0
    if not (_is_ascii_word_token(left) and _is_ascii_word_token(right)):
        return 0.0
    ratio = SequenceMatcher(None, left, right, autojunk=False).ratio()
    return ratio if ratio >= 0.82 else 0.0


def _bounds_from_word_indexes(words: list[dict[str, Any]], word_indexes: list[int]) -> tuple[float, float] | None:
    if not word_indexes:
        return None
    first_word_index = max(min(word_indexes), 0)
    last_word_index = min(max(word_indexes), len(words) - 1)
    start = _positive_float(words[first_word_index].get("start"))
    end = _positive_float(words[last_word_index].get("end"))
    if end <= start:
        center = _word_center(words[first_word_index])
        return (center, center)
    return (start, end)


def _bounds_from_lyric_span(
    start_lyric_index: int,
    end_lyric_index: int,
    words: list[dict[str, Any]],
    match_by_lyric: dict[int, _TokenMatch],
    matched_lyric_indexes: list[int],
) -> tuple[float, float] | None:
    start = _time_for_lyric_token(
        start_lyric_index,
        words,
        match_by_lyric,
        matched_lyric_indexes,
        boundary="start",
    )
    end = _time_for_lyric_token(
        end_lyric_index,
        words,
        match_by_lyric,
        matched_lyric_indexes,
        boundary="end",
    )
    if start is None or end is None:
        return None
    if end < start:
        midpoint = (start + end) / 2
        return (midpoint, midpoint)
    return (start, end)


def _time_for_lyric_token(
    lyric_index: int,
    words: list[dict[str, Any]],
    match_by_lyric: dict[int, _TokenMatch],
    matched_lyric_indexes: list[int],
    *,
    boundary: str,
) -> float | None:
    match = match_by_lyric.get(lyric_index)
    if match is not None:
        word = words[match.word_index]
        if boundary == "start":
            return _positive_float(word.get("start"))
        if boundary == "end":
            return _positive_float(word.get("end"))
        return _word_center(word)

    position = bisect_left(matched_lyric_indexes, lyric_index)
    if position <= 0 or position >= len(matched_lyric_indexes):
        return None
    previous_index = matched_lyric_indexes[position - 1]
    next_index = matched_lyric_indexes[position]
    lyric_gap = next_index - previous_index
    if lyric_gap <= 0:
        return None
    previous_time = _word_center(words[match_by_lyric[previous_index].word_index])
    next_time = _word_center(words[match_by_lyric[next_index].word_index])
    time_gap = next_time - previous_time
    if time_gap <= 0:
        return None
    if time_gap / lyric_gap > _MAX_INTERPOLATED_SECONDS_PER_TOKEN:
        return None
    ratio = (lyric_index - previous_index) / lyric_gap
    return previous_time + (time_gap * ratio)


def _cue_bounds_with_padding(
    start: float,
    end: float,
    *,
    track_start: float,
    track_end: float,
) -> tuple[float, float]:
    start = max(start - 0.12, track_start)
    end = min(end + 0.25, track_end)
    if end - start < 0.55:
        midpoint = (start + end) / 2
        half_duration = 0.45
        start = max(midpoint - half_duration, track_start)
        end = min(midpoint + half_duration, track_end)
    if end - start < 0.45:
        end = min(start + 0.75, track_end)
    return start, end


def _word_center(word: dict[str, Any]) -> float:
    start = _positive_float(word.get("start"))
    end = _positive_float(word.get("end"))
    if end <= start:
        return start
    return (start + end) / 2


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
    tokens: list[str] = []
    current_word: list[str] = []

    def flush_word() -> None:
        if current_word:
            tokens.append("".join(current_word))
            current_word.clear()

    normalized = unicodedata.normalize("NFKC", str(text or "")).lower()
    for char in normalized:
        if _is_cjk_kana_or_hangul(char):
            flush_word()
            tokens.append(char)
            continue
        for piece in unicodedata.normalize("NFKD", char):
            if unicodedata.combining(piece):
                continue
            if _is_cjk_kana_or_hangul(piece):
                flush_word()
                tokens.append(piece)
            elif piece.isascii() and piece.isalnum():
                current_word.append(piece)
            else:
                flush_word()
    flush_word()
    return tokens


def _is_cjk_kana_or_hangul(char: str) -> bool:
    if not char:
        return False
    codepoint = ord(char)
    return (
        0x3040 <= codepoint <= 0x30FF
        or 0x3400 <= codepoint <= 0x9FFF
        or 0xAC00 <= codepoint <= 0xD7AF
    )


def _is_ascii_word_token(token: str) -> bool:
    return bool(token) and all(char.isascii() and char.isalnum() for char in token)


def _line_weight(line: str) -> float:
    ascii_count = sum(1 for char in line if ord(char) < 128)
    non_ascii_count = max(len(line) - ascii_count, 0)
    return (ascii_count * 1.0) + (non_ascii_count * 1.4)


def _positive_float(value: Any) -> float:
    try:
        return max(float(value or 0), 0.0)
    except (TypeError, ValueError):
        return 0.0
