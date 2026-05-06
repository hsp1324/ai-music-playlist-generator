import json
import shutil
import subprocess
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.enums import JobStatus, JobType, PlaylistStatus, TrackStatus
from app.models.job import Job
from app.models.playlist import Playlist
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
    _store_youtube_channel_metadata,
    _utcnow,
    approve_playlist_cover,
    approve_playlist_metadata,
    approve_playlist_publish,
    attach_uploaded_playlist_cover,
    attach_uploaded_loop_video,
    attach_uploaded_playlist_thumbnail,
    build_playlist_from_tracks,
    create_playlist_workspace,
    generate_playlist_cover,
    generate_playlist_metadata,
    list_available_approved_tracks,
    list_playlist_workspaces,
    queue_workspace_video_render,
    queue_workspace_audio_render,
    reorder_workspace_tracks,
    serialize_playlist_workspace,
    set_playlist_workspace_archive_state,
)
from app.utils.openclaw_slack_loop import post_next_playlist_request

router = APIRouter(prefix="/playlists", tags=["playlists"])

ALLOWED_COVER_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_LOOP_VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm"}
LOOP_VIDEO_MIN_SECONDS = 8.0
LOOP_VIDEO_MAX_SECONDS = 12.0
LOOP_VIDEO_SAMPLE_WIDTH = 64
LOOP_VIDEO_SAMPLE_HEIGHT = 36
LOOP_VIDEO_MIN_AVERAGE_MOTION = 1.25
LOOP_VIDEO_MIN_PEAK_MOTION = 2.0


def get_services(request: Request) -> ServiceRegistry:
    return request.app.state.services


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
    try:
        duration_seconds = float((payload.get("format") or {}).get("duration") or 0)
    except (TypeError, ValueError):
        duration_seconds = 0
    if not LOOP_VIDEO_MIN_SECONDS <= duration_seconds <= LOOP_VIDEO_MAX_SECONDS:
        raise HTTPException(
            status_code=400,
            detail=(
                "Loop video must be close to 10 seconds long "
                f"({LOOP_VIDEO_MIN_SECONDS:.0f}-{LOOP_VIDEO_MAX_SECONDS:.0f}s accepted)."
            ),
        )

    frame_size = LOOP_VIDEO_SAMPLE_WIDTH * LOOP_VIDEO_SAMPLE_HEIGHT
    try:
        frames = subprocess.run(
            [
                ffmpeg_binary,
                "-v",
                "error",
                "-i",
                str(path),
                "-vf",
                f"fps=1,scale={LOOP_VIDEO_SAMPLE_WIDTH}:{LOOP_VIDEO_SAMPLE_HEIGHT},format=gray",
                "-frames:v",
                "12",
                "-f",
                "rawvideo",
                "-",
            ],
            check=True,
            capture_output=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise HTTPException(status_code=400, detail="Uploaded loop video frames could not be decoded.") from exc

    samples = [
        frames[index : index + frame_size]
        for index in range(0, len(frames), frame_size)
        if len(frames[index : index + frame_size]) == frame_size
    ]
    if len(samples) < 3:
        raise HTTPException(status_code=400, detail="Uploaded loop video does not contain enough decodable frames.")

    differences = [
        sum(abs(left - right) for left, right in zip(previous, current)) / frame_size
        for previous, current in zip(samples, samples[1:])
    ]
    average_motion = sum(differences) / len(differences)
    peak_motion = max(differences)
    if average_motion < LOOP_VIDEO_MIN_AVERAGE_MOTION and peak_motion < LOOP_VIDEO_MIN_PEAK_MOTION:
        raise HTTPException(
            status_code=400,
            detail=(
                "Uploaded loop video has too little visible motion. "
                "Regenerate a moving 10 second Dreamina/Seedance clip before rendering."
            ),
        )


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
def list_workspace_playlists(db: Session = Depends(get_db)) -> list[PlaylistWorkspaceRead]:
    return [serialize_playlist_workspace(playlist) for playlist in list_playlist_workspaces(db)]


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
    db: Session = Depends(get_db),
) -> PlaylistWorkspaceRead:
    try:
        playlist = queue_workspace_audio_render(
            db,
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
        )
    except HTTPException:
        Path(loop_video_path).unlink(missing_ok=True)
        raise
    except ValueError as exc:
        Path(loop_video_path).unlink(missing_ok=True)
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
    db: Session = Depends(get_db),
) -> PlaylistWorkspaceRead:
    try:
        playlist = queue_workspace_video_render(
            db,
            playlist_id=playlist_id,
            actor=payload.actor,
            allow_still_image_fallback=payload.allow_still_image_fallback,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
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
    meta = {
        **(playlist.metadata_json or {}),
        "uploaded_by": payload.actor,
        "upload_note": payload.note,
        "workflow_state": "uploaded",
        "publish_ready": True,
        "publish_approved": True,
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
