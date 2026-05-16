from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.playlist import Playlist
from app.services.registry import ServiceRegistry
from app.utils.openclaw_slack_loop import post_backlog_queue_request
from app.workflows.openclaw_runtime import (
    acquire_openclaw_lock,
    build_openclaw_backlog_summary,
    evaluate_openclaw_backlog_scheduler,
    finish_openclaw_lock,
    get_openclaw_lock_status,
    heartbeat_openclaw_lock,
    record_openclaw_backlog_scheduler_request,
    read_runtime_state,
)

router = APIRouter(prefix="/openclaw", tags=["openclaw"])


class OpenClawLockRequest(BaseModel):
    owner: str = "openclaw"
    run_id: str = ""
    operation: str = ""
    channel_title: str = ""
    release_id: str = ""
    message: str = ""


class OpenClawLockFinishRequest(BaseModel):
    owner: str = "openclaw"
    run_id: str
    status: str = "completed"
    message: str = ""


class OpenClawBacklogRequest(BaseModel):
    reason: str = "manual"
    prompt: str | None = None


def get_services(request: Request) -> ServiceRegistry:
    return request.app.state.services


def _request_token(
    authorization: str | None = Header(default=None),
    x_openclaw_token: str | None = Header(default=None),
) -> str:
    if x_openclaw_token:
        return x_openclaw_token.strip()
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return ""


def _require_openclaw_token(services: ServiceRegistry, token: str) -> None:
    expected = services.settings.openclaw_shared_token.strip()
    if expected and not secrets.compare_digest(token, expected):
        raise HTTPException(status_code=403, detail="Invalid OpenClaw token.")


def _record_release_channel_hint(db: Session, *, release_id: str, channel_title: str) -> bool:
    normalized_release_id = release_id.strip()
    normalized_channel_title = channel_title.strip()
    if not normalized_release_id or not normalized_channel_title:
        return False

    playlist = db.get(Playlist, normalized_release_id)
    if playlist is None:
        return False

    meta = dict(playlist.metadata_json or {})
    changed = False
    if not str(meta.get("target_youtube_channel_title") or "").strip():
        meta["target_youtube_channel_title"] = normalized_channel_title
        changed = True
    if meta.get("openclaw_lock_channel_title") != normalized_channel_title:
        meta["openclaw_lock_channel_title"] = normalized_channel_title
        changed = True
    if not changed:
        return False

    playlist.metadata_json = meta
    db.add(playlist)
    db.commit()
    return True


@router.get("/status")
def openclaw_status(
    services: ServiceRegistry = Depends(get_services),
    token: str = Depends(_request_token),
) -> dict:
    _require_openclaw_token(services, token)
    return {
        "ok": True,
        "runtime": read_runtime_state(services.settings.storage_root),
        "lock": get_openclaw_lock_status(services.settings.storage_root),
    }


@router.post("/lock/start")
def start_lock(
    payload: OpenClawLockRequest,
    db: Session = Depends(get_db),
    services: ServiceRegistry = Depends(get_services),
    token: str = Depends(_request_token),
) -> dict:
    _require_openclaw_token(services, token)
    result = acquire_openclaw_lock(
        storage_root=services.settings.storage_root,
        ttl_seconds=services.settings.openclaw_lock_ttl_seconds,
        owner=payload.owner,
        run_id=payload.run_id,
        operation=payload.operation,
        channel_title=payload.channel_title,
        release_id=payload.release_id,
        message=payload.message,
    )
    if result.get("ok"):
        result["release_channel_hint_recorded"] = _record_release_channel_hint(
            db,
            release_id=payload.release_id,
            channel_title=payload.channel_title,
        )
    return result


@router.post("/lock/heartbeat")
def heartbeat_lock(
    payload: OpenClawLockRequest,
    db: Session = Depends(get_db),
    services: ServiceRegistry = Depends(get_services),
    token: str = Depends(_request_token),
) -> dict:
    _require_openclaw_token(services, token)
    result = heartbeat_openclaw_lock(
        storage_root=services.settings.storage_root,
        ttl_seconds=services.settings.openclaw_lock_ttl_seconds,
        owner=payload.owner,
        run_id=payload.run_id,
        operation=payload.operation,
        channel_title=payload.channel_title,
        release_id=payload.release_id,
        message=payload.message,
    )
    if result.get("ok"):
        result["release_channel_hint_recorded"] = _record_release_channel_hint(
            db,
            release_id=payload.release_id,
            channel_title=payload.channel_title,
        )
    return result


@router.post("/lock/finish")
def finish_lock(
    payload: OpenClawLockFinishRequest,
    services: ServiceRegistry = Depends(get_services),
    token: str = Depends(_request_token),
) -> dict:
    _require_openclaw_token(services, token)
    return finish_openclaw_lock(
        storage_root=services.settings.storage_root,
        owner=payload.owner,
        run_id=payload.run_id,
        status=payload.status,
        message=payload.message,
    )


@router.get("/backlog/status")
def backlog_status(
    request: Request,
    db: Session = Depends(get_db),
    token: str = Depends(_request_token),
) -> dict:
    services = get_services(request)
    _require_openclaw_token(services, token)
    return {
        "ok": True,
        "evaluation": evaluate_openclaw_backlog_scheduler(db, services),
        "summary": build_openclaw_backlog_summary(db, services),
    }


@router.post("/backlog/request")
async def request_backlog(
    payload: OpenClawBacklogRequest,
    request: Request,
    db: Session = Depends(get_db),
    token: str = Depends(_request_token),
) -> dict:
    services = get_services(request)
    _require_openclaw_token(services, token)
    evaluation = evaluate_openclaw_backlog_scheduler(db, services)
    blocking_reasons = {
        "openclaw_lock_active",
        "backlog_request_cooldown",
        "auto_loop_stopped",
        "max_uploads_reached",
    }
    if (
        not evaluation.get("should_request")
        and payload.reason != "manual-force"
        and evaluation.get("reason") in blocking_reasons
    ):
        return {"ok": True, "skipped": True, "evaluation": evaluation}
    result = await post_backlog_queue_request(
        db,
        services,
        reason=payload.reason or evaluation.get("reason") or "manual",
        backlog_summary=evaluation.get("summary"),
        prompt_override=payload.prompt,
    )
    if result.get("ok"):
        record_openclaw_backlog_scheduler_request(
            storage_root=services.settings.storage_root,
            result={
                **evaluation,
                "manual_reason": payload.reason,
                "slack": {key: result.get(key) for key in ("ok", "channel", "ts")},
            },
        )
    if not result.get("ok"):
        raise HTTPException(status_code=502, detail=result)
    return {"ok": True, "evaluation": evaluation, "slack": result}
