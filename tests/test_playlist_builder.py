import json

from app.config import Settings
from app.services.playlist_builder import FFMpegPlaylistBuilder, YOUTUBE_STILL_IMAGE_FILTER


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
        )
    )

    result = builder.build_video(audio_path, cover_path, output_path)

    assert result == output_path
    assert output_path.read_bytes() == b"fake-video"
    args = json.loads(args_path.read_text(encoding="utf-8"))
    assert args[args.index("-vf") + 1] == YOUTUBE_STILL_IMAGE_FILTER
    assert "scale=1280:720" in args[args.index("-vf") + 1]


def test_build_looped_video_creates_forward_crossfade_loop_unit(tmp_path) -> None:
    calls_path = tmp_path / "ffmpeg-calls.jsonl"
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
        )
    )

    result = builder.build_looped_video(clip_path, audio_path, output_path)

    assert result == output_path
    calls = [json.loads(line) for line in calls_path.read_text(encoding="utf-8").splitlines()]
    assert len(calls) == 6

    normalize_filter = calls[0][calls[0].index("-vf") + 1]
    assert "trim=duration=8" in normalize_filter

    intro_call = calls[1]
    assert intro_call[intro_call.index("-t") + 1] == "7"

    transition_call = calls[2]
    transition_filter = transition_call[transition_call.index("-filter_complex") + 1]
    assert "reverse" not in transition_filter
    assert "xfade=transition=fade:duration=1:offset=0" in transition_filter
    assert transition_call[transition_call.index("-ss") + 1] == "7"

    body_call = calls[3]
    assert body_call[body_call.index("-ss") + 1] == "1"
    assert body_call[body_call.index("-t") + 1] == "6"

    loop_unit_call = calls[4]
    loop_unit_filter = loop_unit_call[loop_unit_call.index("-filter_complex") + 1]
    assert "concat=n=2:v=1:a=0" in loop_unit_filter

    render_call = calls[5]
    assert render_call[render_call.index("-stream_loop") + 1] == "-1"
    render_filter = render_call[render_call.index("-filter_complex") + 1]
    assert "concat=n=2:v=1:a=0" in render_filter
    assert render_call[render_call.index("-map") + 1] == "[loopv]"
    assert "2:a:0" in render_call
    assert output_path.read_bytes() == b"fake-video"
