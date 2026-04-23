from fastapi.testclient import TestClient

from app.main import create_app


def test_track_create_and_agent_review() -> None:
    client = TestClient(create_app())

    create_response = client.post(
        "/api/tracks",
        json={
            "title": "Candidate 01",
            "prompt": "lofi rain piano, soft vinyl crackle",
            "duration_seconds": 180,
            "metadata": {"model_score": 0.9},
        },
    )
    assert create_response.status_code == 201
    track = create_response.json()
    assert track["title"] == "Candidate 01"

    review_response = client.post(f"/api/tracks/{track['id']}/agent-review")
    assert review_response.status_code == 200
    reviewed_track = review_response.json()
    assert reviewed_track["status"] == "approved"
    assert reviewed_track["approvals"][-1]["source"] == "agent"
