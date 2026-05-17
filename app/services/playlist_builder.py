import colorsys
import math
import subprocess
import time
from array import array
from io import BytesIO
from dataclasses import dataclass
from math import ceil
from mimetypes import guess_type
from pathlib import Path
from selectors import EVENT_READ, DefaultSelector
from tempfile import NamedTemporaryFile
from typing import Any, Callable

from PIL import Image, ImageChops, ImageDraw, ImageOps

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
DEFAULT_LOOP_VIDEO_SOURCE_SECONDS = 6
DEFAULT_LOOP_VIDEO_TRANSITION_SECONDS = 1.0
SPECTRUM_OVERLAY_WIDTH = 560
SPECTRUM_OVERLAY_HEIGHT = 90
SPECTRUM_OVERLAY_FPS = 30
SPECTRUM_OVERLAY_BARS = 28
SPECTRUM_ANALYSIS_SAMPLE_RATE = 4000
SPECTRUM_EDGE_FADE_MIN_PX = 64
SPECTRUM_EDGE_FADE_RATIO = 0.16
SPECTRUM_DOT_COUNT = 44
SPECTRUM_DOT_BASE_RADIUS = 2
SPECTRUM_DOT_SIGNAL_RADIUS = 4.0
SPECTRUM_DOT_PUNCH_RADIUS = 3.0
RADIAL_SPECTRUM_OVERLAY_WIDTH = 320
RADIAL_SPECTRUM_OVERLAY_HEIGHT = 320


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
        stage: str = "video_render",
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
                    "stage": stage,
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
        except BaseException:
            if process.poll() is None:
                process.kill()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    pass
            raise
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

    def build_audio(
        self,
        tracks: list[Track],
        output_path: Path,
        *,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
        total_duration_seconds: int | float | None = None,
    ) -> Path:
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
            "-hide_banner",
            "-nostats",
            "-progress",
            "pipe:1",
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
            output_path.unlink(missing_ok=True)
            self._run_ffmpeg_with_progress(
                command,
                output_path=output_path,
                total_duration_seconds=total_duration_seconds or sum(probed_durations),
                progress_callback=progress_callback,
                stage="audio_render",
            )
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
        spectrum_overlay_style: str | None = None,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
        total_duration_seconds: int | float | None = None,
    ) -> Path:
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file does not exist: {audio_path}")
        if not cover_image_path.exists():
            raise FileNotFoundError(f"Cover image does not exist: {cover_image_path}")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        image_mimetype = guess_type(str(cover_image_path))[0] or "image/png"
        apply_spectrum_overlay = self._spectrum_overlay_enabled(spectrum_overlay_style)
        render_output_path = self._base_render_path(output_path) if apply_spectrum_overlay else output_path

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
            str(render_output_path),
        ]
        output_path.unlink(missing_ok=True)
        render_output_path.unlink(missing_ok=True)
        try:
            self._run_ffmpeg_with_progress(
                command,
                output_path=render_output_path,
                total_duration_seconds=total_duration_seconds,
                progress_callback=progress_callback,
            )
            if apply_spectrum_overlay and render_output_path != output_path:
                self._apply_spectrum_overlay(
                    render_output_path,
                    audio_path,
                    cover_image_path,
                    output_path,
                    spectrum_overlay_style=spectrum_overlay_style,
                    total_duration_seconds=total_duration_seconds,
                    progress_callback=progress_callback,
                )
        finally:
            if render_output_path != output_path:
                render_output_path.unlink(missing_ok=True)
        return output_path

    def build_looped_video(
        self,
        clip_path: Path,
        audio_path: Path,
        output_path: Path,
        *,
        smooth_loop: bool = True,
        spectrum_overlay_style: str | None = None,
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
        apply_spectrum_overlay = self._spectrum_overlay_enabled(spectrum_overlay_style)
        render_output_path = self._base_render_path(output_path) if apply_spectrum_overlay else output_path
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
                str(render_output_path),
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
                str(render_output_path),
            ]
        output_path.unlink(missing_ok=True)
        render_output_path.unlink(missing_ok=True)
        try:
            self._run_ffmpeg_with_progress(
                command,
                output_path=render_output_path,
                total_duration_seconds=total_duration_seconds,
                progress_callback=progress_callback,
            )
            if apply_spectrum_overlay and render_output_path != output_path:
                self._apply_spectrum_overlay(
                    render_output_path,
                    audio_path,
                    clip_path,
                    output_path,
                    spectrum_overlay_style=spectrum_overlay_style,
                    total_duration_seconds=total_duration_seconds,
                    progress_callback=progress_callback,
                )
        finally:
            if render_output_path != output_path:
                render_output_path.unlink(missing_ok=True)
            if loop_unit_path:
                loop_unit_path.unlink(missing_ok=True)
            if concat_list_path:
                concat_list_path.unlink(missing_ok=True)
            if smooth_loop:
                intro_path.unlink(missing_ok=True)
        return output_path

    def _spectrum_overlay_enabled(self, style: str | None = None) -> bool:
        if not bool(getattr(self.settings, "video_spectrum_overlay_enabled", True)):
            return False
        return self._normalize_spectrum_overlay_style(style) != "none"

    def _base_render_path(self, output_path: Path) -> Path:
        return output_path.with_name(f"{output_path.stem}-base-render{output_path.suffix}")

    def _normalize_spectrum_overlay_style(self, style: str) -> str:
        normalized = str(style or "bars").strip().lower().replace("_", "-")
        aliases = {
            "bar": "bars",
            "spectrum": "bars",
            "spectrum-bars": "bars",
            "wave": "multiwave",
            "waveform": "multiwave",
            "waves": "multiwave",
            "multi-wave": "multiwave",
            "thin-wave": "thinwave",
            "clean-wave": "thinwave",
            "dot": "dots",
            "particles": "dots",
            "mirror": "mirror-bars",
            "mirrorbars": "mirror-bars",
            "mirrored-bars": "mirror-bars",
            "circle": "radial",
            "ring": "radial",
            "radial-bars": "radial",
            "pulse-line": "pulse",
            "pulses": "pulse",
            "off": "none",
            "disabled": "none",
            "disable": "none",
            "no": "none",
            "no-spectrum": "none",
            "fast": "none",
        }
        normalized = aliases.get(normalized, normalized)
        if normalized not in {"bars", "multiwave", "thinwave", "dots", "mirror-bars", "radial", "pulse", "none"}:
            return "bars"
        return normalized

    def _apply_spectrum_overlay(
        self,
        base_video_path: Path,
        audio_path: Path,
        visual_source_path: Path,
        output_path: Path,
        *,
        spectrum_overlay_style: str | None,
        total_duration_seconds: int | float | None,
        progress_callback: Callable[[dict[str, Any]], None] | None,
    ) -> None:
        style = self._normalize_spectrum_overlay_style(
            spectrum_overlay_style or str(getattr(self.settings, "video_spectrum_overlay_style", "bars") or "bars")
        )

        output_path.unlink(missing_ok=True)
        visual_frame = self._normalize_preview_frame(self._load_visual_source_frame(visual_source_path))
        primary, accent = self._extract_spectrum_palette(visual_frame)
        overlay_size = self._spectrum_overlay_size(style)
        x, y = self._choose_spectrum_overlay_position(
            visual_frame,
            overlay_size,
        )
        overlay_path = output_path.with_name(f"{output_path.stem}-spectrum-overlay.mov")

        if progress_callback:
            progress_callback(
                {
                    "stage": "video_spectrum_prepare",
                    "progress_ratio": 0.0,
                    "percent": 0.0,
                    "processed_seconds": 0.0,
                    "total_seconds": round(float(total_duration_seconds or 0), 1)
                    if total_duration_seconds
                    else None,
                    "eta_seconds": None,
                    "message": "Preparing audio-reactive visualizer overlay.",
                    "status": "running",
                }
            )

        try:
            self._build_spectrum_overlay_video(
                audio_path,
                overlay_path,
                primary=primary,
                accent=accent,
                style=style,
                overlay_size=overlay_size,
                total_duration_seconds=total_duration_seconds,
                progress_callback=progress_callback,
            )
            command = [
                self.settings.ffmpeg_binary,
                "-y",
                "-hide_banner",
                "-nostats",
                "-progress",
                "pipe:1",
                "-i",
                str(base_video_path),
                "-stream_loop",
                "-1",
                "-i",
                str(overlay_path),
                "-filter_complex",
                (
                    "[1:v]format=rgba[visualizer];"
                    f"[0:v][visualizer]overlay=x={x}:y={y}:shortest=1:format=auto,"
                    "format=yuv420p[v]"
                ),
                "-map",
                "[v]",
                "-map",
                "0:a:0",
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                "-crf",
                "24",
                "-c:a",
                "copy",
                "-shortest",
                "-movflags",
                "+faststart",
                str(output_path),
            ]
            self._run_ffmpeg_with_progress(
                command,
                output_path=output_path,
                total_duration_seconds=total_duration_seconds,
                progress_callback=progress_callback,
                stage="video_spectrum_overlay",
            )
        finally:
            overlay_path.unlink(missing_ok=True)

    def _build_spectrum_overlay_video(
        self,
        audio_path: Path,
        output_path: Path,
        *,
        primary: tuple[int, int, int],
        accent: tuple[int, int, int],
        style: str,
        overlay_size: tuple[int, int],
        total_duration_seconds: int | float | None,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> Path:
        duration_seconds = float(total_duration_seconds or 0)
        if duration_seconds <= 0:
            duration_seconds = self._probe_media_duration(audio_path)
        duration_seconds = max(duration_seconds, 0.1)
        if progress_callback:
            progress_callback(
                {
                    "stage": "video_spectrum_prepare",
                    "progress_ratio": 0.0,
                    "percent": 0.0,
                    "processed_seconds": 0.0,
                    "total_seconds": round(duration_seconds, 1),
                    "eta_seconds": None,
                    "status": "analyzing_audio",
                }
            )
        samples = self._read_audio_samples(audio_path, duration_seconds)
        frame_count = max(1, int(math.ceil(duration_seconds * SPECTRUM_OVERLAY_FPS)))
        overlay_width, overlay_height = overlay_size
        edge_fade_mask = None if style == "radial" else self._spectrum_edge_fade_mask(overlay_size)

        command = [
            self.settings.ffmpeg_binary,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgba",
            "-s",
            f"{overlay_width}x{overlay_height}",
            "-r",
            str(SPECTRUM_OVERLAY_FPS),
            "-i",
            "pipe:0",
            "-an",
            "-c:v",
            "qtrle",
            str(output_path),
        ]
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        if process.stdin is None:
            raise RuntimeError("ffmpeg overlay pipe could not be opened.")

        smoothed = 0.0
        started = time.monotonic()
        last_emit = 0.0

        def emit_overlay_progress(frame_index: int, *, force: bool = False) -> None:
            nonlocal last_emit
            if progress_callback is None:
                return
            now = time.monotonic()
            if not force and now - last_emit < 2:
                return
            last_emit = now
            processed_seconds = min(frame_index / SPECTRUM_OVERLAY_FPS, duration_seconds)
            ratio = min(processed_seconds / duration_seconds, 1.0) if duration_seconds > 0 else 0.0
            eta_seconds = None
            if ratio > 0 and ratio < 1:
                elapsed = max(now - started, 0.1)
                eta_seconds = max(elapsed * (1 - ratio) / ratio, 0.0)
            progress_callback(
                {
                    "stage": "video_spectrum_prepare",
                    "progress_ratio": ratio,
                    "percent": round(ratio * 100, 1),
                    "processed_seconds": round(processed_seconds, 1),
                    "total_seconds": round(duration_seconds, 1),
                    "eta_seconds": round(eta_seconds, 1) if eta_seconds is not None else None,
                    "elapsed_seconds": round(now - started, 1),
                    "frame": str(frame_index),
                    "status": "rendering_overlay",
                }
            )

        try:
            for frame_index in range(frame_count):
                timestamp = frame_index / SPECTRUM_OVERLAY_FPS
                raw_level = self._audio_level_for_time(samples, timestamp)
                if raw_level > smoothed:
                    smoothed = (smoothed * 0.45) + (raw_level * 0.55)
                else:
                    smoothed = (smoothed * 0.82) + (raw_level * 0.18)
                if style == "multiwave":
                    frame = self._draw_wave_spectrum_frame(
                        frame_index,
                        smoothed,
                        raw_level=raw_level,
                        samples=samples,
                        timestamp=timestamp,
                        primary=primary,
                        accent=accent,
                    )
                elif style == "thinwave":
                    frame = self._draw_thin_wave_spectrum_frame(
                        frame_index,
                        smoothed,
                        raw_level=raw_level,
                        samples=samples,
                        timestamp=timestamp,
                        primary=primary,
                        accent=accent,
                    )
                elif style == "dots":
                    frame = self._draw_dot_spectrum_frame(
                        frame_index,
                        smoothed,
                        raw_level=raw_level,
                        samples=samples,
                        timestamp=timestamp,
                        primary=primary,
                        accent=accent,
                    )
                elif style == "mirror-bars":
                    frame = self._draw_mirror_bar_spectrum_frame(
                        frame_index,
                        smoothed,
                        primary=primary,
                        accent=accent,
                    )
                elif style == "radial":
                    frame = self._draw_radial_spectrum_frame(
                        frame_index,
                        smoothed,
                        primary=primary,
                        accent=accent,
                        overlay_size=overlay_size,
                    )
                elif style == "pulse":
                    frame = self._draw_pulse_spectrum_frame(
                        frame_index,
                        smoothed,
                        raw_level=raw_level,
                        samples=samples,
                        timestamp=timestamp,
                        primary=primary,
                        accent=accent,
                    )
                else:
                    frame = self._draw_bar_spectrum_frame(
                        frame_index,
                        smoothed,
                        primary=primary,
                        accent=accent,
                    )
                if edge_fade_mask is not None:
                    frame = self._apply_spectrum_edge_fade(frame, edge_fade_mask)
                process.stdin.write(frame.tobytes())
                emit_overlay_progress(frame_index)
            emit_overlay_progress(frame_count, force=True)
        except BrokenPipeError as exc:
            raise RuntimeError("ffmpeg overlay pipe closed unexpectedly.") from exc
        finally:
            process.stdin.close()

        stderr = process.stderr.read().decode("utf-8", errors="replace") if process.stderr else ""
        return_code = process.wait()
        if return_code != 0:
            details = "\n".join(line for line in stderr.splitlines()[-8:] if line.strip())
            raise RuntimeError(f"ffmpeg failed while preparing visualizer overlay: {details or return_code}")
        return output_path

    def _spectrum_overlay_size(self, style: str) -> tuple[int, int]:
        if style == "radial":
            return (RADIAL_SPECTRUM_OVERLAY_WIDTH, RADIAL_SPECTRUM_OVERLAY_HEIGHT)
        return (SPECTRUM_OVERLAY_WIDTH, SPECTRUM_OVERLAY_HEIGHT)

    def _spectrum_edge_fade_mask(self, size: tuple[int, int]) -> Image.Image:
        width, height = size
        fade_width = min(width // 2, max(SPECTRUM_EDGE_FADE_MIN_PX, int(width * SPECTRUM_EDGE_FADE_RATIO)))
        values: list[int] = []
        for _y in range(height):
            for x in range(width):
                edge_distance = min(x, width - 1 - x)
                ratio = min(max(edge_distance / max(fade_width, 1), 0.0), 1.0)
                eased = ratio * ratio * (3 - (2 * ratio))
                values.append(int(round(eased * 255)))
        mask = Image.new("L", size)
        mask.putdata(values)
        return mask

    def _apply_spectrum_edge_fade(self, image: Image.Image, mask: Image.Image) -> Image.Image:
        faded = image.copy()
        faded.putalpha(ImageChops.multiply(faded.getchannel("A"), mask))
        return faded

    def _read_audio_samples(self, audio_path: Path, duration_seconds: float) -> array:
        command = [
            self.settings.ffmpeg_binary,
            "-v",
            "error",
            "-t",
            self._format_seconds(duration_seconds),
            "-i",
            str(audio_path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(SPECTRUM_ANALYSIS_SAMPLE_RATE),
            "-f",
            "s16le",
            "pipe:1",
        ]
        try:
            result = subprocess.run(command, check=True, capture_output=True)
        except subprocess.CalledProcessError as exc:
            details = (exc.stderr or b"").decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"ffmpeg failed while reading audio for visualizer: {details or exc}") from exc

        samples = array("h")
        samples.frombytes(result.stdout[: len(result.stdout) - (len(result.stdout) % samples.itemsize)])
        return samples

    def _audio_level_for_time(self, samples: array, timestamp: float) -> float:
        if not samples:
            return 0.0
        center = int(timestamp * SPECTRUM_ANALYSIS_SAMPLE_RATE)
        radius = max(int(SPECTRUM_ANALYSIS_SAMPLE_RATE * 0.055), 1)
        start = max(center - radius, 0)
        end = min(center + radius, len(samples))
        if end <= start:
            return 0.0
        total = 0
        peak = 0
        for value in samples[start:end]:
            magnitude = abs(int(value))
            total += magnitude
            peak = max(peak, magnitude)
        average = total / max(end - start, 1) / 32768
        peak_ratio = peak / 32768
        return min(((average * 3.9) + (peak_ratio * 0.45)) ** 0.72, 1.0)

    def _draw_bar_spectrum_frame(
        self,
        frame_index: int,
        level: float,
        *,
        primary: tuple[int, int, int],
        accent: tuple[int, int, int],
    ) -> Image.Image:
        image = Image.new("RGBA", (SPECTRUM_OVERLAY_WIDTH, SPECTRUM_OVERLAY_HEIGHT), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image, "RGBA")
        bottom = SPECTRUM_OVERLAY_HEIGHT - 12
        max_height = SPECTRUM_OVERLAY_HEIGHT - 30
        bar_width = 8
        total_gap = SPECTRUM_OVERLAY_WIDTH - (SPECTRUM_OVERLAY_BARS * bar_width)
        gap = total_gap / max(SPECTRUM_OVERLAY_BARS - 1, 1)
        center = 0.52 + (math.sin(frame_index * 0.055) * 0.08)

        for index in range(SPECTRUM_OVERLAY_BARS):
            ratio = index / max(SPECTRUM_OVERLAY_BARS - 1, 1)
            gaussian = math.exp(-((ratio - center) ** 2) / (2 * 0.22**2))
            ripple = 0.76 + (0.24 * math.sin((frame_index * 0.24) + (index * 1.37)))
            height = 7 + int(max_height * (0.10 + (level * (0.24 + (0.82 * gaussian)) * ripple)))
            height = max(5, min(height, max_height))
            x = int(round(index * (bar_width + gap)))
            y = bottom - height
            color = self._mix_rgb(primary, accent, ratio)
            glow_alpha = int(30 + (level * 44) + (gaussian * 24))
            fill_alpha = int(112 + (level * 74) + (gaussian * 34))
            draw.rounded_rectangle(
                [x - 3, y - 3, x + bar_width + 3, bottom + 3],
                radius=6,
                fill=(*color, min(glow_alpha, 105)),
            )
            draw.rounded_rectangle(
                [x, y, x + bar_width, bottom],
                radius=4,
                fill=(*color, min(fill_alpha, 220)),
            )
        return image

    def _draw_mirror_bar_spectrum_frame(
        self,
        frame_index: int,
        level: float,
        *,
        primary: tuple[int, int, int],
        accent: tuple[int, int, int],
    ) -> Image.Image:
        image = Image.new("RGBA", (SPECTRUM_OVERLAY_WIDTH, SPECTRUM_OVERLAY_HEIGHT), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image, "RGBA")
        center_y = SPECTRUM_OVERLAY_HEIGHT // 2
        max_height = (SPECTRUM_OVERLAY_HEIGHT // 2) - 10
        bar_width = 8
        total_gap = SPECTRUM_OVERLAY_WIDTH - (SPECTRUM_OVERLAY_BARS * bar_width)
        gap = total_gap / max(SPECTRUM_OVERLAY_BARS - 1, 1)
        center = 0.52 + (math.sin(frame_index * 0.075) * 0.10)

        for index in range(SPECTRUM_OVERLAY_BARS):
            ratio = index / max(SPECTRUM_OVERLAY_BARS - 1, 1)
            gaussian = math.exp(-((ratio - center) ** 2) / (2 * 0.24**2))
            ripple = 0.70 + (0.30 * math.sin((frame_index * 0.36) + (index * 1.6)))
            half_height = 4 + int(max_height * (0.08 + (level * (0.30 + (0.95 * gaussian)) * ripple)))
            half_height = max(3, min(half_height, max_height))
            x = int(round(index * (bar_width + gap)))
            color = self._mix_rgb(primary, accent, ratio)
            alpha = int(120 + (level * 82) + (gaussian * 32))
            draw.rounded_rectangle(
                [x - 2, center_y - half_height - 2, x + bar_width + 2, center_y + half_height + 2],
                radius=5,
                fill=(*color, min(alpha // 2, 100)),
            )
            draw.rounded_rectangle(
                [x, center_y - half_height, x + bar_width, center_y + half_height],
                radius=4,
                fill=(*color, min(alpha, 225)),
            )
        return image

    def _draw_dot_spectrum_frame(
        self,
        frame_index: int,
        level: float,
        *,
        raw_level: float,
        samples: array,
        timestamp: float,
        primary: tuple[int, int, int],
        accent: tuple[int, int, int],
    ) -> Image.Image:
        image = Image.new("RGBA", (SPECTRUM_OVERLAY_WIDTH, SPECTRUM_OVERLAY_HEIGHT), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image, "RGBA")
        center_y = int(SPECTRUM_OVERLAY_HEIGHT * 0.55)
        transient = max(raw_level - (level * 0.78), 0.0)
        punch = min((raw_level * 1.08) + (transient * 4.2), 1.0)
        x_gap = SPECTRUM_OVERLAY_WIDTH / max(SPECTRUM_DOT_COUNT - 1, 1)

        for index in range(SPECTRUM_DOT_COUNT):
            ratio = index / max(SPECTRUM_DOT_COUNT - 1, 1)
            sample_time = timestamp + ((ratio - 0.5) * 0.26)
            signal = self._audio_signal_at_time(samples, sample_time)
            envelope = math.exp(-((ratio - 0.53) ** 2) / (2 * 0.36**2))
            radius = SPECTRUM_DOT_BASE_RADIUS + int(
                (abs(signal) * SPECTRUM_DOT_SIGNAL_RADIUS) + (punch * SPECTRUM_DOT_PUNCH_RADIUS * envelope)
            )
            x = int(round(index * x_gap))
            y = center_y + int(signal * (15 + (punch * 14)) * (0.42 + envelope))
            color = self._mix_rgb(primary, accent, ratio)
            draw.ellipse(
                [x - radius - 2, y - radius - 2, x + radius + 2, y + radius + 2],
                fill=(*color, 26 + int(punch * 30)),
            )
            draw.ellipse(
                [x - radius, y - radius, x + radius, y + radius],
                fill=(*color, min(120 + int(punch * 72), 205)),
            )
        return image

    def _draw_radial_spectrum_frame(
        self,
        frame_index: int,
        level: float,
        *,
        primary: tuple[int, int, int],
        accent: tuple[int, int, int],
        overlay_size: tuple[int, int],
    ) -> Image.Image:
        overlay_width, overlay_height = overlay_size
        image = Image.new("RGBA", (overlay_width, overlay_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image, "RGBA")
        center_x = int(overlay_width * 0.50)
        center_y = int(overlay_height * 0.50)
        base_radius = 60
        ring_count = 48
        pulse = 0.75 + (0.25 * math.sin(frame_index * 0.23))
        for index in range(ring_count):
            ratio = index / ring_count
            angle = (ratio * math.tau) - (math.pi / 2)
            color = self._mix_rgb(primary, accent, ratio)
            ripple = 0.60 + (0.40 * math.sin((frame_index * 0.36) + (index * 1.23)))
            length = 12 + int(54 * level * pulse * ripple)
            inner = base_radius + int(level * 9)
            outer = inner + length
            x1 = center_x + math.cos(angle) * inner
            y1 = center_y + math.sin(angle) * inner
            x2 = center_x + math.cos(angle) * outer
            y2 = center_y + math.sin(angle) * outer
            draw.line((x1, y1, x2, y2), fill=(*color, 100 + int(level * 95)), width=7)
        glow_color = self._mix_rgb(primary, accent, 0.5)
        glow_radius = base_radius + 12 + int(level * 24)
        draw.ellipse(
            [
                center_x - glow_radius,
                center_y - glow_radius,
                center_x + glow_radius,
                center_y + glow_radius,
            ],
            outline=(*glow_color, 46 + int(level * 40)),
            width=6,
        )
        return image

    def _draw_pulse_spectrum_frame(
        self,
        frame_index: int,
        level: float,
        *,
        raw_level: float,
        samples: array,
        timestamp: float,
        primary: tuple[int, int, int],
        accent: tuple[int, int, int],
    ) -> Image.Image:
        image = Image.new("RGBA", (SPECTRUM_OVERLAY_WIDTH, SPECTRUM_OVERLAY_HEIGHT), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image, "RGBA")
        center_y = int(SPECTRUM_OVERLAY_HEIGHT * 0.57)
        transient = max(raw_level - (level * 0.76), 0.0)
        punch = min((raw_level * 1.25) + (transient * 5.8), 1.0)
        points_top: list[tuple[int, int]] = []
        points_bottom: list[tuple[int, int]] = []
        for x in range(0, SPECTRUM_OVERLAY_WIDTH, 5):
            ratio = x / max(SPECTRUM_OVERLAY_WIDTH - 1, 1)
            sample_time = timestamp + ((ratio - 0.5) * 0.18)
            signal = abs(self._audio_signal_at_time(samples, sample_time))
            envelope = math.exp(-((ratio - 0.53) ** 2) / (2 * 0.32**2))
            height = int((4 + (signal * 34) + (punch * 16)) * (0.35 + (0.80 * envelope)))
            points_top.append((x, center_y - height))
            points_bottom.append((x, center_y + int(height * 0.45)))
        glow = self._mix_rgb(primary, accent, 0.45)
        draw.line(points_top, fill=(*glow, 72), width=10, joint="curve")
        draw.line(points_bottom, fill=(*glow, 42), width=8, joint="curve")
        draw.line(points_top, fill=(*accent, 182), width=4, joint="curve")
        draw.line(points_bottom, fill=(*primary, 124), width=3, joint="curve")
        draw.line([(0, center_y), (SPECTRUM_OVERLAY_WIDTH, center_y)], fill=(*primary, 72), width=2)
        return image

    def _draw_thin_wave_spectrum_frame(
        self,
        frame_index: int,
        level: float,
        *,
        raw_level: float,
        samples: array,
        timestamp: float,
        primary: tuple[int, int, int],
        accent: tuple[int, int, int],
    ) -> Image.Image:
        image = Image.new("RGBA", (SPECTRUM_OVERLAY_WIDTH, SPECTRUM_OVERLAY_HEIGHT), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image, "RGBA")
        center_y = int(SPECTRUM_OVERLAY_HEIGHT * 0.56)
        transient = max(raw_level - (level * 0.82), 0.0)
        punch = min((raw_level * 1.05) + (transient * 4.2), 1.0)
        amplitude = 18 + (level * 34) + (punch * 18)
        window_seconds = 0.24
        lines = [
            (-10, -0.018, 0.70, primary, 94, 2),
            (0, 0.000, 1.00, accent, 150, 3),
            (10, 0.018, 0.70, self._mix_rgb(primary, accent, 0.62), 94, 2),
        ]
        for offset, time_shift, amp_scale, color, alpha, width in lines:
            points: list[tuple[int, int]] = []
            for x in range(0, SPECTRUM_OVERLAY_WIDTH, 4):
                ratio = x / max(SPECTRUM_OVERLAY_WIDTH - 1, 1)
                envelope = math.exp(-((ratio - 0.53) ** 2) / (2 * 0.31**2))
                signal = self._audio_signal_at_time(samples, timestamp + time_shift + ((ratio - 0.5) * window_seconds))
                y = center_y + offset + int(signal * amplitude * amp_scale * (0.35 + (0.82 * envelope)))
                points.append((x, y))
            draw.line(points, fill=(*color, min(alpha + int(punch * 36), 190)), width=width, joint="curve")
        return image

    def _draw_wave_spectrum_frame(
        self,
        frame_index: int,
        level: float,
        *,
        raw_level: float,
        samples: array,
        timestamp: float,
        primary: tuple[int, int, int],
        accent: tuple[int, int, int],
    ) -> Image.Image:
        image = Image.new("RGBA", (SPECTRUM_OVERLAY_WIDTH, SPECTRUM_OVERLAY_HEIGHT), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image, "RGBA")
        center_y = int(SPECTRUM_OVERLAY_HEIGHT * 0.55)
        transient = max(raw_level - (level * 0.78), 0.0)
        punch = min((raw_level * 1.15) + (transient * 5.2), 1.0)
        base_amplitude = 18 + (level * 36) + (punch * 28)
        window_seconds = 0.28
        glow = self._mix_rgb(primary, accent, 0.50)
        lines = [
            (-17, -0.030, 0.58, primary, 66, 2),
            (-8, -0.014, 0.76, self._mix_rgb(primary, accent, 0.30), 94, 2),
            (0, 0.000, 1.02, accent, 132, 3),
            (8, 0.014, 0.76, self._mix_rgb(primary, accent, 0.68), 94, 2),
            (17, 0.030, 0.58, glow, 62, 2),
        ]

        # A soft bloom keeps the punchy lines integrated with the background.
        midline = [
            (
                x,
                center_y
                + int(
                    self._audio_signal_at_time(samples, timestamp + ((x / SPECTRUM_OVERLAY_WIDTH) - 0.5) * 0.08)
                    * base_amplitude
                    * 0.22
                ),
            )
            for x in range(0, SPECTRUM_OVERLAY_WIDTH, 5)
        ]
        draw.line(midline, fill=(*glow, 32), width=8, joint="curve")

        for offset, time_shift, amp_scale, color, alpha, width in lines:
            points: list[tuple[int, int]] = []
            for x in range(0, SPECTRUM_OVERLAY_WIDTH, 3):
                ratio = x / max(SPECTRUM_OVERLAY_WIDTH - 1, 1)
                envelope = math.exp(-((ratio - 0.53) ** 2) / (2 * 0.28**2))
                sample_time = timestamp + time_shift + ((ratio - 0.5) * window_seconds)
                wave = self._audio_signal_at_time(samples, sample_time)
                y = center_y + offset + int(
                    wave * base_amplitude * amp_scale * (0.35 + (0.95 * envelope))
                )
                points.append((x, y))
            draw.line(points, fill=(*color, min(alpha + int(punch * 58), 225)), width=width, joint="curve")
        return image

    def _audio_signal_at_time(self, samples: array, timestamp: float) -> float:
        if not samples:
            return 0.0
        sample_index = min(max(timestamp * SPECTRUM_ANALYSIS_SAMPLE_RATE, 0.0), len(samples) - 1)
        left_index = int(sample_index)
        right_index = min(left_index + 1, len(samples) - 1)
        ratio = sample_index - left_index
        left = int(samples[left_index]) / 32768
        right = int(samples[right_index]) / 32768
        value = left + ((right - left) * ratio)
        return math.copysign(min(abs(value) ** 0.58, 1.0), value)

    def _load_visual_source_frame(self, source_path: Path) -> Image.Image:
        mimetype = guess_type(str(source_path))[0] or ""
        if mimetype.startswith("image/"):
            try:
                with Image.open(source_path) as image:
                    return image.convert("RGB").copy()
            except OSError:
                pass

        try:
            result = subprocess.run(
                [
                    self.settings.ffmpeg_binary,
                    "-v",
                    "error",
                    "-ss",
                    "0",
                    "-i",
                    str(source_path),
                    "-frames:v",
                    "1",
                    "-f",
                    "image2pipe",
                    "-vcodec",
                    "png",
                    "pipe:1",
                ],
                check=True,
                capture_output=True,
            )
            with Image.open(BytesIO(result.stdout)) as image:
                return image.convert("RGB").copy()
        except (OSError, subprocess.CalledProcessError):
            return Image.new("RGB", (1280, 720), "#10141d")

    def _normalize_preview_frame(self, source: Image.Image) -> Image.Image:
        image = ImageOps.contain(source.convert("RGB"), (1280, 720), Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", (1280, 720), "#000000")
        canvas.paste(image, ((1280 - image.width) // 2, (720 - image.height) // 2))
        return canvas

    def _extract_spectrum_palette(self, image: Image.Image) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
        sample = image.resize((96, 54), Image.Resampling.BILINEAR).convert("RGB")
        candidates: list[tuple[float, float, tuple[int, int, int]]] = []
        for r, g, b in sample.getdata():
            h, lightness, saturation = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
            brightness = max(r, g, b) / 255
            if brightness < 0.16:
                continue
            if saturation < 0.12 and brightness > 0.84:
                continue
            score = (saturation * 0.72) + (brightness * 0.28)
            candidates.append((score, h, (r, g, b)))

        if not candidates:
            return (86, 232, 255), (255, 88, 210)

        candidates.sort(reverse=True, key=lambda item: item[0])
        primary = self._enhance_overlay_color(self._average_rgb([rgb for _, _, rgb in candidates[:80]]))
        primary_hue = colorsys.rgb_to_hls(*(channel / 255 for channel in primary))[0]
        accent_rgb = next(
            (
                rgb
                for _, hue, rgb in candidates[:260]
                if min(abs(hue - primary_hue), 1 - abs(hue - primary_hue)) > 0.13
            ),
            self._rotate_hue(primary, 0.16),
        )
        accent = self._enhance_overlay_color(accent_rgb)
        return primary, accent

    def _choose_spectrum_overlay_position(self, image: Image.Image, size: tuple[int, int]) -> tuple[int, int]:
        width, height = size
        if width >= 300 and height >= 300:
            candidates = [
                (930, 380),
                (950, 370),
                (900, 395),
                (875, 360),
                (930, 300),
                (760, 360),
            ]
        else:
            right_x = max(1280 - width - 55, 0)
            lower_y = max(720 - height - 45, 0)
            candidates = [
                (right_x, lower_y),
                (max(right_x - 35, 0), lower_y),
                (max(1280 - width - 40, 0), 500),
                (max(right_x - 205, 0), lower_y),
                (max(640 - (width // 2), 0), max(720 - height - 30, 0)),
                (max(1280 - width - 55, 0), 455),
            ]
        candidates = [(x, y) for x, y in candidates if x + width <= 1280 and y + height <= 720]
        if not candidates:
            return max(1280 - width - 50, 0), max(720 - height - 45, 0)

        scored = [(self._overlay_region_score(image, x, y, width, height), (x, y)) for x, y in candidates]
        default_score = scored[0][0]
        best_score, best_position = min(scored, key=lambda item: item[0])
        if default_score <= 0.46 or default_score <= best_score + 0.12:
            return candidates[0]
        return best_position

    def _overlay_region_score(self, image: Image.Image, x: int, y: int, width: int, height: int) -> float:
        crop = image.crop((x, y, x + width, y + height)).resize((72, 24), Image.Resampling.BILINEAR).convert("RGB")
        pixels = list(crop.getdata())
        if not pixels:
            return 0.0
        bright = 0
        white = 0
        saturated = 0
        luma_sum = 0.0
        for r, g, b in pixels:
            luma = ((r * 0.2126) + (g * 0.7152) + (b * 0.0722)) / 255
            luma_sum += luma
            if luma > 0.72:
                bright += 1
            if min(r, g, b) > 190:
                white += 1
            if max(r, g, b) - min(r, g, b) > 95 and luma > 0.36:
                saturated += 1
        count = len(pixels)
        return ((bright / count) * 0.9) + ((white / count) * 1.5) + ((saturated / count) * 0.45) + (
            (luma_sum / count) * 0.15
        )

    def _average_rgb(self, values: list[tuple[int, int, int]]) -> tuple[int, int, int]:
        if not values:
            return 86, 232, 255
        count = len(values)
        return (
            int(sum(value[0] for value in values) / count),
            int(sum(value[1] for value in values) / count),
            int(sum(value[2] for value in values) / count),
        )

    def _enhance_overlay_color(self, rgb: tuple[int, int, int]) -> tuple[int, int, int]:
        h, lightness, saturation = colorsys.rgb_to_hls(*(channel / 255 for channel in rgb))
        lightness = min(max(lightness, 0.52), 0.70)
        saturation = min(max(saturation, 0.58), 0.92)
        r, g, b = colorsys.hls_to_rgb(h, lightness, saturation)
        return int(r * 255), int(g * 255), int(b * 255)

    def _rotate_hue(self, rgb: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
        h, lightness, saturation = colorsys.rgb_to_hls(*(channel / 255 for channel in rgb))
        r, g, b = colorsys.hls_to_rgb((h + amount) % 1.0, lightness, saturation)
        return int(r * 255), int(g * 255), int(b * 255)

    def _mix_rgb(
        self,
        first: tuple[int, int, int],
        second: tuple[int, int, int],
        ratio: float,
    ) -> tuple[int, int, int]:
        ratio = min(max(ratio, 0.0), 1.0)
        return (
            int(first[0] + ((second[0] - first[0]) * ratio)),
            int(first[1] + ((second[1] - first[1]) * ratio)),
            int(first[2] + ((second[2] - first[2]) * ratio)),
        )

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
            return str(path.resolve()).replace("'", "'\\''")

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
