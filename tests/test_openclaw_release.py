import json
from types import SimpleNamespace

import httpx
import pytest

import scripts.openclaw_release as openclaw_release
from scripts.openclaw_release import (
    CINEMATIC_PULSE_YOUTUBE_CHANNEL_TITLE,
    JAPAN_YOUTUBE_CHANNEL_TITLE,
    DEFAULT_YOUTUBE_CHANNEL_TITLE,
    HARUHARU_YOUTUBE_CHANNEL_TITLE,
    NEW_VERSE_YOUTUBE_CHANNEL_TITLE,
    SIGNAL_DESK_LEGACY_CHANNEL_TITLE,
    SIGNAL_ROOM_YOUTUBE_CHANNEL_TITLE,
    SOLWAVE_YOUTUBE_CHANNEL_TITLE,
    STORYLIGHT_YOUTUBE_CHANNEL_TITLE,
    SUNDAZE_YOUTUBE_CHANNEL_TITLE,
    approve_metadata,
    auto_publish_playlist,
    auto_publish_single,
    build_channel_profile,
    create_release,
    infer_youtube_channel_title,
    is_bulsong_channel_title,
    is_pop_family_vocal_request,
    release_has_uploaded_cover,
    release_has_uploaded_loop_video,
    release_has_uploaded_thumbnail,
    resolve_youtube_channel_id,
    resolve_lyrics_items,
    resolve_exclude_style_items,
    resolve_style_items,
    slack_notify_command,
    upload_audio_file_to_release,
    upload_loop_video,
    upload_single_candidates,
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
        "exclude_style": [],
        "tags": "",
        "lyrics": [],
        "lyrics_file": [],
        "target_seconds": 3600,
        "min_track_seconds": openclaw_release.DEFAULT_MIN_PLAYLIST_TRACK_SECONDS,
        "max_track_seconds": openclaw_release.DEFAULT_MAX_PLAYLIST_TRACK_SECONDS,
        "allow_short_track": False,
        "allow_long_track": False,
        "youtube_channel_title": "",
        "youtube_channel_id": "",
        "force_under_target": False,
        "allow_reupload": False,
        "actor": "openclaw:auto-playlist",
        "wait_timeout_seconds": 1,
        "poll_seconds": 0.01,
        "allow_generated_draft_cover": False,
        "thumbnail": "",
        "allow_cover_as_thumbnail": False,
        "loop_video": "",
        "loop_video_provider": "",
        "hard_loop_video": False,
        "allow_still_image_video": False,
        "allow_short_loop_video": False,
        "video_spectrum_overlay_style": "bars",
        "video_render_resolution": "720p",
        "video_render_source_mode": "auto",
        "lyrics_overlay": False,
        "lyrics_alignment_mode": "whisper",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_playlist_track_duration_allows_two_minute_tracks_by_default() -> None:
    args = _auto_publish_args("song.mp3")

    openclaw_release.require_playlist_track_duration(
        {"title": "Short Pop", "duration_seconds": 150},
        args=args,
        context="duration check",
    )


def test_playlist_track_duration_rejects_under_two_minutes_by_default() -> None:
    args = _auto_publish_args("song.mp3")

    with pytest.raises(RuntimeError, match="at least 02:00"):
        openclaw_release.require_playlist_track_duration(
            {"title": "Too Short Pop", "duration_seconds": 59},
            args=args,
            context="duration check",
        )


def test_playlist_track_duration_rejects_short_tracks_when_min_configured() -> None:
    args = _auto_publish_args("song.mp3", min_track_seconds=180)

    with pytest.raises(RuntimeError, match="at least 03:00"):
        openclaw_release.require_playlist_track_duration(
            {"title": "Short Pop", "duration_seconds": 150},
            args=args,
            context="duration check",
        )


def test_playlist_track_duration_allows_short_tracks_with_explicit_flag() -> None:
    args = _auto_publish_args("song.mp3", allow_short_track=True)

    openclaw_release.require_playlist_track_duration(
        {"title": "Short Pop", "duration_seconds": 59},
        args=args,
        context="duration check",
    )


def test_playlist_track_duration_allows_long_tracks_for_soft_hour() -> None:
    args = _auto_publish_args("song.mp3", youtube_channel_title=DEFAULT_YOUTUBE_CHANNEL_TITLE)

    openclaw_release.require_playlist_track_duration(
        {"title": "Long Ambient Cue", "duration_seconds": 286},
        args=args,
        context="duration check",
    )


def test_playlist_track_duration_allows_long_tracks_for_cinematic_pulse() -> None:
    args = _auto_publish_args("song.mp3", youtube_channel_title=CINEMATIC_PULSE_YOUTUBE_CHANNEL_TITLE)

    openclaw_release.require_playlist_track_duration(
        {"title": "Long Cinematic Cue", "duration_seconds": 286},
        args=args,
        context="duration check",
    )


def test_playlist_track_duration_uses_existing_release_channel_for_long_track_exemption() -> None:
    args = _auto_publish_args("song.mp3", youtube_channel_title="")

    openclaw_release.require_playlist_track_duration(
        {"title": "Long Existing Cinematic Cue", "duration_seconds": 286},
        args=args,
        context="duration check",
        release={"target_youtube_channel_title": CINEMATIC_PULSE_YOUTUBE_CHANNEL_TITLE},
    )


def test_playlist_track_duration_rejects_long_tracks_for_non_exempt_channels() -> None:
    args = _auto_publish_args("song.mp3", youtube_channel_title=JAPAN_YOUTUBE_CHANNEL_TITLE)

    with pytest.raises(RuntimeError, match="04:20 or shorter"):
        openclaw_release.require_playlist_track_duration(
            {"title": "Long J-pop Track", "duration_seconds": 286},
            args=args,
            context="duration check",
        )


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


def test_bulsong_channel_title_matches_current_and_legacy_names() -> None:
    assert is_bulsong_channel_title(NEW_VERSE_YOUTUBE_CHANNEL_TITLE)
    assert is_bulsong_channel_title("Bulsong")
    assert is_bulsong_channel_title("The New Verse")
    assert not is_bulsong_channel_title(DEFAULT_YOUTUBE_CHANNEL_TITLE)


def test_release_has_uploaded_loop_video_requires_manual_upload_source() -> None:
    assert release_has_uploaded_loop_video(
        {
            "loop_video_path": "/tmp/loop.mp4",
            "loop_video_source": "manual-upload",
        }
    )
    assert not release_has_uploaded_loop_video({"loop_video_path": "/tmp/loop.mp4"})


def test_require_normal_loop_video_duration_allows_short_gemini_clip(monkeypatch, tmp_path) -> None:
    loop_video = tmp_path / "gemini-short.mp4"
    loop_video.write_bytes(b"fake mp4")
    monkeypatch.setattr(openclaw_release, "probe_media_duration_seconds", lambda _path: 5.0)

    openclaw_release.require_normal_loop_video_duration(
        loop_video,
        SimpleNamespace(allow_short_loop_video=False),
        context="auto-publish-playlist",
    )


def test_require_normal_loop_video_duration_allows_explicit_short_override(monkeypatch, tmp_path) -> None:
    loop_video = tmp_path / "intentional-short.mp4"
    loop_video.write_bytes(b"fake mp4")
    monkeypatch.setattr(openclaw_release, "probe_media_duration_seconds", lambda _path: 5.0)

    openclaw_release.require_normal_loop_video_duration(
        loop_video,
        SimpleNamespace(allow_short_loop_video=True),
        context="upload-loop-video",
    )


def test_upload_loop_video_sends_provider_tag(tmp_path) -> None:
    loop_video = tmp_path / "gemini-loop.mp4"
    loop_video.write_bytes(b"fake mp4")
    captured_bodies: list[bytes] = []
    release = {
        "id": "release-1",
        "title": "Storylight Test",
        "workflow_state": "audio_ready",
        "loop_video_path": None,
        "loop_video_source": None,
        "loop_video_provider": None,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and request.url.path.endswith("/playlists/workspaces/release-1"):
            return httpx.Response(200, json=release)
        if request.method == "GET" and request.url.path.endswith("/playlists/workspaces"):
            return httpx.Response(200, json=[release])
        if request.method == "POST" and request.url.path.endswith("/playlists/release-1/loop-video/upload"):
            captured_bodies.append(request.read())
            uploaded = {
                **release,
                "loop_video_path": "/tmp/uploaded-loop.mp4",
                "loop_video_source": "manual-upload",
                "loop_video_provider": "gemini",
                "loop_video_smooth": True,
            }
            return httpx.Response(200, json=uploaded)
        return httpx.Response(500, json={"detail": "unexpected request"})

    client = httpx.Client(base_url="http://test/api", transport=httpx.MockTransport(handler))
    result = upload_loop_video(
        client,
        SimpleNamespace(
            release_id="release-1",
            release_title="",
            loop_video=str(loop_video),
            loop_video_provider="gemini",
            hard_loop=False,
            allow_short_loop_video=True,
            actor="openclaw",
        ),
    )

    assert captured_bodies
    assert b'name="loop_video_provider"' in captured_bodies[-1]
    assert b"gemini" in captured_bodies[-1]
    assert result["release"]["loop_video_provider"] == "gemini"


def test_infer_youtube_channel_routes_jpop_releases_to_tokyo_daydream() -> None:
    assert infer_youtube_channel_title(
        _auto_publish_args(
            "/tmp/audio.mp3",
            release_title="Tokyo Night City Pop",
            description="J-pop night drive playlist",
        )
    ) == JAPAN_YOUTUBE_CHANNEL_TITLE
    assert infer_youtube_channel_title(
        _auto_publish_args(
            "/tmp/audio.mp3",
            release_title="Japanese Dance Pop",
            description="mainstream vocal pop playlist",
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
            release_title="Japanese Lofi Cafe BGM",
            description="instrumental study background music",
        )
    ) == DEFAULT_YOUTUBE_CHANNEL_TITLE
    assert infer_youtube_channel_title(
        _auto_publish_args(
            "/tmp/audio.mp3",
            release_title="Summer Night English Pop",
            description="mainstream American pop playlist",
        )
    ) == SUNDAZE_YOUTUBE_CHANNEL_TITLE
    assert infer_youtube_channel_title(
        _auto_publish_args(
            "/tmp/audio.mp3",
            release_title="Verano Latino Reggaeton Pop",
            description="Spanish vocal pop playlist",
        )
    ) == SOLWAVE_YOUTUBE_CHANNEL_TITLE
    assert infer_youtube_channel_title(
        _auto_publish_args(
            "/tmp/audio.mp3",
            release_title="Mystery Documentary BGM",
            description="dark ambient investigation music for story videos",
        )
    ) == STORYLIGHT_YOUTUBE_CHANNEL_TITLE
    assert infer_youtube_channel_title(
        _auto_publish_args(
            "/tmp/audio.mp3",
            release_title="Signal Desk Documentary BGM",
        )
    ) == STORYLIGHT_YOUTUBE_CHANNEL_TITLE
    assert infer_youtube_channel_title(
        _auto_publish_args(
            "/tmp/audio.mp3",
            release_title="Cute Arcade Game OST",
            description="playful no-vocal anime game BGM for a fantasy game menu",
        )
    ) == STORYLIGHT_YOUTUBE_CHANNEL_TITLE
    assert infer_youtube_channel_title(
        _auto_publish_args(
            "/tmp/audio.mp3",
            release_title="Fantasy RPG Menu Music",
            youtube_channel_title=STORYLIGHT_YOUTUBE_CHANNEL_TITLE,
        )
    ) == STORYLIGHT_YOUTUBE_CHANNEL_TITLE


def test_channel_profile_returns_doc_for_inferred_and_explicit_channels() -> None:
    tokyo = build_channel_profile(
        _auto_publish_args(
            "/tmp/audio.mp3",
            release_title="Tokyo Night City Pop",
            description="Japanese city pop playlist",
        )
    )
    assert tokyo["youtube_channel_title"] == JAPAN_YOUTUBE_CHANNEL_TITLE
    assert tokyo["profile"] == "tokyo-daydream-radio"
    assert tokyo["profile_doc"] == "docs/openclaw-channel-profiles/tokyo-daydream-radio.md"
    assert tokyo["concept_doc"] == "docs/openclaw-channel-concepts/tokyo-daydream-radio.md"
    assert tokyo["explicit_channel_requested"] is False

    soft_hour = build_channel_profile(
        _auto_publish_args(
            "/tmp/audio.mp3",
            release_title="Tokyo Night City Pop",
            youtube_channel_title="Soft Hour Radio",
        )
    )
    assert soft_hour["youtube_channel_title"] == DEFAULT_YOUTUBE_CHANNEL_TITLE
    assert soft_hour["profile"] == "soft-hour-radio"
    assert soft_hour["profile_doc"] == "docs/openclaw-channel-profiles/soft-hour-radio.md"
    assert soft_hour["concept_doc"] == "docs/openclaw-channel-concepts/soft-hour-radio.md"
    assert soft_hour["explicit_channel_requested"] is True

    sundaze = build_channel_profile(
        _auto_publish_args(
            "/tmp/audio.mp3",
            release_title="Summer Night English Pop",
            description="American pop playlist",
        )
    )
    assert sundaze["youtube_channel_title"] == SUNDAZE_YOUTUBE_CHANNEL_TITLE
    assert sundaze["profile"] == "sundaze"
    assert sundaze["profile_doc"] == "docs/openclaw-channel-profiles/sundaze.md"
    assert sundaze["concept_doc"] == "docs/openclaw-channel-concepts/sundaze.md"

    solwave = build_channel_profile(
        _auto_publish_args(
            "/tmp/audio.mp3",
            release_title="Verano Latino Reggaeton Pop",
            description="Spanish vocal pop playlist",
        )
    )
    assert solwave["youtube_channel_title"] == SOLWAVE_YOUTUBE_CHANNEL_TITLE
    assert solwave["profile"] == "solwave-radio"
    assert solwave["profile_doc"] == "docs/openclaw-channel-profiles/solwave-radio.md"
    assert solwave["concept_doc"] == "docs/openclaw-channel-concepts/solwave-radio.md"

    haruharu = build_channel_profile(
        _auto_publish_args(
            "/tmp/audio.mp3",
            release_title="Rainy Seoul K-pop Mix",
            description="Korean pop playlist with lyrics",
        )
    )
    assert haruharu["youtube_channel_title"] == HARUHARU_YOUTUBE_CHANNEL_TITLE
    assert haruharu["profile"] == "haruharu"
    assert haruharu["profile_doc"] == "docs/openclaw-channel-profiles/haruharu.md"
    assert haruharu["concept_doc"] == "docs/openclaw-channel-concepts/haruharu.md"

    storylight_from_signal = build_channel_profile(
        _auto_publish_args(
            "/tmp/audio.mp3",
            release_title="AI Debate Prep BGM",
            description="research story documentary music",
        )
    )
    assert storylight_from_signal["youtube_channel_title"] == STORYLIGHT_YOUTUBE_CHANNEL_TITLE
    assert storylight_from_signal["profile"] == "storylight-ost"
    assert storylight_from_signal["profile_doc"] == "docs/openclaw-channel-profiles/storylight-ost.md"
    assert storylight_from_signal["concept_doc"] == "docs/openclaw-channel-concepts/storylight-ost.md"

    custom = build_channel_profile(
        _auto_publish_args(
            "/tmp/audio.mp3",
            release_title="New Channel Playlist",
            youtube_channel_title="Future Pop Radio",
        )
    )
    assert custom["youtube_channel_title"] == "Future Pop Radio"
    assert custom["profile"] == "custom-channel"
    assert custom["profile_doc"] == "docs/openclaw-channel-profiles/custom-channel.md"
    assert custom["concept_doc"] == "docs/openclaw-channel-concepts/custom-channel.md"
    assert custom["explicit_channel_requested"] is True


def test_resolve_youtube_channel_id_uses_signal_room_legacy_alias() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/youtube/status"
        return httpx.Response(
            200,
            json={
                "channels": [
                    {"id": "legacy-signal-desk", "title": SIGNAL_DESK_LEGACY_CHANNEL_TITLE},
                    {"id": "soft-hour", "title": DEFAULT_YOUTUBE_CHANNEL_TITLE},
                ]
            },
        )

    client = httpx.Client(base_url="http://test/api", transport=httpx.MockTransport(handler))

    assert (
        resolve_youtube_channel_id(client, title=SIGNAL_ROOM_YOUTUBE_CHANNEL_TITLE)
        == "legacy-signal-desk"
    )


def test_slack_notify_command_posts_plain_message() -> None:
    captured_payloads = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_payloads.append(json.loads(request.read()))
        return httpx.Response(200, json={"ok": True, "channel": "C123", "ts": "1.2"})

    client = httpx.Client(base_url="http://test/api", transport=httpx.MockTransport(handler))
    result = slack_notify_command(
        client,
        SimpleNamespace(
            text="영상 만들기 실패해서 프롬프트를 수정해 다시 만듭니다. (1/10)",
            channel_id="C123",
            team_id="T123",
        ),
    )

    assert result["ok"] is True
    assert captured_payloads == [
        {
            "text": "영상 만들기 실패해서 프롬프트를 수정해 다시 만듭니다. (1/10)",
            "channel_id": "C123",
            "team_id": "T123",
        }
    ]


def test_create_release_creates_empty_workspace_before_suno_generation() -> None:
    captured_payloads = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_payloads.append(json.loads(request.read()))
        return httpx.Response(
            201,
            json={
                "id": "release-123",
                "title": "Night Walk J-pop",
                "workspace_mode": "single_track_video",
                "workflow_state": "collecting",
                "target_duration_seconds": 1,
            },
        )

    client = httpx.Client(base_url="http://test/api", transport=httpx.MockTransport(handler))
    result = create_release(
        client,
        SimpleNamespace(
            release_title="Night Walk J-pop",
            workspace_mode="single",
            target_seconds=3600,
            description="Create workspace before Suno generation.",
        ),
    )

    assert captured_payloads[-1]["workspace_mode"] == "single_track_video"
    assert captured_payloads[-1]["auto_publish_when_ready"] is False
    assert result["release"]["id"] == "release-123"
    assert "--release-id" in result["next"]


def test_create_release_uses_channel_aware_playlist_target_defaults() -> None:
    captured_payloads = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.read())
        captured_payloads.append(payload)
        return httpx.Response(
            201,
            json={
                "id": f"release-{len(captured_payloads)}",
                "title": payload["title"],
                "workspace_mode": "playlist",
                "workflow_state": "collecting",
                "target_duration_seconds": payload["target_duration_seconds"],
            },
        )

    client = httpx.Client(base_url="http://test/api", transport=httpx.MockTransport(handler))
    create_release(
        client,
        SimpleNamespace(
            release_title="Club Mix",
            workspace_mode="playlist",
            target_seconds=0,
            description="Create workspace before Suno generation.",
            youtube_channel_title="Club Bloom",
        ),
    )
    create_release(
        client,
        SimpleNamespace(
            release_title="Heart Sutra Songs",
            workspace_mode="playlist",
            target_seconds=0,
            description="Create workspace before Suno generation.",
            youtube_channel_title=NEW_VERSE_YOUTUBE_CHANNEL_TITLE,
        ),
    )

    assert captured_payloads[0]["target_duration_seconds"] == 900
    assert captured_payloads[1]["target_duration_seconds"] == 2400


def test_upload_single_candidates_can_target_existing_precreated_release(tmp_path) -> None:
    first_audio = tmp_path / "first.mp3"
    second_audio = tmp_path / "second.mp3"
    first_audio.write_bytes(b"fake mp3")
    second_audio.write_bytes(b"fake mp3")
    requested_paths = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        if request.method == "GET" and request.url.path.endswith("/playlists/workspaces/release-123"):
            return httpx.Response(
                200,
                json={
                    "id": "release-123",
                    "title": "Precreated Single",
                    "workspace_mode": "single_track_video",
                    "tracks": [{"id": "existing-track"}],
                },
            )
        if request.method == "GET" and request.url.path.endswith("/playlists/workspaces"):
            return httpx.Response(
                200,
                json=[
                    {
                        "id": "release-123",
                        "title": "Precreated Single",
                        "workspace_mode": "single_track_video",
                        "tracks": [{"id": "existing-track"}],
                    }
                ],
            )
        return httpx.Response(500, json={"detail": "unexpected request"})

    client = httpx.Client(base_url="http://test/api", transport=httpx.MockTransport(handler))

    with pytest.raises(RuntimeError, match="at most two candidate"):
        upload_single_candidates(
            client,
            SimpleNamespace(
                audio=[str(first_audio), str(second_audio)],
                title=[],
                cover=[],
                release_id="release-123",
                release_title="",
                prompt="cafe piano",
                style=[],
                tags="cafe,piano",
                lyrics=[],
                lyrics_file=[],
            ),
        )

    assert not any(path.endswith("/tracks/manual-upload") for path in requested_paths)


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


def test_resolve_exclude_style_items_allows_shared_and_per_track() -> None:
    assert resolve_exclude_style_items(2, exclude_styles=[]) == ["", ""]
    assert resolve_exclude_style_items(2, exclude_styles=["shared exclude"]) == [
        "shared exclude",
        "shared exclude",
    ]
    assert resolve_exclude_style_items(2, exclude_styles=["exclude one", "exclude two"]) == [
        "exclude one",
        "exclude two",
    ]
    with pytest.raises(RuntimeError, match="exactly one per --audio"):
        resolve_exclude_style_items(2, exclude_styles=["one", "two", "three"])


def test_upload_audio_file_retries_and_returns_probed_duration(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(openclaw_release.time, "sleep", lambda _seconds: None)
    audio_path = tmp_path / "retry.mp3"
    audio_path.write_bytes(b"fake mp3")
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        assert request.url.path.endswith("/tracks/manual-upload")
        body = request.read()
        assert b'name="exclude_style"' in body
        assert b"muddy vocals, heavy reverb" in body
        attempts += 1
        if attempts < 3:
            return httpx.Response(400, json={"detail": "Uploaded audio file is empty."})
        return httpx.Response(
            201,
            json={
                "id": "track-1",
                "title": "Retry Track",
                "status": "pending_review",
                "duration_seconds": 123,
                "metadata_json": {},
            },
        )

    client = httpx.Client(base_url="http://test/api", transport=httpx.MockTransport(handler))
    track = upload_audio_file_to_release(
        client,
        release_id="release-1",
        audio_path=audio_path,
        title="Retry Track",
        prompt="",
        tags="",
        exclude_style="muddy vocals, heavy reverb",
    )

    assert attempts == 3
    assert track["duration_seconds"] == 123


def test_pop_family_vocal_detection_allows_explicit_bgm_exception() -> None:
    assert is_pop_family_vocal_request("Tokyo J-pop single", "bright anime opening")
    assert is_pop_family_vocal_request("Summer English pop single", "mainstream American pop")
    assert is_pop_family_vocal_request("Verano Latino", "Spanish reggaeton pop")
    assert not is_pop_family_vocal_request("J-pop style BGM", "가사 없는 배경음악")


def test_approve_metadata_sends_language_localizations(tmp_path) -> None:
    ko_description = tmp_path / "ko.txt"
    ja_description = tmp_path / "ja.txt"
    en_description = tmp_path / "en.txt"
    es_description = tmp_path / "es.txt"
    ko_description.write_text("한국어 설명", encoding="utf-8")
    ja_description.write_text("日本語の説明", encoding="utf-8")
    en_description.write_text("English description", encoding="utf-8")
    es_description.write_text("Descripcion en espanol", encoding="utf-8")
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
                    "es": {"title": "Titulo en espanol", "description": "Descripcion en espanol"},
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
            es_title="Titulo en espanol",
            es_description="",
            es_description_file=str(es_description),
            actor="openclaw",
            note="",
        ),
    )

    payload = json.loads(captured_payloads[-1])
    assert payload["default_language"] == "ko"
    assert payload["localizations"]["ja"]["title"] == "日本語タイトル"
    assert payload["localizations"]["en"]["description"] == "English description"
    assert payload["localizations"]["es"]["title"] == "Titulo en espanol"
    assert result["release"]["youtube_localizations"]["ko"]["title"] == "한국어 제목"


