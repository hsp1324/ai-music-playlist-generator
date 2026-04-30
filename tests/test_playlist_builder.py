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


def test_build_looped_video_creates_smooth_pingpong_unit(tmp_path) -> None:
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
    assert len(calls) == 2
    assert "reverse" in calls[0][calls[0].index("-filter_complex") + 1]
    assert "concat=n=2" in calls[0][calls[0].index("-filter_complex") + 1]
    assert calls[1][calls[1].index("-stream_loop") + 1] == "-1"
    assert output_path.read_bytes() == b"fake-video"
