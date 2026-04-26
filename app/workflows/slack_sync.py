from sqlalchemy.orm import Session

from app.models.enums import DecisionValue
from app.models.track import Track
from app.services.registry import ServiceRegistry


async def sync_slack_review_decision(
    db: Session,
    services: ServiceRegistry,
    track: Track,
    *,
    decision: DecisionValue,
    actor: str,
    workspace_title: str | None = None,
    note: str | None = None,
) -> dict | None:
    if not track.slack_channel_id or not track.slack_message_ts:
        return None

    installation = services.slack_installations.get_active_installation(db)
    token = installation.bot_token if installation else services.settings.slack_bot_token
    result = await services.slack.update_review_message(
        track,
        decision=decision.value,
        actor=actor,
        token=token,
        channel=track.slack_channel_id,
        ts=track.slack_message_ts,
        workspace_title=workspace_title,
        note=note,
    )
    return result.raw or {"ok": result.ok}
