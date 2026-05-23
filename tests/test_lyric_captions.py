from pathlib import Path

import app.services.lyric_caption_service as lyric_caption_service
from app.config import Settings
from app.models.playlist import Playlist
from app.models.track import Track
from app.services.lyric_caption_service import LyricCaptionService
from app.utils.lyric_captions import build_srt_from_lyric_cues


def test_build_srt_from_lyric_cues_formats_caption_blocks() -> None:
    srt = build_srt_from_lyric_cues(
        [
            {"start": 1.234, "end": 4.5, "text": "First line"},
            {"start": 5.0, "end": 7.25, "text": "Second <bad> line"},
        ]
    )

    assert srt == (
        "1\n"
        "00:00:01,234 --> 00:00:04,500\n"
        "First line\n\n"
        "2\n"
        "00:00:05,000 --> 00:00:07,250\n"
        "Second line\n"
    )


def test_lyric_caption_service_builds_source_and_translated_caption_tracks(monkeypatch, tmp_path) -> None:
    audio_path = tmp_path / "rendered.mp3"
    audio_path.write_bytes(b"fake")
    playlist = Playlist(
        id="playlist-1",
        title="Lyrics Release",
        actual_duration_seconds=60,
        metadata_json={
            "rendered_timeline": [
                {
                    "track_id": "track-1",
                    "title": "Song One",
                    "start_seconds_exact": 0,
                    "duration_seconds_exact": 60,
                }
            ]
        },
    )
    track = Track(
        id="track-1",
        title="Song One",
        duration_seconds=60,
        metadata_json={"lyrics": "First line\nSecond line"},
    )

    monkeypatch.setattr(
        lyric_caption_service,
        "build_word_aligned_line_lyric_cues",
        lambda *_args, **_kwargs: [
            {"start": 1.0, "end": 3.0, "text": "First line"},
            {"start": 4.0, "end": 6.0, "text": "Second line"},
        ],
    )

    service = LyricCaptionService(
        Settings(
            storage_root=tmp_path / "storage",
            youtube_lyrics_captions_languages="en,ko,ja",
        )
    )
    monkeypatch.setattr(
        service,
        "_translate_cue_texts",
        lambda texts, source_language, target_languages: {
            "ko": ["첫 번째 줄", "두 번째 줄"],
            "ja": ["最初の行", "二番目の行"],
        },
    )

    result = service.build_youtube_caption_tracks(
        playlist,
        [track],
        audio_path=Path(audio_path),
        default_language="en",
    )

    assert result.source_language == "en"
    assert result.cue_count == 2
    assert sorted(result.caption_tracks) == ["en", "ja", "ko"]
    assert "First line" in result.caption_tracks["en"]
    assert "첫 번째 줄" in result.caption_tracks["ko"]
    assert "最初の行" in result.caption_tracks["ja"]


def test_lyric_caption_service_repeats_cues_for_repeated_final_video(monkeypatch, tmp_path) -> None:
    audio_path = tmp_path / "rendered.mp3"
    audio_path.write_bytes(b"fake")
    playlist = Playlist(
        id="playlist-repeat",
        title="Lyrics Release",
        actual_duration_seconds=60,
        metadata_json={
            "video_base_duration_seconds": 60,
            "video_final_repeat_count": 2,
            "rendered_timeline": [
                {
                    "track_id": "track-1",
                    "title": "Song One",
                    "start_seconds_exact": 0,
                    "duration_seconds_exact": 60,
                }
            ],
        },
    )
    track = Track(
        id="track-1",
        title="Song One",
        duration_seconds=60,
        metadata_json={"lyrics": "First line"},
    )

    monkeypatch.setattr(
        lyric_caption_service,
        "build_word_aligned_line_lyric_cues",
        lambda *_args, **_kwargs: [{"start": 1.0, "end": 3.0, "text": "First line"}],
    )

    service = LyricCaptionService(
        Settings(
            storage_root=tmp_path / "storage",
            youtube_lyrics_captions_languages="en",
        )
    )
    result = service.build_youtube_caption_tracks(
        playlist,
        [track],
        audio_path=Path(audio_path),
        default_language="en",
    )

    assert result.cue_count == 2
    assert "00:01:01,000 --> 00:01:03,000" in result.caption_tracks["en"]
