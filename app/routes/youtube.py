from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.enums import PlaylistStatus
from app.models.playlist import Playlist
from app.services.registry import ServiceRegistry
from app.utils.youtube_localizations import (
    DEFAULT_YOUTUBE_LANGUAGE,
    normalize_youtube_language,
    normalize_youtube_localizations,
    sanitize_youtube_copy,
)
from app.workflows.playlist_automation import resume_youtube_publish_after_auth

router = APIRouter(prefix="/youtube", tags=["youtube"])


class YouTubeChannelSelectRequest(BaseModel):
    channel_id: str


class YouTubeImportUploadsRequest(BaseModel):
    channel_id: str | None = None
    max_results: int = 20
    update_existing: bool = True


def get_services(request: Request) -> ServiceRegistry:
    return request.app.state.services


@router.get("/status")
def youtube_status(request: Request):
    services = get_services(request)
    status = services.youtube.get_status()
    accept = request.headers.get("accept", "")
    if "text/html" in accept and "application/json" not in accept:
        channels = status.get("channels") if isinstance(status, dict) else []
        channel_titles = [
            str(channel.get("title") or channel.get("id") or "").strip()
            for channel in channels or []
            if isinstance(channel, dict) and str(channel.get("title") or channel.get("id") or "").strip()
        ]
        channel_list = ", ".join(channel_titles) if channel_titles else "No connected channels found."
        ready_text = "ready" if status.get("ready") else "not ready"
        return HTMLResponse(
            "<!doctype html>"
            "<meta charset='utf-8'>"
            "<title>YouTube API Status</title>"
            "<body style='font-family:sans-serif;max-width:760px;margin:48px auto;line-height:1.5'>"
            "<h1>YouTube API Status</h1>"
            f"<p>Status: <strong>{ready_text}</strong></p>"
            f"<p>Channels: {channel_list}</p>"
            "<p>This is an automation API endpoint. OpenClaw should read it with "
            "<code>curl -fsS \"$AIMP_LOCAL_API_BASE/youtube/status\"</code> or "
            "<code>scripts/openclaw-release</code>, not by opening it in the browser.</p>"
            "<p><a href='/'>Back to dashboard</a></p>"
            "</body>"
        )
    return status


@router.get("/connect")
def youtube_connect_redirect(request: Request, playlist_id: str | None = None) -> RedirectResponse:
    services = get_services(request)
    try:
        if playlist_id:
            payload = services.youtube.build_authorization_url(playlist_id=playlist_id)
        else:
            payload = services.youtube.build_authorization_url()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return RedirectResponse(payload["authorization_url"])


@router.post("/connect")
def youtube_connect(request: Request, playlist_id: str | None = None) -> dict:
    services = get_services(request)
    try:
        if playlist_id:
            return services.youtube.build_authorization_url(playlist_id=playlist_id)
        return services.youtube.build_authorization_url()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/channels/select")
def youtube_select_channel(payload: YouTubeChannelSelectRequest, request: Request) -> dict:
    services = get_services(request)
    try:
        return services.youtube.select_channel(payload.channel_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/import-uploads")
def youtube_import_uploads(
    payload: YouTubeImportUploadsRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    services = get_services(request)
    status = services.youtube.get_status()
    channel_id = payload.channel_id or status.get("selected_channel_id")
    if not channel_id:
        raise HTTPException(status_code=400, detail="Select or connect a YouTube channel before importing uploads.")

    try:
        uploads = services.youtube.list_channel_uploads(channel_id=channel_id, max_results=payload.max_results)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    imported: list[dict] = []
    updated: list[dict] = []
    skipped: list[dict] = []
    now = datetime.now(timezone.utc).isoformat()
    for upload in uploads:
        video_id = str(upload.get("video_id") or "").strip()
        if not video_id:
            continue
        playlist = db.scalars(select(Playlist).where(Playlist.youtube_video_id == video_id)).first()
        if playlist and not payload.update_existing:
            skipped.append({"video_id": video_id, "reason": "already_exists", "playlist_id": playlist.id})
            continue

        title = sanitize_youtube_copy(upload.get("title") or video_id).strip()[:255]
        description = sanitize_youtube_copy(upload.get("description") or "").strip()
        tags = [str(tag).strip() for tag in upload.get("tags") or [] if str(tag).strip()][:15]
        default_language = normalize_youtube_language(
            upload.get("default_language") or upload.get("default_audio_language") or DEFAULT_YOUTUBE_LANGUAGE
        )
        localizations = normalize_youtube_localizations(
            upload.get("localizations"),
            default_title=title,
            default_description=description,
            default_language=default_language,
        )
        duration_seconds = int(upload.get("duration_seconds") or 0)
        meta = {
            **(playlist.metadata_json if playlist else {}),
            "workspace_mode": "youtube_import",
            "workflow_state": "uploaded",
            "publish_ready": True,
            "publish_approved": True,
            "metadata_approved": True,
            "youtube_title": title,
            "youtube_description": description,
            "youtube_tags": tags,
            "youtube_default_language": default_language,
            "youtube_localizations": localizations,
            "youtube_channel_id": upload.get("channel_id") or channel_id,
            "youtube_channel_title": upload.get("channel_title") or status.get("selected_channel_title"),
            "youtube_published_at": upload.get("published_at"),
            "youtube_privacy_status": upload.get("privacy_status"),
            "youtube_thumbnail_path": upload.get("thumbnail_url"),
            "youtube_thumbnail_source": "youtube-import",
            "youtube_import_source": "channel_uploads",
            "youtube_imported_at": now,
        }

        if playlist:
            playlist.title = title or playlist.title
            playlist.status = PlaylistStatus.uploaded
            playlist.actual_duration_seconds = duration_seconds or playlist.actual_duration_seconds
            if duration_seconds and playlist.target_duration_seconds <= 0:
                playlist.target_duration_seconds = duration_seconds
            playlist.metadata_json = meta
            db.add(playlist)
            updated.append({"video_id": video_id, "playlist_id": playlist.id, "title": title})
        else:
            playlist = Playlist(
                title=title or video_id,
                status=PlaylistStatus.uploaded,
                target_duration_seconds=duration_seconds,
                actual_duration_seconds=duration_seconds,
                youtube_video_id=video_id,
                metadata_json=meta,
            )
            db.add(playlist)
            db.flush()
            imported.append({"video_id": video_id, "playlist_id": playlist.id, "title": title})

    db.commit()
    return {
        "ok": True,
        "channel_id": channel_id,
        "imported": imported,
        "updated": updated,
        "skipped": skipped,
        "count": len(imported) + len(updated),
    }


@router.get("/oauth/callback")
def youtube_oauth_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    if error:
        raise HTTPException(status_code=400, detail=f"YouTube OAuth failed: {error}")
    if not code:
        raise HTTPException(status_code=400, detail="YouTube OAuth callback is missing code.")

    services = get_services(request)
    try:
        result = services.youtube.exchange_web_code(code, state)
        playlist_id = result.get("playlist_id")
        if result.get("ready") and playlist_id:
            resume_youtube_publish_after_auth(
                db,
                services,
                playlist_id=playlist_id,
                youtube_channel_id=result.get("channel_id"),
            )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return RedirectResponse("/?youtube=connected")
