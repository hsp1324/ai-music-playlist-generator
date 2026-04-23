from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.approval import Approval
from app.models.enums import DecisionSource, DecisionValue, TrackStatus
from app.models.track import Track


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


DECISION_STATUS_MAP = {
    DecisionValue.approve: TrackStatus.approved,
    DecisionValue.reject: TrackStatus.rejected,
    DecisionValue.hold: TrackStatus.held,
    DecisionValue.regenerate: TrackStatus.held,
}


def apply_track_decision(
    db: Session,
    track: Track,
    *,
    decision: DecisionValue,
    source: DecisionSource,
    actor: str,
    rationale: str | None = None,
    confidence: float | None = None,
) -> Approval:
    approval = Approval(
        track_id=track.id,
        decision=decision,
        source=source,
        actor=actor,
        rationale=rationale,
        confidence=confidence,
    )
    track.status = DECISION_STATUS_MAP[decision]
    track.reviewed_at = utcnow()

    db.add(approval)
    db.add(track)
    db.flush()
    db.refresh(track)
    return approval
