from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.playlist import Playlist
from app.services.registry import ServiceRegistry
from app.utils.openclaw_slack_loop import post_backlog_queue_request
from app.utils.video_render_policy import apply_release_vocal_metadata
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
from app.workflows.scripture_sequence import (
    ScriptureSequenceError,
    complete_scripture_passage,
    fail_scripture_passage,
    reserve_scripture_passage,
    scripture_sequence_status,
)

router = APIRouter(prefix="/openclaw", tags=["openclaw"])

BIBLE_SCRIPTURE_UPLOAD_CHANNEL_TITLE = "BibliaCanto"


def _canonical_scripture_branch_title(channel_title: str) -> str:
    normalized = str(channel_title or "").strip().lower().replace("-", "_")
    if normalized in {"bibliacanto", "biblia canto", "the old verse", "the_old_verse", "old testament", "old"}:
        return "The Old Verse"
    if normalized in {"the new verse", "the_new_verse", "new testament", "new_testament", "new"}:
        return "New Testament"
    return str(channel_title or "").strip()


def _scripture_upload_target_title(branch_title: str) -> str:
    if _canonical_scripture_branch_title(branch_title) in {"The Old Verse", "New Testament"}:
        return BIBLE_SCRIPTURE_UPLOAD_CHANNEL_TITLE
    return str(branch_title or "").strip()


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


class OpenClawScriptureReserveRequest(BaseModel):
    channel_title: str
    release_id: str = ""
    title: str = ""
    notes: str = ""
    passage_range: str = ""


class OpenClawScriptureCompleteRequest(BaseModel):
    channel_title: str
    passage_range: str
    status: str = "scheduled"
    release_id: str = ""
    youtube_video_id: str = ""
    title: str = ""
    notes: str = ""
    next_start: str = ""


class OpenClawScriptureFailRequest(BaseModel):
    channel_title: str
    passage_range: str
    release_id: str = ""
    title: str = ""
    reason: str = ""


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
    before_vocal = (
        meta.get("release_vocal_mode"),
        meta.get("release_has_singable_lyrics"),
        meta.get("release_vocal_mode_source"),
    )
    apply_release_vocal_metadata(meta)
    after_vocal = (
        meta.get("release_vocal_mode"),
        meta.get("release_has_singable_lyrics"),
        meta.get("release_vocal_mode_source"),
    )
    if after_vocal != before_vocal:
        changed = True
    if not changed:
        return False

    playlist.metadata_json = meta
    db.add(playlist)
    db.commit()
    return True


def _record_release_scripture_hint(
    db: Session,
    *,
    release_id: str,
    channel_title: str,
    passage_range: str,
    sequence_status: str,
) -> bool:
    normalized_release_id = release_id.strip()
    if not normalized_release_id:
        return False

    playlist = db.get(Playlist, normalized_release_id)
    if playlist is None:
        return False

    meta = dict(playlist.metadata_json or {})
    changed = False
    normalized_channel_title = _canonical_scripture_branch_title(channel_title)
    normalized_passage_range = passage_range.strip()
    target_channel_title = _scripture_upload_target_title(normalized_channel_title)
    current_target = str(meta.get("target_youtube_channel_title") or "").strip()
    if target_channel_title and current_target != target_channel_title:
        meta["target_youtube_channel_title"] = target_channel_title
        changed = True
    scripture_updates = {
        "scripture_channel_title": normalized_channel_title,
        "scripture_passage_range": normalized_passage_range,
        "scripture_sequence_status": sequence_status,
    }
    for key, value in scripture_updates.items():
        if value and meta.get(key) != value:
            meta[key] = value
            changed = True
    before_vocal = (
        meta.get("release_vocal_mode"),
        meta.get("release_has_singable_lyrics"),
        meta.get("release_vocal_mode_source"),
    )
    apply_release_vocal_metadata(meta)
    after_vocal = (
        meta.get("release_vocal_mode"),
        meta.get("release_has_singable_lyrics"),
        meta.get("release_vocal_mode_source"),
    )
    if after_vocal != before_vocal:
        changed = True
    if not changed:
        return False

    playlist.metadata_json = meta
    db.add(playlist)
    db.commit()
    return True


