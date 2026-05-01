from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import TrackStatus


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Track(Base):
    __tablename__ = "tracks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    source_track_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    prompt: Mapped[str] = mapped_column(Text)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    audio_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    preview_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    status: Mapped[TrackStatus] = mapped_column(
        Enum(TrackStatus),
        default=TrackStatus.pending_review,
        index=True,
    )
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    slack_channel_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    slack_message_ts: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    approvals = relationship("Approval", back_populates="track", cascade="all, delete-orphan")
    playlist_items = relationship("PlaylistItem", back_populates="track")
    jobs = relationship("Job", back_populates="track")

    @property
    def lyrics(self) -> str:
        return str((self.metadata_json or {}).get("lyrics") or "")
