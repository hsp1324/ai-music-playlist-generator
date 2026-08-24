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


def test_club_bloom_garage_style_uses_mainstream_public_playlist_name() -> None:
    classification = infer_channel_genre_classification(
        {
            "youtube_channel_title": "Club Bloom",
            "youtube_title": "[playlist] Dance Music Night Drive Mix",
        },
        tracks=[
            SimpleNamespace(
                title="Shuffle Current",
                prompt="UK garage instrumental club rhythm",
                metadata_json={"style": "UK garage, no vocals"},
            )
        ],
    )

    assert classification.style_lane == "UK garage"
    assert classification.playlist_titles == ("Bass Music",)


def test_bulsong_source_explicit_titles_archive_to_bulsong_playlist() -> None:
    classification = infer_channel_genre_classification(
        {"youtube_channel_title": "불송", "youtube_title": "[playlist] 마음을 다스리는 법구경 힙합"},
        tracks=[SimpleNamespace(title="밤의 숨", prompt="", metadata_json={"style": "Korean hip-hop"})],
    )

    assert classification.style_lane == "legacy source-explicit Bulsong"
    assert classification.playlist_titles == ("불송",)


def test_bulsong_mainstream_titles_default_to_song_playlist() -> None:
    classification = infer_channel_genre_classification(
        {"youtube_channel_title": "불송", "youtube_title": "[playlist] 오늘은 조금 가벼워져 | 밤에 듣는 힙합 노래"},
        tracks=[SimpleNamespace(title="가벼워져", prompt="", metadata_json={"style": "Korean hip-hop"})],
    )

    assert classification.style_lane == "mainstream Korean hip-hop / rap-pop"
    assert classification.playlist_titles == ("노래",)


def test_bulsong_hidden_source_context_does_not_force_archive_playlist() -> None:
    classification = infer_channel_genre_classification(
        {
            "youtube_channel_title": "불송",
            "youtube_title": "[playlist] 다시 웃을 수 있게 | 지친 밤에 듣는 R&B 노래",
            "description": "Internal note: inspired by the Dhammapada.",
        },
    )

    assert classification.playlist_titles == ("노래",)
