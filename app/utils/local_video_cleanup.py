from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models.enums import PlaylistStatus
from app.models.playlist import Playlist


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _disk_usage_target(path: Path) -> Path:
    candidate = path
    while not candidate.exists() and candidate != candidate.parent:
        candidate = candidate.parent
    return candidate


def _disk_usage_percent(path: Path, *, usage_provider: Callable[[Path], Any] | None = None) -> float:
    usage = (usage_provider or shutil.disk_usage)(_disk_usage_target(path))
    if hasattr(usage, "total") and hasattr(usage, "used"):
        total = float(usage.total)
        used = float(usage.used)
    else:
        total = float(usage[0])
        used = float(usage[1])
    if total <= 0:
        return 0.0
    return used / total * 100.0


def _youtube_response_status(meta: dict[str, Any]) -> dict[str, Any]:
    response = meta.get("youtube_response")
    if not isinstance(response, dict):
        return {}
    status = response.get("status")
    return status if isinstance(status, dict) else {}


def youtube_public_at(playlist: Playlist, *, now: datetime | None = None) -> datetime | None:
    if playlist.status != PlaylistStatus.uploaded or not playlist.youtube_video_id:
        return None

    current = now or _utcnow()
    meta = dict(playlist.metadata_json or {})
    status = _youtube_response_status(meta)
    privacy_status = str(
        status.get("privacyStatus")
        or meta.get("youtube_privacy_status")
        or meta.get("privacy_status")
        or ""
    ).strip().lower()
    if privacy_status == "public":
        return (
            _parse_datetime(meta.get("youtube_public_at"))
            or _parse_datetime(meta.get("youtube_published_at"))
            or _parse_datetime(status.get("publishAt"))
            or playlist.updated_at
            or playlist.created_at
        )

    scheduled_values = [
        meta.get("youtube_scheduled_publish_at"),
        meta.get("youtube_publish_at"),
        status.get("publishAt"),
    ]
    parsed_schedule = [parsed for value in scheduled_values if (parsed := _parse_datetime(value))]
    public_schedules = [scheduled_at for scheduled_at in parsed_schedule if scheduled_at <= current]
    if public_schedules:
        return min(public_schedules)
    return None


def youtube_uploaded_at(playlist: Playlist, *, now: datetime | None = None) -> datetime | None:
    if playlist.status != PlaylistStatus.uploaded or not playlist.youtube_video_id:
        return None

    meta = dict(playlist.metadata_json or {})
    status = _youtube_response_status(meta)
    uploaded_at = (
        _parse_datetime(meta.get("youtube_uploaded_at"))
        or _parse_datetime(meta.get("youtube_upload_completed_at"))
        or _parse_datetime(meta.get("youtube_published_at"))
        or _parse_datetime(meta.get("uploaded_at"))
        or _parse_datetime(meta.get("youtube_scheduled_publish_at"))
        or _parse_datetime(meta.get("youtube_publish_at"))
        or _parse_datetime(status.get("publishAt"))
        or _parse_datetime(playlist.updated_at)
        or _parse_datetime(playlist.created_at)
    )
    return uploaded_at or now or _utcnow()


@dataclass
class LocalVideoCandidate:
    playlist: Playlist
    path: Path
    public_at: datetime
    eligible_after: datetime
    source: str
    size_bytes: int


@dataclass
class EmergencyLocalVideoCandidate:
    playlist: Playlist
    path: Path
    uploaded_at: datetime
    eligible_after: datetime
    source: str
    size_bytes: int


def _candidate_paths(playlist: Playlist, settings: Settings) -> list[tuple[Path, str]]:
    paths: list[tuple[Path, str]] = []
    output_video_path = str(playlist.output_video_path or "").strip()
    if output_video_path:
        paths.append((Path(output_video_path), "output_video_path"))

    canonical_path = settings.playlists_dir / f"{playlist.id}.mp4"
    if not any(path == canonical_path for path, _source in paths):
        paths.append((canonical_path, "canonical_playlist_mp4"))
    return paths


def collect_public_uploaded_local_video_candidates(
    db: Session,
    settings: Settings,
    *,
    now: datetime | None = None,
) -> list[LocalVideoCandidate]:
    current = now or _utcnow()
    retention_days = max(int(settings.local_video_cleanup_public_retention_days or 0), 0)
    retention = timedelta(days=retention_days)
    candidates: list[LocalVideoCandidate] = []
    playlists = db.scalars(
        select(Playlist).where(
            Playlist.status == PlaylistStatus.uploaded,
            Playlist.youtube_video_id.is_not(None),
        )
    ).all()
    seen_paths: set[Path] = set()
    for playlist in playlists:
        public_at = youtube_public_at(playlist, now=current)
        if public_at is None:
            continue
        eligible_after = public_at + retention
        if eligible_after > current:
            continue
        for path, source in _candidate_paths(playlist, settings):
            try:
                resolved = path.resolve()
            except OSError:
                resolved = path
            if resolved in seen_paths or not path.exists() or not path.is_file():
                continue
            seen_paths.add(resolved)
            candidates.append(
                LocalVideoCandidate(
                    playlist=playlist,
                    path=path,
                    public_at=public_at,
                    eligible_after=eligible_after,
                    source=source,
                    size_bytes=path.stat().st_size,
                )
            )
    return sorted(candidates, key=lambda item: (item.public_at, item.playlist.updated_at or item.public_at))


