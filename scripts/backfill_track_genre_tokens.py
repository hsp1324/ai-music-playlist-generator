#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.db import SessionLocal
from app.models.track import Track
from app.utils.genre_tokens import (
    AI_GENRE_TOKEN_HASH_METADATA_KEY,
    AI_GENRE_TOKEN_VERSION,
    AI_GENRE_TOKEN_VERSION_METADATA_KEY,
    GENRE_PATTERNS,
    current_ai_genre_tokens,
    normalize_genre_tokens,
    track_genre_token_source_hash,
    update_track_ai_genre_token_metadata,
    update_track_genre_token_metadata,
)


def db_path_from_url(database_url: str) -> Path | None:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        return None
    return Path(database_url[len(prefix) :])


def backup_database() -> Path | None:
    settings = get_settings()
    db_path = db_path_from_url(settings.database_url)
    if not db_path or not db_path.exists():
        return None
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    backup_path = db_path.with_name(f"{db_path.name}.backup-before-track-genre-tokens-{timestamp}")
    shutil.copy2(db_path, backup_path)
    return backup_path


def codex_command(default: str) -> str:
    command = os.environ.get("AIMP_CODEX_METADATA_COMMAND", default).strip() or default
    if "/" in command:
        return command
    return shutil.which(command) or command


def compact_text(value: Any, *, limit: int = 700) -> str:
    text = str(value or "").strip()
    return text if len(text) <= limit else f"{text[:limit]}..."


def track_payload(track: Track) -> dict[str, Any]:
    meta = dict(track.metadata_json or {})
    return {
        "id": track.id,
        "title": track.title,
        "prompt": compact_text(track.prompt),
        "duration_seconds": track.duration_seconds,
        "style": compact_text(meta.get("style")),
        "genre": compact_text(meta.get("genre")),
        "suno_style": compact_text(meta.get("suno_style")),
        "music_style": compact_text(meta.get("music_style")),
        "tags": meta.get("tags") or "",
        "rule_tokens": meta.get("genre_tokens") or [],
    }


def output_schema(track_ids: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["tracks"],
        "properties": {
            "tracks": {
                "type": "array",
                "minItems": len(track_ids),
                "maxItems": len(track_ids),
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["id", "tokens", "label", "confidence"],
                    "properties": {
                        "id": {"type": "string", "enum": track_ids},
                        "tokens": {
                            "type": "array",
                            "minItems": 1,
                            "maxItems": 8,
                            "items": {"type": "string", "minLength": 1, "maxLength": 48},
                        },
                        "label": {"type": "string", "minLength": 1, "maxLength": 120},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                },
            }
        },
    }


def build_prompt(batch: list[dict[str, Any]]) -> str:
    known_tokens = sorted(GENRE_PATTERNS)
    return "\n".join(
        [
            "Classify AI music tracks into reusable genre tokens for playlist backfill matching.",
            "Return only JSON matching the schema.",
            "",
            "Rules:",
            "- Use only the provided title, prompt, style, genre, suno_style, music_style, tags, and existing rule_tokens.",
            "- You cannot hear the audio. Do not infer from lyrics; lyrics are intentionally not provided.",
            "- Return 2-6 useful genre tokens per track when possible.",
            "- Tokens must be lowercase kebab-case, stable, and reusable across future tracks.",
            "- Prefer existing known tokens when they fit.",
            "- You may introduce new tokens for real genres not covered by known tokens, such as hyperpop, jersey-club, phonk, drill, pluggnb, afrobeat, amapiano, bossa-nova, shoegaze, dream-pop, new-jack-swing, deconstructed-club, breakcore, or similar.",
            "- Do not create mood/use-case tokens such as study, workout, night-drive, confidence, rain, focus, cafe, gaming, or sleep unless they are also real music genres.",
            "- Add language/channel-family tokens like kpop or jpop only when the metadata clearly says Korean/K-pop or Japanese/J-pop, not merely because of a title language.",
            "- If rule_tokens are partly wrong or too broad, correct them in tokens.",
            "- Keep label as a short human-readable genre label.",
            "- Confidence should reflect how clear the metadata is. Use lower confidence when metadata is vague.",
            "",
            "Known tokens:",
            ", ".join(known_tokens),
            "",
            "Tracks JSON:",
            json.dumps({"tracks": batch}, ensure_ascii=False, indent=2),
        ]
    )


