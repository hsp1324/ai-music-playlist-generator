import json
from secrets import token_urlsafe
from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.enums import DecisionSource, DecisionValue, TrackStatus
from app.models.playlist import Playlist
from app.models.slack_installation import SlackInstallation
from app.models.track import Track
from app.services.registry import ServiceRegistry
from app.workflows.approvals import apply_track_decision
from app.workflows.playlist_automation import (
    assign_track_to_playlist,
    maybe_archive_rejected_single_workspace,
    maybe_build_auto_playlist,
    return_track_to_workspace_queue,
)
from app.workflows.slack_sync import sync_slack_review_decision

router = APIRouter(prefix="/slack", tags=["slack"])


def get_services(request: Request) -> ServiceRegistry:
    return request.app.state.services


def _status_counts(db: Session) -> dict[str, int]:
    rows = db.execute(select(Track.status, func.count(Track.id)).group_by(Track.status)).all()
    return {status.value if hasattr(status, "value") else str(status): count for status, count in rows}


def _bot_token_for_team(services: ServiceRegistry, db: Session, team_id: str | None = None) -> str | None:
    installation = services.slack_installations.get_active_installation(db, team_id)
    return installation.bot_token if installation else services.settings.slack_bot_token


def _interaction_message_target(payload: dict) -> tuple[str | None, str | None]:
    container = payload.get("container") or {}
    channel = payload.get("channel") or {}
    message = payload.get("message") or {}
    return (
        container.get("channel_id") or channel.get("id"),
        container.get("message_ts") or message.get("ts"),
    )


@router.get("/install")
async def slack_install(request: Request) -> RedirectResponse:
    services = get_services(request)
    install_url = services.slack.build_install_url(state=token_urlsafe(16))
    return RedirectResponse(url=install_url, status_code=302)


@router.get("/oauth/callback")
async def slack_oauth_callback(
    code: str,
    request: Request,
    db: Session = Depends(get_db),
) -> JSONResponse:
    services = get_services(request)
    result = await services.slack.exchange_code_for_installation(code)
    if not result.ok:
        raise HTTPException(status_code=400, detail=result.raw)

    installation = services.slack.installation_from_oauth(result.raw)
    if not installation:
        raise HTTPException(status_code=400, detail="Slack OAuth response missing installation details")

    saved = services.slack_installations.upsert_installation(db, installation)
    db.commit()
    db.refresh(saved)
    return JSONResponse(
        {
            "ok": True,
            "team_id": saved.team_id,
            "team_name": saved.team_name,
            "installed_by_user_id": saved.installed_by_user_id,
        }
    )


@router.get("/installations")
async def list_installations(
    db: Session = Depends(get_db),
) -> list[dict[str, str | bool | None]]:
    installations = db.scalars(
        select(SlackInstallation).order_by(SlackInstallation.updated_at.desc())
    ).all()
    return [
        {
            "team_id": installation.team_id,
            "team_name": installation.team_name,
            "bot_user_id": installation.bot_user_id,
            "installed_by_user_id": installation.installed_by_user_id,
            "is_active": installation.is_active,
        }
        for installation in installations
    ]


@router.post("/events")
async def slack_events(
    request: Request,
    db: Session = Depends(get_db),
) -> JSONResponse:
    services = get_services(request)
    raw_body = await request.body()
    headers = {key.lower(): value for key, value in request.headers.items()}

    if not services.slack.verify_signature(headers, raw_body):
        raise HTTPException(status_code=401, detail="Invalid Slack signature")

    payload = await request.json()

    if payload.get("type") == "url_verification":
        return JSONResponse({"challenge": payload["challenge"]})

    event = payload.get("event", {})
    if event.get("type") == "app_home_opened":
        token = _bot_token_for_team(services, db, payload.get("team_id"))
        status_counts = _status_counts(db)
        publish_result = {"ok": False, "error": "missing_bot_token"}
        if token and event.get("user"):
            publish_result = await services.slack.publish_app_home(
                user_id=event["user"],
                stats=status_counts,
                token=token,
            )
        return JSONResponse(
            {
                "ok": True,
                "published": publish_result.get("ok", False),
                "publish_result": publish_result,
            }
        )

    return JSONResponse({"ok": True})


