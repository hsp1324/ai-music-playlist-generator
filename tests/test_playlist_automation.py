import json
import os
import io
import hashlib
import time
import wave
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient
from google.oauth2.credentials import Credentials
from PIL import Image
from sqlalchemy import select

from app.config import Settings, get_settings
from app.db import SessionLocal
from app.main import create_app
from app.models.enums import JobStatus, JobType, PlaylistStatus, TrackStatus
from app.models.job import Job
from app.models.playlist import Playlist, PlaylistItem
from app.models.track import Track
from app.routes import playlists as playlist_routes
from app.routes.tracks import _extract_embedded_cover
from app.services.background_worker import BackgroundJobWorker, _is_long_video_verification_upload_error
from app.services import youtube_service as youtube_service_module
from app.services.youtube_service import YOUTUBE_THUMBNAIL_MAX_BYTES, YouTubeService
from app.utils.local_video_cleanup import cleanup_public_uploaded_local_videos
from app.utils.openclaw_slack_loop import (
    build_backlog_queue_request_message,
    handle_auto_loop_control_message,
    record_auto_loop_upload,
)
from app.utils.youtube_localizations import SUPPORTED_YOUTUBE_LANGUAGES
from app.workflows.playlist_automation import (
    next_youtube_scheduled_publish_at,
    reconcile_due_scheduled_youtube_public_states,
    scripture_youtube_playlist_titles,
    youtube_schedule_options_for_playlist,
)
from app.workflows.openclaw_runtime import (
    build_openclaw_backlog_summary,
    evaluate_openclaw_backlog_scheduler,
    record_openclaw_backlog_scheduler_request,
)
from scripts import render_worker as render_worker_script


def create_isolated_client(tmp_path, *, cache_remote_audio: bool = False) -> TestClient:
    os.environ["AIMP_STORAGE_ROOT"] = str(tmp_path / "storage")
    os.environ["AIMP_DATABASE_URL"] = f"sqlite:///{tmp_path / 'app.db'}"
    os.environ["AIMP_WORKER_AUTOSTART"] = "false"
    os.environ["AIMP_CACHE_REMOTE_AUDIO_ON_INTAKE"] = "true" if cache_remote_audio else "false"
    os.environ.pop("AIMP_SLACK_ENABLE_SIGNATURE_VERIFICATION", None)
    os.environ.pop("AIMP_SLACK_SIGNING_SECRET", None)
    get_settings.cache_clear()
    return TestClient(create_app())


def clear_isolated_client_env() -> None:
    os.environ.pop("AIMP_STORAGE_ROOT", None)
    os.environ.pop("AIMP_DATABASE_URL", None)
    os.environ.pop("AIMP_WORKER_AUTOSTART", None)
    os.environ.pop("AIMP_CACHE_REMOTE_AUDIO_ON_INTAKE", None)
    os.environ.pop("AIMP_YOUTUBE_OAUTH_REDIRECT_URI", None)
    os.environ.pop("AIMP_SLACK_BOT_TOKEN", None)
    os.environ.pop("AIMP_SLACK_ENABLE_SIGNATURE_VERIFICATION", None)
    os.environ.pop("AIMP_SLACK_SIGNING_SECRET", None)
    os.environ.pop("AIMP_SLACK_OPS_CHANNEL_ID", None)
    os.environ.pop("AIMP_OPENCLAW_SLACK_CHANNEL_ID", None)
    os.environ.pop("AIMP_OPENCLAW_AUTO_REQUEST_NEXT_ON_PUBLISH", None)
    os.environ.pop("AIMP_OPENCLAW_REQUEST_NEXT_ON_VIDEO_RENDER_EVENTS", None)
    os.environ.pop("AIMP_OPENCLAW_AUTO_REQUEST_NEXT_MAX_UPLOADS", None)
    os.environ.pop("AIMP_OPENCLAW_SLACK_TRIGGER_PREFIX", None)
    os.environ.pop("AIMP_OPENCLAW_NEXT_PLAYLIST_PROMPT", None)
    os.environ.pop("AIMP_OPENCLAW_SHARED_TOKEN", None)
    os.environ.pop("AIMP_OPENCLAW_LOCK_TTL_SECONDS", None)
    os.environ.pop("AIMP_OPENCLAW_BACKLOG_SCHEDULER_ENABLED", None)
    os.environ.pop("AIMP_OPENCLAW_BACKLOG_SCHEDULER_INTERVAL_SECONDS", None)
    os.environ.pop("AIMP_OPENCLAW_BACKLOG_REQUEST_COOLDOWN_SECONDS", None)
    os.environ.pop("AIMP_OPENCLAW_MANUAL_BLOCKER_BACKOFF_SECONDS", None)
    os.environ.pop("AIMP_OPENCLAW_BACKLOG_TARGET_PER_CHANNEL", None)
    os.environ.pop("AIMP_OPENCLAW_BACKLOG_MAX_PER_CHANNEL", None)
    os.environ.pop("AIMP_VIDEO_RENDER_EXECUTION_MODE", None)
    os.environ.pop("AIMP_RENDER_WORKER_SHARED_TOKEN", None)
    os.environ.pop("AIMP_RENDER_WORKER_CLAIM_TIMEOUT_SECONDS", None)
    os.environ.pop("AIMP_RENDER_WORKER_UPLOAD_CHUNK_BYTES", None)
    os.environ.pop("AIMP_RENDER_WORKER_CACHE_CLEANUP_ORPHAN_AGE_HOURS", None)
    os.environ.pop("AIMP_YOUTUBE_SCHEDULE_PUBLIC_ENABLED", None)
    os.environ.pop("AIMP_YOUTUBE_SCHEDULE_TIMEZONE", None)
    os.environ.pop("AIMP_YOUTUBE_SCHEDULE_HOUR", None)
    os.environ.pop("AIMP_YOUTUBE_SCHEDULE_MINUTE", None)
    os.environ.pop("AIMP_YOUTUBE_SCHEDULE_MIN_LEAD_MINUTES", None)
    get_settings.cache_clear()


def wav_bytes(duration_seconds: float = 1.0, *, sample_rate: int = 8000) -> bytes:
    buffer = io.BytesIO()
    frame_count = max(1, int(duration_seconds * sample_rate))
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(b"\x00\x00" * frame_count)
    return buffer.getvalue()


def test_dreamina_prompt_uses_tokyo_daydream_three_person_signature() -> None:
    playlist = Playlist(title="Tokyo Daydream", metadata_json={})
    track = Track(
        title="Neon Walk",
        prompt="upbeat J-pop night walk",
        metadata_json={
            "lyrics": "bright city chorus",
            "style": "J-pop, anime opening, synth",
            "tags": "jpop, tokyo",
        },
    )

    prompt = BackgroundJobWorker._build_dreamina_prompt(playlist, [track])

    assert "animated, anime, illustrated, or stylized" in prompt
    assert "Do not use photorealistic" in prompt
    assert "must not contain a channel name" in prompt
    assert "short release style/genre phrase" in prompt
    assert "Tokyo Daydream Radio" not in prompt
    assert "exactly three people walking toward the viewer" in prompt
    assert "camera moves backward at the same speed" in prompt


def test_long_video_verification_upload_error_is_detected_for_long_release() -> None:
    playlist = Playlist(
        title="Long deferred release",
        actual_duration_seconds=60 * 60,
        metadata_json={"rendered_duration_seconds": 60 * 60},
    )

    assert _is_long_video_verification_upload_error(
        "UploadLimitExceeded: this account must be verified to upload videos longer than 15 minutes",
        playlist,
    )


def test_long_video_verification_upload_error_ignores_short_release() -> None:
    playlist = Playlist(
        title="Short single",
        actual_duration_seconds=3 * 60,
        metadata_json={"rendered_duration_seconds": 3 * 60},
    )

    assert not _is_long_video_verification_upload_error(
        "UploadLimitExceeded: this account must be verified to upload videos longer than 15 minutes",
        playlist,
    )


def test_dreamina_prompt_keeps_soft_hour_out_of_tokyo_signature() -> None:
    playlist = Playlist(title="Deep Sleep Piano", metadata_json={"youtube_channel_title": "Soft Hour Radio"})
    track = Track(
        title="Quiet Moon Keys",
        prompt="soft piano sleep bgm",
        metadata_json={
            "lyrics": "[Instrumental only - no vocals]",
            "style": "felt piano, warm room tone, sleep music",
            "tags": "sleep,piano,bgm",
        },
    )

    prompt = BackgroundJobWorker._build_dreamina_prompt(playlist, [track])

    assert "Background-music visual system" in prompt
    assert "do not force a fixed recurring mascot" in prompt
    assert "must not contain a channel name" in prompt
    assert "short release style/genre phrase" in prompt
    assert "calm but clearly visible motion" in prompt
    assert "Keep the camera locked in the same crop and framing" in prompt
    assert "no zoom" in prompt
    assert 'channel brand label "Soft Hour Radio"' not in prompt
    assert "exactly three people walking toward the viewer" not in prompt


def test_dreamina_prompt_soft_hour_channel_overrides_japanese_style_terms() -> None:
    playlist = Playlist(title="Japanese Cafe BGM", metadata_json={"youtube_channel_title": "Soft Hour Radio"})
    track = Track(
        title="Quiet Cafe Notes",
        prompt="Japanese cafe jazz bgm for focus",
        metadata_json={
            "lyrics": "[Instrumental only - no vocals]",
            "style": "Japanese cafe jazz, soft bossa nova, no vocals",
            "tags": "japanese,cafe,bgm",
        },
    )

    prompt = BackgroundJobWorker._build_dreamina_prompt(playlist, [track])

    assert "Background-music visual system" in prompt
    assert 'channel brand label "Soft Hour Radio"' not in prompt
    assert "exactly three people walking toward the viewer" not in prompt


def test_dreamina_prompt_uses_cinematic_pulse_photorealistic_style() -> None:
    playlist = Playlist(
        title="Cinematic Pulse Release",
        metadata_json={"youtube_channel_title": "Cinematic Pulse"},
    )
    track = Track(
        title="Dark Horizon",
        prompt="dark fantasy cinematic orchestra",
        metadata_json={
            "style": "cinematic orchestra, brass, strings",
            "tags": "dark fantasy, trailer music",
        },
    )

    prompt = BackgroundJobWorker._build_dreamina_prompt(playlist, [track])

    assert "photorealistic cinematic film-still" in prompt
    assert "premium movie-poster realism" in prompt
    assert "must not contain a channel name" in prompt
    assert 'channel brand label "Cinematic Pulse"' not in prompt
    assert "Do not turn the image into anime" in prompt
    assert "Do not use photorealistic" not in prompt
    assert "exactly three people walking toward the viewer" not in prompt
    assert "Soft Hour Radio/background-music visual system" not in prompt


