from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _registry_path(storage_root: Path) -> Path:
    return storage_root / "render-workers.json"


def _empty_registry() -> dict[str, Any]:
    return {"workers": {}}


def read_render_worker_registry(storage_root: Path) -> dict[str, Any]:
    path = _registry_path(storage_root)
    if not path.exists():
        return _empty_registry()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return _empty_registry()
    if not isinstance(data, dict):
        return _empty_registry()
    workers = data.get("workers")
    if not isinstance(workers, dict):
        data["workers"] = {}
    return data


def write_render_worker_registry(storage_root: Path, registry: dict[str, Any]) -> None:
    path = _registry_path(storage_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        tmp_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        tmp_path.replace(path)
    finally:
        tmp_path.unlink(missing_ok=True)


def record_render_worker_seen(
    storage_root: Path,
    *,
    worker_id: str,
    hostname: str = "",
    capabilities: dict[str, Any] | None = None,
    claimed_at: str | None = None,
) -> dict[str, Any]:
    registry = read_render_worker_registry(storage_root)
    workers = registry.setdefault("workers", {})
    now = _utcnow_iso()
    entry = dict(workers.get(worker_id) or {})
    if not entry:
        entry["worker_id"] = worker_id
        entry["first_seen_at"] = now
        entry["nickname"] = ""
    entry["worker_id"] = worker_id
    entry["hostname"] = hostname or entry.get("hostname") or ""
    entry["capabilities"] = capabilities or entry.get("capabilities") or {}
    entry["last_seen_at"] = now
    if claimed_at:
        entry["last_claimed_at"] = claimed_at
    workers[worker_id] = entry
    write_render_worker_registry(storage_root, registry)
    return entry


def set_render_worker_nickname(
    storage_root: Path,
    *,
    worker_id: str,
    nickname: str,
    actor: str = "web-ui",
) -> dict[str, Any]:
    registry = read_render_worker_registry(storage_root)
    workers = registry.setdefault("workers", {})
    now = _utcnow_iso()
    entry = dict(workers.get(worker_id) or {})
    if not entry:
        entry["worker_id"] = worker_id
        entry["first_seen_at"] = now
        entry["hostname"] = ""
        entry["capabilities"] = {}
    entry["worker_id"] = worker_id
    entry["nickname"] = nickname.strip()
    entry["nickname_updated_at"] = now
    entry["nickname_updated_by"] = actor or "web-ui"
    entry["last_seen_at"] = now
    workers[worker_id] = entry
    write_render_worker_registry(storage_root, registry)
    return entry


def render_worker_display_name(worker: dict[str, Any] | None) -> str:
    if not worker:
        return ""
    return str(worker.get("nickname") or worker.get("hostname") or worker.get("worker_id") or "").strip()
