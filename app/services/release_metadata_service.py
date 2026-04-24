from __future__ import annotations

from dataclasses import dataclass

from app.config import Settings
from app.models.playlist import Playlist
from app.models.track import Track


@dataclass
class YouTubeMetadata:
    title: str
    description: str
    tags: list[str]


class ReleaseMetadataService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def build_youtube_metadata(self, playlist: Playlist, tracks: list[Track]) -> YouTubeMetadata:
        meta = playlist.metadata_json or {}
        mode = str(meta.get("workspace_mode") or "playlist")
        title = playlist.title.strip()
        description_summary = meta.get("description") or "AI-generated music release."

        tags = sorted(
            {
                tag.strip().lower()
                for track in tracks
                for tag in str((track.metadata_json or {}).get("tags") or "").split(",")
                if tag.strip()
            }
        )

        if mode == "single_track_video" and tracks:
            track = tracks[0]
            title = f"{track.title} | {self.settings.youtube_title_suffix}".strip(" |")
            description = "\n".join(
                [
                    f"{track.title}",
                    "",
                    description_summary,
                    "",
                    f"Prompt: {track.prompt or 'N/A'}",
                    f"Tags: {', '.join(tags) if tags else 'ai music, visualizer'}",
                    "Visuals: Cover art + Dreamina-generated motion loop.",
                    "",
                    "Generated with an automated AI music release workflow.",
                    self.settings.youtube_default_hashtags,
                ]
            )
            return YouTubeMetadata(
                title=title[:100],
                description=description.strip(),
                tags=(tags or ["ai music", "visualizer", "electronic"])[:15],
            )

        track_titles = ", ".join(track.title for track in tracks[:6]) if tracks else playlist.title
        description = "\n".join(
            [
                playlist.title,
                "",
                description_summary,
                "",
                f"Featured tracks: {track_titles}",
                f"Tags: {', '.join(tags) if tags else 'ai music, playlist'}",
                "",
                "Generated with an automated AI music release workflow.",
                self.settings.youtube_default_hashtags,
            ]
        )
        return YouTubeMetadata(
            title=playlist.title[:100],
            description=description.strip(),
            tags=(tags or ["ai music", "playlist", "background music"])[:15],
        )
