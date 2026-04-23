from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.enums import JobStatus, JobType, PlaylistStatus, TrackStatus
from app.models.job import Job
from app.models.playlist import Playlist, PlaylistItem
from app.models.track import Track
from app.schemas.playlist import PlaylistTrackRead, PlaylistWorkspaceRead
from app.services.registry import ServiceRegistry


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _default_target_duration_seconds(services: ServiceRegistry) -> int:
    return services.settings.playlist_target_minutes * 60


def _playlist_meta(playlist: Playlist) -> dict:
    return dict(playlist.metadata_json or {})


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


def serialize_playlist_workspace(playlist: Playlist) -> PlaylistWorkspaceRead:
    meta = _playlist_meta(playlist)
    tracks = [
        _track_payload(item.track)
        for item in sorted(playlist.items, key=lambda item: item.order_index)
        if item.track is not None
    ]
    progress_ratio = 0.0
    if playlist.target_duration_seconds > 0:
        progress_ratio = min(playlist.actual_duration_seconds / playlist.target_duration_seconds, 1.0)
    return PlaylistWorkspaceRead(
        id=playlist.id,
        title=playlist.title,
        status=playlist.status,
        target_duration_seconds=playlist.target_duration_seconds,
        actual_duration_seconds=playlist.actual_duration_seconds,
        progress_ratio=progress_ratio,
        description=meta.get("description"),
        cover_prompt=meta.get("cover_prompt"),
        workflow_state=meta.get("workflow_state", "collecting"),
        publish_ready=bool(meta.get("publish_ready")),
        publish_approved=bool(meta.get("publish_approved")),
        output_audio_path=playlist.output_audio_path,
        output_video_path=playlist.output_video_path,
        cover_image_path=meta.get("cover_image_path"),
        youtube_video_id=playlist.youtube_video_id,
        note=meta.get("note"),
        created_at=playlist.created_at,
        updated_at=playlist.updated_at,
        tracks=tracks,
    )


def list_playlist_workspaces(db: Session) -> list[Playlist]:
    return db.scalars(
        select(Playlist)
        .options(selectinload(Playlist.items).selectinload(PlaylistItem.track))
        .order_by(Playlist.updated_at.desc())
    ).all()


