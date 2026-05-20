from app.utils.lyric_subtitles import build_line_lyric_cues, lyric_lines_from_text


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
