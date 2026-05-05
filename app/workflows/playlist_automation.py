from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.enums import JobStatus, JobType, PlaylistStatus, TrackStatus
from app.models.job import Job
from app.models.playlist import Playlist, PlaylistItem
from app.models.track import Track
from app.schemas.playlist import PlaylistJobRead, PlaylistTrackRead, PlaylistWorkspaceRead
from app.services.registry import ServiceRegistry
from app.utils.youtube_localizations import (
    DEFAULT_YOUTUBE_LANGUAGE,
    ensure_playlist_localization_title_prefix,
    ensure_playlist_title_prefix,
    normalize_youtube_language,
    normalize_youtube_localizations,
    sanitize_youtube_copy,
)


ARCHIVE_RETENTION_DAYS = 7
FAILED_WORKFLOW_STATES = {
    "render_failed",
    "video_build_failed",
    "youtube_upload_failed",
    "publish_failed",
}
FALLBACK_DESCRIPTION_HASHTAGS = ["AIMusic", "Playlist", "BackgroundMusic", "Visualizer"]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _default_target_duration_seconds(services: ServiceRegistry) -> int:
    return services.settings.playlist_target_minutes * 60


def _playlist_meta(playlist: Playlist) -> dict:
    return dict(playlist.metadata_json or {})


def _resolve_youtube_channel_title(services: ServiceRegistry, channel_id: str | None) -> str | None:
    if not channel_id:
        return None
    try:
        channel = services.youtube.get_channel(channel_id)
    except Exception:  # noqa: BLE001
        return None
    if not channel:
        return None
    title = str(channel.get("title") or "").strip()
    return title or None


def _store_youtube_channel_metadata(
    meta: dict,
    services: ServiceRegistry,
    *,
    channel_id: str | None,
) -> None:
    if not channel_id:
        return
    meta["youtube_channel_id"] = channel_id
    channel_title = _resolve_youtube_channel_title(services, channel_id)
    if channel_title:
        meta["youtube_channel_title"] = channel_title


def _parse_metadata_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _archive_purge_after(archived_at: datetime) -> datetime:
    return archived_at + timedelta(days=ARCHIVE_RETENTION_DAYS)


def _normalize_youtube_tags(tags: list[str] | str) -> list[str]:
    if isinstance(tags, str):
        candidates = tags.split(",")
    else:
        candidates = tags
    normalized: list[str] = []
    seen: set[str] = set()
    for tag in candidates:
        value = str(tag).strip().lstrip("#").strip()
        if not value:
            continue
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(value)
    return normalized[:15]


def _hashtag_from_tag(tag: str) -> str | None:
    value = "".join(character for character in str(tag).strip().lstrip("#") if character.isalnum() or character == "_")
    if not value:
        return None
    return f"#{value}"


def _description_hashtag_line(tags: list[str] | str | None) -> str:
    normalized_tags = _normalize_youtube_tags(tags or FALLBACK_DESCRIPTION_HASHTAGS)
    hashtags: list[str] = []
    seen: set[str] = set()
    for tag in [*normalized_tags, *FALLBACK_DESCRIPTION_HASHTAGS]:
        hashtag = _hashtag_from_tag(tag)
        if not hashtag:
            continue
        key = hashtag.lower()
        if key in seen:
            continue
        seen.add(key)
        hashtags.append(hashtag)
        if len(hashtags) >= 8:
            break
    return " ".join(hashtags)


def _description_has_hashtag_line(description: str) -> bool:
    lines = [line.strip() for line in str(description or "").splitlines() if line.strip()]
    for line in lines[-4:]:
        if sum(1 for token in line.split() if token.startswith("#") and len(token) > 1) >= 2:
            return True
    return False


def _ensure_description_hashtags(description: str, tags: list[str] | str | None) -> str:
    description = str(description or "").strip()
    if not description or _description_has_hashtag_line(description):
        return description
    hashtag_line = _description_hashtag_line(tags)
    return f"{description}\n\n{hashtag_line}" if hashtag_line else description


def _workspace_mode(playlist: Playlist) -> str:
    return str(_playlist_meta(playlist).get("workspace_mode") or "playlist")


def _auto_publish_when_ready(playlist: Playlist) -> bool:
    return bool(_playlist_meta(playlist).get("auto_publish_when_ready"))


def _publish_is_ready(playlist: Playlist) -> bool:
    mode = _workspace_mode(playlist)
    if mode == "single_track_video":
        return len(playlist.items) == 1
    return playlist.actual_duration_seconds >= playlist.target_duration_seconds


def _final_publish_is_ready(playlist: Playlist) -> bool:
    meta = _playlist_meta(playlist)
    return bool(
        playlist.output_audio_path
        and playlist.output_video_path
        and meta.get("cover_image_path")
        and meta.get("cover_approved")
        and meta.get("youtube_title")
        and meta.get("metadata_approved")
    )


def _has_local_audio(track: Track) -> bool:
    if not track.audio_path:
        return False
    if track.audio_path.startswith(("http://", "https://")):
        return False
    return Path(track.audio_path).exists()


def _track_payload(track: Track) -> PlaylistTrackRead:
    metadata = track.metadata_json or {}
    return PlaylistTrackRead(
        id=track.id,
        title=track.title,
        prompt=track.prompt,
        duration_seconds=track.duration_seconds,
        audio_path=track.audio_path,
        preview_url=track.preview_url,
        image_url=metadata.get("image_url"),
        tags=metadata.get("tags"),
        lyrics=str(metadata.get("lyrics") or ""),
        style=str(metadata.get("style") or ""),
    )


def _latest_render_job(playlist: Playlist) -> PlaylistJobRead | None:
    jobs = [
        job
        for job in playlist.jobs
        if job.type in {JobType.build_playlist, JobType.build_video}
    ]
    if not jobs:
        return None

    active_jobs = [job for job in jobs if job.status in {JobStatus.queued, JobStatus.running}]
    job = max(active_jobs or jobs, key=lambda candidate: candidate.created_at)
    result = job.result_json or {}
    return PlaylistJobRead(
        id=job.id,
        type=job.type.value,
        status=job.status.value,
        source=job.source,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        error_text=job.error_text,
        output_audio_path=result.get("output_audio_path"),
        output_video_path=result.get("output_video_path"),
        progress=result.get("progress"),
    )


def _cover_source(meta: dict) -> str | None:
    cover_image_path = meta.get("cover_image_path")
    if not cover_image_path:
        return None
    if meta.get("cover_source"):
        return str(meta["cover_source"])
    for entry in reversed(list(meta.get("cover_history") or [])):
        if entry.get("cover_image_path") != cover_image_path:
            continue
        if entry.get("source"):
            return str(entry["source"])
        if entry.get("generated_at"):
            return "generated-draft"
    return None


def _youtube_thumbnail_source(meta: dict) -> str | None:
    thumbnail_path = meta.get("youtube_thumbnail_path")
    if not thumbnail_path:
        return None
    if meta.get("youtube_thumbnail_source"):
        return str(meta["youtube_thumbnail_source"])
    for entry in reversed(list(meta.get("youtube_thumbnail_history") or [])):
        if entry.get("thumbnail_path") == thumbnail_path and entry.get("source"):
            return str(entry["source"])
    return None


def _loop_video_source(meta: dict) -> str | None:
    loop_video_path = meta.get("loop_video_path")
    if not loop_video_path:
        return None
    if meta.get("loop_video_source"):
        return str(meta["loop_video_source"])
    for entry in reversed(list(meta.get("loop_video_history") or [])):
        if entry.get("loop_video_path") == loop_video_path and entry.get("source"):
            return str(entry["source"])
    return None


