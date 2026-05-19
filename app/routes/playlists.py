import json
import shutil
import subprocess
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.models.enums import JobStatus, JobType, PlaylistStatus, TrackStatus
from app.models.job import Job
from app.models.playlist import Playlist, PlaylistItem
from app.models.track import Track
from app.schemas.playlist import (
    PlaylistBuildRequest,
    PlaylistArchiveRequest,
    PlaylistCoverApproveRequest,
    PlaylistCoverGenerateRequest,
    PlaylistMetadataApproveRequest,
    PlaylistMetadataGenerateRequest,
    PlaylistOpenClawNextRequest,
    PlaylistPublishApproveRequest,
    PlaylistRead,
    PlaylistRenderRequest,
    PlaylistTrackReorderRequest,
    PlaylistUploadMarkRequest,
    PlaylistVideoRenderRequest,
    PlaylistWorkspaceCreateRequest,
    PlaylistWorkspaceRead,
)
from app.services.registry import ServiceRegistry
from app.workflows.playlist_automation import (
    _ensure_description_hashtags,
    _normalize_youtube_tags,
    _store_youtube_channel_metadata,
    _utcnow,
    approve_playlist_cover,
    approve_playlist_metadata,
    approve_playlist_publish,
    attach_uploaded_playlist_cover,
    attach_uploaded_loop_video,
    attach_uploaded_playlist_thumbnail,
    build_playlist_from_tracks,
    clear_uploaded_loop_video,
    create_playlist_workspace,
    generate_playlist_cover,
    generate_playlist_metadata,
    list_compact_playlist_workspaces,
    list_workspace_channel_summaries,
    list_available_approved_tracks,
    list_playlist_workspaces,
    queue_workspace_video_render,
    queue_workspace_audio_render,
    reorder_workspace_tracks,
    serialize_playlist_workspace,
    set_playlist_workspace_archive_state,
)
from app.utils.openclaw_slack_loop import post_next_playlist_request
from app.utils.ops_notifications import notify_video_render_queued
from app.utils.local_video_cleanup import cleanup_public_uploaded_local_videos
from app.utils.render_worker_registry import set_render_worker_nickname
from app.utils.youtube_localizations import (
    normalize_youtube_language,
    normalize_youtube_localizations,
    sanitize_youtube_copy,
)

router = APIRouter(prefix="/playlists", tags=["playlists"])

ALLOWED_COVER_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_LOOP_VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm"}


class RenderWorkerNicknameRequest(BaseModel):
    nickname: str = Field(default="", max_length=128)
    actor: str = Field(default="web-ui", max_length=128)


def get_services(request: Request) -> ServiceRegistry:
    return request.app.state.services


def _run_public_video_cleanup(db: Session, services: ServiceRegistry) -> None:
    cleanup_public_uploaded_local_videos(db, services.settings)


def _store_image_upload(upload: UploadFile, destination_dir: Path, playlist_id: str, *, asset_name: str) -> str:
    if not upload.filename:
        raise HTTPException(status_code=400, detail=f"{asset_name.title()} image filename is required.")

    suffix = Path(upload.filename).suffix.lower()
    if suffix not in ALLOWED_COVER_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"{asset_name.title()} image must be jpg, png, or webp.")
    if upload.content_type and not upload.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail=f"{asset_name.title()} upload must be an image file.")

    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / f"{playlist_id}-{asset_name}-upload-{uuid4().hex}{suffix}"
    with destination.open("wb") as handle:
        shutil.copyfileobj(upload.file, handle)

    if not destination.exists() or destination.stat().st_size == 0:
        raise HTTPException(status_code=400, detail=f"Uploaded {asset_name} image is empty.")
    return str(destination)


def _store_cover_upload(upload: UploadFile, destination_dir: Path, playlist_id: str) -> str:
    return _store_image_upload(upload, destination_dir, playlist_id, asset_name="cover")


def _store_thumbnail_upload(upload: UploadFile, destination_dir: Path, playlist_id: str) -> str:
    return _store_image_upload(upload, destination_dir, playlist_id, asset_name="thumbnail")


