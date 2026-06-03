from app.utils.short_track_observations import (
    annotate_short_track_metadata,
    record_playlist_short_track_observation,
)


def test_annotate_short_track_metadata_records_under_two_minutes() -> None:
    metadata = annotate_short_track_metadata(
        {"source": "manual-upload", "style": "dance pop", "tags": "pop"},
        duration_seconds=88,
        title="Short Hook",
        track_id="track-1",
        prompt="bright chorus",
        style="dance pop",
        tags="pop",
        lyrics="line one",
        source="manual-upload",
        context="track_intake",
    )

    assert metadata["short_track_under_120_seconds"] is True
    assert metadata["short_track_duration_seconds"] == 88
    assert metadata["short_track_duration_bucket"] == "60_to_119_seconds"
    assert metadata["short_track_observation"]["track_id"] == "track-1"
    assert metadata["short_track_observation"]["style"] == "dance pop"


def test_annotate_short_track_metadata_ignores_two_minutes_or_more() -> None:
    metadata = annotate_short_track_metadata(
        {"short_track_under_120_seconds": True, "short_track_observation": {"track_id": "old"}},
        duration_seconds=130,
        title="Longer Song",
        context="track_intake",
    )

    assert "short_track_under_120_seconds" not in metadata
    assert "short_track_observation" not in metadata


def test_record_playlist_short_track_observation_counts_unique_tracks() -> None:
    track_meta = annotate_short_track_metadata(
        {},
        duration_seconds=75,
        title="Short Hook",
        track_id="track-1",
        context="playlist_assignment",
    )
    observation = track_meta["short_track_observation"]

    metadata = record_playlist_short_track_observation(
        {},
        observation,
        playlist_id="release-1",
        playlist_title="Release",
        channel_title="sundaze",
        actor="openclaw",
    )
    metadata = record_playlist_short_track_observation(
        metadata,
        observation,
        playlist_id="release-1",
        playlist_title="Release",
        channel_title="sundaze",
        actor="openclaw",
    )

    assert metadata["short_track_under_120_count"] == 1
    assert metadata["short_track_under_120_bucket_counts"] == {"60_to_119_seconds": 1}
    assert metadata["short_track_observations"][0]["playlist_id"] == "release-1"
