from sqlalchemy.orm import Session
from pathlib import Path

from app.models.enums import DecisionSource, TrackStatus
from app.models.track import Track
from app.services.registry import ServiceRegistry
from app.workflows.approvals import apply_track_decision
from app.workflows.playlist_automation import maybe_build_auto_playlist


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
        installation = services.slack_installations.get_active_installation(db)
        token = installation.bot_token if installation else services.settings.slack_bot_token
        channel = services.settings.slack_review_channel_id
        post_result = await services.slack.post_review_message(track, token=token, channel=channel)
        if post_result.ok:
            track.slack_channel_id = post_result.channel
            track.slack_message_ts = post_result.ts
            db.add(track)
            db.commit()
            db.refresh(track)
            if (
                token
                and track.audio_path
                and not track.audio_path.startswith(("http://", "https://"))
                and Path(track.audio_path).exists()
            ):
                await services.slack.upload_local_audio_file(
                    file_path=track.audio_path,
                    title=track.title,
                    token=token,
                    channel=post_result.channel or channel,
                    thread_ts=post_result.ts,
                    initial_comment=f"Audio preview for {track.title}",
                )

    await maybe_build_auto_playlist(db, services, trigger=f"dispatch-review:{track.id}")
    return track
