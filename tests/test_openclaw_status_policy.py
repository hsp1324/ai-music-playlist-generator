from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.routes.openclaw import openclaw_status


@pytest.mark.parametrize("enabled,target", [(True, 7200), (False, 0)])
def test_status_exposes_actual_backfill_policy_without_credentials(tmp_path, enabled, target):
    services = SimpleNamespace(settings=SimpleNamespace(
        storage_root=tmp_path,
        openclaw_shared_token="test-status-token",
        playlist_reuse_back_half_enabled=enabled,
        playlist_reuse_back_half_target_seconds=target,
        youtube_client_secret="must-not-be-exposed",
    ))

    result = openclaw_status(services=services, token="test-status-token")

    assert result["production_policy"] == {
        "playlist_reuse_back_half_enabled": enabled,
        "playlist_reuse_back_half_target_seconds": target,
    }
    assert set(result) == {"ok", "runtime", "lock", "production_policy"}
    assert "test-status-token" not in repr(result)
    assert "must-not-be-exposed" not in repr(result)


def test_status_still_requires_existing_openclaw_authentication(tmp_path):
    services = SimpleNamespace(settings=SimpleNamespace(
        storage_root=tmp_path, openclaw_shared_token="test-status-token",
    ))

    with pytest.raises(HTTPException) as exc:
        openclaw_status(services=services, token="wrong-token")

    assert exc.value.status_code == 403
