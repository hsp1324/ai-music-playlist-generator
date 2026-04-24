from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import DecisionSource, DecisionValue, TrackStatus


class ApprovalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    decision: DecisionValue
    source: DecisionSource
    actor: str
    rationale: str | None
    confidence: float | None
    created_at: datetime


class TrackCreateRequest(BaseModel):
    title: str
    prompt: str
    duration_seconds: int = Field(default=0, ge=0)
    audio_path: str | None = None
    preview_url: str | None = None
    source_track_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TrackDecisionRequest(BaseModel):
    decision: DecisionValue
    source: DecisionSource = DecisionSource.human
    actor: str = "unknown"
    rationale: str | None = None
    confidence: float | None = None
    playlist_id: str | None = None


class TrackReturnToReviewRequest(BaseModel):
    playlist_id: str
    actor: str = "unknown"
    rationale: str | None = None


class TrackRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_track_id: str | None
    title: str
    prompt: str
    duration_seconds: int
    audio_path: str | None
    preview_url: str | None
    status: TrackStatus
    metadata_json: dict[str, Any]
    slack_channel_id: str | None
    slack_message_ts: str | None
    created_at: datetime
    updated_at: datetime
    reviewed_at: datetime | None
    approvals: list[ApprovalRead] = []
