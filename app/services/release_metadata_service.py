from __future__ import annotations

from dataclasses import dataclass

from app.config import Settings
from app.models.playlist import Playlist
from app.models.track import Track
from app.utils.track_titles import clean_track_display_title, display_track_titles


@dataclass
class YouTubeMetadata:
    title: str
    description: str
    tags: list[str]
    provider: str = "template"
    error: str | None = None


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
            release_title = playlist.title.strip() if len(tracks) > 1 else track.title
            title = f"{release_title} | {self.settings.youtube_title_suffix}".strip(" |")
            prompt_lines = [track.prompt for track in tracks if track.prompt]
            prompt_summary = " / ".join(prompt_lines[:2]) if prompt_lines else "N/A"
            description = "\n".join(
                [
                    release_title,
                    "",
                    description_summary,
                    "",
                    f"Prompt: {prompt_summary}",
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

        if self._is_cafe_piano_release(playlist, tracks, tags):
            return self._build_cafe_piano_metadata(playlist, tracks)

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

    def _build_cafe_piano_metadata(self, playlist: Playlist, tracks: list[Track]) -> YouTubeMetadata:
        title = "조용한 카페 피아노 솔로 1시간 | 공부, 작업, 휴식할 때 듣는 잔잔한 플레이리스트"
        timestamps = self._timestamp_lines(tracks)
        description = "\n".join(
            [
                "카페 한쪽에서 조용히 흐르는 듯한 잔잔한 솔로 피아노 플레이리스트입니다.",
                "",
                "부드러운 건반 소리와 따뜻한 분위기의 피아노 곡들을 모아,",
                "공부할 때, 작업할 때, 책을 읽을 때, 혹은 잠시 쉬고 싶을 때 편하게 들을 수 있도록 구성했습니다.",
                "",
                "Recommended for",
                "공부 / 작업 / 독서 / 휴식 / 카페 분위기 / 조용한 배경음악",
                "",
                *timestamps,
                "",
                "#Piano #CafePiano #StudyMusic #WorkMusic #RelaxingMusic #SoloPiano",
            ]
        )
        return YouTubeMetadata(
            title=title[:100],
            description=description.strip(),
            tags=["Piano", "CafePiano", "StudyMusic", "WorkMusic", "RelaxingMusic", "SoloPiano"],
        )

    def _is_cafe_piano_release(self, playlist: Playlist, tracks: list[Track], tags: list[str]) -> bool:
        haystack = " ".join(
            [
                playlist.title,
                str((playlist.metadata_json or {}).get("description") or ""),
                " ".join(tags),
                " ".join(track.title for track in tracks),
            ]
        ).lower()
        return ("cafe" in haystack or "카페" in haystack) and ("piano" in haystack or "피아노" in haystack)

    def _timestamp_lines(self, tracks: list[Track]) -> list[str]:
        offset = 0
        lines = []
        display_titles = self._display_track_titles(tracks)
        for track, display_title in zip(tracks, display_titles):
            lines.append(f"{self._format_timestamp(offset)} {display_title}")
            offset += max(int(track.duration_seconds or 0), 0)
        return lines

    def _display_track_titles(self, tracks: list[Track]) -> list[str]:
        return display_track_titles([{"title": track.title} for track in tracks])

    def _clean_track_display_title(self, title: str) -> str:
        return clean_track_display_title(title)

    def _format_timestamp(self, seconds: int) -> str:
        seconds = max(seconds, 0)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        remainder = seconds % 60
        if hours:
            return f"{hours}:{minutes:02d}:{remainder:02d}"
        return f"{minutes:02d}:{remainder:02d}"
