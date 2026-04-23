from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.enums import JobStatus, JobType, PlaylistStatus, TrackStatus
from app.models.job import Job
from app.models.playlist import Playlist
from app.models.track import Track
from app.schemas.playlist import (
    PlaylistBuildRequest,
    PlaylistPublishApproveRequest,
    PlaylistRead,
    PlaylistUploadMarkRequest,
    PlaylistWorkspaceCreateRequest,
    PlaylistWorkspaceRead,
)
from app.services.registry import ServiceRegistry
from app.workflows.playlist_automation import (
    approve_playlist_publish,
    build_playlist_from_tracks,
    create_playlist_workspace,
    list_available_approved_tracks,
    list_playlist_workspaces,
    serialize_playlist_workspace,
)

router = APIRouter(prefix="/playlists", tags=["playlists"])


def get_services(request: Request) -> ServiceRegistry:
    return request.app.state.services


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
        description=payload.description,
        cover_prompt=payload.cover_prompt,
    )
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
            note=payload.note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return serialize_playlist_workspace(playlist)


@router.post("/{playlist_id}/mark-uploaded", response_model=PlaylistRead)
def mark_playlist_uploaded(
    playlist_id: str,
    payload: PlaylistUploadMarkRequest,
    db: Session = Depends(get_db),
) -> PlaylistRead:
    playlist = db.get(Playlist, playlist_id)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    playlist.status = PlaylistStatus.uploaded
    if payload.youtube_video_id:
        playlist.youtube_video_id = payload.youtube_video_id
    if payload.output_video_path:
        playlist.output_video_path = payload.output_video_path
    playlist.metadata_json = {
        **(playlist.metadata_json or {}),
        "uploaded_by": payload.actor,
        "upload_note": payload.note,
        "workflow_state": "uploaded",
        "publish_ready": True,
        "publish_approved": True,
    }
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
