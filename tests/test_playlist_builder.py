import json
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from app.config import Settings
from app.models.track import Track
from app.services.playlist_builder import (
    FFMpegPlaylistBuilder,
    SPECTRUM_OVERLAY_HEIGHT,
    SPECTRUM_OVERLAY_WIDTH,
    YOUTUBE_STILL_IMAGE_FILTER,
)
from app.utils.video_render_policy import apply_video_spectrum_channel_policy, resolve_final_video_repeat_count


def test_build_video_normalizes_uploaded_cover_to_youtube_frame(tmp_path) -> None:
    args_path = tmp_path / "ffmpeg-args.json"
    ffmpeg_path = tmp_path / "fake-ffmpeg.py"
    ffmpeg_path.write_text(
        "\n".join(
            [
                "#!/usr/bin/env python3",
                "import json",
                "import pathlib",
                "import sys",
                f"pathlib.Path({str(args_path)!r}).write_text(json.dumps(sys.argv[1:]), encoding='utf-8')",
                "pathlib.Path(sys.argv[-1]).write_bytes(b'fake-video')",
            ]
        ),
        encoding="utf-8",
    )
    ffmpeg_path.chmod(0o755)

    audio_path = tmp_path / "source.mp3"
    cover_path = tmp_path / "odd-cover.png"
    output_path = tmp_path / "release.mp4"
    audio_path.write_bytes(b"fake-audio")
    cover_path.write_bytes(b"fake-cover")

    builder = FFMpegPlaylistBuilder(
        Settings(
            storage_root=tmp_path / "storage",
            ffmpeg_binary=str(ffmpeg_path),
            video_spectrum_overlay_enabled=False,
        )
    )

    result = builder.build_video(audio_path, cover_path, output_path)

    assert result == output_path
    assert output_path.read_bytes() == b"fake-video"
    args = json.loads(args_path.read_text(encoding="utf-8"))
    assert args[args.index("-vf") + 1] == YOUTUBE_STILL_IMAGE_FILTER
    assert "scale=1280:720" in args[args.index("-vf") + 1]
    assert "fps=30" in args[args.index("-vf") + 1]


def test_build_video_accepts_2k_render_resolution(tmp_path) -> None:
    args_path = tmp_path / "ffmpeg-args.json"
    ffmpeg_path = tmp_path / "fake-ffmpeg.py"
    ffmpeg_path.write_text(
        "\n".join(
            [
                "#!/usr/bin/env python3",
                "import json",
                "import pathlib",
                "import sys",
                f"pathlib.Path({str(args_path)!r}).write_text(json.dumps(sys.argv[1:]), encoding='utf-8')",
                "pathlib.Path(sys.argv[-1]).write_bytes(b'fake-video')",
            ]
        ),
        encoding="utf-8",
    )
    ffmpeg_path.chmod(0o755)

    audio_path = tmp_path / "source.mp3"
    cover_path = tmp_path / "cinematic-cover.png"
    output_path = tmp_path / "release.mp4"
    audio_path.write_bytes(b"fake-audio")
    cover_path.write_bytes(b"fake-cover")

    builder = FFMpegPlaylistBuilder(
        Settings(
            storage_root=tmp_path / "storage",
            ffmpeg_binary=str(ffmpeg_path),
            video_spectrum_overlay_enabled=False,
        )
    )

    result = builder.build_video(audio_path, cover_path, output_path, render_resolution="2k")

    assert result == output_path
    args = json.loads(args_path.read_text(encoding="utf-8"))
    assert "scale=2560:1440" in args[args.index("-vf") + 1]
    assert args[args.index("-crf") + 1] == "18"


