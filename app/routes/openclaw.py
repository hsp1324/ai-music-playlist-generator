from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
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
    services: ServiceRegistry = Depends(get_services),
    token: str = Depends(_request_token),
) -> dict:
    _require_openclaw_token(services, token)
    return acquire_openclaw_lock(
        storage_root=services.settings.storage_root,
        ttl_seconds=services.settings.openclaw_lock_ttl_seconds,
        owner=payload.owner,
        run_id=payload.run_id,
        operation=payload.operation,
        channel_title=payload.channel_title,
        release_id=payload.release_id,
        message=payload.message,
    )


@router.post("/lock/heartbeat")
def heartbeat_lock(
    payload: OpenClawLockRequest,
    services: ServiceRegistry = Depends(get_services),
    token: str = Depends(_request_token),
) -> dict:
    _require_openclaw_token(services, token)
    return heartbeat_openclaw_lock(
        storage_root=services.settings.storage_root,
        ttl_seconds=services.settings.openclaw_lock_ttl_seconds,
        owner=payload.owner,
        run_id=payload.run_id,
        operation=payload.operation,
        channel_title=payload.channel_title,
        release_id=payload.release_id,
        message=payload.message,
    )


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
