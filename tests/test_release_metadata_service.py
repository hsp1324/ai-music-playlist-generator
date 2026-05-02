import json
import subprocess
from pathlib import Path

from app.config import Settings
from app.models.playlist import Playlist
from app.models.track import Track
from app.services.codex_metadata_service import CodexMetadataService
from app.services.release_metadata_service import ReleaseMetadataService
from app.utils.youtube_localizations import normalize_youtube_localizations, sanitize_youtube_copy
from app.workflows.playlist_automation import _normalize_youtube_tags
from scripts.openclaw_release import release_timeline
from app.utils.track_titles import upload_track_title


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
    assert "00:00 Cinnamon Pulse" in metadata.description
    assert "03:22 Cinnamon Bloom" in metadata.description
    assert "06:50 Feltward Silverline" in metadata.description
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


def test_korean_youtube_copy_avoids_instrumental_transliteration() -> None:
    assert sanitize_youtube_copy("숲길 산책 J-pop 감성 인스트루멘털 플레이리스트") == "숲길 산책 J-pop 감성 BGM 플레이리스트"
    localizations = normalize_youtube_localizations(
        {
            "ko": {
                "title": "해변 산책 인스투르멘털 1시간",
                "description": "가사가 없는 인스트루멘털 음악입니다.",
            }
        }
    )

    assert localizations["ko"]["title"] == "해변 산책 BGM 1시간"
    assert localizations["ko"]["description"] == "가사가 없는 BGM입니다."


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
        "Cinnamon Pulse",
        "Cinnamon Bloom",
        "Feltward Silverline",
    ]


def test_openclaw_metadata_context_uses_hhmmss_for_one_hour_plus_release() -> None:
    timeline = release_timeline(
        {
            "tracks": [
                {"title": "First Track", "duration_seconds": 3595},
                {"title": "Second Track", "duration_seconds": 130},
                {"title": "Third Track", "duration_seconds": 60},
            ]
        }
    )

    assert [item["start"] for item in timeline] == ["00:00:00", "00:59:55", "01:02:05"]


def test_template_metadata_uses_hhmmss_for_one_hour_plus_tracklist() -> None:
    service = ReleaseMetadataService(Settings())
    playlist = Playlist(
        title="카페 피아노 솔로 1시간 플레이리스트",
        metadata_json={
            "description": "카페에서 잔잔하게 흐르는 감미로운 솔로 피아노 후보 모음.",
            "workspace_mode": "playlist",
        },
    )
    tracks = [
        Track(title="Cinnamon Keys A", duration_seconds=3595, metadata_json={"tags": "cafe, solo piano"}),
        Track(title="Cinnamon Keys B", duration_seconds=130, metadata_json={"tags": "cafe, solo piano"}),
        Track(title="Feltward Sonata A", duration_seconds=60, metadata_json={"tags": "cafe, solo piano"}),
    ]

    metadata = service.build_youtube_metadata(playlist, tracks)

    assert "00:00:00 " in metadata.description
    assert "00:59:55 " in metadata.description
    assert "01:02:05 " in metadata.description


def test_title_cleanup_rewrites_pair_labels_without_trimming_normal_words() -> None:
    assert upload_track_title("Highway Saffron - Morning") == "Saffron Afterglow"
    assert upload_track_title("Highway Saffron - Evening") == "Saffron Current"
    assert upload_track_title("Song 1") != "Song"
    assert upload_track_title("Song 2") != "Song"
    assert upload_track_title("Samba") == "Samba"


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
        assert "Do not show A/B, 1/2, or artificial pair labels" in input
        assert "display_title_hint" in input
        assert "write as one standalone song/release" in input
        assert "Use prompt, style, tags, and lyrics as private creative context" in input
        assert "timeline_timestamp_format" in input
        assert "Japanese title plus Korean translation in parentheses" in input
        assert "never use the transliterated words" in input
        assert "listening use cases directly in the title" in input
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
    assert "00:00 Cinnamon Pulse" in metadata.description
    assert "Cinnamon Keys A" not in metadata.description
    assert metadata.tags == ["Piano", "CafePiano"]


def test_codex_metadata_service_normalizes_one_hour_timestamps_and_localizations(monkeypatch) -> None:
    settings = Settings(codex_metadata_enabled=True)
    service = CodexMetadataService(settings, ReleaseMetadataService(settings))
    playlist = Playlist(
        id="release-1",
        title="해변 산책 J-POP 1시간 플레이리스트",
        actual_duration_seconds=3665,
        target_duration_seconds=3600,
        metadata_json={"workspace_mode": "playlist", "description": "상쾌한 일본어 J-pop"},
    )
    tracks = [
        Track(title="Beach Song A", duration_seconds=3605, metadata_json={"tags": "jpop", "lyrics": "lyrics"}),
        Track(title="Beach Song B", duration_seconds=60, metadata_json={"tags": "jpop", "lyrics": "lyrics"}),
    ]

    monkeypatch.setattr("app.services.codex_metadata_service.shutil.which", lambda command: "/usr/bin/codex")

    def fake_run(cmd, input, **kwargs):
        output_path = Path(cmd[cmd.index("-o") + 1])
        assert '"timeline_timestamp_format": "HH:MM:SS"' in input
        assert "00:00:00 Beach Song A" in input
        assert "01:00:05 Beach Song B" in input
        output_path.write_text(
            json.dumps(
                {
                    "title": "해변 산책 J-POP",
                    "description": "상쾌한 해변 산책곡입니다.\n\n0:00:00 Beach Song A\n1:00:05 Beach Song B",
                    "tags": ["Jpop", "Beach"],
                    "localizations": {
                        "ko": {
                            "title": "해변 산책 J-POP",
                            "description": "0:00:00 海辺の歌 (해변의 노래)\n1:00:05 夏の光 (여름의 빛)",
                        },
                        "ja": {
                            "title": "海辺散歩J-POP",
                            "description": "0:00:00 海辺の歌\n1:00:05 夏の光",
                        },
                        "en": {
                            "title": "Seaside Walk J-Pop",
                            "description": "0:00:00 Seaside Song\n1:00:05 Summer Light",
                        },
                    },
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr("app.services.codex_metadata_service.subprocess.run", fake_run)

    metadata = service.build_youtube_metadata(playlist, tracks)

    assert "00:00:00 " in metadata.description
    assert "01:00:05 " in metadata.description
    assert "Beach Song A" not in metadata.description
    assert "Beach Song B" not in metadata.description
    assert "00:00:00 海辺の歌 (해변의 노래)" in metadata.localizations["ko"]["description"]
    assert "01:00:05 夏の光" in metadata.localizations["ja"]["description"]
    assert "01:00:05 Summer Light" in metadata.localizations["en"]["description"]
    assert metadata.tags == ["Jpop", "Beach"]


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
    assert "00:00 Cinnamon Pulse" in metadata.description
    assert "Cinnamon Keys A" not in metadata.description