def serialize_playlist_workspace(playlist: Playlist) -> PlaylistWorkspaceRead:
    meta = _playlist_meta(playlist)
    tracks = [
        _track_payload(item.track)
        for item in sorted(playlist.items, key=lambda item: item.order_index)
        if item.track is not None
    ]
    progress_ratio = 0.0
    if _workspace_mode(playlist) == "single_track_video":
        progress_ratio = 1.0 if tracks else 0.0
    elif playlist.target_duration_seconds > 0:
        progress_ratio = min(playlist.actual_duration_seconds / playlist.target_duration_seconds, 1.0)
    return PlaylistWorkspaceRead(
        id=playlist.id,
        title=playlist.title,
        hidden=bool(meta.get("hidden")),
        archived_at=_parse_metadata_datetime(meta.get("archived_at")),
        purge_after=_parse_metadata_datetime(meta.get("purge_after")),
        status=playlist.status,
        workspace_mode=str(meta.get("workspace_mode") or "playlist"),
        auto_publish_when_ready=bool(meta.get("auto_publish_when_ready")),
        target_duration_seconds=playlist.target_duration_seconds,
        actual_duration_seconds=playlist.actual_duration_seconds,
        progress_ratio=progress_ratio,
        description=meta.get("description"),
        cover_prompt=meta.get("cover_prompt"),
        dreamina_prompt=meta.get("dreamina_prompt"),
        workflow_state=meta.get("workflow_state", "collecting"),
        publish_ready=bool(meta.get("publish_ready")),
        publish_approved=bool(meta.get("publish_approved")),
        cover_approved=bool(meta.get("cover_approved")),
        metadata_approved=bool(meta.get("metadata_approved")),
        output_audio_path=playlist.output_audio_path,
        output_video_path=playlist.output_video_path,
        cover_image_path=meta.get("cover_image_path"),
        cover_source=_cover_source(meta),
        loop_video_path=meta.get("loop_video_path"),
        loop_video_source=_loop_video_source(meta),
        loop_video_smooth=bool(meta.get("loop_video_smooth", True)),
        youtube_thumbnail_path=meta.get("youtube_thumbnail_path"),
        youtube_thumbnail_source=_youtube_thumbnail_source(meta),
        youtube_title=meta.get("youtube_title"),
        youtube_description=meta.get("youtube_description"),
        youtube_tags=list(meta.get("youtube_tags") or []),
        youtube_localizations=normalize_youtube_localizations(
            meta.get("youtube_localizations"),
            default_title=meta.get("youtube_title"),
            default_description=meta.get("youtube_description"),
            default_language=str(meta.get("youtube_default_language") or DEFAULT_YOUTUBE_LANGUAGE),
        ),
        youtube_default_language=normalize_youtube_language(meta.get("youtube_default_language")),
        metadata_provider=meta.get("metadata_provider"),
        metadata_generation_error=meta.get("metadata_generation_error"),
        youtube_video_id=playlist.youtube_video_id,
        youtube_channel_id=meta.get("youtube_channel_id"),
        youtube_channel_title=meta.get("youtube_channel_title"),
        note=meta.get("note"),
        render_job=_latest_render_job(playlist),
        created_at=playlist.created_at,
        updated_at=playlist.updated_at,
        tracks=tracks,
    )


def list_playlist_workspaces(db: Session) -> list[Playlist]:
    purge_expired_archived_workspaces(db)
    return db.scalars(
        select(Playlist)
        .options(
            selectinload(Playlist.items).selectinload(PlaylistItem.track),
            selectinload(Playlist.jobs),
        )
        .order_by(Playlist.updated_at.desc())
    ).all()


def _metadata_path_values(value: object, *, key: str | None = None) -> list[str]:
    if isinstance(value, dict):
        paths: list[str] = []
        for child_key, child_value in value.items():
            paths.extend(_metadata_path_values(child_value, key=str(child_key)))
        return paths
    if isinstance(value, list):
        paths = []
        for item in value:
            paths.extend(_metadata_path_values(item, key=key))
        return paths
    if isinstance(value, str) and key and key.endswith("_path"):
        return [value]
    return []


def _delete_local_path(path_value: str | None) -> None:
    if not path_value or path_value.startswith(("http://", "https://")):
        return
    path = Path(path_value)
    if not path.is_file():
        return
    try:
        path.unlink()
    except OSError:
        return


def _archived_playlist_is_purgeable(playlist: Playlist, *, now: datetime) -> bool:
    meta = _playlist_meta(playlist)
    if not meta.get("hidden"):
        return False
    if any(job.status in {JobStatus.queued, JobStatus.running} for job in playlist.jobs):
        return False
    purge_after = _parse_metadata_datetime(meta.get("purge_after"))
    if purge_after is None:
        archived_at = _parse_metadata_datetime(meta.get("archived_at"))
        if archived_at is None:
            return False
        purge_after = _archive_purge_after(archived_at)
    return purge_after <= now


def purge_expired_archived_workspaces(db: Session, *, now: datetime | None = None) -> int:
    now = now or _utcnow()
    playlists = db.scalars(
        select(Playlist).options(
            selectinload(Playlist.items),
            selectinload(Playlist.jobs),
        )
    ).all()
    purged = 0
    for playlist in playlists:
        if not _archived_playlist_is_purgeable(playlist, now=now):
            continue

        meta = _playlist_meta(playlist)
        for path_value in {
            playlist.output_audio_path,
            playlist.output_video_path,
            *_metadata_path_values(meta),
        }:
            _delete_local_path(path_value)
        for job in list(playlist.jobs):
            db.delete(job)
        for item in list(playlist.items):
            db.delete(item)
        db.delete(playlist)
        purged += 1
    if purged:
        db.commit()
    return purged


def _load_playlist_with_tracks(db: Session, playlist_id: str) -> Playlist | None:
    return db.scalars(
        select(Playlist)
        .options(
            selectinload(Playlist.items).selectinload(PlaylistItem.track),
            selectinload(Playlist.jobs),
        )
        .where(Playlist.id == playlist_id)
    ).first()


def create_playlist_workspace(
    db: Session,
    *,
    title: str,
    target_duration_seconds: int,
    workspace_mode: str = "playlist",
    auto_publish_when_ready: bool | None = None,
    description: str | None = None,
    cover_prompt: str | None = None,
    dreamina_prompt: str | None = None,
) -> Playlist:
    normalized_mode = workspace_mode if workspace_mode in {"playlist", "single_track_video"} else "playlist"
    if normalized_mode == "single_track_video":
        target_duration_seconds = 1
    auto_publish = auto_publish_when_ready
    if auto_publish is None:
        auto_publish = False

    playlist = Playlist(
        title=title,
        status=PlaylistStatus.draft,
        target_duration_seconds=target_duration_seconds,
        actual_duration_seconds=0,
        metadata_json={
            "workspace_mode": normalized_mode,
            "auto_publish_when_ready": auto_publish,
            "description": description,
            "cover_prompt": cover_prompt,
            "dreamina_prompt": dreamina_prompt,
            "workflow_state": "collecting",
            "publish_ready": False,
            "publish_approved": False,
            "cover_approved": False,
            "metadata_approved": False,
        },
    )
    db.add(playlist)
    db.commit()
    db.refresh(playlist)
    return playlist


def set_playlist_workspace_archive_state(
    db: Session,
    *,
    playlist_id: str,
    actor: str,
    archived: bool,
    revive_rejected: bool = True,
) -> Playlist:
    playlist = _load_playlist_with_tracks(db, playlist_id)
    if not playlist:
        raise ValueError("Playlist not found")

    meta = _playlist_meta(playlist)
    history = list(meta.get("archive_history") or [])
    history.append(
        {
            "actor": actor,
            "archived": archived,
            "decided_at": _utcnow().isoformat(),
        }
    )
    meta["archive_history"] = history
    meta["hidden"] = archived
    if archived:
        now = _utcnow()
        previous_workflow_state = meta.get("workflow_state")
        if previous_workflow_state != "archived":
            meta["pre_archive_workflow_state"] = previous_workflow_state
            meta["pre_archive_status"] = playlist.status.value
            meta["pre_archive_note"] = meta.get("note")
        purge_after = _archive_purge_after(now)
        meta["archived_at"] = now.isoformat()
        meta["purge_after"] = purge_after.isoformat()
        meta["archived_by"] = actor
        meta["archive_retention_days"] = ARCHIVE_RETENTION_DAYS
        meta["workflow_state"] = "archived"
        if previous_workflow_state in FAILED_WORKFLOW_STATES or playlist.status == PlaylistStatus.failed:
            meta["note"] = "Failed release archived. It will be permanently deleted after 7 days unless restored."
        else:
            meta["note"] = "Release archived. It will be permanently deleted after 7 days unless restored."
    else:
        meta.pop("archived_at", None)
        meta.pop("purge_after", None)
        meta.pop("archived_by", None)
        meta.pop("archive_retention_days", None)
        previous_workflow_state = meta.pop("pre_archive_workflow_state", None)
        previous_status = meta.pop("pre_archive_status", None)
        previous_note = meta.pop("pre_archive_note", None)
        if not playlist.items:
            meta["workflow_state"] = previous_workflow_state or "collecting"
            meta["publish_ready"] = False
        elif previous_workflow_state:
            meta["workflow_state"] = previous_workflow_state
        meta["note"] = "Release restored from archive."
        if previous_note and previous_workflow_state in FAILED_WORKFLOW_STATES:
            meta["note"] = previous_note
        if previous_status:
            try:
                playlist.status = PlaylistStatus(previous_status)
            except ValueError:
                pass
        if revive_rejected:
            for track in _workspace_candidate_tracks(db, playlist.id):
                if track.status == TrackStatus.rejected:
                    track.status = TrackStatus.pending_review
                    track.reviewed_at = None
                    db.add(track)
    playlist.metadata_json = meta
    db.add(playlist)
    db.commit()
    return _load_playlist_with_tracks(db, playlist.id)


