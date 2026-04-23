import json

from app.config import Settings
from app.services.suno_session_service import SunoBrowserSessionService


def test_suno_session_status_needs_login_without_state(tmp_path) -> None:
    settings = Settings(storage_root=tmp_path)
    settings.ensure_storage_dirs()
    service = SunoBrowserSessionService(settings)

    status = service.get_status()

    assert status.needs_login is True
    assert status.state == "needs_login"


def test_suno_session_status_ready_with_recent_auth_cookie(tmp_path) -> None:
    settings = Settings(storage_root=tmp_path)
    settings.ensure_storage_dirs()
    settings.suno_browser_state_path.write_text(
        json.dumps(
            {
                "saved_at": "2026-04-20T12:00:00+00:00",
                "cookies": [
                    {
                        "name": "__client",
                        "domain": ".suno.com",
                        "value": "abc",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    service = SunoBrowserSessionService(settings)

    status = service.get_status()

    assert status.authenticated is True
    assert status.needs_login is False
    assert status.state == "ready"
