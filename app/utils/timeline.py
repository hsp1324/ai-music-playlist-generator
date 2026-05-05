from __future__ import annotations

from typing import Any

from app.utils.track_titles import display_track_titles


def format_timestamp(seconds: int | float, *, force_hours: bool = False) -> str:
    total_seconds = max(int(round(float(seconds or 0))), 0)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    remainder = total_seconds % 60
    if force_hours:
        return f"{hours:02d}:{minutes:02d}:{remainder:02d}"
    if hours:
        return f"{hours}:{minutes:02d}:{remainder:02d}"
    return f"{minutes:02d}:{remainder:02d}"


def timeline_from_track_dicts(
    tracks: list[dict[str, Any]],
    rendered_timeline: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    snapshot = _matching_rendered_timeline(tracks, rendered_timeline or [])
    rows = _snapshot_rows(tracks, snapshot) if snapshot else _duration_rows(tracks)
    total_seconds = _timeline_total_seconds(rows)
    force_hours = total_seconds >= 3600
    display_titles = display_track_titles(tracks)

    timeline = []
    for index, (row, track, display_title) in enumerate(zip(rows, tracks, display_titles), start=1):
        duration_seconds = max(int(row["duration_seconds"]), 0)
        start_seconds = max(int(row["start_seconds"]), 0)
        timeline.append(
            {
                "index": index,
                "track_id": track.get("id") or row.get("track_id"),
                "start_seconds": start_seconds,
                "start_seconds_exact": row.get("start_seconds_exact"),
                "start": format_timestamp(start_seconds, force_hours=force_hours),
                "title": track.get("title") or row.get("title") or f"Track {index}",
                "display_title_hint": display_title,
                "duration_seconds": duration_seconds,
                "duration_seconds_exact": row.get("duration_seconds_exact"),
                "duration": format_timestamp(duration_seconds),
                "lyrics": str(track.get("lyrics") or ""),
                "style": str(track.get("style") or ""),
                "prompt": track.get("prompt") or "",
                "tags": track.get("tags") or "",
                "duration_source": row.get("duration_source") or "track_duration",
            }
        )
    return timeline


def build_rendered_timeline_snapshot(
    tracks: list[dict[str, Any]],
    exact_durations: list[float],
    duration_sources: list[str] | None = None,
) -> list[dict[str, Any]]:
    offset = 0.0
    snapshot = []
    for index, track in enumerate(tracks):
        duration_exact = _positive_float(exact_durations[index] if index < len(exact_durations) else 0)
        duration_source = (duration_sources or [])[index] if duration_sources and index < len(duration_sources) else "ffprobe"
        if duration_exact <= 0:
            duration_exact = _positive_float(track.get("duration_seconds"))
            duration_source = "track_duration"
        start_seconds = int(round(offset))
        duration_seconds = max(int(round(duration_exact)), 0)
        snapshot.append(
            {
                "index": index + 1,
                "track_id": track.get("id"),
                "title": track.get("title") or f"Track {index + 1}",
                "start_seconds": start_seconds,
                "start_seconds_exact": round(offset, 3),
                "duration_seconds": duration_seconds,
                "duration_seconds_exact": round(duration_exact, 3),
                "duration_source": duration_source,
            }
        )
        offset += duration_exact
    return snapshot


def _matching_rendered_timeline(
    tracks: list[dict[str, Any]],
    rendered_timeline: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not tracks or not rendered_timeline or len(tracks) != len(rendered_timeline):
        return []
    track_ids = [str(track.get("id") or "") for track in tracks]
    snapshot_ids = [str(row.get("track_id") or "") for row in rendered_timeline]
    if not all(track_ids) or track_ids != snapshot_ids:
        return []
    return rendered_timeline


def _snapshot_rows(
    tracks: list[dict[str, Any]],
    snapshot: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    offset = 0.0
    for track, row in zip(tracks, snapshot):
        start_exact = _positive_float(row.get("start_seconds_exact"))
        if start_exact <= 0 and rows:
            start_exact = offset
        duration_exact = _positive_float(row.get("duration_seconds_exact"))
        if duration_exact <= 0:
            duration_exact = _positive_float(row.get("duration_seconds"))
        if duration_exact <= 0:
            duration_exact = _positive_float(track.get("duration_seconds"))
        rows.append(
            {
                **row,
                "start_seconds": int(round(start_exact)),
                "start_seconds_exact": round(start_exact, 3),
                "duration_seconds": max(int(round(duration_exact)), 0),
                "duration_seconds_exact": round(duration_exact, 3),
            }
        )
        offset = start_exact + duration_exact
    return rows


def _duration_rows(tracks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    offset = 0
    rows = []
    for track in tracks:
        duration = max(int(track.get("duration_seconds") or 0), 0)
        rows.append(
            {
                "track_id": track.get("id"),
                "title": track.get("title"),
                "start_seconds": offset,
                "start_seconds_exact": float(offset),
                "duration_seconds": duration,
                "duration_seconds_exact": float(duration),
                "duration_source": "track_duration",
            }
        )
        offset += duration
    return rows


def _timeline_total_seconds(rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    last = rows[-1]
    start = _positive_float(last.get("start_seconds_exact"))
    duration = _positive_float(last.get("duration_seconds_exact"))
    if start <= 0 and len(rows) > 1:
        start = _positive_float(last.get("start_seconds"))
    if duration <= 0:
        duration = _positive_float(last.get("duration_seconds"))
    return max(int(round(start + duration)), 0)


def _positive_float(value: Any) -> float:
    try:
        return max(float(value or 0), 0.0)
    except (TypeError, ValueError):
        return 0.0