@router.post("/interactions")
async def slack_interactions(
    request: Request,
    db: Session = Depends(get_db),
) -> JSONResponse:
    services = get_services(request)
    raw_body = await request.body()
    headers = {key.lower(): value for key, value in request.headers.items()}
    form_data = parse_qs(raw_body.decode("utf-8"))

    if form_data.get("ssl_check", ["0"])[0] == "1":
        return JSONResponse({"ok": True})

    if not services.slack.verify_signature(headers, raw_body):
        raise HTTPException(status_code=401, detail="Invalid Slack signature")

    payload_raw = form_data.get("payload", [None])[0]
    if not payload_raw:
        raise HTTPException(status_code=400, detail="Missing Slack payload")

    payload = json.loads(payload_raw)
    actions = payload.get("actions", [])
    if not actions:
        return JSONResponse({"text": "No action found."})

    action_value = actions[0].get("value", "")
    parsed = services.slack.parse_track_action(action_value)
    if not parsed:
        system_action = services.slack.parse_system_action(action_value)
        if system_action == "refresh_dashboard":
            status_counts = _status_counts(db)
            team = payload.get("team", {})
            token = _bot_token_for_team(services, db, team.get("id"))
            user = payload.get("user", {})
            publish_result = await services.slack.publish_app_home(
                user_id=user.get("id", ""),
                stats=status_counts,
                token=token,
            )
            return JSONResponse({"text": "Dashboard refreshed.", "publish_result": publish_result})

        if system_action == "build_playlist":
            approved_count = db.scalar(
                select(func.count(Track.id)).where(Track.status == TrackStatus.approved)
            ) or 0
            playlist_count = db.scalar(select(func.count(Playlist.id))) or 0
            return JSONResponse(
                {
                    "text": (
                        f"Approved tracks available: {approved_count}. "
                        "Use POST /api/playlists/build to render the next playlist."
                    ),
                    "approved_count": approved_count,
                    "existing_playlists": playlist_count,
                }
            )

        return JSONResponse({"text": "Unsupported action."})

    track_id, action_text = parsed
    track = db.get(Track, track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    user = payload.get("user", {})
    actor = user.get("username") or user.get("name") or user.get("id") or "slack-user"

    clicked_channel, clicked_ts = _interaction_message_target(payload)
    if clicked_channel and clicked_ts:
        track.slack_channel_id = clicked_channel
        track.slack_message_ts = clicked_ts
        db.add(track)
        db.commit()
        db.refresh(track)

    if action_text == "return_to_review":
        pending_workspace_id = (track.metadata_json or {}).get("pending_workspace_id")
        if not pending_workspace_id:
            return JSONResponse(
                {
                    "text": f"Could not return `{track.title}` to queue: no workspace is linked.",
                    "track_status": track.status.value,
                    "slack_update_ok": False,
                }
            )

        apply_track_decision(
            db,
            track,
            decision=DecisionValue.hold,
            source=DecisionSource.slack,
            actor=actor,
            rationale="Returned from approved state to the review queue from Slack.",
        )
        db.commit()
        db.refresh(track)

        assignment_error = None
        workspace_title = None
        try:
            playlist = await return_track_to_workspace_queue(
                db,
                services,
                track=track,
                playlist_id=pending_workspace_id,
                actor=actor,
            )
            workspace_title = playlist.title
        except ValueError as exc:
            assignment_error = str(exc)

        db.refresh(track)
        response_text = (
            f"Returned `{track.title}` to the review queue"
            f"{f' for workspace `{workspace_title}`' if workspace_title else ''}."
        )
        if assignment_error:
            response_text = f"Could not return `{track.title}` to queue: {assignment_error}."

        installation = services.slack_installations.get_active_installation(db)
        token = installation.bot_token if installation else services.settings.slack_bot_token
        update_result = await services.slack.update_review_request_message(track, token=token)
        return JSONResponse(
            {
                "text": response_text,
                "track_status": track.status.value,
                "assignment_error": assignment_error,
                "slack_update_ok": update_result.ok,
            }
        )

    decision = DecisionValue(action_text)

    apply_track_decision(
        db,
        track,
        decision=decision,
        source=DecisionSource.slack,
        actor=actor,
        rationale=f"Decision submitted from Slack interactive action `{decision.value}`.",
    )
    db.commit()
    db.refresh(track)

    assigned_workspace_id = None
    assigned_workspace_title = None
    assignment_error = None
    archive_note = None
    archived_workspace_title = None
    pending_workspace_id = (track.metadata_json or {}).get("pending_workspace_id")
    if decision == DecisionValue.approve and pending_workspace_id:
        try:
            playlist = await assign_track_to_playlist(
                db,
                services,
                track=track,
                playlist_id=pending_workspace_id,
                actor=actor,
            )
            assigned_workspace_id = playlist.id
            assigned_workspace_title = playlist.title
        except ValueError as exc:
            assignment_error = str(exc)
            await maybe_build_auto_playlist(db, services, trigger=f"slack-decision:{track.id}")
    elif decision == DecisionValue.reject:
        archived = maybe_archive_rejected_single_workspace(
            db,
            playlist_id=pending_workspace_id,
            actor=actor,
        )
        if archived:
            archived_workspace_title = archived.title
            archive_note = "All single release candidates were rejected; workspace archived."
    else:
        await maybe_build_auto_playlist(db, services, trigger=f"slack-decision:{track.id}")

    response_text = f"Recorded `{decision.value}` for track `{track.title}`."
    if assigned_workspace_title:
        response_text += f" Assigned to workspace `{assigned_workspace_title}`."
    if archive_note:
        response_text += f" Workspace `{archived_workspace_title}` archived. {archive_note}"
    elif assignment_error:
        response_text += f" Workspace assignment failed: {assignment_error}."

    slack_update = await sync_slack_review_decision(
        db,
        services,
        track,
        decision=decision,
        actor=actor,
        workspace_title=assigned_workspace_title,
        note=response_text,
    )

    return JSONResponse(
        {
            "text": response_text,
            "track_status": track.status.value,
            "assigned_workspace_id": assigned_workspace_id,
            "assignment_error": assignment_error,
            "slack_update_ok": bool(slack_update and slack_update.get("ok")),
        }
    )


@router.post("/app-home/publish/{user_id}")
async def publish_app_home_for_user(
    user_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> JSONResponse:
    services = get_services(request)
    token = _bot_token_for_team(services, db)
    result = await services.slack.publish_app_home(
        user_id=user_id,
        stats=_status_counts(db),
        token=token,
    )
    return JSONResponse(result)