def create_playlist_workspace(
    db: Session,
    *,
    title: str,
    target_duration_seconds: int,
    description: str | None = None,
    cover_prompt: str | None = None,
) -> Playlist:
    playlist = Playlist(
        title=title,
        status=PlaylistStatus.draft,
        target_duration_seconds=target_duration_seconds,
        actual_duration_seconds=0,
        metadata_json={
            "description": description,
            "cover_prompt": cover_prompt,
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


def _render_playlist_audio_if_possible(
    db: Session,
    services: ServiceRegistry,
    playlist: Playlist,
) -> None:
    tracks = _playlist_tracks(playlist)
    if not tracks or not _all_tracks_renderable(playlist):
        return
    if playlist.output_audio_path and Path(playlist.output_audio_path).exists():
        return

    output_path = Path(services.settings.playlists_dir) / f"{playlist.id}.mp3"
    rendered_path = services.playlist_builder.build_audio(tracks, output_path)
    playlist.output_audio_path = str(rendered_path)
    db.add(playlist)


async def _update_publish_state(
    db: Session,
    services: ServiceRegistry,
    playlist: Playlist,
    *,
    trigger: str,
) -> None:
    meta = _playlist_meta(playlist)
    _refresh_playlist_duration(playlist)

    if playlist.actual_duration_seconds >= playlist.target_duration_seconds:
        meta["workflow_state"] = "pending_publish_approval"
        meta["publish_ready"] = True
        meta["publish_ready_trigger"] = trigger
        if _all_tracks_renderable(playlist):
            try:
                _render_playlist_audio_if_possible(db, services, playlist)
                playlist.status = PlaylistStatus.ready
                meta["render_ready"] = True
            except Exception as exc:  # noqa: BLE001
                meta["render_ready"] = False
                meta["render_error"] = str(exc)
                playlist.status = PlaylistStatus.draft
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
        status=JobStatus.running if execute_render else JobStatus.succeeded,
        source=source,
        payload_json={
            "title": title,
            "target_duration_seconds": target_duration_seconds,
            "execute_render": execute_render,
        },
        result_json={"selected_track_ids": [track.id for track in selected_tracks]},
        playlist=playlist,
        started_at=now,
        finished_at=None if execute_render else now,
    )
    db.add(job)
    db.flush()

    if execute_render:
        output_path = Path(services.settings.playlists_dir) / f"{playlist.id}.mp3"
        try:
            rendered_path = services.playlist_builder.build_audio(selected_tracks, output_path)
            playlist.output_audio_path = str(rendered_path)
            playlist.status = PlaylistStatus.ready
            job.status = JobStatus.succeeded
            job.result_json = {
                "selected_track_ids": [track.id for track in selected_tracks],
                "output_audio_path": str(rendered_path),
            }
            job.finished_at = _utcnow()
        except Exception as exc:  # noqa: BLE001
            playlist.status = PlaylistStatus.failed
            job.status = JobStatus.failed
            job.error_text = str(exc)
            job.finished_at = _utcnow()

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
    if not meta.get("publish_ready") or playlist.actual_duration_seconds < playlist.target_duration_seconds:
        raise ValueError("Playlist has not reached its target duration yet.")
    if not youtube_video_id:
        if not playlist.output_audio_path:
            raise ValueError("Playlist audio has not been rendered yet.")
        audio_path = Path(playlist.output_audio_path)
        if not audio_path.exists():
            raise ValueError("Rendered playlist audio file is missing on disk.")

    cover_image_path = services.cover_art.generate_cover(playlist)
    meta["cover_image_path"] = cover_image_path
    meta["publish_approved"] = True
    meta["workflow_state"] = "ready_for_youtube"
    meta["publish_approved_by"] = actor
    meta["note"] = note
    playlist.metadata_json = meta

    if (
        playlist.output_audio_path
        and (
            not playlist.output_video_path
            or not Path(playlist.output_video_path).exists()
        )
    ):
        audio_path = Path(playlist.output_audio_path)
        video_path = Path(services.settings.playlists_dir) / f"{playlist.id}.mp4"
        try:
            playlist.output_video_path = str(
                services.playlist_builder.build_video(audio_path, Path(cover_image_path), video_path)
            )
        except Exception as exc:  # noqa: BLE001
            playlist.status = PlaylistStatus.ready
            meta["workflow_state"] = "video_build_failed"
            meta["note"] = f"Automatic video build failed: {exc}"
            meta["video_build_error"] = str(exc)
            playlist.metadata_json = meta
            db.add(playlist)

            job = Job(
                type=JobType.upload_youtube,
                status=JobStatus.failed,
                source="web",
                payload_json={
                    "playlist_id": playlist.id,
                    "actor": actor,
                    "note": note,
                },
                result_json={
                    "cover_image_path": cover_image_path,
                    "output_video_path": playlist.output_video_path,
                },
                error_text=str(exc),
                playlist=playlist,
                started_at=_utcnow(),
                finished_at=_utcnow(),
            )
            db.add(job)
            db.commit()
            db.refresh(playlist)
            return playlist

    upload_status = JobStatus.queued
    if playlist.output_video_path and services.settings.youtube_auto_upload_on_publish:
        youtube_status = services.youtube.get_status()
        if youtube_status["ready"]:
            description = meta.get("description") or f"{playlist.title}\n\nGenerated by AI music workspace."
            tags = sorted(
                {
                    tag.strip()
                    for item in playlist.items
                    for tag in str((item.track.metadata_json or {}).get("tags") or "").split(",")
                    if tag.strip()
                }
            )
            try:
                result = services.youtube.upload_playlist_video(
                    playlist,
                    title=playlist.title,
                    description=description,
                    tags=tags,
                    thumbnail_path=cover_image_path,
                )
                playlist.youtube_video_id = result.video_id
                playlist.status = PlaylistStatus.uploaded
                meta["workflow_state"] = "uploaded"
                meta["youtube_response"] = result.response
                upload_status = JobStatus.succeeded
                for item in playlist.items:
                    item.track.status = TrackStatus.uploaded
                    db.add(item.track)
            except Exception as exc:  # noqa: BLE001
                playlist.status = PlaylistStatus.ready
                meta["workflow_state"] = "youtube_upload_failed"
                meta["note"] = f"Automatic YouTube upload failed: {exc}"
                meta["youtube_upload_error"] = str(exc)
                upload_status = JobStatus.failed
        else:
            meta["workflow_state"] = "ready_for_youtube_auth"
            meta["note"] = (
                f"{note} "
                if note
                else ""
            ) + "Connect YouTube in the web app to enable automatic upload."

    if youtube_video_id:
        playlist.youtube_video_id = youtube_video_id
        playlist.status = PlaylistStatus.uploaded
        meta["workflow_state"] = "uploaded"
        upload_status = JobStatus.succeeded
    db.add(playlist)

    job = Job(
        type=JobType.upload_youtube,
        status=upload_status,
        source="web",
        payload_json={
            "playlist_id": playlist.id,
            "actor": actor,
            "note": note,
        },
        result_json={
            "cover_image_path": cover_image_path,
            "youtube_video_id": playlist.youtube_video_id,
            "output_video_path": playlist.output_video_path,
        },
        playlist=playlist,
        started_at=_utcnow(),
        finished_at=_utcnow() if upload_status in {JobStatus.succeeded, JobStatus.failed} else None,
    )
    db.add(job)
    db.commit()
    db.refresh(playlist)
    return playlist
