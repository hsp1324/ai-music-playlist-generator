from datetime import datetime
from typing import Any, Literal

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
    lyrics: str | None = None
    style: str | None = None
    exclude_style: str | None = None
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


class TrackRatingRequest(BaseModel):
    rating: Literal["like", "dislike", "none"] = "none"
    actor: str = "web-ui"


class TrackRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_track_id: str | None
    title: str
    prompt: str
    lyrics: str = ""
    style: str = ""
    exclude_style: str = ""
    duration_seconds: int
    audio_path: str | None
    preview_url: str | None
    status: TrackStatus
    metadata_json: dict[str, Any]
    user_rating: str = ""
    slack_channel_id: str | None
    slack_message_ts: str | None
    created_at: datetime
    updated_at: datetime
    reviewed_at: datetime | None
    approvals: list[ApprovalRead] = []


class TrackReuseEventRead(BaseModel):
    id: str
    track_id: str
    track_title: str
    target_playlist_id: str
    target_playlist_title: str
    source_playlist_id: str | None = None
    source_playlist_title: str | None = None
    source_youtube_video_id: str | None = None
    actor: str
    source: str
    reused_duration_seconds: int
    source_start_seconds: int
    reuse_count_before: int
    reused_seconds_before: int
    selection_rank: int
    metadata_json: dict[str, Any]
    created_at: datetime


class TrackReuseSummaryRead(BaseModel):
    track_id: str
    title: str
    duration_seconds: int
    audio_path: str | None = None
    reuse_count: int = 0
    reused_seconds: int = 0
    event_count: int = 0
    last_reused_at: str | None = None
    last_reused_in_playlist_id: str | None = None
    last_reused_by: str | None = None
