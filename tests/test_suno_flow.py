from fastapi.testclient import TestClient

from app.main import create_app


def test_manual_suno_webhook_creates_track_and_holds_without_score() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/suno/webhook",
        json={
            "provider_job_id": "provider-1",
            "source_track_id": "suno-track-1",
            "title": "Webhook Candidate",
            "prompt": "ambient piano, soft rain, sparse strings",
            "duration_seconds": 210,
            "audio_path": "storage/tracks/webhook-candidate.mp3",
            "metadata": {},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["tracks_created"] == 1

    track_response = client.get(f"/api/tracks/{body['track_ids'][0]}")
    assert track_response.status_code == 200
    track = track_response.json()
    assert track["title"] == "Webhook Candidate"


def test_sunoapi_complete_callback_creates_two_tracks_idempotently() -> None:
    client = TestClient(create_app())
    client.app.state.services.suno.download_audio_to_storage = lambda source_url, source_track_id=None: (
        f"storage/tracks/{source_track_id}.mp3"
    )

    payload = {
        "code": 200,
        "msg": "All generated successfully.",
        "data": {
            "callbackType": "complete",
            "task_id": "task-sunoapi-1",
            "data": [
                {
                    "id": "music-1",
                    "audio_url": "https://cdn.example.com/music-1.mp3",
                    "stream_audio_url": "https://cdn.example.com/music-1-stream",
                    "image_url": "https://cdn.example.com/music-1.jpg",
                    "prompt": "[Verse] Neon skyline",
                    "model_name": "chirp-v3-5",
                    "title": "Night Drive A",
                    "tags": "synthwave, neon",
                    "createTime": "2026-04-20 00:00:00",
                    "duration": 201.2,
                },
                {
                    "id": "music-2",
                    "audio_url": "https://cdn.example.com/music-2.mp3",
                    "stream_audio_url": "https://cdn.example.com/music-2-stream",
                    "image_url": "https://cdn.example.com/music-2.jpg",
                    "prompt": "[Verse] Neon skyline",
                    "model_name": "chirp-v3-5",
                    "title": "Night Drive B",
                    "tags": "synthwave, neon",
                    "createTime": "2026-04-20 00:00:00",
                    "duration": 198.6,
                },
            ],
        },
    }

    first_response = client.post("/api/suno/webhook", json=payload)
    assert first_response.status_code == 200
    assert first_response.json()["tracks_created"] == 2

    second_response = client.post("/api/suno/webhook", json=payload)
    assert second_response.status_code == 200
    assert second_response.json()["tracks_created"] == 2

    tracks_response = client.get("/api/tracks")
    assert tracks_response.status_code == 200
    tracks = [track for track in tracks_response.json() if track["source_track_id"] in {"music-1", "music-2"}]
    assert len(tracks) == 2
    assert all(track["audio_path"].startswith("storage/tracks/") for track in tracks)


def test_sunoapi_progress_callback_only_acknowledges_without_creating_tracks() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/suno/webhook",
        json={
            "code": 200,
            "msg": "First track completed.",
            "data": {
                "callbackType": "first",
                "task_id": "task-sunoapi-progress",
                "data": [],
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["tracks_created"] == 0
    assert body["callback_type"] == "first"


def test_dispatch_review_in_agent_mode_approves_high_score() -> None:
    client = TestClient(create_app())
    client.app.state.settings.auto_approval_mode = "agent"

    create_response = client.post(
        "/api/tracks",
        json={
            "title": "Agent Candidate",
            "prompt": "driving synth bass, neon pads",
            "duration_seconds": 200,
            "metadata": {"model_score": 0.92},
        },
    )
    track_id = create_response.json()["id"]

    review_response = client.post(f"/api/tracks/{track_id}/dispatch-review")
    assert review_response.status_code == 200
    reviewed = review_response.json()
    assert reviewed["status"] == "approved"
