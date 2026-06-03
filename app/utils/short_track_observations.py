from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

SHORT_TRACK_OBSERVATION_THRESHOLD_SECONDS = 120


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_int(value: Any) -> int:
    try:
        return max(int(float(value or 0)), 0)
    except (TypeError, ValueError):
        return 0


def _duration_bucket(duration_seconds: int) -> str:
    if duration_seconds < 60:
        return "under_60_seconds"
    if duration_seconds < SHORT_TRACK_OBSERVATION_THRESHOLD_SECONDS:
        return "60_to_119_seconds"
    return "120_seconds_or_more"


def build_short_track_observation(
    *,
    duration_seconds: int,
    title: str | None = None,
    track_id: str | None = None,
    prompt: str | None = None,
    style: str | None = None,
    exclude_style: str | None = None,
    tags: str | None = None,
    lyrics: str | None = None,
    source: str | None = None,
    context: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    duration = _safe_int(duration_seconds)
    if duration <= 0 or duration >= SHORT_TRACK_OBSERVATION_THRESHOLD_SECONDS:
        return None

    observation: dict[str, Any] = {
        "observed_at": _utcnow_iso(),
        "context": context,
        "threshold_seconds": SHORT_TRACK_OBSERVATION_THRESHOLD_SECONDS,
        "duration_seconds": duration,
        "duration_bucket": _duration_bucket(duration),
        "track_id": str(track_id or ""),
        "track_title": str(title or ""),
        "source": str(source or ""),
        "prompt": str(prompt or ""),
        "style": str(style or ""),
        "exclude_style": str(exclude_style or ""),
        "tags": str(tags or ""),
        "lyrics_present": bool(str(lyrics or "").strip()),
    }
    if extra:
        observation.update({key: value for key, value in extra.items() if value not in (None, "")})
    return observation


def annotate_short_track_metadata(
    metadata: dict[str, Any] | None,
    *,
    duration_seconds: int,
    title: str | None = None,
    track_id: str | None = None,
    prompt: str | None = None,
    style: str | None = None,
    exclude_style: str | None = None,
    tags: str | None = None,
    lyrics: str | None = None,
    source: str | None = None,
    context: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = dict(metadata or {})
    observation = build_short_track_observation(
        duration_seconds=duration_seconds,
        title=title,
        track_id=track_id,
        prompt=prompt,
        style=style,
        exclude_style=exclude_style,
        tags=tags,
        lyrics=lyrics,
        source=source,
        context=context,
        extra=extra,
    )
    if not observation:
        result.pop("short_track_observation", None)
        result.pop("short_track_under_120_seconds", None)
        result.pop("short_track_duration_seconds", None)
        result.pop("short_track_duration_bucket", None)
        return result

    result["short_track_observation"] = observation
    result["short_track_under_120_seconds"] = True
    result["short_track_duration_seconds"] = observation["duration_seconds"]
    result["short_track_duration_bucket"] = observation["duration_bucket"]
    return result


def record_playlist_short_track_observation(
    metadata: dict[str, Any] | None,
    observation: dict[str, Any] | None,
    *,
    playlist_id: str,
    playlist_title: str,
    channel_title: str | None = None,
    actor: str | None = None,
) -> dict[str, Any]:
    result = dict(metadata or {})
    if not observation:
        return result

    release_observation = {
        **observation,
        "playlist_id": playlist_id,
        "playlist_title": playlist_title,
        "channel_title": str(channel_title or ""),
        "assigned_by": str(actor or ""),
        "assigned_at": _utcnow_iso(),
    }
    track_id = str(release_observation.get("track_id") or "")
    existing = [
        item
        for item in list(result.get("short_track_observations") or [])
        if str((item or {}).get("track_id") or "") != track_id
    ]
    existing.append(release_observation)
    result["short_track_observations"] = existing[-200:]
    result["short_track_under_120_count"] = len(result["short_track_observations"])
    result["short_track_under_120_total_seconds"] = sum(
        _safe_int(item.get("duration_seconds")) for item in result["short_track_observations"]
    )
    bucket_counts: dict[str, int] = {}
    for item in result["short_track_observations"]:
        bucket = str(item.get("duration_bucket") or "unknown")
        bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1
    result["short_track_under_120_bucket_counts"] = bucket_counts
    result["short_track_observations_updated_at"] = _utcnow_iso()
    return result