def maybe_archive_rejected_single_workspace(
    db: Session,
    *,
    playlist_id: str | None,
    actor: str,
) -> Playlist | None:
    if not playlist_id:
        return None
    playlist = _load_playlist_with_tracks(db, playlist_id)
    if not playlist:
        return None
    meta = _playlist_meta(playlist)
    if _workspace_mode(playlist) != "single_track_video" or meta.get("hidden") or playlist.items:
        return None

    candidates = _workspace_candidate_tracks(db, playlist.id)
    if not candidates:
        return None
    if any(track.status in {TrackStatus.pending_review, TrackStatus.held, TrackStatus.approved} for track in candidates):
        return None
    if not all(track.status == TrackStatus.rejected for track in candidates):
        return None

    return set_playlist_workspace_archive_state(
        db,
        playlist_id=playlist.id,
        actor=actor,
        archived=True,
        revive_rejected=False,
    )


def _refresh_playlist_duration(playlist: Playlist) -> None:
    playlist.actual_duration_seconds = sum(
        max(item.included_duration_seconds, 0) for item in playlist.items
    )


def _playlist_tracks(playlist: Playlist) -> list[Track]:
    return [
        item.track
        for item in sorted(playlist.items, key=lambda item: item.order_index)
        if item.track is not None
    ]


def _playlist_track_ids(playlist: Playlist) -> list[str]:
    return [
        item.track_id
        for item in sorted(playlist.items, key=lambda item: item.order_index)
        if item.track_id
    ]


def _rendered_audio_matches_current_tracks(playlist: Playlist) -> bool:
    rendered_track_ids = (playlist.metadata_json or {}).get("rendered_track_ids")
    if not rendered_track_ids:
        return True
    return list(rendered_track_ids) == _playlist_track_ids(playlist)


def _invalidate_playlist_render_after_content_change(playlist: Playlist) -> None:
    meta = _playlist_meta(playlist)
    rendered_workflow_states = {
        "rendering",
        "render_queued",
        "audio_ready",
        "rendered",
        "video_required",
        "video_queued",
        "video_rendering",
        "metadata_review",
        "publish_ready",
        "publish_queued",
        "uploaded",
    }
    has_rendered_state = bool(
        playlist.output_audio_path
        or playlist.output_video_path
        or playlist.youtube_video_id
        or meta.get("render_ready")
        or meta.get("metadata_approved")
        or meta.get("publish_approved")
        or meta.get("rendered_track_ids")
        or meta.get("rendered_video_track_ids")
        or meta.get("workflow_state") in rendered_workflow_states
    )
    if not has_rendered_state:
        return

    playlist.output_audio_path = None
    playlist.output_video_path = None
    playlist.youtube_video_id = None
    meta["render_ready"] = False
    meta["metadata_approved"] = False
    meta["publish_approved"] = False
    meta["workflow_state"] = "pending_audio_render"
    meta["note"] = "Track list changed. Re-render audio/video before publishing."
    for key in (
        "rendered_track_ids",
        "rendered_track_count",
        "rendered_duration_seconds",
        "rendered_video_track_ids",
        "rendered_video_track_count",
        "youtube_title",
        "youtube_description",
        "youtube_tags",
        "youtube_localizations",
        "youtube_default_language",
        "publish_approved_by",
    ):
        meta.pop(key, None)
    playlist.metadata_json = meta


def _all_tracks_renderable(playlist: Playlist) -> bool:
    tracks = _playlist_tracks(playlist)
    return bool(tracks) and all(_has_local_audio(track) for track in tracks)


def _workspace_candidate_tracks(db: Session, playlist_id: str) -> list[Track]:
    tracks = db.scalars(select(Track).order_by(Track.created_at.asc())).all()
    return [
        track
        for track in tracks
        if (track.metadata_json or {}).get("pending_workspace_id") == playlist_id
    ]


def _clear_downstream_release_assets(playlist: Playlist, meta: dict) -> None:
    meta["cover_approved"] = False
    meta["metadata_approved"] = False
    meta["publish_approved"] = False
    meta.pop("cover_image_path", None)
    meta.pop("youtube_title", None)
    meta.pop("youtube_description", None)
    meta.pop("youtube_tags", None)
    meta.pop("youtube_localizations", None)
    meta.pop("youtube_default_language", None)
    meta.pop("publish_approved_by", None)
    meta.pop("video_build_error", None)
    playlist.output_video_path = None
    playlist.youtube_video_id = None


def _track_cover_path(track: Track) -> str | None:
    image_url = (track.metadata_json or {}).get("image_url")
    if not image_url or str(image_url).startswith(("http://", "https://")):
        return None
    path = Path(str(image_url))
    return str(path) if path.exists() else None


def _promote_single_release_cover_from_track(playlist: Playlist, track: Track, meta: dict) -> bool:
    cover_path = _track_cover_path(track)
    if not cover_path:
        return False

    history = list(meta.get("cover_history") or [])
    if not any(item.get("cover_image_path") == cover_path for item in history):
        history.append(
            {
                "actor": "system:track-cover",
                "track_id": track.id,
                "cover_image_path": cover_path,
                "uploaded_at": _utcnow().isoformat(),
                "source": "track-upload",
            }
        )
    meta["cover_history"] = history
    meta["cover_image_path"] = cover_path
    meta["cover_approved"] = False
    meta["metadata_approved"] = False
    meta["publish_approved"] = False
    meta["workflow_state"] = "cover_review"
    meta["note"] = "Single audio and uploaded cover are ready. Review and approve cover next."
    return True


def _promote_single_release_audio(
    playlist: Playlist,
    track: Track,
    *,
    reset_downstream_assets: bool,
) -> bool:
    if _workspace_mode(playlist) != "single_track_video":
        return False

    meta = _playlist_meta(playlist)
    _refresh_playlist_duration(playlist)
    if not _has_local_audio(track):
        playlist.output_audio_path = None
        playlist.output_video_path = None
        playlist.youtube_video_id = None
        playlist.status = PlaylistStatus.draft
        meta["publish_ready"] = bool(playlist.items)
        meta["render_ready"] = False
        meta["workflow_state"] = "pending_audio_source"
        meta["render_error"] = "Single release audio must be uploaded as a local file before cover/video rendering."
        meta["note"] = "This single release needs a local uploaded audio file before cover and video steps."
        playlist.metadata_json = meta
        return False

    if playlist.output_audio_path != track.audio_path:
        reset_downstream_assets = True

    playlist.output_audio_path = track.audio_path
    playlist.status = PlaylistStatus.ready
    meta["publish_ready"] = True
    meta["render_ready"] = True
    meta["workflow_state"] = "audio_ready"
    meta["note"] = "Single audio is ready. Upload or approve cover next."
    meta.pop("render_error", None)
    if reset_downstream_assets:
        _clear_downstream_release_assets(playlist, meta)
    if _promote_single_release_cover_from_track(playlist, track, meta):
        playlist.output_video_path = None
        playlist.youtube_video_id = None
    playlist.metadata_json = meta
    return True


def _sync_single_release_audio_state(
    playlist: Playlist,
    *,
    reset_downstream_assets: bool,
) -> bool:
    if _workspace_mode(playlist) != "single_track_video":
        return False

    tracks = _playlist_tracks(playlist)
    if not tracks:
        return False
    if len(tracks) == 1:
        return _promote_single_release_audio(
            playlist,
            tracks[0],
            reset_downstream_assets=reset_downstream_assets,
        )

    meta = _playlist_meta(playlist)
    _refresh_playlist_duration(playlist)
    if reset_downstream_assets:
        _clear_downstream_release_assets(playlist, meta)
    playlist.output_audio_path = None
    playlist.output_video_path = None
    playlist.youtube_video_id = None
    playlist.status = PlaylistStatus.draft
    meta["publish_ready"] = False
    meta["render_ready"] = False
    meta["workflow_state"] = "needs_single_selection"
    meta["render_error"] = "Single Release can publish only one selected track. Move extra approved tracks into separate Single Releases."
    meta["note"] = "This Single Release has multiple approved tracks. Publish each good Suno output as its own Single Release instead of combining them."
    playlist.metadata_json = meta
    return True