def _store_loop_video_upload(upload: UploadFile, destination_dir: Path, playlist_id: str) -> str:
    if not upload.filename:
        raise HTTPException(status_code=400, detail="Loop video filename is required.")

    suffix = Path(upload.filename).suffix.lower()
    if suffix not in ALLOWED_LOOP_VIDEO_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Loop video must be mp4, mov, m4v, or webm.")
    if upload.content_type and not (
        upload.content_type.startswith("video/") or upload.content_type == "application/octet-stream"
    ):
        raise HTTPException(status_code=400, detail="Loop video upload must be a video file.")

    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / f"{playlist_id}-loop-video-upload-{uuid4().hex}{suffix}"
    with destination.open("wb") as handle:
        shutil.copyfileobj(upload.file, handle)

    if not destination.exists() or destination.stat().st_size == 0:
        raise HTTPException(status_code=400, detail="Uploaded loop video is empty.")
    return str(destination)


def _ffprobe_binary(ffmpeg_binary: str) -> str:
    candidate = Path(ffmpeg_binary).with_name("ffprobe")
    return str(candidate) if candidate.exists() else "ffprobe"


def _validate_loop_video_file(video_path: str, *, ffmpeg_binary: str) -> None:
    path = Path(video_path)
    try:
        probe = subprocess.run(
            [
                _ffprobe_binary(ffmpeg_binary),
                "-v",
                "error",
                "-show_entries",
                "format=duration:stream=index,codec_type,codec_name,width,height",
                "-of",
                "json",
                str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(probe.stdout or "{}")
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Uploaded loop video is not a readable video file.") from exc

    streams = payload.get("streams") or []
    if not any(stream.get("codec_type") == "video" for stream in streams):
        raise HTTPException(status_code=400, detail="Uploaded loop video must contain a video stream.")

def _delete_uploaded_video_file(video_path: str | None) -> dict:
    if not video_path:
        return {"deleted": False, "path": None}
    path = Path(video_path)
    if not path.exists():
        return {"deleted": False, "path": str(path)}
    try:
        path.unlink()
    except OSError as exc:
        return {"deleted": False, "path": str(path), "error": str(exc)}
    return {"deleted": True, "path": str(path)}


@router.post("/build", response_model=PlaylistRead, status_code=status.HTTP_201_CREATED)
def build_playlist(
    payload: PlaylistBuildRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> PlaylistRead:
    services = get_services(request)
    approved_tracks = list_available_approved_tracks(
        db,
        renderable_only=payload.execute_render,
    )
    if not approved_tracks:
        raise HTTPException(status_code=400, detail="No approved tracks are available.")

    try:
        playlist = build_playlist_from_tracks(
            db,
            services,
            approved_tracks,
            title=payload.title,
            target_duration_seconds=payload.target_duration_seconds,
            execute_render=payload.execute_render,
            source="api",
            metadata={"manual_build": True},
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PlaylistRead.model_validate(playlist)


@router.get("", response_model=list[PlaylistRead])
def list_playlists(db: Session = Depends(get_db)) -> list[PlaylistRead]:
    playlists = db.scalars(select(Playlist).order_by(Playlist.created_at.desc())).all()
    return [PlaylistRead.model_validate(playlist) for playlist in playlists]


@router.get("/workspaces", response_model=list[PlaylistWorkspaceRead])
def list_workspace_playlists(
    compact: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> list[PlaylistWorkspaceRead]:
    if compact:
        return list_compact_playlist_workspaces(db)
    return [
        serialize_playlist_workspace(playlist, compact=compact)
        for playlist in list_playlist_workspaces(db, compact=compact)
    ]


@router.get("/workspaces/summary")
def list_workspace_summary(db: Session = Depends(get_db)) -> dict:
    return {"channels": list_workspace_channel_summaries(db)}


@router.post("/render-workers/{worker_id}/nickname")
def set_render_worker_nickname_endpoint(
    worker_id: str,
    payload: RenderWorkerNicknameRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    services = get_services(request)
    nickname = payload.nickname.strip()
    entry = set_render_worker_nickname(
        services.settings.storage_root,
        worker_id=worker_id,
        nickname=nickname,
        actor=payload.actor or "web-ui",
    )

    updated_jobs = 0
    jobs = db.scalars(select(Job).where(Job.type == JobType.build_video)).all()
    for job in jobs:
        result = dict(job.result_json or {})
        worker = result.get("external_render_worker")
        if not isinstance(worker, dict) or worker.get("worker_id") != worker_id:
            continue
        worker = dict(worker)
        if nickname:
            worker["nickname"] = nickname
        else:
            worker.pop("nickname", None)
        worker["nickname_updated_by"] = payload.actor or "web-ui"
        worker["nickname_updated_at"] = _utcnow().isoformat()
        result["external_render_worker"] = worker
        job.result_json = result
        db.add(job)
        updated_jobs += 1
    if updated_jobs:
        db.commit()

    return {"ok": True, "worker": entry, "updated_jobs": updated_jobs}


@router.get("/workspaces/{playlist_id}", response_model=PlaylistWorkspaceRead)
def get_workspace_playlist(
    playlist_id: str,
    db: Session = Depends(get_db),
) -> PlaylistWorkspaceRead:
    playlist = db.scalars(
        select(Playlist)
        .where(Playlist.id == playlist_id)
        .options(
            selectinload(Playlist.items).selectinload(PlaylistItem.track),
            selectinload(Playlist.jobs),
        )
    ).first()
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    return serialize_playlist_workspace(playlist)


@router.post("/workspaces", response_model=PlaylistWorkspaceRead, status_code=status.HTTP_201_CREATED)
def create_workspace_playlist(
    payload: PlaylistWorkspaceCreateRequest,
    db: Session = Depends(get_db),
) -> PlaylistWorkspaceRead:
    playlist = create_playlist_workspace(
        db,
        title=payload.title,
        target_duration_seconds=payload.target_duration_seconds,
        workspace_mode=payload.workspace_mode,
        auto_publish_when_ready=payload.auto_publish_when_ready,
        description=payload.description,
        cover_prompt=payload.cover_prompt,
        dreamina_prompt=payload.dreamina_prompt,
        target_youtube_channel_title=payload.target_youtube_channel_title,
    )
    return serialize_playlist_workspace(playlist)


@router.post("/{playlist_id}/tracks/reorder", response_model=PlaylistWorkspaceRead)
def reorder_workspace_playlist_tracks(
    playlist_id: str,
    payload: PlaylistTrackReorderRequest,
    db: Session = Depends(get_db),
) -> PlaylistWorkspaceRead:
    try:
        playlist = reorder_workspace_tracks(
            db,
            playlist_id=playlist_id,
            track_ids=payload.track_ids,
            actor=payload.actor,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return serialize_playlist_workspace(playlist)


@router.post("/{playlist_id}/archive", response_model=PlaylistWorkspaceRead)
def archive_workspace_playlist(
    playlist_id: str,
    payload: PlaylistArchiveRequest,
    db: Session = Depends(get_db),
) -> PlaylistWorkspaceRead:
    try:
        playlist = set_playlist_workspace_archive_state(
            db,
            playlist_id=playlist_id,
            actor=payload.actor,
            archived=payload.archived,
            revive_rejected=payload.revive_rejected,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return serialize_playlist_workspace(playlist)


@router.post("/{playlist_id}/render-audio", response_model=PlaylistWorkspaceRead)
def render_workspace_playlist_audio(
    playlist_id: str,
    payload: PlaylistRenderRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> PlaylistWorkspaceRead:
    services = get_services(request)
    try:
        playlist = queue_workspace_audio_render(
            db,
            services,
            playlist_id=playlist_id,
            actor=payload.actor,
            randomize_order=payload.effective_randomize_order(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return serialize_playlist_workspace(playlist)


@router.post("/{playlist_id}/cover/generate", response_model=PlaylistWorkspaceRead)
def generate_workspace_cover(
    playlist_id: str,
    payload: PlaylistCoverGenerateRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> PlaylistWorkspaceRead:
    services = get_services(request)
    try:
        playlist = generate_playlist_cover(
            db,
            services,
            playlist_id=playlist_id,
            actor=payload.actor,
            regenerate=payload.regenerate,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return serialize_playlist_workspace(playlist)


@router.post("/{playlist_id}/cover/upload", response_model=PlaylistWorkspaceRead)
def upload_workspace_cover(
    playlist_id: str,
    request: Request,
    actor: str = Form("web-ui"),
    cover_file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> PlaylistWorkspaceRead:
    services = get_services(request)
    playlist = db.get(Playlist, playlist_id)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    cover_image_path = _store_cover_upload(cover_file, services.settings.playlists_dir, playlist_id)
    try:
        playlist = attach_uploaded_playlist_cover(
            db,
            playlist_id=playlist_id,
            actor=actor,
            cover_image_path=cover_image_path,
        )
    except ValueError as exc:
        Path(cover_image_path).unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return serialize_playlist_workspace(playlist)


@router.post("/{playlist_id}/thumbnail/upload", response_model=PlaylistWorkspaceRead)
def upload_workspace_thumbnail(
    playlist_id: str,
    request: Request,
    actor: str = Form("web-ui"),
    thumbnail_file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> PlaylistWorkspaceRead:
    services = get_services(request)
    playlist = db.get(Playlist, playlist_id)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    thumbnail_path = _store_thumbnail_upload(thumbnail_file, services.settings.playlists_dir, playlist_id)
    try:
        playlist = attach_uploaded_playlist_thumbnail(
            db,
            playlist_id=playlist_id,
            actor=actor,
            thumbnail_path=thumbnail_path,
        )
    except ValueError as exc:
        Path(thumbnail_path).unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return serialize_playlist_workspace(playlist)


@router.post("/{playlist_id}/loop-video/upload", response_model=PlaylistWorkspaceRead)
def upload_workspace_loop_video(
    playlist_id: str,
    request: Request,
    actor: str = Form("web-ui"),
    smooth_loop: bool = Form(True),
    loop_video_provider: str = Form(""),
    loop_video_file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> PlaylistWorkspaceRead:
    services = get_services(request)
    playlist = db.get(Playlist, playlist_id)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    loop_video_path = _store_loop_video_upload(loop_video_file, services.settings.playlists_dir, playlist_id)
    try:
        _validate_loop_video_file(loop_video_path, ffmpeg_binary=services.settings.ffmpeg_binary)
        playlist = attach_uploaded_loop_video(
            db,
            playlist_id=playlist_id,
            actor=actor,
            loop_video_path=loop_video_path,
            smooth_loop=smooth_loop,
            provider=loop_video_provider,
        )
        _run_public_video_cleanup(db, services)
    except HTTPException:
        Path(loop_video_path).unlink(missing_ok=True)
        raise
    except ValueError as exc:
        Path(loop_video_path).unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return serialize_playlist_workspace(playlist)


@router.delete("/{playlist_id}/loop-video", response_model=PlaylistWorkspaceRead)
def delete_workspace_loop_video(
    playlist_id: str,
    actor: str = Query("web-ui"),
    db: Session = Depends(get_db),
) -> PlaylistWorkspaceRead:
    try:
        playlist = clear_uploaded_loop_video(
            db,
            playlist_id=playlist_id,
            actor=actor,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return serialize_playlist_workspace(playlist)


@router.post("/{playlist_id}/cover/approve", response_model=PlaylistWorkspaceRead)
def approve_workspace_cover(
    playlist_id: str,
    payload: PlaylistCoverApproveRequest,
    db: Session = Depends(get_db),
) -> PlaylistWorkspaceRead:
    try:
        playlist = approve_playlist_cover(
            db,
            playlist_id=playlist_id,
            actor=payload.actor,
            approved=payload.approved,
            note=payload.note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return serialize_playlist_workspace(playlist)


@router.post("/{playlist_id}/video/render", response_model=PlaylistWorkspaceRead)
def render_workspace_video(
    playlist_id: str,
    payload: PlaylistVideoRenderRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> PlaylistWorkspaceRead:
    services = get_services(request)
    try:
        playlist = queue_workspace_video_render(
            db,
            playlist_id=playlist_id,
            actor=payload.actor,
            allow_still_image_fallback=payload.allow_still_image_fallback,
            video_spectrum_overlay_style=payload.video_spectrum_overlay_style,
            video_render_resolution=payload.video_render_resolution,
            video_render_source_mode=payload.video_render_source_mode,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    job = db.scalars(
        select(Job)
        .where(
            Job.playlist_id == playlist.id,
            Job.type == JobType.build_video,
            Job.status == JobStatus.queued,
        )
        .order_by(Job.created_at.desc())
    ).first()
    notify_video_render_queued(db, services, playlist=playlist, job=job)
    return serialize_playlist_workspace(playlist)


@router.post("/{playlist_id}/metadata/generate", response_model=PlaylistWorkspaceRead)
def generate_workspace_metadata(
    playlist_id: str,
    payload: PlaylistMetadataGenerateRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> PlaylistWorkspaceRead:
    services = get_services(request)
    try:
        playlist = generate_playlist_metadata(
            db,
            services,
            playlist_id=playlist_id,
            actor=payload.actor,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return serialize_playlist_workspace(playlist)


@router.post("/{playlist_id}/metadata/approve", response_model=PlaylistWorkspaceRead)
def approve_workspace_metadata(
    playlist_id: str,
    payload: PlaylistMetadataApproveRequest,
    db: Session = Depends(get_db),
) -> PlaylistWorkspaceRead:
    try:
        playlist = approve_playlist_metadata(
            db,
            playlist_id=playlist_id,
            actor=payload.actor,
            title=payload.title,
            description=payload.description,
            tags=payload.tags,
            localizations=payload.localizations,
            default_language=payload.default_language,
            note=payload.note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return serialize_playlist_workspace(playlist)


@router.post("/{playlist_id}/youtube/metadata", response_model=PlaylistWorkspaceRead)
def update_uploaded_youtube_metadata(
    playlist_id: str,
    payload: PlaylistMetadataApproveRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> PlaylistWorkspaceRead:
    services = get_services(request)
    playlist = db.scalars(
        select(Playlist)
        .where(Playlist.id == playlist_id)
        .options(
            selectinload(Playlist.items).selectinload(PlaylistItem.track),
            selectinload(Playlist.jobs),
        )
    ).first()
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    if not playlist.youtube_video_id:
        raise HTTPException(status_code=400, detail="YouTube video id is required before updating YouTube metadata.")

    meta = dict(playlist.metadata_json or {})
    title = sanitize_youtube_copy(payload.title if payload.title is not None else meta.get("youtube_title")).strip()
    description = sanitize_youtube_copy(
        payload.description if payload.description is not None else meta.get("youtube_description")
    ).strip()
    tags = _normalize_youtube_tags(payload.tags if payload.tags is not None else meta.get("youtube_tags") or [])
    default_language = normalize_youtube_language(payload.default_language or meta.get("youtube_default_language"))
    localizations = normalize_youtube_localizations(
        payload.localizations if payload.localizations is not None else meta.get("youtube_localizations"),
        default_title=title,
        default_description=description,
        default_language=default_language,
    )
    default_copy = localizations.get(default_language)
    if default_copy:
        title = default_copy["title"]
        description = default_copy["description"]
    if not title or not description:
        raise HTTPException(status_code=400, detail="YouTube title and description are required.")

    description = _ensure_description_hashtags(description, tags)
    for localized_copy in localizations.values():
        localized_copy["description"] = _ensure_description_hashtags(localized_copy.get("description") or "", tags)
    default_copy = localizations.get(default_language)
    if default_copy:
        title = default_copy["title"]
        description = default_copy["description"]

    try:
        result = services.youtube.update_video_metadata(
            video_id=playlist.youtube_video_id,
            title=title,
            description=description,
            tags=tags,
            youtube_channel_id=meta.get("youtube_channel_id"),
            localizations=localizations,
            default_language=default_language,
        )
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    updated_at = _utcnow().isoformat()
    history = list(meta.get("youtube_metadata_update_history") or [])
    history.append(
        {
            "actor": payload.actor,
            "note": payload.note,
            "updated_at": updated_at,
            "youtube_video_id": playlist.youtube_video_id,
        }
    )
    meta.update(
        {
            "youtube_title": title,
            "youtube_description": description,
            "youtube_tags": tags,
            "youtube_default_language": default_language,
            "youtube_localizations": result.get("localizations") or localizations,
            "metadata_approved": True,
            "publish_ready": True,
            "publish_approved": True,
            "workflow_state": "uploaded",
            "youtube_metadata_updated_at": updated_at,
            "youtube_metadata_update_history": history,
            "note": payload.note or "YouTube metadata updated from web UI.",
        }
    )
    playlist.title = title[:255]
    playlist.status = PlaylistStatus.uploaded
    playlist.metadata_json = meta
    db.add(playlist)
    db.commit()
    db.refresh(playlist)
    return serialize_playlist_workspace(playlist)


@router.post("/{playlist_id}/approve-publish", response_model=PlaylistWorkspaceRead)
def approve_publish(
    playlist_id: str,
    payload: PlaylistPublishApproveRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> PlaylistWorkspaceRead:
    services = get_services(request)
    playlist = db.get(Playlist, playlist_id)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    try:
        playlist = approve_playlist_publish(
            db,
            services,
            playlist=playlist,
            actor=payload.actor,
            youtube_video_id=payload.youtube_video_id,
            youtube_channel_id=payload.youtube_channel_id,
            note=payload.note,
            force_under_target=payload.force_under_target,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return serialize_playlist_workspace(playlist)


@router.post("/{playlist_id}/mark-uploaded", response_model=PlaylistRead)
def mark_playlist_uploaded(
    playlist_id: str,
    payload: PlaylistUploadMarkRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> PlaylistRead:
    services = get_services(request)
    playlist = db.get(Playlist, playlist_id)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    playlist.status = PlaylistStatus.uploaded
    if payload.youtube_video_id:
        playlist.youtube_video_id = payload.youtube_video_id
    if payload.output_video_path:
        playlist.output_video_path = payload.output_video_path
    published_at = _utcnow().isoformat()
    meta = {
        **(playlist.metadata_json or {}),
        "uploaded_by": payload.actor,
        "upload_note": payload.note,
        "workflow_state": "uploaded",
        "publish_ready": True,
        "publish_approved": True,
        "youtube_published_at": published_at,
    }
    _store_youtube_channel_metadata(
        meta,
        services,
        channel_id=payload.youtube_channel_id or meta.get("youtube_channel_id"),
    )
    cleanup = _delete_uploaded_video_file(playlist.output_video_path if playlist.youtube_video_id else None)
    if cleanup["deleted"]:
        playlist.output_video_path = None
        meta["local_video_deleted_after_youtube_upload"] = cleanup["path"]
        meta["local_video_deleted_at"] = _utcnow().isoformat()
        meta.pop("local_video_cleanup_error", None)
    elif cleanup.get("error"):
        meta["local_video_cleanup_error"] = cleanup["error"]
    playlist.metadata_json = meta
    db.add(playlist)

    for item in playlist.items:
        item.track.status = TrackStatus.uploaded
        db.add(item.track)

    job = Job(
        type=JobType.upload_youtube,
        status=JobStatus.succeeded,
        source="manual",
        payload_json=payload.model_dump(),
        result_json={
            "playlist_id": playlist.id,
            "youtube_video_id": playlist.youtube_video_id,
            "output_video_path": playlist.output_video_path,
        },
        playlist=playlist,
    )
    db.add(job)
    db.commit()
    db.refresh(playlist)
    return PlaylistRead.model_validate(playlist)


@router.post("/{playlist_id}/openclaw/request-next")
async def request_next_playlist_from_openclaw(
    playlist_id: str,
    payload: PlaylistOpenClawNextRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    services = get_services(request)
    playlist = db.get(Playlist, playlist_id)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    if not playlist.youtube_video_id:
        raise HTTPException(status_code=400, detail="YouTube publish must complete before requesting the next playlist.")

    result = await post_next_playlist_request(
        db,
        services,
        playlist,
        prompt_override=payload.prompt,
    )

    meta = dict(playlist.metadata_json or {})
    meta["openclaw_next_request"] = result
    meta["openclaw_next_request_at"] = _utcnow().isoformat()
    if result.get("ok"):
        meta["openclaw_next_request_youtube_video_id"] = playlist.youtube_video_id
    playlist.metadata_json = meta
    db.add(playlist)
    db.commit()
    db.refresh(playlist)

    if not result.get("ok"):
        raise HTTPException(status_code=502, detail=result)
    return result
