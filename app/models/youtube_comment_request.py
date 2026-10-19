from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class YouTubeCommentRequest(Base):
    __tablename__ = "youtube_comment_requests"
    __table_args__ = (
        UniqueConstraint(
            "youtube_channel_id",
            "comment_id",
            name="uq_youtube_comment_requests_channel_comment",
        ),
        UniqueConstraint(
            "youtube_channel_id",
            "queue_rank",
            name="uq_youtube_comment_requests_channel_queue_rank",
        ),
        Index(
            "ix_youtube_comment_requests_active_queue",
            "channel_title",
            "status",
            "queue_rank",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    channel_title: Mapped[str] = mapped_column(String(255), index=True)
    youtube_channel_id: Mapped[str] = mapped_column(String(255), index=True)
    source_video_id: Mapped[str] = mapped_column(String(255), index=True)
    comment_id: Mapped[str] = mapped_column(String(255), index=True)
    requester_display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    requester_channel_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    requested_genres_json: Mapped[list] = mapped_column(JSON, default=list)
    requested_mood: Mapped[str | None] = mapped_column(String(255), nullable=True)
    requested_duration_seconds: Mapped[int] = mapped_column(Integer, default=3600)
    request_summary: Mapped[str] = mapped_column(String(500))
    normalized_prompt: Mapped[str] = mapped_column(Text)
    source_text: Mapped[str] = mapped_column(Text)
    queue_rank: Mapped[int] = mapped_column(Integer, index=True)
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    claim_owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    claim_run_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    claim_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    available_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    defer_count: Mapped[int] = mapped_column(Integer, default=0)
    deferred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    defer_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    release_id: Mapped[str | None] = mapped_column(
        ForeignKey("playlists.id"), nullable=True, unique=True, index=True
    )
    provenance_json: Mapped[dict] = mapped_column(JSON, default=dict)
    operation_results_json: Mapped[dict] = mapped_column(JSON, default=dict)
    completion_idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    defer_idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    schedule_plan_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    schedule_plan_status: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    schedule_plan_json: Mapped[dict] = mapped_column(JSON, default=dict)
    scheduled_publish_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