def _create_split_single_release_for_track(
    db: Session,
    *,
    source_playlist: Playlist,
    track: Track,
    actor: str,
) -> Playlist:
    source_meta = _playlist_meta(source_playlist)
    title = track.title or f"{source_playlist.title} Single"
    playlist = Playlist(
        title=title,
        status=PlaylistStatus.draft,
        target_duration_seconds=1,
        actual_duration_seconds=0,
        metadata_json={
            "workspace_mode": "single_track_video",
            "auto_publish_when_ready": bool(source_meta.get("auto_publish_when_ready")),
            "description": f"Split from {source_playlist.title} after multiple Suno candidates were approved.",
            "cover_prompt": "",
            "dreamina_prompt": "",
            "workflow_state": "collecting",
            "publish_ready": False,
            "publish_approved": False,
            "cover_approved": False,
            "metadata_approved": False,
            "split_from_release_id": source_playlist.id,
            "split_from_release_title": source_playlist.title,
        },
    )
    db.add(playlist)
    db.flush()
    db.add(
        PlaylistItem(
            playlist_id=playlist.id,
            track_id=track.id,
            order_index=1,
            included_duration_seconds=track.duration_seconds,
        )
    )
    db.flush()
    db.refresh(playlist)

    assignment_history = [
        {
            "track_id": track.id,
            "actor": actor,
            "assigned_at": _utcnow().isoformat(),
            "split_from_release_id": source_playlist.id,
        }
    ]
    _promote_single_release_audio(playlist, track, reset_downstream_assets=True)
    meta = _playlist_meta(playlist)
    meta["assignment_history"] = assignment_history
    meta["split_from_release_id"] = source_playlist.id
    meta["split_from_release_title"] = source_playlist.title
    meta["note"] = "Approved as its own Single Release because the source candidate set already has a selected track."
    playlist.metadata_json = meta

    track_meta = dict(track.metadata_json or {})
    track_meta["pending_workspace_id"] = playlist.id
    track_meta["pending_workspace_title"] = playlist.title
    track_meta["split_from_release_id"] = source_playlist.id
    track.metadata_json = track_meta
    db.add(track)
    db.add(playlist)
    db.flush()
    return playlist


def _find_active_playlist_job(
    db: Session,
    playlist: Playlist,
) -> Job | None:
    return db.scalars(
        select(Job).where(
            Job.playlist_id == playlist.id,
            Job.type == JobType.build_playlist,
            Job.status.in_([JobStatus.queued, JobStatus.running]),
        )
    ).first()


def _queue_playlist_render_job(
    db: Session,
    playlist: Playlist,
    *,
    source: str,
    trigger: str,
) -> Job | None:
    if not _all_tracks_renderable(playlist):
        return None
    if playlist.output_audio_path and Path(playlist.output_audio_path).exists():
        return None

    active_job = _find_active_playlist_job(db, playlist)
    if active_job:
        return active_job

    job = Job(
        type=JobType.build_playlist,
        status=JobStatus.queued,
        source=source,
        payload_json={
            "playlist_id": playlist.id,
            "trigger": trigger,
        },
        result_json={},
        playlist=playlist,
    )
    db.add(job)
    return job


def _find_active_video_job(
    db: Session,
    playlist: Playlist,
) -> Job | None:
    return db.scalars(
        select(Job).where(
            Job.playlist_id == playlist.id,
            Job.type == JobType.build_video,
            Job.status.in_([JobStatus.queued, JobStatus.running]),
        )
    ).first()


def generate_playlist_cover(
    db: Session,
    services: ServiceRegistry,
    *,
    playlist_id: str,
    actor: str,
    regenerate: bool = False,
) -> Playlist:
    playlist = _load_playlist_with_tracks(db, playlist_id)
    if not playlist:
        raise ValueError("Playlist not found")
    if not playlist.output_audio_path or not Path(playlist.output_audio_path).exists():
        raise ValueError("Rendered audio is required before generating cover art.")

    meta = _playlist_meta(playlist)
    if meta.get("cover_image_path") and meta.get("cover_approved") and not regenerate:
        raise ValueError("Cover is already approved. Regenerate only if you want to replace it.")

    cover_image_path = services.cover_art.generate_cover(playlist)
    history = list(meta.get("cover_history") or [])
    history.append(
        {
            "actor": actor,
            "cover_image_path": cover_image_path,
            "generated_at": _utcnow().isoformat(),
        }
    )
    meta["cover_history"] = history
    meta["cover_image_path"] = cover_image_path
    meta["cover_source"] = "generated-draft"
    meta["cover_approved"] = False
    meta["metadata_approved"] = False
    meta["publish_approved"] = False
    meta["workflow_state"] = "cover_review"
    meta["note"] = "Cover image generated. Review and approve it before rendering video."
    meta.pop("publish_approved_by", None)
    playlist.output_video_path = None
    playlist.youtube_video_id = None
    playlist.metadata_json = meta
    playlist.status = PlaylistStatus.ready
    db.add(playlist)
    db.commit()
    return _load_playlist_with_tracks(db, playlist.id)


def attach_uploaded_playlist_cover(
    db: Session,
    *,
    playlist_id: str,
    actor: str,
    cover_image_path: str,
) -> Playlist:
    playlist = _load_playlist_with_tracks(db, playlist_id)
    if not playlist:
        raise ValueError("Playlist not found")
    if not playlist.output_audio_path or not Path(playlist.output_audio_path).exists():
        raise ValueError("Rendered audio is required before uploading cover art.")
    if not Path(cover_image_path).exists():
        raise ValueError("Uploaded cover image is missing on disk.")

    meta = _playlist_meta(playlist)
    history = list(meta.get("cover_history") or [])
    history.append(
        {
            "actor": actor,
            "cover_image_path": cover_image_path,
            "uploaded_at": _utcnow().isoformat(),
            "source": "manual-upload",
        }
    )
    meta["cover_history"] = history
    meta["cover_image_path"] = cover_image_path
    meta["cover_source"] = "manual-upload"
    meta["cover_approved"] = False
    meta["metadata_approved"] = False
    meta["publish_approved"] = False
    meta["workflow_state"] = "cover_review"
    meta["note"] = "Cover image uploaded. Review and approve it before rendering video."
    meta.pop("publish_approved_by", None)
    playlist.output_video_path = None
    playlist.youtube_video_id = None
    playlist.metadata_json = meta
    playlist.status = PlaylistStatus.ready
    db.add(playlist)
    db.commit()
    return _load_playlist_with_tracks(db, playlist.id)


def attach_uploaded_playlist_thumbnail(
    db: Session,
    *,
    playlist_id: str,
    actor: str,
    thumbnail_path: str,
) -> Playlist:
    playlist = _load_playlist_with_tracks(db, playlist_id)
    if not playlist:
        raise ValueError("Playlist not found")
    if not Path(thumbnail_path).exists():
        raise ValueError("Uploaded thumbnail image is missing on disk.")

    meta = _playlist_meta(playlist)
    history = list(meta.get("youtube_thumbnail_history") or [])
    history.append(
        {
            "actor": actor,
            "thumbnail_path": thumbnail_path,
            "uploaded_at": _utcnow().isoformat(),
            "source": "manual-upload",
        }
    )
    meta["youtube_thumbnail_history"] = history
    meta["youtube_thumbnail_path"] = thumbnail_path
    meta["youtube_thumbnail_source"] = "manual-upload"
    meta.pop("youtube_thumbnail_upload_error", None)
    playlist.metadata_json = meta
    db.add(playlist)
    db.commit()
    return _load_playlist_with_tracks(db, playlist.id)


def attach_uploaded_loop_video(
    db: Session,
    *,
    playlist_id: str,
    actor: str,
    loop_video_path: str,
    smooth_loop: bool = True,
) -> Playlist:
    playlist = _load_playlist_with_tracks(db, playlist_id)
    if not playlist:
        raise ValueError("Playlist not found")
    if not Path(loop_video_path).exists():
        raise ValueError("Uploaded loop video is missing on disk.")

    meta = _playlist_meta(playlist)
    history = list(meta.get("loop_video_history") or [])
    history.append(
        {
            "actor": actor,
            "loop_video_path": loop_video_path,
            "uploaded_at": _utcnow().isoformat(),
            "source": "manual-upload",
            "smooth_loop": smooth_loop,
        }
    )
    meta["loop_video_history"] = history
    meta["loop_video_path"] = loop_video_path
    meta["loop_video_source"] = "manual-upload"
    meta["loop_video_smooth"] = smooth_loop
    meta["metadata_approved"] = False
    meta["publish_approved"] = False
    if playlist.output_video_path:
        playlist.output_video_path = None
        playlist.youtube_video_id = None
        if playlist.output_audio_path and meta.get("cover_approved"):
            meta["workflow_state"] = "video_required"
        meta["note"] = "Loop video uploaded. Re-render video before publishing."
    elif playlist.output_audio_path and meta.get("cover_approved"):
        meta["workflow_state"] = "video_required"
        meta["note"] = "Loop video uploaded. Re-render video before publishing."
    else:
        meta["note"] = "Loop video uploaded. It will be used during video render."
    playlist.metadata_json = meta
    db.add(playlist)
    db.commit()
    return _load_playlist_with_tracks(db, playlist.id)


