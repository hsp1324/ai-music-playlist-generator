from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.enums import JobStatus, JobType
from app.models.job import Job
from app.models.track import Track
from app.schemas.suno import SunoGenerationCreateRequest, SunoWebhookRequest
from app.services.registry import ServiceRegistry
from app.services.suno_service import SunoGenerationRequest
from app.workflows.review_dispatch import dispatch_track_review

router = APIRouter(prefix="/suno", tags=["suno"])


def get_services(request: Request) -> ServiceRegistry:
    return request.app.state.services


async def _notify_session_login_required(
    services: ServiceRegistry,
    db: Session,
    *,
    reason: str,
) -> None:
    installation = services.slack_installations.get_active_installation(db)
    token = installation.bot_token if installation else services.settings.slack_bot_token
    await services.slack.post_ops_message(
        token=token,
        text=(
            f"Suno session requires login. Reason: {reason}. "
            f"Open {services.settings.public_base_url}/ and use the session panel to re-authenticate."
        ),
    )


@router.post("/generations", status_code=status.HTTP_202_ACCEPTED)
def create_suno_generation(
    payload: SunoGenerationCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    services = get_services(request)
    if services.settings.suno_provider_mode == "browser_profile":
        session_status = services.suno_session.get_status()
        if session_status.needs_login:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "suno_login_required",
                    "session_status": session_status.__dict__,
                },
            )
        raise HTTPException(
            status_code=501,
            detail={
                "error": "browser_profile_generation_not_implemented",
                "message": "Session management is ready, but browser-profile generation adapter is not implemented yet.",
                "session_status": session_status.__dict__,
            },
        )

    generation_request = SunoGenerationRequest(
        title=payload.title,
        prompt=payload.prompt,
        metadata=payload.metadata,
        custom_mode=payload.custom_mode,
        instrumental=payload.instrumental,
        model=payload.model,
        style=payload.style,
        callback_url=payload.callback_url,
        persona_id=payload.persona_id,
        persona_model=payload.persona_model,
        negative_tags=payload.negative_tags,
        vocal_gender=payload.vocal_gender,
        style_weight=payload.style_weight,
        weirdness_constraint=payload.weirdness_constraint,
        audio_weight=payload.audio_weight,
    )
    result = services.suno.submit_generation_batch([generation_request])[0]

    job = Job(
        type=JobType.generate_track,
        status=JobStatus.queued if result.ok else JobStatus.failed,
        source=f"suno:{services.settings.suno_provider_mode}",
        payload_json=payload.model_dump(),
        result_json=result.raw,
        error_text=None if result.ok else str(result.raw),
        external_id=result.provider_job_id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    return {
        "ok": result.ok,
        "job_id": job.id,
        "provider_job_id": job.external_id,
        "provider_mode": services.settings.suno_provider_mode,
        "provider_response": result.raw,
    }


@router.get("/generations/{task_id}")
def get_suno_generation_details(task_id: str, request: Request) -> dict:
    services = get_services(request)
    return services.suno.get_generation_details(task_id)


@router.get("/credits")
def get_suno_credits(request: Request) -> dict:
    services = get_services(request)
    return services.suno.get_remaining_credits()


@router.get("/session-status")
def get_suno_session_status(request: Request) -> dict:
    services = get_services(request)
    return services.suno_session.get_status().__dict__


@router.post("/session/open-login")
def open_suno_login_window(request: Request) -> dict:
    services = get_services(request)
    return services.suno_session.open_login_window()


@router.post("/session/notify-expired")
async def notify_suno_session_expired(
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    services = get_services(request)
    status_payload = services.suno_session.mark_login_required()
    await _notify_session_login_required(services, db, reason=status_payload.message)
    return {
        "ok": True,
        "session_status": status_payload.__dict__,
    }


@router.post("/webhook")
async def suno_webhook(
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    services = get_services(request)
    raw_body = await request.body()
    signature = request.headers.get("x-suno-signature")
    if not services.suno.verify_webhook_signature(raw_body, signature):
        raise HTTPException(status_code=401, detail="Invalid Suno webhook signature")

    payload_dict = await request.json()
    payload = SunoWebhookRequest.model_validate(payload_dict)
    normalized = services.suno.normalize_webhook_payload(
        payload.model_dump(by_alias=True, exclude_none=True)
    )

    job = None
    if normalized.provider_job_id:
        job = db.scalars(
            select(Job).where(Job.external_id == normalized.provider_job_id)
        ).first()
    if job:
        job.result_json = {
            **job.result_json,
            "webhook_received": True,
            "callback_type": normalized.callback_type,
            "provider_payload": normalized.raw,
        }
        job.status = JobStatus.succeeded if normalized.ok and normalized.tracks else JobStatus.running
        if not normalized.ok:
            job.status = JobStatus.failed
            job.error_text = normalized.error_message
        db.add(job)

    if not normalized.ok:
        db.commit()
        return {
            "ok": False,
            "provider_job_id": normalized.provider_job_id,
            "callback_type": normalized.callback_type,
            "message": normalized.error_message,
            "tracks_created": 0,
            "track_ids": [],
        }

    if not normalized.tracks:
        db.commit()
        return {
            "ok": True,
            "provider_job_id": normalized.provider_job_id,
            "callback_type": normalized.callback_type,
            "message": "Progress callback received",
            "tracks_created": 0,
            "track_ids": [],
        }

    tracks: list[Track] = []
    for item in normalized.tracks:
        track = None
        if item.source_track_id:
            track = db.scalars(
                select(Track).where(Track.source_track_id == item.source_track_id)
            ).first()
        if not track:
            track = Track(source_track_id=item.source_track_id)
        track.title = item.title
        track.prompt = item.prompt
        track.duration_seconds = item.duration_seconds
        track.audio_path = item.audio_path
        track.preview_url = item.preview_url
        track.metadata_json = item.metadata
        db.add(track)
        db.flush()
        tracks.append(track)

    if job and tracks:
        job.track_id = tracks[0].id
        job.status = JobStatus.succeeded
        job.result_json = {
            **job.result_json,
            "track_ids": [track.id for track in tracks],
        }
        db.add(job)

    db.commit()
    for track in tracks:
        db.refresh(track)

    for track in tracks:
        await dispatch_track_review(db, services, track)

    return {
        "ok": True,
        "callback_type": normalized.callback_type,
        "provider_job_id": normalized.provider_job_id,
        "tracks_created": len(tracks),
        "track_ids": [track.id for track in tracks],
    }
