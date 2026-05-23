from pathlib import Path

import app.utils.lyric_subtitles as lyric_subtitles
from app.utils.lyric_subtitles import build_line_lyric_cues, build_word_aligned_line_lyric_cues, lyric_lines_from_text


def test_lyric_lines_from_text_skips_headers_and_control_notes() -> None:
    lyrics = """
    [Verse 1]
    1. First real line
    - Second real line

    [Chorus]
    Instrumental
    Final real line
    """

    assert lyric_lines_from_text(lyrics) == [
        "First real line",
        "Second real line",
        "Final real line",
    ]


def test_build_line_lyric_cues_uses_rendered_timeline_and_clip_limit() -> None:
    cues = build_line_lyric_cues(
        [
            {
                "id": "track-1",
                "title": "Song One",
                "duration_seconds": 120,
                "lyrics": "[Verse]\nLine one\nLine two\nLine three",
            }
        ],
        [
            {
                "track_id": "track-1",
                "title": "Song One",
                "start_seconds_exact": 30,
                "duration_seconds_exact": 60,
            }
        ],
        max_end_seconds=70,
    )

    assert [cue["text"] for cue in cues] == ["Line one", "Line two", "Line three"]
    assert cues[0]["start"] >= 30
    assert cues[-1]["end"] <= 70
    assert all(cue["track_id"] == "track-1" for cue in cues)


def test_build_word_aligned_line_lyric_cues_uses_asr_word_timestamps(monkeypatch, tmp_path) -> None:
    audio_path = tmp_path / "song.wav"
    audio_path.write_bytes(b"fake-audio")

    monkeypatch.setattr(
        lyric_subtitles,
        "transcribe_words_with_faster_whisper",
        lambda *_args, **_kwargs: [
            {"token": "first", "text": "First", "start": 3.0, "end": 3.3},
            {"token": "real", "text": "real", "start": 3.35, "end": 3.7},
            {"token": "line", "text": "line", "start": 3.75, "end": 4.0},
            {"token": "second", "text": "Second", "start": 8.0, "end": 8.4},
            {"token": "real", "text": "real", "start": 8.45, "end": 8.8},
            {"token": "line", "text": "line", "start": 8.85, "end": 9.2},
        ],
    )

    cues = build_word_aligned_line_lyric_cues(
        [
            {
                "id": "track-1",
                "title": "Song One",
                "duration_seconds": 20,
                "lyrics": "[Verse]\nFirst real line\nSecond real line",
            }
        ],
        [],
        audio_path=Path(audio_path),
        model_size="tiny",
    )

    assert [cue["text"] for cue in cues] == ["First real line", "Second real line"]
    assert cues[0]["start"] < 3.0
    assert cues[0]["end"] > 4.0
    assert cues[1]["start"] < 8.0
    assert cues[1]["alignment"] == "faster-whisper"


def test_build_word_aligned_line_lyric_cues_interpolates_missing_lines(monkeypatch, tmp_path) -> None:
    audio_path = tmp_path / "song.wav"
    audio_path.write_bytes(b"fake-audio")

    monkeypatch.setattr(
        lyric_subtitles,
        "transcribe_words_with_faster_whisper",
        lambda *_args, **_kwargs: [
            {"token": "first", "text": "First", "start": 3.0, "end": 3.3},
            {"token": "real", "text": "real", "start": 3.35, "end": 3.7},
            {"token": "line", "text": "line", "start": 3.75, "end": 4.0},
            {"token": "final", "text": "Final", "start": 9.0, "end": 9.4},
            {"token": "real", "text": "real", "start": 9.45, "end": 9.8},
            {"token": "line", "text": "line", "start": 9.85, "end": 10.2},
        ],
    )

    cues = build_word_aligned_line_lyric_cues(
        [
            {
                "id": "track-1",
                "title": "Song One",
                "duration_seconds": 20,
                "lyrics": "[Verse]\nFirst real line\nMissing middle line\nFinal real line",
            }
        ],
        [],
        audio_path=Path(audio_path),
        model_size="tiny",
    )

    assert [cue["text"] for cue in cues] == [
        "First real line",
        "Missing middle line",
        "Final real line",
    ]
    assert cues[1]["alignment"] == "faster-whisper-interpolated"
    assert cues[0]["end"] <= cues[1]["start"]
    assert cues[1]["end"] <= cues[2]["start"]


def test_build_word_aligned_line_lyric_cues_normalizes_spanish_accents(monkeypatch, tmp_path) -> None:
    audio_path = tmp_path / "song.wav"
    audio_path.write_bytes(b"fake-audio")

    monkeypatch.setattr(
        lyric_subtitles,
        "transcribe_words_with_faster_whisper",
        lambda *_args, **_kwargs: [
            {"token": token, "text": token, "start": start, "end": start + 0.3}
            for token, start in [
                ("corazon", 2.0),
                ("de", 2.35),
                ("mi", 2.7),
                ("cancion", 3.05),
                ("senal", 6.0),
                ("en", 6.35),
                ("la", 6.7),
                ("noche", 7.05),
            ]
        ],
    )

    cues = build_word_aligned_line_lyric_cues(
        [
            {
                "id": "track-1",
                "title": "Cancion",
                "duration_seconds": 15,
                "lyrics": "[Verso]\nCorazón de mi canción\nSeñal en la noche",
            }
        ],
        [],
        audio_path=Path(audio_path),
        model_size="tiny",
    )

    assert [cue["text"] for cue in cues] == ["Corazón de mi canción", "Señal en la noche"]
    assert all(cue["alignment_match_coverage"] == 1.0 for cue in cues)