def _scripture_http_error(exc: ScriptureSequenceError) -> HTTPException:
    status_code = 409 if exc.code in {"passage_already_active", "next_block_missing"} else 400
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": str(exc)})


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


@router.get("/scripture/status")
def scripture_status(
    services: ServiceRegistry = Depends(get_services),
    token: str = Depends(_request_token),
) -> dict:
    _require_openclaw_token(services, token)
    return {"ok": True, **scripture_sequence_status(services.settings.storage_root)}


@router.post("/scripture/reserve")
def reserve_scripture(
    payload: OpenClawScriptureReserveRequest,
    db: Session = Depends(get_db),
    services: ServiceRegistry = Depends(get_services),
    token: str = Depends(_request_token),
) -> dict:
    _require_openclaw_token(services, token)
    try:
        result = reserve_scripture_passage(
            services.settings.storage_root,
            channel_title=payload.channel_title,
            release_id=payload.release_id,
            title=payload.title,
            notes=payload.notes,
            passage_range=payload.passage_range,
        )
    except ScriptureSequenceError as exc:
        raise _scripture_http_error(exc) from exc
    entry = dict(result.get("entry") or {})
    result["release_scripture_hint_recorded"] = _record_release_scripture_hint(
        db,
        release_id=payload.release_id,
        channel_title=result.get("channel") or payload.channel_title,
        passage_range=str(entry.get("passage_range") or ""),
        sequence_status=str(entry.get("status") or "in_progress"),
    )
    return {"ok": True, **result}


@router.post("/scripture/complete")
def complete_scripture(
    payload: OpenClawScriptureCompleteRequest,
    db: Session = Depends(get_db),
    services: ServiceRegistry = Depends(get_services),
    token: str = Depends(_request_token),
) -> dict:
    _require_openclaw_token(services, token)
    try:
        result = complete_scripture_passage(
            services.settings.storage_root,
            channel_title=payload.channel_title,
            passage_range=payload.passage_range,
            status=payload.status,
            release_id=payload.release_id,
            youtube_video_id=payload.youtube_video_id,
            title=payload.title,
            notes=payload.notes,
            next_start=payload.next_start,
        )
    except ScriptureSequenceError as exc:
        raise _scripture_http_error(exc) from exc
    entry = dict(result.get("entry") or {})
    result["release_scripture_hint_recorded"] = _record_release_scripture_hint(
        db,
        release_id=payload.release_id,
        channel_title=result.get("channel") or payload.channel_title,
        passage_range=str(entry.get("passage_range") or payload.passage_range),
        sequence_status=str(entry.get("status") or payload.status),
    )
    return {"ok": True, **result}


@router.post("/scripture/fail")
def fail_scripture(
    payload: OpenClawScriptureFailRequest,
    db: Session = Depends(get_db),
    services: ServiceRegistry = Depends(get_services),
    token: str = Depends(_request_token),
) -> dict:
    _require_openclaw_token(services, token)
    try:
        result = fail_scripture_passage(
            services.settings.storage_root,
            channel_title=payload.channel_title,
            passage_range=payload.passage_range,
            release_id=payload.release_id,
            title=payload.title,
            reason=payload.reason,
        )
    except ScriptureSequenceError as exc:
        raise _scripture_http_error(exc) from exc
    entry = dict(result.get("entry") or {})
    result["release_scripture_hint_recorded"] = _record_release_scripture_hint(
        db,
        release_id=payload.release_id,
        channel_title=result.get("channel") or payload.channel_title,
        passage_range=str(entry.get("passage_range") or payload.passage_range),
        sequence_status=str(entry.get("status") or "failed"),
    )
    return {"ok": True, **result}
