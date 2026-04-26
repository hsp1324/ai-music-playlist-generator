from sqlalchemy.orm import Session
from pathlib import Path

from app.models.enums import DecisionSource, TrackStatus
from app.models.track import Track
from app.services.slack_service import SlackPostResult
from app.services.registry import ServiceRegistry
from app.workflows.approvals import apply_track_decision
from app.workflows.playlist_automation import maybe_build_auto_playlist


def _has_uploadable_local_audio(track: Track) -> bool:
    return bool(
        track.audio_path
        and not track.audio_path.startswith(("http://", "https://"))
        and Path(track.audio_path).exists()
    )


async def post_track_review_to_slack(
    db: Session,
    services: ServiceRegistry,
    track: Track,
) -> SlackPostResult:
    installation = services.slack_installations.get_active_installation(db)
    token = installation.bot_token if installation else services.settings.slack_bot_token
    channel = services.settings.slack_review_channel_id

    if token and channel and _has_uploadable_local_audio(track):
        post_result = await services.slack.post_review_message_with_local_audio(track, token=token, channel=channel)
        if not post_result.ok:
            post_result = await services.slack.post_review_message(track, token=token, channel=channel)
    else:
        post_result = await services.slack.post_review_message(track, token=token, channel=channel)

    if post_result.ok:
        track.slack_channel_id = post_result.channel
        track.slack_message_ts = post_result.ts
        db.add(track)
        db.commit()
        db.refresh(track)

    return post_result


async def dispatch_track_review(
    db: Session,
    services: ServiceRegistry,
    track: Track,
) -> Track:
    if services.settings.auto_approval_mode in {"hybrid", "agent"}:
        decision = services.decision_engine.review_track(track)
        apply_track_decision(
            db,
            track,
            decision=decision.decision,
            source=DecisionSource.agent,
            actor=decision.actor,
            rationale=decision.rationale,
            confidence=decision.confidence,
        )
        db.commit()
        db.refresh(track)

    needs_human_followup = (
        services.settings.auto_approval_mode == "human"
        or track.status == TrackStatus.held
        or services.settings.auto_approval_mode == "hybrid"
    )
    if needs_human_followup:
        await post_track_review_to_slack(db, services, track)

    await maybe_build_auto_playlist(db, services, trigger=f"dispatch-review:{track.id}")
    return track