def test_auto_publish_playlist_requires_final_cover_before_side_effects(tmp_path) -> None:
    audio_path = tmp_path / "track.mp3"
    audio_path.write_bytes(b"fake mp3")
    requested_paths = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        if request.method == "GET" and request.url.path.endswith("/playlists/workspaces/release-1"):
            return httpx.Response(
                200,
                json={
                    "id": "release-1",
                    "title": "Playlist",
                    "workspace_mode": "playlist",
                    "cover_image_path": None,
                    "cover_source": None,
                },
            )
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
        if request.method == "GET" and request.url.path.endswith("/playlists/workspaces/release-1"):
            return httpx.Response(
                200,
                json={
                    "id": "release-1",
                    "title": "Playlist",
                    "workspace_mode": "playlist",
                    "cover_image_path": "/tmp/final-cover.png",
                    "cover_source": "manual-upload",
                    "youtube_thumbnail_path": None,
                    "youtube_thumbnail_source": None,
                },
            )
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


def test_auto_publish_playlist_rejects_existing_youtube_video_without_allow_reupload(tmp_path) -> None:
    audio_path = tmp_path / "track.mp3"
    audio_path.write_bytes(b"fake mp3")
    requested_paths = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        if request.method == "GET" and request.url.path.endswith("/playlists/workspaces/release-1"):
            return httpx.Response(
                200,
                json={
                    "id": "release-1",
                    "title": "Playlist",
                    "workspace_mode": "playlist",
                    "youtube_video_id": "yt-existing",
                    "cover_image_path": "/tmp/final-cover.png",
                    "cover_source": "manual-upload",
                    "youtube_thumbnail_path": "/tmp/final-thumbnail.png",
                    "youtube_thumbnail_source": "manual-upload",
                },
            )
        if request.method == "GET" and request.url.path.endswith("/playlists/workspaces"):
            return httpx.Response(
                200,
                json=[
                    {
                        "id": "release-1",
                        "title": "Playlist",
                        "workspace_mode": "playlist",
                        "youtube_video_id": "yt-existing",
                        "cover_image_path": "/tmp/final-cover.png",
                        "cover_source": "manual-upload",
                        "youtube_thumbnail_path": "/tmp/final-thumbnail.png",
                        "youtube_thumbnail_source": "manual-upload",
                    }
                ],
            )
        return httpx.Response(500, json={"detail": "unexpected request"})

    client = httpx.Client(base_url="http://test/api", transport=httpx.MockTransport(handler))

    with pytest.raises(RuntimeError, match="already has YouTube video id yt-existing"):
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