def approve_playlist_cover(
    db: Session,
    *,
    playlist_id: str,
    actor: str,
    approved: bool = True,
    note: str | None = None,
) -> Playlist:
    playlist = _load_playlist_with_tracks(db, playlist_id)
    if not playlist:
        raise ValueError("Playlist not found")

    meta = _playlist_meta(playlist)
    cover_image_path = meta.get("cover_image_path")
    if not cover_image_path or not Path(cover_image_path).exists():
        raise ValueError("Cover image is missing. Generate cover art first.")

    history = list(meta.get("cover_approval_history") or [])
    history.append(
        {
            "actor": actor,
            "approved": approved,
            "note": note,
            "decided_at": _utcnow().isoformat(),
        }
    )
    meta["cover_approval_history"] = history
    meta["cover_approved"] = approved
    meta["metadata_approved"] = False
    meta["publish_approved"] = False
    meta["workflow_state"] = "video_required" if approved else "cover_review"
    meta["note"] = note or (
        "Cover approved. Render video next." if approved else "Cover returned for review."
    )
    meta.pop("publish_approved_by", None)
    playlist.output_video_path = None
    playlist.youtube_video_id = None
    playlist.metadata_json = meta
    playlist.status = PlaylistStatus.ready
    db.add(playlist)
    db.commit()
    return _load_playlist_with_tracks(db, playlist.id)


def queue_workspace_video_render(
    db: Session,
    *,
    playlist_id: str,
    actor: str,
) -> Playlist:
    playlist = _load_playlist_with_tracks(db, playlist_id)
    if not playlist:
        raise ValueError("Playlist not found")
    if not playlist.output_audio_path or not Path(playlist.output_audio_path).exists():
        raise ValueError("Rendered audio is required before rendering video.")
    if not _rendered_audio_matches_current_tracks(playlist):
        raise ValueError("Rendered audio is stale because the track list changed. Re-render audio before rendering video.")

    meta = _playlist_meta(playlist)
    cover_image_path = meta.get("cover_image_path")
    if not cover_image_path or not Path(cover_image_path).exists():
        raise ValueError("Approved cover image is required before rendering video.")
    if not meta.get("cover_approved"):
        raise ValueError("Cover image must be approved before rendering video.")

    active_job = _find_active_video_job(db, playlist)
    meta["workflow_state"] = "video_queued"
    meta["metadata_approved"] = False
    meta["publish_approved"] = False
    meta["note"] = "Video render queued from the web dashboard."
    meta.pop("video_build_error", None)
    meta.pop("publish_approved_by", None)
    playlist.output_video_path = None
    playlist.youtube_video_id = None
    playlist.metadata_json = meta
    playlist.status = PlaylistStatus.building
    db.add(playlist)

    if active_job is None:
        db.add(
            Job(
                type=JobType.build_video,
                status=JobStatus.queued,
                source="web:render-video",
                payload_json={
                    "playlist_id": playlist.id,
                    "actor": actor,
                    "trigger": "manual-video-render",
                },
                result_json={},
                playlist=playlist,
            )
        )

    db.commit()
    return _load_playlist_with_tracks(db, playlist.id)


def generate_playlist_metadata(
    db: Session,
    services: ServiceRegistry,
    *,
    playlist_id: str,
    actor: str,
) -> Playlist:
    playlist = _load_playlist_with_tracks(db, playlist_id)
    if not playlist:
        raise ValueError("Playlist not found")
    if not playlist.output_video_path or not Path(playlist.output_video_path).exists():
        raise ValueError("Rendered video is required before generating metadata.")

    tracks = _playlist_tracks(playlist)
    youtube_metadata = services.release_metadata.build_youtube_metadata(playlist, tracks)
    meta = _playlist_meta(playlist)
    is_playlist_release = _workspace_mode(playlist) != "single_track_video"
    history = list(meta.get("metadata_history") or [])
    history.append(
        {
            "actor": actor,
            "generated_at": _utcnow().isoformat(),
            "title": youtube_metadata.title,
            "provider": youtube_metadata.provider,
            "error": youtube_metadata.error,
        }
    )
    meta["metadata_history"] = history
    meta["youtube_title"] = ensure_playlist_title_prefix(
        youtube_metadata.title,
        is_playlist=is_playlist_release,
    )
    meta["youtube_description"] = sanitize_youtube_copy(youtube_metadata.description)
    meta["youtube_tags"] = youtube_metadata.tags
    meta["youtube_default_language"] = normalize_youtube_language(
        getattr(youtube_metadata, "default_language", DEFAULT_YOUTUBE_LANGUAGE)
    )
    meta["youtube_localizations"] = ensure_playlist_localization_title_prefix(
        normalize_youtube_localizations(
            getattr(youtube_metadata, "localizations", {}),
            default_title=youtube_metadata.title,
            default_description=youtube_metadata.description,
            default_language=meta["youtube_default_language"],
        ),
        is_playlist=is_playlist_release,
    )
    meta["youtube_description"] = _ensure_description_hashtags(meta["youtube_description"], meta["youtube_tags"])
    for localized_copy in meta["youtube_localizations"].values():
        localized_copy["description"] = _ensure_description_hashtags(
            localized_copy.get("description") or "",
            meta["youtube_tags"],
        )
    meta["metadata_provider"] = youtube_metadata.provider
    if youtube_metadata.error:
        meta["metadata_generation_error"] = youtube_metadata.error
    else:
        meta.pop("metadata_generation_error", None)
    meta["metadata_approved"] = False
    meta["publish_approved"] = False
    meta["workflow_state"] = "metadata_review"
    if youtube_metadata.error:
        meta["note"] = "YouTube metadata draft generated with template fallback. Review before publishing."
    elif youtube_metadata.provider == "codex":
        meta["note"] = "YouTube metadata draft generated with Codex. Review and approve it before publishing."
    else:
        meta["note"] = "YouTube metadata draft generated. Review and approve it before publishing."
    meta.pop("publish_approved_by", None)
    playlist.metadata_json = meta
    playlist.status = PlaylistStatus.ready
    db.add(playlist)
    db.commit()
    return _load_playlist_with_tracks(db, playlist.id)


def approve_playlist_metadata(
    db: Session,
    *,
    playlist_id: str,
    actor: str,
    title: str | None = None,
    description: str | None = None,
    tags: list[str] | str | None = None,
    localizations: dict[str, dict[str, str]] | None = None,
    default_language: str = DEFAULT_YOUTUBE_LANGUAGE,
    note: str | None = None,
) -> Playlist:
    playlist = _load_playlist_with_tracks(db, playlist_id)
    if not playlist:
        raise ValueError("Playlist not found")
    if not playlist.output_video_path or not Path(playlist.output_video_path).exists():
        raise ValueError("Rendered video is required before approving metadata.")

    meta = _playlist_meta(playlist)
    is_playlist_release = _workspace_mode(playlist) != "single_track_video"
    if title is not None:
        meta["youtube_title"] = ensure_playlist_title_prefix(title, is_playlist=is_playlist_release)
    if description is not None:
        meta["youtube_description"] = sanitize_youtube_copy(description)
    if tags is not None:
        meta["youtube_tags"] = _normalize_youtube_tags(tags)
    default_language = normalize_youtube_language(default_language or meta.get("youtube_default_language"))
    normalized_localizations = normalize_youtube_localizations(
        localizations if localizations is not None else meta.get("youtube_localizations"),
        default_title=meta.get("youtube_title"),
        default_description=meta.get("youtube_description"),
        default_language=default_language,
    )
    normalized_localizations = ensure_playlist_localization_title_prefix(
        normalized_localizations,
        is_playlist=is_playlist_release,
    )
    if normalized_localizations:
        meta["youtube_default_language"] = default_language
        meta["youtube_localizations"] = normalized_localizations
        default_copy = normalized_localizations.get(default_language)
        if default_copy:
            meta["youtube_title"] = default_copy["title"]
            meta["youtube_description"] = default_copy["description"]
    if meta.get("youtube_title"):
        meta["youtube_title"] = ensure_playlist_title_prefix(
            meta.get("youtube_title"),
            is_playlist=is_playlist_release,
        )
    if not meta.get("youtube_title") or not meta.get("youtube_description"):
        raise ValueError("YouTube metadata draft is missing. Generate metadata first.")
    meta["youtube_description"] = _ensure_description_hashtags(
        str(meta.get("youtube_description") or ""),
        meta.get("youtube_tags"),
    )
    if meta.get("youtube_localizations"):
        localized_metadata = ensure_playlist_localization_title_prefix(
            normalize_youtube_localizations(
                meta.get("youtube_localizations"),
                default_title=meta.get("youtube_title"),
                default_description=meta.get("youtube_description"),
                default_language=default_language,
            ),
            is_playlist=is_playlist_release,
        )
        for localized_copy in localized_metadata.values():
            localized_copy["description"] = _ensure_description_hashtags(
                localized_copy.get("description") or "",
                meta.get("youtube_tags"),
            )
        meta["youtube_localizations"] = localized_metadata
        default_copy = localized_metadata.get(default_language)
        if default_copy:
            meta["youtube_title"] = default_copy["title"]
            meta["youtube_description"] = default_copy["description"]

    history = list(meta.get("metadata_approval_history") or [])
    history.append(
        {
            "actor": actor,
            "note": note,
            "approved_at": _utcnow().isoformat(),
        }
    )
    meta["metadata_approval_history"] = history
    meta["metadata_approved"] = True
    meta["publish_ready"] = True
    meta["publish_approved"] = False
    meta["workflow_state"] = "publish_ready"
    meta["note"] = note or "Metadata approved. Final YouTube publish approval is ready."
    meta.pop("publish_approved_by", None)
    playlist.metadata_json = meta
    playlist.status = PlaylistStatus.ready
    db.add(playlist)
    db.commit()
    return _load_playlist_with_tracks(db, playlist.id)


