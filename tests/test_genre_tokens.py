from types import SimpleNamespace

from app.utils.genre_tokens import (
    AI_GENRE_TOKEN_VERSION,
    cached_track_genre_tokens,
    extract_genre_tokens_from_values,
    track_genre_token_source_hash,
    update_track_ai_genre_token_metadata,
    update_track_genre_token_metadata,
)


def test_korean_citypop_derives_citypop_and_kpop_tokens() -> None:
    tokens = set(extract_genre_tokens_from_values(["Korean city-pop groove, retro synth bass"]))

    assert {"city-pop", "kpop"} <= tokens


def test_japanese_citypop_derives_citypop_and_jpop_tokens() -> None:
    tokens = set(extract_genre_tokens_from_values(["Japanese city pop, Tokyo night drive"]))

    assert {"city-pop", "jpop"} <= tokens


def test_korean_latin_context_does_not_force_kpop_without_pop_lane() -> None:
    tokens = set(extract_genre_tokens_from_values(["Korean lofi sleep BGM"]))

    assert "kpop" not in tokens
    assert {"lofi", "bgm"} <= tokens


def test_solo_piano_derives_piano_and_solo_piano_tokens() -> None:
    tokens = set(extract_genre_tokens_from_values(["felt solo piano for rainy reading BGM"]))

    assert {"piano", "solo-piano", "bgm"} <= tokens


def test_kpop_boom_bap_and_trap_keep_specific_lane_tokens() -> None:
    boom_bap_tokens = set(extract_genre_tokens_from_values(["K-pop boom bap rap-pop street groove"]))
    trap_tokens = set(extract_genre_tokens_from_values(["K-pop trap-pop with 808 drums"]))

    assert {"kpop", "hip-hop", "boom-bap", "rap-pop"} <= boom_bap_tokens
    assert {"kpop", "hip-hop", "trap"} <= trap_tokens


def test_pop_channel_specific_lanes_keep_reuse_tokens() -> None:
    sundaze_tokens = set(extract_genre_tokens_from_values(["English country pop road trip"]))
    solwave_tokens = set(extract_genre_tokens_from_values(["Spanish reggaeton pop urbano latino"]))
    tokyo_tokens = set(extract_genre_tokens_from_values(["Japanese R&B Tokyo night vocal"]))

    assert {"country-pop", "pop"} <= sundaze_tokens
    assert {"reggaeton", "urbano"} <= solwave_tokens
    assert {"jpop", "rnb"} <= tokyo_tokens


def test_cached_track_genre_tokens_merges_current_ai_tokens() -> None:
    metadata = update_track_genre_token_metadata(
        {"style": "leftfield electronic"},
        title="Basement Pulse",
        prompt="experimental club track",
    )
    metadata = update_track_ai_genre_token_metadata(
        metadata,
        title="Basement Pulse",
        prompt="experimental club track",
        tokens=["hyperpop", "deconstructed club"],
        label="Hyperpop / Deconstructed Club",
        confidence=0.88,
    )
    track = SimpleNamespace(title="Basement Pulse", prompt="experimental club track", metadata_json=metadata)

    tokens = set(cached_track_genre_tokens(track))

    assert {"hyperpop", "deconstructed-club"} <= tokens
    assert metadata["ai_genre_token_version"] == AI_GENRE_TOKEN_VERSION


def test_cached_track_genre_tokens_ignores_stale_ai_tokens() -> None:
    metadata = update_track_genre_token_metadata(
        {"style": "tech house"},
        title="Old Title",
        prompt="club track",
    )
    metadata["ai_genre_tokens"] = ["hyperpop"]
    metadata["ai_genre_token_version"] = AI_GENRE_TOKEN_VERSION
    metadata["ai_genre_token_source_hash"] = track_genre_token_source_hash(
        title="Old Title",
        prompt="club track",
        metadata=metadata,
    )
    track = SimpleNamespace(title="New Title", prompt="club track", metadata_json=metadata)

    tokens = set(cached_track_genre_tokens(track, update_missing=False))

    assert "hyperpop" not in tokens
    assert {"tech-house", "house"} <= tokens
