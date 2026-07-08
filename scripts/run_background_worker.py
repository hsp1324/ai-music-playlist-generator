from __future__ import annotations

import signal
import time

from app.config import get_settings
from app.db import init_db
from app.services import build_service_registry


def main() -> None:
    settings = get_settings()
    settings.worker_autostart = True
    settings.ensure_storage_dirs()
    init_db()

    services = build_service_registry(settings)
    stop_requested = False

    def request_stop(signum: int, frame: object | None) -> None:
        nonlocal stop_requested
        stop_requested = True
        services.worker.stop()

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    services.worker.start()
    while not stop_requested:
        time.sleep(1.0)


if __name__ == "__main__":
    main()
