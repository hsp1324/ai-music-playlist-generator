import json
import subprocess
from pathlib import Path

from app.config import Settings
from app.models.playlist import Playlist
from app.models.track import Track
from app.services.codex_metadata_service import CodexMetadataService
from app.services.release_metadata_service import ReleaseMetadataService
from app.workflows.playlist_automation import _normalize_youtube_tags
from scripts.openclaw_release import release_timeline


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
    assert "00:00 Cinnamon Keys - Morning" in metadata.description
    assert "03:22 Cinnamon Keys - Evening" in metadata.description
    assert "06:50 Feltward Sonata" in metadata.description
    assert "Cinnamon Keys A" not in metadata.description
    assert "#Piano #CafePiano #StudyMusic #WorkMusic #RelaxingMusic #SoloPiano" in metadata.description
    assert metadata.tags == ["Piano", "CafePiano", "StudyMusic", "WorkMusic", "RelaxingMusic", "SoloPiano"]


def test_metadata_approval_accepts_comma_separated_tags() -> None:
    assert _normalize_youtube_tags("Piano, #CafePiano, StudyMusic, piano,  WorkMusic ") == [
        "Piano",
        "CafePiano",
        "StudyMusic",
        "WorkMusic",
    ]


def test_openclaw_metadata_context_timeline_uses_final_order() -> None:
    timeline = release_timeline(
        {
            "tracks": [
                {"title": "Cinnamon Keys A", "duration_seconds": 202},
                {"title": "Cinnamon Keys B", "duration_seconds": 208},
                {"title": "Feltward Sonata A", "duration_seconds": 225},
            ]
        }
    )

    assert [item["start"] for item in timeline] == ["00:00", "03:22", "06:50"]
    assert [item["title"] for item in timeline] == ["Cinnamon Keys A", "Cinnamon Keys B", "Feltward Sonata A"]
    assert [item["display_title_hint"] for item in timeline] == [
        "Cinnamon Keys - Morning",
        "Cinnamon Keys - Evening",
        "Feltward Sonata",
    ]


def test_codex_metadata_service_uses_codex_json(monkeypatch) -> None:
    settings = Settings(codex_metadata_enabled=True)
    service = CodexMetadataService(settings, ReleaseMetadataService(settings))
    playlist = Playlist(
        id="release-1",
        title="카페 피아노",
        actual_duration_seconds=202,
        target_duration_seconds=3600,
        metadata_json={"workspace_mode": "playlist", "description": "잔잔한 카페 피아노"},
    )
    tracks = [Track(title="Cinnamon Keys A", duration_seconds=202, metadata_json={"tags": "piano,cafe"})]

    monkeypatch.setattr("app.services.codex_metadata_service.shutil.which", lambda command: "/usr/bin/codex")

    def fake_run(cmd, input, **kwargs):
        output_path = Path(cmd[cmd.index("-o") + 1])
        assert "--output-schema" in cmd
        assert "00:00 Cinnamon Keys A" in input
        assert "🎧 Recommended for" in input
        assert "do not append 'Official AI Visualizer'" in input
        assert "Never swap timestamps between tracks" in input
        assert "Do not show trailing A/B labels" in input
        assert "display_title_hint" in input
        output_path.write_text(
            json.dumps(
                {
                    "title": "조용한 카페 피아노",
                    "description": "잔잔한 피아노입니다.\n\n00:00 Cinnamon Keys A",
                    "tags": ["Piano", "#CafePiano", "Piano"],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr("app.services.codex_metadata_service.subprocess.run", fake_run)

    metadata = service.build_youtube_metadata(playlist, tracks)

    assert metadata.provider == "codex"
    assert metadata.error is None
    assert metadata.title == "조용한 카페 피아노"
    assert "00:00 Cinnamon Keys" in metadata.description
    assert "Cinnamon Keys A" not in metadata.description
    assert metadata.tags == ["Piano", "CafePiano"]


def test_codex_metadata_service_falls_back_when_cli_fails(monkeypatch) -> None:
    settings = Settings(codex_metadata_enabled=True)
    service = CodexMetadataService(settings, ReleaseMetadataService(settings))
    playlist = Playlist(
        id="release-1",
        title="카페 피아노",
        actual_duration_seconds=202,
        target_duration_seconds=3600,
        metadata_json={"workspace_mode": "playlist", "description": "잔잔한 카페 피아노"},
    )
    tracks = [Track(title="Cinnamon Keys A", duration_seconds=202, metadata_json={"tags": "piano,cafe"})]

    monkeypatch.setattr("app.services.codex_metadata_service.shutil.which", lambda command: "/usr/bin/codex")

    def fake_run(cmd, input, **kwargs):
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=kwargs.get("timeout"))

    monkeypatch.setattr("app.services.codex_metadata_service.subprocess.run", fake_run)

    metadata = service.build_youtube_metadata(playlist, tracks)

    assert metadata.provider == "template"
    assert "Codex metadata generation failed" in (metadata.error or "")
    assert "00:00 Cinnamon Keys" in metadata.description
    assert "Cinnamon Keys A" not in metadata.description