def test_build_video_can_burn_line_lyric_subtitles(tmp_path, monkeypatch) -> None:
    audio_path = tmp_path / "source.mp3"
    cover_path = tmp_path / "cover.png"
    output_path = tmp_path / "release.mp4"
    audio_path.write_bytes(b"fake-audio")
    cover_path.write_bytes(b"fake-cover")

    builder = FFMpegPlaylistBuilder(
        Settings(
            storage_root=tmp_path / "storage",
            video_spectrum_overlay_enabled=False,
        )
    )
    calls = []

    def fake_run(command, *, output_path, total_duration_seconds, progress_callback=None, stage="video_render"):
        calls.append(
            {
                "command": command,
                "output_path": output_path,
                "total_duration_seconds": total_duration_seconds,
                "stage": stage,
            }
        )
        output_path.write_bytes(f"fake-{stage}".encode("utf-8"))

    monkeypatch.setattr(builder, "_run_ffmpeg_with_progress", fake_run)

    result = builder.build_video(
        audio_path,
        cover_path,
        output_path,
        lyric_cues=[
            {"start": 1.0, "end": 4.0, "text": "First line"},
            {"start": 4.2, "end": 7.0, "text": "Second line"},
        ],
        total_duration_seconds=10,
    )

    assert result == output_path
    assert output_path.read_bytes() == b"fake-video_lyrics_overlay"
    assert [call["stage"] for call in calls] == ["video_render", "video_lyrics_overlay"]
    assert calls[0]["output_path"].name == "release-base-render.mp4"
    subtitle_command = calls[1]["command"]
    assert subtitle_command[subtitle_command.index("-vf") + 1].startswith("ass=")
    assert "fps=30" in subtitle_command[subtitle_command.index("-vf") + 1]
    assert subtitle_command[subtitle_command.index("-c:a") + 1] == "copy"
    assert not (tmp_path / "release-base-render.mp4").exists()
    assert not (tmp_path / "release-lyrics.ass").exists()