def collect_emergency_uploaded_local_video_candidates(
    db: Session,
    settings: Settings,
    *,
    now: datetime | None = None,
) -> list[EmergencyLocalVideoCandidate]:
    current = now or _utcnow()
    min_age_hours = max(float(settings.local_video_cleanup_emergency_min_uploaded_age_hours or 0), 0.0)
    min_age = timedelta(hours=min_age_hours)
    candidates: list[EmergencyLocalVideoCandidate] = []
    playlists = db.scalars(
        select(Playlist).where(
            Playlist.status == PlaylistStatus.uploaded,
            Playlist.youtube_video_id.is_not(None),
        )
    ).all()
    seen_paths: set[Path] = set()
    for playlist in playlists:
        uploaded_at = youtube_uploaded_at(playlist, now=current)
        if uploaded_at > current - min_age:
            continue
        eligible_after = uploaded_at + min_age
        for path, source in _candidate_paths(playlist, settings):
            try:
                resolved = path.resolve()
            except OSError:
                resolved = path
            if resolved in seen_paths or not path.exists() or not path.is_file():
                continue
            seen_paths.add(resolved)
            candidates.append(
                EmergencyLocalVideoCandidate(
                    playlist=playlist,
                    path=path,
                    uploaded_at=uploaded_at,
                    eligible_after=eligible_after,
                    source=source,
                    size_bytes=path.stat().st_size,
                )
            )
    return sorted(candidates, key=lambda item: (item.uploaded_at, item.playlist.updated_at or item.uploaded_at))


def mark_local_video_retained_after_youtube_upload(
    playlist: Playlist,
    meta: dict[str, Any],
    *,
    video_path: str | None,
    settings: Settings,
    now: datetime | None = None,
) -> dict[str, Any]:
    if not video_path:
        return meta
    path = Path(video_path)
    current = now or _utcnow()
    retention_days = max(int(settings.local_video_cleanup_public_retention_days or 0), 0)
    public_at = youtube_public_at(playlist, now=current)
    eligible_after = public_at + timedelta(days=retention_days) if public_at else None
    meta["local_video_retained_after_youtube_upload"] = str(path)
    meta["local_video_retention_policy"] = "delete_after_public_retention"
    meta["local_video_retention_days"] = retention_days
    meta["local_video_retention_recorded_at"] = current.isoformat()
    if eligible_after:
        meta["local_video_cleanup_eligible_after"] = eligible_after.isoformat()
    else:
        meta.pop("local_video_cleanup_eligible_after", None)
    meta.pop("local_video_deleted_after_youtube_upload", None)
    meta.pop("local_video_deleted_at", None)
    meta.pop("local_video_cleanup_error", None)
    return meta


def _delete_local_video_candidate(
    db: Session,
    candidate: LocalVideoCandidate | EmergencyLocalVideoCandidate,
    result: dict[str, Any],
    *,
    current: datetime,
    before_percent: float,
    threshold: float,
    reason: str,
) -> bool:
    path = candidate.path
    try:
        path.unlink()
    except OSError as exc:
        meta = dict(candidate.playlist.metadata_json or {})
        meta["local_video_cleanup_error"] = str(exc)
        meta["local_video_cleanup_error_at"] = current.isoformat()
        candidate.playlist.metadata_json = meta
        db.add(candidate.playlist)
        result["errors"].append(
            {
                "playlist_id": candidate.playlist.id,
                "path": str(path),
                "error": str(exc),
            }
        )
        return False

    if candidate.playlist.output_video_path and Path(candidate.playlist.output_video_path) == path:
        candidate.playlist.output_video_path = None

    meta = dict(candidate.playlist.metadata_json or {})
    history = list(meta.get("local_video_cleanup_history") or [])
    entry = {
        "path": str(path),
        "deleted_at": current.isoformat(),
        "reason": reason,
        "source": candidate.source,
        "size_bytes": candidate.size_bytes,
        "youtube_video_id": candidate.playlist.youtube_video_id,
        "disk_usage_before_percent": round(before_percent, 2),
        "threshold_percent": threshold,
    }
    deleted_entry = {
        "playlist_id": candidate.playlist.id,
        "title": candidate.playlist.title,
        "path": str(path),
        "size_bytes": candidate.size_bytes,
        "source": candidate.source,
        "youtube_video_id": candidate.playlist.youtube_video_id,
    }
    if isinstance(candidate, LocalVideoCandidate):
        entry["youtube_public_at"] = candidate.public_at.isoformat()
        entry["local_video_cleanup_eligible_after"] = candidate.eligible_after.isoformat()
        deleted_entry["youtube_public_at"] = candidate.public_at.isoformat()
        deleted_entry["local_video_cleanup_eligible_after"] = candidate.eligible_after.isoformat()
    else:
        entry["youtube_uploaded_at"] = candidate.uploaded_at.isoformat()
        entry["local_video_cleanup_eligible_after"] = candidate.eligible_after.isoformat()
        deleted_entry["youtube_uploaded_at"] = candidate.uploaded_at.isoformat()
        deleted_entry["local_video_cleanup_eligible_after"] = candidate.eligible_after.isoformat()

    history.append(entry)
    meta["local_video_cleanup_history"] = history
    meta["local_video_deleted_after_youtube_upload"] = str(path)
    meta["local_video_deleted_at"] = current.isoformat()
    meta["local_video_cleanup_reason"] = entry["reason"]
    meta["local_video_cleanup_source"] = candidate.source
    meta["local_video_cleanup_threshold_percent"] = threshold
    meta["local_video_cleanup_disk_usage_before_percent"] = round(before_percent, 2)
    meta.pop("local_video_cleanup_error", None)
    meta.pop("local_video_cleanup_error_at", None)
    candidate.playlist.metadata_json = meta
    db.add(candidate.playlist)
    result["deleted_count"] += 1
    result["deleted_bytes"] += candidate.size_bytes
    result["deleted"].append(deleted_entry)
    return True


