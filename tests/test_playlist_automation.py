import json
import os
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import SessionLocal
from app.main import create_app
from app.models.track import Track


def create_isolated_client(tmp_path) -> TestClient:
    os.environ["AIMP_STORAGE_ROOT"] = str(tmp_path / "storage")
    os.environ["AIMP_DATABASE_URL"] = f"sqlite:///{tmp_path / 'app.db'}"
    os.environ["AIMP_WORKER_AUTOSTART"] = "false"
    get_settings.cache_clear()
    return TestClient(create_app())


def clear_isolated_client_env() -> None:
    os.environ.pop("AIMP_STORAGE_ROOT", None)
    os.environ.pop("AIMP_DATABASE_URL", None)
    os.environ.pop("AIMP_WORKER_AUTOSTART", None)
    get_settings.cache_clear()


def drain_background_jobs(client: TestClient, max_jobs: int = 10) -> int:
    processed = 0
    while client.app.state.services.worker.process_pending_once():
        processed += 1
        if processed >= max_jobs:
            raise AssertionError("Background worker exceeded expected job count.")
    return processed


def test_manual_upload_creates_track_and_stores_file(tmp_path) -> None:
    try:
        client = create_isolated_client(tmp_path)
        marker = uuid4().hex

        response = client.post(
            "/api/tracks/manual-upload",
            data={
                "title": f"Manual Upload {marker}",
                "prompt": "manual suno intake candidate",
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

        uploaded_response = client.post(
            f"/api/playlists/{playlist['id']}/mark-uploaded",
            json={
                "youtube_video_id": f"yt-{marker}",
                "actor": "test-suite",
                "note": "uploaded manually",
            },
        )
        assert uploaded_response.status_code == 200
        uploaded = uploaded_response.json()
        assert uploaded["status"] == "uploaded"
        assert uploaded["youtube_video_id"] == f"yt-{marker}"

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
        assert workspace["workflow_state"] == "pending_publish_approval"
        assert [track["id"] for track in workspace["tracks"]] == track_ids
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

        client.app.state.services.slack.update_review_message = fake_update_review_message

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
        assert interaction["replace_original"] is True
        assert interaction["track_status"] == "approved"
        assert interaction["assigned_workspace_id"] == workspace_id
        assert interaction["assignment_error"] is None
        assert "Approved" in str(interaction["blocks"])
        button_texts = [
            element["text"]["text"]
            for block in interaction["blocks"]
            if block["type"] == "actions"
            for element in block["elements"]
        ]
        assert "Approve" not in button_texts
        assert "Hold" not in button_texts
        assert "Reject" not in button_texts
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


def test_publish_approval_generates_cover_asset(tmp_path) -> None:
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
        assert drain_background_jobs(client) == 1

        publish_response = client.post(
            f"/api/playlists/{workspace_id}/approve-publish",
            json={
                "actor": "test-suite",
                "note": "ready to publish",
            },
        )
        assert publish_response.status_code == 200
        queued = publish_response.json()
        assert queued["publish_approved"] is True
        assert queued["workflow_state"] == "publish_queued"

        assert drain_background_jobs(client) == 1

        workspaces_response = client.get("/api/playlists/workspaces")
        published = next(item for item in workspaces_response.json() if item["id"] == workspace_id)
        assert published["workflow_state"] == "ready_for_youtube_auth"
        assert published["cover_image_path"].endswith(".png")
        assert published["output_video_path"].endswith(".mp4")
        assert os.path.exists(published["cover_image_path"])
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
        assert drain_background_jobs(client) == 1

        publish_response = client.post(
            f"/api/playlists/{workspace_id}/approve-publish",
            json={
                "actor": "test-suite",
            },
        )
        assert publish_response.status_code == 200
        queued = publish_response.json()
        assert queued["workflow_state"] == "publish_queued"

        assert drain_background_jobs(client) == 1

        workspaces_response = client.get("/api/playlists/workspaces")
        published = next(item for item in workspaces_response.json() if item["id"] == workspace_id)
        assert published["workflow_state"] == "video_build_failed"
        assert "ffmpeg missing" in published["note"]
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

        class UploadResult:
            video_id = "yt-auto-123"
            response = {"id": "yt-auto-123"}

        services.playlist_builder.build_audio = fake_build_audio
        services.playlist_builder.build_video = fake_build_video
        services.youtube.get_status = lambda: {"configured": True, "authenticated": True, "ready": True}
        services.youtube.upload_playlist_video = lambda *args, **kwargs: UploadResult()

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
        assert drain_background_jobs(client) == 1

        publish_response = client.post(
            f"/api/playlists/{workspace_id}/approve-publish",
            json={
                "actor": "test-suite",
                "note": "auto upload ready",
            },
        )
        assert publish_response.status_code == 200
        queued = publish_response.json()
        assert queued["workflow_state"] == "publish_queued"

        assert drain_background_jobs(client) == 1

        workspaces_response = client.get("/api/playlists/workspaces")
        published = next(item for item in workspaces_response.json() if item["id"] == workspace_id)
        assert published["workflow_state"] == "uploaded"
        assert published["youtube_video_id"] == "yt-auto-123"
        assert published["output_video_path"].endswith(".mp4")
    finally:
        clear_isolated_client_env()


def test_single_track_video_mode_auto_publishes_with_dreamina_loop(tmp_path) -> None:
    try:
        client = create_isolated_client(tmp_path)
        services = client.app.state.services

        def fake_build_audio(tracks, output_path):
            output_path.write_bytes(b"fake-mp3")
            return output_path

        def fake_build_looped_video(clip_path, audio_path, output_path):
            output_path.write_bytes(b"fake-looped-mp4")
            return output_path

        class DreaminaResult:
            job_id = "dreamina-job-1"
            provider_response = {"status": "completed"}
            video_url = "https://example.com/dreamina-loop.mp4"

        class UploadResult:
            video_id = "yt-single-123"
            response = {"id": "yt-single-123"}

        def fake_download_video(video_url, output_path):
            output_path.write_bytes(b"clip")
            return output_path

        services.playlist_builder.build_audio = fake_build_audio
        services.playlist_builder.build_looped_video = fake_build_looped_video
        services.dreamina.get_status = lambda: {"configured": True, "ready": True}
        services.dreamina.generate_loop_clip = lambda prompt: DreaminaResult()
        services.dreamina.download_video = fake_download_video
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

        assert drain_background_jobs(client) == 2

        workspaces_response = client.get("/api/playlists/workspaces")
        published = next(item for item in workspaces_response.json() if item["id"] == workspace["id"])
        assert published["workflow_state"] == "uploaded"
        assert published["youtube_video_id"] == "yt-single-123"
        assert published["output_video_path"].endswith(".mp4")

        playlists_response = client.get("/api/playlists")
        playlist = next(item for item in playlists_response.json() if item["id"] == workspace["id"])
        assert playlist["metadata_json"]["youtube_title"].startswith("Neon Solo")
        assert playlist["metadata_json"]["dreamina_job_id"] == "dreamina-job-1"
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
        assert "could not be read" in payload["error"]
    finally:
        clear_isolated_client_env()
