from app.utils.video_render_policy import (
    infer_release_vocal_mode,
    is_still_image_render_default_release,
    release_has_singable_lyrics,
    resolve_video_lyrics_overlay_style,
    should_auto_enable_video_lyrics_overlay,
)


def test_bulsong_uses_center_lyrics_even_when_explicit_style_is_different() -> None:
    meta = {"youtube_channel_title": "불송"}

    assert resolve_video_lyrics_overlay_style("auto", meta, title="자비 트립합") == "center_breath_serif"
    assert resolve_video_lyrics_overlay_style("1", meta, title="자비 트립합") == "center_breath_serif"
    assert resolve_video_lyrics_overlay_style("4", meta, title="자비 트립합") == "center_breath_serif"
    assert is_still_image_render_default_release(meta)


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


def test_non_bulsong_channels_choose_editorial_lower_left_for_auto_lyrics() -> None:
    for channel_title in ("Soft Hour Radio", "Storylight OST", "Club Bloom", "BibliaCanto"):
        assert (
            resolve_video_lyrics_overlay_style(
                "auto",
                {"youtube_channel_title": channel_title},
                title="[playlist] Gentle Music",
            )
            == "editorial_lower_left"
        )


def test_unknown_channels_use_editorial_lower_left_for_lyrics() -> None:
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
        == "editorial_lower_left"
    )


def test_non_bulsong_explicit_styles_are_forced_to_editorial_lower_left() -> None:
    meta = {"youtube_channel_title": "Custom", "id": "release-123"}

    assert resolve_video_lyrics_overlay_style("9", meta, title="Ambiguous Release") == "editorial_lower_left"
    assert resolve_video_lyrics_overlay_style("1", meta, title="Ambiguous Release") == "editorial_lower_left"


def test_release_vocal_mode_uses_channel_before_track_fallback() -> None:
    assert infer_release_vocal_mode({"target_youtube_channel_title": "불송"}) == ("vocal", "channel")
    assert infer_release_vocal_mode({"youtube_channel_title": "BibliaCanto"}) == ("vocal", "channel")
    assert infer_release_vocal_mode({"youtube_channel_title": "HaruHaru"}) == ("vocal", "channel")
    assert infer_release_vocal_mode({"youtube_channel_title": "Solwave Radio"}) == ("vocal", "channel")
    assert infer_release_vocal_mode({"youtube_channel_title": "Club Bloom"}) == ("instrumental", "channel")
    assert infer_release_vocal_mode({"youtube_channel_title": "Storylight OST"}) == ("instrumental", "channel")
    assert infer_release_vocal_mode({"youtube_channel_title": "Cinematic Pulse"}) == ("instrumental", "channel")
    assert infer_release_vocal_mode({"youtube_channel_title": "Soft Hour Radio"}) == ("instrumental", "channel")

    custom_meta = {"youtube_channel_title": "Custom Channel"}
    assert infer_release_vocal_mode(custom_meta, [{"lyrics": "line one\nline two"}]) == ("vocal", "tracks")
    assert release_has_singable_lyrics(custom_meta, [{"lyrics": "line one"}])


def test_auto_lyrics_overlay_uses_channel_policy_and_respects_disable_flag() -> None:
    assert should_auto_enable_video_lyrics_overlay({"youtube_channel_title": "불송"}, [])
    assert not should_auto_enable_video_lyrics_overlay({"youtube_channel_title": "Club Bloom"}, [{"lyrics": "line"}])
    assert should_auto_enable_video_lyrics_overlay(
        {"youtube_channel_title": "Solwave Radio"},
        [{"lyrics": "line"}],
    )
    assert not should_auto_enable_video_lyrics_overlay(
        {"youtube_channel_title": "불송", "video_lyrics_overlay_disabled": True},
        [{"lyrics": "line"}],
    )
