from __future__ import annotations

import json
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPTURE_SEQUENCE_FILE = "openclaw-scripture-sequence.json"

ACTIVE_STATUSES = {"in_progress", "scheduled", "published"}

CHANNELS = {
    "the old verse": {
        "key": "the_old_verse",
        "title": "The Old Verse",
        "default_next_start": "Genesis 1:1",
        "default_first_range": "Genesis 1:1-5",
    },
    "old": {
        "key": "the_old_verse",
        "title": "The Old Verse",
        "default_next_start": "Genesis 1:1",
        "default_first_range": "Genesis 1:1-5",
    },
    "the_old_verse": {
        "key": "the_old_verse",
        "title": "The Old Verse",
        "default_next_start": "Genesis 1:1",
        "default_first_range": "Genesis 1:1-5",
    },
    "the new verse": {
        "key": "the_new_verse",
        "title": "New Testament",
        "default_next_start": "Matthew 1:1",
        "default_first_range": "Matthew 1:1-17",
    },
    "new testament": {
        "key": "the_new_verse",
        "title": "New Testament",
        "default_next_start": "Matthew 1:1",
        "default_first_range": "Matthew 1:1-17",
    },
    "new": {
        "key": "the_new_verse",
        "title": "New Testament",
        "default_next_start": "Matthew 1:1",
        "default_first_range": "Matthew 1:1-17",
    },
    "new_testament": {
        "key": "the_new_verse",
        "title": "New Testament",
        "default_next_start": "Matthew 1:1",
        "default_first_range": "Matthew 1:1-17",
    },
    "the_new_verse": {
        "key": "the_new_verse",
        "title": "New Testament",
        "default_next_start": "Matthew 1:1",
        "default_first_range": "Matthew 1:1-17",
    },
}