def test_build_video_can_repeat_final_video_with_stream_copy(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    audio_path = Path("source.mp3")
    cover_path = Path("cover.png")
    output_path = Path("job/release.mp4")
    audio_path.write_bytes(b"fake-audio")
    cover_path.write_bytes(b"fake-cover")

    builder = FFMpegPlaylistBuilder(
        Settings(
            storage_root=tmp_path / "storage",
            video_spectrum_overlay_enabled=False,
        )
    )
    calls = []
    concat_contents = []

    def fake_run(command, *, output_path, total_duration_seconds, progress_callback=None, stage="video_render"):
        if stage == "video_repeat_concat":
            concat_path = Path(command[command.index("-i") + 1])
            concat_contents.append(concat_path.read_text(encoding="utf-8"))
        calls.append(
            {
                "command": command,
                "output_path": output_path,
                "total_duration_seconds": total_duration_seconds,
                "stage": stage,
            }
        )
        output_path.write_bytes(f"fake-{stage}".encode("utf-8"))

    monkeypatch.setattr(builder, "_run_ffmpeg_with_progress", fake_run)

    result = builder.build_video(
        audio_path,
        cover_path,
        output_path,
        total_duration_seconds=2400,
        final_repeat_count=3,
    )

    assert result == output_path
    assert output_path.read_bytes() == b"fake-video_repeat_concat"
    assert [call["stage"] for call in calls] == ["video_render", "video_repeat_concat"]
    repeat_command = calls[1]["command"]
    assert repeat_command[repeat_command.index("-f") + 1] == "concat"
    assert repeat_command[repeat_command.index("-c") + 1] == "copy"
    assert calls[1]["total_duration_seconds"] == 7200
    assert f"file '{tmp_path / 'job' / 'release-repeat-source-render.mp4'}'" in concat_contents[0]
    assert not Path("job/release-repeat-source-render.mp4").exists()


def test_final_video_repeat_is_disabled_by_default() -> None:
    assert resolve_final_video_repeat_count(Settings(), {}, base_duration_seconds=2400) == 1
    assert (
        resolve_final_video_repeat_count(
            Settings(playlist_final_video_repeat_enabled=True),
            {},
            base_duration_seconds=2400,
        )
        == 3
    )


def test_spectrum_overlay_forces_30fps_output(tmp_path, monkeypatch) -> None:
    audio_path = tmp_path / "source.mp3"
    base_video_path = tmp_path / "base.mp4"
    cover_path = tmp_path / "cover.png"
    output_path = tmp_path / "release.mp4"
    audio_path.write_bytes(b"fake-audio")
    base_video_path.write_bytes(b"fake-video")
    Image.new("RGB", (1280, 720), "black").save(cover_path)

    builder = FFMpegPlaylistBuilder(Settings(storage_root=tmp_path / "storage"))
    calls = []

    def fake_build_overlay(*args, **_kwargs):
        output_path = args[1]
        output_path.write_bytes(b"fake-overlay")
        return output_path

    def fake_run(command, *, output_path, total_duration_seconds, progress_callback=None, stage="video_render"):
        calls.append({"command": command, "output_path": output_path, "stage": stage})
        output_path.write_bytes(b"fake-spectrum")

    monkeypatch.setattr(builder, "_build_spectrum_overlay_video", fake_build_overlay)
    monkeypatch.setattr(builder, "_run_ffmpeg_with_progress", fake_run)

    builder._apply_spectrum_overlay(
        base_video_path,
        audio_path,
        cover_path,
        output_path,
        spectrum_overlay_style="bars",
        render_resolution="720p",
        total_duration_seconds=10,
        progress_callback=None,
    )

    assert output_path.read_bytes() == b"fake-spectrum"
    filter_complex = calls[0]["command"][calls[0]["command"].index("-filter_complex") + 1]
    assert "[0:v]fps=30" in filter_complex
    assert "[1:v]fps=30" in filter_complex
    assert "overlay=" in filter_complex
    assert "fps=30,format=yuv420p[v]" in filter_complex


def test_ass_lyric_text_wraps_into_two_useful_lines(tmp_path) -> None:
    builder = FFMpegPlaylistBuilder(Settings(storage_root=tmp_path / "storage"))

    text = builder._format_ass_lyric_text(
        "Gathered up the promise, took the child and walked away",
        wrap_chars=42,
    )

    assert text == r"Gathered up the promise, took the child\Nand walked away"


def test_ass_lyric_fade_scales_with_cue_duration(tmp_path) -> None:
    builder = FFMpegPlaylistBuilder(Settings(storage_root=tmp_path / "storage"))

    assert builder._lyric_ass_fade_tag(1.0, 4.0) == r"{\fad(320,460)}"
    assert builder._lyric_ass_fade_tag(1.0, 1.6) == r"{\fad(180,200)}"


def test_lyric_ass_styles_are_transparent_and_positioned(tmp_path) -> None:
    builder = FFMpegPlaylistBuilder(Settings(storage_root=tmp_path / "storage"))
    cues = [{"start": 1.0, "end": 4.0, "text": "자비의 길을 걸어"}]

    center_path = tmp_path / "center.ass"
    builder._write_lyric_ass_file(
        center_path,
        cues,
        frame_size=(1280, 720),
        lyric_overlay_style="center_breath_serif",
    )
    center_text = center_path.read_text(encoding="utf-8")
    center_style = next(line for line in center_text.splitlines() if line.startswith("Style: Lyrics,"))
    assert "Style: Lyrics,Noto Serif KR" in center_text
    assert ",0,0,0,,{\\fad(540,720)\\blur0.45}" in center_text
    assert "&H00000000" in center_style
    assert center_style.split(",")[18] == "5"

    lower_left_path = tmp_path / "lower-left.ass"
    builder._write_lyric_ass_file(
        lower_left_path,
        cues,
        frame_size=(1280, 720),
        lyric_overlay_style="editorial_lower_left",
    )
    lower_left_style = next(
        line for line in lower_left_path.read_text(encoding="utf-8").splitlines() if line.startswith("Style: Lyrics,")
    )
    assert "&H00000000" in lower_left_style
    assert lower_left_style.split(",")[18] == "1"


def test_build_audio_rejects_unreadable_source_file(tmp_path) -> None:
    audio_path = tmp_path / "empty.mp3"
    output_path = tmp_path / "release.mp3"
    audio_path.write_bytes(b"")

    builder = FFMpegPlaylistBuilder(Settings(storage_root=tmp_path / "storage"))

    with pytest.raises(ValueError, match="unreadable audio"):
        builder.build_audio(
            [Track(title="Broken Upload", duration_seconds=210, audio_path=str(audio_path))],
            output_path,
        )

    assert not output_path.exists()


def test_spectrum_edge_fade_softens_linear_overlay_edges(tmp_path) -> None:
    builder = FFMpegPlaylistBuilder(Settings(storage_root=tmp_path / "storage"))
    image = Image.new("RGBA", (SPECTRUM_OVERLAY_WIDTH, SPECTRUM_OVERLAY_HEIGHT), (255, 255, 255, 200))

    mask = builder._spectrum_edge_fade_mask(image.size)
    faded = builder._apply_spectrum_edge_fade(image, mask)

    center_x = SPECTRUM_OVERLAY_WIDTH // 2
    assert faded.getpixel((0, SPECTRUM_OVERLAY_HEIGHT // 2))[3] == 0
    assert faded.getpixel((SPECTRUM_OVERLAY_WIDTH - 1, SPECTRUM_OVERLAY_HEIGHT // 2))[3] == 0
    assert faded.getpixel((center_x, SPECTRUM_OVERLAY_HEIGHT // 2))[3] == 200
    assert 0 < faded.getpixel((32, SPECTRUM_OVERLAY_HEIGHT // 2))[3] < 200


def test_removed_dot_visualizer_aliases_fall_back_to_bars(tmp_path) -> None:
    builder = FFMpegPlaylistBuilder(Settings(storage_root=tmp_path / "storage"))

    assert builder._normalize_spectrum_overlay_style("dots") == "bars"
    assert builder._normalize_spectrum_overlay_style("dot") == "bars"
    assert builder._normalize_spectrum_overlay_style("particles") == "bars"
    assert builder._normalize_spectrum_overlay_style("thinwave") == "bars"
    assert builder._normalize_spectrum_overlay_style("thin-wave") == "bars"
    assert builder._normalize_spectrum_overlay_style("clean-wave") == "bars"
    assert builder._normalize_spectrum_overlay_style("multiwave") == "bars"
    assert builder._normalize_spectrum_overlay_style("radial") == "bars"
    assert builder._normalize_spectrum_overlay_style("pulse") == "bars"
    assert builder._normalize_spectrum_overlay_style("calm") == "calm-bars"
    assert builder._normalize_spectrum_overlay_style("low-motion-bars") == "calm-bars"


def test_buddhist_channel_uses_low_motion_spectrum() -> None:
    assert (
        apply_video_spectrum_channel_policy(
            "bars",
            {"target_youtube_channel_title": "불송"},
            title="[playlist] 법구경 힙합",
        )
        == "calm-bars"
    )


def test_spectrum_overlay_position_stays_bottom_right(tmp_path) -> None:
    builder = FFMpegPlaylistBuilder(Settings(storage_root=tmp_path / "storage"))
    frame = Image.new("RGB", (1280, 720), "#111111")
    draw = ImageDraw.Draw(frame)
    assert SPECTRUM_OVERLAY_WIDTH == 280
    expected = (1280 - SPECTRUM_OVERLAY_WIDTH - 55, 720 - SPECTRUM_OVERLAY_HEIGHT - 45)
    draw.rectangle(
        [
            expected[0],
            expected[1],
            expected[0] + SPECTRUM_OVERLAY_WIDTH,
            expected[1] + SPECTRUM_OVERLAY_HEIGHT,
        ],
        fill="#ffffff",
    )

    assert builder._choose_spectrum_overlay_position(frame, (SPECTRUM_OVERLAY_WIDTH, SPECTRUM_OVERLAY_HEIGHT)) == expected


def test_bar_spectrum_is_center_weighted_and_balanced(tmp_path) -> None:
    builder = FFMpegPlaylistBuilder(Settings(storage_root=tmp_path / "storage"))

    image = builder._draw_bar_spectrum_frame(
        0,
        0.72,
        primary=(220, 230, 255),
        accent=(255, 180, 210),
    )
    alpha = image.getchannel("A")

    def region_alpha(left: int, right: int) -> int:
        return sum(alpha.crop((left, 0, right, SPECTRUM_OVERLAY_HEIGHT)).getdata())

    left_edge = region_alpha(0, 64)
    center = region_alpha(108, 172)
    right_edge = region_alpha(SPECTRUM_OVERLAY_WIDTH - 64, SPECTRUM_OVERLAY_WIDTH)

    assert center > left_edge * 2
    assert center > right_edge * 2
    assert abs(left_edge - right_edge) < max(left_edge, right_edge) * 0.35


def test_bar_spectrum_bounces_without_horizontal_drift(tmp_path) -> None:
    builder = FFMpegPlaylistBuilder(Settings(storage_root=tmp_path / "storage"))

    def alpha_centroid_x(frame_index: int) -> float:
        image = builder._draw_bar_spectrum_frame(
            frame_index,
            0.72,
            primary=(220, 230, 255),
            accent=(255, 180, 210),
        )
        alpha = image.getchannel("A")
        total = 0
        weighted = 0
        for y in range(SPECTRUM_OVERLAY_HEIGHT):
            for x in range(SPECTRUM_OVERLAY_WIDTH):
                value = alpha.getpixel((x, y))
                total += value
                weighted += x * value
        return weighted / total

    assert abs(alpha_centroid_x(0) - alpha_centroid_x(24)) < 2.5


def test_build_audio_reports_ffmpeg_progress(tmp_path, monkeypatch) -> None:
    audio_paths = [tmp_path / "one.mp3", tmp_path / "two.mp3"]
    for path in audio_paths:
        path.write_bytes(b"fake-audio")
    output_path = tmp_path / "release.mp3"

    builder = FFMpegPlaylistBuilder(Settings(storage_root=tmp_path / "storage"))
    captured = {}
    progress_events = []

    monkeypatch.setattr(builder, "_probe_media_duration", lambda path: 20.0 if path == output_path else 10.0)

    def fake_run(command, *, output_path, total_duration_seconds, progress_callback=None, stage="video_render"):
        captured["command"] = command
        captured["total_duration_seconds"] = total_duration_seconds
        captured["stage"] = stage
        output_path.write_bytes(b"rendered-audio")
        if progress_callback:
            progress_callback({"stage": stage, "percent": 50.0})

    monkeypatch.setattr(builder, "_run_ffmpeg_with_progress", fake_run)

    result = builder.build_audio(
        [
            Track(title="One", duration_seconds=10, audio_path=str(audio_paths[0])),
            Track(title="Two", duration_seconds=10, audio_path=str(audio_paths[1])),
        ],
        output_path,
        progress_callback=progress_events.append,
    )

    assert result == output_path
    assert output_path.read_bytes() == b"rendered-audio"
    assert captured["stage"] == "audio_render"
    assert captured["total_duration_seconds"] == 20.0
    assert captured["command"][captured["command"].index("-progress") + 1] == "pipe:1"
    assert progress_events == [{"stage": "audio_render", "percent": 50.0}]


def test_build_audio_uses_decoded_duration_when_mp3_metadata_is_inaccurate(tmp_path, monkeypatch) -> None:
    audio_paths = [tmp_path / "one.mp3", tmp_path / "two.mp3"]
    for path in audio_paths:
        path.write_bytes(b"fake-audio")
    output_path = tmp_path / "release.mp3"
    builder = FFMpegPlaylistBuilder(Settings(storage_root=tmp_path / "storage"))
    captured = {}

    monkeypatch.setattr(builder, "_probe_media_duration", lambda path: 40.0 if path == output_path else 30.0)
    monkeypatch.setattr(builder, "_decode_media_duration", lambda _path: 20.0)

    def fake_run(command, *, output_path, total_duration_seconds, progress_callback=None, stage="video_render"):
        captured["total_duration_seconds"] = total_duration_seconds
        output_path.write_bytes(b"rendered-audio")

    monkeypatch.setattr(builder, "_run_ffmpeg_with_progress", fake_run)

    builder.build_audio(
        [
            Track(title="One", duration_seconds=30, audio_path=str(audio_paths[0])),
            Track(title="Two", duration_seconds=30, audio_path=str(audio_paths[1])),
        ],
        output_path,
    )

    assert captured["total_duration_seconds"] == 40.0


def test_build_looped_video_creates_forward_crossfade_loop_unit(tmp_path) -> None:
    calls_path = tmp_path / "ffmpeg-calls.jsonl"
    concat_path = tmp_path / "concat-list.txt"
    ffmpeg_path = tmp_path / "fake-ffmpeg.py"
    ffmpeg_path.write_text(
        "\n".join(
            [
                "#!/usr/bin/env python3",
                "import json",
                "import pathlib",
                "import sys",
                f"with pathlib.Path({str(calls_path)!r}).open('a', encoding='utf-8') as handle:",
                "    handle.write(json.dumps(sys.argv[1:]) + '\\n')",
                "for arg in sys.argv[1:]:",
                "    if arg.endswith('-loop-concat.txt') and pathlib.Path(arg).exists():",
                f"        pathlib.Path({str(concat_path)!r}).write_text(pathlib.Path(arg).read_text(encoding='utf-8'), encoding='utf-8')",
                "pathlib.Path(sys.argv[-1]).write_bytes(b'fake-video')",
            ]
        ),
        encoding="utf-8",
    )
    ffmpeg_path.chmod(0o755)

    clip_path = tmp_path / "loop.mp4"
    audio_path = tmp_path / "source.mp3"
    output_path = tmp_path / "release.mp4"
    clip_path.write_bytes(b"fake-clip")
    audio_path.write_bytes(b"fake-audio")

    builder = FFMpegPlaylistBuilder(
        Settings(
            storage_root=tmp_path / "storage",
            ffmpeg_binary=str(ffmpeg_path),
            video_spectrum_overlay_enabled=False,
        )
    )

    result = builder.build_looped_video(clip_path, audio_path, output_path)

    assert result == output_path
    calls = [json.loads(line) for line in calls_path.read_text(encoding="utf-8").splitlines()]
    assert len(calls) == 6

    normalize_filter = calls[0][calls[0].index("-vf") + 1]
    assert "trim=duration=7" in normalize_filter

    intro_call = calls[1]
    assert intro_call[intro_call.index("-t") + 1] == "5.5"

    transition_call = calls[2]
    transition_filter = transition_call[transition_call.index("-filter_complex") + 1]
    assert "reverse" not in transition_filter
    assert "xfade=transition=fade:duration=1.5:offset=0" in transition_filter
    assert transition_call[transition_call.index("-ss") + 1] == "5.5"

    body_call = calls[3]
    assert body_call[body_call.index("-ss") + 1] == "1.5"
    assert body_call[body_call.index("-t") + 1] == "4"

    loop_unit_call = calls[4]
    loop_unit_filter = loop_unit_call[loop_unit_call.index("-filter_complex") + 1]
    assert "concat=n=2:v=1:a=0" in loop_unit_filter

    render_call = calls[5]
    assert render_call[render_call.index("-f") + 1] == "concat"
    assert render_call[render_call.index("-safe") + 1] == "0"
    assert "-filter_complex" not in render_call
    assert "-stream_loop" not in render_call
    assert render_call[render_call.index("-c:v") + 1] == "copy"
    assert render_call[render_call.index("-map") + 1] == "0:v:0"
    assert "1:a:0" in render_call
    concat_lines = concat_path.read_text(encoding="utf-8").splitlines()
    assert concat_lines[0].endswith("-loop-intro.mp4'")
    assert all(line.endswith("-loop-unit.mp4'") for line in concat_lines[1:])
    assert output_path.read_bytes() == b"fake-video"


def test_looped_video_uses_requested_crossfade_seconds(tmp_path) -> None:
    builder = FFMpegPlaylistBuilder(
        Settings(
            storage_root=tmp_path / "storage",
            video_spectrum_overlay_enabled=False,
        )
    )

    assert builder._resolve_loop_transition_seconds(10.0, configured_transition=2.0) == 2.0
    assert builder._resolve_loop_transition_seconds(3.0, configured_transition=2.0) == 1.0
