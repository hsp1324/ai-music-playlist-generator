import os

import pytest

from app.config import get_settings


@pytest.fixture(autouse=True)
def isolate_app_storage(tmp_path):
    original_env = {
        key: os.environ.get(key)
        for key in (
            "AIMP_STORAGE_ROOT",
            "AIMP_DATABASE_URL",
            "AIMP_WORKER_AUTOSTART",
        )
    }
    os.environ["AIMP_STORAGE_ROOT"] = str(tmp_path / "storage")
    os.environ["AIMP_DATABASE_URL"] = f"sqlite:///{tmp_path / 'app.db'}"
    os.environ["AIMP_WORKER_AUTOSTART"] = "false"
    get_settings.cache_clear()

    try:
        yield
    finally:
        for key, value in original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        get_settings.cache_clear()