SCRIPTURE_BLOCKS = {
    "the_old_verse": [
        {"next_start": "Genesis 1:1", "passage_range": "Genesis 1:1-5", "next_start_after_completion": "Genesis 1:6"},
        {"next_start": "Genesis 1:6", "passage_range": "Genesis 1:6-13", "next_start_after_completion": "Genesis 1:14"},
        {"next_start": "Genesis 1:14", "passage_range": "Genesis 1:14-25", "next_start_after_completion": "Genesis 1:26"},
        {"next_start": "Genesis 1:26", "passage_range": "Genesis 1:26-31", "next_start_after_completion": "Genesis 2:1"},
        {"next_start": "Genesis 2:1", "passage_range": "Genesis 2:1-3", "next_start_after_completion": "Genesis 2:4"},
        {"next_start": "Genesis 2:4", "passage_range": "Genesis 2:4-17", "next_start_after_completion": "Genesis 2:18"},
        {"next_start": "Genesis 2:18", "passage_range": "Genesis 2:18-25", "next_start_after_completion": "Genesis 3:1"},
        {"next_start": "Genesis 3:1", "passage_range": "Genesis 3:1-7", "next_start_after_completion": "Genesis 3:8"},
        {"next_start": "Genesis 3:8", "passage_range": "Genesis 3:8-13", "next_start_after_completion": "Genesis 3:14"},
        {"next_start": "Genesis 3:14", "passage_range": "Genesis 3:14-19", "next_start_after_completion": "Genesis 3:20"},
        {"next_start": "Genesis 3:20", "passage_range": "Genesis 3:20-24", "next_start_after_completion": "Genesis 4:1"},
        {"next_start": "Genesis 4:1", "passage_range": "Genesis 4:1-16", "next_start_after_completion": "Genesis 4:17"},
        {"next_start": "Genesis 4:17", "passage_range": "Genesis 4:17-26", "next_start_after_completion": "Genesis 5:1"},
        {"next_start": "Genesis 5:1", "passage_range": "Genesis 5:1-32", "next_start_after_completion": "Genesis 6:1"},
        {"next_start": "Genesis 6:1", "passage_range": "Genesis 6:1-8", "next_start_after_completion": "Genesis 6:9"},
        {"next_start": "Genesis 6:9", "passage_range": "Genesis 6:9-22", "next_start_after_completion": "Genesis 7:1"},
        {"next_start": "Genesis 7:1", "passage_range": "Genesis 7:1-24", "next_start_after_completion": "Genesis 8:1"},
        {"next_start": "Genesis 8:1", "passage_range": "Genesis 8:1-22", "next_start_after_completion": "Genesis 9:1"},
        {"next_start": "Genesis 9:1", "passage_range": "Genesis 9:1-17", "next_start_after_completion": "Genesis 9:18"},
        {"next_start": "Genesis 9:18", "passage_range": "Genesis 9:18-29", "next_start_after_completion": "Genesis 10:1"},
        {"next_start": "Genesis 10:1", "passage_range": "Genesis 10:1-32", "next_start_after_completion": "Genesis 11:1"},
        {"next_start": "Genesis 11:1", "passage_range": "Genesis 11:1-9", "next_start_after_completion": "Genesis 11:10"},
        {"next_start": "Genesis 11:10", "passage_range": "Genesis 11:10-32", "next_start_after_completion": "Genesis 12:1"},
        {"next_start": "Genesis 12:1", "passage_range": "Genesis 12:1-9", "next_start_after_completion": "Genesis 12:10"},
        {"next_start": "Genesis 12:10", "passage_range": "Genesis 12:10-20", "next_start_after_completion": "Genesis 13:1"},
        {"next_start": "Genesis 13:1", "passage_range": "Genesis 13:1-18", "next_start_after_completion": "Genesis 14:1"},
        {"next_start": "Genesis 14:1", "passage_range": "Genesis 14:1-16", "next_start_after_completion": "Genesis 14:17"},
        {"next_start": "Genesis 14:17", "passage_range": "Genesis 14:17-24", "next_start_after_completion": "Genesis 15:1"},
        {"next_start": "Genesis 15:1", "passage_range": "Genesis 15:1-21", "next_start_after_completion": "Genesis 16:1"},
        {"next_start": "Genesis 16:1", "passage_range": "Genesis 16:1-16", "next_start_after_completion": "Genesis 17:1"},
        {"next_start": "Genesis 17:1", "passage_range": "Genesis 17:1-27", "next_start_after_completion": "Genesis 18:1"},
        {"next_start": "Genesis 18:1", "passage_range": "Genesis 18:1-15", "next_start_after_completion": "Genesis 18:16"},
    ],
    "the_new_verse": [
        {"next_start": "Matthew 1:1", "passage_range": "Matthew 1:1-17", "next_start_after_completion": "Matthew 1:18"},
        {"next_start": "Matthew 1:18", "passage_range": "Matthew 1:18-25", "next_start_after_completion": "Matthew 2:1"},
        {"next_start": "Matthew 2:1", "passage_range": "Matthew 2:1-12", "next_start_after_completion": "Matthew 2:13"},
        {"next_start": "Matthew 2:13", "passage_range": "Matthew 2:13-23", "next_start_after_completion": "Matthew 3:1"},
        {"next_start": "Matthew 3:1", "passage_range": "Matthew 3:1-17", "next_start_after_completion": "Matthew 4:1"},
        {"next_start": "Matthew 4:1", "passage_range": "Matthew 4:1-11", "next_start_after_completion": "Matthew 4:12"},
        {"next_start": "Matthew 4:12", "passage_range": "Matthew 4:12-25", "next_start_after_completion": "Matthew 5:1"},
        {"next_start": "Matthew 5:1", "passage_range": "Matthew 5:1-12", "next_start_after_completion": "Matthew 5:13"},
        {"next_start": "Matthew 5:13", "passage_range": "Matthew 5:13-16", "next_start_after_completion": "Matthew 5:17"},
        {"next_start": "Matthew 5:17", "passage_range": "Matthew 5:17-20", "next_start_after_completion": "Matthew 5:21"},
        {"next_start": "Matthew 5:21", "passage_range": "Matthew 5:21-26", "next_start_after_completion": "Matthew 5:27"},
        {"next_start": "Matthew 5:27", "passage_range": "Matthew 5:27-30", "next_start_after_completion": "Matthew 5:31"},
        {"next_start": "Matthew 5:31", "passage_range": "Matthew 5:31-32", "next_start_after_completion": "Matthew 5:33"},
        {"next_start": "Matthew 5:33", "passage_range": "Matthew 5:33-37", "next_start_after_completion": "Matthew 5:38"},
        {"next_start": "Matthew 5:38", "passage_range": "Matthew 5:38-42", "next_start_after_completion": "Matthew 5:43"},
        {"next_start": "Matthew 5:43", "passage_range": "Matthew 5:43-48", "next_start_after_completion": "Matthew 6:1"},
        {"next_start": "Matthew 6:1", "passage_range": "Matthew 6:1-4", "next_start_after_completion": "Matthew 6:5"},
        {"next_start": "Matthew 6:5", "passage_range": "Matthew 6:5-15", "next_start_after_completion": "Matthew 6:16"},
        {"next_start": "Matthew 6:16", "passage_range": "Matthew 6:16-18", "next_start_after_completion": "Matthew 6:19"},
        {"next_start": "Matthew 6:19", "passage_range": "Matthew 6:19-24", "next_start_after_completion": "Matthew 6:25"},
        {"next_start": "Matthew 6:25", "passage_range": "Matthew 6:25-34", "next_start_after_completion": "Matthew 7:1"},
        {"next_start": "Matthew 7:1", "passage_range": "Matthew 7:1-6", "next_start_after_completion": "Matthew 7:7"},
        {"next_start": "Matthew 7:7", "passage_range": "Matthew 7:7-12", "next_start_after_completion": "Matthew 7:13"},
        {"next_start": "Matthew 7:13", "passage_range": "Matthew 7:13-14", "next_start_after_completion": "Matthew 7:15"},
        {"next_start": "Matthew 7:15", "passage_range": "Matthew 7:15-23", "next_start_after_completion": "Matthew 7:24"},
        {"next_start": "Matthew 7:24", "passage_range": "Matthew 7:24-29", "next_start_after_completion": "Matthew 8:1"},
        {"next_start": "Matthew 8:1", "passage_range": "Matthew 8:1-4", "next_start_after_completion": "Matthew 8:5"},
        {"next_start": "Matthew 8:5", "passage_range": "Matthew 8:5-13", "next_start_after_completion": "Matthew 8:14"},
        {"next_start": "Matthew 8:14", "passage_range": "Matthew 8:14-17", "next_start_after_completion": "Matthew 8:18"},
        {"next_start": "Matthew 8:18", "passage_range": "Matthew 8:18-22", "next_start_after_completion": "Matthew 8:23"},
        {"next_start": "Matthew 8:23", "passage_range": "Matthew 8:23-27", "next_start_after_completion": "Matthew 8:28"},
        {"next_start": "Matthew 8:28", "passage_range": "Matthew 8:28-34", "next_start_after_completion": "Matthew 9:1"},
        {"next_start": "Matthew 9:1", "passage_range": "Matthew 9:1-8", "next_start_after_completion": "Matthew 9:9"},
        {"next_start": "Matthew 9:9", "passage_range": "Matthew 9:9-13", "next_start_after_completion": "Matthew 9:14"},
        {"next_start": "Matthew 9:14", "passage_range": "Matthew 9:14-17", "next_start_after_completion": "Matthew 9:18"},
        {"next_start": "Matthew 9:18", "passage_range": "Matthew 9:18-26", "next_start_after_completion": "Matthew 9:27"},
        {"next_start": "Matthew 9:27", "passage_range": "Matthew 9:27-34", "next_start_after_completion": "Matthew 9:35"},
        {"next_start": "Matthew 9:35", "passage_range": "Matthew 9:35-38", "next_start_after_completion": "Matthew 10:1"},
        {"next_start": "Matthew 10:1", "passage_range": "Matthew 10:1-15", "next_start_after_completion": "Matthew 10:16"},
        {"next_start": "Matthew 10:16", "passage_range": "Matthew 10:16-25", "next_start_after_completion": "Matthew 10:26"},
        {"next_start": "Matthew 10:26", "passage_range": "Matthew 10:26-33", "next_start_after_completion": "Matthew 10:34"},
        {"next_start": "Matthew 10:34", "passage_range": "Matthew 10:34-39", "next_start_after_completion": "Matthew 10:40"},
        {"next_start": "Matthew 10:40", "passage_range": "Matthew 10:40-42", "next_start_after_completion": "Matthew 11:1"},
    ],
}