def run_codex_batch(
    batch: list[dict[str, Any]],
    *,
    command: str,
    model: str,
    timeout: int,
) -> dict[str, dict[str, Any]]:
    track_ids = [str(item["id"]) for item in batch]
    with tempfile.TemporaryDirectory(prefix="aimp-track-genre-codex-") as temp_dir:
        temp_path = Path(temp_dir)
        schema_path = temp_path / "schema.json"
        output_path = temp_path / "genres.json"
        schema_path.write_text(json.dumps(output_schema(track_ids), ensure_ascii=False), encoding="utf-8")
        cmd = [
            command,
            "exec",
            "--ephemeral",
            "--sandbox",
            "read-only",
            "--cd",
            str(Path.cwd()),
            "--output-schema",
            str(schema_path),
            "-o",
            str(output_path),
        ]
        if model.strip():
            cmd.extend(["--model", model.strip()])
        cmd.append("-")
        env = dict(os.environ)
        env["NO_COLOR"] = "1"
        result = subprocess.run(
            cmd,
            input=build_prompt(batch),
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
            env=env,
        )
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip()
            raise RuntimeError(detail or f"codex exited with status {result.returncode}")
        if not output_path.exists():
            raise RuntimeError("codex did not write an output file")
        parsed = json.loads(output_path.read_text(encoding="utf-8"))

    by_id: dict[str, dict[str, Any]] = {}
    for item in parsed.get("tracks") or []:
        track_id = str(item.get("id") or "")
        if track_id in track_ids:
            by_id[track_id] = item
    missing = [track_id for track_id in track_ids if track_id not in by_id]
    if missing:
        raise RuntimeError(f"codex output missing track ids: {', '.join(missing)}")
    return by_id


def needs_ai_update(track: Track, *, force: bool) -> bool:
    if force:
        return True
    meta = dict(track.metadata_json or {})
    expected_hash = track_genre_token_source_hash(
        title=track.title or "",
        prompt=track.prompt or "",
        metadata=meta,
    )
    return not (
        meta.get(AI_GENRE_TOKEN_VERSION_METADATA_KEY) == AI_GENRE_TOKEN_VERSION
        and meta.get(AI_GENRE_TOKEN_HASH_METADATA_KEY) == expected_hash
        and current_ai_genre_tokens(meta, title=track.title or "", prompt=track.prompt or "")
    )


def chunks(items: list[Track], size: int) -> list[list[Track]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill deterministic and optional Codex-assisted track genre tokens.",
    )
    parser.add_argument("--mode", choices=["rules", "codex"], default="rules")
    parser.add_argument("--apply", action="store_true", help="Write changes to the database.")
    parser.add_argument("--force", action="store_true", help="Refresh existing AI classifications.")
    parser.add_argument("--limit", type=int, default=0, help="Limit tracks processed; 0 means all.")
    parser.add_argument("--batch-size", type=int, default=30, help="Codex tracks per request.")
    parser.add_argument("--timeout", type=int, default=900, help="Codex batch timeout seconds.")
    parser.add_argument("--model", default=os.environ.get("AIMP_CODEX_GENRE_MODEL", ""))
    parser.add_argument("--codex-command", default="codex")
    parser.add_argument("--no-backup", action="store_true", help="Skip sqlite DB backup before --apply.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.batch_size <= 0:
        raise SystemExit("--batch-size must be positive")
    if args.mode == "codex" and not args.apply:
        print("Running Codex classification without --apply; database will not be changed.")
    if args.apply and not args.no_backup:
        backup_path = backup_database()
        if backup_path:
            print(f"backup={backup_path}")

    session = SessionLocal()
    try:
        query = session.query(Track).order_by(Track.created_at.asc())
        tracks = query.limit(args.limit).all() if args.limit and args.limit > 0 else query.all()
        changed_rules = 0
        for track in tracks:
            before = dict(track.metadata_json or {})
            after = update_track_genre_token_metadata(
                before,
                title=track.title or "",
                prompt=track.prompt or "",
            )
            if before != after:
                changed_rules += 1
                if args.apply:
                    track.metadata_json = after

        ai_candidates = [track for track in tracks if args.mode == "codex" and needs_ai_update(track, force=args.force)]
        changed_ai = 0
        command = codex_command(args.codex_command)
        for batch_index, batch_tracks in enumerate(chunks(ai_candidates, args.batch_size), start=1):
            payload = [track_payload(track) for track in batch_tracks]
            print(f"codex_batch={batch_index} tracks={len(batch_tracks)}", flush=True)
            classifications = run_codex_batch(payload, command=command, model=args.model, timeout=args.timeout)
            for track in batch_tracks:
                result = classifications[track.id]
                tokens = normalize_genre_tokens(result.get("tokens") or [])
                if not tokens:
                    continue
                before = dict(track.metadata_json or {})
                after = update_track_ai_genre_token_metadata(
                    before,
                    title=track.title or "",
                    prompt=track.prompt or "",
                    tokens=tokens,
                    label=str(result.get("label") or ""),
                    confidence=result.get("confidence"),
                    provider="codex",
                )
                if before != after:
                    changed_ai += 1
                    if args.apply:
                        track.metadata_json = after
            if args.apply:
                session.commit()

        if args.apply:
            session.commit()
        else:
            session.rollback()
        print(
            "summary "
            f"tracks={len(tracks)} rules_changed={changed_rules} "
            f"ai_candidates={len(ai_candidates)} ai_changed={changed_ai} applied={args.apply}"
        )
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