def test_auto_publish_playlist_allows_bulsong_cover_as_thumbnail_before_creating_new_release(tmp_path) -> None:
    audio_path = tmp_path / "track.mp3"
    audio_path.write_bytes(b"fake mp3")
    cover_path = tmp_path / "cover.png"
    cover_path.write_bytes(b"fake cover")
    requested_paths = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        return httpx.Response(500, json={"detail": "unexpected request"})

    client = httpx.Client(base_url="http://test/api", transport=httpx.MockTransport(handler))

    with pytest.raises(RuntimeError, match="requires --loop-video"):
        auto_publish_playlist(
            client,
            _auto_publish_args(
                str(audio_path),
                release_id="",
                release_title="자비 명상 트립합",
                cover=str(cover_path),
                youtube_channel_title=NEW_VERSE_YOUTUBE_CHANNEL_TITLE,
            ),
        )

    assert requested_paths == []


def test_auto_publish_playlist_uploads_remaining_tracks_and_notifies_slack_on_failed_track(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(openclaw_release.time, "sleep", lambda _seconds: None)
    failed_audio = tmp_path / "failed.mp3"
    good_audio = tmp_path / "good.mp3"
    failed_audio.write_bytes(b"failed audio")
    good_audio.write_bytes(b"good audio")
    requested_paths = []
    failed_upload_attempts = 0
    render_requested = False
    slack_notices = []

    release = {
        "id": "release-1",
        "title": "Cafe BGM Playlist",
        "workspace_mode": "playlist",
        "workflow_state": "collecting",
        "cover_image_path": "/tmp/final-cover.png",
        "cover_source": "manual-upload",
        "youtube_thumbnail_path": "/tmp/thumb.png",
        "youtube_thumbnail_source": "manual-upload",
        "loop_video_path": "/tmp/loop.mp4",
        "loop_video_source": "manual-upload",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal failed_upload_attempts, render_requested
        requested_paths.append(request.url.path)
        if request.method == "GET" and request.url.path.endswith("/playlists/workspaces/release-1"):
            return httpx.Response(200, json=release)
        if request.method == "GET" and request.url.path.endswith("/playlists/workspaces"):
            return httpx.Response(200, json=[release])
        if request.method == "POST" and request.url.path.endswith("/tracks/manual-upload"):
            body = request.read()
            if b'filename="failed.mp3"' in body:
                failed_upload_attempts += 1
                return httpx.Response(400, json={"detail": "Uploaded audio file is empty."})
            return httpx.Response(
                201,
                json={
                        "id": "track-good",
                        "title": "Good Track",
                        "status": "pending_review",
                        "duration_seconds": 190,
                        "metadata_json": {},
                    },
                )
        if request.method == "POST" and request.url.path.endswith("/tracks/track-good/decisions"):
            return httpx.Response(
                200,
                json={
                        "id": "track-good",
                        "title": "Good Track",
                        "status": "approved",
                        "duration_seconds": 190,
                        "metadata_json": {},
                    },
                )
        if request.method == "POST" and request.url.path.endswith("/slack/notify"):
            slack_notices.append(json.loads(request.read())["text"])
            return httpx.Response(200, json={"ok": True})
        if request.method == "POST" and request.url.path.endswith("/playlists/release-1/render-audio"):
            render_requested = True
        return httpx.Response(500, json={"detail": "unexpected request"})

    client = httpx.Client(base_url="http://test/api", transport=httpx.MockTransport(handler))

    with pytest.raises(RuntimeError, match="1 audio upload"):
        auto_publish_playlist(
            client,
            _auto_publish_args(
                str(failed_audio),
                audio=[str(failed_audio), str(good_audio)],
                title=["Broken Track", "Good Track"],
                release_title="Cafe BGM Playlist",
                description="instrumental cafe BGM",
                tags="BGM,instrumental",
            ),
        )

    assert failed_upload_attempts == 3
    assert any(path.endswith("/tracks/track-good/decisions") for path in requested_paths)
    assert slack_notices
    assert "Broken Track" in slack_notices[-1]
    assert not render_requested


def test_auto_publish_playlist_rejects_tracks_longer_than_allowed_limit(tmp_path) -> None:
    audio_path = tmp_path / "long.mp3"
    audio_path.write_bytes(b"long audio")
    render_requested = False
    slack_notices = []

    release = {
        "id": "release-1",
        "title": "Cafe BGM Playlist",
        "workspace_mode": "playlist",
        "workflow_state": "collecting",
        "cover_image_path": "/tmp/final-cover.png",
        "cover_source": "manual-upload",
        "youtube_thumbnail_path": "/tmp/thumb.png",
        "youtube_thumbnail_source": "manual-upload",
        "loop_video_path": "/tmp/loop.mp4",
        "loop_video_source": "manual-upload",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal render_requested
        if request.method == "GET" and request.url.path.endswith("/playlists/workspaces/release-1"):
            return httpx.Response(200, json=release)
        if request.method == "GET" and request.url.path.endswith("/playlists/workspaces"):
            return httpx.Response(200, json=[release])
        if request.method == "POST" and request.url.path.endswith("/tracks/manual-upload"):
            return httpx.Response(
                201,
                json={
                    "id": "track-long",
                    "title": "Long Track",
                    "status": "pending_review",
                    "duration_seconds": 286,
                    "metadata_json": {},
                },
            )
        if request.method == "POST" and request.url.path.endswith("/slack/notify"):
            slack_notices.append(json.loads(request.read())["text"])
            return httpx.Response(200, json={"ok": True})
        if request.method == "POST" and request.url.path.endswith("/playlists/release-1/render-audio"):
            render_requested = True
        return httpx.Response(500, json={"detail": "unexpected request"})

    client = httpx.Client(base_url="http://test/api", transport=httpx.MockTransport(handler))

    with pytest.raises(RuntimeError, match="1 audio upload"):
        auto_publish_playlist(
            client,
            _auto_publish_args(
                str(audio_path),
                release_title="Cafe BGM Playlist",
                description="instrumental cafe BGM",
                tags="BGM,instrumental",
                youtube_channel_title=JAPAN_YOUTUBE_CHANNEL_TITLE,
            ),
        )

    assert not render_requested
    assert slack_notices
    assert "Long Track" in slack_notices[-1]
    assert "04:20 or shorter" in slack_notices[-1]


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


def test_auto_publish_single_allows_bulsong_cover_as_thumbnail_before_side_effects(tmp_path) -> None:
    audio_path = tmp_path / "track.mp3"
    audio_path.write_bytes(b"fake mp3")
    cover_path = tmp_path / "cover.png"
    cover_path.write_bytes(b"fake cover")
    requested_paths = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        return httpx.Response(500, json={"detail": "unexpected request"})

    client = httpx.Client(base_url="http://test/api", transport=httpx.MockTransport(handler))

    with pytest.raises(RuntimeError, match="requires --loop-video"):
        auto_publish_single(
            client,
            _auto_publish_args(
                str(audio_path),
                release_id="",
                release_title="자비 명상 트립합",
                cover=str(cover_path),
                actor="openclaw:auto-single",
                youtube_channel_title=NEW_VERSE_YOUTUBE_CHANNEL_TITLE,
            ),
        )

    assert requested_paths == []


def test_auto_publish_single_rejects_existing_youtube_video_without_allow_reupload(tmp_path) -> None:
    audio_path = tmp_path / "track.mp3"
    audio_path.write_bytes(b"fake mp3")
    requested_paths = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        if request.method == "GET" and request.url.path.endswith("/playlists/workspaces/release-1"):
            return httpx.Response(
                200,
                json={
                    "id": "release-1",
                    "title": "Single",
                    "workspace_mode": "single_track_video",
                    "youtube_video_id": "yt-existing",
                    "tracks": [],
                    "cover_image_path": "/tmp/final-cover.png",
                    "cover_source": "manual-upload",
                    "youtube_thumbnail_path": "/tmp/final-thumbnail.png",
                    "youtube_thumbnail_source": "manual-upload",
                },
            )
        if request.method == "GET" and request.url.path.endswith("/playlists/workspaces"):
            return httpx.Response(
                200,
                json=[
                    {
                        "id": "release-1",
                        "title": "Single",
                        "workspace_mode": "single_track_video",
                        "youtube_video_id": "yt-existing",
                        "tracks": [],
                        "cover_image_path": "/tmp/final-cover.png",
                        "cover_source": "manual-upload",
                        "youtube_thumbnail_path": "/tmp/final-thumbnail.png",
                        "youtube_thumbnail_source": "manual-upload",
                    }
                ],
            )
        return httpx.Response(500, json={"detail": "unexpected request"})

    client = httpx.Client(base_url="http://test/api", transport=httpx.MockTransport(handler))

    with pytest.raises(RuntimeError, match="already has YouTube video id yt-existing"):
        auto_publish_single(client, _auto_publish_args(str(audio_path), actor="openclaw:auto-single"))

    assert not any(path.endswith("/tracks/manual-upload") for path in requested_paths)


def test_auto_publish_single_requires_lyrics_for_jpop_before_side_effects(tmp_path) -> None:
    audio_path = tmp_path / "track.mp3"
    audio_path.write_bytes(b"fake mp3")
    cover_path = tmp_path / "cover.png"
    cover_path.write_bytes(b"fake cover")
    thumbnail_path = tmp_path / "thumb.png"
    thumbnail_path.write_bytes(b"fake thumb")
    requested_paths = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        return httpx.Response(500, json={"detail": "unexpected request"})

    client = httpx.Client(base_url="http://test/api", transport=httpx.MockTransport(handler))

    with pytest.raises(RuntimeError, match="lyrics are required"):
        auto_publish_single(
            client,
            _auto_publish_args(
                str(audio_path),
                release_id="",
                release_title="Tokyo Night J-pop Single",
                cover=str(cover_path),
                thumbnail=str(thumbnail_path),
                tags="Jpop,Tokyo",
                actor="openclaw:auto-single",
            ),
        )

    assert requested_paths == []
