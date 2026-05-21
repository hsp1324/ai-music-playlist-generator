from app.utils.video_render_policy import resolve_video_lyrics_overlay_style


def test_bulsong_uses_center_lyrics_even_when_explicit_style_is_different() -> None:
    meta = {"youtube_channel_title": "불송"}

    assert resolve_video_lyrics_overlay_style("auto", meta, title="자비 트립합") == "center_breath_serif"
    assert resolve_video_lyrics_overlay_style("1", meta, title="자비 트립합") == "center_breath_serif"
    assert resolve_video_lyrics_overlay_style("4", meta, title="자비 트립합") == "center_breath_serif"


def test_pop_vocal_channels_choose_editorial_lower_left_for_auto_lyrics() -> None:
    assert (
        resolve_video_lyrics_overlay_style(
            "auto",
            {"youtube_channel_title": "HaruHaru"},
            title="[playlist] K-POP R&B Mix",
        )
        == "editorial_lower_left"
    )
    assert (
        resolve_video_lyrics_overlay_style(
            "",
            {"target_youtube_channel_title": "Tokyo Daydream Radio"},
            title="[playlist] Feel-Good J-POP Mix",
        )
        == "editorial_lower_left"
    )


def test_background_and_religious_channels_choose_soft_bottom_for_auto_lyrics() -> None:
    for channel_title in ("Soft Hour Radio", "Storylight OST", "Club Bloom", "BibliaCanto"):
        assert (
            resolve_video_lyrics_overlay_style(
                "auto",
                {"youtube_channel_title": channel_title},
                title="[playlist] Gentle Music",
            )
            == "soft_bottom_fade"
        )


def test_unknown_channels_use_content_hints_before_stable_fallback() -> None:
    assert (
        resolve_video_lyrics_overlay_style(
            "auto",
            {"youtube_channel_title": "Custom"},
            title="[playlist] Latin Pop R&B Vocal Mix",
        )
        == "editorial_lower_left"
    )
    assert (
        resolve_video_lyrics_overlay_style(
            "auto",
            {"youtube_channel_title": "Custom"},
            title="[playlist] Lofi Study BGM Instrumental",
        )
        == "soft_bottom_fade"
    )


def test_unknown_ambiguous_channels_get_stable_mixed_auto_choice() -> None:
    meta = {"youtube_channel_title": "Custom", "id": "release-123"}

    first = resolve_video_lyrics_overlay_style("auto", meta, title="Ambiguous Release")
    second = resolve_video_lyrics_overlay_style("auto", meta, title="Ambiguous Release")

    assert first in {"soft_bottom_fade", "editorial_lower_left"}
    assert second == first
