import json
from types import SimpleNamespace

import httpx
import pytest

from scripts.openclaw_release import (
    JAPAN_YOUTUBE_CHANNEL_TITLE,
    DEFAULT_YOUTUBE_CHANNEL_TITLE,
    approve_metadata,
    auto_publish_playlist,
    auto_publish_single,
    infer_youtube_channel_title,
    release_has_uploaded_cover,
    release_has_uploaded_thumbnail,
    resolve_lyrics_items,
    resolve_style_items,
)


def _auto_publish_args(audio_path: str, **overrides):
    values = {
        "audio": [audio_path],
        "title": ["Standalone Track"],
        "cover": "",
        "release_id": "release-1",
        "release_title": "",
        "description": "",
        "prompt": "",
        "style": [],
        "tags": "",
        "lyrics": [],
        "lyrics_file": [],
        "target_seconds": 3600,
        "youtube_channel_title": "",
        "youtube_channel_id": "",
        "force_under_target": False,
        "actor": "openclaw:auto-playlist",
        "wait_timeout_seconds": 1,
        "poll_seconds": 0.01,
        "allow_generated_draft_cover": False,
        "thumbnail": "",
        "allow_cover_as_thumbnail": False,
        "loop_video": "",
        "hard_loop_video": False,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_release_has_uploaded_cover_requires_manual_upload_source() -> None:
    assert release_has_uploaded_cover(
        {
            "cover_image_path": "/tmp/final.png",
            "cover_source": "manual-upload",
        }
    )
    assert not release_has_uploaded_cover(
        {
            "cover_image_path": "/tmp/draft.png",
            "cover_source": "generated-draft",
        }
    )
    assert not release_has_uploaded_cover({"cover_image_path": "/tmp/unknown.png"})


def test_release_has_uploaded_thumbnail_requires_manual_upload_source() -> None:
    assert release_has_uploaded_thumbnail(
        {
            "youtube_thumbnail_path": "/tmp/thumb.png",
            "youtube_thumbnail_source": "manual-upload",
        }
    )
    assert not release_has_uploaded_thumbnail({"youtube_thumbnail_path": "/tmp/thumb.png"})


def test_infer_youtube_channel_routes_japanese_releases_to_tokyo_daydream() -> None:
    assert infer_youtube_channel_title(
        _auto_publish_args(
            "/tmp/audio.mp3",
            release_title="Tokyo Night City Pop",
            description="Japanese lofi playlist",
        )
    ) == JAPAN_YOUTUBE_CHANNEL_TITLE
    assert infer_youtube_channel_title(
        _auto_publish_args(
            "/tmp/audio.mp3",
            release_title="도쿄 감성 시티팝",
        )
    ) == JAPAN_YOUTUBE_CHANNEL_TITLE
    assert infer_youtube_channel_title(
        _auto_publish_args(
            "/tmp/audio.mp3",
            release_title="Cafe Piano",
        )
    ) == DEFAULT_YOUTUBE_CHANNEL_TITLE


def test_resolve_lyrics_items_allows_empty_shared_and_per_track(tmp_path) -> None:
    assert resolve_lyrics_items(2, lyrics=[], lyrics_files=[]) == ["", ""]
    assert resolve_lyrics_items(2, lyrics=["shared lyrics"], lyrics_files=[]) == ["shared lyrics", "shared lyrics"]
    assert resolve_lyrics_items(2, lyrics=["first", "second"], lyrics_files=[]) == ["first", "second"]

    lyrics_file = tmp_path / "lyrics.txt"
    lyrics_file.write_text("file lyrics\n", encoding="utf-8")
    assert resolve_lyrics_items(1, lyrics=[], lyrics_files=[str(lyrics_file)]) == ["file lyrics"]

    with pytest.raises(RuntimeError, match="exactly one per --audio"):
        resolve_lyrics_items(2, lyrics=["one", "two", "three"], lyrics_files=[])
    assert infer_youtube_channel_title(
        _auto_publish_args(
            "/tmp/audio.mp3",
            release_title="Tokyo Night",
            youtube_channel_title="Soft Hour Radio",
        )
    ) == DEFAULT_YOUTUBE_CHANNEL_TITLE


def test_resolve_style_items_allows_shared_and_per_track() -> None:
    assert resolve_style_items(2, styles=[]) == ["", ""]
    assert resolve_style_items(2, styles=["shared style"]) == ["shared style", "shared style"]
    assert resolve_style_items(2, styles=["style one", "style two"]) == ["style one", "style two"]
    with pytest.raises(RuntimeError, match="exactly one per --audio"):
        resolve_style_items(2, styles=["one", "two", "three"])


def test_approve_metadata_sends_language_localizations(tmp_path) -> None:
    ko_description = tmp_path / "ko.txt"
    ja_description = tmp_path / "ja.txt"
    en_description = tmp_path / "en.txt"
    ko_description.write_text("한국어 설명", encoding="utf-8")
    ja_description.write_text("日本語の説明", encoding="utf-8")
    en_description.write_text("English description", encoding="utf-8")
    captured_payloads = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_payloads.append(request.read())
        return httpx.Response(
            200,
            json={
                "id": "release-1",
                "title": "Release",
                "workflow_state": "publish_ready",
                "metadata_approved": True,
                "youtube_title": "한국어 제목",
                "youtube_description": "한국어 설명",
                "youtube_tags": ["Jpop"],
                "youtube_localizations": {
                    "ko": {"title": "한국어 제목", "description": "한국어 설명"},
                    "ja": {"title": "日本語タイトル", "description": "日本語の説明"},
                    "en": {"title": "English Title", "description": "English description"},
                },
            },
        )

    client = httpx.Client(base_url="http://test/api", transport=httpx.MockTransport(handler))
    result = approve_metadata(
        client,
        SimpleNamespace(
            release_id="release-1",
            release_title="",
            title="한국어 제목",
            description="",
            description_file=str(ko_description),
            tags="Jpop",
            ko_title="한국어 제목",
            ko_description="",
            ko_description_file=str(ko_description),
            ja_title="日本語タイトル",
            ja_description="",
            ja_description_file=str(ja_description),
            en_title="English Title",
            en_description="",
            en_description_file=str(en_description),
            actor="openclaw",
            note="",
        ),
    )

    payload = json.loads(captured_payloads[-1])
    assert payload["default_language"] == "ko"
    assert payload["localizations"]["ja"]["title"] == "日本語タイトル"
    assert payload["localizations"]["en"]["description"] == "English description"
    assert result["release"]["youtube_localizations"]["ko"]["title"] == "한국어 제목"


def test_auto_publish_playlist_requires_final_cover_before_side_effects(tmp_path) -> None:
    audio_path = tmp_path / "track.mp3"
    audio_path.write_bytes(b"fake mp3")
    requested_paths = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        if request.method == "GET" and request.url.path.endswith("/playlists/workspaces"):
            return httpx.Response(
                200,
                json=[
                    {
                        "id": "release-1",
                        "title": "Playlist",
                        "workspace_mode": "playlist",
                        "cover_image_path": None,
                        "cover_source": None,
                    }
                ],
            )
        return httpx.Response(500, json={"detail": "unexpected request"})

    client = httpx.Client(base_url="http://test/api", transport=httpx.MockTransport(handler))

    with pytest.raises(RuntimeError, match="requires a final 16:9 cover image"):
        auto_publish_playlist(client, _auto_publish_args(str(audio_path)))

    assert not any(path.endswith("/tracks/manual-upload") for path in requested_paths)


def test_auto_publish_playlist_requires_thumbnail_before_side_effects(tmp_path) -> None:
    audio_path = tmp_path / "track.mp3"
    audio_path.write_bytes(b"fake mp3")
    requested_paths = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        if request.method == "GET" and request.url.path.endswith("/playlists/workspaces"):
            return httpx.Response(
                200,
                json=[
                    {
                        "id": "release-1",
                        "title": "Playlist",
                        "workspace_mode": "playlist",
                        "cover_image_path": "/tmp/final-cover.png",
                        "cover_source": "manual-upload",
                        "youtube_thumbnail_path": None,
                        "youtube_thumbnail_source": None,
                    }
                ],
            )
        return httpx.Response(500, json={"detail": "unexpected request"})

    client = httpx.Client(base_url="http://test/api", transport=httpx.MockTransport(handler))

    with pytest.raises(RuntimeError, match="requires a YouTube thumbnail image"):
        auto_publish_playlist(client, _auto_publish_args(str(audio_path)))

    assert not any(path.endswith("/tracks/manual-upload") for path in requested_paths)


def test_auto_publish_playlist_requires_cover_before_creating_new_release(tmp_path) -> None:
    audio_path = tmp_path / "track.mp3"
    audio_path.write_bytes(b"fake mp3")
    requested_paths = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        return httpx.Response(500, json={"detail": "unexpected request"})

    client = httpx.Client(base_url="http://test/api", transport=httpx.MockTransport(handler))

    with pytest.raises(RuntimeError, match="requires --cover"):
        auto_publish_playlist(
            client,
            _auto_publish_args(
                str(audio_path),
                release_id="",
                release_title="New Playlist",
            ),
        )

    assert requested_paths == []


def test_auto_publish_playlist_requires_thumbnail_before_creating_new_release(tmp_path) -> None:
    audio_path = tmp_path / "track.mp3"
    audio_path.write_bytes(b"fake mp3")
    cover_path = tmp_path / "cover.png"
    cover_path.write_bytes(b"fake cover")
    requested_paths = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        return httpx.Response(500, json={"detail": "unexpected request"})

    client = httpx.Client(base_url="http://test/api", transport=httpx.MockTransport(handler))

    with pytest.raises(RuntimeError, match="requires --thumbnail"):
        auto_publish_playlist(
            client,
            _auto_publish_args(
                str(audio_path),
                release_id="",
                release_title="New Playlist",
                cover=str(cover_path),
            ),
        )

    assert requested_paths == []


def test_auto_publish_single_requires_final_cover_before_side_effects(tmp_path) -> None:
    audio_path = tmp_path / "track.mp3"
    audio_path.write_bytes(b"fake mp3")
    requested_paths = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        return httpx.Response(500, json={"detail": "unexpected request"})

    client = httpx.Client(base_url="http://test/api", transport=httpx.MockTransport(handler))

    with pytest.raises(RuntimeError, match="requires --cover"):
        auto_publish_single(
            client,
            _auto_publish_args(
                str(audio_path),
                release_id="",
                release_title="J-pop Single",
                actor="openclaw:auto-single",
            ),
        )

    assert requested_paths == []


def test_auto_publish_single_rejects_multiple_audio_paths(tmp_path) -> None:
    first_audio = tmp_path / "first.mp3"
    second_audio = tmp_path / "second.mp3"
    first_audio.write_bytes(b"fake mp3")
    second_audio.write_bytes(b"fake mp3")
    client = httpx.Client(base_url="http://test/api", transport=httpx.MockTransport(lambda request: httpx.Response(500)))

    with pytest.raises(RuntimeError, match="exactly one final song"):
        auto_publish_single(
            client,
            _auto_publish_args(
                str(first_audio),
                audio=[str(first_audio), str(second_audio)],
                actor="openclaw:auto-single",
            ),
        )


def test_auto_publish_single_requires_thumbnail_before_side_effects(tmp_path) -> None:
    audio_path = tmp_path / "track.mp3"
    audio_path.write_bytes(b"fake mp3")
    cover_path = tmp_path / "cover.png"
    cover_path.write_bytes(b"fake cover")
    requested_paths = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        return httpx.Response(500, json={"detail": "unexpected request"})

    client = httpx.Client(base_url="http://test/api", transport=httpx.MockTransport(handler))

    with pytest.raises(RuntimeError, match="requires --thumbnail"):
        auto_publish_single(
            client,
            _auto_publish_args(
                str(audio_path),
                release_id="",
                release_title="J-pop Single",
                cover=str(cover_path),
                actor="openclaw:auto-single",
            ),
        )

    assert requested_paths == []
