from types import SimpleNamespace

from app.utils.channel_genre_playlists import infer_channel_genre_classification


def test_haruharu_trap_and_boom_bap_share_hiphop_playlist() -> None:
    trap = infer_channel_genre_classification(
        {"youtube_channel_title": "HaruHaru", "youtube_title": "[playlist] K-POP Trap Night"},
        tracks=[SimpleNamespace(title="Seoul Step", prompt="", metadata_json={"style": "K-pop trap, 808 drums"})],
    )
    boom_bap = infer_channel_genre_classification(
        {"youtube_channel_title": "HaruHaru", "youtube_title": "[playlist] K-POP Boom Bap Walk"},
        tracks=[SimpleNamespace(title="Old Hoodie", prompt="", metadata_json={"style": "K-pop boom bap rap-pop"})],
    )

    assert trap.style_lane == "K-pop trap / rap-pop"
    assert boom_bap.style_lane == "K-pop boom bap / rap-pop"
    assert trap.playlist_titles == ("K-pop Hip-Hop",)
    assert boom_bap.playlist_titles == ("K-pop Hip-Hop",)


def test_haruharu_citypop_maps_to_synthpop_playlist_when_explicit() -> None:
    citypop = infer_channel_genre_classification(
        {"youtube_channel_title": "HaruHaru", "youtube_title": "[playlist] K-POP 시티팝 그루브"},
    )

    assert citypop.style_lane == "K-pop synth-pop"
    assert citypop.playlist_titles == ("K-pop Synth-Pop",)


def test_channel_specific_genre_playlist_classification() -> None:
    soft = infer_channel_genre_classification(
        {"youtube_channel_title": "Soft Hour Radio", "youtube_title": "[playlist] Lofi Study BGM"},
    )
    sundaze = infer_channel_genre_classification(
        {"youtube_channel_title": "sundaze", "youtube_title": "[playlist] Country Pop Road Trip"},
    )
    solwave = infer_channel_genre_classification(
        {"youtube_channel_title": "Solwave Radio", "youtube_title": "[playlist] Bachata Pop para Noche de Lluvia"},
    )
    club = infer_channel_genre_classification(
        {"youtube_channel_title": "Club Bloom", "youtube_title": "[playlist] Tech House Workout Mix"},
    )

    assert soft.style_lane == "solo piano BGM"
    assert soft.playlist_titles == ("Piano BGM",)
    assert sundaze.playlist_titles == ("Country Pop",)
    assert solwave.playlist_titles == ("Bachata Pop",)
    assert club.playlist_titles == ("House Music",)
