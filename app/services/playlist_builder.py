import subprocess
import time
from dataclasses import dataclass
from mimetypes import guess_type
from pathlib import Path
from selectors import EVENT_READ, DefaultSelector
from tempfile import NamedTemporaryFile
from typing import Any, Callable

from app.config import Settings
from app.models.track import Track


YOUTUBE_STILL_IMAGE_FILTER = (
    "scale=1280:720:force_original_aspect_ratio=decrease,"
    "pad=1280:720:(ow-iw)/2:(oh-ih)/2,"
    "setsar=1,"
    "format=yuv420p"
)
YOUTUBE_LOOP_VIDEO_FILTER = (
    "scale=1280:720:force_original_aspect_ratio=decrease,"
    "pad=1280:720:(ow-iw)/2:(oh-ih)/2,"
    "setsar=1,"
    "fps=30,"
    "format=yuv420p"
)
LOOP_VIDEO_SOURCE_SECONDS = 8
LOOP_VIDEO_TRANSITION_SECONDS = 2


@dataclass
class PlaylistPlan:
    track_ids: list[str]
    estimated_duration_seconds: int
    shortage_seconds: int


class FFMpegPlaylistBuilder:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _run_ffmpeg(self, command: list[str]) -> None:
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as exc:
            details = (exc.stderr or exc.stdout or "").strip()
            if details:
                lines = [line for line in details.splitlines() if line.strip()]
                details = "\n".join(lines[-8:])
            else:
                details = str(exc)
            raise RuntimeError(f"ffmpeg failed: {details}") from exc

    def _run_ffmpeg_with_progress(
        self,
        command: list[str],
        *,
        output_path: Path,
        total_duration_seconds: int | float | None,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        if process.stdout is None or process.stderr is None:
            raise RuntimeError("ffmpeg progress pipes could not be opened.")

        selector = DefaultSelector()
        selector.register(process.stdout, EVENT_READ, "stdout")
        selector.register(process.stderr, EVENT_READ, "stderr")

        started = time.monotonic()
        last_activity = started
        last_emit = 0.0
        last_output_size = output_path.stat().st_size if output_path.exists() else 0
        stderr_lines: list[str] = []
        progress_values: dict[str, str] = {}
        processed_seconds = 0.0
        total_seconds = float(total_duration_seconds or 0)
        killed_for_stall = False

        def parse_processed_seconds(key: str, value: str) -> float | None:
            if key in {"out_time_ms", "out_time_us"}:
                try:
                    return max(float(value) / 1_000_000, 0.0)
                except ValueError:
                    return None
            if key != "out_time":
                return None
            try:
                hours, minutes, seconds = value.split(":")
                return (int(hours) * 3600) + (int(minutes) * 60) + float(seconds)
            except ValueError:
                return None

        def parse_speed(value: str | None) -> float | None:
            if not value:
                return None
            try:
                return float(value.rstrip("x"))
            except ValueError:
                return None

        def emit(force: bool = False) -> None:
            nonlocal last_emit
            if progress_callback is None:
                return
            now = time.monotonic()
            if not force and now - last_emit < 2:
                return
            last_emit = now
            output_size = output_path.stat().st_size if output_path.exists() else 0
            speed = parse_speed(progress_values.get("speed"))
            ratio = min(processed_seconds / total_seconds, 1.0) if total_seconds > 0 else 0.0
            eta_seconds = None
            if ratio > 0 and ratio < 1:
                if speed and speed > 0:
                    eta_seconds = max((total_seconds - processed_seconds) / speed, 0.0)
                else:
                    elapsed = max(now - started, 0.1)
                    eta_seconds = max(elapsed * (1 - ratio) / ratio, 0.0)
            progress_callback(
                {
                    "stage": "video_render",
                    "progress_ratio": ratio,
                    "percent": round(ratio * 100, 1),
                    "processed_seconds": round(processed_seconds, 1),
                    "total_seconds": round(total_seconds, 1) if total_seconds else None,
                    "eta_seconds": round(eta_seconds, 1) if eta_seconds is not None else None,
                    "elapsed_seconds": round(now - started, 1),
                    "speed": speed,
                    "frame": progress_values.get("frame"),
                    "output_size_bytes": output_size,
                    "status": progress_values.get("progress") or "running",
                }
            )

        try:
            while True:
                if process.poll() is not None:
                    break

                if not selector.get_map():
                    time.sleep(0.2)
                    continue

                events = selector.select(timeout=1)
                if not events:
                    output_size = output_path.stat().st_size if output_path.exists() else 0
                    if output_size != last_output_size:
                        last_output_size = output_size
                        last_activity = time.monotonic()
                        emit()
                    elif time.monotonic() - last_activity > self.settings.ffmpeg_stall_timeout_seconds:
                        killed_for_stall = True
                        process.kill()
                        break
                    continue

                for key, _ in events:
                    stream = key.fileobj
                    line = stream.readline()
                    if line == "":
                        selector.unregister(stream)
                        continue
                    line = line.strip()
                    if not line:
                        continue
                    last_activity = time.monotonic()
                    if key.data == "stderr":
                        stderr_lines.append(line)
                        stderr_lines = stderr_lines[-12:]
                        continue

                    if "=" not in line:
                        continue
                    name, value = line.split("=", 1)
                    progress_values[name] = value
                    parsed_seconds = parse_processed_seconds(name, value)
                    if parsed_seconds is not None:
                        processed_seconds = max(processed_seconds, parsed_seconds)
                        emit()
                    elif name == "progress":
                        emit(force=value == "end")
        finally:
            selector.close()

        return_code = process.wait()
        if killed_for_stall:
            raise RuntimeError(
                "ffmpeg stalled without progress or output file growth for "
                f"{self.settings.ffmpeg_stall_timeout_seconds} seconds."
            )
        if return_code != 0:
            details = "\n".join(line for line in stderr_lines[-8:] if line.strip())
            raise RuntimeError(f"ffmpeg failed: {details or f'exit code {return_code}'}")

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
            self._run_ffmpeg(command)
        finally:
            manifest_path.unlink(missing_ok=True)

        return output_path

    def build_video(
        self,
        audio_path: Path,
        cover_image_path: Path,
        output_path: Path,
        *,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
        total_duration_seconds: int | float | None = None,
    ) -> Path:
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file does not exist: {audio_path}")
        if not cover_image_path.exists():
            raise FileNotFoundError(f"Cover image does not exist: {cover_image_path}")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        image_mimetype = guess_type(str(cover_image_path))[0] or "image/png"

        command = [
            self.settings.ffmpeg_binary,
            "-y",
            "-hide_banner",
            "-nostats",
            "-progress",
            "pipe:1",
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
            "-preset",
            "veryfast",
            "-tune",
            "stillimage",
            "-vf",
            YOUTUBE_STILL_IMAGE_FILTER,
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
        output_path.unlink(missing_ok=True)
        self._run_ffmpeg_with_progress(
            command,
            output_path=output_path,
            total_duration_seconds=total_duration_seconds,
            progress_callback=progress_callback,
        )
        return output_path

    def build_looped_video(
        self,
        clip_path: Path,
        audio_path: Path,
        output_path: Path,
        *,
        smooth_loop: bool = True,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
        total_duration_seconds: int | float | None = None,
    ) -> Path:
        if not clip_path.exists():
            raise FileNotFoundError(f"Loop clip does not exist: {clip_path}")
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file does not exist: {audio_path}")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        loop_source_path = clip_path
        loop_unit_path: Path | None = None
        command: list[str]
        if smooth_loop:
            intro_path, loop_unit_path = self._build_smooth_loop_assets(clip_path, output_path)
            loop_filter = (
                "[0:v]setpts=PTS-STARTPTS[intro];"
                "[1:v]fps=30,setpts=N/(30*TB)[loop];"
                "[intro][loop]concat=n=2:v=1:a=0,format=yuv420p[loopv]"
            )
            command = [
                self.settings.ffmpeg_binary,
                "-y",
                "-hide_banner",
                "-nostats",
                "-progress",
                "pipe:1",
                "-i",
                str(intro_path),
                "-stream_loop",
                "-1",
                "-i",
                str(loop_unit_path),
                "-i",
                str(audio_path),
                "-filter_complex",
                loop_filter,
                "-map",
                "[loopv]",
                "-map",
                "2:a:0",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
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
        else:
            command = [
                self.settings.ffmpeg_binary,
                "-y",
                "-hide_banner",
                "-nostats",
                "-progress",
                "pipe:1",
                "-stream_loop",
                "-1",
                "-i",
                str(loop_source_path),
                "-i",
                str(audio_path),
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
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
        output_path.unlink(missing_ok=True)
        try:
            self._run_ffmpeg_with_progress(
                command,
                output_path=output_path,
                total_duration_seconds=total_duration_seconds,
                progress_callback=progress_callback,
            )
        finally:
            if loop_unit_path:
                loop_unit_path.unlink(missing_ok=True)
            if smooth_loop:
                intro_path.unlink(missing_ok=True)
        return output_path

    def _build_smooth_loop_assets(self, clip_path: Path, output_path: Path) -> tuple[Path, Path]:
        intro_path = output_path.with_name(f"{output_path.stem}-loop-intro.mp4")
        loop_unit_path = output_path.with_name(f"{output_path.stem}-loop-unit.mp4")
        normalized_path = output_path.with_name(f"{output_path.stem}-loop-normalized.mp4")
        transition_path = output_path.with_name(f"{output_path.stem}-loop-transition.mp4")
        body_path = output_path.with_name(f"{output_path.stem}-loop-body.mp4")
        transition_offset = LOOP_VIDEO_SOURCE_SECONDS - LOOP_VIDEO_TRANSITION_SECONDS
        normalized_filter = (
            f"{YOUTUBE_LOOP_VIDEO_FILTER},"
            f"tpad=stop_mode=clone:stop_duration={LOOP_VIDEO_SOURCE_SECONDS},"
            f"trim=duration={LOOP_VIDEO_SOURCE_SECONDS},"
            "setpts=PTS-STARTPTS"
        )
        transition_filter = (
            "[0:v]setpts=PTS-STARTPTS[tail];"
            "[1:v]setpts=PTS-STARTPTS[head];"
            "[tail][head]"
            f"xfade=transition=fade:duration={LOOP_VIDEO_TRANSITION_SECONDS}:offset=0"
            ",format=yuv420p[transition]"
        )
        concat_filter = (
            "[0:v]setpts=PTS-STARTPTS[transition];"
            "[1:v]setpts=PTS-STARTPTS[body];"
            "[transition][body]concat=n=2:v=1:a=0,format=yuv420p[loopv]"
        )

        for path in (intro_path, loop_unit_path, normalized_path, transition_path, body_path):
            path.unlink(missing_ok=True)

        try:
            self._run_ffmpeg(
                [
                    self.settings.ffmpeg_binary,
                    "-y",
                    "-hide_banner",
                    "-nostats",
                    "-i",
                    str(clip_path),
                    "-vf",
                    normalized_filter,
                    "-an",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-pix_fmt",
                    "yuv420p",
                    "-movflags",
                    "+faststart",
                    str(normalized_path),
                ]
            )
            self._run_ffmpeg(
                [
                    self.settings.ffmpeg_binary,
                    "-y",
                    "-hide_banner",
                    "-nostats",
                    "-i",
                    str(normalized_path),
                    "-t",
                    str(transition_offset),
                    "-an",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-pix_fmt",
                    "yuv420p",
                    "-movflags",
                    "+faststart",
                    str(intro_path),
                ]
            )
            self._run_ffmpeg(
                [
                    self.settings.ffmpeg_binary,
                    "-y",
                    "-hide_banner",
                    "-nostats",
                    "-ss",
                    str(transition_offset),
                    "-t",
                    str(LOOP_VIDEO_TRANSITION_SECONDS),
                    "-i",
                    str(normalized_path),
                    "-ss",
                    "0",
                    "-t",
                    str(LOOP_VIDEO_TRANSITION_SECONDS),
                    "-i",
                    str(normalized_path),
                    "-filter_complex",
                    transition_filter,
                    "-map",
                    "[transition]",
                    "-an",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-pix_fmt",
                    "yuv420p",
                    "-movflags",
                    "+faststart",
                    str(transition_path),
                ]
            )
            self._run_ffmpeg(
                [
                    self.settings.ffmpeg_binary,
                    "-y",
                    "-hide_banner",
                    "-nostats",
                    "-ss",
                    str(LOOP_VIDEO_TRANSITION_SECONDS),
                    "-t",
                    str(transition_offset - LOOP_VIDEO_TRANSITION_SECONDS),
                    "-i",
                    str(normalized_path),
                    "-an",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-pix_fmt",
                    "yuv420p",
                    "-movflags",
                    "+faststart",
                    str(body_path),
                ]
            )
            self._run_ffmpeg(
                [
                    self.settings.ffmpeg_binary,
                    "-y",
                    "-hide_banner",
                    "-nostats",
                    "-i",
                    str(transition_path),
                    "-i",
                    str(body_path),
                    "-filter_complex",
                    concat_filter,
                    "-map",
                    "[loopv]",
                    "-an",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-pix_fmt",
                    "yuv420p",
                    "-movflags",
                    "+faststart",
                    str(loop_unit_path),
                ]
            )
        except Exception:
            intro_path.unlink(missing_ok=True)
            loop_unit_path.unlink(missing_ok=True)
            raise
        finally:
            normalized_path.unlink(missing_ok=True)
            transition_path.unlink(missing_ok=True)
            body_path.unlink(missing_ok=True)

        return intro_path, loop_unit_path
