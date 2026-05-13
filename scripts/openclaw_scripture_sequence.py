#!/usr/bin/env python3
"""Track sequential scripture progress for OpenClaw Bible channels.

This file intentionally keeps the Bible-order decision human/OpenClaw-facing:
the tool records and guards passage ranges, while the channel concept docs
decide the next coherent passage block.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_STATE_PATH = Path("storage/openclaw-scripture-sequence.json")

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
        "title": "The New Verse",
        "default_next_start": "Matthew 1:1",
        "default_first_range": "Matthew 1:1-17",
    },
    "new": {
        "key": "the_new_verse",
        "title": "The New Verse",
        "default_next_start": "Matthew 1:1",
        "default_first_range": "Matthew 1:1-17",
    },
    "the_new_verse": {
        "key": "the_new_verse",
        "title": "The New Verse",
        "default_next_start": "Matthew 1:1",
        "default_first_range": "Matthew 1:1-17",
    },
}

ACTIVE_STATUSES = {"in_progress", "scheduled", "published"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def state_path() -> Path:
    raw = os.environ.get("AIMP_SCRIPTURE_SEQUENCE_PATH", "").strip()
    return Path(raw) if raw else DEFAULT_STATE_PATH


def channel_info(channel: str) -> dict[str, str]:
    normalized = channel.strip().lower().replace("-", "_")
    info = CHANNELS.get(normalized)
    if not info:
        valid = ", ".join(sorted({value["title"] for value in CHANNELS.values()}))
        raise SystemExit(f"Unknown scripture channel '{channel}'. Use one of: {valid}")
    return info


def empty_channel_state(info: dict[str, str]) -> dict[str, Any]:
    return {
        "channel": info["title"],
        "last_completed": None,
        "next_start": info["default_next_start"],
        "default_first_range": info["default_first_range"],
        "entries": [],
    }


def empty_state() -> dict[str, Any]:
    old_info = channel_info("The Old Verse")
    new_info = channel_info("The New Verse")
    return {
        "version": 1,
        "updated_at": utc_now(),
        "the_old_verse": empty_channel_state(old_info),
        "the_new_verse": empty_channel_state(new_info),
    }


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return empty_state()
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    base = empty_state()
    for key in ("the_old_verse", "the_new_verse"):
        existing = data.get(key) if isinstance(data, dict) else None
        if isinstance(existing, dict):
            base[key].update(existing)
            entries = existing.get("entries")
            base[key]["entries"] = entries if isinstance(entries, list) else []
    base["version"] = int(data.get("version", 1)) if isinstance(data, dict) else 1
    base["updated_at"] = data.get("updated_at") or base["updated_at"] if isinstance(data, dict) else base["updated_at"]
    return base


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = utc_now()
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(state, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(tmp_name, path)
    finally:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass


def find_entry(channel_state: dict[str, Any], passage: str) -> dict[str, Any] | None:
    normalized = passage.strip().lower()
    for entry in channel_state.get("entries", []):
        if str(entry.get("passage_range", "")).strip().lower() == normalized:
            return entry
    return None


def reject_duplicate(channel_state: dict[str, Any], passage: str) -> None:
    existing = find_entry(channel_state, passage)
    if not existing:
        return
    status = str(existing.get("status", "")).strip().lower()
    if status in ACTIVE_STATUSES:
        raise SystemExit(
            "Refusing duplicate scripture passage. "
            f"{channel_state.get('channel')} already has {passage} as {status} "
            f"(release_id={existing.get('release_id') or 'unknown'}, "
            f"youtube_video_id={existing.get('youtube_video_id') or 'none'})."
        )


def print_json(data: Any) -> None:
    json.dump(data, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


def command_status(args: argparse.Namespace) -> None:
    path = state_path()
    state = load_state(path)
    if args.init:
        save_state(path, state)
    print_json({"path": str(path), "state": state})


def command_start(args: argparse.Namespace) -> None:
    path = state_path()
    state = load_state(path)
    info = channel_info(args.channel)
    channel_state = state[info["key"]]
    passage = args.passage.strip()
    if not args.force:
        reject_duplicate(channel_state, passage)
    entry = find_entry(channel_state, passage)
    if not entry:
        entry = {"passage_range": passage}
        channel_state.setdefault("entries", []).append(entry)
    entry.update(
        {
            "status": "in_progress",
            "release_id": args.release_id or entry.get("release_id"),
            "youtube_video_id": args.youtube_video_id or entry.get("youtube_video_id"),
            "title": args.title or entry.get("title"),
            "notes": args.notes or entry.get("notes"),
            "started_at": entry.get("started_at") or utc_now(),
            "updated_at": utc_now(),
        }
    )
    save_state(path, state)
    print_json({"path": str(path), "channel": info["title"], "entry": entry})


def command_complete(args: argparse.Namespace) -> None:
    path = state_path()
    state = load_state(path)
    info = channel_info(args.channel)
    channel_state = state[info["key"]]
    passage = args.passage.strip()
    entry = find_entry(channel_state, passage)
    if not entry:
        entry = {"passage_range": passage, "started_at": args.started_at or utc_now()}
        channel_state.setdefault("entries", []).append(entry)
    entry.update(
        {
            "status": args.status,
            "release_id": args.release_id or entry.get("release_id"),
            "youtube_video_id": args.youtube_video_id or entry.get("youtube_video_id"),
            "title": args.title or entry.get("title"),
            "notes": args.notes or entry.get("notes"),
            "published_at": args.published_at or utc_now(),
            "updated_at": utc_now(),
        }
    )
    channel_state["last_completed"] = passage
    if args.next_start:
        channel_state["next_start"] = args.next_start.strip()
    save_state(path, state)
    print_json({"path": str(path), "channel": info["title"], "entry": entry})


def command_fail(args: argparse.Namespace) -> None:
    path = state_path()
    state = load_state(path)
    info = channel_info(args.channel)
    channel_state = state[info["key"]]
    passage = args.passage.strip()
    entry = find_entry(channel_state, passage)
    if not entry:
        entry = {"passage_range": passage}
        channel_state.setdefault("entries", []).append(entry)
    entry.update(
        {
            "status": "failed",
            "release_id": args.release_id or entry.get("release_id"),
            "title": args.title or entry.get("title"),
            "failure_reason": args.reason,
            "updated_at": utc_now(),
        }
    )
    save_state(path, state)
    print_json({"path": str(path), "channel": info["title"], "entry": entry})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Track OpenClaw Bible-channel scripture passage progress.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    status_parser = subparsers.add_parser("status", help="Print scripture sequence state.")
    status_parser.add_argument("--init", action="store_true", help="Create the state file if it does not exist.")
    status_parser.set_defaults(func=command_status)

    start_parser = subparsers.add_parser("start", help="Mark a passage range as in progress before generation.")
    start_parser.add_argument("--channel", required=True, help="The Old Verse or The New Verse.")
    start_parser.add_argument("--passage", required=True, help="Passage range, e.g. Genesis 1:1-5.")
    start_parser.add_argument("--release-id", default="")
    start_parser.add_argument("--youtube-video-id", default="")
    start_parser.add_argument("--title", default="")
    start_parser.add_argument("--notes", default="")
    start_parser.add_argument("--force", action="store_true", help="Allow rewriting an existing active entry.")
    start_parser.set_defaults(func=command_start)

    complete_parser = subparsers.add_parser("complete", help="Mark a passage range as scheduled/published.")
    complete_parser.add_argument("--channel", required=True, help="The Old Verse or The New Verse.")
    complete_parser.add_argument("--passage", required=True, help="Passage range, e.g. Matthew 1:1-17.")
    complete_parser.add_argument("--release-id", default="")
    complete_parser.add_argument("--youtube-video-id", default="")
    complete_parser.add_argument("--title", default="")
    complete_parser.add_argument("--notes", default="")
    complete_parser.add_argument("--published-at", default="")
    complete_parser.add_argument("--started-at", default="")
    complete_parser.add_argument("--next-start", default="", help="Next canonical passage start, e.g. Genesis 1:6.")
    complete_parser.add_argument("--status", choices=["scheduled", "published"], default="published")
    complete_parser.set_defaults(func=command_complete)

    fail_parser = subparsers.add_parser("fail", help="Mark a passage range as failed so it can be retried.")
    fail_parser.add_argument("--channel", required=True, help="The Old Verse or The New Verse.")
    fail_parser.add_argument("--passage", required=True, help="Passage range.")
    fail_parser.add_argument("--release-id", default="")
    fail_parser.add_argument("--title", default="")
    fail_parser.add_argument("--reason", required=True)
    fail_parser.set_defaults(func=command_fail)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