_SCRIPTURE_LOCK = threading.Lock()


class ScriptureSequenceError(ValueError):
    def __init__(self, message: str, *, code: str = "scripture_sequence_error") -> None:
        super().__init__(message)
        self.code = code


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def scripture_sequence_path(storage_root: Path) -> Path:
    return Path(storage_root) / SCRIPTURE_SEQUENCE_FILE


def channel_info(channel: str) -> dict[str, str]:
    normalized = str(channel or "").strip().lower().replace("-", "_")
    info = CHANNELS.get(normalized)
    if not info:
        valid = ", ".join(sorted({value["title"] for value in CHANNELS.values()}))
        raise ScriptureSequenceError(f"Unknown scripture channel '{channel}'. Use one of: {valid}", code="unknown_channel")
    return info


def _empty_channel_state(info: dict[str, str]) -> dict[str, Any]:
    return {
        "channel": info["title"],
        "last_completed": None,
        "next_start": info["default_next_start"],
        "default_first_range": info["default_first_range"],
        "entries": [],
    }


def _empty_state() -> dict[str, Any]:
    return {
        "version": 1,
        "updated_at": _utcnow(),
        "the_old_verse": _empty_channel_state(channel_info("The Old Verse")),
        "the_new_verse": _empty_channel_state(channel_info("New Testament")),
    }


