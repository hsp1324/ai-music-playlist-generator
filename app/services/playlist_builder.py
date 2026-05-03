import subprocess
import time
from dataclasses import dataclass
from math import ceil
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
DEFAULT_LOOP_VIDEO_SOURCE_SECONDS = 8
DEFAULT_LOOP_VIDEO_TRANSITION_SECONDS = 2


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

        probed_durations: list[float] = []
        unreadable: list[str] = []
        for track, audio_path in zip(tracks, audio_paths, strict=True):
            duration = self._probe_media_duration(audio_path)
            if duration <= 0:
                unreadable.append(f"{track.title} ({audio_path})")
            else:
                probed_durations.append(duration)
        if unreadable:
            raise ValueError("Playlist contains unreadable audio files: " + "; ".join(unreadable))

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

        expected_duration = sum(probed_durations)
        actual_duration = self._probe_media_duration(output_path)
        if actual_duration <= 0:
            raise RuntimeError(f"Rendered playlist audio is unreadable: {output_path}")
        tolerance_seconds = max(2.0, expected_duration * 0.01)
        if actual_duration + tolerance_seconds < expected_duration:
            raise RuntimeError(
                "Rendered playlist audio is shorter than the source tracks: "
                f"{actual_duration:.1f}s rendered vs {expected_duration:.1f}s expected."
            )

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
        concat_list_path: Path | None = None
        command: list[str]
        if smooth_loop:
            source_seconds = self._resolve_loop_source_seconds(clip_path)
            transition_seconds = self._resolve_loop_transition_seconds(source_seconds)
            loop_unit_seconds = source_seconds - transition_seconds
            intro_path, loop_unit_path = self._build_smooth_loop_assets(
                clip_path,
                output_path,
                source_seconds=source_seconds,
                transition_seconds=transition_seconds,
            )
            concat_list_path = self._write_loop_concat_list(
                intro_path,
                loop_unit_path,
                output_path,
                loop_unit_seconds=loop_unit_seconds,
                total_duration_seconds=total_duration_seconds,
                audio_path=audio_path,
            )
            command = [
                self.settings.ffmpeg_binary,
                "-y",
                "-hide_banner",
                "-nostats",
                "-progress",
                "pipe:1",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_list_path),
                "-i",
                str(audio_path),
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-c:v",
                "copy",
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
            if concat_list_path:
                concat_list_path.unlink(missing_ok=True)
            if smooth_loop:
                intro_path.unlink(missing_ok=True)
        return output_path

    def _write_loop_concat_list(
        self,
        intro_path: Path,
        loop_unit_path: Path,
        output_path: Path,
        *,
        loop_unit_seconds: float,
        total_duration_seconds: int | float | None,
        audio_path: Path,
    ) -> Path:
        total_duration = float(total_duration_seconds or 0)
        if total_duration <= 0:
            total_duration = self._probe_media_duration(audio_path)
        if total_duration <= 0:
            total_duration = DEFAULT_LOOP_VIDEO_SOURCE_SECONDS

        loop_unit_duration = max(loop_unit_seconds, 0.1)
        intro_duration = loop_unit_duration
        repeat_count = max(1, ceil(max(total_duration - intro_duration, 0) / loop_unit_duration) + 1)
        list_path = output_path.with_name(f"{output_path.stem}-loop-concat.txt")

        def escape_concat_path(path: Path) -> str:
            return str(path).replace("'", "'\\''")

        lines = [f"file '{escape_concat_path(intro_path)}'"]
        lines.extend(f"file '{escape_concat_path(loop_unit_path)}'" for _ in range(repeat_count))
        list_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return list_path

    def _probe_media_duration(self, media_path: Path) -> float:
        ffprobe_binary = str(Path(self.settings.ffmpeg_binary).with_name("ffprobe"))
        if not Path(ffprobe_binary).exists():
            ffprobe_binary = "ffprobe"
        try:
            result = subprocess.run(
                [
                    ffprobe_binary,
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    str(media_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            return max(float(result.stdout.strip()), 0.0)
        except (OSError, subprocess.CalledProcessError, ValueError):
            return 0.0

    def _resolve_loop_source_seconds(self, clip_path: Path) -> float:
        probed_duration = self._probe_media_duration(clip_path)
        if probed_duration > 0:
            return max(probed_duration, 1.0)
        configured_duration = float(
            getattr(self.settings, "dreamina_video_duration_seconds", DEFAULT_LOOP_VIDEO_SOURCE_SECONDS)
            or DEFAULT_LOOP_VIDEO_SOURCE_SECONDS
        )
        return max(configured_duration, 1.0)

    def _resolve_loop_transition_seconds(self, source_seconds: float) -> float:
        configured_transition = float(
            getattr(self.settings, "crossfade_seconds", DEFAULT_LOOP_VIDEO_TRANSITION_SECONDS)
            or DEFAULT_LOOP_VIDEO_TRANSITION_SECONDS
        )
        transition_seconds = max(configured_transition, 0.1)
        return min(transition_seconds, max(source_seconds / 3, 0.1))

    def _format_seconds(self, seconds: float) -> str:
        if float(seconds).is_integer():
            return str(int(seconds))
        return f"{seconds:.3f}".rstrip("0").rstrip(".")

    def _build_smooth_loop_assets(
        self,
        clip_path: Path,
        output_path: Path,
        *,
        source_seconds: float,
        transition_seconds: float,
    ) -> tuple[Path, Path]:
        intro_path = output_path.with_name(f"{output_path.stem}-loop-intro.mp4")
        loop_unit_path = output_path.with_name(f"{output_path.stem}-loop-unit.mp4")
        normalized_path = output_path.with_name(f"{output_path.stem}-loop-normalized.mp4")
        transition_path = output_path.with_name(f"{output_path.stem}-loop-transition.mp4")
        body_path = output_path.with_name(f"{output_path.stem}-loop-body.mp4")
        transition_offset = source_seconds - transition_seconds
        body_duration = source_seconds - (transition_seconds * 2)
        source_arg = self._format_seconds(source_seconds)
        transition_arg = self._format_seconds(transition_seconds)
        transition_offset_arg = self._format_seconds(transition_offset)
        body_duration_arg = self._format_seconds(body_duration)
        normalized_filter = (
            f"{YOUTUBE_LOOP_VIDEO_FILTER},"
            f"tpad=stop_mode=clone:stop_duration={source_arg},"
            f"trim=duration={source_arg},"
            "setpts=PTS-STARTPTS"
        )
        transition_filter = (
            "[0:v]setpts=PTS-STARTPTS[tail];"
            "[1:v]setpts=PTS-STARTPTS[head];"
            "[tail][head]"
            f"xfade=transition=fade:duration={transition_arg}:offset=0"
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
                    transition_offset_arg,
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
                    transition_offset_arg,
                    "-t",
                    transition_arg,
                    "-i",
                    str(normalized_path),
                    "-ss",
                    "0",
                    "-t",
                    transition_arg,
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
                    transition_arg,
                    "-t",
                    body_duration_arg,
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
