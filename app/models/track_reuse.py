from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TrackReuseEvent(Base):
    __tablename__ = "track_reuse_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    track_id: Mapped[str] = mapped_column(ForeignKey("tracks.id"), index=True)
    target_playlist_id: Mapped[str] = mapped_column(ForeignKey("playlists.id"), index=True)
    source_playlist_id: Mapped[str | None] = mapped_column(ForeignKey("playlists.id"), nullable=True, index=True)
    actor: Mapped[str] = mapped_column(String(255), default="unknown")
    source: Mapped[str] = mapped_column(String(64), default="youtube_back_half")
    reused_duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    source_start_seconds: Mapped[int] = mapped_column(Integer, default=0)
    reuse_count_before: Mapped[int] = mapped_column(Integer, default=0)
    reused_seconds_before: Mapped[int] = mapped_column(Integer, default=0)
    selection_rank: Mapped[int] = mapped_column(Integer, default=0)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    track = relationship("Track", back_populates="reuse_events")
    target_playlist = relationship("Playlist", foreign_keys=[target_playlist_id])
    source_playlist = relationship("Playlist", foreign_keys=[source_playlist_id])
