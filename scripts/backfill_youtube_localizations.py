#!/usr/bin/env python3
"""Backfill YouTube metadata localizations for already published releases."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.models.playlist import Playlist
from app.services.youtube_service import YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, YouTubeService
from app.utils.youtube_localizations import (
    DEFAULT_YOUTUBE_LANGUAGE,
    SUPPORTED_YOUTUBE_LANGUAGES,
    localizations_for_youtube_api,
    normalize_youtube_language,
    normalize_youtube_localizations,
    sanitize_youtube_copy,
)


TARGET_LANGUAGES = ("vi", "th", "hi", "zh-CN")
LANGUAGE_NAMES = {
    "ko": "Korean",
    "ja": "Japanese",
    "en": "English",
    "es": "Spanish",
    "vi": "Vietnamese",
    "th": "Thai",
    "hi": "Hindi",
    "zh-CN": "Simplified Chinese",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate missing vi/th/hi/zh-CN YouTube localizations and push them to YouTube."
    )
    parser.add_argument("--release-id", action="append", default=[], help="Limit to a release id. Repeatable.")
    parser.add_argument("--dry-run", action="store_true", help="Generate and print a summary without DB/API writes.")
    parser.add_argument("--skip-youtube", action="store_true", help="Update only the local DB.")
    parser.add_argument("--timeout", type=int, default=360, help="Per-release Codex timeout in seconds.")
    parser.add_argument("--model", default="", help="Optional Codex model override.")
    parser.add_argument("--force", action="store_true", help="Regenerate target languages even if they already exist.")
    return parser.parse_args()


def db_path_from_url(database_url: str) -> Path | None:
    if database_url.startswith("sqlite:///"):
        return Path(database_url.replace("sqlite:///", "", 1))
    return None


def backup_database() -> Path | None:
    settings = get_settings()
    db_path = db_path_from_url(settings.database_url)
    if not db_path or not db_path.exists():
        return None
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    backup_path = db_path.with_name(f"{db_path.name}.backup-before-8lang-localizations-{timestamp}")
    shutil.copy2(db_path, backup_path)
    return backup_path


def codex_command() -> str:
    return os.environ.get("AIMP_CODEX_METADATA_COMMAND", "codex").strip() or "codex"


def output_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(TARGET_LANGUAGES),
        "properties": {language: {"$ref": "#/$defs/localizedCopy"} for language in TARGET_LANGUAGES},
        "$defs": {
            "localizedCopy": {
                "type": "object",
                "additionalProperties": False,
                "required": ["title", "description"],
                "properties": {
                    "title": {"type": "string", "minLength": 1, "maxLength": 100},
                    "description": {"type": "string", "minLength": 1},
                },
            }
        },
    }


def compact_copy(payload: dict[str, Any]) -> dict[str, str]:
    return {
        "title": sanitize_youtube_copy(payload.get("title")).strip()[:100],
        "description": sanitize_youtube_copy(payload.get("description")).strip(),
    }


def source_payload(
    *,
    playlist: Playlist,
    youtube_item: dict[str, Any] | None,
) -> dict[str, Any]:
    meta = dict(playlist.metadata_json or {})
    snippet = dict((youtube_item or {}).get("snippet") or {})
    youtube_localizations = dict((youtube_item or {}).get("localizations") or {})
    default_language = normalize_youtube_language(
        meta.get("youtube_default_language") or snippet.get("defaultLanguage") or DEFAULT_YOUTUBE_LANGUAGE
    )
    default_title = sanitize_youtube_copy(snippet.get("title") or meta.get("youtube_title") or playlist.title).strip()
    default_description = sanitize_youtube_copy(
        snippet.get("description") or meta.get("youtube_description") or meta.get("description") or ""
    ).strip()
    localizations = normalize_youtube_localizations(
        {
            **normalize_youtube_localizations(
                meta.get("youtube_localizations"),
                default_title=default_title,
                default_description=default_description,
                default_language=default_language,
            ),
            **normalize_youtube_localizations(
                youtube_localizations,
                default_title=default_title,
                default_description=default_description,
                default_language=default_language,
            ),
        },
        default_title=default_title,
        default_description=default_description,
        default_language=default_language,
    )
    return {
        "release": {
            "id": playlist.id,
            "title": playlist.title,
            "youtube_video_id": playlist.youtube_video_id,
            "youtube_channel_title": meta.get("youtube_channel_title"),
            "youtube_channel_id": meta.get("youtube_channel_id"),
            "default_language": default_language,
            "tags": snippet.get("tags") or meta.get("youtube_tags") or [],
        },
        "default_copy": {
            "language": default_language,
            "title": default_title,
            "description": default_description,
        },
        "existing_localizations": {
            language: compact_copy(payload)
            for language, payload in localizations.items()
            if language in SUPPORTED_YOUTUBE_LANGUAGES
        },
    }


def build_prompt(payload: dict[str, Any], missing_languages: list[str]) -> str:
    requested = ", ".join(f"{language} ({LANGUAGE_NAMES[language]})" for language in TARGET_LANGUAGES)
    source_json = json.dumps(payload, ensure_ascii=False, indent=2)
    return "\n".join(
        [
            "You are translating YouTube metadata for an AI music channel.",
            f"Write localized metadata for these languages only: {requested}.",
            "Return JSON with exactly these keys: vi, th, hi, zh-CN.",
            "",
            "Rules:",
            "- Preserve the release intent, music genre, mood, and target use case.",
            "- If any source title starts with [playlist], every output title must also start with [playlist].",
            "- Keep each title natural for YouTube and no longer than 100 characters.",
            "- Preserve every timestamp exactly. Do not add, remove, reorder, round, or translate timestamp tokens.",
            "- Preserve the tracklist order exactly. Translate only the displayed track title text after each timestamp.",
            "- Keep hashtag lines at the end of every description; translate or localize hashtags where natural, but do not omit them.",
            "- Do not invent upload status, URLs, channel claims, or extra metadata fields.",
            "- Use natural Vietnamese, Thai, Hindi, and Simplified Chinese copy for listeners in those languages.",
            "",
            "Source metadata JSON:",
            source_json,
        ]
    )


def run_codex(payload: dict[str, Any], missing_languages: list[str], *, timeout: int, model: str) -> dict[str, dict[str, str]]:
    with tempfile.TemporaryDirectory(prefix="aimp-localization-backfill-") as temp_dir:
        temp_path = Path(temp_dir)
        schema_path = temp_path / "schema.json"
        output_path = temp_path / "localizations.json"
        schema_path.write_text(json.dumps(output_schema(), ensure_ascii=False), encoding="utf-8")
        cmd = [
            codex_command(),
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
            input=build_prompt(payload, missing_languages),
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

    normalized = normalize_youtube_localizations(parsed)
    missing = [language for language in missing_languages if language not in normalized]
    if missing:
        raise RuntimeError(f"codex output did not include required languages: {', '.join(missing)}")
    return {language: normalized[language] for language in TARGET_LANGUAGES}


def youtube_client(service: YouTubeService, channel_id: str | None) -> Any:
    credentials = service._load_credentials(youtube_channel_id=channel_id)  # noqa: SLF001
    return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, credentials=credentials)


def fetch_youtube_item(youtube: Any, video_id: str) -> dict[str, Any] | None:
    response = youtube.videos().list(part="snippet,localizations", id=video_id).execute()
    items = response.get("items") or []
    return items[0] if items else None


def update_youtube_item(
    youtube: Any,
    *,
    item: dict[str, Any],
    localizations: dict[str, dict[str, str]],
    default_language: str,
) -> None:
    snippet = dict(item.get("snippet") or {})
    body_snippet = {
        "title": sanitize_youtube_copy(snippet.get("title")).strip()[:100],
        "description": sanitize_youtube_copy(snippet.get("description")).strip(),
        "categoryId": str(snippet.get("categoryId") or "10"),
    }
    if snippet.get("tags"):
        body_snippet["tags"] = list(snippet.get("tags") or [])
    if snippet.get("defaultLanguage"):
        body_snippet["defaultLanguage"] = normalize_youtube_language(snippet.get("defaultLanguage"))
    else:
        body_snippet["defaultLanguage"] = default_language
    if snippet.get("defaultAudioLanguage"):
        body_snippet["defaultAudioLanguage"] = snippet["defaultAudioLanguage"]

    api_localizations = localizations_for_youtube_api(localizations, default_language=default_language)
    youtube.videos().update(
        part="snippet,localizations",
        body={
            "id": item["id"],
            "snippet": body_snippet,
            "localizations": api_localizations,
        },
    ).execute()


def channel_id_for_playlist(playlist: Playlist, service: YouTubeService) -> str | None:
    meta = dict(playlist.metadata_json or {})
    channel_id = str(meta.get("youtube_channel_id") or "").strip()
    if channel_id:
        return channel_id
    channel_title = str(meta.get("youtube_channel_title") or "").strip().lower()
    if channel_title:
        for channel in service.get_status().get("channels", []):
            if str(channel.get("title") or "").strip().lower() == channel_title:
                return str(channel.get("id") or "").strip() or None
    return None


def main() -> int:
    args = parse_args()
    settings = get_settings()
    service = YouTubeService(settings)
    backup_path = None if args.dry_run else backup_database()
    if backup_path:
        print(f"DB backup: {backup_path}", flush=True)

    with SessionLocal() as db:
        stmt = select(Playlist).where(Playlist.youtube_video_id.is_not(None)).order_by(Playlist.updated_at.asc())
        playlists = list(db.scalars(stmt))
        if args.release_id:
            wanted = set(args.release_id)
            playlists = [playlist for playlist in playlists if playlist.id in wanted]

        print(f"published releases: {len(playlists)}", flush=True)
        failures: list[str] = []
        updated_count = 0
        skipped_count = 0
        youtube_cache: dict[str | None, Any] = {}

        for index, playlist in enumerate(playlists, start=1):
            video_id = str(playlist.youtube_video_id or "").strip()
            meta = dict(playlist.metadata_json or {})
            existing = normalize_youtube_localizations(
                meta.get("youtube_localizations"),
                default_title=meta.get("youtube_title") or playlist.title,
                default_description=meta.get("youtube_description") or meta.get("description") or "",
                default_language=meta.get("youtube_default_language") or DEFAULT_YOUTUBE_LANGUAGE,
            )
            missing_languages = [language for language in TARGET_LANGUAGES if args.force or language not in existing]
            if not missing_languages:
                print(f"[{index}/{len(playlists)}] skip {playlist.title}: target languages already present", flush=True)
                skipped_count += 1
                continue

            try:
                channel_id = channel_id_for_playlist(playlist, service)
                youtube = None
                youtube_item = None
                if not args.skip_youtube:
                    if channel_id not in youtube_cache:
                        youtube_cache[channel_id] = youtube_client(service, channel_id)
                    youtube = youtube_cache[channel_id]
                    youtube_item = fetch_youtube_item(youtube, video_id)
                    if not youtube_item:
                        raise RuntimeError(f"YouTube video not found: {video_id}")

                print(
                    f"[{index}/{len(playlists)}] generate {playlist.title} ({video_id}) -> {', '.join(missing_languages)}",
                    flush=True,
                )
                payload = source_payload(playlist=playlist, youtube_item=youtube_item)
                generated = run_codex(payload, missing_languages, timeout=args.timeout, model=args.model)
                merged = normalize_youtube_localizations(
                    {
                        **payload["existing_localizations"],
                        **existing,
                        **generated,
                    },
                    default_title=payload["default_copy"]["title"],
                    default_description=payload["default_copy"]["description"],
                    default_language=payload["default_copy"]["language"],
                )

                if args.dry_run:
                    print(f"  dry-run languages: {', '.join(merged)}", flush=True)
                    continue

                if youtube is not None and youtube_item is not None:
                    update_youtube_item(
                        youtube,
                        item=youtube_item,
                        localizations=merged,
                        default_language=payload["default_copy"]["language"],
                    )

                meta["youtube_localizations"] = merged
                meta["youtube_localizations_backfilled_at"] = datetime.now(timezone.utc).isoformat()
                playlist.metadata_json = meta
                db.add(playlist)
                db.commit()
                updated_count += 1
                print(f"  updated languages: {', '.join(merged)}", flush=True)
            except (HttpError, Exception) as exc:  # noqa: BLE001
                db.rollback()
                message = f"{playlist.id} {video_id} {playlist.title}: {exc}"
                failures.append(message)
                print(f"  FAILED {message}", flush=True)

        print(
            f"done: updated={updated_count} skipped={skipped_count} failures={len(failures)} dry_run={args.dry_run}",
            flush=True,
        )
        if failures:
            print("failures:", flush=True)
            for failure in failures:
                print(f"- {failure}", flush=True)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