def test_openclaw_next_playlist_request_posts_to_configured_slack_channel(tmp_path) -> None:
    os.environ["AIMP_OPENCLAW_SLACK_CHANNEL_ID"] = "C0AVBUYP150"
    os.environ["AIMP_SLACK_BOT_TOKEN"] = "xoxb-test"
    client = create_isolated_client(tmp_path)
    calls = []

    async def fake_post_plain_message(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(ok=True, channel=kwargs["channel"], ts="123.456", raw={"ok": True})

    try:
        client.app.state.services.slack.post_plain_message = fake_post_plain_message
        with SessionLocal() as db:
            playlist = Playlist(
                title="Published Cafe Playlist",
                status=PlaylistStatus.uploaded,
                target_duration_seconds=3600,
                actual_duration_seconds=3600,
                youtube_video_id="yt-next-123",
                metadata_json={"youtube_channel_title": "Soft Hour Radio"},
            )
            db.add(playlist)
            db.commit()
            playlist_id = playlist.id

        response = client.post(
            f"/api/playlists/{playlist_id}/openclaw/request-next",
            json={"actor": "test-suite"},
        )

        assert response.status_code == 200
        assert response.json()["ok"] is True
        assert calls[0]["channel"] == "C0AVBUYP150"
        assert calls[0]["text"].startswith("OPENCLAW_RUN:\n")
        assert "OpenClaw Next Release Publisher Skill" in calls[0]["text"]
        assert "docs/openclaw-backlog-queue.md" in calls[0]["text"]
        assert "docs/openclaw-next-release-planner.md" in calls[0]["text"]
        assert "완료/중단 시 release id, YouTube video id, blocker만 간단히 보고" in calls[0]["text"]
        assert "https://youtu.be/yt-next-123" in calls[0]["text"]
        assert "Soft Hour Radio" in calls[0]["text"]
        with SessionLocal() as db:
            updated = db.get(Playlist, playlist_id)
            assert updated.metadata_json["openclaw_next_request_youtube_video_id"] == "yt-next-123"
    finally:
        clear_isolated_client_env()


def test_publish_completion_requests_next_even_with_video_event_requests_enabled(tmp_path) -> None:
    client = create_isolated_client(tmp_path)
    calls = []

    async def fake_post_plain_message(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(ok=True, channel=kwargs["channel"], ts="123.456", raw={"ok": True})

    try:
        services = client.app.state.services
        services.slack.post_plain_message = fake_post_plain_message
        services.settings.openclaw_slack_channel_id = "C0AVBUYP150"
        services.settings.slack_bot_token = "xoxb-test"
        services.settings.openclaw_auto_request_next_on_publish = True

        def fake_build_audio(tracks, output_path):
            output_path.write_bytes(b"fake-mp3")
            return output_path

        def fake_build_video(audio_path, cover_image_path, output_path, **_kwargs):
            output_path.write_bytes(b"fake-mp4")
            return output_path

        services.playlist_builder.build_audio = fake_build_audio
        services.playlist_builder.build_video = fake_build_video
        services.youtube.get_status = lambda: {"configured": True, "authenticated": True, "ready": True}
        services.youtube.upload_playlist_video = lambda *args, **kwargs: SimpleNamespace(
            video_id="yt-published-next",
            response={
                "id": "yt-published-next",
                "upload_channel": {"id": kwargs.get("youtube_channel_id"), "title": "Soft Hour Radio"},
            },
        )

        workspace_response = client.post(
            "/api/playlists/workspaces",
            json={
                "title": "Published Next Request Workspace",
                "target_duration_seconds": 60,
                "description": "Publish should request next.",
            },
        )
        workspace_id = workspace_response.json()["id"]
        local_audio = tmp_path / "single.mp3"
        local_audio.write_bytes(b"fake source")
        track_response = client.post(
            "/api/tracks",
            json={
                "title": "Single Track",
                "prompt": "minimal electronic",
                "duration_seconds": 60,
                "audio_path": str(local_audio),
                "metadata": {"source": "test"},
            },
        )
        track_id = track_response.json()["id"]
        approve_response = client.post(
            f"/api/tracks/{track_id}/decisions",
            json={
                "decision": "approve",
                "source": "human",
                "actor": "test-suite",
                "playlist_id": workspace_id,
            },
        )
        assert approve_response.status_code == 200
        render_workspace_audio(client, workspace_id)
        prepare_release_for_final_publish(client, workspace_id)

        services.settings.openclaw_request_next_on_video_render_events = True
        publish_response = client.post(
            f"/api/playlists/{workspace_id}/approve-publish",
            json={
                "actor": "test-suite",
                "note": "publish should request next",
                "youtube_channel_id": "UC_SOFT",
            },
        )
        assert publish_response.status_code == 200
        assert drain_background_jobs(client) == 1

        deadline = time.monotonic() + 3
        while not calls and time.monotonic() < deadline:
            time.sleep(0.05)
        assert len(calls) == 1
        assert calls[0]["channel"] == "C0AVBUYP150"
        assert "OpenClaw Next Release Publisher Skill" in calls[0]["text"]
        assert "scheduler_reason: publish_completed" in calls[0]["text"]
        assert "docs/openclaw-backlog-queue.md" in calls[0]["text"]
        metadata_deadline = time.monotonic() + 3
        while time.monotonic() < metadata_deadline:
            with SessionLocal() as db:
                playlist = db.get(Playlist, workspace_id)
                if playlist.metadata_json.get("openclaw_next_request_youtube_video_id") == "yt-published-next":
                    break
            time.sleep(0.05)
        else:
            with SessionLocal() as db:
                playlist = db.get(Playlist, workspace_id)
                assert playlist.metadata_json["openclaw_next_request_youtube_video_id"] == "yt-published-next"
        with SessionLocal() as db:
            playlist = db.get(Playlist, workspace_id)
            assert playlist.metadata_json["openclaw_auto_loop"]["should_request_next"] is True
    finally:
        clear_isolated_client_env()


def test_openclaw_lock_blocks_second_run(tmp_path) -> None:
    client = create_isolated_client(tmp_path)
    try:
        first = client.post(
            "/api/openclaw/lock/start",
            json={"owner": "openclaw", "run_id": "run-1", "operation": "backlog"},
        )
        second = client.post(
            "/api/openclaw/lock/start",
            json={"owner": "openclaw", "run_id": "run-2", "operation": "backlog"},
        )
        finished = client.post(
            "/api/openclaw/lock/finish",
            json={"owner": "openclaw", "run_id": "run-1", "status": "completed"},
        )

        assert first.status_code == 200
        assert first.json()["ok"] is True
        assert second.status_code == 200
        assert second.json()["ok"] is False
        assert second.json()["reason"] == "openclaw_lock_active"
        assert finished.status_code == 200
        assert finished.json()["ok"] is True
    finally:
        clear_isolated_client_env()


def test_openclaw_lock_records_release_channel_hint(tmp_path) -> None:
    client = create_isolated_client(tmp_path)
    try:
        with SessionLocal() as db:
            playlist = Playlist(
                title="Tech House",
                status=PlaylistStatus.building,
                target_duration_seconds=2400,
                actual_duration_seconds=2400,
                metadata_json={"workflow_state": "video_rendering"},
            )
            db.add(playlist)
            db.commit()
            playlist_id = playlist.id

        response = client.post(
            "/api/openclaw/lock/start",
            json={
                "owner": "openclaw",
                "run_id": "run-1",
                "operation": "video",
                "channel_title": "Club Bloom",
                "release_id": playlist_id,
            },
        )

        assert response.status_code == 200
        assert response.json()["ok"] is True
        assert response.json()["release_channel_hint_recorded"] is True
        with SessionLocal() as db:
            updated = db.get(Playlist, playlist_id)
            assert updated.metadata_json["target_youtube_channel_title"] == "Club Bloom"
            assert updated.metadata_json["openclaw_lock_channel_title"] == "Club Bloom"
    finally:
        clear_isolated_client_env()


def test_backlog_request_message_prioritizes_incomplete_unknown_workspaces() -> None:
    message = build_backlog_queue_request_message(
        reason="underfilled_backlog",
        backlog_summary={
            "target_per_channel": 10,
            "max_per_channel": 10,
            "channels": {
                "Soft Hour Radio": {
                    "count": 0,
                    "finishable": 0,
                    "deferred": 0,
                    "releases": [],
                }
            },
            "unknown_channel_releases": [
                {
                    "id": "workspace-1",
                    "title": "[playlist] Backyard Pool Party Pop",
                    "workflow_state": "collecting",
                    "channel_title": None,
                }
            ],
        },
    )

    assert "새 workspace를 만들기 전에 기존 미완성 workspace" in message
    assert "먼저 확인할 채널 미지정/미완성 workspace" in message
    assert "[playlist] Backyard Pool Party Pop: collecting, id workspace-1, channel unknown" in message


def test_backlog_request_message_includes_future_scheduled_public_upload_counts() -> None:
    message = build_backlog_queue_request_message(
        reason="underfilled_backlog",
        backlog_summary={
            "target_per_channel": 10,
            "max_per_channel": 10,
            "channels": {
                "The New Verse": {
                    "count": 0,
                    "finishable": 0,
                    "deferred": 0,
                    "youtube_scheduled_public_count": 0,
                    "youtube_uploaded_count": 0,
                    "releases": [],
                },
                "Club Bloom": {
                    "count": 0,
                    "finishable": 0,
                    "deferred": 0,
                    "youtube_scheduled_public_count": 2,
                    "last_youtube_scheduled_public_local_date": "2099-05-20",
                    "last_youtube_scheduled_public_at": "2099-05-19T22:00:00+00:00",
                    "youtube_uploaded_count": 2,
                    "releases": [],
                },
            },
            "unknown_channel_releases": [],
        },
    )

    assert "scheduled-through 날짜가 균등해지게 가장 짧은 채널부터" in message
    assert "The New Verse: 0 unfinished, 0 finishable, 0 deferred, 0 YouTube reconnect needed, 0 future scheduled-public YouTube uploads, scheduled-through none" in message
    assert "Club Bloom: 0 unfinished, 0 finishable, 0 deferred, 0 YouTube reconnect needed, 2 future scheduled-public YouTube uploads, scheduled-through 2099-05-20" in message


def test_backlog_request_message_skips_auth_blocked_channels_in_priority_list() -> None:
    message = build_backlog_queue_request_message(
        reason="underfilled_backlog",
        backlog_summary={
            "target_per_channel": 10,
            "max_per_channel": 10,
            "channels": {
                "Solwave Radio": {
                    "count": 1,
                    "finishable": 0,
                    "deferred": 1,
                    "auth_blocked": 1,
                    "youtube_scheduled_public_count": 0,
                    "youtube_uploaded_count": 11,
                    "releases": [],
                },
                "The New Verse": {
                    "count": 0,
                    "finishable": 0,
                    "deferred": 0,
                    "auth_blocked": 0,
                    "youtube_scheduled_public_count": 0,
                    "youtube_uploaded_count": 2,
                    "releases": [],
                },
            },
            "unknown_channel_releases": [],
        },
    )

    priority_section = message.split("현재 웹앱 backlog snapshot:", 1)[0]
    assert "The New Verse: 0 unfinished" in priority_section
    assert "Solwave Radio: 1 unfinished" not in priority_section
    assert "YouTube 재연결 전까지 새 release를 만들지 말아야 할 채널" in message
    assert "Solwave Radio: 1 failed publish item(s)" in message


def test_backlog_request_message_lists_zero_scheduled_lowest_unfinished_first() -> None:
    message = build_backlog_queue_request_message(
        reason="underfilled_backlog",
        backlog_summary={
            "target_per_channel": 10,
            "max_per_channel": 10,
            "channels": {
                "sundaze": {
                    "count": 2,
                    "finishable": 0,
                    "deferred": 2,
                    "youtube_scheduled_public_count": 0,
                    "youtube_uploaded_count": 11,
                    "releases": [],
                },
                "The Old Verse": {
                    "count": 0,
                    "finishable": 0,
                    "deferred": 0,
                    "youtube_scheduled_public_count": 0,
                    "youtube_uploaded_count": 1,
                    "releases": [],
                },
                "The New Verse": {
                    "count": 0,
                    "finishable": 0,
                    "deferred": 0,
                    "youtube_scheduled_public_count": 0,
                    "youtube_uploaded_count": 1,
                    "releases": [],
                },
                "Club Bloom": {
                    "count": 0,
                    "finishable": 0,
                    "deferred": 0,
                    "youtube_scheduled_public_count": 2,
                    "last_youtube_scheduled_public_local_date": "2099-05-20",
                    "last_youtube_scheduled_public_at": "2099-05-19T22:00:00+00:00",
                    "youtube_uploaded_count": 4,
                    "releases": [],
                },
            },
            "unknown_channel_releases": [],
        },
    )

    priority_header = message.index("먼저 채울 채널 우선순위")
    new_index = message.index("- The New Verse: 0 unfinished", priority_header)
    old_index = message.index("- The Old Verse: 0 unfinished", priority_header)
    sundaze_index = message.index("- sundaze: 2 unfinished", priority_header)
    assert new_index < sundaze_index
    assert old_index < sundaze_index
    assert "먼저 채울 채널 우선순위(예약 horizon 짧은 순, 모든 채널 날짜 균등)" in message


def test_backlog_request_message_prioritizes_shortest_schedule_horizon() -> None:
    message = build_backlog_queue_request_message(
        reason="underfilled_backlog",
        backlog_summary={
            "target_per_channel": 10,
            "max_per_channel": 10,
            "channels": {
                "불송": {
                    "count": 2,
                    "finishable": 0,
                    "deferred": 0,
                    "youtube_scheduled_public_count": 7,
                    "last_youtube_scheduled_public_local_date": "2026-05-27",
                    "last_youtube_scheduled_public_at": "2026-05-26T22:00:00+00:00",
                    "youtube_uploaded_count": 7,
                    "releases": [],
                },
                "Storylight OST": {
                    "count": 0,
                    "finishable": 0,
                    "deferred": 0,
                    "youtube_scheduled_public_count": 1,
                    "last_youtube_scheduled_public_local_date": "2026-05-21",
                    "last_youtube_scheduled_public_at": "2026-05-20T22:00:00+00:00",
                    "youtube_uploaded_count": 6,
                    "releases": [],
                },
                "Club Bloom": {
                    "count": 0,
                    "finishable": 0,
                    "deferred": 0,
                    "youtube_scheduled_public_count": 2,
                    "last_youtube_scheduled_public_local_date": "2026-05-22",
                    "last_youtube_scheduled_public_at": "2026-05-21T22:00:00+00:00",
                    "youtube_uploaded_count": 6,
                    "releases": [],
                },
            },
            "unknown_channel_releases": [],
        },
    )

    priority_header = message.index("먼저 채울 채널 우선순위")
    storylight_index = message.index("- Storylight OST: 0 unfinished", priority_header)
    club_index = message.index("- Club Bloom: 0 unfinished", priority_header)
    bulsong_index = message.index("- 불송: 2 unfinished", priority_header)
    assert storylight_index < club_index < bulsong_index
    assert "Storylight OST: 0 unfinished, 0 deferred, 1 future scheduled-public YouTube uploads, scheduled-through 2026-05-21" in message
    assert "불송: 2 unfinished, 0 deferred, 7 future scheduled-public YouTube uploads, scheduled-through 2026-05-27" in message


def test_backlog_request_message_resumes_manual_blocker_instead_of_next_release() -> None:
    message = build_backlog_queue_request_message(
        reason="resume_openclaw_manual_blocker",
        backlog_summary={
            "manual_blocker": {
                "last_finished_lock": {
                    "release_id": "release-captcha",
                    "channel_title": "Tokyo Daydream Radio",
                    "operation": "backlog-pass",
                    "run_id": "run-captcha",
                    "finish_message": "Suno hCaptcha manual verification is required.",
                }
            },
            "channels": {
                "Tokyo Daydream Radio": {
                    "count": 0,
                    "finishable": 0,
                    "deferred": 0,
                    "youtube_scheduled_public_count": 0,
                    "youtube_uploaded_count": 17,
                }
            },
        },
    )

    assert "blocked release resume" in message
    assert "다음 곡을 만들지 말고" in message
    assert "같은 작업을 계속 진행해줘" in message
    assert "blocked_release_id: release-captcha" in message
    assert "OpenClaw Next Release Publisher Skill" not in message


def test_openclaw_backlog_summary_counts_future_scheduled_public_youtube_uploads(tmp_path) -> None:
    client = create_isolated_client(tmp_path)
    try:
        services = client.app.state.services
        services.youtube.get_status = lambda: {
            "configured": True,
            "authenticated": True,
            "ready": True,
            "channels": [
                {"id": "UC_NEW", "title": "The New Verse"},
                {"id": "UC_CLUB", "title": "Club Bloom"},
            ],
        }
        with SessionLocal() as db:
            db.add_all(
                [
                    Playlist(
                        title="Scheduled Club",
                        status=PlaylistStatus.uploaded,
                        youtube_video_id="yt-scheduled",
                        metadata_json={
                            "workflow_state": "uploaded",
                            "youtube_channel_title": "Club Bloom",
                            "youtube_scheduled_publish_at": "2099-05-18T22:00:00+00:00",
                        },
                    ),
                    Playlist(
                        title="Past Scheduled New Verse",
                        status=PlaylistStatus.uploaded,
                        youtube_video_id="yt-past-scheduled",
                        metadata_json={
                            "workflow_state": "uploaded",
                            "youtube_channel_title": "The New Verse",
                            "youtube_scheduled_publish_at": "2026-01-01T22:00:00+00:00",
                        },
                    ),
                    Playlist(
                        title="Private New Verse",
                        status=PlaylistStatus.uploaded,
                        youtube_video_id="yt-private",
                        metadata_json={
                            "workflow_state": "uploaded",
                            "youtube_channel_title": "The New Verse",
                            "youtube_published_at": "2026-05-18T21:00:00+00:00",
                            "youtube_response": {"status": {"privacyStatus": "private"}},
                        },
                    ),
                    Playlist(
                        title="Collecting New Verse",
                        status=PlaylistStatus.draft,
                        metadata_json={
                            "workflow_state": "collecting",
                            "target_youtube_channel_title": "The New Verse",
                        },
                    ),
                    Playlist(
                        title="Cover Review New Verse",
                        status=PlaylistStatus.ready,
                        metadata_json={
                            "workflow_state": "cover_review",
                            "target_youtube_channel_title": "The New Verse",
                        },
                    ),
                ]
            )
            db.commit()

            summary = build_openclaw_backlog_summary(db, services)

        assert summary["channels"]["Club Bloom"]["youtube_uploaded_count"] == 1
        assert summary["channels"]["Club Bloom"]["youtube_scheduled_public_count"] == 1
        assert summary["channels"]["Club Bloom"]["last_youtube_scheduled_public_local_date"] == "2099-05-19"
        assert summary["channels"]["Club Bloom"]["youtube_scheduled_public_local_dates"] == ["2099-05-19"]
        assert summary["channels"]["불송"]["youtube_uploaded_count"] == 2
        assert summary["channels"]["불송"]["youtube_scheduled_public_count"] == 0
        assert summary["channels"]["불송"]["last_youtube_scheduled_public_local_date"] is None
        assert summary["channels"]["불송"]["count"] == 2
    finally:
        clear_isolated_client_env()


def test_openclaw_scripture_sequence_is_reserved_by_webapp(tmp_path) -> None:
    os.environ["AIMP_OPENCLAW_SHARED_TOKEN"] = "test-token"
    client = create_isolated_client(tmp_path)
    headers = {"X-OpenClaw-Token": "test-token"}
    try:
        with SessionLocal() as db:
            playlist = Playlist(
                title="[playlist] Matthew 1:18-25 Emmanuel Worship",
                status=PlaylistStatus.draft,
                metadata_json={"workflow_state": "collecting"},
            )
            db.add(playlist)
            db.commit()
            release_id = playlist.id

        reserve_response = client.post(
            "/api/openclaw/scripture/reserve",
            headers=headers,
            json={
                "channel_title": "New Testament",
                "release_id": release_id,
                "title": "[playlist] Matthew 1:1-17 Gospel Worship",
            },
        )
        assert reserve_response.status_code == 200
        reserved = reserve_response.json()
        assert reserved["entry"]["passage_range"] == "Matthew 1:1-17"
        assert reserved["entry"]["next_start_after_completion"] == "Matthew 1:18"
        assert reserved["release_scripture_hint_recorded"] is True

        retry_response = client.post(
            "/api/openclaw/scripture/reserve",
            headers=headers,
            json={
                "channel_title": "New Testament",
                "release_id": release_id,
                "title": "[playlist] Matthew 1:1-17 Gospel Worship",
            },
        )
        assert retry_response.status_code == 200
        assert retry_response.json()["idempotent"] is True

        with SessionLocal() as db:
            playlist = db.get(Playlist, release_id)
            assert playlist.metadata_json["target_youtube_channel_title"] == "BibliaCanto"
            assert playlist.metadata_json["scripture_channel_title"] == "New Testament"
            assert playlist.metadata_json["scripture_passage_range"] == "Matthew 1:1-17"
            assert playlist.metadata_json["scripture_sequence_status"] == "in_progress"

        complete_response = client.post(
            "/api/openclaw/scripture/complete",
            headers=headers,
            json={
                "channel_title": "The New Verse",
                "passage_range": "Matthew 1:1-17",
                "release_id": release_id,
                "youtube_video_id": "yt-new-1",
                "title": "[playlist] Matthew 1:1-17 Gospel Worship",
                "status": "scheduled",
            },
        )
        assert complete_response.status_code == 200
        assert complete_response.json()["next_start"] == "Matthew 1:18"

        status_response = client.get("/api/openclaw/scripture/status", headers=headers)
        assert status_response.status_code == 200
        status_payload = status_response.json()
        assert status_payload["state"]["the_new_verse"]["last_completed"] == "Matthew 1:1-17"
        assert status_payload["next_suggestions"]["the_new_verse"]["passage_range"] == "Matthew 1:18-25"
    finally:
        clear_isolated_client_env()


def test_openclaw_scripture_sequence_rejects_duplicate_active_passage(tmp_path) -> None:
    client = create_isolated_client(tmp_path)
    try:
        first_response = client.post(
            "/api/openclaw/scripture/reserve",
            json={
                "channel_title": "The Old Verse",
                "release_id": "release-1",
                "title": "[playlist] Genesis 1:1-5 Creation Worship",
            },
        )
        assert first_response.status_code == 200

        duplicate_response = client.post(
            "/api/openclaw/scripture/reserve",
            json={
                "channel_title": "The Old Verse",
                "release_id": "release-2",
                "title": "[playlist] Genesis 1:1-5 Duplicate",
            },
        )
        assert duplicate_response.status_code == 409
        assert duplicate_response.json()["detail"]["code"] == "passage_already_active"
    finally:
        clear_isolated_client_env()


def test_openclaw_backlog_scheduler_does_not_prioritize_auth_blocked_upload_failures(tmp_path) -> None:
    os.environ["AIMP_OPENCLAW_BACKLOG_SCHEDULER_ENABLED"] = "true"
    os.environ["AIMP_OPENCLAW_SLACK_CHANNEL_ID"] = "C0AVBUYP150"
    client = create_isolated_client(tmp_path)
    try:
        services = client.app.state.services
        services.youtube.get_status = lambda: {
            "configured": True,
            "authenticated": True,
            "ready": True,
            "channels": [
                {"id": "UC_SOL", "title": "Solwave Radio"},
                {"id": "UC_NEW", "title": "The New Verse"},
            ],
        }
        with SessionLocal() as db:
            db.add(
                Playlist(
                    title="Auth Blocked Solwave",
                    status=PlaylistStatus.ready,
                    metadata_json={
                        "workflow_state": "youtube_upload_failed",
                        "youtube_channel_title": "Solwave Radio",
                        "target_youtube_channel_title": "Solwave Radio",
                        "youtube_upload_error": "Stored YouTube channel token expired or was revoked. Connect this channel again.",
                    },
                )
            )
            db.commit()

            summary = build_openclaw_backlog_summary(db, services)
            evaluation = evaluate_openclaw_backlog_scheduler(db, services)

        assert summary["channels"]["Solwave Radio"]["count"] == 1
        assert summary["channels"]["Solwave Radio"]["finishable"] == 0
        assert summary["channels"]["Solwave Radio"]["deferred"] == 1
        assert summary["channels"]["Solwave Radio"]["auth_blocked"] == 1
        assert evaluation["reason"] == "zero_scheduled_public_backlog"
        assert "Solwave Radio" not in evaluation["underfilled_channels"]
        assert "Solwave Radio" in evaluation["auth_blocked_channels"]
        assert evaluation["zero_scheduled_public_channels"] == ["불송"]
        assert "불송" in evaluation["underfilled_channels"]
    finally:
        clear_isolated_client_env()


def test_openclaw_backlog_scheduler_pauses_when_only_underfilled_channel_needs_reconnect(tmp_path) -> None:
    os.environ["AIMP_OPENCLAW_BACKLOG_SCHEDULER_ENABLED"] = "true"
    os.environ["AIMP_OPENCLAW_SLACK_CHANNEL_ID"] = "C0AVBUYP150"
    client = create_isolated_client(tmp_path)
    try:
        services = client.app.state.services
        services.youtube.get_status = lambda: {
            "configured": True,
            "authenticated": True,
            "ready": True,
            "channels": [{"id": "UC_SOL", "title": "Solwave Radio"}],
        }
        with SessionLocal() as db:
            db.add(
                Playlist(
                    title="Auth Blocked Solwave",
                    status=PlaylistStatus.ready,
                    metadata_json={
                        "workflow_state": "youtube_upload_failed",
                        "youtube_channel_title": "Solwave Radio",
                        "target_youtube_channel_title": "Solwave Radio",
                        "youtube_upload_error": "Stored YouTube channel token expired or was revoked. Connect this channel again.",
                    },
                )
            )
            db.commit()

            evaluation = evaluate_openclaw_backlog_scheduler(db, services)

        assert evaluation["should_request"] is False
        assert evaluation["reason"] == "underfilled_channels_need_youtube_reconnect"
        assert evaluation["underfilled_channels"] == []
        assert evaluation["auth_blocked_channels"] == ["Solwave Radio"]
    finally:
        clear_isolated_client_env()


def test_openclaw_backlog_scheduler_retries_failed_publish_after_channel_reconnect(tmp_path) -> None:
    os.environ["AIMP_OPENCLAW_BACKLOG_SCHEDULER_ENABLED"] = "true"
    os.environ["AIMP_OPENCLAW_SLACK_CHANNEL_ID"] = "C0AVBUYP150"
    client = create_isolated_client(tmp_path)
    failed_at = datetime(2026, 5, 19, 0, 59)
    reconnected_at = datetime(2026, 5, 19, 1, 31, tzinfo=timezone.utc)
    try:
        services = client.app.state.services
        services.youtube.get_status = lambda: {
            "configured": True,
            "authenticated": True,
            "ready": True,
            "channels": [
                {
                    "id": "UC_SOL",
                    "title": "Solwave Radio",
                    "connected_at": reconnected_at.isoformat(),
                }
            ],
        }
        with SessionLocal() as db:
            db.add(
                Playlist(
                    title="Reconnected Solwave",
                    status=PlaylistStatus.ready,
                    updated_at=failed_at,
                    metadata_json={
                        "workflow_state": "youtube_upload_failed",
                        "youtube_channel_title": "Solwave Radio",
                        "target_youtube_channel_title": "Solwave Radio",
                        "youtube_upload_error": "Stored YouTube channel token expired or was revoked. Connect this channel again.",
                    },
                )
            )
            db.commit()

            summary = build_openclaw_backlog_summary(db, services)
            evaluation = evaluate_openclaw_backlog_scheduler(db, services)

        assert summary["channels"]["Solwave Radio"]["finishable"] == 1
        assert summary["channels"]["Solwave Radio"]["deferred"] == 0
        assert summary["channels"]["Solwave Radio"]["auth_blocked"] == 0
        assert evaluation["should_request"] is True
        assert evaluation["reason"] == "finishable_releases"
        assert evaluation["finishable_channels"] == ["Solwave Radio"]
    finally:
        clear_isolated_client_env()


def test_openclaw_backlog_scheduler_prioritizes_finishable_before_zero_scheduled_channels(tmp_path) -> None:
    os.environ["AIMP_OPENCLAW_BACKLOG_SCHEDULER_ENABLED"] = "true"
    os.environ["AIMP_OPENCLAW_SLACK_CHANNEL_ID"] = "C0AVBUYP150"
    client = create_isolated_client(tmp_path)
    try:
        services = client.app.state.services
        services.youtube.get_status = lambda: {
            "configured": True,
            "authenticated": True,
            "ready": True,
            "channels": [
                {"id": "UC_SOFT", "title": "Soft Hour Radio"},
                {"id": "UC_NEW", "title": "The New Verse"},
                {"id": "UC_OLD", "title": "The Old Verse"},
            ],
        }
        with SessionLocal() as db:
            db.add(
                Playlist(
                    title="Ready Metadata Release",
                    status=PlaylistStatus.ready,
                    metadata_json={
                        "workflow_state": "metadata_review",
                        "youtube_channel_title": "Soft Hour Radio",
                    },
                )
            )
            db.commit()

            evaluation = evaluate_openclaw_backlog_scheduler(db, services)

        assert evaluation["should_request"] is True
        assert evaluation["reason"] == "finishable_releases"
        assert evaluation["finishable_channels"] == ["Soft Hour Radio"]
        assert evaluation["zero_scheduled_public_channels"] == ["BibliaCanto", "불송"]
        assert "불송" in evaluation["underfilled_channels"]
        assert "BibliaCanto" in evaluation["underfilled_channels"]
    finally:
        clear_isolated_client_env()


def test_openclaw_backlog_scheduler_cooldown_blocks_unhandled_duplicate_finishable_request(tmp_path) -> None:
    os.environ["AIMP_OPENCLAW_BACKLOG_SCHEDULER_ENABLED"] = "true"
    os.environ["AIMP_OPENCLAW_BACKLOG_REQUEST_COOLDOWN_SECONDS"] = "1800"
    os.environ["AIMP_OPENCLAW_SLACK_CHANNEL_ID"] = "C0AVBUYP150"
    client = create_isolated_client(tmp_path)
    try:
        services = client.app.state.services
        services.youtube.get_status = lambda: {
            "configured": True,
            "authenticated": True,
            "ready": True,
            "channels": [{"id": "UC_SOFT", "title": "Soft Hour Radio"}],
        }
        with SessionLocal() as db:
            db.add(
                Playlist(
                    title="Ready Metadata Release",
                    status=PlaylistStatus.ready,
                    metadata_json={
                        "workflow_state": "metadata_review",
                        "youtube_channel_title": "Soft Hour Radio",
                    },
                )
            )
            db.commit()
            record_openclaw_backlog_scheduler_request(
                storage_root=services.settings.storage_root,
                result={"reason": "finishable_releases"},
            )

            evaluation = evaluate_openclaw_backlog_scheduler(db, services)

        assert evaluation["should_request"] is False
        assert evaluation["reason"] == "backlog_request_cooldown"
        assert evaluation["pending_reason"] == "finishable_releases"
        assert evaluation["finishable_channels"] == ["Soft Hour Radio"]
    finally:
        clear_isolated_client_env()


def test_openclaw_backlog_scheduler_keeps_cooldown_after_openclaw_finishes_without_backlog_change(
    tmp_path,
) -> None:
    os.environ["AIMP_OPENCLAW_BACKLOG_SCHEDULER_ENABLED"] = "true"
    os.environ["AIMP_OPENCLAW_BACKLOG_REQUEST_COOLDOWN_SECONDS"] = "1800"
    os.environ["AIMP_OPENCLAW_SLACK_CHANNEL_ID"] = "C0AVBUYP150"
    client = create_isolated_client(tmp_path)
    try:
        services = client.app.state.services
        services.youtube.get_status = lambda: {
            "configured": True,
            "authenticated": True,
            "ready": True,
            "channels": [{"id": "UC_SOFT", "title": "Soft Hour Radio"}],
        }
        with SessionLocal() as db:
            db.add(
                Playlist(
                    title="Ready Metadata Release",
                    status=PlaylistStatus.ready,
                    metadata_json={
                        "workflow_state": "metadata_review",
                        "youtube_channel_title": "Soft Hour Radio",
                    },
                )
            )
            db.commit()
            record_openclaw_backlog_scheduler_request(
                storage_root=services.settings.storage_root,
                result={"reason": "underfilled_backlog"},
            )

        client.post(
            "/api/openclaw/lock/start",
            json={"owner": "openclaw", "run_id": "run-finished", "operation": "backlog-pass"},
        )
        client.post(
            "/api/openclaw/lock/finish",
            json={
                "owner": "openclaw",
                "run_id": "run-finished",
                "status": "completed",
                "message": "Queued video render and released lock.",
            },
        )

        with SessionLocal() as db:
            evaluation = evaluate_openclaw_backlog_scheduler(db, services)

        assert evaluation["should_request"] is False
        assert evaluation["reason"] == "backlog_request_cooldown"
        assert evaluation["pending_reason"] == "finishable_releases"
        assert evaluation["finishable_channels"] == ["Soft Hour Radio"]
    finally:
        clear_isolated_client_env()


def test_openclaw_backlog_scheduler_bypasses_cooldown_after_backlog_state_changes(tmp_path) -> None:
    os.environ["AIMP_OPENCLAW_BACKLOG_SCHEDULER_ENABLED"] = "true"
    os.environ["AIMP_OPENCLAW_BACKLOG_REQUEST_COOLDOWN_SECONDS"] = "1800"
    os.environ["AIMP_OPENCLAW_SLACK_CHANNEL_ID"] = "C0AVBUYP150"
    client = create_isolated_client(tmp_path)
    try:
        services = client.app.state.services
        services.youtube.get_status = lambda: {
            "configured": True,
            "authenticated": True,
            "ready": True,
            "channels": [{"id": "UC_SOFT", "title": "Soft Hour Radio"}],
        }
        with SessionLocal() as db:
            initial_evaluation = evaluate_openclaw_backlog_scheduler(db, services)
            record_openclaw_backlog_scheduler_request(
                storage_root=services.settings.storage_root,
                result=initial_evaluation,
            )
            db.add(
                Playlist(
                    title="Newly Queued Video Release",
                    status=PlaylistStatus.ready,
                    metadata_json={
                        "workflow_state": "video_rendering",
                        "youtube_channel_title": "Soft Hour Radio",
                    },
                )
            )
            db.commit()

            evaluation = evaluate_openclaw_backlog_scheduler(db, services)

        assert evaluation["should_request"] is True
        assert evaluation["reason"] == "underfilled_backlog"
        assert evaluation["underfilled_channels"] == ["Soft Hour Radio"]
    finally:
        clear_isolated_client_env()


def test_openclaw_backlog_scheduler_bypasses_cooldown_for_new_finishable_release(tmp_path) -> None:
    os.environ["AIMP_OPENCLAW_BACKLOG_SCHEDULER_ENABLED"] = "true"
    os.environ["AIMP_OPENCLAW_BACKLOG_REQUEST_COOLDOWN_SECONDS"] = "1800"
    os.environ["AIMP_OPENCLAW_SLACK_CHANNEL_ID"] = "C0AVBUYP150"
    client = create_isolated_client(tmp_path)
    try:
        services = client.app.state.services
        services.youtube.get_status = lambda: {
            "configured": True,
            "authenticated": True,
            "ready": True,
            "channels": [{"id": "UC_SOFT", "title": "Soft Hour Radio"}],
        }
        with SessionLocal() as db:
            record_openclaw_backlog_scheduler_request(
                storage_root=services.settings.storage_root,
                result={"reason": "underfilled_backlog"},
            )
            db.add(
                Playlist(
                    title="Newly Rendered Release",
                    status=PlaylistStatus.ready,
                    metadata_json={
                        "workflow_state": "metadata_review",
                        "youtube_channel_title": "Soft Hour Radio",
                    },
                )
            )
            db.commit()

            evaluation = evaluate_openclaw_backlog_scheduler(db, services)

        assert evaluation["should_request"] is True
        assert evaluation["reason"] == "finishable_releases"
        assert evaluation["finishable_channels"] == ["Soft Hour Radio"]
    finally:
        clear_isolated_client_env()


def test_openclaw_backlog_scheduler_posts_when_channel_is_underfilled(tmp_path) -> None:
    os.environ["AIMP_OPENCLAW_BACKLOG_SCHEDULER_ENABLED"] = "true"
    os.environ["AIMP_OPENCLAW_BACKLOG_SCHEDULER_INTERVAL_SECONDS"] = "30"
    os.environ["AIMP_OPENCLAW_BACKLOG_REQUEST_COOLDOWN_SECONDS"] = "1800"
    os.environ["AIMP_OPENCLAW_SLACK_CHANNEL_ID"] = "C0AVBUYP150"
    os.environ["AIMP_SLACK_BOT_TOKEN"] = "xoxb-test"
    client = create_isolated_client(tmp_path)
    calls = []

    async def fake_post_plain_message(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(ok=True, channel=kwargs["channel"], ts="123.456", raw={"ok": True})

    try:
        services = client.app.state.services
        services.youtube.get_status = lambda: {
            "configured": True,
            "authenticated": True,
            "ready": True,
            "channels": [
                {"id": "UC_SOFT", "title": "Soft Hour Radio"},
                {"id": "UC_MUSIC", "title": "MusicSun"},
            ],
        }
        services.slack.post_plain_message = fake_post_plain_message

        services.worker._maybe_request_openclaw_backlog()
        services.worker._maybe_request_openclaw_backlog()

        assert len(calls) == 1
        assert calls[0]["channel"] == "C0AVBUYP150"
        assert calls[0]["text"].startswith("OPENCLAW_RUN:\n")
        assert "OpenClaw Next Release Publisher Skill" in calls[0]["text"]
        assert "Soft Hour Radio: 0 unfinished" in calls[0]["text"]
        assert "MusicSun:" not in calls[0]["text"]
    finally:
        clear_isolated_client_env()


def test_openclaw_backlog_scheduler_skips_when_lock_is_active(tmp_path) -> None:
    os.environ["AIMP_OPENCLAW_BACKLOG_SCHEDULER_ENABLED"] = "true"
    os.environ["AIMP_OPENCLAW_BACKLOG_SCHEDULER_INTERVAL_SECONDS"] = "30"
    os.environ["AIMP_OPENCLAW_SLACK_CHANNEL_ID"] = "C0AVBUYP150"
    os.environ["AIMP_SLACK_BOT_TOKEN"] = "xoxb-test"
    client = create_isolated_client(tmp_path)
    calls = []

    async def fake_post_plain_message(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(ok=True, channel=kwargs["channel"], ts="123.456", raw={"ok": True})

    try:
        services = client.app.state.services
        services.youtube.get_status = lambda: {
            "configured": True,
            "authenticated": True,
            "ready": True,
            "channels": [{"id": "UC_SOFT", "title": "Soft Hour Radio"}],
        }
        services.slack.post_plain_message = fake_post_plain_message
        client.post(
            "/api/openclaw/lock/start",
            json={"owner": "openclaw", "run_id": "run-1", "operation": "suno"},
        )

        services.worker._maybe_request_openclaw_backlog()

        assert calls == []
    finally:
        clear_isolated_client_env()


def test_openclaw_backlog_scheduler_backs_off_after_manual_blocker(tmp_path) -> None:
    os.environ["AIMP_OPENCLAW_BACKLOG_SCHEDULER_ENABLED"] = "true"
    os.environ["AIMP_OPENCLAW_BACKLOG_SCHEDULER_INTERVAL_SECONDS"] = "30"
    os.environ["AIMP_OPENCLAW_BACKLOG_REQUEST_COOLDOWN_SECONDS"] = "0"
    os.environ["AIMP_OPENCLAW_MANUAL_BLOCKER_BACKOFF_SECONDS"] = "1800"
    os.environ["AIMP_OPENCLAW_SLACK_CHANNEL_ID"] = "C0AVBUYP150"
    os.environ["AIMP_SLACK_BOT_TOKEN"] = "xoxb-test"
    client = create_isolated_client(tmp_path)
    calls = []

    async def fake_post_plain_message(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(ok=True, channel=kwargs["channel"], ts="123.456", raw={"ok": True})

    try:
        services = client.app.state.services
        services.youtube.get_status = lambda: {
            "configured": True,
            "authenticated": True,
            "ready": True,
            "channels": [{"id": "UC_TOKYO", "title": "Tokyo Daydream Radio"}],
        }
        services.slack.post_plain_message = fake_post_plain_message
        client.post(
            "/api/openclaw/lock/start",
            json={"owner": "openclaw", "run_id": "run-captcha", "operation": "backlog-pass"},
        )
        client.post(
            "/api/openclaw/lock/finish",
            json={
                "owner": "openclaw",
                "run_id": "run-captcha",
                "status": "blocked",
                "message": "Suno hCaptcha manual verification is required at https://suno.com/create.",
            },
        )

        with SessionLocal() as db:
            evaluation = evaluate_openclaw_backlog_scheduler(db, services)

        services.worker._maybe_request_openclaw_backlog()

        assert evaluation["should_request"] is False
        assert evaluation["reason"] == "recent_openclaw_manual_blocker"
        assert evaluation["manual_blocker_backoff_seconds"] == 1800
        assert calls == []
    finally:
        clear_isolated_client_env()


def test_openclaw_backlog_scheduler_backs_off_finishable_release_after_manual_blocker(tmp_path) -> None:
    os.environ["AIMP_OPENCLAW_BACKLOG_SCHEDULER_ENABLED"] = "true"
    os.environ["AIMP_OPENCLAW_BACKLOG_REQUEST_COOLDOWN_SECONDS"] = "0"
    os.environ["AIMP_OPENCLAW_MANUAL_BLOCKER_BACKOFF_SECONDS"] = "1800"
    os.environ["AIMP_OPENCLAW_SLACK_CHANNEL_ID"] = "C0AVBUYP150"
    client = create_isolated_client(tmp_path)
    try:
        services = client.app.state.services
        services.youtube.get_status = lambda: {
            "configured": True,
            "authenticated": True,
            "ready": True,
            "channels": [{"id": "UC_SOFT", "title": "Soft Hour Radio"}],
        }
        client.post(
            "/api/openclaw/lock/start",
            json={"owner": "openclaw", "run_id": "run-captcha", "operation": "backlog-pass"},
        )
        client.post(
            "/api/openclaw/lock/finish",
            json={
                "owner": "openclaw",
                "run_id": "run-captcha",
                "status": "blocked",
                "message": "Suno hCaptcha manual verification is required at https://suno.com/create.",
            },
        )
        with SessionLocal() as db:
            db.add(
                Playlist(
                    title="Ready Metadata Release",
                    status=PlaylistStatus.ready,
                    metadata_json={
                        "workflow_state": "metadata_review",
                        "youtube_channel_title": "Soft Hour Radio",
                    },
                )
            )
            db.commit()

            evaluation = evaluate_openclaw_backlog_scheduler(db, services)

        assert evaluation["should_request"] is False
        assert evaluation["reason"] == "recent_openclaw_manual_blocker"
        assert evaluation["finishable_channels"] == ["Soft Hour Radio"]
    finally:
        clear_isolated_client_env()


def test_openclaw_backlog_scheduler_resumes_blocked_release_after_backoff(tmp_path) -> None:
    os.environ["AIMP_OPENCLAW_BACKLOG_SCHEDULER_ENABLED"] = "true"
    os.environ["AIMP_OPENCLAW_BACKLOG_REQUEST_COOLDOWN_SECONDS"] = "0"
    os.environ["AIMP_OPENCLAW_MANUAL_BLOCKER_BACKOFF_SECONDS"] = "0"
    os.environ["AIMP_OPENCLAW_SLACK_CHANNEL_ID"] = "C0AVBUYP150"
    client = create_isolated_client(tmp_path)
    try:
        services = client.app.state.services
        services.youtube.get_status = lambda: {
            "configured": True,
            "authenticated": True,
            "ready": True,
            "channels": [{"id": "UC_TOKYO", "title": "Tokyo Daydream Radio"}],
        }
        client.post(
            "/api/openclaw/lock/start",
            json={
                "owner": "openclaw",
                "run_id": "run-captcha",
                "operation": "backlog-pass",
                "channel_title": "Tokyo Daydream Radio",
                "release_id": "release-captcha",
            },
        )
        client.post(
            "/api/openclaw/lock/finish",
            json={
                "owner": "openclaw",
                "run_id": "run-captcha",
                "status": "blocked",
                "message": "Suno hCaptcha manual verification is required at https://suno.com/create.",
            },
        )

        with SessionLocal() as db:
            evaluation = evaluate_openclaw_backlog_scheduler(db, services)

        assert evaluation["should_request"] is True
        assert evaluation["reason"] == "resume_openclaw_manual_blocker"
        assert evaluation["last_finished_lock"]["release_id"] == "release-captcha"
        assert evaluation["summary"]["manual_blocker"]["last_finished_lock"]["release_id"] == "release-captcha"
    finally:
        clear_isolated_client_env()


def test_video_render_completed_event_posts_openclaw_request_after_lock_is_free(tmp_path) -> None:
    os.environ["AIMP_OPENCLAW_REQUEST_NEXT_ON_VIDEO_RENDER_EVENTS"] = "true"
    os.environ["AIMP_OPENCLAW_SLACK_CHANNEL_ID"] = "C0AVBUYP150"
    os.environ["AIMP_SLACK_BOT_TOKEN"] = "xoxb-test"
    client = create_isolated_client(tmp_path)
    calls = []

    async def fake_post_plain_message(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(ok=True, channel=kwargs["channel"], ts="123.456", raw={"ok": True})

    try:
        services = client.app.state.services
        services.youtube.get_status = lambda: {
            "configured": True,
            "authenticated": True,
            "ready": True,
            "channels": [
                {"id": "UC_SOFT", "title": "Soft Hour Radio"},
                {"id": "UC_TOKYO", "title": "Tokyo Daydream Radio"},
            ],
        }
        services.slack.post_plain_message = fake_post_plain_message
        with SessionLocal() as db:
            playlist = Playlist(
                title="Rendered Cafe Playlist",
                status=PlaylistStatus.ready,
                target_duration_seconds=2400,
                actual_duration_seconds=2400,
                metadata_json={
                    "workflow_state": "metadata_review",
                    "youtube_channel_title": "Soft Hour Radio",
                },
            )
            db.add(playlist)
            db.flush()
            job = Job(
                type=JobType.build_video,
                status=JobStatus.running,
                source="web:render-video",
                playlist=playlist,
                playlist_id=playlist.id,
                payload_json={"playlist_id": playlist.id},
                result_json={},
            )
            db.add(job)
            db.commit()
            playlist_id = playlist.id
            job_id = job.id

        services.worker._post_openclaw_video_event_request_when_unlocked(
            playlist_id=playlist_id,
            job_id=job_id,
            event="video_render_completed",
            reason="video_render_completed",
        )

        assert len(calls) == 1
        assert calls[0]["channel"] == "C0AVBUYP150"
        assert "scheduler_reason: video_render_completed" in calls[0]["text"]
        assert "docs/openclaw-backlog-queue.md" in calls[0]["text"]
        assert "Soft Hour Radio: 1 unfinished" in calls[0]["text"]
        assert "Tokyo Daydream Radio: 0 unfinished" in calls[0]["text"]
        with SessionLocal() as db:
            updated = db.get(Playlist, playlist_id)
            assert updated.metadata_json["openclaw_video_render_completed_request_job_id"] == job_id
            assert updated.metadata_json["openclaw_video_render_completed_request"]["ok"] is True
    finally:
        clear_isolated_client_env()


def test_video_render_started_event_does_not_post_openclaw_request(tmp_path) -> None:
    os.environ["AIMP_OPENCLAW_REQUEST_NEXT_ON_VIDEO_RENDER_EVENTS"] = "true"
    os.environ["AIMP_OPENCLAW_SLACK_CHANNEL_ID"] = "C0AVBUYP150"
    os.environ["AIMP_SLACK_BOT_TOKEN"] = "xoxb-test"
    client = create_isolated_client(tmp_path)
    calls = []

    async def fake_post_plain_message(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(ok=True, channel=kwargs["channel"], ts="123.456", raw={"ok": True})

    try:
        services = client.app.state.services
        services.slack.post_plain_message = fake_post_plain_message
        services.worker._post_openclaw_video_event_request_when_unlocked(
            playlist_id=str(uuid4()),
            job_id=str(uuid4()),
            event="video_render_started",
            reason="video_render_started",
        )

        assert calls == []
    finally:
        clear_isolated_client_env()


def test_video_render_completed_event_does_not_wait_when_openclaw_lock_is_active(tmp_path) -> None:
    os.environ["AIMP_OPENCLAW_REQUEST_NEXT_ON_VIDEO_RENDER_EVENTS"] = "true"
    os.environ["AIMP_OPENCLAW_SLACK_CHANNEL_ID"] = "C0AVBUYP150"
    os.environ["AIMP_SLACK_BOT_TOKEN"] = "xoxb-test"
    client = create_isolated_client(tmp_path)
    calls = []

    async def fake_post_plain_message(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(ok=True, channel=kwargs["channel"], ts="123.456", raw={"ok": True})

    try:
        services = client.app.state.services
        services.slack.post_plain_message = fake_post_plain_message
        with SessionLocal() as db:
            playlist = Playlist(
                title="Rendered While OpenClaw Busy",
                status=PlaylistStatus.ready,
                target_duration_seconds=2400,
                actual_duration_seconds=2400,
                metadata_json={
                    "workflow_state": "metadata_review",
                    "youtube_channel_title": "Soft Hour Radio",
                },
            )
            db.add(playlist)
            db.flush()
            job = Job(
                type=JobType.build_video,
                status=JobStatus.succeeded,
                source="web:render-video",
                playlist=playlist,
                playlist_id=playlist.id,
                payload_json={"playlist_id": playlist.id},
                result_json={},
            )
            db.add(job)
            db.commit()
            playlist_id = playlist.id
            job_id = job.id

        lock_response = client.post(
            "/api/openclaw/lock/start",
            json={"owner": "openclaw", "run_id": "run-1", "operation": "producer"},
        )
        assert lock_response.status_code == 200

        services.worker._post_openclaw_video_event_request_when_unlocked(
            playlist_id=playlist_id,
            job_id=job_id,
            event="video_render_completed",
            reason="video_render_completed",
        )

        assert calls == []
        with SessionLocal() as db:
            updated = db.get(Playlist, playlist_id)
            result = updated.metadata_json["openclaw_video_render_completed_request"]
            assert result["skipped"] is True
            assert result["reason"] == "openclaw_lock_active"
            assert updated.metadata_json["openclaw_video_render_completed_request_job_id"] == job_id
    finally:
        clear_isolated_client_env()


def test_openclaw_auto_loop_upload_limit_stops_after_n_uploads(tmp_path) -> None:
    common = {
        "storage_root": tmp_path,
        "max_uploads": 3,
        "channel_id": "C0AVBUYP150",
        "trigger_prefix": "OPENCLAW_RUN:",
    }

    first = record_auto_loop_upload(
        **common,
        playlist_id="playlist-1",
        youtube_video_id="yt-1",
    )
    second = record_auto_loop_upload(
        **common,
        playlist_id="playlist-2",
        youtube_video_id="yt-2",
    )
    third = record_auto_loop_upload(
        **common,
        playlist_id="playlist-3",
        youtube_video_id="yt-3",
    )
    duplicate = record_auto_loop_upload(
        **common,
        playlist_id="playlist-3",
        youtube_video_id="yt-3",
    )

    assert first["should_request_next"] is True
    assert first["completed_uploads"] == 1
    assert first["remaining_uploads"] == 2
    assert second["should_request_next"] is True
    assert second["completed_uploads"] == 2
    assert second["remaining_uploads"] == 1
    assert third["should_request_next"] is False
    assert third["reason"] == "max_uploads_reached"
    assert third["completed_uploads"] == 3
    assert third["remaining_uploads"] == 0
    assert duplicate["should_request_next"] is False
    assert duplicate["completed_uploads"] == 3


def test_openclaw_auto_loop_unlimited_can_be_stopped_and_resumed(tmp_path) -> None:
    common = {
        "storage_root": tmp_path,
        "max_uploads": 0,
        "channel_id": "C0AVBUYP150",
        "trigger_prefix": "OPENCLAW_RUN:",
    }

    first = record_auto_loop_upload(
        **common,
        playlist_id="playlist-1",
        youtube_video_id="yt-1",
    )
    stopped = handle_auto_loop_control_message(
        storage_root=tmp_path,
        text="OpenClaw 자동화 멈춰",
        user_id="U123",
        channel_id="C0AVBUYP150",
        message_ts="111.222",
    )
    blocked = record_auto_loop_upload(
        **common,
        playlist_id="playlist-2",
        youtube_video_id="yt-2",
    )
    resumed = handle_auto_loop_control_message(
        storage_root=tmp_path,
        text="OPENCLAW_LOOP_START",
        user_id="U123",
        channel_id="C0AVBUYP150",
        message_ts="333.444",
    )
    after_resume = record_auto_loop_upload(
        **common,
        playlist_id="playlist-2",
        youtube_video_id="yt-2",
    )

    assert first["should_request_next"] is True
    assert first["limited"] is False
    assert first["reason"] == "unlimited"
    assert stopped["action"] == "stop"
    assert blocked["should_request_next"] is False
    assert blocked["reason"] == "auto_loop_stopped"
    assert blocked["stop_requested_by"] == "U123"
    assert resumed["action"] == "start"
    assert after_resume["should_request_next"] is True
    assert after_resume["reason"] == "unlimited"


def drain_background_jobs(client: TestClient, max_jobs: int = 10) -> int:
    processed = 0
    while client.app.state.services.worker.process_pending_once():
        processed += 1
        if processed >= max_jobs:
            raise AssertionError("Background worker exceeded expected job count.")
    return processed


def install_fake_ops_slack(services, ops_calls: list[dict]) -> None:
    def call_text(kwargs: dict) -> str:
        if kwargs.get("text"):
            return kwargs["text"]
        if kwargs.get("initial_comment"):
            return kwargs["initial_comment"]
        blocks = kwargs.get("blocks") or []
        if blocks:
            text = blocks[0].get("text") or {}
            return str(text.get("text") or "")
        return ""

    async def fake_post_ops_message(**kwargs):
        ops_calls.append({**kwargs, "text": call_text(kwargs)})
        return SimpleNamespace(ok=True, channel="COPS", ts=f"123.{len(ops_calls)}", raw={"ok": True})

    async def fake_upload_local_file(**kwargs):
        ops_calls.append({**kwargs, "text": call_text(kwargs)})
        return SimpleNamespace(
            ok=True,
            channel="COPS",
            ts=f"123.{len(ops_calls)}",
            file_id=f"F{len(ops_calls)}",
            raw={"ok": True},
        )

    services.slack.post_ops_message = fake_post_ops_message
    services.slack.upload_local_file = fake_upload_local_file


def upload_test_loop_video(client: TestClient, workspace_id: str, *, provider: str = "") -> dict:
    original_validator = playlist_routes._validate_loop_video_file
    playlist_routes._validate_loop_video_file = lambda *_args, **_kwargs: None
    data = {"actor": "test-suite", "smooth_loop": "true"}
    if provider:
        data["loop_video_provider"] = provider
    try:
        loop_response = client.post(
            f"/api/playlists/{workspace_id}/loop-video/upload",
            data=data,
            files={"loop_video_file": ("test-loop.mp4", b"fake-loop-mp4", "video/mp4")},
        )
    finally:
        playlist_routes._validate_loop_video_file = original_validator
    assert loop_response.status_code == 200
    payload = loop_response.json()
    assert payload["loop_video_path"].endswith(".mp4")
    return payload


def test_external_render_worker_claim_upload_and_complete(tmp_path) -> None:
    try:
        os.environ["AIMP_VIDEO_RENDER_EXECUTION_MODE"] = "external"
        os.environ["AIMP_RENDER_WORKER_SHARED_TOKEN"] = "test-render-token"
        client = create_isolated_client(tmp_path)
        services = client.app.state.services
        services.settings.slack_bot_token = "xoxb-test"
        services.settings.slack_ops_channel_id = "#all-ai-music-playlist-generator"
        ops_calls = []

        install_fake_ops_slack(services, ops_calls)
        storage = tmp_path / "storage"
        playlist_dir = storage / "playlists"
        track_dir = storage / "tracks"
        playlist_dir.mkdir(parents=True, exist_ok=True)
        track_dir.mkdir(parents=True, exist_ok=True)

        audio_path = playlist_dir / "release-audio.mp3"
        cover_path = playlist_dir / "cover.png"
        loop_path = playlist_dir / "loop.mp4"
        track_path = track_dir / "track.mp3"
        audio_path.write_bytes(b"fake-audio")
        loop_path.write_bytes(b"fake-loop")
        track_path.write_bytes(b"fake-track")
        Image.new("RGB", (1280, 720), "navy").save(cover_path)

        with SessionLocal() as db:
            track = Track(
                title="External Worker Track",
                prompt="test prompt",
                status=TrackStatus.approved,
                duration_seconds=60,
                audio_path=str(track_path),
                metadata_json={"style": "test"},
            )
            playlist = Playlist(
                title="[playlist] External Worker Release | Long Render Subtitle",
                status=PlaylistStatus.building,
                target_duration_seconds=60,
                actual_duration_seconds=60,
                output_audio_path=str(audio_path),
                metadata_json={
                    "workflow_state": "video_queued",
                    "cover_image_path": str(cover_path),
                    "cover_approved": True,
                    "loop_video_path": str(loop_path),
                    "loop_video_smooth": True,
                    "video_spectrum_overlay_style": "bars",
                },
            )
            db.add_all([track, playlist])
            db.flush()
            db.add(PlaylistItem(playlist_id=playlist.id, track_id=track.id, order_index=1, included_duration_seconds=60))
            job = Job(
                type=JobType.build_video,
                status=JobStatus.queued,
                source="web:render-video",
                playlist_id=playlist.id,
                payload_json={"video_spectrum_overlay_style": "bars"},
                result_json={},
            )
            db.add(job)
            db.commit()
            job_id = job.id
            playlist_id = playlist.id

        headers = {"X-Render-Worker-Token": "test-render-token"}
        claim = client.post(
            "/api/render-worker/jobs/claim",
            headers=headers,
            json={"worker_id": "test-worker", "hostname": "test-host"},
        )
        assert claim.status_code == 200
        claim_payload = claim.json()
        assert claim_payload["job"]["id"] == job_id
        assert claim_payload["job"]["render"]["mode"] == "loop_video"
        assert "Render worker claimed" in ops_calls[-1]["text"]
        assert "제목: External Worker Release" in ops_calls[-1]["text"]
        assert "Long Render Subtitle" not in ops_calls[-1]["text"]
        assert "작업자: test-worker" in ops_calls[-1]["text"]
        assert "Queued for:" in ops_calls[-1]["text"]
        assert job_id not in ops_calls[-1]["text"]
        assert ops_calls[-1]["file_path"] == str(cover_path)

        nickname = client.post(
            "/api/playlists/render-workers/test-worker/nickname",
            json={"nickname": "Test Render Box", "actor": "test-suite"},
        )
        assert nickname.status_code == 200
        assert nickname.json()["updated_jobs"] == 1

        workspace_response = client.get(f"/api/playlists/workspaces/{playlist_id}")
        assert workspace_response.status_code == 200
        assert workspace_response.json()["render_job"]["external_render_worker"]["nickname"] == "Test Render Box"

        progress = client.post(
            f"/api/render-worker/jobs/{job_id}/progress",
            headers=headers,
            json={
                "worker_id": "test-worker",
                "progress": {"stage": "video_render", "status": "running", "percent": 10.0},
            },
        )
        assert progress.status_code == 200
        throttled_progress = client.post(
            f"/api/render-worker/jobs/{job_id}/progress",
            headers=headers,
            json={
                "worker_id": "test-worker",
                "progress": {"stage": "video_render", "status": "running", "percent": 10.5},
            },
        )
        assert throttled_progress.status_code == 200
        with SessionLocal() as db:
            job = db.get(Job, job_id)
            assert job.result_json["progress"]["percent"] == 10.0
        committed_progress = client.post(
            f"/api/render-worker/jobs/{job_id}/progress",
            headers=headers,
            json={
                "worker_id": "test-worker",
                "progress": {"stage": "video_render", "status": "running", "percent": 11.0},
            },
        )
        assert committed_progress.status_code == 200
        with SessionLocal() as db:
            job = db.get(Job, job_id)
            assert job.result_json["progress"]["percent"] == 11.0

        payload = b"fake-rendered-video"
        first = client.put(
            f"/api/render-worker/jobs/{job_id}/upload",
            headers={**headers, "Content-Range": f"bytes 0-7/{len(payload)}"},
            content=payload[:8],
        )
        assert first.status_code == 200
        status_response = client.get(f"/api/render-worker/jobs/{job_id}/upload-status", headers=headers)
        assert status_response.status_code == 200
        assert status_response.json()["received_bytes"] == 8
        second = client.put(
            f"/api/render-worker/jobs/{job_id}/upload",
            headers={**headers, "Content-Range": f"bytes 8-{len(payload) - 1}/{len(payload)}"},
            content=payload[8:],
        )
        assert second.status_code == 200
        complete = client.post(
            f"/api/render-worker/jobs/{job_id}/complete",
            headers=headers,
            json={
                "worker_id": "test-worker",
                "size_bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            },
        )
        assert complete.status_code == 200
        assert "Render worker completed" in ops_calls[-1]["text"]
        assert "제목: External Worker Release" in ops_calls[-1]["text"]
        assert "작업자: Test Render Box" in ops_calls[-1]["text"]
        assert "(test-worker)" not in ops_calls[-1]["text"]
        assert "Elapsed:" in ops_calls[-1]["text"]
        assert job_id not in ops_calls[-1]["text"]

        with SessionLocal() as db:
            job = db.get(Job, job_id)
            playlist = db.get(Playlist, playlist_id)
            assert job.status == JobStatus.succeeded
            assert job.result_json["external_render_worker"]["nickname"] == "Test Render Box"
            assert playlist.status == PlaylistStatus.ready
            assert playlist.output_video_path
            assert Path(playlist.output_video_path).read_bytes() == payload
            assert playlist.metadata_json["workflow_state"] == "metadata_review"
            assert playlist.metadata_json["video_render_progress"]["status"] == "end"
    finally:
        clear_isolated_client_env()


def test_render_worker_claim_forces_no_spectrum_for_religious_channel(tmp_path) -> None:
    try:
        os.environ["AIMP_VIDEO_RENDER_EXECUTION_MODE"] = "external"
        os.environ["AIMP_RENDER_WORKER_SHARED_TOKEN"] = "test-render-token"
        client = create_isolated_client(tmp_path)
        settings = client.app.state.settings
        playlist_dir = settings.playlists_dir
        track_dir = settings.tracks_dir
        playlist_dir.mkdir(parents=True, exist_ok=True)
        track_dir.mkdir(parents=True, exist_ok=True)

        audio_path = playlist_dir / "scripture-audio.mp3"
        cover_path = playlist_dir / "scripture-cover.png"
        loop_path = playlist_dir / "scripture-loop.mp4"
        track_path = track_dir / "scripture-track.mp3"
        audio_path.write_bytes(b"fake-audio")
        loop_path.write_bytes(b"fake-loop")
        track_path.write_bytes(b"fake-track")
        Image.new("RGB", (1280, 720), "black").save(cover_path)

        with SessionLocal() as db:
            track = Track(
                title="Scripture Track",
                prompt="Genesis scripture",
                status=TrackStatus.approved,
                duration_seconds=60,
                audio_path=str(track_path),
                metadata_json={"style": "scripture jazz"},
            )
            playlist = Playlist(
                title="[playlist] Genesis Creation Light",
                status=PlaylistStatus.building,
                target_duration_seconds=60,
                actual_duration_seconds=60,
                output_audio_path=str(audio_path),
                metadata_json={
                    "youtube_channel_title": "The Old Verse",
                    "scripture_passage_range": "Genesis 1:1-5",
                    "workflow_state": "video_queued",
                    "cover_image_path": str(cover_path),
                    "cover_approved": True,
                    "loop_video_path": str(loop_path),
                    "video_spectrum_overlay_style": "radial",
                },
            )
            db.add_all([track, playlist])
            db.flush()
            db.add(PlaylistItem(playlist_id=playlist.id, track_id=track.id, order_index=1, included_duration_seconds=60))
            job = Job(
                type=JobType.build_video,
                status=JobStatus.queued,
                source="web:render-video",
                playlist_id=playlist.id,
                payload_json={"video_spectrum_overlay_style": "pulse"},
                result_json={},
            )
            db.add(job)
            db.commit()
            playlist_id = playlist.id

        claim = client.post(
            "/api/render-worker/jobs/claim",
            headers={"X-Render-Worker-Token": "test-render-token"},
            json={"worker_id": "test-worker", "hostname": "test-host"},
        )

        assert claim.status_code == 200
        assert claim.json()["job"]["render"]["video_spectrum_overlay_style"] == "none"
        with SessionLocal() as db:
            playlist = db.get(Playlist, playlist_id)
            assert playlist.metadata_json["video_spectrum_overlay_style"] == "none"
    finally:
        clear_isolated_client_env()


def test_render_worker_claim_prioritizes_resolution_by_worker_profile(tmp_path) -> None:
    try:
        os.environ["AIMP_VIDEO_RENDER_EXECUTION_MODE"] = "external"
        os.environ["AIMP_RENDER_WORKER_SHARED_TOKEN"] = "test-render-token"
        client = create_isolated_client(tmp_path)
        services = client.app.state.services
        playlist_dir = services.settings.playlists_dir
        track_dir = services.settings.tracks_dir
        playlist_dir.mkdir(parents=True, exist_ok=True)
        track_dir.mkdir(parents=True, exist_ok=True)

        audio_path = playlist_dir / "priority-audio.mp3"
        cover_path = playlist_dir / "priority-cover.png"
        loop_path = playlist_dir / "priority-loop.mp4"
        track_path = track_dir / "priority-track.mp3"
        audio_path.write_bytes(b"fake-audio")
        loop_path.write_bytes(b"fake-loop")
        track_path.write_bytes(b"fake-track")
        Image.new("RGB", (1280, 720), "black").save(cover_path)

        with SessionLocal() as db:
            track = Track(
                title="Priority Track",
                prompt="test prompt",
                status=TrackStatus.approved,
                duration_seconds=60,
                audio_path=str(track_path),
                metadata_json={},
            )
            low = Playlist(
                title="Low Resolution First",
                status=PlaylistStatus.building,
                target_duration_seconds=60,
                actual_duration_seconds=60,
                output_audio_path=str(audio_path),
                metadata_json={
                    "workflow_state": "video_queued",
                    "cover_image_path": str(cover_path),
                    "cover_approved": True,
                    "loop_video_path": str(loop_path),
                    "video_render_resolution": "720p",
                    "video_render_source_mode": "loop_video",
                },
            )
            high = Playlist(
                title="High Resolution Cinematic",
                status=PlaylistStatus.building,
                target_duration_seconds=60,
                actual_duration_seconds=60,
                output_audio_path=str(audio_path),
                metadata_json={
                    "youtube_channel_title": "Cinematic Pulse",
                    "workflow_state": "video_queued",
                    "cover_image_path": str(cover_path),
                    "cover_approved": True,
                    "video_render_resolution": "2k",
                    "video_render_source_mode": "still_image",
                },
            )
            db.add_all([track, low, high])
            db.flush()
            db.add_all(
                [
                    PlaylistItem(playlist_id=low.id, track_id=track.id, order_index=1, included_duration_seconds=60),
                    PlaylistItem(playlist_id=high.id, track_id=track.id, order_index=1, included_duration_seconds=60),
                ]
            )
            low_job = Job(
                type=JobType.build_video,
                status=JobStatus.queued,
                source="web:render-video",
                playlist_id=low.id,
                payload_json={"video_render_resolution": "720p", "video_render_source_mode": "loop_video"},
                result_json={},
            )
            high_job = Job(
                type=JobType.build_video,
                status=JobStatus.queued,
                source="web:render-video",
                playlist_id=high.id,
                payload_json={
                    "allow_still_image_fallback": True,
                    "video_render_resolution": "2k",
                    "video_render_source_mode": "still_image",
                },
                result_json={},
            )
            db.add_all([low_job, high_job])
            db.commit()
            low_job_id = low_job.id
            high_job_id = high_job.id

        headers = {"X-Render-Worker-Token": "test-render-token"}
        desktop_claim = client.post(
            "/api/render-worker/jobs/claim",
            headers=headers,
            json={
                "worker_id": "desktop-render",
                "hostname": "home-desktop",
                "capabilities": {"worker_profile": "desktop", "max_render_height": 1440},
            },
        )
        assert desktop_claim.status_code == 200
        assert desktop_claim.json()["job"]["id"] == high_job_id
        assert desktop_claim.json()["job"]["render"]["video_render_resolution"] == "2k"
        assert desktop_claim.json()["job"]["render"]["mode"] == "still_image"

        oracle_claim = client.post(
            "/api/render-worker/jobs/claim",
            headers=headers,
            json={
                "worker_id": "oracle-render",
                "hostname": "oracle-instance",
                "capabilities": {"worker_profile": "oracle", "max_render_height": 720},
            },
        )
        assert oracle_claim.status_code == 200
        assert oracle_claim.json()["job"]["id"] == low_job_id
        assert oracle_claim.json()["job"]["render"]["video_render_resolution"] == "720p"
        assert oracle_claim.json()["job"]["render"]["mode"] == "loop_video"
    finally:
        clear_isolated_client_env()


def test_render_worker_claim_can_prefer_no_lyrics_jobs(tmp_path) -> None:
    try:
        os.environ["AIMP_VIDEO_RENDER_EXECUTION_MODE"] = "external"
        os.environ["AIMP_RENDER_WORKER_SHARED_TOKEN"] = "test-render-token"
        client = create_isolated_client(tmp_path)
        services = client.app.state.services
        playlist_dir = services.settings.playlists_dir
        track_dir = services.settings.tracks_dir
        playlist_dir.mkdir(parents=True, exist_ok=True)
        track_dir.mkdir(parents=True, exist_ok=True)

        audio_path = playlist_dir / "lyrics-priority-audio.mp3"
        cover_path = playlist_dir / "lyrics-priority-cover.png"
        loop_path = playlist_dir / "lyrics-priority-loop.mp4"
        vocal_track_path = track_dir / "lyrics-priority-vocal.mp3"
        instrumental_track_path = track_dir / "lyrics-priority-instrumental.mp3"
        audio_path.write_bytes(b"fake-audio")
        loop_path.write_bytes(b"fake-loop")
        vocal_track_path.write_bytes(b"fake-vocal-track")
        instrumental_track_path.write_bytes(b"fake-instrumental-track")
        Image.new("RGB", (1280, 720), "black").save(cover_path)

        with SessionLocal() as db:
            vocal_track = Track(
                title="Vocal Track",
                prompt="test prompt",
                status=TrackStatus.approved,
                duration_seconds=60,
                audio_path=str(vocal_track_path),
                metadata_json={"lyrics": "[Verse]\nRain over Seoul tonight"},
            )
            instrumental_track = Track(
                title="Instrumental Track",
                prompt="test prompt",
                status=TrackStatus.approved,
                duration_seconds=60,
                audio_path=str(instrumental_track_path),
                metadata_json={"lyrics": "[Instrumental]\nno vocals"},
            )
            vocal_playlist = Playlist(
                title="Older Vocal Release",
                status=PlaylistStatus.building,
                target_duration_seconds=60,
                actual_duration_seconds=60,
                output_audio_path=str(audio_path),
                metadata_json={
                    "workflow_state": "video_queued",
                    "cover_image_path": str(cover_path),
                    "cover_approved": True,
                    "loop_video_path": str(loop_path),
                    "video_render_resolution": "720p",
                    "video_render_source_mode": "loop_video",
                },
            )
            instrumental_playlist = Playlist(
                title="Newer Instrumental Release",
                status=PlaylistStatus.building,
                target_duration_seconds=60,
                actual_duration_seconds=60,
                output_audio_path=str(audio_path),
                metadata_json={
                    "workflow_state": "video_queued",
                    "cover_image_path": str(cover_path),
                    "cover_approved": True,
                    "loop_video_path": str(loop_path),
                    "video_render_resolution": "720p",
                    "video_render_source_mode": "loop_video",
                },
            )
            db.add_all([vocal_track, instrumental_track, vocal_playlist, instrumental_playlist])
            db.flush()
            db.add_all(
                [
                    PlaylistItem(
                        playlist_id=vocal_playlist.id,
                        track_id=vocal_track.id,
                        order_index=1,
                        included_duration_seconds=60,
                    ),
                    PlaylistItem(
                        playlist_id=instrumental_playlist.id,
                        track_id=instrumental_track.id,
                        order_index=1,
                        included_duration_seconds=60,
                    ),
                ]
            )
            vocal_job = Job(
                type=JobType.build_video,
                status=JobStatus.queued,
                source="web:render-video",
                playlist_id=vocal_playlist.id,
                payload_json={"video_render_resolution": "720p", "video_render_source_mode": "loop_video"},
                result_json={},
                created_at=datetime.now(timezone.utc) - timedelta(minutes=5),
            )
            instrumental_job = Job(
                type=JobType.build_video,
                status=JobStatus.queued,
                source="web:render-video",
                playlist_id=instrumental_playlist.id,
                payload_json={"video_render_resolution": "720p", "video_render_source_mode": "loop_video"},
                result_json={},
                created_at=datetime.now(timezone.utc),
            )
            db.add_all([vocal_job, instrumental_job])
            db.commit()
            instrumental_job_id = instrumental_job.id

        claim = client.post(
            "/api/render-worker/jobs/claim",
            headers={"X-Render-Worker-Token": "test-render-token"},
            json={
                "worker_id": "oracle-render",
                "hostname": "oracle-instance",
                "capabilities": {
                    "worker_profile": "oracle",
                    "max_render_height": 720,
                },
            },
        )

        assert claim.status_code == 200
        body = claim.json()
        assert body["job"]["id"] == instrumental_job_id
        assert body["job"]["title"] == "Newer Instrumental Release"
    finally:
        clear_isolated_client_env()


def test_render_worker_claim_requires_whisper_capability_for_lyric_jobs(tmp_path) -> None:
    try:
        os.environ["AIMP_VIDEO_RENDER_EXECUTION_MODE"] = "external"
        os.environ["AIMP_RENDER_WORKER_SHARED_TOKEN"] = "test-render-token"
        client = create_isolated_client(tmp_path)
        services = client.app.state.services
        playlist_dir = services.settings.playlists_dir
        track_dir = services.settings.tracks_dir
        playlist_dir.mkdir(parents=True, exist_ok=True)
        track_dir.mkdir(parents=True, exist_ok=True)

        audio_path = playlist_dir / "lyrics-capability-audio.mp3"
        cover_path = playlist_dir / "lyrics-capability-cover.png"
        loop_path = playlist_dir / "lyrics-capability-loop.mp4"
        track_path = track_dir / "lyrics-capability-track.mp3"
        audio_path.write_bytes(b"fake-audio")
        loop_path.write_bytes(b"fake-loop")
        track_path.write_bytes(b"fake-track")
        Image.new("RGB", (1280, 720), "black").save(cover_path)

        with SessionLocal() as db:
            track = Track(
                title="Lyric Track",
                prompt="test prompt",
                status=TrackStatus.approved,
                duration_seconds=60,
                audio_path=str(track_path),
                metadata_json={"lyrics": "first line\nsecond line"},
            )
            lyric_playlist = Playlist(
                title="Lyric Whisper Render",
                status=PlaylistStatus.building,
                target_duration_seconds=60,
                actual_duration_seconds=60,
                output_audio_path=str(audio_path),
                metadata_json={
                    "workflow_state": "video_queued",
                    "cover_image_path": str(cover_path),
                    "cover_approved": True,
                    "loop_video_path": str(loop_path),
                },
            )
            plain_playlist = Playlist(
                title="Plain Render",
                status=PlaylistStatus.building,
                target_duration_seconds=60,
                actual_duration_seconds=60,
                output_audio_path=str(audio_path),
                metadata_json={
                    "workflow_state": "video_queued",
                    "cover_image_path": str(cover_path),
                    "cover_approved": True,
                    "loop_video_path": str(loop_path),
                },
            )
            db.add_all([track, lyric_playlist, plain_playlist])
            db.flush()
            db.add_all(
                [
                    PlaylistItem(
                        playlist_id=lyric_playlist.id,
                        track_id=track.id,
                        order_index=1,
                        included_duration_seconds=60,
                    ),
                    PlaylistItem(
                        playlist_id=plain_playlist.id,
                        track_id=track.id,
                        order_index=1,
                        included_duration_seconds=60,
                    ),
                ]
            )
            lyric_job = Job(
                type=JobType.build_video,
                status=JobStatus.queued,
                source="web:render-video",
                playlist_id=lyric_playlist.id,
                payload_json={"video_lyrics_overlay_enabled": True, "video_lyrics_alignment_mode": "whisper"},
                result_json={},
            )
            plain_job = Job(
                type=JobType.build_video,
                status=JobStatus.queued,
                source="web:render-video",
                playlist_id=plain_playlist.id,
                payload_json={"video_lyrics_overlay_enabled": False},
                result_json={},
            )
            db.add_all([lyric_job, plain_job])
            db.commit()
            lyric_job_id = lyric_job.id
            plain_job_id = plain_job.id

        headers = {"X-Render-Worker-Token": "test-render-token"}
        legacy_claim = client.post(
            "/api/render-worker/jobs/claim",
            headers=headers,
            json={
                "worker_id": "legacy-oracle",
                "hostname": "oracle-instance",
                "capabilities": {"worker_profile": "oracle", "max_render_height": 720},
            },
        )
        assert legacy_claim.status_code == 200
        assert legacy_claim.json()["job"]["id"] == plain_job_id

        legacy_empty_claim = client.post(
            "/api/render-worker/jobs/claim",
            headers=headers,
            json={
                "worker_id": "legacy-oracle-2",
                "hostname": "oracle-instance-2",
                "capabilities": {"worker_profile": "oracle", "max_render_height": 720},
            },
        )
        assert legacy_empty_claim.status_code == 200
        assert legacy_empty_claim.json()["job"] is None

        whisper_claim = client.post(
            "/api/render-worker/jobs/claim",
            headers=headers,
            json={
                "worker_id": "updated-worker",
                "hostname": "updated-host",
                "capabilities": {
                    "worker_profile": "oracle",
                    "max_render_height": 720,
                    "faster_whisper": True,
                    "lyrics_alignment_modes": ["timeline", "whisper"],
                },
            },
        )
        assert whisper_claim.status_code == 200
        assert whisper_claim.json()["job"]["id"] == lyric_job_id
        assert whisper_claim.json()["job"]["render"]["video_lyrics_alignment_mode"] == "whisper"
    finally:
        clear_isolated_client_env()


def test_stale_external_render_worker_requeue_posts_ops_slack(tmp_path) -> None:
    try:
        os.environ["AIMP_VIDEO_RENDER_EXECUTION_MODE"] = "external"
        os.environ["AIMP_RENDER_WORKER_SHARED_TOKEN"] = "test-render-token"
        os.environ["AIMP_RENDER_WORKER_CLAIM_TIMEOUT_SECONDS"] = "21600"
        client = create_isolated_client(tmp_path)
        services = client.app.state.services
        services.settings.slack_bot_token = "xoxb-test"
        services.settings.slack_ops_channel_id = "#all-ai-music-playlist-generator"
        ops_calls = []

        install_fake_ops_slack(services, ops_calls)
        storage = tmp_path / "storage"
        playlist_dir = storage / "playlists"
        track_dir = storage / "tracks"
        playlist_dir.mkdir(parents=True, exist_ok=True)
        track_dir.mkdir(parents=True, exist_ok=True)
        audio_path = playlist_dir / "stale-audio.mp3"
        cover_path = playlist_dir / "stale-cover.png"
        loop_path = playlist_dir / "stale-loop.mp4"
        track_path = track_dir / "stale-track.mp3"
        audio_path.write_bytes(b"fake-audio")
        loop_path.write_bytes(b"fake-loop")
        track_path.write_bytes(b"fake-track")
        Image.new("RGB", (1280, 720), "purple").save(cover_path)
        stale_heartbeat = (datetime.now(timezone.utc) - timedelta(seconds=21630)).isoformat()

        with SessionLocal() as db:
            track = Track(
                title="Stale Worker Track",
                prompt="test prompt",
                status=TrackStatus.approved,
                duration_seconds=60,
                audio_path=str(track_path),
            )
            playlist = Playlist(
                title="Stale Worker Release",
                status=PlaylistStatus.building,
                target_duration_seconds=60,
                actual_duration_seconds=60,
                output_audio_path=str(audio_path),
                metadata_json={
                    "workflow_state": "video_rendering",
                    "cover_image_path": str(cover_path),
                    "cover_approved": True,
                    "loop_video_path": str(loop_path),
                    "loop_video_smooth": True,
                },
            )
            db.add_all([track, playlist])
            db.flush()
            db.add(PlaylistItem(playlist_id=playlist.id, track_id=track.id, order_index=1, included_duration_seconds=60))
            job = Job(
                type=JobType.build_video,
                status=JobStatus.running,
                source="web:render-video",
                playlist_id=playlist.id,
                payload_json={"video_spectrum_overlay_style": "bars"},
                result_json={
                    "external_render_worker": {
                        "worker_id": "stale-worker",
                        "hostname": "old-host",
                        "claimed_at": stale_heartbeat,
                        "heartbeat_at": stale_heartbeat,
                        "rendered_track_ids": [track.id],
                    }
                },
                started_at=datetime.now(timezone.utc) - timedelta(seconds=21630),
            )
            db.add(job)
            db.commit()
            job_id = job.id

        claim = client.post(
            "/api/render-worker/jobs/claim",
            headers={"X-Render-Worker-Token": "test-render-token"},
            json={"worker_id": "fresh-worker", "hostname": "fresh-host"},
        )

        assert claim.status_code == 200
        assert claim.json()["job"]["id"] == job_id
        assert len(ops_calls) == 2
        assert "Render worker timed out" in ops_calls[0]["text"]
        assert "Stale Worker Release" in ops_calls[0]["text"]
        assert "작업자: stale-worker" in ops_calls[0]["text"]
        assert "Timeout: 6h 0m 0s" in ops_calls[0]["text"]
        assert job_id not in ops_calls[0]["text"]
        assert ops_calls[0]["file_path"] == str(cover_path)
        assert "Render worker claimed" in ops_calls[1]["text"]
        assert "작업자: fresh-worker" in ops_calls[1]["text"]
        assert job_id not in ops_calls[1]["text"]
    finally:
        clear_isolated_client_env()


def prepare_release_for_final_publish(client: TestClient, workspace_id: str, *, use_still_fallback: bool = True) -> dict:
    cover_response = client.post(
        f"/api/playlists/{workspace_id}/cover/generate",
        json={"actor": "test-suite"},
    )
    assert cover_response.status_code == 200
    cover = cover_response.json()
    assert cover["workflow_state"] == "cover_review"
    assert cover["cover_image_path"].endswith(".png")

    if not use_still_fallback:
        upload_test_loop_video(client, workspace_id)

    approve_cover_response = client.post(
        f"/api/playlists/{workspace_id}/cover/approve",
        json={"actor": "test-suite", "approved": True},
    )
    assert approve_cover_response.status_code == 200
    assert approve_cover_response.json()["workflow_state"] == "video_required"

    render_video_response = client.post(
        f"/api/playlists/{workspace_id}/video/render",
        json={"actor": "test-suite", "allow_still_image_fallback": use_still_fallback},
    )
    assert render_video_response.status_code == 200
    assert render_video_response.json()["workflow_state"] == "video_queued"
    assert drain_background_jobs(client) == 1

    metadata_response = client.get("/api/playlists/workspaces")
    metadata_ready = next(item for item in metadata_response.json() if item["id"] == workspace_id)
    assert metadata_ready["workflow_state"] == "metadata_review"
    assert metadata_ready["output_video_path"].endswith(".mp4")
    assert metadata_ready["youtube_title"]

    metadata_description = metadata_ready["youtube_description"]
    if "00:00" not in metadata_description:
        metadata_description = f"{metadata_description}\n\n00:00:00 Single Track\n\n#Music #Playlist"
    localizations = {
        language: {
            "title": metadata_ready["youtube_title"],
            "description": metadata_description,
        }
        for language in SUPPORTED_YOUTUBE_LANGUAGES
    }
    approve_metadata_response = client.post(
        f"/api/playlists/{workspace_id}/metadata/approve",
        json={
            "actor": "test-suite",
            "note": "metadata approved",
            "title": metadata_ready["youtube_title"],
            "description": metadata_description,
            "tags": ",".join(metadata_ready["youtube_tags"]),
            "default_language": metadata_ready.get("youtube_default_language") or "ko",
            "localizations": localizations,
        },
    )
    assert approve_metadata_response.status_code == 200, approve_metadata_response.text
    approved = approve_metadata_response.json()
    assert approved["workflow_state"] == "publish_ready"
    assert approved["metadata_approved"] is True
    return approved


def render_workspace_audio(client: TestClient, workspace_id: str) -> dict:
    render_response = client.post(
        f"/api/playlists/{workspace_id}/render-audio",
        json={"actor": "test-suite"},
    )
    assert render_response.status_code == 200
    assert render_response.json()["workflow_state"] == "render_queued"
    assert drain_background_jobs(client) == 1
    workspaces_response = client.get("/api/playlists/workspaces")
    assert workspaces_response.status_code == 200
    workspace = next(item for item in workspaces_response.json() if item["id"] == workspace_id)
    assert workspace["output_audio_path"]
    return workspace


def test_reaching_target_duration_does_not_post_ops_slack(tmp_path) -> None:
    try:
        client = create_isolated_client(tmp_path)
        services = client.app.state.services
        services.settings.slack_bot_token = "xoxb-test"
        services.settings.slack_ops_channel_id = "#all-ai-music-playlist-generator"
        ops_calls = []

        install_fake_ops_slack(services, ops_calls)

        workspace_response = client.post(
            "/api/playlists/workspaces",
            json={
                "title": "No Target Alert Workspace",
                "target_duration_seconds": 60,
            },
        )
        workspace_id = workspace_response.json()["id"]
        local_audio = tmp_path / "target-alert.mp3"
        local_audio.write_bytes(b"fake source")
        track_response = client.post(
            "/api/tracks",
            json={
                "title": "Target Alert Track",
                "prompt": "quiet piano",
                "duration_seconds": 60,
                "audio_path": str(local_audio),
            },
        )
        approve_response = client.post(
            f"/api/tracks/{track_response.json()['id']}/decisions",
            json={
                "decision": "approve",
                "source": "human",
                "actor": "test-suite",
                "playlist_id": workspace_id,
            },
        )

        assert approve_response.status_code == 200
        workspace_after_response = client.get(f"/api/playlists/workspaces/{workspace_id}")
        assert workspace_after_response.status_code == 200
        assert workspace_after_response.json()["publish_ready"] is True
        assert ops_calls == []
    finally:
        clear_isolated_client_env()


def test_video_render_queue_posts_ops_slack(tmp_path) -> None:
    try:
        os.environ["AIMP_VIDEO_RENDER_EXECUTION_MODE"] = "external"
        client = create_isolated_client(tmp_path)
        services = client.app.state.services
        services.settings.slack_bot_token = "xoxb-test"
        services.settings.slack_ops_channel_id = "#all-ai-music-playlist-generator"
        ops_calls = []

        def fake_build_audio(_tracks, output_path):
            output_path.write_bytes(b"fake-mp3")
            return output_path

        install_fake_ops_slack(services, ops_calls)
        services.playlist_builder.build_audio = fake_build_audio

        workspace_response = client.post(
            "/api/playlists/workspaces",
            json={
                "title": "Queued Video Alert Workspace",
                "target_duration_seconds": 60,
            },
        )
        workspace_id = workspace_response.json()["id"]
        local_audio = tmp_path / "queued-video.mp3"
        local_audio.write_bytes(b"fake source")
        track_response = client.post(
            "/api/tracks",
            json={
                "title": "Queued Video Track",
                "prompt": "soft synth",
                "duration_seconds": 60,
                "audio_path": str(local_audio),
            },
        )
        approve_response = client.post(
            f"/api/tracks/{track_response.json()['id']}/decisions",
            json={
                "decision": "approve",
                "source": "human",
                "actor": "test-suite",
                "playlist_id": workspace_id,
            },
        )
        assert approve_response.status_code == 200
        render_workspace_audio(client, workspace_id)

        cover_response = client.post(
            f"/api/playlists/{workspace_id}/cover/generate",
            json={"actor": "test-suite"},
        )
        assert cover_response.status_code == 200
        upload_test_loop_video(client, workspace_id)
        approve_cover_response = client.post(
            f"/api/playlists/{workspace_id}/cover/approve",
            json={"actor": "test-suite", "approved": True},
        )
        assert approve_cover_response.status_code == 200

        render_video_response = client.post(
            f"/api/playlists/{workspace_id}/video/render",
            json={
                "actor": "test-suite",
                "video_spectrum_overlay_style": "thinwave",
            },
        )

        assert render_video_response.status_code == 200
        assert render_video_response.json()["workflow_state"] == "video_queued"
        assert len(ops_calls) == 1
        assert "Video render queued" in ops_calls[0]["text"]
        assert "Queued Video Alert Workspace" in ops_calls[0]["text"]
        assert "Mode: external" in ops_calls[0]["text"]
        assert "Visualizer: bars" in ops_calls[0]["text"]
        assert "job_id" not in ops_calls[0]["text"]
        assert ops_calls[0]["file_path"].endswith(".png")
        with SessionLocal() as db:
            job = db.scalars(
                select(Job).where(Job.playlist_id == workspace_id, Job.type == JobType.build_video)
            ).first()
            assert job.result_json["ops_video_queued_notification"]["ok"] is True
    finally:
        clear_isolated_client_env()


def test_cinematic_pulse_video_render_forces_bar_spectrum(tmp_path) -> None:
    try:
        client = create_isolated_client(tmp_path)
        settings = client.app.state.settings
        playlist_dir = settings.playlists_dir
        track_dir = settings.tracks_dir
        playlist_dir.mkdir(parents=True, exist_ok=True)
        track_dir.mkdir(parents=True, exist_ok=True)

        audio_path = playlist_dir / "cinematic-audio.mp3"
        cover_path = playlist_dir / "cinematic-cover.png"
        track_path = track_dir / "cinematic-track.mp3"
        audio_path.write_bytes(b"fake-audio")
        track_path.write_bytes(b"fake-track")
        Image.new("RGB", (1280, 720), "black").save(cover_path)

        with SessionLocal() as db:
            track = Track(
                title="Cinematic Pulse Track",
                prompt="cinematic orchestra",
                status=TrackStatus.approved,
                duration_seconds=60,
                audio_path=str(track_path),
                metadata_json={"style": "cinematic orchestra"},
            )
            playlist = Playlist(
                title="Cinematic Pulse Render",
                status=PlaylistStatus.ready,
                target_duration_seconds=60,
                actual_duration_seconds=60,
                output_audio_path=str(audio_path),
                metadata_json={
                    "youtube_channel_title": "Cinematic Pulse",
                    "workflow_state": "audio_ready",
                    "cover_image_path": str(cover_path),
                    "cover_approved": True,
                },
            )
            db.add_all([track, playlist])
            db.flush()
            db.add(PlaylistItem(playlist_id=playlist.id, track_id=track.id, order_index=1, included_duration_seconds=60))
            db.commit()
            playlist_id = playlist.id

        response = client.post(
            f"/api/playlists/{playlist_id}/video/render",
            json={
                "actor": "test-suite",
                "video_spectrum_overlay_style": "radial",
            },
        )

        assert response.status_code == 200
        assert response.json()["video_spectrum_overlay_style"] == "bars"
        assert response.json()["video_render_source_mode"] == "still_image"
        assert response.json()["video_render_resolution"] == "2k"
        with SessionLocal() as db:
            job = db.scalars(
                select(Job).where(Job.playlist_id == playlist_id, Job.type == JobType.build_video)
            ).one()
            playlist = db.get(Playlist, playlist_id)
            assert playlist.metadata_json["video_spectrum_overlay_style"] == "bars"
            assert playlist.metadata_json["video_render_source_mode"] == "still_image"
            assert playlist.metadata_json["video_render_resolution"] == "2k"
            assert job.payload_json["allow_still_image_fallback"] is True
            assert job.payload_json["video_spectrum_overlay_style"] == "bars"
            assert job.payload_json["video_render_source_mode"] == "still_image"
            assert job.payload_json["video_render_resolution"] == "2k"
    finally:
        clear_isolated_client_env()


def test_religious_channel_video_render_forces_no_spectrum(tmp_path) -> None:
    try:
        client = create_isolated_client(tmp_path)
        settings = client.app.state.settings
        playlist_dir = settings.playlists_dir
        track_dir = settings.tracks_dir
        playlist_dir.mkdir(parents=True, exist_ok=True)
        track_dir.mkdir(parents=True, exist_ok=True)

        audio_path = playlist_dir / "genesis-audio.mp3"
        cover_path = playlist_dir / "genesis-cover.png"
        loop_path = playlist_dir / "genesis-loop.mp4"
        track_path = track_dir / "genesis-track.mp3"
        audio_path.write_bytes(b"fake-audio")
        loop_path.write_bytes(b"fake-loop")
        track_path.write_bytes(b"fake-track")
        Image.new("RGB", (1280, 720), "black").save(cover_path)

        with SessionLocal() as db:
            track = Track(
                title="Genesis Track",
                prompt="scripture worship",
                status=TrackStatus.approved,
                duration_seconds=60,
                audio_path=str(track_path),
                metadata_json={"style": "scripture jazz"},
            )
            playlist = Playlist(
                title="[playlist] Genesis Creation Light",
                status=PlaylistStatus.ready,
                target_duration_seconds=60,
                actual_duration_seconds=60,
                output_audio_path=str(audio_path),
                metadata_json={
                    "youtube_channel_title": "The Old Verse",
                    "scripture_channel_title": "The Old Verse",
                    "scripture_passage_range": "Genesis 1:1-5",
                    "workflow_state": "audio_ready",
                    "cover_image_path": str(cover_path),
                    "cover_approved": True,
                    "loop_video_path": str(loop_path),
                },
            )
            db.add_all([track, playlist])
            db.flush()
            db.add(PlaylistItem(playlist_id=playlist.id, track_id=track.id, order_index=1, included_duration_seconds=60))
            db.commit()
            playlist_id = playlist.id

        response = client.post(
            f"/api/playlists/{playlist_id}/video/render",
            json={
                "actor": "test-suite",
                "video_spectrum_overlay_style": "radial",
            },
        )

        assert response.status_code == 200
        assert response.json()["video_spectrum_overlay_style"] == "none"
        with SessionLocal() as db:
            job = db.scalars(
                select(Job).where(Job.playlist_id == playlist_id, Job.type == JobType.build_video)
            ).one()
            playlist = db.get(Playlist, playlist_id)
            assert playlist.metadata_json["video_spectrum_overlay_style"] == "none"
            assert job.payload_json["video_spectrum_overlay_style"] == "none"
    finally:
        clear_isolated_client_env()


def test_local_video_cleanup_deletes_public_youtube_videos_above_threshold_oldest_first(tmp_path) -> None:
    try:
        client = create_isolated_client(tmp_path)
        settings = client.app.state.settings
        settings.local_video_cleanup_enabled = True
        settings.local_video_cleanup_disk_threshold_percent = 50
        settings.playlists_dir.mkdir(parents=True, exist_ok=True)
        now = datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc)

        with SessionLocal() as db:
            public_playlist = Playlist(
                title="Public Local Video",
                status=PlaylistStatus.uploaded,
                target_duration_seconds=60,
                actual_duration_seconds=60,
                youtube_video_id="yt-public",
                metadata_json={
                    "workflow_state": "uploaded",
                    "youtube_uploaded_at": "2026-05-10T12:00:00+00:00",
                    "youtube_response": {"status": {"privacyStatus": "public"}},
                },
            )
            orphan_playlist = Playlist(
                title="Public Orphan Local Video",
                status=PlaylistStatus.uploaded,
                target_duration_seconds=60,
                actual_duration_seconds=60,
                youtube_video_id="yt-orphan",
                metadata_json={
                    "workflow_state": "uploaded",
                    "youtube_uploaded_at": "2026-05-11T12:00:00+00:00",
                    "youtube_scheduled_publish_at": "2026-05-14T12:00:00+00:00",
                },
            )
            future_playlist = Playlist(
                title="Future Scheduled Video",
                status=PlaylistStatus.uploaded,
                target_duration_seconds=60,
                actual_duration_seconds=60,
                youtube_video_id="yt-future",
                metadata_json={
                    "workflow_state": "uploaded",
                    "youtube_uploaded_at": "2026-05-12T12:00:00+00:00",
                    "youtube_scheduled_publish_at": "2026-05-16T12:00:00+00:00",
                },
            )
            private_playlist = Playlist(
                title="Private Video",
                status=PlaylistStatus.uploaded,
                target_duration_seconds=60,
                actual_duration_seconds=60,
                youtube_video_id="yt-private",
                metadata_json={
                    "workflow_state": "uploaded",
                    "youtube_uploaded_at": "2026-05-13T12:00:00+00:00",
                    "youtube_response": {"status": {"privacyStatus": "private"}},
                },
            )
            not_uploaded_playlist = Playlist(
                title="Not Uploaded Local Video",
                status=PlaylistStatus.ready,
                target_duration_seconds=60,
                actual_duration_seconds=60,
                metadata_json={"workflow_state": "metadata_review"},
            )
            db.add_all([public_playlist, orphan_playlist, future_playlist, private_playlist, not_uploaded_playlist])
            db.flush()
            public_path = settings.playlists_dir / f"{public_playlist.id}.mp4"
            orphan_path = settings.playlists_dir / f"{orphan_playlist.id}.mp4"
            future_path = settings.playlists_dir / f"{future_playlist.id}.mp4"
            private_path = settings.playlists_dir / f"{private_playlist.id}.mp4"
            not_uploaded_path = settings.playlists_dir / f"{not_uploaded_playlist.id}.mp4"
            for path in (public_path, orphan_path, future_path, private_path, not_uploaded_path):
                path.write_bytes(b"fake-video")
            public_playlist.output_video_path = str(public_path)
            future_playlist.output_video_path = str(future_path)
            private_playlist.output_video_path = str(private_path)
            not_uploaded_playlist.output_video_path = str(not_uploaded_path)
            db.commit()
            public_id = public_playlist.id
            orphan_id = orphan_playlist.id
            future_id = future_playlist.id
            private_id = private_playlist.id
            not_uploaded_id = not_uploaded_playlist.id

            result = cleanup_public_uploaded_local_videos(
                db,
                settings,
                now=now,
                usage_provider=lambda _path: SimpleNamespace(total=100, used=90, free=10),
            )

            assert result["deleted_count"] == 2
            assert [item["playlist_id"] for item in result["deleted"]] == [
                public_id,
                orphan_id,
            ]
            assert not public_path.exists()
            assert not orphan_path.exists()
            assert future_path.exists()
            assert private_path.exists()
            assert not_uploaded_path.exists()
            public_updated = db.get(Playlist, public_id)
            orphan_updated = db.get(Playlist, orphan_id)
            future_updated = db.get(Playlist, future_id)
            private_updated = db.get(Playlist, private_id)
            not_uploaded_updated = db.get(Playlist, not_uploaded_id)
            assert public_updated.output_video_path is None
            assert public_updated.metadata_json["local_video_deleted_after_youtube_upload"] == str(public_path)
            assert public_updated.metadata_json["local_video_cleanup_reason"] == "disk_usage_threshold_uploaded_youtube_video"
            assert orphan_updated.output_video_path is None
            assert orphan_updated.metadata_json["local_video_cleanup_source"] == "canonical_playlist_mp4"
            assert future_updated.output_video_path == str(future_path)
            assert private_updated.output_video_path == str(private_path)
            assert not_uploaded_updated.output_video_path == str(not_uploaded_path)
    finally:
        clear_isolated_client_env()


def test_local_video_cleanup_skips_when_disk_usage_is_at_or_below_threshold(tmp_path) -> None:
    try:
        client = create_isolated_client(tmp_path)
        settings = client.app.state.settings
        settings.local_video_cleanup_enabled = True
        settings.local_video_cleanup_disk_threshold_percent = 50
        settings.playlists_dir.mkdir(parents=True, exist_ok=True)

        with SessionLocal() as db:
            playlist = Playlist(
                title="Below Threshold Public Video",
                status=PlaylistStatus.uploaded,
                target_duration_seconds=60,
                actual_duration_seconds=60,
                youtube_video_id="yt-public",
                metadata_json={
                    "workflow_state": "uploaded",
                    "youtube_response": {"status": {"privacyStatus": "public"}},
                },
            )
            db.add(playlist)
            db.flush()
            video_path = settings.playlists_dir / f"{playlist.id}.mp4"
            video_path.write_bytes(b"fake-video")
            playlist.output_video_path = str(video_path)
            db.commit()

            result = cleanup_public_uploaded_local_videos(
                db,
                settings,
                usage_provider=lambda _path: SimpleNamespace(total=100, used=50, free=50),
            )

            assert result["skipped"] is True
            assert result["reason"] == "below_threshold"
            assert result["deleted_count"] == 0
            assert video_path.exists()
            assert db.get(Playlist, playlist.id).output_video_path == str(video_path)
    finally:
        clear_isolated_client_env()


def test_loop_video_upload_triggers_public_video_cleanup(tmp_path, monkeypatch) -> None:
    try:
        client = create_isolated_client(tmp_path)
        calls = []

        def fake_cleanup(db, settings):
            calls.append({"storage_root": str(settings.storage_root)})
            return {"ok": True, "deleted_count": 0}

        monkeypatch.setattr(playlist_routes, "cleanup_public_uploaded_local_videos", fake_cleanup)
        workspace_response = client.post(
            "/api/playlists/workspaces",
            json={"title": "Loop Cleanup Trigger", "target_duration_seconds": 60},
        )
        workspace_id = workspace_response.json()["id"]

        upload_test_loop_video(client, workspace_id)

        assert calls == [{"storage_root": str(client.app.state.settings.storage_root)}]
    finally:
        clear_isolated_client_env()


def test_render_worker_cache_cleanup_deletes_stale_unmarked_jobs(tmp_path, monkeypatch) -> None:
    cache_dir = tmp_path / "cache"
    jobs_dir = cache_dir / "jobs"
    completed_dir = jobs_dir / "completed-job"
    orphan_dir = jobs_dir / "old-unmarked-job"
    fresh_dir = jobs_dir / "fresh-unmarked-job"
    for directory in (completed_dir, orphan_dir, fresh_dir):
        directory.mkdir(parents=True)
        (directory / "render.mp4").write_bytes(b"fake-video")

    (completed_dir / render_worker_script.COMPLETED_JOB_MARKER).write_text(
        json.dumps(
            {
                "job_id": "completed-job",
                "playlist_id": "playlist-completed",
                "uploaded_to_webapp_at": "2026-05-10T12:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )
    old_timestamp = time.time() - (48 * 60 * 60)
    for path in (orphan_dir, orphan_dir / "render.mp4"):
        os.utime(path, (old_timestamp, old_timestamp))

    monkeypatch.setattr(
        render_worker_script.shutil,
        "disk_usage",
        lambda _path: SimpleNamespace(total=100, used=90, free=10),
    )

    result = render_worker_script.cleanup_uploaded_job_cache(
        cache_dir,
        80,
        orphan_age_hours=24,
    )

    assert result["deleted_count"] == 2
    assert {item["job_id"] for item in result["deleted"]} == {"completed-job", "old-unmarked-job"}
    assert not completed_dir.exists()
    assert not orphan_dir.exists()
    assert fresh_dir.exists()


def test_workspace_lists_sort_unpublished_before_scheduled_publish_then_published(tmp_path) -> None:
    try:
        client = create_isolated_client(tmp_path)
        with SessionLocal() as db:
            created_release = Playlist(
                title="Created Fallback Release",
                status=PlaylistStatus.draft,
                target_duration_seconds=60,
                actual_duration_seconds=0,
                created_at=datetime(2026, 5, 13, 12, 0, tzinfo=timezone.utc),
                updated_at=datetime(2026, 5, 20, 12, 0, tzinfo=timezone.utc),
                metadata_json={"workflow_state": "collecting"},
            )
            published_release = Playlist(
                title="Published Release",
                status=PlaylistStatus.uploaded,
                target_duration_seconds=60,
                actual_duration_seconds=60,
                youtube_video_id="yt-published",
                created_at=datetime(2026, 5, 10, 12, 0, tzinfo=timezone.utc),
                updated_at=datetime(2026, 5, 10, 13, 0, tzinfo=timezone.utc),
                metadata_json={
                    "workflow_state": "uploaded",
                    "youtube_published_at": "2026-05-14T12:00:00+00:00",
                    "youtube_channel_id": "UC_A",
                    "youtube_channel_title": "Channel A",
                },
            )
            scheduled_release = Playlist(
                title="Scheduled Release",
                status=PlaylistStatus.uploaded,
                target_duration_seconds=60,
                actual_duration_seconds=60,
                youtube_video_id="yt-scheduled",
                created_at=datetime(2026, 5, 9, 12, 0, tzinfo=timezone.utc),
                updated_at=datetime(2026, 5, 9, 13, 0, tzinfo=timezone.utc),
                metadata_json={
                    "workflow_state": "uploaded",
                    "youtube_scheduled_publish_at": "2099-05-15T12:00:00+00:00",
                    "youtube_channel_id": "UC_A",
                    "youtube_channel_title": "Channel A",
                },
            )
            future_scheduled_release = Playlist(
                title="Future Scheduled Release",
                status=PlaylistStatus.uploaded,
                target_duration_seconds=60,
                actual_duration_seconds=60,
                youtube_video_id="yt-future-scheduled",
                created_at=datetime(2026, 5, 8, 12, 0, tzinfo=timezone.utc),
                updated_at=datetime(2026, 5, 8, 13, 0, tzinfo=timezone.utc),
                metadata_json={
                    "workflow_state": "uploaded",
                    "youtube_scheduled_publish_at": "2099-05-16T12:00:00+00:00",
                    "youtube_channel_id": "UC_A",
                    "youtube_channel_title": "Channel A",
                },
            )
            db.add_all([created_release, published_release, scheduled_release, future_scheduled_release])
            db.commit()
            expected_order = [
                created_release.id,
                future_scheduled_release.id,
                scheduled_release.id,
                published_release.id,
            ]

        full_response = client.get("/api/playlists/workspaces")
        compact_response = client.get("/api/playlists/workspaces?compact=true")

        assert full_response.status_code == 200
        assert compact_response.status_code == 200
        assert [item["id"] for item in full_response.json()] == expected_order
        assert [item["id"] for item in compact_response.json()] == expected_order
    finally:
        clear_isolated_client_env()


def test_workspace_lists_treat_due_scheduled_upload_as_public(tmp_path) -> None:
    try:
        client = create_isolated_client(tmp_path)
        with SessionLocal() as db:
            due_release = Playlist(
                title="Due Scheduled Release",
                status=PlaylistStatus.uploaded,
                target_duration_seconds=60,
                actual_duration_seconds=60,
                youtube_video_id="yt-due-scheduled",
                metadata_json={
                    "workflow_state": "uploaded",
                    "youtube_published_at": "2026-05-10T12:00:00+00:00",
                    "youtube_scheduled_publish_at": "2026-05-12T22:00:00+00:00",
                    "youtube_channel_id": "UC_A",
                    "youtube_channel_title": "Channel A",
                    "youtube_response": {
                        "status": {
                            "privacyStatus": "private",
                            "publishAt": "2026-05-12T22:00:00Z",
                        }
                    },
                },
            )
            future_release = Playlist(
                title="Future Scheduled Release",
                status=PlaylistStatus.uploaded,
                target_duration_seconds=60,
                actual_duration_seconds=60,
                youtube_video_id="yt-future-scheduled",
                metadata_json={
                    "workflow_state": "uploaded",
                    "youtube_scheduled_publish_at": "2099-05-12T22:00:00+00:00",
                    "youtube_channel_id": "UC_A",
                    "youtube_channel_title": "Channel A",
                },
            )
            db.add_all([due_release, future_release])
            db.commit()
            due_id = due_release.id
            future_id = future_release.id

        response = client.get("/api/playlists/workspaces")

        assert response.status_code == 200
        by_id = {item["id"]: item for item in response.json()}
        assert by_id[due_id]["youtube_scheduled_publish_at"] is None
        assert by_id[due_id]["youtube_published_at"] == "2026-05-12T22:00:00Z"
        assert by_id[future_id]["youtube_scheduled_publish_at"] == "2099-05-12T22:00:00Z"
    finally:
        clear_isolated_client_env()


def test_reconcile_due_scheduled_youtube_public_states_marks_past_schedule_public(tmp_path) -> None:
    try:
        create_isolated_client(tmp_path)
        with SessionLocal() as db:
            playlist = Playlist(
                title="Due Scheduled Release",
                status=PlaylistStatus.uploaded,
                youtube_video_id="yt-due-scheduled",
                metadata_json={
                    "workflow_state": "uploaded",
                    "youtube_scheduled_publish_at": "2026-05-12T22:00:00+00:00",
                    "youtube_response": {
                        "status": {
                            "privacyStatus": "private",
                            "publishAt": "2026-05-12T22:00:00Z",
                        }
                    },
                },
            )
            db.add(playlist)
            db.commit()
            playlist_id = playlist.id

            updated = reconcile_due_scheduled_youtube_public_states(
                db,
                now=datetime(2026, 5, 13, 0, 0, tzinfo=timezone.utc),
            )

            reloaded = db.get(Playlist, playlist_id)

        assert updated == 1
        meta = reloaded.metadata_json
        assert meta["youtube_public_at"] == "2026-05-12T22:00:00+00:00"
        assert meta["youtube_published_at"] == "2026-05-12T22:00:00+00:00"
        assert meta["youtube_response"]["status"]["privacyStatus"] == "public"
        assert "publishAt" not in meta["youtube_response"]["status"]
        assert "youtube_scheduled_publish_at" not in meta
    finally:
        clear_isolated_client_env()


def test_manual_upload_creates_track_and_stores_file(tmp_path) -> None:
    try:
        client = create_isolated_client(tmp_path)
        marker = uuid4().hex

        response = client.post(
            "/api/tracks/manual-upload",
            data={
                "title": f"Manual Upload {marker}",
                "prompt": "manual suno intake candidate",
                "lyrics": "달빛 아래 조용한 후렴",
                "style": "bright Korean pop ballad, clean vocal, 92 BPM",
                "exclude_style": "muddy vocals, heavy reverb, concert hall echo",
                "duration_seconds": "123",
                "model_score": "0.87",
            },
            files={"audio_file": ("manual-upload.mp3", b"fake-audio-data", "audio/mpeg")},
        )

        assert response.status_code == 201
        track = response.json()
        assert track["title"] == f"Manual Upload {marker}"
        assert os.path.exists(track["audio_path"])
        assert track["audio_path"].endswith("manual-upload.mp3")
        assert track["metadata_json"]["source"] == "manual-upload"
        assert track["metadata_json"]["model_score"] == 0.87
        assert track["metadata_json"]["lyrics"] == "달빛 아래 조용한 후렴"
        assert track["metadata_json"]["style"] == "bright Korean pop ballad, clean vocal, 92 BPM"
        assert track["metadata_json"]["exclude_style"] == "muddy vocals, heavy reverb, concert hall echo"
        assert track["lyrics"] == "달빛 아래 조용한 후렴"
        assert track["style"] == "bright Korean pop ballad, clean vocal, 92 BPM"
        assert track["exclude_style"] == "muddy vocals, heavy reverb, concert hall echo"
    finally:
        clear_isolated_client_env()


def test_track_rating_updates_metadata_and_can_be_filtered(tmp_path) -> None:
    try:
        client = create_isolated_client(tmp_path)

        response = client.post(
            "/api/tracks/manual-upload",
            data={
                "title": "Rating Candidate",
                "prompt": "rating test track",
            },
            files={"audio_file": ("rating.mp3", b"fake-audio-data", "audio/mpeg")},
        )
        assert response.status_code == 201
        track_id = response.json()["id"]

        liked = client.post(f"/api/tracks/{track_id}/rating", json={"rating": "like", "actor": "web-ui"})
        assert liked.status_code == 200
        assert liked.json()["user_rating"] == "like"
        assert liked.json()["metadata_json"]["user_rating"] == "like"
        assert liked.json()["metadata_json"]["user_rating_actor"] == "web-ui"

        liked_list = client.get("/api/tracks?user_rating=like")
        assert liked_list.status_code == 200
        assert any(track["id"] == track_id for track in liked_list.json())

        disliked_list = client.get("/api/tracks?user_rating=dislike")
        assert disliked_list.status_code == 200
        assert all(track["id"] != track_id for track in disliked_list.json())

        cleared = client.post(f"/api/tracks/{track_id}/rating", json={"rating": "none", "actor": "web-ui"})
        assert cleared.status_code == 200
        assert cleared.json()["user_rating"] == ""
        assert "user_rating" not in cleared.json()["metadata_json"]
    finally:
        clear_isolated_client_env()


def test_manual_upload_uses_actual_audio_duration_over_supplied_value(tmp_path) -> None:
    try:
        client = create_isolated_client(tmp_path)
        marker = uuid4().hex

        response = client.post(
            "/api/tracks/manual-upload",
            data={
                "title": f"Duration Probe {marker}",
                "prompt": "duration probe",
                "duration_seconds": "999",
            },
            files={"audio_file": ("duration-probe.wav", wav_bytes(2.0), "audio/wav")},
        )

        assert response.status_code == 201
        assert response.json()["duration_seconds"] == 2
    finally:
        clear_isolated_client_env()


def test_manual_upload_rejects_empty_audio_file_even_with_supplied_duration(tmp_path) -> None:
    try:
        client = create_isolated_client(tmp_path)

        response = client.post(
            "/api/tracks/manual-upload",
            data={
                "title": "Empty Upload",
                "prompt": "empty upload",
                "duration_seconds": "210",
            },
            files={"audio_file": ("empty.mp3", b"", "audio/mpeg")},
        )

        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()
    finally:
        clear_isolated_client_env()


def test_manual_upload_audio_url_is_cached_locally(tmp_path, monkeypatch) -> None:
    try:
        client = create_isolated_client(tmp_path, cache_remote_audio=True)
        cached_audio = tmp_path / "storage" / "tracks" / "remote-song.mp3"

        def fake_cache_remote_audio_url(audio_url, tracks_dir, *, title):
            assert audio_url == "https://cdn.example.com/remote-song.mp3"
            cached_audio.parent.mkdir(parents=True, exist_ok=True)
            cached_audio.write_bytes(b"fake-remote-audio")
            return str(cached_audio)

        monkeypatch.setattr("app.routes.tracks._cache_remote_audio_url", fake_cache_remote_audio_url)

        response = client.post(
            "/api/tracks/manual-upload",
            data={
                "title": "Remote Song",
                "prompt": "remote suno intake candidate",
                "duration_seconds": "123",
                "audio_url": "https://cdn.example.com/remote-song.mp3",
            },
        )

        assert response.status_code == 201
        track = response.json()
        assert track["audio_path"] == str(cached_audio)
        assert track["metadata_json"]["source_audio_url"] == "https://cdn.example.com/remote-song.mp3"
        assert track["metadata_json"]["audio_source"] == "remote-url-cache"
    finally:
        clear_isolated_client_env()


def test_create_track_audio_url_is_cached_locally(tmp_path, monkeypatch) -> None:
    try:
        client = create_isolated_client(tmp_path, cache_remote_audio=True)
        cached_audio = tmp_path / "storage" / "tracks" / "api-remote.mp3"

        def fake_cache_remote_audio_url(audio_url, tracks_dir, *, title):
            assert audio_url == "https://cdn.example.com/api-remote.mp3"
            cached_audio.parent.mkdir(parents=True, exist_ok=True)
            cached_audio.write_bytes(b"fake-remote-audio")
            return str(cached_audio)

        monkeypatch.setattr("app.routes.tracks._cache_remote_audio_url", fake_cache_remote_audio_url)

        response = client.post(
            "/api/tracks",
            json={
                "title": "API Remote",
                "prompt": "api remote intake",
                "lyrics": "remote api lyrics",
                "style": "remote api style",
                "duration_seconds": 123,
                "audio_path": "https://cdn.example.com/api-remote.mp3",
                "metadata": {"source": "api-test"},
            },
        )

        assert response.status_code == 201
        track = response.json()
        assert track["audio_path"] == str(cached_audio)
        assert track["metadata_json"]["source_audio_url"] == "https://cdn.example.com/api-remote.mp3"
        assert track["metadata_json"]["audio_source"] == "remote-url-cache"
        assert track["metadata_json"]["source"] == "api-test"
        assert track["metadata_json"]["lyrics"] == "remote api lyrics"
        assert track["metadata_json"]["style"] == "remote api style"
        assert track["style"] == "remote api style"
    finally:
        clear_isolated_client_env()


def test_manual_upload_requires_audio_source(tmp_path) -> None:
    try:
        client = create_isolated_client(tmp_path)

        response = client.post(
            "/api/tracks/manual-upload",
            data={
                "title": "Missing Audio",
                "prompt": "manual suno intake candidate",
                "duration_seconds": "123",
            },
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Either audio_file or audio_url is required."
    finally:
        clear_isolated_client_env()


def test_manual_upload_rejects_empty_audio_file(tmp_path) -> None:
    try:
        client = create_isolated_client(tmp_path)

        response = client.post(
            "/api/tracks/manual-upload",
            data={
                "title": "Empty Audio",
                "prompt": "manual upload",
                "duration_seconds": "123",
            },
            files={"audio_file": ("empty.mp3", b"", "audio/mpeg")},
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Uploaded audio file is empty."
    finally:
        clear_isolated_client_env()


def test_manual_upload_deduplicates_original_filename(tmp_path) -> None:
    try:
        client = create_isolated_client(tmp_path)

        first = client.post(
            "/api/tracks/manual-upload",
            data={
                "title": "First Upload",
                "prompt": "manual upload",
                "duration_seconds": "123",
            },
            files={"audio_file": ("same-name.mp3", b"first-audio", "audio/mpeg")},
        )
        second = client.post(
            "/api/tracks/manual-upload",
            data={
                "title": "Second Upload",
                "prompt": "manual upload",
                "duration_seconds": "123",
            },
            files={"audio_file": ("same-name.mp3", b"second-audio", "audio/mpeg")},
        )

        assert first.status_code == 201
        assert second.status_code == 201
        assert first.json()["audio_path"].endswith("same-name.mp3")
        assert second.json()["audio_path"].endswith("same-name-2.mp3")
    finally:
        clear_isolated_client_env()


def test_extract_embedded_cover_uses_stable_jpeg_output(tmp_path, monkeypatch) -> None:
    source = tmp_path / "cover-source.mp3"
    source.write_bytes(b"fake-audio")
    covers_dir = tmp_path / "covers"
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        Path(args[-1]).write_bytes(b"fake-jpeg")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("app.routes.tracks.subprocess.run", fake_run)

    result = _extract_embedded_cover(str(source), covers_dir)

    assert result is not None
    assert result.endswith("cover-source-cover.jpg")
    assert Path(result).exists()
    assert "-an" in calls[0]
    assert calls[0][calls[0].index("-c:v") + 1] == "mjpeg"


def test_auto_build_creates_playlist_when_enough_tracks_are_approved(tmp_path) -> None:
    try:
        client = create_isolated_client(tmp_path)
        client.app.state.settings.auto_build_playlists = True
        client.app.state.settings.auto_build_render_audio = False
        client.app.state.settings.playlist_target_minutes = 5
        marker = uuid4().hex

        track_ids = []
        for suffix in ("A", "B"):
            response = client.post(
                "/api/tracks",
                json={
                    "title": f"Auto Build {marker} {suffix}",
                    "prompt": "steady synth groove",
                    "duration_seconds": 180,
                    "audio_path": str(tmp_path / f"{marker}-{suffix}.mp3"),
                    "metadata": {"source": "test"},
                },
            )
            assert response.status_code == 201
            track_ids.append(response.json()["id"])

        approve_first = client.post(
            f"/api/tracks/{track_ids[0]}/decisions",
            json={
                "decision": "approve",
                "source": "human",
                "actor": "test-suite",
            },
        )
        assert approve_first.status_code == 200

        approve_second = client.post(
            f"/api/tracks/{track_ids[1]}/decisions",
            json={
                "decision": "approve",
                "source": "human",
                "actor": "test-suite",
            },
        )
        assert approve_second.status_code == 200

        playlists_response = client.get("/api/playlists")
        assert playlists_response.status_code == 200
        matching = [
            playlist
            for playlist in playlists_response.json()
            if playlist["metadata_json"].get("auto_built")
            and set(playlist["metadata_json"].get("selected_track_ids", [])) == set(track_ids)
        ]
        assert matching, playlists_response.json()
        assert matching[0]["status"] == "draft"
    finally:
        clear_isolated_client_env()


def test_manual_build_with_render_queues_background_job(tmp_path) -> None:
    try:
        client = create_isolated_client(tmp_path)
        client.app.state.settings.auto_build_playlists = False
        marker = uuid4().hex

        local_audio = tmp_path / f"{marker}.mp3"
        local_audio.write_bytes(b"fake source")
        track_response = client.post(
            "/api/tracks",
            json={
                "title": f"Render Build {marker}",
                "prompt": "playlist render test",
                "duration_seconds": 120,
                "audio_path": str(local_audio),
                "metadata": {"source": "test"},
            },
        )
        track_id = track_response.json()["id"]

        approve_response = client.post(
            f"/api/tracks/{track_id}/decisions",
            json={
                "decision": "approve",
                "source": "human",
                "actor": "test-suite",
            },
        )
        assert approve_response.status_code == 200

        services = client.app.state.services

        def fake_build_audio(tracks, output_path):
            output_path.write_bytes(b"fake-mp3")
            return output_path

        services.playlist_builder.build_audio = fake_build_audio

        playlist_response = client.post(
            "/api/playlists/build",
            json={
                "title": f"Manual Playlist {marker}",
                "target_duration_seconds": 60,
                "execute_render": True,
            },
        )
        assert playlist_response.status_code == 201
        playlist = playlist_response.json()
        assert playlist["status"] == "building"
        assert playlist["output_audio_path"] is None

        assert drain_background_jobs(client) == 1

        playlists_response = client.get("/api/playlists")
        refreshed = next(item for item in playlists_response.json() if item["id"] == playlist["id"])
        assert refreshed["status"] == "ready"
        assert refreshed["output_audio_path"].endswith(".mp3")
    finally:
        clear_isolated_client_env()


def test_mark_playlist_uploaded_updates_playlist_and_tracks(tmp_path) -> None:
    try:
        client = create_isolated_client(tmp_path)
        client.app.state.settings.auto_build_playlists = False
        client.app.state.services.youtube.get_channel = lambda channel_id: {
            "id": channel_id,
            "title": "Soft Hour Radio",
        }
        marker = uuid4().hex

        track_response = client.post(
            "/api/tracks",
            json={
                "title": f"Upload Ready {marker}",
                "prompt": "playlist upload state test",
                "duration_seconds": 120,
                "audio_path": str(tmp_path / f"{marker}.mp3"),
                "metadata": {"source": "test"},
            },
        )
        assert track_response.status_code == 201
        track_id = track_response.json()["id"]

        approve_response = client.post(
            f"/api/tracks/{track_id}/decisions",
            json={
                "decision": "approve",
                "source": "human",
                "actor": "test-suite",
            },
        )
        assert approve_response.status_code == 200

        playlist_response = client.post(
            "/api/playlists/build",
            json={
                "title": f"Manual Playlist {marker}",
                "target_duration_seconds": 999999,
                "execute_render": False,
            },
        )
        assert playlist_response.status_code == 201
        playlist = playlist_response.json()
        local_video = tmp_path / f"{marker}.mp4"
        local_video.write_bytes(b"uploaded video")

        uploaded_response = client.post(
            f"/api/playlists/{playlist['id']}/mark-uploaded",
            json={
                "youtube_video_id": f"yt-{marker}",
                "youtube_channel_id": "UC-soft-hour",
                "output_video_path": str(local_video),
                "actor": "test-suite",
                "note": "uploaded manually",
            },
        )
        assert uploaded_response.status_code == 200
        uploaded = uploaded_response.json()
        assert uploaded["status"] == "uploaded"
        assert uploaded["youtube_video_id"] == f"yt-{marker}"
        assert uploaded["output_video_path"] is None
        assert uploaded["metadata_json"]["youtube_channel_id"] == "UC-soft-hour"
        assert uploaded["metadata_json"]["youtube_channel_title"] == "Soft Hour Radio"
        assert not local_video.exists()

        track_after = client.get(f"/api/tracks/{track_id}")
        assert track_after.status_code == 200
        assert track_after.json()["status"] == "uploaded"
    finally:
        clear_isolated_client_env()


def test_workspace_flow_assigns_tracks_and_requests_publish_approval(tmp_path) -> None:
    try:
        client = create_isolated_client(tmp_path)
        workspace_response = client.post(
            "/api/playlists/workspaces",
            json={
                "title": "Workspace A",
                "target_duration_seconds": 240,
                "description": "Channel A synthwave lane",
                "cover_prompt": "Neon road and orange skyline",
            },
        )
        assert workspace_response.status_code == 201
        workspace_id = workspace_response.json()["id"]

        track_ids = []
        for index in range(2):
            track_response = client.post(
                "/api/tracks",
                json={
                    "title": f"Queue Track {index}",
                    "prompt": "city pop with soft pads",
                    "duration_seconds": 120,
                    "audio_path": f"https://cdn.example.com/{index}.mp3",
                    "metadata": {"source": "test"},
                },
            )
            assert track_response.status_code == 201
            track_ids.append(track_response.json()["id"])

        for track_id in track_ids:
            approve_response = client.post(
                f"/api/tracks/{track_id}/decisions",
                json={
                    "decision": "approve",
                    "source": "human",
                    "actor": "test-suite",
                    "playlist_id": workspace_id,
                },
            )
            assert approve_response.status_code == 200

        workspaces_response = client.get("/api/playlists/workspaces")
        assert workspaces_response.status_code == 200
        workspace = next(item for item in workspaces_response.json() if item["id"] == workspace_id)
        assert workspace["actual_duration_seconds"] == 240
        assert workspace["publish_ready"] is True
        assert workspace["workflow_state"] == "pending_audio_render"
        assert [track["id"] for track in workspace["tracks"]] == track_ids
    finally:
        clear_isolated_client_env()


def test_second_single_candidate_approval_creates_separate_release(tmp_path) -> None:
    try:
        client = create_isolated_client(tmp_path)
        services = client.app.state.services
        rendered_titles = []

        def fake_build_audio(tracks, output_path):
            rendered_titles.extend(track.title for track in tracks)
            output_path.write_bytes(b"combined-single-audio")
            return output_path

        services.playlist_builder.build_audio = fake_build_audio

        workspace_response = client.post(
            "/api/playlists/workspaces",
            json={
                "title": "Single Lane",
                "workspace_mode": "single_track_video",
                "auto_publish_when_ready": False,
            },
        )
        assert workspace_response.status_code == 201
        workspace_id = workspace_response.json()["id"]

        track_ids = []
        for index in range(2):
            audio_path = tmp_path / f"single-{index}.mp3"
            audio_path.write_bytes(f"single candidate {index}".encode())
            track_response = client.post(
                "/api/tracks",
                json={
                    "title": f"Single Candidate {index}",
                    "prompt": "solo release candidate",
                    "duration_seconds": 180,
                    "audio_path": str(audio_path),
                    "metadata": {"source": "test"},
                },
            )
            assert track_response.status_code == 201
            track_ids.append(track_response.json()["id"])

        first_approve = client.post(
            f"/api/tracks/{track_ids[0]}/decisions",
            json={
                "decision": "approve",
                "source": "human",
                "actor": "test-suite",
                "playlist_id": workspace_id,
            },
        )
        assert first_approve.status_code == 200
        assert drain_background_jobs(client) == 0

        second_approve = client.post(
            f"/api/tracks/{track_ids[1]}/decisions",
            json={
                "decision": "approve",
                "source": "human",
                "actor": "test-suite",
                "playlist_id": workspace_id,
            },
        )
        assert second_approve.status_code == 200
        assert drain_background_jobs(client) == 0

        workspaces_response = client.get("/api/playlists/workspaces")
        assert workspaces_response.status_code == 200
        workspaces = workspaces_response.json()
        original = next(item for item in workspaces if item["id"] == workspace_id)
        split = next(
            item
            for item in workspaces
            if item["id"] != workspace_id
            and item["workspace_mode"] == "single_track_video"
            and [track["id"] for track in item["tracks"]] == [track_ids[1]]
        )
        assert [track["id"] for track in original["tracks"]] == [track_ids[0]]
        assert original["actual_duration_seconds"] == 180
        assert original["workflow_state"] == "audio_ready"
        assert original["output_audio_path"].endswith("single-0.mp3")
        assert split["title"] == "Single Candidate 1"
        assert split["actual_duration_seconds"] == 180
        assert split["workflow_state"] == "audio_ready"
        assert split["output_audio_path"].endswith("single-1.mp3")
        assert "own Single Release" in split["note"]
        assert rendered_titles == []
    finally:
        clear_isolated_client_env()


def test_single_release_archives_when_all_candidates_are_rejected_and_can_restore(tmp_path) -> None:
    try:
        client = create_isolated_client(tmp_path)
        workspace_response = client.post(
            "/api/playlists/workspaces",
            json={
                "title": "Two Candidate Single",
                "workspace_mode": "single_track_video",
                "auto_publish_when_ready": False,
            },
        )
        assert workspace_response.status_code == 201
        workspace_id = workspace_response.json()["id"]

        track_ids = []
        for index in range(2):
            upload_response = client.post(
                "/api/tracks/manual-upload",
                data={
                    "title": f"Candidate {index + 1}",
                    "prompt": "suno two-candidate single",
                    "duration_seconds": "60",
                    "pending_workspace_id": workspace_id,
                },
                files={"audio_file": (f"candidate-{index + 1}.mp3", b"fake-audio", "audio/mpeg")},
            )
            assert upload_response.status_code == 201
            track_ids.append(upload_response.json()["id"])

        third_upload = client.post(
            "/api/tracks/manual-upload",
            data={
                "title": "Candidate 3",
                "prompt": "too many candidates",
                "duration_seconds": "60",
                "pending_workspace_id": workspace_id,
            },
            files={"audio_file": ("candidate-3.mp3", b"fake-audio", "audio/mpeg")},
        )
        assert third_upload.status_code == 400
        assert "at most two" in third_upload.json()["detail"]

        first_reject = client.post(
            f"/api/tracks/{track_ids[0]}/decisions",
            json={
                "decision": "reject",
                "source": "human",
                "actor": "test-suite",
                "playlist_id": workspace_id,
            },
        )
        assert first_reject.status_code == 200
        workspaces_response = client.get("/api/playlists/workspaces")
        workspace = next(item for item in workspaces_response.json() if item["id"] == workspace_id)
        assert workspace["hidden"] is False

        second_reject = client.post(
            f"/api/tracks/{track_ids[1]}/decisions",
            json={
                "decision": "reject",
                "source": "human",
                "actor": "test-suite",
                "playlist_id": workspace_id,
            },
        )
        assert second_reject.status_code == 200
        workspaces_response = client.get("/api/playlists/workspaces")
        archived = next(item for item in workspaces_response.json() if item["id"] == workspace_id)
        assert archived["hidden"] is True
        assert archived["workflow_state"] == "archived"
        assert "archived" in archived["note"]

        restore_response = client.post(
            f"/api/playlists/{workspace_id}/archive",
            json={
                "actor": "test-suite",
                "archived": False,
                "revive_rejected": True,
            },
        )
        assert restore_response.status_code == 200
        restored = restore_response.json()
        assert restored["hidden"] is False
        assert restored["workflow_state"] == "collecting"

        for track_id in track_ids:
            track_response = client.get(f"/api/tracks/{track_id}")
            assert track_response.status_code == 200
            assert track_response.json()["status"] == "pending_review"
    finally:
        clear_isolated_client_env()


def test_workspace_tracks_can_be_reordered(tmp_path) -> None:
    try:
        client = create_isolated_client(tmp_path)
        workspace_response = client.post(
            "/api/playlists/workspaces",
            json={
                "title": "Workspace Reorder",
                "target_duration_seconds": 999,
            },
        )
        assert workspace_response.status_code == 201
        workspace_id = workspace_response.json()["id"]

        track_ids = []
        for index in range(3):
            track_response = client.post(
                "/api/tracks",
                json={
                    "title": f"Ordered Track {index}",
                    "prompt": "sequence test",
                    "duration_seconds": 60,
                    "audio_path": f"https://cdn.example.com/ordered-{index}.mp3",
                    "metadata": {"source": "test"},
                },
            )
            assert track_response.status_code == 201
            track_id = track_response.json()["id"]
            track_ids.append(track_id)
            approve_response = client.post(
                f"/api/tracks/{track_id}/decisions",
                json={
                    "decision": "approve",
                    "source": "human",
                    "actor": "test-suite",
                    "playlist_id": workspace_id,
                },
            )
            assert approve_response.status_code == 200

        stale_output = tmp_path / "old-render.mp3"
        stale_output.write_bytes(b"old")
        cover_path = tmp_path / "existing-cover.png"
        cover_path.write_bytes(b"cover")
        db = SessionLocal()
        try:
            playlist = db.get(Playlist, workspace_id)
            playlist.output_audio_path = str(stale_output)
            playlist.metadata_json = {
                **(playlist.metadata_json or {}),
                "render_ready": True,
                "workflow_state": "pending_publish_approval",
                "cover_image_path": str(cover_path),
                "cover_source": "manual-upload",
                "cover_approved": True,
            }
            db.add(playlist)
            db.commit()
        finally:
            db.close()

        new_order = list(reversed(track_ids))
        reorder_response = client.post(
            f"/api/playlists/{workspace_id}/tracks/reorder",
            json={
                "track_ids": new_order,
                "actor": "test-suite",
            },
        )

        assert reorder_response.status_code == 200
        workspace = reorder_response.json()
        assert [track["id"] for track in workspace["tracks"]] == new_order
        assert workspace["output_audio_path"] is None
        assert workspace["workflow_state"] == "render_required"
        assert workspace["cover_image_path"] == str(cover_path)
        assert workspace["cover_approved"] is True
        assert workspace["note"] == "Track order changed. Re-render audio to update the playlist file."
    finally:
        clear_isolated_client_env()


def test_workspace_audio_render_can_be_queued_before_target_duration(tmp_path) -> None:
    try:
        client = create_isolated_client(tmp_path)
        services = client.app.state.services

        def fake_build_audio(tracks, output_path):
            output_path.write_bytes("|".join(track.title for track in tracks).encode("utf-8"))
            return output_path

        services.playlist_builder.build_audio = fake_build_audio
        workspace_response = client.post(
            "/api/playlists/workspaces",
            json={
                "title": "Manual Render Workspace",
                "target_duration_seconds": 999,
            },
        )
        assert workspace_response.status_code == 201
        workspace_id = workspace_response.json()["id"]

        for index in range(2):
            local_audio = tmp_path / f"render-{index}.mp3"
            local_audio.write_bytes(b"fake-audio")
            track_response = client.post(
                "/api/tracks",
                json={
                    "title": f"Renderable Track {index}",
                    "prompt": "render test",
                    "duration_seconds": 60,
                    "audio_path": str(local_audio),
                    "metadata": {"source": "test"},
                },
            )
            assert track_response.status_code == 201
            approve_response = client.post(
                f"/api/tracks/{track_response.json()['id']}/decisions",
                json={
                    "decision": "approve",
                    "source": "human",
                    "actor": "test-suite",
                    "playlist_id": workspace_id,
                },
            )
            assert approve_response.status_code == 200

        cover_path = tmp_path / "existing-cover.png"
        cover_path.write_bytes(b"cover")
        db = SessionLocal()
        try:
            playlist = db.get(Playlist, workspace_id)
            playlist.metadata_json = {
                **(playlist.metadata_json or {}),
                "cover_image_path": str(cover_path),
                "cover_source": "manual-upload",
                "cover_approved": True,
            }
            db.add(playlist)
            db.commit()
        finally:
            db.close()

        render_response = client.post(
            f"/api/playlists/{workspace_id}/render-audio",
            json={
                "actor": "test-suite",
            },
        )
        assert render_response.status_code == 200
        queued = render_response.json()
        assert queued["status"] == "building"
        assert queued["workflow_state"] == "render_queued"
        assert queued["output_audio_path"] is None
        assert queued["cover_image_path"] == str(cover_path)
        assert queued["cover_approved"] is True
        assert queued["render_job"]["status"] == "queued"
        assert queued["render_job"]["source"] == "web:render-audio"

        assert drain_background_jobs(client) == 1

        workspaces_response = client.get("/api/playlists/workspaces")
        workspace = next(item for item in workspaces_response.json() if item["id"] == workspace_id)
        assert workspace["output_audio_path"].endswith(".mp3")
        assert workspace["workflow_state"] == "rendered"
        assert workspace["cover_image_path"] == str(cover_path)
        assert workspace["cover_approved"] is True
        assert workspace["render_job"]["status"] == "succeeded"
        assert workspace["render_job"]["output_audio_path"] == workspace["output_audio_path"]
        assert workspace["actual_duration_seconds"] == 120
        assert Path(workspace["output_audio_path"]).exists()
    finally:
        clear_isolated_client_env()


def test_workspace_audio_render_reuses_similar_youtube_back_half_tracks(tmp_path) -> None:
    try:
        client = create_isolated_client(tmp_path)
        with SessionLocal() as db:
            source_tracks = []
            for index in range(4):
                audio_path = tmp_path / f"source-tech-house-{index}.mp3"
                audio_path.write_bytes(b"fake-audio")
                track = Track(
                    title=f"Source Tech House {index + 1}",
                    prompt="tech house instrumental groove",
                    duration_seconds=600,
                    audio_path=str(audio_path),
                    status=TrackStatus.approved,
                    metadata_json={"style": "tech house, club instrumental", "tags": "tech house"},
                )
                db.add(track)
                source_tracks.append(track)
            db.flush()
            source_playlist = Playlist(
                title="Tech House Running Mix",
                status=PlaylistStatus.uploaded,
                target_duration_seconds=2400,
                actual_duration_seconds=2400,
                youtube_video_id="yt-tech-house-source",
                metadata_json={
                    "workspace_mode": "playlist",
                    "youtube_channel_title": "Club Bloom",
                    "rendered_timeline": [
                        {
                            "track_id": track.id,
                            "title": track.title,
                            "start_seconds": index * 600,
                            "duration_seconds": 600,
                        }
                        for index, track in enumerate(source_tracks)
                    ],
                },
            )
            db.add(source_playlist)
            db.flush()
            for index, track in enumerate(source_tracks, start=1):
                db.add(
                    PlaylistItem(
                        playlist=source_playlist,
                        track=track,
                        order_index=index,
                        included_duration_seconds=600,
                    )
                )
            db.commit()

        workspace_response = client.post(
            "/api/playlists/workspaces",
            json={
                "title": "Tech House Workout Mix",
                "target_duration_seconds": 2400,
                "description": "Tech house workout and running energy.",
                "target_youtube_channel_title": "Club Bloom",
            },
        )
        assert workspace_response.status_code == 201
        workspace_id = workspace_response.json()["id"]

        new_audio_path = tmp_path / "new-tech-house.mp3"
        new_audio_path.write_bytes(b"fake-audio")
        track_response = client.post(
            "/api/tracks",
            json={
                "title": "New Tech House Lead",
                "prompt": "tech house workout groove",
                "duration_seconds": 1200,
                "audio_path": str(new_audio_path),
                "metadata": {"style": "tech house", "tags": "tech house"},
            },
        )
        assert track_response.status_code == 201
        approve_response = client.post(
            f"/api/tracks/{track_response.json()['id']}/decisions",
            json={
                "decision": "approve",
                "source": "human",
                "actor": "test-suite",
                "playlist_id": workspace_id,
            },
        )
        assert approve_response.status_code == 200

        render_response = client.post(
            f"/api/playlists/{workspace_id}/render-audio",
            json={"actor": "test-suite"},
        )
        assert render_response.status_code == 200
        queued = render_response.json()
        assert queued["actual_duration_seconds"] == 2400
        assert [track["title"] for track in queued["tracks"]] == [
            "New Tech House Lead",
            "Source Tech House 3",
            "Source Tech House 4",
        ]
        assert "Added 2 reused back-half track(s)" in queued["note"]
    finally:
        clear_isolated_client_env()


def test_workspace_audio_render_extends_forty_minute_release_to_one_hour_with_reuse(tmp_path) -> None:
    try:
        client = create_isolated_client(tmp_path)
        with SessionLocal() as db:
            source_tracks = []
            for index in range(4):
                audio_path = tmp_path / f"source-ukg-{index}.mp3"
                audio_path.write_bytes(b"fake-audio")
                track = Track(
                    title=f"Source UK Garage {index + 1}",
                    prompt="uk garage night drive club groove",
                    duration_seconds=600,
                    audio_path=str(audio_path),
                    status=TrackStatus.approved,
                    metadata_json={"style": "uk garage, club instrumental", "tags": "uk garage"},
                )
                db.add(track)
                source_tracks.append(track)
            db.flush()
            source_playlist = Playlist(
                title="UK Garage Night Drive Mix",
                status=PlaylistStatus.uploaded,
                target_duration_seconds=2400,
                actual_duration_seconds=2400,
                youtube_video_id="yt-ukg-source",
                metadata_json={
                    "workspace_mode": "playlist",
                    "youtube_channel_title": "Club Bloom",
                    "rendered_timeline": [
                        {
                            "track_id": track.id,
                            "title": track.title,
                            "start_seconds": index * 600,
                            "duration_seconds": 600,
                        }
                        for index, track in enumerate(source_tracks)
                    ],
                },
            )
            db.add(source_playlist)
            db.flush()
            for index, track in enumerate(source_tracks, start=1):
                db.add(
                    PlaylistItem(
                        playlist=source_playlist,
                        track=track,
                        order_index=index,
                        included_duration_seconds=600,
                    )
                )
            db.commit()

        workspace_response = client.post(
            "/api/playlists/workspaces",
            json={
                "title": "UK Garage Night Drive Mix",
                "target_duration_seconds": 2400,
                "description": "UK garage night drive and city lights.",
                "target_youtube_channel_title": "Club Bloom",
            },
        )
        assert workspace_response.status_code == 201
        workspace_id = workspace_response.json()["id"]

        new_audio_path = tmp_path / "new-ukg.mp3"
        new_audio_path.write_bytes(b"fake-audio")
        track_response = client.post(
            "/api/tracks",
            json={
                "title": "New UK Garage Hour Lead",
                "prompt": "uk garage night drive groove",
                "duration_seconds": 2400,
                "audio_path": str(new_audio_path),
                "metadata": {"style": "uk garage", "tags": "uk garage"},
            },
        )
        assert track_response.status_code == 201
        approve_response = client.post(
            f"/api/tracks/{track_response.json()['id']}/decisions",
            json={
                "decision": "approve",
                "source": "human",
                "actor": "test-suite",
                "playlist_id": workspace_id,
            },
        )
        assert approve_response.status_code == 200

        render_response = client.post(
            f"/api/playlists/{workspace_id}/render-audio",
            json={"actor": "test-suite"},
        )
        assert render_response.status_code == 200
        queued = render_response.json()
        assert queued["target_duration_seconds"] == 2400
        assert queued["actual_duration_seconds"] == 3600
        assert [track["title"] for track in queued["tracks"]] == [
            "New UK Garage Hour Lead",
            "Source UK Garage 3",
            "Source UK Garage 4",
        ]
        assert "Added 2 reused back-half track(s)" in queued["note"]
    finally:
        clear_isolated_client_env()


def test_workspace_audio_render_skips_reuse_when_genre_does_not_match(tmp_path) -> None:
    try:
        client = create_isolated_client(tmp_path)
        with SessionLocal() as db:
            source_tracks = []
            for index in range(2):
                audio_path = tmp_path / f"source-trance-{index}.mp3"
                audio_path.write_bytes(b"fake-audio")
                track = Track(
                    title=f"Source Trance {index + 1}",
                    prompt="progressive trance night drive",
                    duration_seconds=600,
                    audio_path=str(audio_path),
                    status=TrackStatus.approved,
                    metadata_json={"style": "progressive trance", "tags": "trance"},
                )
                db.add(track)
                source_tracks.append(track)
            db.flush()
            source_playlist = Playlist(
                title="Progressive Trance Night Drive",
                status=PlaylistStatus.uploaded,
                target_duration_seconds=1200,
                actual_duration_seconds=1200,
                youtube_video_id="yt-trance-source",
                metadata_json={
                    "workspace_mode": "playlist",
                    "youtube_channel_title": "Club Bloom",
                    "rendered_timeline": [
                        {
                            "track_id": track.id,
                            "title": track.title,
                            "start_seconds": index * 600,
                            "duration_seconds": 600,
                        }
                        for index, track in enumerate(source_tracks)
                    ],
                },
            )
            db.add(source_playlist)
            db.flush()
            for index, track in enumerate(source_tracks, start=1):
                db.add(
                    PlaylistItem(
                        playlist=source_playlist,
                        track=track,
                        order_index=index,
                        included_duration_seconds=600,
                    )
                )
            db.commit()

        workspace_response = client.post(
            "/api/playlists/workspaces",
            json={
                "title": "Tech House Workout Mix",
                "target_duration_seconds": 2400,
                "description": "Tech house workout and running energy.",
                "target_youtube_channel_title": "Club Bloom",
            },
        )
        workspace_id = workspace_response.json()["id"]

        new_audio_path = tmp_path / "new-tech-house.mp3"
        new_audio_path.write_bytes(b"fake-audio")
        track_response = client.post(
            "/api/tracks",
            json={
                "title": "New Tech House Lead",
                "prompt": "tech house workout groove",
                "duration_seconds": 1200,
                "audio_path": str(new_audio_path),
                "metadata": {"style": "tech house", "tags": "tech house"},
            },
        )
        approve_response = client.post(
            f"/api/tracks/{track_response.json()['id']}/decisions",
            json={
                "decision": "approve",
                "source": "human",
                "actor": "test-suite",
                "playlist_id": workspace_id,
            },
        )
        assert approve_response.status_code == 200

        render_response = client.post(
            f"/api/playlists/{workspace_id}/render-audio",
            json={"actor": "test-suite"},
        )
        assert render_response.status_code == 200
        queued = render_response.json()
        assert queued["actual_duration_seconds"] == 1200
        assert [track["title"] for track in queued["tracks"]] == ["New Tech House Lead"]
        assert "reused back-half" not in queued["note"]
    finally:
        clear_isolated_client_env()


def test_workspace_audio_render_can_randomize_track_order(tmp_path) -> None:
    try:
        client = create_isolated_client(tmp_path)
        services = client.app.state.services

        def fake_build_audio(tracks, output_path):
            output_path.write_text("|".join(track.title for track in tracks), encoding="utf-8")
            return output_path

        services.playlist_builder.build_audio = fake_build_audio
        workspace_response = client.post(
            "/api/playlists/workspaces",
            json={
                "title": "Random Render Workspace",
                "target_duration_seconds": 999,
            },
        )
        assert workspace_response.status_code == 201
        workspace_id = workspace_response.json()["id"]

        original_track_ids = []
        for index in range(4):
            local_audio = tmp_path / f"random-render-{index}.mp3"
            local_audio.write_bytes(b"fake-audio")
            track_response = client.post(
                "/api/tracks",
                json={
                    "title": f"Random Track {index}",
                    "prompt": "random render test",
                    "duration_seconds": 60,
                    "audio_path": str(local_audio),
                    "metadata": {"source": "test"},
                },
            )
            assert track_response.status_code == 201
            track_id = track_response.json()["id"]
            original_track_ids.append(track_id)
            approve_response = client.post(
                f"/api/tracks/{track_id}/decisions",
                json={
                    "decision": "approve",
                    "source": "human",
                    "actor": "test-suite",
                    "playlist_id": workspace_id,
                },
            )
            assert approve_response.status_code == 200

        render_response = client.post(
            f"/api/playlists/{workspace_id}/render-audio",
            json={
                "actor": "test-suite",
                "random": True,
            },
        )
        assert render_response.status_code == 200
        queued = render_response.json()
        randomized_track_ids = [track["id"] for track in queued["tracks"]]
        assert set(randomized_track_ids) == set(original_track_ids)
        assert randomized_track_ids != original_track_ids
        assert queued["note"] == "Playlist audio render queued with randomized track order."

        assert drain_background_jobs(client) == 1

        workspaces_response = client.get("/api/playlists/workspaces")
        workspace = next(item for item in workspaces_response.json() if item["id"] == workspace_id)
        rendered_titles = Path(workspace["output_audio_path"]).read_text(encoding="utf-8").split("|")
        assert rendered_titles == [track["title"] for track in workspace["tracks"]]
        assert [item["track_id"] for item in workspace["rendered_timeline"]] == [track["id"] for track in workspace["tracks"]]
        assert [item["start_seconds"] for item in workspace["rendered_timeline"]] == [0, 60, 120, 180]
    finally:
        clear_isolated_client_env()


def test_track_added_during_audio_render_requeues_fresh_render(tmp_path) -> None:
    try:
        client = create_isolated_client(tmp_path)
        services = client.app.state.services
        injected = False

        workspace_response = client.post(
            "/api/playlists/workspaces",
            json={
                "title": "Race Render Workspace",
                "target_duration_seconds": 60,
            },
        )
        assert workspace_response.status_code == 201
        workspace_id = workspace_response.json()["id"]

        def upload_and_assign(title: str, duration_seconds: int) -> str:
            local_audio = tmp_path / f"{title}.mp3"
            local_audio.write_bytes(b"fake-audio")
            track_response = client.post(
                "/api/tracks",
                json={
                    "title": title,
                    "prompt": "render race test",
                    "duration_seconds": duration_seconds,
                    "audio_path": str(local_audio),
                    "metadata": {"source": "test"},
                },
            )
            assert track_response.status_code == 201
            track_id = track_response.json()["id"]
            approve_response = client.post(
                f"/api/tracks/{track_id}/decisions",
                json={
                    "decision": "approve",
                    "source": "human",
                    "actor": "test-suite",
                    "playlist_id": workspace_id,
                },
            )
            assert approve_response.status_code == 200
            return track_id

        first_track_id = upload_and_assign("Race Track 1", 60)

        def fake_build_audio(tracks, output_path):
            nonlocal injected
            output_path.write_bytes("|".join(track.title for track in tracks).encode("utf-8"))
            if not injected:
                injected = True
                upload_and_assign("Race Track 2", 60)
            return output_path

        services.playlist_builder.build_audio = fake_build_audio

        render_response = client.post(
            f"/api/playlists/{workspace_id}/render-audio",
            json={"actor": "test-suite"},
        )
        assert render_response.status_code == 200

        assert drain_background_jobs(client, max_jobs=3) == 2

        workspaces_response = client.get("/api/playlists/workspaces")
        workspace = next(item for item in workspaces_response.json() if item["id"] == workspace_id)
        assert workspace["output_audio_path"].endswith(".mp3")
        assert workspace["actual_duration_seconds"] == 120
        assert Path(workspace["output_audio_path"]).read_text(encoding="utf-8") == "Race Track 1|Race Track 2"
        assert [track["title"] for track in workspace["tracks"]] == ["Race Track 1", "Race Track 2"]
        assert workspace["render_job"]["source"] == "system:stale-render-retry"

        with SessionLocal() as db:
            playlist = db.get(Playlist, workspace_id)
            assert playlist is not None
            meta = playlist.metadata_json
            assert meta["rendered_track_ids"] != [first_track_id]
            assert meta["rendered_track_count"] == 2
            assert [item["title"] for item in meta["rendered_timeline"]] == ["Race Track 1", "Race Track 2"]
            assert [item["start_seconds"] for item in meta["rendered_timeline"]] == [0, 60]
            assert "stale_audio_render" not in meta
    finally:
        clear_isolated_client_env()


def test_slack_approve_assigns_track_to_pending_workspace(tmp_path) -> None:
    try:
        client = create_isolated_client(tmp_path)
        client.app.state.settings.auto_build_playlists = False
        client.app.state.settings.slack_bot_token = "xoxb-test"
        updates = []

        async def fake_update_review_message(track, **kwargs):
            updates.append({"track_id": track.id, **kwargs})
            return SimpleNamespace(ok=True, raw={"ok": True})

        request_updates = []

        async def fake_update_review_request_message(track, **kwargs):
            request_updates.append({"track_id": track.id, **kwargs})
            return SimpleNamespace(ok=True, raw={"ok": True})

        async def fake_post_review_message(track, **kwargs):
            return SimpleNamespace(ok=False, raw={"ok": False})

        client.app.state.services.slack.post_review_message = fake_post_review_message
        client.app.state.services.slack.update_review_message = fake_update_review_message
        client.app.state.services.slack.update_review_request_message = fake_update_review_request_message

        workspace_response = client.post(
            "/api/playlists/workspaces",
            json={
                "title": "Slack Approval Workspace",
                "target_duration_seconds": 120,
            },
        )
        assert workspace_response.status_code == 201
        workspace_id = workspace_response.json()["id"]

        track_response = client.post(
            "/api/tracks",
            json={
                "title": "Slack Approved Track",
                "prompt": "bright synth hook",
                "duration_seconds": 120,
                "audio_path": "https://cdn.example.com/slack-approved.mp3",
                "metadata": {
                    "source": "test",
                    "pending_workspace_id": workspace_id,
                },
            },
        )
        assert track_response.status_code == 201
        track_id = track_response.json()["id"]

        interaction_response = client.post(
            "/api/slack/interactions",
            data={
                "payload": json.dumps(
                    {
                        "actions": [{"value": f"track:{track_id}:approve"}],
                        "user": {"id": "U123", "username": "slack-reviewer"},
                        "container": {
                            "channel_id": "C123",
                            "message_ts": "1777000000.000300",
                        },
                    }
                )
            },
        )
        assert interaction_response.status_code == 200
        interaction = interaction_response.json()
        assert interaction["track_status"] == "approved"
        assert interaction["assigned_workspace_id"] == workspace_id
        assert interaction["assignment_error"] is None
        assert interaction["slack_update_ok"] is True
        assert updates[-1]["channel"] == "C123"
        assert updates[-1]["ts"] == "1777000000.000300"

        workspaces_response = client.get("/api/playlists/workspaces")
        assert workspaces_response.status_code == 200
        workspace = next(item for item in workspaces_response.json() if item["id"] == workspace_id)
        assert workspace["actual_duration_seconds"] == 120
        assert [track["id"] for track in workspace["tracks"]] == [track_id]

        track_after = client.get(f"/api/tracks/{track_id}")
        assert track_after.status_code == 200
        track = track_after.json()
        assert track["status"] == "approved"
        assert track["approvals"][-1]["source"] == "slack"
        assert track["approvals"][-1]["actor"] == "slack-reviewer"

        return_response = client.post(
            "/api/slack/interactions",
            data={
                "payload": json.dumps(
                    {
                        "actions": [{"value": f"track:{track_id}:return_to_review"}],
                        "user": {"id": "U123", "username": "slack-reviewer"},
                        "container": {
                            "channel_id": "C123",
                            "message_ts": "1777000000.000300",
                        },
                    }
                )
            },
        )
        assert return_response.status_code == 200
        returned = return_response.json()
        assert returned["track_status"] == "pending_review"
        assert returned["assignment_error"] is None
        assert returned["slack_update_ok"] is True
        assert request_updates[-1]["track_id"] == track_id

        workspaces_after_return = client.get("/api/playlists/workspaces")
        assert workspaces_after_return.status_code == 200
        workspace_after_return = next(
            item for item in workspaces_after_return.json() if item["id"] == workspace_id
        )
        assert workspace_after_return["actual_duration_seconds"] == 0
        assert workspace_after_return["tracks"] == []

        track_after_return = client.get(f"/api/tracks/{track_id}")
        assert track_after_return.status_code == 200
        assert track_after_return.json()["status"] == "pending_review"
    finally:
        clear_isolated_client_env()


def test_web_decision_updates_existing_slack_review_message(tmp_path) -> None:
    try:
        client = create_isolated_client(tmp_path)
        client.app.state.settings.auto_build_playlists = False
        client.app.state.settings.slack_bot_token = "xoxb-test"
        updates = []

        async def fake_update_review_message(track, **kwargs):
            updates.append({"track_id": track.id, **kwargs})
            return SimpleNamespace(ok=True, raw={"ok": True})

        client.app.state.services.slack.update_review_message = fake_update_review_message

        workspace_response = client.post(
            "/api/playlists/workspaces",
            json={
                "title": "Web Slack Sync Workspace",
                "target_duration_seconds": 120,
            },
        )
        assert workspace_response.status_code == 201
        workspace_id = workspace_response.json()["id"]

        track_response = client.post(
            "/api/tracks",
            json={
                "title": "Web Synced Track",
                "prompt": "warm guitar loop",
                "duration_seconds": 120,
                "audio_path": "https://cdn.example.com/web-synced.mp3",
                "metadata": {
                    "source": "test",
                    "pending_workspace_id": workspace_id,
                },
            },
        )
        assert track_response.status_code == 201
        track_id = track_response.json()["id"]

        db = SessionLocal()
        try:
            track = db.get(Track, track_id)
            track.slack_channel_id = "C123"
            track.slack_message_ts = "1777000000.000100"
            db.add(track)
            db.commit()
        finally:
            db.close()

        decision_response = client.post(
            f"/api/tracks/{track_id}/decisions",
            json={
                "decision": "approve",
                "actor": "web-reviewer",
                "playlist_id": workspace_id,
            },
        )
        assert decision_response.status_code == 200
        assert updates
        assert updates[-1]["track_id"] == track_id
        assert updates[-1]["decision"] == "approve"
        assert updates[-1]["actor"] == "web-reviewer"
        assert updates[-1]["workspace_title"] == "Web Slack Sync Workspace"
    finally:
        clear_isolated_client_env()


def test_return_approved_track_to_workspace_queue(tmp_path) -> None:
    try:
        client = create_isolated_client(tmp_path)
        request_updates = []

        async def fake_update_review_request_message(track, **kwargs):
            request_updates.append({"track_id": track.id, **kwargs})
            return SimpleNamespace(ok=True, raw={"ok": True})

        client.app.state.services.slack.update_review_request_message = fake_update_review_request_message

        workspace_response = client.post(
            "/api/playlists/workspaces",
            json={
                "title": "Workspace Hold Test",
                "target_duration_seconds": 240,
            },
        )
        assert workspace_response.status_code == 201
        workspace_id = workspace_response.json()["id"]

        track_response = client.post(
            "/api/tracks",
            json={
                "title": "Approved Then Hold",
                "prompt": "city pop with soft pads",
                "duration_seconds": 120,
                "audio_path": str(tmp_path / "hold-test.mp3"),
                "metadata": {"source": "test"},
            },
        )
        assert track_response.status_code == 201
        track_id = track_response.json()["id"]

        approve_response = client.post(
            f"/api/tracks/{track_id}/decisions",
            json={
                "decision": "approve",
                "source": "human",
                "actor": "test-suite",
                "playlist_id": workspace_id,
            },
        )
        assert approve_response.status_code == 200

        db = SessionLocal()
        try:
            track = db.get(Track, track_id)
            track.slack_channel_id = "C123"
            track.slack_message_ts = "1777000000.000200"
            db.add(track)
            db.commit()
        finally:
            db.close()

        hold_response = client.post(
            f"/api/tracks/{track_id}/return-to-review",
            json={
                "playlist_id": workspace_id,
                "actor": "test-suite",
                "rationale": "Move back to review queue.",
            },
        )
        assert hold_response.status_code == 200
        held_track = hold_response.json()
        assert held_track["status"] == "pending_review"
        assert held_track["metadata_json"]["pending_workspace_id"] == workspace_id
        assert request_updates[-1]["track_id"] == track_id
        assert request_updates[-1]["channel"] == "C123"
        assert request_updates[-1]["ts"] == "1777000000.000200"

        workspaces_response = client.get("/api/playlists/workspaces")
        assert workspaces_response.status_code == 200
        workspace = next(item for item in workspaces_response.json() if item["id"] == workspace_id)
        assert workspace["tracks"] == []

        track_after = client.get(f"/api/tracks/{track_id}")
        assert track_after.status_code == 200
        assert track_after.json()["status"] == "pending_review"
        assert track_after.json()["metadata_json"]["pending_workspace_id"] == workspace_id
    finally:
        clear_isolated_client_env()


def test_release_pipeline_generates_cover_video_and_metadata_before_publish(tmp_path) -> None:
    try:
        client = create_isolated_client(tmp_path)
        services = client.app.state.services

        def fake_build_audio(tracks, output_path):
            output_path.write_bytes(b"fake-mp3")
            return output_path

        def fake_build_video(audio_path, cover_image_path, output_path):
            output_path.write_bytes(b"fake-mp4")
            return output_path

        services.playlist_builder.build_audio = fake_build_audio
        services.playlist_builder.build_video = fake_build_video
        workspace_response = client.post(
            "/api/playlists/workspaces",
            json={
                "title": "Upload Workspace",
                "target_duration_seconds": 60,
                "cover_prompt": "Night freeway and glowing taillights",
            },
        )
        workspace_id = workspace_response.json()["id"]

        local_audio = tmp_path / "cover-source.mp3"
        local_audio.write_bytes(b"fake source")
        track_response = client.post(
            "/api/tracks",
            json={
                "title": "Single Track",
                "prompt": "minimal electronic",
                "duration_seconds": 60,
                "audio_path": str(local_audio),
                "metadata": {"source": "test"},
            },
        )
        track_id = track_response.json()["id"]

        approve_response = client.post(
            f"/api/tracks/{track_id}/decisions",
            json={
                "decision": "approve",
                "source": "human",
                "actor": "test-suite",
                "playlist_id": workspace_id,
            },
        )
        assert approve_response.status_code == 200
        render_workspace_audio(client, workspace_id)

        staged = prepare_release_for_final_publish(client, workspace_id)
        assert staged["cover_approved"] is True
        assert staged["metadata_approved"] is True
        assert os.path.exists(staged["cover_image_path"])

        publish_response = client.post(
            f"/api/playlists/{workspace_id}/approve-publish",
            json={
                "actor": "test-suite",
                "note": "ready to publish",
            },
        )
        assert publish_response.status_code == 200
        assert publish_response.json()["workflow_state"] == "publish_queued"
        assert drain_background_jobs(client) == 1
        workspaces_response = client.get("/api/playlists/workspaces")
        published = next(item for item in workspaces_response.json() if item["id"] == workspace_id)
        assert published["workflow_state"] == "ready_for_youtube_auth"
        assert published["cover_image_path"].endswith(".png")
        assert published["output_video_path"].endswith(".mp4")
        assert os.path.exists(published["cover_image_path"])
    finally:
        clear_isolated_client_env()


def test_cover_image_can_be_uploaded_for_review(tmp_path) -> None:
    try:
        client = create_isolated_client(tmp_path)
        services = client.app.state.services

        def fake_build_audio(tracks, output_path):
            output_path.write_bytes(b"fake-mp3")
            return output_path

        def fake_build_video(audio_path, cover_image_path, output_path):
            assert cover_image_path.exists()
            output_path.write_bytes(b"fake-mp4")
            return output_path

        services.playlist_builder.build_audio = fake_build_audio
        services.playlist_builder.build_video = fake_build_video

        workspace_response = client.post(
            "/api/playlists/workspaces",
            json={
                "title": "Uploaded Cover Workspace",
                "target_duration_seconds": 60,
            },
        )
        workspace_id = workspace_response.json()["id"]

        local_audio = tmp_path / "uploaded-cover-source.mp3"
        local_audio.write_bytes(b"fake source")
        track_response = client.post(
            "/api/tracks",
            json={
                "title": "Cover Upload Track",
                "prompt": "minimal electronic",
                "duration_seconds": 60,
                "audio_path": str(local_audio),
                "metadata": {"source": "test"},
            },
        )
        track_id = track_response.json()["id"]

        approve_response = client.post(
            f"/api/tracks/{track_id}/decisions",
            json={
                "decision": "approve",
                "source": "human",
                "actor": "test-suite",
                "playlist_id": workspace_id,
            },
        )
        assert approve_response.status_code == 200
        render_workspace_audio(client, workspace_id)

        upload_response = client.post(
            f"/api/playlists/{workspace_id}/cover/upload",
            data={"actor": "test-suite"},
            files={"cover_file": ("cover.png", b"fake-png", "image/png")},
        )
        assert upload_response.status_code == 200
        uploaded = upload_response.json()
        assert uploaded["workflow_state"] == "cover_review"
        assert uploaded["cover_approved"] is False
        assert uploaded["cover_image_path"].endswith(".png")
        assert os.path.exists(uploaded["cover_image_path"])

        approve_cover_response = client.post(
            f"/api/playlists/{workspace_id}/cover/approve",
            json={"actor": "test-suite", "approved": True},
        )
        assert approve_cover_response.status_code == 200
        render_video_response = client.post(
            f"/api/playlists/{workspace_id}/video/render",
            json={"actor": "test-suite"},
        )
        assert render_video_response.status_code == 400
        assert "loop video is required" in render_video_response.json()["detail"]

        render_video_response = client.post(
            f"/api/playlists/{workspace_id}/video/render",
            json={"actor": "test-suite", "allow_still_image_fallback": True},
        )
        assert render_video_response.status_code == 200
        assert drain_background_jobs(client) == 1

        workspaces_response = client.get("/api/playlists/workspaces")
        workspace = next(item for item in workspaces_response.json() if item["id"] == workspace_id)
        assert workspace["workflow_state"] == "metadata_review"
        assert workspace["output_video_path"].endswith(".mp4")
    finally:
        clear_isolated_client_env()


def test_uploaded_loop_video_is_used_for_video_render(tmp_path) -> None:
    try:
        client = create_isolated_client(tmp_path)
        services = client.app.state.services

        def fake_build_audio(tracks, output_path):
            output_path.write_bytes(b"fake-mp3")
            return output_path

        def fake_build_looped_video(clip_path, audio_path, output_path, *, smooth_loop=True, **_kwargs):
            assert clip_path.exists()
            assert clip_path.name.endswith(".mp4")
            assert audio_path.exists()
            assert smooth_loop is True
            output_path.write_bytes(b"fake-looped-mp4")
            return output_path

        def fake_build_video(*_args, **_kwargs):
            raise AssertionError("still-image video renderer should not be used when loop video is uploaded")

        services.playlist_builder.build_audio = fake_build_audio
        services.playlist_builder.build_looped_video = fake_build_looped_video
        services.playlist_builder.build_video = fake_build_video

        workspace_response = client.post(
            "/api/playlists/workspaces",
            json={
                "title": "Loop Video Workspace",
                "target_duration_seconds": 60,
            },
        )
        workspace_id = workspace_response.json()["id"]

        local_audio = tmp_path / "source.mp3"
        local_audio.write_bytes(b"fake source")
        track_response = client.post(
            "/api/tracks",
            json={
                "title": "Loop Track",
                "prompt": "ambient loop visual",
                "duration_seconds": 60,
                "audio_path": str(local_audio),
                "metadata": {"source": "test"},
            },
        )
        track_id = track_response.json()["id"]

        approve_response = client.post(
            f"/api/tracks/{track_id}/decisions",
            json={
                "decision": "approve",
                "source": "human",
                "actor": "test-suite",
                "playlist_id": workspace_id,
            },
        )
        assert approve_response.status_code == 200
        render_workspace_audio(client, workspace_id)

        cover_response = client.post(
            f"/api/playlists/{workspace_id}/cover/upload",
            data={"actor": "test-suite"},
            files={"cover_file": ("cover.png", b"fake-png", "image/png")},
        )
        assert cover_response.status_code == 200
        loop_payload = upload_test_loop_video(client, workspace_id, provider="gemini")
        assert loop_payload["loop_video_path"].endswith(".mp4")
        assert loop_payload["loop_video_source"] == "manual-upload"
        assert loop_payload["loop_video_provider"] == "gemini"
        assert loop_payload["loop_video_smooth"] is True

        approve_cover_response = client.post(
            f"/api/playlists/{workspace_id}/cover/approve",
            json={"actor": "test-suite", "approved": True},
        )
        assert approve_cover_response.status_code == 200
        render_video_response = client.post(
            f"/api/playlists/{workspace_id}/video/render",
            json={"actor": "test-suite"},
        )
        assert render_video_response.status_code == 200
        assert drain_background_jobs(client) == 1

        workspaces_response = client.get("/api/playlists/workspaces")
        workspace = next(item for item in workspaces_response.json() if item["id"] == workspace_id)
        assert workspace["workflow_state"] == "metadata_review"
        assert workspace["output_video_path"].endswith(".mp4")
        assert workspace["loop_video_path"].endswith(".mp4")
        assert workspace["loop_video_provider"] == "gemini"
    finally:
        clear_isolated_client_env()


def test_uploaded_loop_video_can_be_deleted_and_requires_replacement(tmp_path) -> None:
    try:
        client = create_isolated_client(tmp_path)
        services = client.app.state.services

        def fake_build_audio(tracks, output_path):
            output_path.write_bytes(b"fake-mp3")
            return output_path

        def fake_build_looped_video(clip_path, audio_path, output_path, *, smooth_loop=True, **_kwargs):
            assert clip_path.exists()
            assert audio_path.exists()
            output_path.write_bytes(b"fake-looped-mp4")
            return output_path

        services.playlist_builder.build_audio = fake_build_audio
        services.playlist_builder.build_looped_video = fake_build_looped_video

        workspace_response = client.post(
            "/api/playlists/workspaces",
            json={
                "title": "Delete Loop Video Workspace",
                "target_duration_seconds": 60,
            },
        )
        workspace_id = workspace_response.json()["id"]

        local_audio = tmp_path / "source.mp3"
        local_audio.write_bytes(b"fake source")
        track_response = client.post(
            "/api/tracks",
            json={
                "title": "Delete Loop Track",
                "prompt": "ambient loop visual",
                "duration_seconds": 60,
                "audio_path": str(local_audio),
                "metadata": {"source": "test"},
            },
        )
        track_id = track_response.json()["id"]
        approve_response = client.post(
            f"/api/tracks/{track_id}/decisions",
            json={
                "decision": "approve",
                "source": "human",
                "actor": "test-suite",
                "playlist_id": workspace_id,
            },
        )
        assert approve_response.status_code == 200
        render_workspace_audio(client, workspace_id)

        cover_response = client.post(
            f"/api/playlists/{workspace_id}/cover/upload",
            data={"actor": "test-suite"},
            files={"cover_file": ("cover.png", b"fake-png", "image/png")},
        )
        assert cover_response.status_code == 200
        loop_payload = upload_test_loop_video(client, workspace_id)
        loop_video_path = loop_payload["loop_video_path"]
        assert Path(loop_video_path).exists()

        approve_cover_response = client.post(
            f"/api/playlists/{workspace_id}/cover/approve",
            json={"actor": "test-suite", "approved": True},
        )
        assert approve_cover_response.status_code == 200
        render_video_response = client.post(
            f"/api/playlists/{workspace_id}/video/render",
            json={"actor": "test-suite"},
        )
        assert render_video_response.status_code == 200
        assert drain_background_jobs(client) == 1

        delete_response = client.delete(
            f"/api/playlists/{workspace_id}/loop-video",
            params={"actor": "test-suite"},
        )
        assert delete_response.status_code == 200
        deleted = delete_response.json()
        assert deleted["loop_video_path"] is None
        assert deleted["loop_video_source"] is None
        assert deleted["output_video_path"] is None
        assert deleted["youtube_video_id"] is None
        assert deleted["workflow_state"] == "video_required"
        assert "replacement loop video" in deleted["note"]
        assert not Path(loop_video_path).exists()

        with SessionLocal() as db:
            playlist = db.get(Playlist, workspace_id)
            clear_history = playlist.metadata_json["loop_video_clear_history"]
            assert clear_history[-1]["loop_video_path"] == loop_video_path
            assert clear_history[-1]["deleted_local_file"] is True

        rerender_response = client.post(
            f"/api/playlists/{workspace_id}/video/render",
            json={"actor": "test-suite"},
        )
        assert rerender_response.status_code == 400
        assert "loop video is required" in rerender_response.json()["detail"]
    finally:
        clear_isolated_client_env()


def test_background_worker_marks_interrupted_upload_for_retry(tmp_path) -> None:
    try:
        client = create_isolated_client(tmp_path)

        with SessionLocal() as db:
            playlist = Playlist(
                title="Interrupted Publish",
                status=PlaylistStatus.ready,
                target_duration_seconds=60,
                actual_duration_seconds=60,
                metadata_json={
                    "workflow_state": "publish_queued",
                    "publish_ready": True,
                    "publish_approved": True,
                },
            )
            db.add(playlist)
            db.flush()
            job = Job(
                type=JobType.upload_youtube,
                status=JobStatus.running,
                source="web",
                playlist=playlist,
                playlist_id=playlist.id,
                payload_json={"playlist_id": playlist.id},
                result_json={},
                started_at=datetime.now(timezone.utc) - timedelta(minutes=5),
            )
            db.add(job)
            db.commit()
            job_id = job.id
            playlist_id = playlist.id

        result = client.app.state.services.worker.recover_interrupted_jobs()

        assert result["failed_uploads"] == 1
        with SessionLocal() as db:
            job = db.get(Job, job_id)
            playlist = db.get(Playlist, playlist_id)
            assert job.status == JobStatus.failed
            assert "interrupted" in job.error_text.lower()
            assert job.result_json["interrupted_worker_resolution"] == "failed_requires_retry"
            assert playlist.status == PlaylistStatus.ready
            assert playlist.metadata_json["workflow_state"] == "youtube_upload_failed"
            assert playlist.metadata_json["publish_approved"] is False
    finally:
        clear_isolated_client_env()


def test_single_release_uses_source_audio_and_uploaded_cover_can_render_video(tmp_path) -> None:
    try:
        client = create_isolated_client(tmp_path)
        services = client.app.state.services

        def fake_build_video(audio_path, cover_image_path, output_path):
            assert audio_path.name == "single-source.mp3"
            assert cover_image_path.exists()
            output_path.write_bytes(b"fake-single-mp4")
            return output_path

        services.playlist_builder.build_video = fake_build_video

        workspace_response = client.post(
            "/api/playlists/workspaces",
            json={
                "title": "Single Upload Cover",
                "workspace_mode": "single_track_video",
            },
        )
        assert workspace_response.status_code == 201
        workspace_id = workspace_response.json()["id"]

        local_audio = tmp_path / "single-source.mp3"
        local_audio.write_bytes(b"fake source")
        track_response = client.post(
            "/api/tracks",
            json={
                "title": "Single Source Track",
                "prompt": "single release source",
                "duration_seconds": 88,
                "audio_path": str(local_audio),
                "metadata": {"source": "test"},
            },
        )
        track_id = track_response.json()["id"]

        approve_response = client.post(
            f"/api/tracks/{track_id}/decisions",
            json={
                "decision": "approve",
                "source": "human",
                "actor": "test-suite",
                "playlist_id": workspace_id,
            },
        )
        assert approve_response.status_code == 200
        assert drain_background_jobs(client) == 0

        workspaces_response = client.get("/api/playlists/workspaces")
        audio_ready = next(item for item in workspaces_response.json() if item["id"] == workspace_id)
        assert audio_ready["workflow_state"] == "audio_ready"
        assert audio_ready["output_audio_path"] == str(local_audio)

        upload_response = client.post(
            f"/api/playlists/{workspace_id}/cover/upload",
            data={"actor": "test-suite"},
            files={"cover_file": ("single-cover.png", b"fake-png", "image/png")},
        )
        assert upload_response.status_code == 200
        uploaded = upload_response.json()
        assert uploaded["workflow_state"] == "cover_review"
        assert uploaded["cover_image_path"].endswith(".png")

        approve_cover_response = client.post(
            f"/api/playlists/{workspace_id}/cover/approve",
            json={"actor": "test-suite", "approved": True},
        )
        assert approve_cover_response.status_code == 200
        assert approve_cover_response.json()["workflow_state"] == "video_required"

        render_response = client.post(
            f"/api/playlists/{workspace_id}/video/render",
            json={"actor": "test-suite", "allow_still_image_fallback": True},
        )
        assert render_response.status_code == 200
        assert render_response.json()["workflow_state"] == "video_queued"
        assert drain_background_jobs(client) == 1

        refreshed_response = client.get("/api/playlists/workspaces")
        rendered = next(item for item in refreshed_response.json() if item["id"] == workspace_id)
        assert rendered["workflow_state"] == "metadata_review"
        assert rendered["output_video_path"].endswith(".mp4")
    finally:
        clear_isolated_client_env()


def test_single_release_promotes_uploaded_candidate_cover_on_approval(tmp_path) -> None:
    try:
        client = create_isolated_client(tmp_path)
        workspace_response = client.post(
            "/api/playlists/workspaces",
            json={
                "title": "Single Candidate With Cover",
                "workspace_mode": "single_track_video",
            },
        )
        assert workspace_response.status_code == 201
        workspace_id = workspace_response.json()["id"]

        upload_response = client.post(
            "/api/tracks/manual-upload",
            data={
                "title": "Covered Candidate",
                "prompt": "single with generated cover",
                "duration_seconds": "60",
                "pending_workspace_id": workspace_id,
            },
            files={
                "audio_file": ("covered-candidate.mp3", b"fake-audio", "audio/mpeg"),
                "cover_file": ("covered-candidate.png", b"fake-cover", "image/png"),
            },
        )
        assert upload_response.status_code == 201
        track = upload_response.json()
        assert track["metadata_json"]["cover_source"] == "cover-upload"
        assert track["metadata_json"]["image_url"].endswith(".png")
        assert os.path.exists(track["metadata_json"]["image_url"])

        approve_response = client.post(
            f"/api/tracks/{track['id']}/decisions",
            json={
                "decision": "approve",
                "source": "human",
                "actor": "test-suite",
                "playlist_id": workspace_id,
            },
        )
        assert approve_response.status_code == 200

        workspaces_response = client.get("/api/playlists/workspaces")
        workspace = next(item for item in workspaces_response.json() if item["id"] == workspace_id)
        assert workspace["workflow_state"] == "cover_review"
        assert workspace["cover_image_path"] == track["metadata_json"]["image_url"]
        assert workspace["cover_approved"] is False
        assert workspace["output_audio_path"].endswith(".mp3")
    finally:
        clear_isolated_client_env()


def test_publish_approval_rejects_incomplete_workspace(tmp_path) -> None:
    try:
        client = create_isolated_client(tmp_path)
        workspace_response = client.post(
            "/api/playlists/workspaces",
            json={
                "title": "Incomplete Workspace",
                "target_duration_seconds": 300,
            },
        )
        workspace_id = workspace_response.json()["id"]

        publish_response = client.post(
            f"/api/playlists/{workspace_id}/approve-publish",
            json={
                "actor": "test-suite",
            },
        )

        assert publish_response.status_code == 400
        assert publish_response.json()["detail"] == "Playlist has no tracks to publish."
    finally:
        clear_isolated_client_env()


def test_publish_approval_with_manual_video_id_stores_channel_title(tmp_path) -> None:
    try:
        client = create_isolated_client(tmp_path)
        client.app.state.services.youtube.get_channel = lambda channel_id: {
            "id": channel_id,
            "title": "Soft Hour Radio",
        }
        workspace_response = client.post(
            "/api/playlists/workspaces",
            json={
                "title": "Manual YouTube Id Workspace",
                "target_duration_seconds": 300,
            },
        )
        workspace_id = workspace_response.json()["id"]
        local_audio = tmp_path / "manual-youtube-id.mp3"
        local_audio.write_bytes(b"fake source")
        track_response = client.post(
            "/api/tracks",
            json={
                "title": "Manual YouTube Id Track",
                "prompt": "manual youtube id channel test",
                "duration_seconds": 60,
                "audio_path": str(local_audio),
                "metadata": {"source": "test"},
            },
        )
        track_id = track_response.json()["id"]

        approve_response = client.post(
            f"/api/tracks/{track_id}/decisions",
            json={
                "decision": "approve",
                "source": "human",
                "actor": "test-suite",
                "playlist_id": workspace_id,
            },
        )
        assert approve_response.status_code == 200

        publish_response = client.post(
            f"/api/playlists/{workspace_id}/approve-publish",
            json={
                "actor": "test-suite",
                "youtube_video_id": "manual-video-123",
                "youtube_channel_id": "UC-soft-hour",
                "force_under_target": True,
            },
        )

        assert publish_response.status_code == 200
        payload = publish_response.json()
        assert payload["youtube_video_id"] == "manual-video-123"
        assert payload["youtube_channel_id"] == "UC-soft-hour"
        assert payload["youtube_channel_title"] == "Soft Hour Radio"
    finally:
        clear_isolated_client_env()


def test_publish_approval_reports_video_build_failure(tmp_path) -> None:
    try:
        client = create_isolated_client(tmp_path)
        services = client.app.state.services

        def fake_build_audio(tracks, output_path):
            output_path.write_bytes(b"fake-mp3")
            return output_path

        def fake_build_video(audio_path, cover_image_path, output_path):
            raise RuntimeError("ffmpeg missing")

        services.playlist_builder.build_audio = fake_build_audio
        services.playlist_builder.build_video = fake_build_video

        workspace_response = client.post(
            "/api/playlists/workspaces",
            json={
                "title": "Broken Video Workspace",
                "target_duration_seconds": 60,
            },
        )
        workspace_id = workspace_response.json()["id"]

        local_audio = tmp_path / "single.mp3"
        local_audio.write_bytes(b"fake source")
        track_response = client.post(
            "/api/tracks",
            json={
                "title": "Single Track",
                "prompt": "minimal electronic",
                "duration_seconds": 60,
                "audio_path": str(local_audio),
                "metadata": {"source": "test"},
            },
        )
        track_id = track_response.json()["id"]

        approve_response = client.post(
            f"/api/tracks/{track_id}/decisions",
            json={
                "decision": "approve",
                "source": "human",
                "actor": "test-suite",
                "playlist_id": workspace_id,
            },
        )
        assert approve_response.status_code == 200
        render_workspace_audio(client, workspace_id)

        cover_response = client.post(
            f"/api/playlists/{workspace_id}/cover/generate",
            json={"actor": "test-suite"},
        )
        assert cover_response.status_code == 200
        approve_cover_response = client.post(
            f"/api/playlists/{workspace_id}/cover/approve",
            json={"actor": "test-suite", "approved": True},
        )
        assert approve_cover_response.status_code == 200
        render_response = client.post(
            f"/api/playlists/{workspace_id}/video/render",
            json={"actor": "test-suite", "allow_still_image_fallback": True},
        )
        assert render_response.status_code == 200
        assert drain_background_jobs(client) == 1

        workspaces_response = client.get("/api/playlists/workspaces")
        published = next(item for item in workspaces_response.json() if item["id"] == workspace_id)
        assert published["workflow_state"] == "video_build_failed"
        assert "ffmpeg missing" in published["note"]
    finally:
        clear_isolated_client_env()


def test_failed_workspace_archive_is_purged_after_retention(tmp_path) -> None:
    try:
        client = create_isolated_client(tmp_path)
        services = client.app.state.services

        def fake_build_audio(tracks, output_path):
            output_path.write_bytes(b"fake-mp3")
            return output_path

        def fake_build_video(audio_path, cover_image_path, output_path):
            raise RuntimeError("ffmpeg missing")

        services.playlist_builder.build_audio = fake_build_audio
        services.playlist_builder.build_video = fake_build_video

        workspace_response = client.post(
            "/api/playlists/workspaces",
            json={
                "title": "Failed Archive Workspace",
                "target_duration_seconds": 60,
            },
        )
        workspace_id = workspace_response.json()["id"]

        local_audio = tmp_path / "single.mp3"
        local_audio.write_bytes(b"fake source")
        track_response = client.post(
            "/api/tracks",
            json={
                "title": "Single Track",
                "prompt": "minimal electronic",
                "duration_seconds": 60,
                "audio_path": str(local_audio),
                "metadata": {"source": "test"},
            },
        )
        track_id = track_response.json()["id"]

        approve_response = client.post(
            f"/api/tracks/{track_id}/decisions",
            json={
                "decision": "approve",
                "source": "human",
                "actor": "test-suite",
                "playlist_id": workspace_id,
            },
        )
        assert approve_response.status_code == 200
        render_workspace_audio(client, workspace_id)

        cover_response = client.post(
            f"/api/playlists/{workspace_id}/cover/generate",
            json={"actor": "test-suite"},
        )
        assert cover_response.status_code == 200
        approve_cover_response = client.post(
            f"/api/playlists/{workspace_id}/cover/approve",
            json={"actor": "test-suite", "approved": True},
        )
        assert approve_cover_response.status_code == 200
        render_response = client.post(
            f"/api/playlists/{workspace_id}/video/render",
            json={"actor": "test-suite", "allow_still_image_fallback": True},
        )
        assert render_response.status_code == 200
        assert drain_background_jobs(client) == 1

        archive_response = client.post(
            f"/api/playlists/{workspace_id}/archive",
            json={
                "actor": "test-suite",
                "archived": True,
                "revive_rejected": False,
            },
        )
        assert archive_response.status_code == 200
        archived = archive_response.json()
        assert archived["hidden"] is True
        assert archived["workflow_state"] == "archived"
        assert archived["archived_at"]
        assert archived["purge_after"]
        assert "permanently deleted after 7 days" in archived["note"]

        with SessionLocal() as db:
            playlist = db.get(Playlist, workspace_id)
            meta = dict(playlist.metadata_json or {})
            audio_path = Path(playlist.output_audio_path)
            cover_path = Path(meta["cover_image_path"])
            assert audio_path.exists()
            assert cover_path.exists()
            old_archive_time = datetime.now(timezone.utc) - timedelta(days=8)
            meta["archived_at"] = old_archive_time.isoformat()
            meta["purge_after"] = (old_archive_time + timedelta(days=7)).isoformat()
            playlist.metadata_json = meta
            db.add(playlist)
            db.commit()

        workspaces_response = client.get("/api/playlists/workspaces")
        assert workspaces_response.status_code == 200
        assert all(item["id"] != workspace_id for item in workspaces_response.json())
        assert not audio_path.exists()
        assert not cover_path.exists()
        with SessionLocal() as db:
            assert db.get(Playlist, workspace_id) is None
    finally:
        clear_isolated_client_env()


def test_publish_approval_can_force_under_target_playlist(tmp_path) -> None:
    try:
        client = create_isolated_client(tmp_path)
        services = client.app.state.services

        def fake_build_audio(tracks, output_path):
            output_path.write_bytes(b"fake-mp3")
            return output_path

        def fake_build_video(audio_path, cover_image_path, output_path):
            output_path.write_bytes(b"fake-mp4")
            return output_path

        services.playlist_builder.build_audio = fake_build_audio
        services.playlist_builder.build_video = fake_build_video

        workspace_response = client.post(
            "/api/playlists/workspaces",
            json={
                "title": "Short Playlist",
                "target_duration_seconds": 3600,
            },
        )
        workspace_id = workspace_response.json()["id"]

        local_audio = tmp_path / "short.mp3"
        local_audio.write_bytes(b"fake source")
        track_response = client.post(
            "/api/tracks",
            json={
                "title": "Short Track",
                "prompt": "short playlist",
                "duration_seconds": 120,
                "audio_path": str(local_audio),
                "metadata": {"source": "test"},
            },
        )
        track_id = track_response.json()["id"]

        approve_response = client.post(
            f"/api/tracks/{track_id}/decisions",
            json={
                "decision": "approve",
                "source": "human",
                "actor": "test-suite",
                "playlist_id": workspace_id,
            },
        )
        assert approve_response.status_code == 200
        render_response = client.post(
            f"/api/playlists/{workspace_id}/render-audio",
            json={"actor": "test-suite"},
        )
        assert render_response.status_code == 200
        assert drain_background_jobs(client) == 1

        prepare_release_for_final_publish(client, workspace_id)

        blocked_response = client.post(
            f"/api/playlists/{workspace_id}/approve-publish",
            json={"actor": "test-suite"},
        )
        assert blocked_response.status_code == 400
        assert blocked_response.json()["detail"] == "Playlist has not reached its target duration yet."

        forced_response = client.post(
            f"/api/playlists/{workspace_id}/approve-publish",
            json={
                "actor": "test-suite",
                "note": "publish short playlist",
                "force_under_target": True,
            },
        )
        assert forced_response.status_code == 200
        forced = forced_response.json()
        assert forced["workflow_state"] == "publish_queued"

        assert drain_background_jobs(client) == 1
        workspaces_response = client.get("/api/playlists/workspaces")
        published = next(item for item in workspaces_response.json() if item["id"] == workspace_id)
        assert published["workflow_state"] == "ready_for_youtube_auth"
    finally:
        clear_isolated_client_env()


def test_publish_approval_auto_uploads_when_youtube_ready(tmp_path) -> None:
    try:
        client = create_isolated_client(tmp_path)
        services = client.app.state.services

        def fake_build_audio(tracks, output_path):
            output_path.write_bytes(b"fake-mp3")
            return output_path

        def fake_build_video(audio_path, cover_image_path, output_path):
            output_path.write_bytes(b"fake-mp4")
            return output_path

        def fake_build_looped_video(clip_path, audio_path, output_path, **_kwargs):
            assert clip_path.name.endswith(".mp4")
            output_path.write_bytes(b"fake-looped-mp4")
            return output_path

        services.playlist_builder.build_audio = fake_build_audio
        services.playlist_builder.build_video = fake_build_video
        services.playlist_builder.build_looped_video = fake_build_looped_video
        services.youtube.get_status = lambda: {"configured": True, "authenticated": True, "ready": True}
        upload_video_ids = ["yt-auto-123"]
        upload_channel_ids = []
        upload_localizations = []

        def fake_upload_playlist_video(*args, **kwargs):
            upload_channel_ids.append(kwargs.get("youtube_channel_id"))
            upload_localizations.append(
                {
                    "default_language": kwargs.get("default_language"),
                    "localizations": kwargs.get("localizations"),
                }
            )
            return SimpleNamespace(
                video_id=upload_video_ids[-1],
                response={
                    "id": upload_video_ids[-1],
                    "upload_channel": {"id": kwargs.get("youtube_channel_id"), "title": "Main Music"},
                },
            )

        services.youtube.upload_playlist_video = fake_upload_playlist_video

        workspace_response = client.post(
            "/api/playlists/workspaces",
            json={
                "title": "Auto Upload Workspace",
                "target_duration_seconds": 60,
                "description": "Auto upload flow",
                "cover_prompt": "Orange skyline and highway lights",
            },
        )
        workspace_id = workspace_response.json()["id"]

        local_audio = tmp_path / "single.mp3"
        local_audio.write_bytes(b"fake source")
        track_response = client.post(
            "/api/tracks",
            json={
                "title": "Single Track",
                "prompt": "minimal electronic",
                "duration_seconds": 60,
                "audio_path": str(local_audio),
                "metadata": {"source": "test", "tags": "night,drive"},
            },
        )
        track_id = track_response.json()["id"]

        approve_response = client.post(
            f"/api/tracks/{track_id}/decisions",
            json={
                "decision": "approve",
                "source": "human",
                "actor": "test-suite",
                "playlist_id": workspace_id,
            },
        )
        assert approve_response.status_code == 200
        render_workspace_audio(client, workspace_id)

        prepared_release = prepare_release_for_final_publish(client, workspace_id)
        localized_metadata_response = client.post(
            f"/api/playlists/{workspace_id}/metadata/approve",
            json={
                "actor": "test-suite",
                "title": "한국어 제목",
                "description": "한국어 설명\n\n00:00:00 Single Track\n\n#jpop #playlist",
                "tags": "jpop,playlist",
                "default_language": "ko",
                "localizations": {
                    language: {
                        "title": {
                            "ko": "한국어 제목",
                            "ja": "日本語タイトル",
                            "en": "English Title",
                            "es": "Titulo en espanol",
                        }.get(language, f"{language} Title"),
                        "description": {
                            "ko": "한국어 설명",
                            "ja": "日本語の説明",
                            "en": "English description",
                            "es": "Descripcion en espanol",
                        }.get(language, f"{language} description")
                        + "\n\n00:00:00 Single Track\n\n#jpop #playlist",
                    }
                    for language in SUPPORTED_YOUTUBE_LANGUAGES
                },
            },
        )
        assert localized_metadata_response.status_code == 200
        assert localized_metadata_response.json()["youtube_title"] == "[playlist] 한국어 제목"
        assert localized_metadata_response.json()["youtube_localizations"]["ja"]["title"] == "[playlist] 日本語タイトル"
        assert "#jpop #playlist" in localized_metadata_response.json()["youtube_description"]
        assert "#jpop #playlist" in localized_metadata_response.json()["youtube_localizations"]["ja"]["description"]
        assert "#jpop #playlist" in localized_metadata_response.json()["youtube_localizations"]["en"]["description"]
        assert "#jpop #playlist" in localized_metadata_response.json()["youtube_localizations"]["es"]["description"]
        with SessionLocal() as db:
            playlist = db.get(Playlist, workspace_id)
            meta = dict(playlist.metadata_json or {})
            meta["youtube_upload_error"] = "old thumbnail failure"
            playlist.metadata_json = meta
            db.add(playlist)
            db.commit()

        first_video_path = localized_metadata_response.json()["output_video_path"] or prepared_release["output_video_path"]
        assert os.path.exists(first_video_path)
        ops_calls = []

        services.settings.slack_bot_token = "xoxb-test"
        services.settings.slack_ops_channel_id = "#all-ai-music-playlist-generator"
        install_fake_ops_slack(services, ops_calls)

        publish_response = client.post(
            f"/api/playlists/{workspace_id}/approve-publish",
            json={
                "actor": "test-suite",
                "note": "auto upload ready",
                "youtube_channel_id": "UC123",
            },
        )
        assert publish_response.status_code == 200
        assert publish_response.json()["workflow_state"] == "publish_queued"
        assert drain_background_jobs(client) == 1

        workspaces_response = client.get("/api/playlists/workspaces")
        published = next(item for item in workspaces_response.json() if item["id"] == workspace_id)
        assert published["workflow_state"] == "uploaded"
        assert published["youtube_video_id"] == "yt-auto-123"
        assert published["output_video_path"] is None
        assert not os.path.exists(first_video_path)
        assert any("YouTube publish completed" in call["text"] for call in ops_calls)
        assert any("https://youtu.be/yt-auto-123" in call["text"] for call in ops_calls)
        assert upload_channel_ids[-1] == "UC123"
        assert upload_localizations[-1]["default_language"] == "ko"
        assert upload_localizations[-1]["localizations"]["en"]["title"] == "[playlist] English Title"
        original_youtube_title = published["youtube_title"]
        original_youtube_description = published["youtube_description"]
        original_youtube_localizations = published["youtube_localizations"]
        with SessionLocal() as db:
            playlist = db.get(Playlist, workspace_id)
            assert "youtube_upload_error" not in playlist.metadata_json
            assert playlist.metadata_json["youtube_channel_id"] == "UC123"
            assert playlist.metadata_json["local_video_deleted_after_youtube_upload"] == first_video_path

        loop_replaced = upload_test_loop_video(client, workspace_id)
        assert loop_replaced["workflow_state"] == "video_required"
        assert loop_replaced["loop_video_path"].endswith(".mp4")
        assert loop_replaced["metadata_approved"] is False
        assert loop_replaced["publish_approved"] is False
        assert loop_replaced["youtube_video_id"] == "yt-auto-123"

        upload_video_ids.append("yt-auto-456")
        render_again_response = client.post(
            f"/api/playlists/{workspace_id}/video/render",
            json={"actor": "test-suite"},
        )
        assert render_again_response.status_code == 200
        assert drain_background_jobs(client) == 1
        metadata_again_response = client.get("/api/playlists/workspaces")
        metadata_again = next(item for item in metadata_again_response.json() if item["id"] == workspace_id)
        assert metadata_again["youtube_title"] == original_youtube_title
        assert metadata_again["youtube_description"] == original_youtube_description
        assert metadata_again["youtube_localizations"] == original_youtube_localizations
        assert metadata_again["metadata_approved"] is False
        metadata_again_description = metadata_again["youtube_description"]
        if "00:00" not in metadata_again_description:
            metadata_again_description = f"{metadata_again_description}\n\n00:00:00 Single Track\n\n#Music #Playlist"
        metadata_again_localizations = {
            language: {
                "title": metadata_again["youtube_title"],
                "description": metadata_again_description,
            }
            for language in SUPPORTED_YOUTUBE_LANGUAGES
        }
        approve_again_response = client.post(
            f"/api/playlists/{workspace_id}/metadata/approve",
            json={
                "actor": "test-suite",
                "note": "metadata approved again",
                "title": metadata_again["youtube_title"],
                "description": metadata_again_description,
                "tags": ",".join(metadata_again["youtube_tags"]),
                "default_language": metadata_again.get("youtube_default_language") or "ko",
                "localizations": metadata_again_localizations,
            },
        )
        assert approve_again_response.status_code == 200
        second_video_path = approve_again_response.json()["output_video_path"]
        assert second_video_path.endswith(".mp4")
        assert os.path.exists(second_video_path)

        reupload_response = client.post(
            f"/api/playlists/{workspace_id}/approve-publish",
            json={
                "actor": "test-suite",
                "note": "re-upload test",
                "force_under_target": True,
                "youtube_channel_id": "UC456",
                "allow_reupload": True,
            },
        )
        assert reupload_response.status_code == 200
        assert reupload_response.json()["workflow_state"] == "publish_queued"
        assert drain_background_jobs(client) == 1

        reloaded_response = client.get("/api/playlists/workspaces")
        reuploaded = next(item for item in reloaded_response.json() if item["id"] == workspace_id)
        assert reuploaded["workflow_state"] == "uploaded"
        assert reuploaded["youtube_video_id"] == "yt-auto-456"
        assert reuploaded["output_video_path"] is None
        assert not os.path.exists(second_video_path)
        assert upload_channel_ids[-1] == "UC456"
    finally:
        clear_isolated_client_env()


def test_publish_retry_adopts_recent_existing_youtube_upload(tmp_path) -> None:
    try:
        client = create_isolated_client(tmp_path)
        services = client.app.state.services

        def fake_build_audio(tracks, output_path):
            output_path.write_bytes(b"fake-mp3")
            return output_path

        def fake_build_video(audio_path, cover_image_path, output_path, **_kwargs):
            output_path.write_bytes(b"fake-mp4")
            return output_path

        services.playlist_builder.build_audio = fake_build_audio
        services.playlist_builder.build_video = fake_build_video
        services.youtube.get_status = lambda: {"configured": True, "authenticated": True, "ready": True}
        services.youtube.upload_playlist_video = lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("retry should adopt the existing upload instead of uploading again")
        )

        adopted_calls = []

        def fake_find_recent_upload_by_title(**kwargs):
            adopted_calls.append(kwargs)
            return {
                "video_id": "yt-adopted-123",
                "title": kwargs["title"],
                "published_at": "2026-05-21T00:00:00Z",
                "channel_id": kwargs["channel_id"],
                "channel_title": "Soft Hour Radio",
                "privacy_status": "private",
                "duration": "PT1M",
                "publish_at": "2026-05-22T00:00:00Z",
            }

        services.youtube.find_recent_upload_by_title = fake_find_recent_upload_by_title

        workspace_response = client.post(
            "/api/playlists/workspaces",
            json={
                "title": "Adopt Retry Workspace",
                "target_duration_seconds": 60,
                "description": "Existing YouTube upload should be adopted after interrupted retry.",
            },
        )
        workspace_id = workspace_response.json()["id"]
        local_audio = tmp_path / "single.mp3"
        local_audio.write_bytes(b"fake source")
        track_response = client.post(
            "/api/tracks",
            json={
                "title": "Single Track",
                "prompt": "minimal electronic",
                "duration_seconds": 60,
                "audio_path": str(local_audio),
                "metadata": {"source": "test"},
            },
        )
        approve_response = client.post(
            f"/api/tracks/{track_response.json()['id']}/decisions",
            json={
                "decision": "approve",
                "source": "human",
                "actor": "test-suite",
                "playlist_id": workspace_id,
            },
        )
        assert approve_response.status_code == 200
        render_workspace_audio(client, workspace_id)
        prepare_release_for_final_publish(client, workspace_id)

        with SessionLocal() as db:
            db.add(
                Job(
                    type=JobType.upload_youtube,
                    status=JobStatus.failed,
                    playlist_id=workspace_id,
                    error_text="Background YouTube upload was interrupted before completion. Retry publish.",
                    result_json={"interrupted_worker_resolution": "failed_requires_retry"},
                    finished_at=datetime.now(timezone.utc),
                )
            )
            db.commit()

        publish_response = client.post(
            f"/api/playlists/{workspace_id}/approve-publish",
            json={
                "actor": "test-suite",
                "note": "adopt interrupted upload",
                "youtube_channel_id": "UC_SOFT",
            },
        )
        assert publish_response.status_code == 200
        assert drain_background_jobs(client) == 1
        assert adopted_calls

        workspaces_response = client.get("/api/playlists/workspaces")
        published = next(item for item in workspaces_response.json() if item["id"] == workspace_id)
        assert published["workflow_state"] == "uploaded"
        assert published["youtube_video_id"] == "yt-adopted-123"
        assert published["output_video_path"] is None
        with SessionLocal() as db:
            playlist = db.get(Playlist, workspace_id)
            assert playlist.metadata_json["youtube_response"]["adopted_existing_upload"] is True
            assert playlist.metadata_json["youtube_channel_id"] == "UC_SOFT"
    finally:
        clear_isolated_client_env()


def test_single_track_video_mode_uses_uploaded_loop_in_video_stage(tmp_path) -> None:
    try:
        client = create_isolated_client(tmp_path)
        services = client.app.state.services

        def fake_build_audio(tracks, output_path):
            output_path.write_bytes(b"fake-mp3")
            return output_path

        def fake_build_looped_video(clip_path, audio_path, output_path, *, smooth_loop=True, **_kwargs):
            assert smooth_loop is True
            output_path.write_bytes(b"fake-looped-mp4")
            return output_path

        class UploadResult:
            video_id = "yt-single-123"
            response = {"id": "yt-single-123"}

        services.playlist_builder.build_audio = fake_build_audio
        services.playlist_builder.build_looped_video = fake_build_looped_video
        services.youtube.get_status = lambda: {"configured": True, "authenticated": True, "ready": True}
        services.youtube.upload_playlist_video = lambda *args, **kwargs: UploadResult()

        workspace_response = client.post(
            "/api/playlists/workspaces",
            json={
                "title": "Single Release Lane",
                "workspace_mode": "single_track_video",
                "auto_publish_when_ready": True,
                "description": "One-track cinematic upload lane.",
                "cover_prompt": "Chrome skyline and midnight rain.",
                "dreamina_prompt": "A seamless neon rain visualizer loop with slow camera drift.",
            },
        )
        assert workspace_response.status_code == 201
        workspace = workspace_response.json()
        assert workspace["workspace_mode"] == "single_track_video"
        assert workspace["auto_publish_when_ready"] is True

        local_audio = tmp_path / "single-release.mp3"
        local_audio.write_bytes(b"fake source")
        track_response = client.post(
            "/api/tracks",
            json={
                "title": "Neon Solo",
                "prompt": "night drive synth lead with warm bass and glossy pads",
                "duration_seconds": 180,
                "audio_path": str(local_audio),
                "metadata": {"source": "test", "tags": "synthwave, neon, night drive"},
            },
        )
        track_id = track_response.json()["id"]

        approve_response = client.post(
            f"/api/tracks/{track_id}/decisions",
            json={
                "decision": "approve",
                "source": "human",
                "actor": "test-suite",
                "playlist_id": workspace["id"],
            },
        )
        assert approve_response.status_code == 200

        assert drain_background_jobs(client) == 0
        workspaces_response = client.get("/api/playlists/workspaces")
        audio_ready = next(item for item in workspaces_response.json() if item["id"] == workspace["id"])
        assert audio_ready["workflow_state"] == "audio_ready"
        assert audio_ready["output_audio_path"] == str(local_audio)

        prepare_release_for_final_publish(client, workspace["id"], use_still_fallback=False)

        publish_response = client.post(
            f"/api/playlists/{workspace['id']}/approve-publish",
            json={
                "actor": "test-suite",
                "note": "single ready",
            },
        )
        assert publish_response.status_code == 200
        assert drain_background_jobs(client) == 1

        playlists_response = client.get("/api/playlists")
        playlist = next(item for item in playlists_response.json() if item["id"] == workspace["id"])
        assert playlist["youtube_video_id"] == "yt-single-123"
        assert playlist["output_video_path"] is None
        assert playlist["metadata_json"]["youtube_title"].startswith("Neon Solo")
        assert playlist["metadata_json"]["loop_video_source"] == "manual-upload"
        assert "dreamina_job_id" not in playlist["metadata_json"]
    finally:
        clear_isolated_client_env()


def test_youtube_status_ignores_invalid_token_file(tmp_path) -> None:
    try:
        client = create_isolated_client(tmp_path)
        secrets_path = tmp_path / "client_secrets.json"
        secrets_path.write_text(
            '{"installed":{"client_id":"test","project_id":"demo","auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://oauth2.googleapis.com/token","client_secret":"secret","redirect_uris":["http://localhost"]}}',
            encoding="utf-8",
        )
        token_path = client.app.state.settings.youtube_token_path
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text("not-json", encoding="utf-8")
        client.app.state.settings.youtube_client_secrets_path = str(secrets_path)

        response = client.get("/api/youtube/status")

        assert response.status_code == 200
        payload = response.json()
        assert payload["configured"] is True
        assert payload["authenticated"] is False
        assert payload["ready"] is False
        assert payload["redirect_uri"].endswith("/api/youtube/oauth/callback")
        assert "could not be read" in payload["error"]
    finally:
        clear_isolated_client_env()


def test_youtube_status_browser_request_gets_human_page(tmp_path) -> None:
    try:
        client = create_isolated_client(tmp_path)
        services = client.app.state.services
        services.youtube.get_status = lambda: {
            "configured": True,
            "authenticated": True,
            "ready": True,
            "channels": [{"id": "UC_SOFT", "title": "Soft Hour Radio"}],
        }

        browser_response = client.get("/api/youtube/status", headers={"accept": "text/html"})
        assert browser_response.status_code == 200
        assert "text/html" in browser_response.headers["content-type"]
        assert "YouTube API Status" in browser_response.text
        assert "Soft Hour Radio" in browser_response.text
        assert "not by opening it in the browser" in browser_response.text

        api_response = client.get("/api/youtube/status", headers={"accept": "application/json"})
        assert api_response.status_code == 200
        assert api_response.headers["content-type"].startswith("application/json")
        assert api_response.json()["channels"][0]["title"] == "Soft Hour Radio"
    finally:
        clear_isolated_client_env()


def test_youtube_thumbnail_upload_is_compressed_under_api_limit(tmp_path) -> None:
    source = tmp_path / "large-cover.png"
    image = Image.frombytes("RGB", (1920, 1080), os.urandom(1920 * 1080 * 3))
    image.save(source, "PNG")
    assert source.stat().st_size > YOUTUBE_THUMBNAIL_MAX_BYTES

    service = YouTubeService(Settings(storage_root=tmp_path / "storage"))

    prepared = service._prepare_thumbnail_upload(str(source))

    assert prepared.suffix == ".jpg"
    assert prepared.stat().st_size <= YOUTUBE_THUMBNAIL_MAX_BYTES


def test_youtube_upload_includes_localized_metadata_in_insert(tmp_path, monkeypatch) -> None:
    video_path = tmp_path / "release.mp4"
    video_path.write_bytes(b"fake video")
    captured = {}

    class FakeInsertRequest:
        def next_chunk(self):
            return None, {"id": "yt-localized"}

    class FakeVideos:
        def insert(self, *, part, body, media_body):
            captured["part"] = part
            captured["body"] = body
            captured["media_body"] = media_body
            return FakeInsertRequest()

    class FakeYouTube:
        def videos(self):
            return FakeVideos()

    monkeypatch.setattr(youtube_service_module, "build", lambda *args, **kwargs: FakeYouTube())
    monkeypatch.setattr(youtube_service_module, "MediaFileUpload", lambda *args, **kwargs: {"args": args, "kwargs": kwargs})

    service = YouTubeService(Settings(storage_root=tmp_path / "storage"))
    service._load_credentials = lambda youtube_channel_id=None: object()

    result = service.upload_playlist_video(
        SimpleNamespace(output_video_path=str(video_path)),
        title="한국어 제목",
        description="한국어 설명",
        tags=["Jpop"],
        localizations={
            "ko": {"title": "한국어 제목", "description": "한국어 설명"},
            "ja": {"title": "日本語タイトル", "description": "日本語の説明"},
            "en": {"title": "English Title", "description": "English description"},
            "es": {"title": "Titulo en espanol", "description": "Descripcion en espanol"},
        },
        default_language="ko",
    )

    assert result.video_id == "yt-localized"
    assert captured["part"] == "snippet,status,localizations"
    assert captured["body"]["snippet"]["defaultLanguage"] == "ko"
    assert captured["body"]["snippet"]["defaultAudioLanguage"] == "ja"
    assert captured["body"]["status"]["privacyStatus"] == "private"
    assert captured["body"]["status"]["containsSyntheticMedia"] is False
    assert captured["body"]["status"]["selfDeclaredMadeForKids"] is False
    assert captured["body"]["localizations"] == {
        "ja": {"title": "日本語タイトル", "description": "日本語の説明"},
        "en": {"title": "English Title", "description": "English description"},
        "es": {"title": "Titulo en espanol", "description": "Descripcion en espanol"},
    }


def test_youtube_upload_can_schedule_public_release(tmp_path, monkeypatch) -> None:
    video_path = tmp_path / "release.mp4"
    video_path.write_bytes(b"fake video")
    captured = {}

    class FakeInsertRequest:
        def next_chunk(self):
            return None, {
                "id": "yt-scheduled",
                "status": {
                    "privacyStatus": "private",
                    "publishAt": "2026-05-12T22:00:00Z",
                },
            }

    class FakeVideos:
        def insert(self, *, part, body, media_body):
            captured["part"] = part
            captured["body"] = body
            captured["media_body"] = media_body
            return FakeInsertRequest()

    class FakeYouTube:
        def videos(self):
            return FakeVideos()

    monkeypatch.setattr(youtube_service_module, "build", lambda *args, **kwargs: FakeYouTube())
    monkeypatch.setattr(youtube_service_module, "MediaFileUpload", lambda *args, **kwargs: {"args": args, "kwargs": kwargs})

    service = YouTubeService(Settings(storage_root=tmp_path / "storage", youtube_privacy_status="public"))
    service._load_credentials = lambda youtube_channel_id=None: object()

    result = service.upload_playlist_video(
        SimpleNamespace(output_video_path=str(video_path)),
        title="Scheduled Release",
        description="Scheduled description",
        tags=["Music"],
        scheduled_publish_at=datetime(2026, 5, 12, 22, 0, tzinfo=timezone.utc),
    )

    assert result.video_id == "yt-scheduled"
    assert captured["body"]["status"]["privacyStatus"] == "private"
    assert captured["body"]["status"]["publishAt"] == "2026-05-12T22:00:00Z"
    assert result.response["scheduled_publish_at"] == "2026-05-12T22:00:00+00:00"


def test_youtube_service_replaces_caption_track(tmp_path, monkeypatch) -> None:
    caption_path = tmp_path / "lyrics.srt"
    caption_path.write_text("1\n00:00:01,000 --> 00:00:02,000\nHello\n", encoding="utf-8")
    captured = {"deleted": [], "insert": None}

    class FakeRequest:
        def __init__(self, payload):
            self.payload = payload

        def execute(self):
            return self.payload

    class FakeCaptions:
        def list(self, *, part, videoId):
            captured["list"] = {"part": part, "videoId": videoId}
            return FakeRequest(
                {
                    "items": [
                        {"id": "old-caption", "snippet": {"language": "en", "name": "Lyrics"}},
                        {"id": "other-caption", "snippet": {"language": "ko", "name": "Lyrics"}},
                    ]
                }
            )

        def list_next(self, _request, _response):
            return None

        def delete(self, *, id):
            captured["deleted"].append(id)
            return FakeRequest({})

        def insert(self, *, part, body, media_body):
            captured["insert"] = {"part": part, "body": body, "media_body": media_body}
            return FakeRequest({"id": "new-caption", "snippet": {"language": "en", "name": "Lyrics"}})

    class FakeYouTube:
        def captions(self):
            return FakeCaptions()

    monkeypatch.setattr(youtube_service_module, "build", lambda *args, **kwargs: FakeYouTube())
    monkeypatch.setattr(youtube_service_module, "MediaFileUpload", lambda *args, **kwargs: {"args": args, "kwargs": kwargs})

    service = YouTubeService(Settings(storage_root=tmp_path / "storage"))
    service._load_credentials = lambda youtube_channel_id=None: object()

    result = service.replace_video_caption_track(
        video_id="yt-caption-test",
        language="en",
        caption_path=caption_path,
        youtube_channel_id="UC123",
    )

    assert result["id"] == "new-caption"
    assert captured["deleted"] == ["old-caption"]
    assert captured["insert"]["body"]["snippet"] == {
        "videoId": "yt-caption-test",
        "language": "en",
        "name": "Lyrics",
        "isDraft": False,
    }
    assert captured["insert"]["media_body"]["kwargs"]["mimetype"] == "application/x-subrip"


def test_next_youtube_scheduled_publish_at_skips_occupied_daily_slots_per_channel(tmp_path) -> None:
    try:
        client = create_isolated_client(tmp_path)
        services = client.app.state.services
        services.settings.youtube_schedule_public_enabled = True
        services.settings.youtube_schedule_timezone = "Asia/Seoul"
        services.settings.youtube_schedule_hour = 7
        services.settings.youtube_schedule_minute = 0
        services.settings.youtube_schedule_min_lead_minutes = 30

        with SessionLocal() as db:
            db.add(
                Playlist(
                    title="Scheduled 1",
                    metadata_json={
                        "youtube_channel_id": "UC-A",
                        "youtube_channel_title": "Channel A",
                        "youtube_scheduled_publish_at": "2026-05-11T22:00:00+00:00",
                    },
                )
            )
            db.add(
                Playlist(
                    title="Scheduled 2",
                    metadata_json={
                        "youtube_channel_id": "UC-A",
                        "youtube_channel_title": "Channel A",
                        "youtube_response": {
                            "status": {"publishAt": "2026-05-12T22:00:00Z"},
                        },
                    },
                )
            )
            db.add(
                Playlist(
                    title="Other Channel Scheduled",
                    metadata_json={
                        "youtube_channel_id": "UC-B",
                        "youtube_channel_title": "Channel B",
                        "youtube_scheduled_publish_at": "2026-05-13T22:00:00+00:00",
                    },
                )
            )
            db.commit()

            scheduled = next_youtube_scheduled_publish_at(
                db,
                services,
                youtube_channel_id="UC-A",
                youtube_channel_title="Channel A",
                now=datetime(2026, 5, 11, 20, 0, tzinfo=timezone.utc),
            )
            other_channel_scheduled = next_youtube_scheduled_publish_at(
                db,
                services,
                youtube_channel_id="UC-B",
                youtube_channel_title="Channel B",
                now=datetime(2026, 5, 11, 20, 0, tzinfo=timezone.utc),
            )
            two_day_interval_scheduled = next_youtube_scheduled_publish_at(
                db,
                services,
                youtube_channel_id="UC-A",
                youtube_channel_title="Channel A",
                now=datetime(2026, 5, 11, 20, 0, tzinfo=timezone.utc),
                schedule_interval_days=2,
            )

        assert scheduled == datetime(2026, 5, 13, 22, 0, tzinfo=timezone.utc)
        assert other_channel_scheduled == datetime(2026, 5, 11, 22, 0, tzinfo=timezone.utc)
        assert two_day_interval_scheduled == datetime(2026, 5, 14, 22, 0, tzinfo=timezone.utc)
    finally:
        clear_isolated_client_env()


def test_next_youtube_scheduled_publish_at_allows_distinct_daily_slots(tmp_path) -> None:
    try:
        client = create_isolated_client(tmp_path)
        services = client.app.state.services
        services.settings.youtube_schedule_public_enabled = True
        services.settings.youtube_schedule_timezone = "Asia/Seoul"
        services.settings.youtube_schedule_min_lead_minutes = 30

        with SessionLocal() as db:
            db.add(
                Playlist(
                    title="Old Testament Slot",
                    metadata_json={
                        "youtube_channel_id": "UC-OLD",
                        "youtube_channel_title": "The Old Verse",
                        "youtube_scheduled_publish_at": "2026-05-11T22:00:00+00:00",
                    },
                )
            )
            db.commit()

            old_slot = next_youtube_scheduled_publish_at(
                db,
                services,
                youtube_channel_id="UC-OLD",
                youtube_channel_title="The Old Verse",
                now=datetime(2026, 5, 11, 20, 0, tzinfo=timezone.utc),
                schedule_hour=7,
                schedule_minute=0,
                schedule_scope="slot",
            )
            new_slot = next_youtube_scheduled_publish_at(
                db,
                services,
                youtube_channel_id="UC-OLD",
                youtube_channel_title="The Old Verse",
                now=datetime(2026, 5, 11, 20, 0, tzinfo=timezone.utc),
                schedule_hour=16,
                schedule_minute=0,
                schedule_scope="slot",
            )

        assert old_slot == datetime(2026, 5, 12, 22, 0, tzinfo=timezone.utc)
        assert new_slot == datetime(2026, 5, 12, 7, 0, tzinfo=timezone.utc)
    finally:
        clear_isolated_client_env()


def test_scripture_schedule_options_and_playlist_titles() -> None:
    old_playlist = Playlist(
        title="[playlist] Genesis Scripture Jazz",
        metadata_json={
            "target_youtube_channel_title": "The Old Verse",
            "scripture_channel_title": "The Old Verse",
            "scripture_passage_range": "Genesis 1:1-5",
            "scripture_music_lane": "scripture jazz",
        },
    )
    new_playlist = Playlist(
        title="[playlist] Matthew Gospel Soul Songs",
        metadata_json={
            "target_youtube_channel_title": "The Old Verse",
            "scripture_channel_title": "New Testament",
            "scripture_passage_range": "Matthew 1:18-25",
            "scripture_music_lane": "gospel R&B soul",
        },
    )
    buddhist_playlist = Playlist(
        title="[playlist] 마음을 다스리는 불경 힙합",
        metadata_json={"target_youtube_channel_title": "The New Verse"},
    )

    assert youtube_schedule_options_for_playlist(old_playlist) == {
        "schedule_hour": 7,
        "schedule_minute": 0,
        "schedule_scope": "slot",
        "schedule_label": "old_testament",
    }
    assert youtube_schedule_options_for_playlist(new_playlist) == {
        "schedule_hour": 16,
        "schedule_minute": 0,
        "schedule_scope": "slot",
        "schedule_label": "new_testament",
    }
    assert youtube_schedule_options_for_playlist(buddhist_playlist) == {
        "schedule_hour": 7,
        "schedule_minute": 0,
        "schedule_interval_days": 1,
        "schedule_scope": "date",
        "schedule_label": "buddhist_scripture",
    }
    assert scripture_youtube_playlist_titles(old_playlist.metadata_json, title=old_playlist.title) == [
        "Old Testament Songs",
        "Scripture Jazz Songs",
    ]
    assert scripture_youtube_playlist_titles(new_playlist.metadata_json, title=new_playlist.title) == [
        "New Testament Songs",
        "Scripture R&B Songs",
    ]


def test_youtube_upload_audio_language_inference_marks_pop_vocals(tmp_path) -> None:
    service = YouTubeService(Settings(storage_root=tmp_path / "storage"))

    assert (
        service._infer_default_audio_language(
            title="Night Park J-POP",
            description="Japanese vocals with city pop energy.",
            tags=["J-pop", "Japanese vocals"],
        )
        == "ja"
    )


def test_youtube_upload_audio_language_inference_skips_instrumental_bgm(tmp_path) -> None:
    service = YouTubeService(Settings(storage_root=tmp_path / "storage"))

    assert (
        service._infer_default_audio_language(
            title="Beach Walk BGM",
            description="No-vocal instrumental music for walking.",
            tags=["J-pop inspired BGM", "Instrumental"],
        )
        is None
    )


def test_youtube_upload_retries_without_default_audio_language_if_api_rejects(
    tmp_path,
    monkeypatch,
) -> None:
    video_path = tmp_path / "release.mp4"
    video_path.write_bytes(b"fake video")
    captured_bodies = []

    class FakeResponse:
        status = 400
        reason = "Bad Request"

    class FakeInsertRequest:
        def __init__(self, reject_default_audio_language: bool) -> None:
            self.reject_default_audio_language = reject_default_audio_language

        def next_chunk(self):
            if self.reject_default_audio_language:
                raise youtube_service_module.HttpError(
                    FakeResponse(),
                    b'{"error":{"message":"defaultAudioLanguage is invalid"}}',
                )
            return None, {"id": "yt-retried"}

    class FakeVideos:
        def insert(self, *, part, body, media_body):
            del part, media_body
            captured_bodies.append(json.loads(json.dumps(body)))
            return FakeInsertRequest("defaultAudioLanguage" in body["snippet"])

    class FakeYouTube:
        def videos(self):
            return FakeVideos()

    monkeypatch.setattr(youtube_service_module, "build", lambda *args, **kwargs: FakeYouTube())
    monkeypatch.setattr(
        youtube_service_module,
        "MediaFileUpload",
        lambda *args, **kwargs: {"args": args, "kwargs": kwargs},
    )

    service = YouTubeService(Settings(storage_root=tmp_path / "storage"))
    service._load_credentials = lambda youtube_channel_id=None: object()

    result = service.upload_playlist_video(
        SimpleNamespace(output_video_path=str(video_path)),
        title="Tokyo Night J-POP",
        description="Japanese vocals over neon drums.",
        tags=["J-pop"],
    )

    assert result.video_id == "yt-retried"
    assert "defaultAudioLanguage" in captured_bodies[0]["snippet"]
    assert "defaultAudioLanguage" not in captured_bodies[1]["snippet"]
    assert "default_audio_language" not in result.response


def test_youtube_channel_selection_updates_active_channel(tmp_path) -> None:
    try:
        client = create_isolated_client(tmp_path)
        service = client.app.state.services.youtube
        secrets_path = tmp_path / "client-secrets.json"
        secrets_path.write_text("{}", encoding="utf-8")
        client.app.state.settings.youtube_client_secrets_path = str(secrets_path)
        token_path = service.channel_tokens_dir / "UC123.json"
        token_path.parent.mkdir(parents=True, exist_ok=True)
        credentials = Credentials(
            token="token",
            refresh_token="refresh",
            token_uri="https://oauth2.googleapis.com/token",
            client_id="client-id",
            client_secret="client-secret",
            scopes=["https://www.googleapis.com/auth/youtube.upload"],
        )
        token_path.write_text(credentials.to_json(), encoding="utf-8")
        service._upsert_channel(
            {"id": "UC123", "title": "Main Music", "thumbnail_url": None},
            token_path=token_path,
        )

        response = client.post("/api/youtube/channels/select", json={"channel_id": "UC123"})

        assert response.status_code == 200
        payload = response.json()
        assert payload["selected_channel_id"] == "UC123"
        assert payload["selected_channel_title"] == "Main Music"
        assert payload["ready"] is True
        assert "client_secrets_path" not in payload
        assert "token_path" not in payload
        assert "token_path" not in payload["channels"][0]
    finally:
        clear_isolated_client_env()


def test_youtube_connect_redirects_to_authorization_url(tmp_path) -> None:
    try:
        client = create_isolated_client(tmp_path)
        client.app.state.services.youtube.build_authorization_url = lambda: {
            "authorization_url": "https://accounts.google.com/o/oauth2/auth?state=test",
            "state": "test",
            "redirect_uri": "https://example.com/api/youtube/oauth/callback",
        }

        response = client.get("/api/youtube/connect", follow_redirects=False)

        assert response.status_code == 307
        assert response.headers["location"] == "https://accounts.google.com/o/oauth2/auth?state=test"
    finally:
        clear_isolated_client_env()


def test_youtube_connect_can_remember_playlist_context(tmp_path) -> None:
    try:
        client = create_isolated_client(tmp_path)
        calls = {}

        def fake_build_authorization_url(playlist_id: str | None = None) -> dict:
            calls["playlist_id"] = playlist_id
            return {
                "authorization_url": "https://accounts.google.com/o/oauth2/auth?state=test",
                "state": "test",
                "redirect_uri": "https://example.com/api/youtube/oauth/callback",
                "playlist_id": playlist_id,
            }

        client.app.state.services.youtube.build_authorization_url = fake_build_authorization_url

        response = client.get("/api/youtube/connect?playlist_id=playlist-123", follow_redirects=False)

        assert response.status_code == 307
        assert response.headers["location"] == "https://accounts.google.com/o/oauth2/auth?state=test"
        assert calls["playlist_id"] == "playlist-123"
    finally:
        clear_isolated_client_env()


def test_youtube_oauth_callback_stores_token_then_returns_to_ui(tmp_path) -> None:
    try:
        client = create_isolated_client(tmp_path)
        calls = {}

        def fake_exchange_web_code(code: str, state: str | None = None) -> dict:
            calls["code"] = code
            calls["state"] = state
            return {"ready": True}

        client.app.state.services.youtube.exchange_web_code = fake_exchange_web_code

        response = client.get("/api/youtube/oauth/callback?code=test-code&state=test-state", follow_redirects=False)

        assert response.status_code == 307
        assert response.headers["location"] == "/?youtube=connected"
        assert calls["code"] == "test-code"
        assert calls["state"] == "test-state"
    finally:
        clear_isolated_client_env()


def test_youtube_oauth_callback_resumes_linked_publish(tmp_path, monkeypatch) -> None:
    try:
        client = create_isolated_client(tmp_path)
        calls = {}

        def fake_exchange_web_code(code: str, state: str | None = None) -> dict:
            calls["code"] = code
            calls["state"] = state
            return {"ready": True, "playlist_id": "playlist-123", "channel_id": "UC123"}

        def fake_resume_youtube_publish_after_auth(
            db,
            services,
            *,
            playlist_id: str,
            actor: str = "youtube-oauth",
            youtube_channel_id: str | None = None,
        ):
            calls["playlist_id"] = playlist_id
            calls["actor"] = actor
            calls["youtube_channel_id"] = youtube_channel_id

        client.app.state.services.youtube.exchange_web_code = fake_exchange_web_code
        monkeypatch.setattr(
            "app.routes.youtube.resume_youtube_publish_after_auth",
            fake_resume_youtube_publish_after_auth,
        )

        response = client.get("/api/youtube/oauth/callback?code=test-code&state=test-state", follow_redirects=False)

        assert response.status_code == 307
        assert response.headers["location"] == "/?youtube=connected"
        assert calls["code"] == "test-code"
        assert calls["state"] == "test-state"
        assert calls["playlist_id"] == "playlist-123"
        assert calls["actor"] == "youtube-oauth"
        assert calls["youtube_channel_id"] == "UC123"
    finally:
        clear_isolated_client_env()