def _queue_publish_job(
    db: Session,
    playlist: Playlist,
    *,
    actor: str,
    note: str | None,
    source: str,
    force_under_target: bool = False,
    youtube_channel_id: str | None = None,
) -> Job | None:
    active_job = db.scalars(
        select(Job).where(
            Job.playlist_id == playlist.id,
            Job.type == JobType.upload_youtube,
            Job.status.in_([JobStatus.queued, JobStatus.running]),
        )
    ).first()
    if active_job:
        return active_job

    meta = _playlist_meta(playlist)
    meta["publish_approved"] = True
    meta["publish_approved_by"] = actor
    meta["workflow_state"] = "publish_queued"
    meta["note"] = note or "Background worker queued cover, video render, and YouTube upload."
    if youtube_channel_id:
        meta["youtube_channel_id"] = youtube_channel_id
    if force_under_target:
        meta["publish_under_target_confirmed"] = True
    playlist.metadata_json = meta
    playlist.status = PlaylistStatus.ready
    db.add(playlist)

    job = Job(
        type=JobType.upload_youtube,
        status=JobStatus.queued,
        source=source,
        payload_json={
            "playlist_id": playlist.id,
            "actor": actor,
            "note": note,
            "force_under_target": force_under_target,
            "youtube_channel_id": youtube_channel_id,
        },
        result_json={},
        playlist=playlist,
    )
    db.add(job)
    return job


def maybe_queue_auto_publish_job(
    db: Session,
    playlist: Playlist,
    *,
    actor: str = "system:auto-publish",
    note: str | None = None,
    source: str = "system:auto-publish",
) -> Job | None:
    meta = _playlist_meta(playlist)
    if not meta.get("publish_ready"):
        return None
    if not _auto_publish_when_ready(playlist):
        return None
    if not _final_publish_is_ready(playlist):
        return None
    if not Path(playlist.output_video_path).exists():
        return None
    return _queue_publish_job(db, playlist, actor=actor, note=note, source=source)


def resume_youtube_publish_after_auth(
    db: Session,
    services: ServiceRegistry,
    *,
    playlist_id: str,
    actor: str = "youtube-oauth",
    youtube_channel_id: str | None = None,
) -> Playlist | None:
    playlist = db.scalars(
        select(Playlist)
        .options(selectinload(Playlist.items).selectinload(PlaylistItem.track))
        .where(Playlist.id == playlist_id)
    ).first()
    if not playlist:
        return None

    meta = _playlist_meta(playlist)
    if playlist.youtube_video_id or not meta.get("publish_approved"):
        return playlist
    if meta.get("workflow_state") not in {"ready_for_youtube_auth", "youtube_upload_failed", "ready_for_youtube"}:
        return playlist
    if not _final_publish_is_ready(playlist):
        return playlist

    return approve_playlist_publish(
        db,
        services,
        playlist=playlist,
        actor=actor,
        note="YouTube connected. Resuming final upload.",
        force_under_target=bool(meta.get("publish_under_target_confirmed")),
        youtube_channel_id=youtube_channel_id,
    )


async def _update_publish_state(
    db: Session,
    services: ServiceRegistry,
    playlist: Playlist,
    *,
    trigger: str,
) -> None:
    meta = _playlist_meta(playlist)
    _refresh_playlist_duration(playlist)
    if _workspace_mode(playlist) == "single_track_video":
        tracks = _playlist_tracks(playlist)
        audio_missing = not playlist.output_audio_path or not Path(playlist.output_audio_path).exists()
        if tracks and (audio_missing or len(tracks) > 1):
            _sync_single_release_audio_state(
                playlist,
                reset_downstream_assets=False,
            )
            meta = _playlist_meta(playlist)
        if len(tracks) > 1:
            playlist.metadata_json = meta
            db.add(playlist)
            db.commit()
            db.refresh(playlist)
            return

    if _publish_is_ready(playlist):
        meta["workflow_state"] = "audio_ready" if playlist.output_audio_path else "pending_audio_render"
        meta["publish_ready"] = True
        meta["publish_ready_trigger"] = trigger
        if _workspace_mode(playlist) == "single_track_video" and not playlist.output_audio_path and not _all_tracks_renderable(playlist):
            meta["workflow_state"] = "pending_audio_source"
            meta["render_ready"] = False
            meta["render_error"] = "Single release audio must be uploaded as local files before cover/video rendering."
            meta["note"] = "This single release needs local uploaded audio before cover and video steps."
            playlist.status = PlaylistStatus.draft
        elif _all_tracks_renderable(playlist):
            if playlist.output_audio_path and Path(playlist.output_audio_path).exists():
                playlist.status = PlaylistStatus.ready
                meta["render_ready"] = True
                meta.pop("render_error", None)
                if meta.get("cover_image_path") and not meta.get("cover_approved"):
                    meta["workflow_state"] = "cover_review"
                    meta["note"] = meta.get("note") or "Cover image uploaded. Review and approve it before rendering video."
                elif meta.get("cover_image_path") and meta.get("cover_approved") and not playlist.output_video_path:
                    meta["workflow_state"] = "video_required"
                    meta["note"] = meta.get("note") or "Cover approved. Render video next."
                else:
                    meta["workflow_state"] = "audio_ready"
                    meta["note"] = meta.get("note") or "Audio render is complete. Generate cover art next."
                if _auto_publish_when_ready(playlist) and _final_publish_is_ready(playlist):
                    meta["publish_approved"] = True
                    meta["publish_approved_by"] = "system:auto-publish"
                    meta["workflow_state"] = "publish_queued"
                    meta["note"] = "Auto-publish queued immediately because the workspace is ready."
                    _queue_publish_job(
                        db,
                        playlist,
                        actor="system:auto-publish",
                        note=meta["note"],
                        source="system:auto-publish",
                    )
            else:
                playlist.status = PlaylistStatus.ready
                meta["render_ready"] = False
                meta.pop("render_error", None)
                meta["note"] = "Playlist reached target duration. Start audio render when all intended tracks are uploaded."
        else:
            meta["render_ready"] = False
            meta["render_error"] = "Some tracks are remote-only and must be uploaded locally before rendering."
            playlist.status = PlaylistStatus.draft
    else:
        meta["workflow_state"] = "collecting"
        meta["publish_ready"] = False
        meta["publish_approved"] = False
        playlist.status = PlaylistStatus.draft

    playlist.metadata_json = meta
    db.add(playlist)
    db.commit()
    db.refresh(playlist)

    if meta.get("publish_ready"):
        installation = services.slack_installations.get_active_installation(db)
        token = installation.bot_token if installation else services.settings.slack_bot_token
        await services.slack.post_ops_message(
            token=token,
            text=(
                f"Playlist `{playlist.title}` reached target duration. "
                "Open the web dashboard and approve publishing when ready."
            ),
        )


