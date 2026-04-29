#!/usr/bin/env python3
"""OpenClaw-friendly helper for uploading generated release assets.

This script is intended to run on the VM next to the FastAPI app. It uses the
local API by default, bypassing public Google OAuth protection.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import sys
from pathlib import Path
from typing import Any

import httpx


DEFAULT_API_BASE = "http://127.0.0.1:8000/api"


def file_stem(path: Path) -> str:
    return path.stem.strip() or "Untitled Release"


def api_base(value: str | None) -> str:
    return (value or os.environ.get("AIMP_LOCAL_API_BASE") or DEFAULT_API_BASE).rstrip("/")


def print_json(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def request_json(client: httpx.Client, method: str, path: str, **kwargs) -> Any:
    response = client.request(method, path, **kwargs)
    try:
        payload = response.json()
    except ValueError:
        payload = response.text
    if response.is_error:
        detail = payload.get("detail") if isinstance(payload, dict) else payload
        raise RuntimeError(f"{response.status_code} {response.reason_phrase}: {detail}")
    return payload


def list_releases(client: httpx.Client, _args: argparse.Namespace) -> dict[str, Any]:
    releases = request_json(client, "GET", "/playlists/workspaces")
    return {
        "releases": [
            {
                "id": release["id"],
                "title": release["title"],
                "type": "single" if release["workspace_mode"] == "single_track_video" else "playlist",
                "workflow_state": release["workflow_state"],
                "archived": release.get("hidden", False),
                "tracks": len(release["tracks"]),
            }
            for release in releases
        ]
    }


def find_release_by_title(client: httpx.Client, title: str) -> dict[str, Any]:
    releases = request_json(client, "GET", "/playlists/workspaces")
    matches = [release for release in releases if release["title"] == title]
    if not matches:
        raise RuntimeError(f"No release found with exact title: {title}")
    if len(matches) > 1:
        ids = ", ".join(release["id"] for release in matches)
        raise RuntimeError(f"Multiple releases share title {title!r}. Use --release-id. Matches: {ids}")
    return matches[0]


def resolve_release(client: httpx.Client, *, release_id: str = "", release_title: str = "") -> dict[str, Any]:
    if release_id:
        releases = request_json(client, "GET", "/playlists/workspaces")
        release = next((item for item in releases if item["id"] == release_id), None)
        if not release:
            raise RuntimeError(f"No release found with id: {release_id}")
        return release
    if release_title:
        return find_release_by_title(client, release_title)
    raise RuntimeError("Use --release-id or --release-title.")


def format_timestamp(seconds: int) -> str:
    seconds = max(int(seconds or 0), 0)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    remainder = seconds % 60
    if hours:
        return f"{hours}:{minutes:02d}:{remainder:02d}"
    return f"{minutes:02d}:{remainder:02d}"


def release_timeline(release: dict[str, Any]) -> list[dict[str, Any]]:
    offset = 0
    timeline = []
    tracks = release.get("tracks") or []
    display_titles = display_track_titles(tracks)
    for index, (track, display_title) in enumerate(zip(tracks, display_titles), start=1):
        duration = max(int(track.get("duration_seconds") or 0), 0)
        timeline.append(
            {
                "index": index,
                "start_seconds": offset,
                "start": format_timestamp(offset),
                "title": track.get("title") or f"Track {index}",
                "display_title_hint": display_title,
                "duration_seconds": duration,
                "duration": format_timestamp(duration),
            }
        )
        offset += duration
    return timeline


def display_track_titles(tracks: list[dict[str, Any]]) -> list[str]:
    base_titles = [clean_track_display_title(track.get("title") or f"Track {index}") for index, track in enumerate(tracks, start=1)]
    counts: dict[str, int] = {}
    for title in base_titles:
        counts[title.lower()] = counts.get(title.lower(), 0) + 1

    seen: dict[str, int] = {}
    group_variants: dict[str, tuple[str, ...]] = {}
    variant_sets = [
        ("Morning", "Evening"),
        ("Warm", "Soft"),
        ("Quiet", "Deep"),
        ("Linen", "Amber"),
        ("Dawn", "Dusk"),
        ("Gentle", "Still"),
    ]
    display_titles = []
    for title in base_titles:
        key = title.lower()
        seen[key] = seen.get(key, 0) + 1
        if counts[key] > 1:
            if key not in group_variants:
                group_variants[key] = variant_sets[len(group_variants) % len(variant_sets)]
            variants = group_variants[key]
            variant = variants[(seen[key] - 1) % len(variants)]
            display_titles.append(f"{title} - {variant}")
        else:
            display_titles.append(title)
    return display_titles


def clean_track_display_title(title: str) -> str:
    cleaned = str(title or "").strip() or "Untitled Track"
    cleaned = re.sub(r"\s*(?:[-_]\s*)?\(?[AB]\)?$", "", cleaned, flags=re.IGNORECASE).strip()
    return cleaned or str(title or "Untitled Track").strip()


def create_single_release(client: httpx.Client, title: str, description: str = "") -> dict[str, Any]:
    return request_json(
        client,
        "POST",
        "/playlists/workspaces",
        json={
            "title": title,
            "target_duration_seconds": 1,
            "workspace_mode": "single_track_video",
            "auto_publish_when_ready": False,
            "description": description,
            "cover_prompt": "",
            "dreamina_prompt": "",
        },
    )


def upload_audio_file_to_release(
    client: httpx.Client,
    *,
    release_id: str,
    audio_path: Path,
    title: str,
    prompt: str,
    tags: str,
    cover_path: Path | None = None,
) -> dict[str, Any]:
    content_type = mimetypes.guess_type(str(audio_path))[0] or "audio/mpeg"
    files: dict[str, tuple[str, Any, str]] = {}
    with audio_path.open("rb") as handle:
        files["audio_file"] = (audio_path.name, handle, content_type)
        cover_handle = None
        if cover_path:
            cover_content_type = mimetypes.guess_type(str(cover_path))[0] or "image/png"
            cover_handle = cover_path.open("rb")
            files["cover_file"] = (cover_path.name, cover_handle, cover_content_type)
        try:
            return request_json(
                client,
                "POST",
                "/tracks/manual-upload",
                data={
                    "title": title,
                    "prompt": prompt or "OpenClaw generated audio upload",
                    "duration_seconds": "0",
                    "pending_workspace_id": release_id,
                    "tags": tags or "",
                },
                files=files,
            )
        finally:
            if cover_handle:
                cover_handle.close()


def resolve_cover_path(value: str | None) -> Path | None:
    if not value:
        return None
    cover_path = Path(value).expanduser().resolve()
    if not cover_path.exists():
        raise RuntimeError(f"Cover file does not exist: {cover_path}")
    if not cover_path.is_file():
        raise RuntimeError(f"Cover path is not a file: {cover_path}")
    return cover_path


def resolve_candidate_covers(values: list[str]) -> list[Path | None]:
    covers = [resolve_cover_path(value) for value in values]
    if len(covers) > 2:
        raise RuntimeError("A single release can accept at most two candidate covers.")
    return covers


def upload_audio(client: httpx.Client, args: argparse.Namespace) -> dict[str, Any]:
    audio_path = Path(args.audio).expanduser().resolve()
    if not audio_path.exists():
        raise RuntimeError(f"Audio file does not exist: {audio_path}")
    if not audio_path.is_file():
        raise RuntimeError(f"Audio path is not a file: {audio_path}")
    cover_path = resolve_cover_path(args.cover)

    title = args.title or file_stem(audio_path)
    release: dict[str, Any]
    created_release = False

    if args.new_single:
        release = create_single_release(
            client,
            args.release_title or title,
            description=f"Single release created by OpenClaw from {audio_path.name}.",
        )
        created_release = True
    elif args.release_id:
        release = request_json(client, "GET", "/playlists/workspaces")
        release = next((item for item in release if item["id"] == args.release_id), None)
        if not release:
            raise RuntimeError(f"No release found with id: {args.release_id}")
    elif args.release_title:
        release = find_release_by_title(client, args.release_title)
    else:
        raise RuntimeError("Use --new-single, --release-id, or --release-title.")

    track = upload_audio_file_to_release(
        client,
        release_id=release["id"],
        audio_path=audio_path,
        title=title,
        prompt=args.prompt,
        tags=args.tags,
        cover_path=cover_path,
    )

    return {
        "ok": True,
        "action": "upload-audio",
        "created_release": created_release,
        "release": {
            "id": release["id"],
            "title": release["title"],
            "workspace_mode": release["workspace_mode"],
            "workflow_state": release["workflow_state"],
        },
        "track": {
            "id": track["id"],
            "title": track["title"],
            "status": track["status"],
            "cover_image_path": (track.get("metadata_json") or {}).get("image_url"),
        },
        "next": "Review and approve the track in Slack or the web UI.",
    }


def upload_single_candidates(client: httpx.Client, args: argparse.Namespace) -> dict[str, Any]:
    audio_paths = [Path(value).expanduser().resolve() for value in args.audio]
    cover_paths = resolve_candidate_covers(args.cover or [])
    if not 1 <= len(audio_paths) <= 2:
        raise RuntimeError("A single release can accept one or two Suno candidate audio files.")
    if cover_paths and len(cover_paths) not in {1, len(audio_paths)}:
        raise RuntimeError("Use either one shared cover or one cover per candidate audio.")
    for audio_path in audio_paths:
        if not audio_path.exists():
            raise RuntimeError(f"Audio file does not exist: {audio_path}")
        if not audio_path.is_file():
            raise RuntimeError(f"Audio path is not a file: {audio_path}")

    release_title = args.release_title or file_stem(audio_paths[0])
    release = create_single_release(
        client,
        release_title,
        description=(
            f"Single release candidate set created by OpenClaw from "
            f"{', '.join(path.name for path in audio_paths)}."
        ),
    )

    tracks = []
    for index, audio_path in enumerate(audio_paths, start=1):
        track_title = args.title[index - 1] if args.title and index <= len(args.title) else file_stem(audio_path)
        cover_path = None
        if cover_paths:
            cover_path = cover_paths[index - 1] if len(cover_paths) == len(audio_paths) else cover_paths[0]
        track = upload_audio_file_to_release(
            client,
            release_id=release["id"],
            audio_path=audio_path,
            title=track_title,
            prompt=args.prompt,
            tags=args.tags,
            cover_path=cover_path,
        )
        tracks.append(
            {
                "id": track["id"],
                "title": track["title"],
                "status": track["status"],
                "cover_image_path": (track.get("metadata_json") or {}).get("image_url"),
            }
        )

    return {
        "ok": True,
        "action": "upload-single-candidates",
        "release": {
            "id": release["id"],
            "title": release["title"],
            "workspace_mode": release["workspace_mode"],
            "workflow_state": release["workflow_state"],
        },
        "tracks": tracks,
        "next": (
            "Human review should approve exactly one candidate. "
            "If both candidates are rejected, the release is automatically archived and can be restored from the web UI."
        ),
    }


def upload_cover(client: httpx.Client, args: argparse.Namespace) -> dict[str, Any]:
    cover_path = Path(args.cover).expanduser().resolve()
    if not cover_path.exists():
        raise RuntimeError(f"Cover file does not exist: {cover_path}")
    if not cover_path.is_file():
        raise RuntimeError(f"Cover path is not a file: {cover_path}")

    release_id = args.release_id
    if not release_id and args.release_title:
        release_id = find_release_by_title(client, args.release_title)["id"]
    if not release_id:
        raise RuntimeError("Use --release-id or --release-title.")

    content_type = mimetypes.guess_type(str(cover_path))[0] or "image/png"
    with cover_path.open("rb") as handle:
        release = request_json(
            client,
            "POST",
            f"/playlists/{release_id}/cover/upload",
            data={"actor": args.actor},
            files={"cover_file": (cover_path.name, handle, content_type)},
        )

    return {
        "ok": True,
        "action": "upload-cover",
        "release": {
            "id": release["id"],
            "title": release["title"],
            "workflow_state": release["workflow_state"],
            "cover_image_path": release["cover_image_path"],
            "cover_approved": release["cover_approved"],
        },
        "next": "Approve the cover in the web UI, then render video.",
    }


def metadata_context(client: httpx.Client, args: argparse.Namespace) -> dict[str, Any]:
    release = resolve_release(client, release_id=args.release_id, release_title=args.release_title)
    timeline = release_timeline(release)
    timestamp_lines = [f"{item['start']} {item['title']}" for item in timeline]
    display_timestamp_lines = [f"{item['start']} {item['display_title_hint']}" for item in timeline]
    return {
        "ok": True,
        "action": "metadata-context",
        "release": {
            "id": release["id"],
            "title": release["title"],
            "workspace_mode": release["workspace_mode"],
            "workflow_state": release["workflow_state"],
            "target_duration_seconds": release["target_duration_seconds"],
            "actual_duration_seconds": release["actual_duration_seconds"],
            "output_audio_path": release.get("output_audio_path"),
            "output_video_path": release.get("output_video_path"),
            "youtube_title": release.get("youtube_title"),
            "youtube_description": release.get("youtube_description"),
            "youtube_tags": release.get("youtube_tags"),
        },
        "timeline": timeline,
        "timestamp_lines": timestamp_lines,
        "display_timestamp_lines": display_timestamp_lines,
        "total_seconds": sum(item["duration_seconds"] for item in timeline),
        "total_duration": format_timestamp(sum(item["duration_seconds"] for item in timeline)),
        "instructions": (
            "Use timestamps and row order exactly. Prefer display_timestamp_lines for metadata so A/B suffixes are not shown. "
            "If you rewrite a displayed title, keep its timestamp fixed. "
            "Write tags as comma-separated plain tags without # symbols."
        ),
    }


def read_description(args: argparse.Namespace) -> str:
    if args.description_file:
        path = Path(args.description_file).expanduser().resolve()
        if not path.exists():
            raise RuntimeError(f"Description file does not exist: {path}")
        if not path.is_file():
            raise RuntimeError(f"Description path is not a file: {path}")
        return path.read_text(encoding="utf-8").strip()
    return (args.description or "").strip()


def approve_metadata(client: httpx.Client, args: argparse.Namespace) -> dict[str, Any]:
    release_id = args.release_id
    if not release_id and args.release_title:
        release_id = find_release_by_title(client, args.release_title)["id"]
    if not release_id:
        raise RuntimeError("Use --release-id or --release-title.")

    title = (args.title or "").strip()
    description = read_description(args)
    tags = (args.tags or "").strip()
    if not title:
        raise RuntimeError("--title is required.")
    if not description:
        raise RuntimeError("Use --description or --description-file.")
    if not tags:
        raise RuntimeError("--tags is required as a comma-separated string.")

    release = request_json(
        client,
        "POST",
        f"/playlists/{release_id}/metadata/approve",
        json={
            "actor": args.actor,
            "title": title,
            "description": description,
            "tags": tags,
            "note": args.note or "Metadata approved from OpenClaw.",
        },
    )
    return {
        "ok": True,
        "action": "approve-metadata",
        "release": {
            "id": release["id"],
            "title": release["title"],
            "workflow_state": release["workflow_state"],
            "metadata_approved": release["metadata_approved"],
            "youtube_title": release["youtube_title"],
            "youtube_description": release["youtube_description"],
            "youtube_tags": release["youtube_tags"],
        },
        "next": "Human can choose Publish Channel and approve publish/re-upload in the web UI.",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Upload OpenClaw-generated music assets to the local AI Music app.")
    parser.add_argument("--api-base", default=None, help=f"API base URL. Default: {DEFAULT_API_BASE}")

    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list-releases", help="List visible releases and ids.")
    list_parser.set_defaults(func=list_releases)

    context_parser = subparsers.add_parser(
        "metadata-context",
        help="Return release context and final-order timestamps for OpenClaw YouTube metadata writing.",
    )
    context_parser.add_argument("--release-id", default="", help="Existing release id.")
    context_parser.add_argument("--release-title", default="", help="Existing release title.")
    context_parser.set_defaults(func=metadata_context)

    audio_parser = subparsers.add_parser("upload-audio", help="Upload an audio file to an existing release or new single.")
    audio_parser.add_argument("--audio", required=True, help="Path to generated audio file.")
    audio_parser.add_argument("--title", default="", help="Track title. Defaults to audio filename stem.")
    audio_parser.add_argument("--prompt", default="", help="Prompt or generation note.")
    audio_parser.add_argument("--tags", default="", help="Comma-separated tags.")
    audio_parser.add_argument("--cover", default="", help="Optional cover image file to upload with this audio.")
    audio_parser.add_argument("--new-single", action="store_true", help="Create a new Single Release from this audio.")
    audio_parser.add_argument("--release-id", default="", help="Existing release id.")
    audio_parser.add_argument("--release-title", default="", help="Existing release title, or new release title with --new-single.")
    audio_parser.set_defaults(func=upload_audio)

    candidates_parser = subparsers.add_parser(
        "upload-single-candidates",
        help="Create a Single Release and upload one or two Suno candidate tracks.",
    )
    candidates_parser.add_argument("--audio", action="append", required=True, help="Candidate audio path. Repeat up to two times.")
    candidates_parser.add_argument("--title", action="append", default=[], help="Candidate title. Repeat in the same order as --audio.")
    candidates_parser.add_argument("--cover", action="append", default=[], help="Optional candidate cover path. Repeat once for a shared cover or once per --audio.")
    candidates_parser.add_argument("--release-title", default="", help="Single release title. Defaults to first audio filename stem.")
    candidates_parser.add_argument("--prompt", default="", help="Prompt or generation note shared by the candidates.")
    candidates_parser.add_argument("--tags", default="", help="Comma-separated tags shared by the candidates.")
    candidates_parser.set_defaults(func=upload_single_candidates)

    cover_parser = subparsers.add_parser("upload-cover", help="Upload a 16:9 cover image for a release.")
    cover_parser.add_argument("--cover", required=True, help="Path to cover image file: jpg, png, or webp.")
    cover_parser.add_argument("--release-id", default="", help="Existing release id.")
    cover_parser.add_argument("--release-title", default="", help="Existing release title.")
    cover_parser.add_argument("--actor", default="openclaw", help="Actor name recorded in release history.")
    cover_parser.set_defaults(func=upload_cover)

    metadata_parser = subparsers.add_parser(
        "approve-metadata",
        help="Approve YouTube metadata for a rendered release using OpenClaw-written copy.",
    )
    metadata_parser.add_argument("--release-id", default="", help="Existing release id.")
    metadata_parser.add_argument("--release-title", default="", help="Existing release title.")
    metadata_parser.add_argument("--title", required=True, help="YouTube title.")
    metadata_parser.add_argument("--description", default="", help="YouTube description text. Prefer --description-file for multiline copy.")
    metadata_parser.add_argument("--description-file", default="", help="UTF-8 text file containing the YouTube description.")
    metadata_parser.add_argument("--tags", required=True, help="Comma-separated YouTube tags, for example: Piano,CafePiano,StudyMusic")
    metadata_parser.add_argument("--actor", default="openclaw", help="Actor name recorded in metadata approval history.")
    metadata_parser.add_argument("--note", default="", help="Optional approval note.")
    metadata_parser.set_defaults(func=approve_metadata)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        with httpx.Client(base_url=api_base(args.api_base), timeout=120.0) as client:
            result = args.func(client, args)
        print_json(result)
        return 0
    except Exception as exc:  # noqa: BLE001
        print_json({"ok": False, "error": str(exc)})
        return 1


if __name__ == "__main__":
    sys.exit(main())
