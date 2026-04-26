from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.enums import JobStatus, JobType, PlaylistStatus, TrackStatus
from app.models.job import Job
from app.models.playlist import Playlist, PlaylistItem
from app.models.track import Track
from app.schemas.playlist import PlaylistJobRead, PlaylistTrackRead, PlaylistWorkspaceRead
from app.services.registry import ServiceRegistry


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _default_target_duration_seconds(services: ServiceRegistry) -> int:
    return services.settings.playlist_target_minutes * 60


def _playlist_meta(playlist: Playlist) -> dict:
    return dict(playlist.metadata_json or {})


def _workspace_mode(playlist: Playlist) -> str:
    return str(_playlist_meta(playlist).get("workspace_mode") or "playlist")


def _auto_publish_when_ready(playlist: Playlist) -> bool:
    return bool(_playlist_meta(playlist).get("auto_publish_when_ready"))


def _publish_is_ready(playlist: Playlist) -> bool:
    mode = _workspace_mode(playlist)
    if mode == "single_track_video":
        return bool(playlist.items)
    return playlist.actual_duration_seconds >= playlist.target_duration_seconds


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
        duration_seconds=track.duration_seconds,
        audio_path=track.audio_path,
        preview_url=track.preview_url,
        image_url=metadata.get("image_url"),
        tags=metadata.get("tags"),
    )


def _latest_render_job(playlist: Playlist) -> PlaylistJobRead | None:
    jobs = [
        job
        for job in playlist.jobs
        if job.type == JobType.build_playlist
    ]
    if not jobs:
        return None

    job = max(jobs, key=lambda candidate: candidate.created_at)
    result = job.result_json or {}
    return PlaylistJobRead(
        id=job.id,
        status=job.status.value,
        source=job.source,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        error_text=job.error_text,
        output_audio_path=result.get("output_audio_path"),
    )


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
        output_audio_path=playlist.output_audio_path,
        output_video_path=playlist.output_video_path,
        cover_image_path=meta.get("cover_image_path"),
        youtube_video_id=playlist.youtube_video_id,
        note=meta.get("note"),
        render_job=_latest_render_job(playlist),
        created_at=playlist.created_at,
        updated_at=playlist.updated_at,
        tracks=tracks,
    )


def list_playlist_workspaces(db: Session) -> list[Playlist]:
    return db.scalars(
        select(Playlist)
        .options(
            selectinload(Playlist.items).selectinload(PlaylistItem.track),
            selectinload(Playlist.jobs),
        )
        .order_by(Playlist.updated_at.desc())
    ).all()


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
        auto_publish = normalized_mode == "single_track_video"

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
        },
    )
    db.add(playlist)
    db.commit()
    db.refresh(playlist)
    return playlist


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


def _all_tracks_renderable(playlist: Playlist) -> bool:
    tracks = _playlist_tracks(playlist)
    return bool(tracks) and all(_has_local_audio(track) for track in tracks)


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


def _queue_publish_job(
    db: Session,
    playlist: Playlist,
    *,
    actor: str,
    note: str | None,
    source: str,
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
    if not playlist.output_audio_path or not Path(playlist.output_audio_path).exists():
        return None
    return _queue_publish_job(db, playlist, actor=actor, note=note, source=source)


async def _update_publish_state(
    db: Session,
    services: ServiceRegistry,
    playlist: Playlist,
    *,
    trigger: str,
) -> None:
    meta = _playlist_meta(playlist)
    _refresh_playlist_duration(playlist)

    if _publish_is_ready(playlist):
        meta["workflow_state"] = "pending_publish_approval"
        meta["publish_ready"] = True
        meta["publish_ready_trigger"] = trigger
        if _all_tracks_renderable(playlist):
            if playlist.output_audio_path and Path(playlist.output_audio_path).exists():
                playlist.status = PlaylistStatus.ready
                meta["render_ready"] = True
                meta.pop("render_error", None)
                meta["note"] = meta.get("note") or "Playlist audio render is complete."
                if _auto_publish_when_ready(playlist):
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
                _queue_playlist_render_job(
                    db,
                    playlist,
                    source="system:workspace-queue",
                    trigger=trigger,
                )
                playlist.status = PlaylistStatus.building
                meta["render_ready"] = False
                meta.pop("render_error", None)
                meta["note"] = "Playlist audio render queued in background."
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
    meta["render_ready"] = False
    meta["publish_approved"] = False
    meta["note"] = "Track order changed. Re-render audio to update the playlist file."
    meta["workflow_state"] = "render_required" if playlist.items else "collecting"
    meta.pop("render_error", None)
    meta.pop("cover_image_path", None)
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
    active_job = _find_active_playlist_job(db, playlist)
    meta = _playlist_meta(playlist)
    meta["render_ready"] = False
    meta["publish_approved"] = False
    meta["workflow_state"] = "render_queued"
    meta["note"] = "Playlist audio render queued from the web dashboard."
    meta.pop("render_error", None)
    meta.pop("cover_image_path", None)
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
    note: str | None = None,
) -> Playlist:
    playlist = db.scalars(
        select(Playlist)
        .options(selectinload(Playlist.items).selectinload(PlaylistItem.track))
        .where(Playlist.id == playlist.id)
    ).first()
    meta = _playlist_meta(playlist)
    if not playlist.items:
        raise ValueError("Playlist has no tracks to publish.")
    if not meta.get("publish_ready") or not _publish_is_ready(playlist):
        raise ValueError("Playlist has not reached its target duration yet.")
    if youtube_video_id:
        playlist.youtube_video_id = youtube_video_id
        playlist.status = PlaylistStatus.uploaded
        meta["workflow_state"] = "uploaded"
        meta["publish_approved"] = True
        meta["publish_approved_by"] = actor
        meta["note"] = note
        db.add(playlist)

        job = Job(
            type=JobType.upload_youtube,
            status=JobStatus.succeeded,
            source="web",
            payload_json={
                "playlist_id": playlist.id,
                "actor": actor,
                "note": note,
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

    _queue_publish_job(
        db,
        playlist,
        actor=actor,
        note=(
        f"{note} " if note else ""
        ) + "Background worker queued cover, video render, and YouTube upload.",
        source="web",
    )

    db.commit()
    db.refresh(playlist)
    return playlist
