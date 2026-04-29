from app.config import Settings
from app.models.playlist import Playlist
from app.models.track import Track
from app.services.release_metadata_service import ReleaseMetadataService
from app.workflows.playlist_automation import _normalize_youtube_tags


def test_cafe_piano_metadata_includes_timestamped_tracklist() -> None:
    service = ReleaseMetadataService(Settings())
    playlist = Playlist(
        title="카페 피아노 솔로 1시간 플레이리스트",
        metadata_json={
            "description": "카페에서 잔잔하게 흐르는 감미로운 솔로 피아노 후보 모음.",
            "workspace_mode": "playlist",
        },
    )
    tracks = [
        Track(title="Cinnamon Keys A", duration_seconds=202, metadata_json={"tags": "cafe, solo piano"}),
        Track(title="Cinnamon Keys B", duration_seconds=208, metadata_json={"tags": "cafe, solo piano"}),
        Track(title="Feltward Sonata A", duration_seconds=225, metadata_json={"tags": "cafe, solo piano"}),
    ]

    metadata = service.build_youtube_metadata(playlist, tracks)

    assert metadata.title == "조용한 카페 피아노 솔로 1시간 | 공부, 작업, 휴식할 때 듣는 잔잔한 플레이리스트"
    assert "공부 / 작업 / 독서 / 휴식 / 카페 분위기 / 조용한 배경음악" in metadata.description
    assert "00:00 Cinnamon Keys A" in metadata.description
    assert "03:22 Cinnamon Keys B" in metadata.description
    assert "06:50 Feltward Sonata A" in metadata.description
    assert "#Piano #CafePiano #StudyMusic #WorkMusic #RelaxingMusic #SoloPiano" in metadata.description
    assert metadata.tags == ["Piano", "CafePiano", "StudyMusic", "WorkMusic", "RelaxingMusic", "SoloPiano"]


def test_metadata_approval_accepts_comma_separated_tags() -> None:
    assert _normalize_youtube_tags("Piano, #CafePiano, StudyMusic, piano,  WorkMusic ") == [
        "Piano",
        "CafePiano",
        "StudyMusic",
        "WorkMusic",
    ]
