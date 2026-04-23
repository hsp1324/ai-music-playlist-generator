from fastapi.testclient import TestClient

from app.main import create_app


def test_root_serves_ui_console() -> None:
    client = TestClient(create_app())

    response = client.get("/")

    assert response.status_code == 200
    assert "AI Music Workspace" in response.text
    assert "/assets/app.js" in response.text
