#!/usr/bin/env python3
"""Local, durable one-time recovery ledger. Does not browse, generate, or upload."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from urllib.parse import urlparse
from uuid import UUID


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def source_id(value: str) -> str:
    return str(UUID(value))


def read_state(path: Path) -> dict | None:
    if not path.exists():
        return None
    state = json.loads(path.read_text())
    if state.get("schema_version") != 1 or not isinstance(state.get("tracks"), dict):
        raise ValueError("Invalid recovery state; preserve it and recover the existing ledger, do not reset.")
    return state


def save_state(path: Path, state: dict) -> None:
    state["updated_at"] = now()
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(state, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def locked(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_suffix(path.suffix + ".lock").open("a") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield


def summary(state: dict | None) -> dict:
    if state is None:
        return {"phase": "uninitialized", "action": "needs_initial_inventory", "scan_library": False}
    counts = {key: 0 for key in ("pending", "blocked", "saved", "ingested", "excluded")}
    for track in state["tracks"].values():
        counts[track["status"]] += 1
    complete = state["phase"] == "complete"
    cancelled = state["phase"] == "cancelled"
    return {
        "batch_id": state["batch_id"],
        "phase": state["phase"],
        "action": "fresh_production" if complete or cancelled else (
            "resume_inventory" if state["phase"] == "discovering" else "recover_known_tracks"
        ),
        "scan_library": state["phase"] == "discovering",
        "workspace": state["workspace"] if state["phase"] == "discovering" else None,
        "cutoff": state["cutoff"] if state["phase"] == "discovering" else None,
        "cursor": state.get("cursor") if state["phase"] == "discovering" else None,
        "counts": counts,
        "completed_at": state.get("completed_at"),
        **({"cancelled_at": state.get("cancelled_at"), "cancellation_reason": state.get("cancellation_reason")} if cancelled else {}),
    }


def fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_audio(path: Path, expected_seconds: float) -> dict:
    if not math.isfinite(expected_seconds) or expected_seconds <= 0:
        raise ValueError("Expected full-song duration must be a positive finite number.")
    path = path.resolve(strict=True)
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError("Audio file is missing or empty.")
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type",
         "-of", "json", str(path)],
        check=True, capture_output=True, text=True, timeout=30,
    )
    data = json.loads(probe.stdout)
    duration = float(data["format"]["duration"])
    if not any(s.get("codec_type") == "audio" for s in data.get("streams", [])):
        raise ValueError("File has no audio stream.")
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("Audio duration is invalid.")
    if abs(duration - expected_seconds) > max(2.0, expected_seconds * 0.01):
        raise ValueError("Downloaded duration does not match the original full song; do not accept a crop/stem.")
    subprocess.run(
        ["ffmpeg", "-v", "error", "-xerror", "-nostdin", "-i", str(path), "-map", "0:a:0", "-f", "null", "-"],
        check=True, capture_output=True, text=True, timeout=180,
    )
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": fingerprint(path),
            "duration_seconds": duration, "full_decode": True, "verified_at": now()}


def add_inventory(state: dict, manifest: Path) -> None:
    if state["phase"] != "discovering":
        raise ValueError("Inventory is sealed; do not rescan or add later generations to this batch.")
    rows = json.loads(manifest.read_text())
    if not isinstance(rows, list):
        raise ValueError("Inventory page must be a JSON list.")
    for row in rows:
        sid = source_id(row["source_id"])
        url = urlparse(row["source_url"])
        if url.scheme != "https" or url.hostname not in {"suno.com", "www.suno.com"} or url.path.rstrip("/") != f"/song/{sid}":
            raise ValueError("source_url must identify the original song on suno.com.")
        if not str(row.get("model_evidence", "")).strip():
            raise ValueError("Record original model evidence, not merely a title/date/export label.")
        model = row.get("model")
        eligible = model == "v6"
        if not eligible and not str(row.get("exclusion_reason", "")).strip():
            raise ValueError("Non-v6/unknown entries need an explicit exclusion reason.")
        existing = state["tracks"].get(sid)
        if existing:
            if existing["model"] != model:
                raise ValueError("Conflicting model evidence; preserve the entry and resolve the provenance.")
            continue
        state["tracks"][sid] = {
            **row, "source_id": sid, "status": "pending" if eligible else "excluded",
            "inventoried_at": now(),
        }


def mutate(state: dict, args: argparse.Namespace) -> None:
    if state["phase"] in {"complete", "cancelled"}:
        raise ValueError("Recovery is terminal. Do not reopen historical discovery; use the current generation manifest.")
    if args.command == "cancel":
        state.update(phase="cancelled", cancelled_at=now(), cancellation_reason=args.reason)
        return
    if args.command == "inventory":
        add_inventory(state, args.manifest)
        state["cursor"] = args.cursor
    elif args.command == "seal":
        if state["phase"] != "discovering":
            raise ValueError("Inventory is already sealed.")
        state.update(phase="recovering", inventory_evidence=args.evidence, inventory_sealed_at=now())
    elif args.command == "complete":
        if state["phase"] != "recovering":
            raise ValueError("Finish the bounded inventory and seal it before completion.")
        for track in state["tracks"].values():
            if track["status"] == "excluded":
                continue
            if track["status"] != "ingested":
                raise ValueError("Unresolved downloads/ingestion remain. A deferred song is not recovered.")
            audio = track["audio"]
            if fingerprint(Path(audio["path"])) != audio["sha256"]:
                raise ValueError("Verified file changed or vanished before completion.")
        state.update(phase="complete", completed_at=now())
    else:
        track = state["tracks"][source_id(args.source_id)]
        if track["status"] == "excluded":
            raise ValueError("Non-v6/unknown source is excluded, not eligible for recovery.")
        if args.command == "record":
            if track["status"] in {"saved", "ingested"}:
                raise ValueError("Already saved; resume app ingestion rather than downloading a duplicate.")
            audio = verify_audio(args.audio, args.expected_seconds)
            track.update(status="saved", audio=audio, studio_url=args.studio_url)
            track.pop("last_error", None)
        elif args.command == "accept":
            if track["status"] != "saved":
                raise ValueError("Verify the complete local file before recording app ingestion.")
            receipt = json.loads(args.receipt.read_text())
            app_track = receipt.get("track", {})
            if receipt.get("ok") is not True or not app_track.get("id") or app_track.get("status") != "approved":
                raise ValueError("Receipt must confirm ok=true and a real approved app track ID.")
            if any(t.get("app_track_id") == app_track["id"] for t in state["tracks"].values()):
                raise ValueError("That app track ID already belongs to another original source; inspect the receipt.")
            if fingerprint(Path(track["audio"]["path"])) != track["audio"]["sha256"]:
                raise ValueError("Audio changed after verification.")
            track.update(status="ingested", app_track_id=app_track["id"],
                         receipt_path=str(args.receipt.resolve()), ingested_at=now())
        elif args.command == "block":
            if track["status"] == "ingested":
                raise ValueError("Already ingested; do not reopen it.")
            track.update(status="blocked", last_error=args.reason)


def nonempty(value: str) -> str:
    if not value.strip():
        raise argparse.ArgumentTypeError("Evidence/reason must not be blank.")
    return value


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--state", type=Path, default=Path("storage/suno-studio-recovery.json"))
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser("status")
    pending = commands.add_parser("pending")
    pending.add_argument("--limit", type=int, choices=range(1, 21), default=5)
    init = commands.add_parser("init")
    init.add_argument("--batch-id", required=True, type=nonempty)
    init.add_argument("--workspace", required=True, type=nonempty)
    init.add_argument("--cutoff", required=True, type=nonempty,
                      help="Original source ID/time boundary frozen at the first inventory, with UI evidence.")
    inventory = commands.add_parser("inventory")
    inventory.add_argument("--manifest", type=Path, required=True)
    inventory.add_argument("--cursor", required=True, type=nonempty)
    seal = commands.add_parser("seal")
    seal.add_argument("--evidence", required=True, type=nonempty)
    record = commands.add_parser("record")
    record.add_argument("--source-id", required=True)
    record.add_argument("--audio", type=Path, required=True)
    record.add_argument("--expected-seconds", type=float, required=True)
    record.add_argument("--studio-url", required=True, type=nonempty)
    accept = commands.add_parser("accept")
    accept.add_argument("--source-id", required=True)
    accept.add_argument("--receipt", type=Path, required=True)
    block = commands.add_parser("block")
    block.add_argument("--source-id", required=True)
    block.add_argument("--reason", required=True, type=nonempty)
    commands.add_parser("complete")
    cancel = commands.add_parser("cancel", help="Explicit human cancellation; preserve unresolved evidence without claiming recovery completed.")
    cancel.add_argument("--reason", required=True, type=nonempty)
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command in {"status", "pending"}:
            state = read_state(args.state)
            output = summary(state)
            if args.command == "pending":
                output["tracks"] = [] if state is None or state["phase"] in {"complete", "cancelled"} else [
                    {k: t.get(k) for k in (
                        "source_id", "source_url", "title", "channel_title", "release_id", "status",
                        "model_evidence", "expected_seconds", "lyrics_file", "style_file", "exclude_style_file",
                        "audio", "last_error",
                    )}
                    for t in state["tracks"].values() if t["status"] not in {"ingested", "excluded"}
                ][:args.limit]
        else:
            with locked(args.state):
                state = read_state(args.state)
                if args.command == "init":
                    if state is not None:
                        if state["batch_id"] != args.batch_id or state["workspace"] != args.workspace or state["cutoff"] != args.cutoff:
                            raise ValueError("Existing batch cannot be reset or replaced.")
                    else:
                        state = {"schema_version": 1, "batch_id": args.batch_id, "workspace": args.workspace,
                                 "cutoff": args.cutoff, "phase": "discovering", "tracks": {}, "created_at": now()}
                        save_state(args.state, state)
                else:
                    if state is None:
                        raise ValueError("No recovery batch exists; restore prior state or initialize the one-time inventory.")
                    mutate(state, args)
                    save_state(args.state, state)
                output = summary(state)
        print(json.dumps(output, ensure_ascii=False))
        return 0
    except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