async def assign_track_to_playlist(
    db: Session,
    services: ServiceRegistry,
    *,
    track: Track,
    playlist_id: str,
    actor: str,
) -> Playlist:
    playlist = db.scalars(
        select(Playlist)
        .options(selectinload(Playlist.items).selectinload(PlaylistItem.track))
        .where(Playlist.id == playlist_id)
    ).first()
    if not playlist:
        raise ValueError("Playlist not found")

    existing_item = next((item for item in playlist.items if item.track_id == track.id), None)
    if _workspace_mode(playlist) == "single_track_video" and existing_item is None and playlist.items:
        split_playlist = _create_split_single_release_for_track(
            db,
            source_playlist=playlist,
            track=track,
            actor=actor,
        )
        db.commit()
        split_playlist = _load_playlist_with_tracks(db, split_playlist.id)
        await _update_publish_state(db, services, split_playlist, trigger=f"assignment:{track.id}")
        return _load_playlist_with_tracks(db, split_playlist.id)

    content_changed = existing_item is None
    if existing_item is None:
        order_index = (max((item.order_index for item in playlist.items), default=0) + 1)
        db.add(
            PlaylistItem(
                playlist_id=playlist.id,
                track_id=track.id,
                order_index=order_index,
                included_duration_seconds=track.duration_seconds,
            )
        )
        db.flush()
        db.refresh(playlist)

    meta = _playlist_meta(playlist)
    history = list(meta.get("assignment_history") or [])
    history.append(
        {
            "track_id": track.id,
            "actor": actor,
            "assigned_at": _utcnow().isoformat(),
        }
    )
    meta["assignment_history"] = history
    if _workspace_mode(playlist) == "single_track_video":
        _sync_single_release_audio_state(
            playlist,
            reset_downstream_assets=existing_item is None,
        )
        meta = _playlist_meta(playlist)
        meta["assignment_history"] = history
    elif content_changed:
        playlist.metadata_json = meta
        _invalidate_playlist_render_after_content_change(playlist)
        meta = _playlist_meta(playlist)
        meta["assignment_history"] = history
    playlist.metadata_json = meta
    db.add(playlist)
    db.commit()
    db.refresh(playlist)

    playlist = db.scalars(
        select(Playlist)
        .options(selectinload(Playlist.items).selectinload(PlaylistItem.track))
        .where(Playlist.id == playlist.id)
    ).first()
    await _update_publish_state(db, services, playlist, trigger=f"assignment:{track.id}")
    return playlist


def reorder_workspace_tracks(
    db: Session,
    *,
    playlist_id: str,
    track_ids: list[str],
    actor: str,
) -> Playlist:
    playlist = _load_playlist_with_tracks(db, playlist_id)
    if not playlist:
        raise ValueError("Playlist not found")
    if _workspace_mode(playlist) == "single_track_video" and len(track_ids) > 1:
        raise ValueError("Single release can only contain one selected track. Publish additional candidates as separate Single Releases.")

    item_by_track_id = {item.track_id: item for item in playlist.items}
    if len(track_ids) != len(item_by_track_id) or set(track_ids) != set(item_by_track_id):
        raise ValueError("Track order must include every approved track exactly once.")

    for index, track_id in enumerate(track_ids, start=1):
        item = item_by_track_id[track_id]
        item.order_index = index
        db.add(item)

    _refresh_playlist_duration(playlist)
    meta = _playlist_meta(playlist)
    history = list(meta.get("reorder_history") or [])
    history.append(
        {
            "actor": actor,
            "track_ids": track_ids,
            "reordered_at": _utcnow().isoformat(),
        }
    )
    meta["reorder_history"] = history
    if _workspace_mode(playlist) == "single_track_video":
        tracks = _playlist_tracks(playlist)
        if len(tracks) == 1:
            _sync_single_release_audio_state(
                playlist,
                reset_downstream_assets=False,
            )
            meta = _playlist_meta(playlist)
            meta["reorder_history"] = history
            meta["note"] = "Single release keeps the approved source audio directly."
            playlist.metadata_json = meta
            db.add(playlist)
            db.commit()
            return _load_playlist_with_tracks(db, playlist.id)
        if len(tracks) > 1:
            raise ValueError("Single release can only contain one selected track. Publish additional candidates as separate Single Releases.")

    meta["render_ready"] = False
    meta["publish_approved"] = False
    meta["note"] = "Track order changed. Re-render audio to update the playlist file."
    meta["workflow_state"] = "render_required" if playlist.items else "collecting"
    meta.pop("render_error", None)
    meta.pop("cover_image_path", None)
    meta.pop("cover_approved", None)
    meta.pop("metadata_approved", None)
    meta.pop("youtube_title", None)
    meta.pop("youtube_description", None)
    meta.pop("youtube_tags", None)
    meta.pop("youtube_localizations", None)
    meta.pop("youtube_default_language", None)
    meta.pop("publish_approved_by", None)
    playlist.metadata_json = meta
    playlist.output_audio_path = None
    playlist.output_video_path = None
    playlist.youtube_video_id = None
    playlist.status = PlaylistStatus.draft
    db.add(playlist)
    db.commit()
    return _load_playlist_with_tracks(db, playlist.id)


def queue_workspace_audio_render(
    db: Session,
    *,
    playlist_id: str,
    actor: str,
) -> Playlist:
    playlist = _load_playlist_with_tracks(db, playlist_id)
    if not playlist:
        raise ValueError("Playlist not found")
    if not playlist.items:
        raise ValueError("Playlist has no approved tracks to render.")
    if not _all_tracks_renderable(playlist):
        raise ValueError("All approved tracks must be local audio files before rendering.")

    _refresh_playlist_duration(playlist)
    if _workspace_mode(playlist) == "single_track_video":
        tracks = _playlist_tracks(playlist)
        if len(tracks) == 1:
            if not _sync_single_release_audio_state(
                playlist,
                reset_downstream_assets=False,
            ):
                raise ValueError("Single release audio must be uploaded as a local file before cover/video rendering.")
            meta = _playlist_meta(playlist)
            meta["note"] = "Single release uses the approved source audio directly. Upload or approve cover next."
            playlist.metadata_json = meta
            db.add(playlist)
            db.commit()
            return _load_playlist_with_tracks(db, playlist.id)
        if len(tracks) > 1:
            raise ValueError("Single release can only render one selected track. Publish additional candidates as separate Single Releases.")

    active_job = _find_active_playlist_job(db, playlist)
    meta = _playlist_meta(playlist)
    meta["render_ready"] = False
    meta["publish_approved"] = False
    meta["workflow_state"] = "render_queued"
    meta["note"] = "Playlist audio render queued from the web dashboard."
    meta.pop("render_error", None)
    meta.pop("cover_image_path", None)
    meta.pop("cover_approved", None)
    meta.pop("metadata_approved", None)
    meta.pop("youtube_title", None)
    meta.pop("youtube_description", None)
    meta.pop("youtube_tags", None)
    meta.pop("youtube_localizations", None)
    meta.pop("youtube_default_language", None)
    meta.pop("publish_approved_by", None)
    playlist.metadata_json = meta
    playlist.output_audio_path = None
    playlist.output_video_path = None
    playlist.youtube_video_id = None
    playlist.status = PlaylistStatus.building
    db.add(playlist)

    if active_job is None:
        db.add(
            Job(
                type=JobType.build_playlist,
                status=JobStatus.queued,
                source="web:render-audio",
                payload_json={
                    "playlist_id": playlist.id,
                    "actor": actor,
                    "trigger": "manual-render",
                },
                result_json={},
                playlist=playlist,
            )
        )

    db.commit()
    return _load_playlist_with_tracks(db, playlist.id)


async def return_track_to_workspace_queue(
    db: Session,
    services: ServiceRegistry,
    *,
    track: Track,
    playlist_id: str,
    actor: str,
) -> Playlist:
    playlist = db.scalars(
        select(Playlist)
        .options(selectinload(Playlist.items).selectinload(PlaylistItem.track))
        .where(Playlist.id == playlist_id)
    ).first()
    if not playlist:
        raise ValueError("Playlist not found")

    item = next((item for item in playlist.items if item.track_id == track.id), None)
    if item is None:
        raise ValueError("Track is not assigned to the selected playlist")

    playlist.items.remove(item)
    db.delete(item)
    db.flush()

    track.status = TrackStatus.pending_review
    track.reviewed_at = None
    track_meta = dict(track.metadata_json or {})
    track_meta["pending_workspace_id"] = playlist.id
    track_meta["pending_workspace_title"] = playlist.title
    track.metadata_json = track_meta
    db.add(track)

    meta = _playlist_meta(playlist)
    history = list(meta.get("return_to_review_history") or [])
    history.append(
        {
            "track_id": track.id,
            "actor": actor,
            "returned_at": _utcnow().isoformat(),
        }
    )
    meta["return_to_review_history"] = history
    meta["publish_ready"] = False
    meta["publish_approved"] = False
    meta["workflow_state"] = "collecting"
    meta["note"] = f"Track `{track.title}` returned to awaiting approval."
    meta.pop("publish_approved_by", None)
    meta.pop("publish_ready_trigger", None)
    meta.pop("render_ready", None)
    meta.pop("render_error", None)
    meta.pop("cover_image_path", None)
    meta.pop("cover_approved", None)
    meta.pop("metadata_approved", None)
    meta.pop("youtube_title", None)
    meta.pop("youtube_description", None)
    meta.pop("youtube_tags", None)
    meta.pop("youtube_localizations", None)
    meta.pop("youtube_default_language", None)
    playlist.metadata_json = meta
    playlist.output_audio_path = None
    playlist.output_video_path = None
    playlist.youtube_video_id = None
    playlist.status = PlaylistStatus.draft
    db.commit()
    db.refresh(playlist)

    playlist = db.scalars(
        select(Playlist)
        .options(selectinload(Playlist.items).selectinload(PlaylistItem.track))
        .where(Playlist.id == playlist.id)
    ).first()
    await _update_publish_state(db, services, playlist, trigger=f"return-to-review:{track.id}")
    return playlist