def cleanup_public_uploaded_local_videos(
    db: Session,
    settings: Settings,
    *,
    now: datetime | None = None,
    usage_provider: Callable[[Path], Any] | None = None,
) -> dict[str, Any]:
    current = now or _utcnow()
    threshold = float(settings.local_video_cleanup_disk_threshold_percent)
    threshold = max(0.0, min(threshold, 100.0))
    before_percent = _disk_usage_percent(settings.storage_root, usage_provider=usage_provider)
    result: dict[str, Any] = {
        "ok": True,
        "enabled": bool(settings.local_video_cleanup_enabled),
        "threshold_percent": threshold,
        "public_retention_days": max(int(settings.local_video_cleanup_public_retention_days or 0), 0),
        "emergency_enabled": bool(settings.local_video_cleanup_emergency_enabled),
        "emergency_min_uploaded_age_hours": max(
            float(settings.local_video_cleanup_emergency_min_uploaded_age_hours or 0), 0.0
        ),
        "disk_usage_before_percent": round(before_percent, 2),
        "disk_usage_after_percent": round(before_percent, 2),
        "deleted_count": 0,
        "deleted_bytes": 0,
        "deleted": [],
        "errors": [],
        "skipped": False,
    }
    if not settings.local_video_cleanup_enabled:
        result["skipped"] = True
        result["reason"] = "disabled"
        return result
    candidates = collect_public_uploaded_local_video_candidates(db, settings, now=current)
    if before_percent <= threshold and not candidates:
        result["skipped"] = True
        result["reason"] = "below_threshold_no_retention_expired_candidates"
        return result

    for candidate in candidates:
        current_percent = _disk_usage_percent(settings.storage_root, usage_provider=usage_provider)
        if current_percent <= threshold and candidate.eligible_after > current:
            break
        _delete_local_video_candidate(
            db,
            candidate,
            result,
            current=current,
            before_percent=before_percent,
            threshold=threshold,
            reason="public_retention_expired_uploaded_youtube_video",
        )

    after_percent = _disk_usage_percent(settings.storage_root, usage_provider=usage_provider)
    if after_percent > threshold and settings.local_video_cleanup_emergency_enabled:
        emergency_candidates = collect_emergency_uploaded_local_video_candidates(db, settings, now=current)
        result["emergency_candidate_count"] = len(emergency_candidates)
        for candidate in emergency_candidates:
            current_percent = _disk_usage_percent(settings.storage_root, usage_provider=usage_provider)
            if current_percent <= threshold:
                break
            _delete_local_video_candidate(
                db,
                candidate,
                result,
                current=current,
                before_percent=before_percent,
                threshold=threshold,
                reason="emergency_disk_pressure_uploaded_youtube_video",
            )
        after_percent = _disk_usage_percent(settings.storage_root, usage_provider=usage_provider)
    elif after_percent > threshold:
        result["emergency_candidate_count"] = 0

    result["disk_usage_after_percent"] = round(after_percent, 2)
    if result["deleted_count"] == 0:
        result["skipped"] = True
        if candidates:
            result["reason"] = "above_threshold_cleanup_candidates_failed"
        elif settings.local_video_cleanup_emergency_enabled:
            result["reason"] = "above_threshold_no_cleanup_candidates"
        else:
            result["reason"] = "above_threshold_no_retention_expired_candidates"
    for candidate in result["deleted"]:
        playlist = db.get(Playlist, candidate["playlist_id"])
        if playlist:
            meta = dict(playlist.metadata_json or {})
            meta["local_video_cleanup_disk_usage_after_percent"] = round(after_percent, 2)
            playlist.metadata_json = meta
            db.add(playlist)
    db.commit()
    return result
