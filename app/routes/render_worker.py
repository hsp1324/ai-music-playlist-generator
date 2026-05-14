import shutil
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.render_worker import (
    RenderWorkerClaimRequest,
    RenderWorkerFailRequest,
    RenderWorkerHeartbeatRequest,
    RenderWorkerResponse,
)
from app.services.registry import ServiceRegistry
from app.workflows.render_worker_queue import (
    RenderWorkerAuthError,
    RenderWorkerJobError,
    claim_external_video_job,
    complete_external_video_job,
    get_render_worker_asset_path,
    load_external_running_job,
    mark_external_video_job_failed,
    update_external_video_heartbeat,
    validate_worker_shared_token,
)

router = APIRouter(prefix="/render-worker", tags=["render-worker"])


def get_services(request: Request) -> ServiceRegistry:
    return request.app.state.services


def _worker_token_from_request(
    x_aimp_render_worker_token: str | None = Header(default=None),
    worker_token: str | None = Query(default=None),
) -> str | None:
    return x_aimp_render_worker_token or worker_token


def _require_worker_token(services: ServiceRegistry, supplied_token: str | None) -> None:
    try:
        validate_worker_shared_token(services.settings.render_worker_shared_token, supplied_token)
    except RenderWorkerAuthError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/claim")
def claim_render_job(
    payload: RenderWorkerClaimRequest,
    services: ServiceRegistry = Depends(get_services),
    db: Session = Depends(get_db),
    worker_token: str | None = Depends(_worker_token_from_request),
) -> dict:
    _require_worker_token(services, worker_token)
    manifest = claim_external_video_job(
        db,
        services,
        worker_id=payload.worker_id,
        capabilities=payload.capabilities,
    )
    if manifest is None:
        return {"has_job": False, "message": "No queued video render jobs."}
    return manifest


@router.get("/jobs/{job_id}/assets/{asset_name}")
def download_render_asset(
    job_id: str,
    asset_name: str,
    lease_token: str = Query(...),
    services: ServiceRegistry = Depends(get_services),
    db: Session = Depends(get_db),
    worker_token: str | None = Depends(_worker_token_from_request),
) -> FileResponse:
    _require_worker_token(services, worker_token)
    try:
        path = get_render_worker_asset_path(
            db,
            job_id=job_id,
            lease_token=lease_token,
            asset_name=asset_name,
        )
    except RenderWorkerAuthError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except RenderWorkerJobError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not path.exists():
        raise HTTPException(status_code=404, detail="Render asset not found.")
    return FileResponse(path, filename=path.name)


@router.post("/jobs/{job_id}/heartbeat", response_model=RenderWorkerResponse)
def heartbeat_render_job(
    job_id: str,
    payload: RenderWorkerHeartbeatRequest,
    services: ServiceRegistry = Depends(get_services),
    db: Session = Depends(get_db),
    worker_token: str | None = Depends(_worker_token_from_request),
) -> RenderWorkerResponse:
    _require_worker_token(services, worker_token)
    try:
        progress = update_external_video_heartbeat(
            db,
            job_id=job_id,
            lease_token=payload.lease_token,
            worker_id=payload.worker_id,
            progress=payload.progress,
            message=payload.message,
        )
    except RenderWorkerAuthError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except RenderWorkerJobError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RenderWorkerResponse(
        ok=True,
        job_id=job_id,
        message=str(progress.get("message") or "Heartbeat recorded."),
    )


@router.post("/jobs/{job_id}/complete", response_model=RenderWorkerResponse)
def complete_render_job(
    job_id: str,
    lease_token: str = Form(...),
    worker_id: str = Form("render-worker"),
    output_file: UploadFile = File(...),
    services: ServiceRegistry = Depends(get_services),
    db: Session = Depends(get_db),
    worker_token: str | None = Depends(_worker_token_from_request),
) -> RenderWorkerResponse:
    _require_worker_token(services, worker_token)
    try:
        job = load_external_running_job(db, job_id=job_id, lease_token=lease_token)
    except RenderWorkerAuthError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except RenderWorkerJobError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not job.playlist_id:
        raise HTTPException(status_code=400, detail="Render job is missing playlist id.")
    if not output_file.filename:
        raise HTTPException(status_code=400, detail="Rendered video upload is missing filename.")

    services.settings.playlists_dir.mkdir(parents=True, exist_ok=True)
    services.settings.temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = services.settings.temp_dir / f"{job_id}-external-render-{uuid4().hex}.mp4.part"
    destination = services.settings.playlists_dir / f"{job.playlist_id}.mp4"
    with temp_path.open("wb") as handle:
        shutil.copyfileobj(output_file.file, handle)
    if not temp_path.exists() or temp_path.stat().st_size == 0:
        temp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Rendered video upload is empty.")
    temp_path.replace(destination)

    try:
        result = complete_external_video_job(
            db,
            services,
            job_id=job_id,
            lease_token=lease_token,
            worker_id=worker_id,
            rendered_video_path=destination,
        )
    except RenderWorkerAuthError as exc:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except RenderWorkerJobError as exc:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RenderWorkerResponse(**result)


@router.post("/jobs/{job_id}/fail", response_model=RenderWorkerResponse)
def fail_render_job(
    job_id: str,
    payload: RenderWorkerFailRequest,
    services: ServiceRegistry = Depends(get_services),
    db: Session = Depends(get_db),
    worker_token: str | None = Depends(_worker_token_from_request),
) -> RenderWorkerResponse:
    _require_worker_token(services, worker_token)
    try:
        job = load_external_running_job(db, job_id=job_id, lease_token=payload.lease_token)
    except RenderWorkerAuthError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except RenderWorkerJobError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    mark_external_video_job_failed(db, job, payload.error_text)
    return RenderWorkerResponse(
        ok=True,
        job_id=job_id,
        playlist_id=job.playlist_id,
        workflow_state="video_build_failed",
        message="Render job marked failed.",
    )