def _load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return _empty_state()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _empty_state()
    base = _empty_state()
    if not isinstance(data, dict):
        return base
    for key in ("the_old_verse", "the_new_verse"):
        existing = data.get(key)
        if isinstance(existing, dict):
            base[key].update(existing)
            entries = existing.get("entries")
            base[key]["entries"] = entries if isinstance(entries, list) else []
    base["version"] = int(data.get("version", 1) or 1)
    base["updated_at"] = data.get("updated_at") or base["updated_at"]
    return base


def _save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = _utcnow()
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with open(fd, "w", encoding="utf-8") as handle:
            json.dump(state, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        Path(tmp_name).replace(path)
    finally:
        Path(tmp_name).unlink(missing_ok=True)


def _normalize_passage(value: str) -> str:
    return " ".join(str(value or "").strip().split()).lower()


def _find_entry(channel_state: dict[str, Any], passage_range: str) -> dict[str, Any] | None:
    normalized = _normalize_passage(passage_range)
    for entry in channel_state.get("entries") or []:
        if isinstance(entry, dict) and _normalize_passage(str(entry.get("passage_range") or "")) == normalized:
            return entry
    return None


def _suggested_block(channel_key: str, next_start: str) -> dict[str, str]:
    normalized_next_start = _normalize_passage(next_start)
    for block in SCRIPTURE_BLOCKS.get(channel_key, []):
        if _normalize_passage(block["next_start"]) == normalized_next_start:
            return dict(block)
    raise ScriptureSequenceError(
        f"No app-managed scripture block is configured after {next_start}. Add the next block before continuing.",
        code="next_block_missing",
    )


def _next_start_after_passage(channel_key: str, passage_range: str) -> str | None:
    normalized_passage = _normalize_passage(passage_range)
    for block in SCRIPTURE_BLOCKS.get(channel_key, []):
        if _normalize_passage(block["passage_range"]) == normalized_passage:
            return block["next_start_after_completion"]
    return None


def _state_with_suggestions(state: dict[str, Any]) -> dict[str, Any]:
    suggestions = {}
    for key in ("the_old_verse", "the_new_verse"):
        channel_state = dict(state.get(key) or {})
        try:
            suggestions[key] = _suggested_block(key, str(channel_state.get("next_start") or ""))
        except ScriptureSequenceError as exc:
            suggestions[key] = {"error": str(exc), "code": exc.code}
    return {"path": "", "state": state, "next_suggestions": suggestions}


def scripture_sequence_status(storage_root: Path) -> dict[str, Any]:
    path = scripture_sequence_path(storage_root)
    with _SCRIPTURE_LOCK:
        state = _load_state(path)
        if not path.exists():
            _save_state(path, state)
    payload = _state_with_suggestions(state)
    payload["path"] = str(path)
    return payload


def reserve_scripture_passage(
    storage_root: Path,
    *,
    channel_title: str,
    release_id: str = "",
    title: str = "",
    notes: str = "",
    passage_range: str = "",
) -> dict[str, Any]:
    info = channel_info(channel_title)
    path = scripture_sequence_path(storage_root)
    now = _utcnow()
    normalized_release_id = str(release_id or "").strip()
    with _SCRIPTURE_LOCK:
        state = _load_state(path)
        channel_state = state[info["key"]]
        if passage_range.strip():
            passage = passage_range.strip()
            next_start_after_completion = _next_start_after_passage(info["key"], passage)
        else:
            block = _suggested_block(info["key"], str(channel_state.get("next_start") or info["default_next_start"]))
            passage = block["passage_range"]
            next_start_after_completion = block["next_start_after_completion"]

        existing = _find_entry(channel_state, passage)
        if existing and str(existing.get("status") or "").strip().lower() in ACTIVE_STATUSES:
            if normalized_release_id and str(existing.get("release_id") or "").strip() == normalized_release_id:
                return {"path": str(path), "channel": info["title"], "entry": existing, "idempotent": True}
            raise ScriptureSequenceError(
                f"{info['title']} already has {passage} as {existing.get('status')} "
                f"(release_id={existing.get('release_id') or 'unknown'}, "
                f"youtube_video_id={existing.get('youtube_video_id') or 'none'}).",
                code="passage_already_active",
            )

        entry = existing or {"passage_range": passage}
        if existing is None:
            channel_state.setdefault("entries", []).append(entry)
        entry.update(
            {
                "status": "in_progress",
                "release_id": normalized_release_id or entry.get("release_id"),
                "youtube_video_id": entry.get("youtube_video_id"),
                "title": str(title or "").strip() or entry.get("title"),
                "notes": str(notes or "").strip() or entry.get("notes"),
                "started_at": entry.get("started_at") or now,
                "updated_at": now,
            }
        )
        if next_start_after_completion:
            entry["next_start_after_completion"] = next_start_after_completion
        _save_state(path, state)
    return {"path": str(path), "channel": info["title"], "entry": entry, "idempotent": False}


def complete_scripture_passage(
    storage_root: Path,
    *,
    channel_title: str,
    passage_range: str,
    status: str = "scheduled",
    release_id: str = "",
    youtube_video_id: str = "",
    title: str = "",
    notes: str = "",
    next_start: str = "",
) -> dict[str, Any]:
    normalized_status = str(status or "scheduled").strip().lower()
    if normalized_status not in {"scheduled", "published"}:
        raise ScriptureSequenceError("Scripture completion status must be scheduled or published.", code="invalid_status")
    info = channel_info(channel_title)
    passage = str(passage_range or "").strip()
    if not passage:
        raise ScriptureSequenceError("passage_range is required.", code="passage_required")

    path = scripture_sequence_path(storage_root)
    now = _utcnow()
    with _SCRIPTURE_LOCK:
        state = _load_state(path)
        channel_state = state[info["key"]]
        entry = _find_entry(channel_state, passage)
        if entry is None:
            entry = {"passage_range": passage, "started_at": now}
            channel_state.setdefault("entries", []).append(entry)
        entry.update(
            {
                "status": normalized_status,
                "release_id": str(release_id or "").strip() or entry.get("release_id"),
                "youtube_video_id": str(youtube_video_id or "").strip() or entry.get("youtube_video_id"),
                "title": str(title or "").strip() or entry.get("title"),
                "notes": str(notes or "").strip() or entry.get("notes"),
                "published_at": entry.get("published_at") or now,
                "updated_at": now,
            }
        )
        channel_state["last_completed"] = passage
        channel_state["next_start"] = (
            str(next_start or "").strip()
            or str(entry.get("next_start_after_completion") or "").strip()
            or _next_start_after_passage(info["key"], passage)
            or str(channel_state.get("next_start") or "").strip()
        )
        _save_state(path, state)
    return {"path": str(path), "channel": info["title"], "entry": entry, "next_start": channel_state["next_start"]}


def fail_scripture_passage(
    storage_root: Path,
    *,
    channel_title: str,
    passage_range: str,
    release_id: str = "",
    title: str = "",
    reason: str = "",
) -> dict[str, Any]:
    info = channel_info(channel_title)
    passage = str(passage_range or "").strip()
    if not passage:
        raise ScriptureSequenceError("passage_range is required.", code="passage_required")

    path = scripture_sequence_path(storage_root)
    now = _utcnow()
    with _SCRIPTURE_LOCK:
        state = _load_state(path)
        channel_state = state[info["key"]]
        entry = _find_entry(channel_state, passage)
        if entry is None:
            entry = {"passage_range": passage, "started_at": now}
            channel_state.setdefault("entries", []).append(entry)
        entry.update(
            {
                "status": "failed",
                "release_id": str(release_id or "").strip() or entry.get("release_id"),
                "title": str(title or "").strip() or entry.get("title"),
                "failure_reason": str(reason or "").strip(),
                "updated_at": now,
            }
        )
        _save_state(path, state)
    return {"path": str(path), "channel": info["title"], "entry": entry}
