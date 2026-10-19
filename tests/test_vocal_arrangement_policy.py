from app.models.playlist import Playlist, PlaylistItem
from app.models.track import Track
from app.utils.vocal_arrangement_policy import (
    ACOUSTIC_GUITAR_ONLY_VOCAL,
    MIXED_VOCAL_ARRANGEMENT,
    ORCHESTRAL_VOCAL,
    PIANO_ONLY_VOCAL,
    infer_orchestral_theme,
    infer_vocal_arrangement_family,
)
from app.workflows.playlist_automation import _reuse_candidate_matches_vocal_arrangement_policy


def _track(*, style: str, lyrics: str = "Verse one\nChorus line") -> Track:
    return Track(
        title="Policy track",
        prompt=style,
        duration_seconds=240,
        metadata_json={"style": style, "lyrics": lyrics},
    )


def _playlist_with_track(track: Track) -> Playlist:
    playlist = Playlist(title="New vocal release", target_duration_seconds=600)
    playlist.items = [PlaylistItem(track=track, order_index=1, included_duration_seconds=240)]
    return playlist


def test_infers_only_the_three_supported_vocal_arrangement_families() -> None:
    assert (
        infer_vocal_arrangement_family(["Nordic cinematic orchestral vocal song"])
        == ORCHESTRAL_VOCAL
    )
    assert (
        infer_vocal_arrangement_family(["solo acoustic grand piano accompaniment only"])
        == PIANO_ONLY_VOCAL
    )
    assert (
        infer_vocal_arrangement_family(["one steel-string acoustic guitar accompaniment only"])
        == ACOUSTIC_GUITAR_ONLY_VOCAL
    )
    assert (
        infer_vocal_arrangement_family(
            ["orchestral vocal song with acoustic guitar accompaniment only"]
        )
        == MIXED_VOCAL_ARRANGEMENT
    )


def test_orchestral_reuse_requires_vocals_and_the_same_theme() -> None:
    target = _playlist_with_track(_track(style="Nordic cinematic orchestral vocal song"))

    assert _reuse_candidate_matches_vocal_arrangement_policy(
        target_playlist=target,
        track=_track(style="Nordic cinematic orchestral vocal song, full symphony orchestra"),
    )
    assert not _reuse_candidate_matches_vocal_arrangement_policy(
        target_playlist=target,
        track=_track(style="medieval cinematic orchestral vocal song, full symphony orchestra"),
    )
    assert not _reuse_candidate_matches_vocal_arrangement_policy(
        target_playlist=target,
        track=_track(style="Nordic cinematic orchestral vocal song", lyrics="[Instrumental]"),
    )
    assert infer_orchestral_theme(["Nordic cinematic orchestral vocal song"]) == "nordic"


def test_piano_only_reuse_rejects_legacy_full_band_vocals() -> None:
    target = _playlist_with_track(_track(style="solo acoustic piano accompaniment only"))

    assert _reuse_candidate_matches_vocal_arrangement_policy(
        target_playlist=target,
        track=_track(style="intimate piano-only vocal, voice and piano only"),
    )
    assert not _reuse_candidate_matches_vocal_arrangement_policy(
        target_playlist=target,
        track=_track(style="K-pop R&B vocal, drums, bass, and synth pads"),
    )
