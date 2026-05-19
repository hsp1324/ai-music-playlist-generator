from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import PlaylistStatus


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Playlist(Base):
    __tablename__ = "playlists"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    title: Mapped[str] = mapped_column(String(255))
    status: Mapped[PlaylistStatus] = mapped_column(Enum(PlaylistStatus), default=PlaylistStatus.draft)
    target_duration_seconds: Mapped[int] = mapped_column(Integer, default=3600)
    actual_duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    output_audio_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    output_video_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    youtube_video_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
    )

    items = relationship("PlaylistItem", back_populates="playlist", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="playlist")


class PlaylistItem(Base):
    __tablename__ = "playlist_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    playlist_id: Mapped[str] = mapped_column(ForeignKey("playlists.id"), index=True)
    track_id: Mapped[str] = mapped_column(ForeignKey("tracks.id"), index=True)
    order_index: Mapped[int] = mapped_column(Integer)
    included_duration_seconds: Mapped[int] = mapped_column(Integer, default=0)

    playlist = relationship("Playlist", back_populates="items")
    track = relationship("Track", back_populates="playlist_items")