def list_available_approved_tracks(
    db: Session,
    *,
    renderable_only: bool = False,
) -> list[Track]:
    consumed_track_ids = (
        select(PlaylistItem.track_id)
        .join(Playlist, Playlist.id == PlaylistItem.playlist_id)
        .where(Playlist.status != PlaylistStatus.failed)
    )
    tracks = db.scalars(
        select(Track)
        .where(
            Track.status == TrackStatus.approved,
            ~Track.id.in_(consumed_track_ids),
        )
        .order_by(Track.created_at.asc())
    ).all()
    if renderable_only:
        return [track for track in tracks if _has_local_audio(track)]
    return tracks


def build_playlist_from_tracks(
    db: Session,
    services: ServiceRegistry,
    tracks: list[Track],
    *,
    title: str,
    target_duration_seconds: int,
    execute_render: bool,
    source: str,
    metadata: dict | None = None,
) -> Playlist:
    candidate_tracks = tracks
    if execute_render:
        candidate_tracks = [track for track in tracks if _has_local_audio(track)]
    if not candidate_tracks:
        raise ValueError("No approved tracks are available for playlist building.")

    selected_tracks: list[Track] = []
    total = 0
    for track in candidate_tracks:
        if total >= target_duration_seconds:
            break
        selected_tracks.append(track)
        total += max(track.duration_seconds, 0)
    if not selected_tracks:
        raise ValueError("Playlist plan selected zero tracks.")

    playlist = Playlist(
        title=title,
        status=PlaylistStatus.building if execute_render else PlaylistStatus.draft,
        target_duration_seconds=target_duration_seconds,
        actual_duration_seconds=total,
        metadata_json={
            "selected_track_ids": [track.id for track in selected_tracks],
            "shortage_seconds": max(target_duration_seconds - total, 0),
            "workflow_state": "collecting" if total < target_duration_seconds else "pending_publish_approval",
            "publish_ready": total >= target_duration_seconds,
            "publish_approved": False,
            **(metadata or {}),
        },
    )
    db.add(playlist)
    db.flush()

    for index, track in enumerate(selected_tracks, start=1):
        db.add(
            PlaylistItem(
                playlist_id=playlist.id,
                track_id=track.id,
                order_index=index,
                included_duration_seconds=track.duration_seconds,
            )
        )

    now = _utcnow()
    job = Job(
        type=JobType.build_playlist,
        status=JobStatus.queued if execute_render else JobStatus.succeeded,
        source=source,
        payload_json={
            "title": title,
            "target_duration_seconds": target_duration_seconds,
            "execute_render": execute_render,
        },
        result_json={"selected_track_ids": [track.id for track in selected_tracks]},
        playlist=playlist,
        started_at=None if execute_render else now,
        finished_at=None if execute_render else now,
    )
    db.add(job)
    db.flush()

    if execute_render:
        playlist.metadata_json = {
            **playlist.metadata_json,
            "render_ready": False,
            "note": "Playlist audio render queued in background.",
        }

    db.commit()
    db.refresh(playlist)
    return playlist


async def maybe_build_auto_playlist(
    db: Session,
    services: ServiceRegistry,
    *,
    trigger: str,
) -> Playlist | None:
    if not services.settings.auto_build_playlists:
        return None

    target_duration_seconds = _default_target_duration_seconds(services)
    render_audio = services.settings.auto_build_render_audio
    available_tracks = list_available_approved_tracks(db, renderable_only=render_audio)
    total_duration = sum(max(track.duration_seconds, 0) for track in available_tracks)
    if total_duration < target_duration_seconds:
        return None

    playlist_count = db.scalar(select(func.count(Playlist.id))) or 0
    title = f"{services.settings.auto_build_title_prefix} {datetime.now().strftime('%Y-%m-%d')} #{playlist_count + 1}"
    playlist = build_playlist_from_tracks(
        db,
        services,
        available_tracks,
        title=title,
        target_duration_seconds=target_duration_seconds,
        execute_render=render_audio,
        source="system:auto-build",
        metadata={"trigger": trigger, "auto_built": True},
    )
    return playlist


def approve_playlist_publish(
    db: Session,
    services: ServiceRegistry,
    *,
    playlist: Playlist,
    actor: str,
    youtube_video_id: str | None = None,
    youtube_channel_id: str | None = None,
    note: str | None = None,
    force_under_target: bool = False,
) -> Playlist:
    playlist = db.scalars(
        select(Playlist)
        .options(selectinload(Playlist.items).selectinload(PlaylistItem.track))
        .where(Playlist.id == playlist.id)
    ).first()
    meta = _playlist_meta(playlist)
    if not playlist.items:
        raise ValueError("Playlist has no tracks to publish.")
    under_target = not _publish_is_ready(playlist)
    if not meta.get("publish_ready") and not (force_under_target and under_target):
        raise ValueError("Playlist has not reached its target duration yet.")
    if under_target and not force_under_target:
        raise ValueError("Playlist has not reached its target duration yet.")
    if force_under_target and under_target:
        meta["publish_ready"] = True
        meta["publish_under_target_confirmed"] = True
        meta["publish_under_target_confirmed_by"] = actor
        meta["publish_under_target_confirmed_at"] = _utcnow().isoformat()
    if youtube_video_id:
        playlist.youtube_video_id = youtube_video_id
        playlist.status = PlaylistStatus.uploaded
        meta["workflow_state"] = "uploaded"
        meta["publish_approved"] = True
        meta["publish_approved_by"] = actor
        meta["note"] = note
        _store_youtube_channel_metadata(meta, services, channel_id=youtube_channel_id)
        playlist.metadata_json = meta
        db.add(playlist)

        job = Job(
            type=JobType.upload_youtube,
            status=JobStatus.succeeded,
            source="web",
            payload_json={
                "playlist_id": playlist.id,
                "actor": actor,
                "note": note,
                "youtube_channel_id": youtube_channel_id,
            },
            result_json={
                "youtube_video_id": playlist.youtube_video_id,
                "output_video_path": playlist.output_video_path,
            },
            playlist=playlist,
            started_at=_utcnow(),
            finished_at=_utcnow(),
        )
        db.add(job)
        db.commit()
        db.refresh(playlist)
        return playlist

    if not playlist.output_audio_path:
        raise ValueError("Playlist audio has not been rendered yet.")
    audio_path = Path(playlist.output_audio_path)
    if not audio_path.exists():
        raise ValueError("Rendered playlist audio file is missing on disk.")
    if not playlist.output_video_path or not Path(playlist.output_video_path).exists():
        raise ValueError("Rendered video is required before final publish approval.")
    if not meta.get("cover_image_path") or not Path(meta["cover_image_path"]).exists():
        raise ValueError("Approved cover image is required before final publish approval.")
    if not meta.get("cover_approved"):
        raise ValueError("Cover image must be approved before final publish approval.")
    if not meta.get("metadata_approved"):
        raise ValueError("YouTube metadata must be approved before final publish approval.")
    if not meta.get("youtube_title") or not meta.get("youtube_description"):
        raise ValueError("YouTube metadata draft is missing before final publish approval.")

    is_playlist_release = _workspace_mode(playlist) != "single_track_video"
    default_language = normalize_youtube_language(meta.get("youtube_default_language"))
    meta["youtube_title"] = ensure_playlist_title_prefix(
        meta.get("youtube_title"),
        is_playlist=is_playlist_release,
    )
    meta["youtube_localizations"] = ensure_playlist_localization_title_prefix(
        normalize_youtube_localizations(
            meta.get("youtube_localizations"),
            default_title=meta.get("youtube_title"),
            default_description=meta.get("youtube_description"),
            default_language=default_language,
        ),
        is_playlist=is_playlist_release,
    )

    _store_youtube_channel_metadata(meta, services, channel_id=youtube_channel_id)
    playlist.metadata_json = meta

    _queue_publish_job(
        db,
        playlist,
        actor=actor,
        note=(f"{note} " if note else "") + "Background worker queued final YouTube upload.",
        source="web",
        force_under_target=force_under_target,
        youtube_channel_id=youtube_channel_id,
    )

    db.commit()
    db.refresh(playlist)
    return playlist
