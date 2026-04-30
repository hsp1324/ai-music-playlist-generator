from types import SimpleNamespace

import httpx
import pytest

from scripts.openclaw_release import (
    JAPAN_YOUTUBE_CHANNEL_TITLE,
    DEFAULT_YOUTUBE_CHANNEL_TITLE,
    auto_publish_playlist,
    infer_youtube_channel_title,
    release_has_uploaded_cover,
    release_has_uploaded_thumbnail,
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
        "tags": "",
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
    assert infer_youtube_channel_title(
        _auto_publish_args(
            "/tmp/audio.mp3",
            release_title="Tokyo Night",
            youtube_channel_title="Soft Hour Radio",
        )
    ) == DEFAULT_YOUTUBE_CHANNEL_TITLE


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
