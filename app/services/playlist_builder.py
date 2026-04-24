import subprocess
from dataclasses import dataclass
from mimetypes import guess_type
from pathlib import Path
from tempfile import NamedTemporaryFile

from app.config import Settings
from app.models.track import Track


@dataclass
class PlaylistPlan:
    track_ids: list[str]
    estimated_duration_seconds: int
    shortage_seconds: int


class FFMpegPlaylistBuilder:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def plan_playlist(self, tracks: list[Track], target_duration_seconds: int) -> PlaylistPlan:
        selected_ids: list[str] = []
        total = 0

        for track in tracks:
            if total >= target_duration_seconds:
                break
            selected_ids.append(track.id)
            total += max(track.duration_seconds, 0)

        shortage = max(target_duration_seconds - total, 0)
        return PlaylistPlan(
            track_ids=selected_ids,
            estimated_duration_seconds=total,
            shortage_seconds=shortage,
        )

    def build_audio(self, tracks: list[Track], output_path: Path) -> Path:
        if not tracks:
            raise ValueError("No tracks were supplied for rendering.")

        audio_paths = [Path(track.audio_path) for track in tracks if track.audio_path]
        if len(audio_paths) != len(tracks):
            raise ValueError("All tracks must have a local audio_path before rendering.")

        missing = [str(path) for path in audio_paths if not path.exists()]
        if missing:
            raise FileNotFoundError(f"Some track files do not exist: {missing}")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False) as handle:
            for audio_path in audio_paths:
                escaped = str(audio_path.resolve()).replace("'", "'\\''")
                handle.write(f"file '{escaped}'\n")
            manifest_path = Path(handle.name)

        command = [
            self.settings.ffmpeg_binary,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(manifest_path),
            "-vn",
            "-c:a",
            "libmp3lame",
            "-q:a",
            "2",
            str(output_path),
        ]

        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
        finally:
            manifest_path.unlink(missing_ok=True)

        return output_path

    def build_video(self, audio_path: Path, cover_image_path: Path, output_path: Path) -> Path:
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file does not exist: {audio_path}")
        if not cover_image_path.exists():
            raise FileNotFoundError(f"Cover image does not exist: {cover_image_path}")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        image_mimetype = guess_type(str(cover_image_path))[0] or "image/png"

        command = [
            self.settings.ffmpeg_binary,
            "-y",
            "-loop",
            "1",
            "-framerate",
            "2",
            "-i",
            str(cover_image_path),
            "-i",
            str(audio_path),
            "-c:v",
            "libx264",
            "-tune",
            "stillimage",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            "-movflags",
            "+faststart",
            "-metadata:s:v:0",
            f"mimetype={image_mimetype}",
            str(output_path),
        ]
        subprocess.run(command, check=True, capture_output=True, text=True)
        return output_path

    def build_looped_video(self, clip_path: Path, audio_path: Path, output_path: Path) -> Path:
        if not clip_path.exists():
            raise FileNotFoundError(f"Loop clip does not exist: {clip_path}")
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file does not exist: {audio_path}")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        command = [
            self.settings.ffmpeg_binary,
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            str(clip_path),
            "-i",
            str(audio_path),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
        subprocess.run(command, check=True, capture_output=True, text=True)
        return output_path
