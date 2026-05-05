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
import sys
import time
from pathlib import Path
from typing import Any

import httpx

from app.utils.track_titles import clean_track_display_title, display_track_titles, upload_track_title


DEFAULT_API_BASE = "http://127.0.0.1:8000/api"
MAX_AUDIO_UPLOAD_ATTEMPTS = 3
DEFAULT_MAX_PLAYLIST_TRACK_SECONDS = 260
DEFAULT_YOUTUBE_CHANNEL_TITLE = "Soft Hour Radio"
JAPAN_YOUTUBE_CHANNEL_TITLE = "Tokyo Daydream Radio"
CHANNEL_PROFILE_DOCS = {
    DEFAULT_YOUTUBE_CHANNEL_TITLE: "docs/openclaw-channel-profiles/soft-hour-radio.md",
    JAPAN_YOUTUBE_CHANNEL_TITLE: "docs/openclaw-channel-profiles/tokyo-daydream-radio.md",
}
CHANNEL_PROFILE_NAMES = {
    DEFAULT_YOUTUBE_CHANNEL_TITLE: "soft-hour-radio",
    JAPAN_YOUTUBE_CHANNEL_TITLE: "tokyo-daydream-radio",
}
JAPAN_CHANNEL_KEYWORDS = (
    "anime",
    "anime pop",
    "anime-pop",
    "city pop",
    "citypop",
    "j-pop",
    "j pop",
    "jpop",
    "japanese pop",
    "japan pop",
    "japanese dance-pop",
    "japanese dance pop",
    "japanese synth-pop",
    "japanese synth pop",
    "japanese pop-rock",
    "japanese pop rock",
    "shibuya",
    "shinjuku",
    "tokyo",
    "vaporwave",
    "アニメ",
    "jポップ",
    "シティポップ",
    "東京",
    "渋谷",
    "新宿",
    "도쿄",
    "시부야",
    "신주쿠",
    "시티팝",
    "애니",
    "애니메이션",
    "제이팝",
)
POP_FAMILY_KEYWORDS = (
    "anime pop",
    "anime-pop",
    "anime opening",
    "j-pop",
    "jpop",
    "japanese pop",
    "k-pop",
    "kpop",
    "korean pop",
    "pop song",
    "pop vocal",
    "제이팝",
    "일본 팝",
    "케이팝",
    "팝송",
    "팝 보컬",
    "ポップ",
    "jポップ",
)
INSTRUMENTAL_INTENT_KEYWORDS = (
    "background music",
    "bgm",
    "instrumental",
    "instrumentals",
    "karaoke",
    "lofi",
    "lo-fi",
    "no lyric",
    "no lyrics",
    "no vocal",
    "no vocals",
    "non-vocal",
    "vocal off",
    "without lyrics",
    "without vocals",
    "가사 없는",
    "가사없",
    "보컬 없는",
    "보컬없",
    "연주곡",
    "배경음악",
    "インスト",
    "歌なし",
    "ボーカルなし",
)


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


def notify_slack(
    client: httpx.Client,
    text: str,
    *,
    channel_id: str | None = None,
    team_id: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"text": text}
    if channel_id:
        payload["channel_id"] = channel_id
    if team_id:
        payload["team_id"] = team_id
    try:
        return request_json(client, "POST", "/slack/notify", json=payload)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


def slack_notify_command(client: httpx.Client, args: argparse.Namespace) -> dict[str, Any]:
    result = notify_slack(
        client,
        args.text,
        channel_id=args.channel_id or None,
        team_id=args.team_id or None,
    )
    return {
        "action": "slack-notify",
        "ok": bool(result.get("ok")),
        "result": result,
    }


def upload_failure_notice(
    *,
    release: dict[str, Any],
    failures: list[dict[str, str]],
    uploaded_count: int,
    action: str,
) -> str:
    release_title = release.get("title") or release.get("id") or "unknown release"
    lines = [
        "*OpenClaw audio upload problem*",
        f"Release: `{release_title}`",
        f"Action: `{action}`",
        f"Uploaded remaining tracks: `{uploaded_count}`",
        f"Failed after {MAX_AUDIO_UPLOAD_ATTEMPTS} attempts:",
    ]
    for failure in failures[:10]:
        title = failure.get("title") or Path(failure.get("audio_path") or "").name
        audio_name = Path(failure.get("audio_path") or "").name
        error = failure.get("error") or "unknown error"
        lines.append(f"- `{title}` (`{audio_name}`): {error[:300]}")
    if len(failures) > 10:
        lines.append(f"- ...and {len(failures) - 10} more")
    lines.append("Render/publish was stopped. Re-download or re-export the failed source files and upload them again.")
    return "\n".join(lines)


def validate_local_audio_file(audio_path: Path) -> None:
    if not audio_path.exists():
        raise RuntimeError(f"Audio file does not exist: {audio_path}")
    if not audio_path.is_file():
        raise RuntimeError(f"Audio path is not a file: {audio_path}")
    if audio_path.stat().st_size <= 0:
        raise RuntimeError(f"Audio file is empty: {audio_path}")


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
                "duration_seconds": release.get("actual_duration_seconds", 0),
                "youtube_video_id": release.get("youtube_video_id"),
                "youtube_channel_id": release.get("youtube_channel_id"),
                "youtube_channel_title": release.get("youtube_channel_title"),
                "created_at": release.get("created_at"),
                "updated_at": release.get("updated_at"),
            }
            for release in releases
        ]
    }


def create_release(client: httpx.Client, args: argparse.Namespace) -> dict[str, Any]:
    mode_aliases = {
        "playlist": "playlist",
        "single": "single_track_video",
        "single_track_video": "single_track_video",
    }
    workspace_mode = mode_aliases.get(str(args.workspace_mode).strip().lower())
    if not workspace_mode:
        raise RuntimeError("--workspace-mode must be playlist or single.")

    release = request_json(
        client,
        "POST",
        "/playlists/workspaces",
        json={
            "title": args.release_title,
            "target_duration_seconds": args.target_seconds,
            "workspace_mode": workspace_mode,
            "auto_publish_when_ready": False,
            "description": args.description,
            "cover_prompt": "",
            "dreamina_prompt": "",
        },
    )
    return {
        "ok": True,
        "action": "create-release",
        "release": {
            "id": release["id"],
            "title": release["title"],
            "workspace_mode": release["workspace_mode"],
            "workflow_state": release["workflow_state"],
            "target_duration_seconds": release["target_duration_seconds"],
        },
        "next": (
            "Use this release.id while generating Suno output, then upload every related audio file with --release-id. "
            "Do not create another workspace for the same prompt/run."
        ),
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


def format_timestamp(seconds: int, *, force_hours: bool = False) -> str:
    seconds = max(int(seconds or 0), 0)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    remainder = seconds % 60
    if force_hours:
        return f"{hours:02d}:{minutes:02d}:{remainder:02d}"
    if hours:
        return f"{hours}:{minutes:02d}:{remainder:02d}"
    return f"{minutes:02d}:{remainder:02d}"


def read_text_file(value: str | None, *, label: str) -> str:
    if not value:
        return ""
    path = Path(value).expanduser().resolve()
    if not path.exists():
        raise RuntimeError(f"{label} file does not exist: {path}")
    if not path.is_file():
        raise RuntimeError(f"{label} path is not a file: {path}")
    return path.read_text(encoding="utf-8").strip()


def read_single_lyrics(args: argparse.Namespace) -> str:
    inline = str(getattr(args, "lyrics", "") or "")
    file_value = str(getattr(args, "lyrics_file", "") or "")
    if inline and file_value:
        raise RuntimeError("Use either --lyrics or --lyrics-file, not both.")
    return read_text_file(file_value, label="Lyrics") if file_value else inline


def resolve_lyrics_items(audio_count: int, *, lyrics: list[str], lyrics_files: list[str]) -> list[str]:
    if lyrics and lyrics_files:
        raise RuntimeError("Use either --lyrics or --lyrics-file for multi-audio uploads, not both.")
    values = [read_text_file(value, label="Lyrics") for value in lyrics_files] if lyrics_files else list(lyrics or [])
    if not values:
        return [""] * audio_count
    if len(values) == 1:
        return [values[0]] * audio_count
    if len(values) != audio_count:
        raise RuntimeError("When using per-track lyrics, provide either one shared value or exactly one per --audio.")
    return values


def resolve_style_items(audio_count: int, *, styles: list[str]) -> list[str]:
    values = list(styles or [])
    if not values:
        return [""] * audio_count
    if len(values) == 1:
        return [values[0]] * audio_count
    if len(values) != audio_count:
        raise RuntimeError("When using per-track styles, provide either one shared value or exactly one per --audio.")
    return values


def _flatten_text_values(*values: Any) -> str:
    parts: list[str] = []
    for value in values:
        if isinstance(value, (list, tuple, set)):
            parts.extend(str(item or "") for item in value)
        else:
            parts.append(str(value or ""))
    return " ".join(parts).lower()


def is_pop_family_vocal_request(*values: Any) -> bool:
    haystack = _flatten_text_values(*values)
    if any(keyword in haystack for keyword in INSTRUMENTAL_INTENT_KEYWORDS):
        return False
    return any(keyword in haystack for keyword in POP_FAMILY_KEYWORDS)


def require_pop_family_lyrics(*, lyrics_items: list[str], context: str, concept_values: list[Any]) -> None:
    if not is_pop_family_vocal_request(*concept_values):
        return
    missing = [index + 1 for index, lyrics in enumerate(lyrics_items) if not str(lyrics or "").strip()]
    if not missing:
        return
    joined = ", ".join(str(index) for index in missing)
    raise RuntimeError(
        f"{context} looks like a J-pop/K-pop/pop vocal release, so lyrics are required for track(s): {joined}. "
        "Generate or capture original lyrics and pass --lyrics or --lyrics-file for every track. "
        "Only omit lyrics when the human explicitly requested BGM/instrumental/no-vocal music."
    )


def max_playlist_track_seconds(args: argparse.Namespace) -> int:
    return max(int(getattr(args, "max_track_seconds", DEFAULT_MAX_PLAYLIST_TRACK_SECONDS) or 0), 0)


def require_playlist_track_duration(
    track: dict[str, Any],
    *,
    args: argparse.Namespace,
    context: str,
) -> None:
    if bool(getattr(args, "allow_long_track", False)):
        return
    max_seconds = max_playlist_track_seconds(args)
    if max_seconds <= 0:
        return
    duration_seconds = int(track.get("duration_seconds") or 0)
    if duration_seconds <= max_seconds:
        return
    title = track.get("title") or track.get("id") or "unknown track"
    raise RuntimeError(
        f"{context} rejected `{title}` because its duration is {format_timestamp(duration_seconds)}. "
        f"Playlist tracks must be {format_timestamp(max_seconds)} or shorter. "
        "Regenerate a shorter Suno track, split the concept into separate songs, or pass --allow-long-track "
        "only when the human explicitly accepts a longer track."
    )


def require_release_playlist_track_durations(
    release: dict[str, Any],
    *,
    args: argparse.Namespace,
    context: str,
) -> None:
    if bool(getattr(args, "allow_long_track", False)):
        return
    for track in release.get("tracks") or []:
        require_playlist_track_duration(track, args=args, context=context)


def release_timeline(release: dict[str, Any]) -> list[dict[str, Any]]:
    offset = 0
    timeline = []
    tracks = release.get("tracks") or []
    total_seconds = sum(max(int(track.get("duration_seconds") or 0), 0) for track in tracks)
    force_hours = total_seconds >= 3600
    display_titles = display_track_titles(tracks)
    for index, (track, display_title) in enumerate(zip(tracks, display_titles), start=1):
        duration = max(int(track.get("duration_seconds") or 0), 0)
        timeline.append(
            {
                "index": index,
                "start_seconds": offset,
                "start": format_timestamp(offset, force_hours=force_hours),
                "title": track.get("title") or f"Track {index}",
                "display_title_hint": display_title,
                "duration_seconds": duration,
                "duration": format_timestamp(duration),
                "lyrics": str(track.get("lyrics") or ""),
                "style": str(track.get("style") or ""),
                "prompt": track.get("prompt") or "",
                "tags": track.get("tags") or "",
            }
        )
        offset += duration
    return timeline


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
    lyrics: str = "",
    style: str = "",
    cover_path: Path | None = None,
    dispatch_review: bool = True,
    attempts: int = MAX_AUDIO_UPLOAD_ATTEMPTS,
) -> dict[str, Any]:
    validate_local_audio_file(audio_path)
    content_type = mimetypes.guess_type(str(audio_path))[0] or "audio/mpeg"
    last_error: Exception | None = None
    for attempt in range(1, max(attempts, 1) + 1):
        files: dict[str, tuple[str, Any, str]] = {}
        with audio_path.open("rb") as handle:
            files["audio_file"] = (audio_path.name, handle, content_type)
            cover_handle = None
            if cover_path:
                cover_content_type = mimetypes.guess_type(str(cover_path))[0] or "image/png"
                cover_handle = cover_path.open("rb")
                files["cover_file"] = (cover_path.name, cover_handle, cover_content_type)
            try:
                track = request_json(
                    client,
                    "POST",
                    "/tracks/manual-upload",
                    data={
                        "title": title,
                        "prompt": prompt or "OpenClaw generated audio upload",
                        "duration_seconds": "0",
                        "pending_workspace_id": release_id,
                        "tags": tags or "",
                        "lyrics": lyrics or "",
                        "style": style or "",
                        "dispatch_review": str(dispatch_review).lower(),
                    },
                    files=files,
                )
                duration_seconds = int(track.get("duration_seconds") or 0)
                if duration_seconds <= 0:
                    raise RuntimeError(
                        f"Upload returned invalid duration_seconds={track.get('duration_seconds')!r}"
                    )
                return track
            except (RuntimeError, httpx.HTTPError) as exc:
                last_error = exc
                if attempt >= max(attempts, 1):
                    break
                time.sleep(min(2.0 * attempt, 5.0))
            finally:
                if cover_handle:
                    cover_handle.close()
    raise RuntimeError(
        f"Audio upload failed after {max(attempts, 1)} attempts for {audio_path.name}: {last_error}"
    ) from last_error


def resolve_cover_path(value: str | None) -> Path | None:
    return resolve_image_path(value, label="Cover")


def resolve_thumbnail_path(value: str | None) -> Path | None:
    return resolve_image_path(value, label="Thumbnail")


def resolve_loop_video_path(value: str | None) -> Path | None:
    return resolve_image_path(value, label="Loop video")


def resolve_image_path(value: str | None, *, label: str) -> Path | None:
    if not value:
        return None
    image_path = Path(value).expanduser().resolve()
    if not image_path.exists():
        raise RuntimeError(f"{label} file does not exist: {image_path}")
    if not image_path.is_file():
        raise RuntimeError(f"{label} path is not a file: {image_path}")
    return image_path


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

    title = upload_track_title(args.title or file_stem(audio_path))
    lyrics = read_single_lyrics(args)
    if args.new_single:
        require_pop_family_lyrics(
            lyrics_items=[lyrics],
            context="upload-audio",
            concept_values=[args.release_title, title, args.prompt, args.style, args.tags],
        )
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

    auto_approve_playlist = release["workspace_mode"] == "playlist" and not args.pending_review
    require_pop_family_lyrics(
        lyrics_items=[lyrics],
        context="upload-audio",
        concept_values=[release.get("title"), title, args.prompt, args.style, args.tags],
    )
    try:
        track = upload_audio_file_to_release(
            client,
            release_id=release["id"],
            audio_path=audio_path,
            title=title,
            prompt=args.prompt,
            tags=args.tags,
            lyrics=lyrics,
            style=args.style,
            cover_path=cover_path,
            dispatch_review=not auto_approve_playlist,
        )
        if auto_approve_playlist:
            require_playlist_track_duration(track, args=args, context="upload-audio playlist auto-approval")
            track = approve_track_to_playlist(
                client,
                track_id=track["id"],
                release_id=release["id"],
                actor=args.actor,
            )
            release = get_release(client, release["id"])
    except Exception as exc:  # noqa: BLE001
        notify_slack(
            client,
            upload_failure_notice(
                release=release,
                failures=[{"title": title, "audio_path": str(audio_path), "error": str(exc)}],
                uploaded_count=0,
                action="upload-audio",
            ),
        )
        raise

    return {
        "ok": True,
        "action": "upload-audio",
        "created_release": created_release,
        "auto_approved": auto_approve_playlist,
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
            "duration_seconds": track["duration_seconds"],
            "cover_image_path": (track.get("metadata_json") or {}).get("image_url"),
            "lyrics_present": bool((track.get("metadata_json") or {}).get("lyrics")),
            "style": (track.get("metadata_json") or {}).get("style") or "",
            "style_present": bool((track.get("metadata_json") or {}).get("style")),
        },
        "next": (
            "Track uploaded and auto-approved into the playlist."
            if auto_approve_playlist
            else "Review and approve the track in Slack or the web UI."
        ),
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
    raw_titles = [
        args.title[index - 1] if args.title and index <= len(args.title) else file_stem(audio_path)
        for index, audio_path in enumerate(audio_paths, start=1)
    ]
    track_titles = display_track_titles(
        [{"title": title, "duration_seconds": 0} for title in raw_titles]
    )
    lyrics_items = resolve_lyrics_items(len(audio_paths), lyrics=args.lyrics or [], lyrics_files=args.lyrics_file or [])
    style_items = resolve_style_items(len(audio_paths), styles=args.style or [])
    require_pop_family_lyrics(
        lyrics_items=lyrics_items,
        context="upload-single-candidates",
        concept_values=[release_title, raw_titles, args.prompt, args.style, args.tags],
    )
    if args.release_id:
        release = get_release(client, args.release_id)
        if release["workspace_mode"] != "single_track_video":
            raise RuntimeError("upload-single-candidates with --release-id requires a Single Release workspace.")
        existing_count = len(release.get("tracks") or [])
        if existing_count + len(audio_paths) > 2:
            raise RuntimeError("A Single Release can contain at most two candidate tracks.")
    else:
        release = create_single_release(
            client,
            release_title,
            description=(
                f"Single release candidate set created by OpenClaw from "
                f"{', '.join(path.name for path in audio_paths)}."
            ),
        )

    tracks = []
    failed_uploads: list[dict[str, str]] = []
    for index, audio_path in enumerate(audio_paths, start=1):
        track_title = track_titles[index - 1]
        cover_path = None
        if cover_paths:
            cover_path = cover_paths[index - 1] if len(cover_paths) == len(audio_paths) else cover_paths[0]
        try:
            track = upload_audio_file_to_release(
                client,
                release_id=release["id"],
                audio_path=audio_path,
                title=track_title,
                prompt=args.prompt,
                tags=args.tags,
                lyrics=lyrics_items[index - 1],
                style=style_items[index - 1],
                cover_path=cover_path,
            )
        except Exception as exc:  # noqa: BLE001
            failed_uploads.append(
                {
                    "title": track_title,
                    "audio_path": str(audio_path),
                    "error": str(exc),
                }
            )
            continue
        tracks.append(
            {
                "id": track["id"],
                "title": track["title"],
                "status": track["status"],
                "duration_seconds": track["duration_seconds"],
                "cover_image_path": (track.get("metadata_json") or {}).get("image_url"),
                "lyrics_present": bool((track.get("metadata_json") or {}).get("lyrics")),
                "style": (track.get("metadata_json") or {}).get("style") or "",
                "style_present": bool((track.get("metadata_json") or {}).get("style")),
            }
        )

    if failed_uploads:
        notice = upload_failure_notice(
            release=release,
            failures=failed_uploads,
            uploaded_count=len(tracks),
            action="upload-single-candidates",
        )
        notify_slack(client, notice)
        if not tracks:
            raise RuntimeError(
                f"All candidate audio uploads failed after {MAX_AUDIO_UPLOAD_ATTEMPTS} attempts."
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
        "failed_uploads": failed_uploads,
        "next": (
            "Human review can approve one candidate. If both candidates are good, approve the second one too; "
            "the app will split it into its own Single Release instead of combining the two songs. "
            "If both candidates are rejected, the release is automatically archived and can be restored from the web UI."
        ),
    }


def create_playlist_release(
    client: httpx.Client,
    *,
    title: str,
    target_duration_seconds: int = 3600,
    description: str = "",
) -> dict[str, Any]:
    return request_json(
        client,
        "POST",
        "/playlists/workspaces",
        json={
            "title": title,
            "target_duration_seconds": target_duration_seconds,
            "workspace_mode": "playlist",
            "auto_publish_when_ready": False,
            "description": description or "Automatic private playlist release created by OpenClaw.",
            "cover_prompt": "",
            "dreamina_prompt": "",
        },
    )


def get_release(client: httpx.Client, release_id: str) -> dict[str, Any]:
    releases = request_json(client, "GET", "/playlists/workspaces")
    release = next((item for item in releases if item["id"] == release_id), None)
    if not release:
        raise RuntimeError(f"No release found with id: {release_id}")
    return release


def wait_for_release(
    client: httpx.Client,
    release_id: str,
    *,
    stage: str,
    timeout_seconds: int,
    poll_seconds: float,
    predicate,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    failed_states = {
        "render_failed",
        "video_build_failed",
        "publish_failed",
        "youtube_upload_failed",
    }
    last_release = get_release(client, release_id)
    while time.monotonic() < deadline:
        last_release = get_release(client, release_id)
        workflow_state = str(last_release.get("workflow_state") or "")
        if workflow_state in failed_states:
            raise RuntimeError(f"{stage} failed: {last_release.get('note') or workflow_state}")
        if predicate(last_release):
            return last_release
        time.sleep(poll_seconds)
    raise RuntimeError(
        f"Timed out waiting for {stage}. "
        f"Last state: {last_release.get('workflow_state')} / {last_release.get('note')}"
    )


def infer_youtube_channel_title(args: argparse.Namespace) -> str:
    explicit_title = str(getattr(args, "youtube_channel_title", "") or "").strip()
    if explicit_title:
        return explicit_title

    haystack = " ".join(
        str(value or "")
        for value in (
            getattr(args, "release_title", ""),
            getattr(args, "description", ""),
            getattr(args, "prompt", ""),
            getattr(args, "tags", ""),
        )
    ).lower()
    if any(keyword.lower() in haystack for keyword in JAPAN_CHANNEL_KEYWORDS):
        return JAPAN_YOUTUBE_CHANNEL_TITLE
    return DEFAULT_YOUTUBE_CHANNEL_TITLE


def build_channel_profile(args: argparse.Namespace) -> dict[str, Any]:
    title = infer_youtube_channel_title(args)
    profile_doc = CHANNEL_PROFILE_DOCS.get(title, "docs/openclaw-channel-profiles/custom-channel.md")
    return {
        "youtube_channel_title": title,
        "profile": CHANNEL_PROFILE_NAMES.get(title, "custom-channel"),
        "profile_doc": profile_doc,
        "explicit_channel_requested": bool(str(getattr(args, "youtube_channel_title", "") or "").strip()),
        "metadata_doc": "docs/openclaw-youtube-metadata.md",
        "shared_upload_doc": "docs/openclaw-upload.md",
        "rule": "Pick the channel first, then read only that channel profile for cover, thumbnail, and loop-video visuals. Do not mix visual signatures across channels.",
    }


def channel_profile(client: httpx.Client, args: argparse.Namespace) -> dict[str, Any]:
    del client
    return build_channel_profile(args)


def resolve_youtube_channel_id(client: httpx.Client, *, title: str, channel_id: str = "") -> str:
    if channel_id:
        return channel_id
    status = request_json(client, "GET", "/youtube/status")
    channels = status.get("channels") or []
    match = next((channel for channel in channels if channel.get("title") == title), None)
    if not match:
        available = ", ".join(channel.get("title") or channel.get("id") or "unknown" for channel in channels)
        raise RuntimeError(f"YouTube channel {title!r} is not connected. Available channels: {available}")
    return str(match["id"])


def approve_track_to_release(
    client: httpx.Client,
    *,
    track_id: str,
    release_id: str,
    actor: str,
    rationale: str,
) -> dict[str, Any]:
    return request_json(
        client,
        "POST",
        f"/tracks/{track_id}/decisions",
        json={
            "decision": "approve",
            "source": "agent",
            "actor": actor,
            "rationale": rationale,
            "playlist_id": release_id,
        },
    )


def approve_track_to_playlist(client: httpx.Client, *, track_id: str, release_id: str, actor: str) -> dict[str, Any]:
    return approve_track_to_release(
        client,
        track_id=track_id,
        release_id=release_id,
        actor=actor,
        rationale="Auto-approved for private playlist publishing.",
    )


def approve_generated_metadata(client: httpx.Client, *, release: dict[str, Any], actor: str) -> dict[str, Any]:
    title = (release.get("youtube_title") or "").strip()
    description = (release.get("youtube_description") or "").strip()
    tags = release.get("youtube_tags") or []
    if not title or not description:
        raise RuntimeError("Generated metadata is missing title or description.")
    return request_json(
        client,
        "POST",
        f"/playlists/{release['id']}/metadata/approve",
        json={
            "actor": actor,
            "title": title,
            "description": description,
            "tags": tags,
            "note": "Auto-approved metadata for private YouTube upload.",
        },
    )


def require_reupload_confirmation(args: argparse.Namespace, release: dict[str, Any], *, action: str) -> None:
    youtube_video_id = str(release.get("youtube_video_id") or "").strip()
    if not youtube_video_id or bool(getattr(args, "allow_reupload", False)):
        return
    raise RuntimeError(
        f"{action} refuses to re-upload release {release.get('id')} because it already has "
        f"YouTube video id {youtube_video_id}. Create a fresh release for a new upload, or pass "
        "--allow-reupload only when the human explicitly asks to upload this same release again."
    )


def release_has_uploaded_cover(release: dict[str, Any]) -> bool:
    return bool(
        release.get("cover_image_path")
        and release.get("cover_source") == "manual-upload"
    )


def release_has_uploaded_thumbnail(release: dict[str, Any]) -> bool:
    return bool(
        release.get("youtube_thumbnail_path")
        and release.get("youtube_thumbnail_source") == "manual-upload"
    )


def auto_publish_playlist(client: httpx.Client, args: argparse.Namespace) -> dict[str, Any]:
    audio_paths = [Path(value).expanduser().resolve() for value in args.audio]
    if not audio_paths:
        raise RuntimeError("Use at least one --audio path.")
    for audio_path in audio_paths:
        if not audio_path.exists():
            raise RuntimeError(f"Audio file does not exist: {audio_path}")
        if not audio_path.is_file():
            raise RuntimeError(f"Audio path is not a file: {audio_path}")
    cover_path = resolve_cover_path(args.cover)
    thumbnail_path = resolve_thumbnail_path(args.thumbnail)
    loop_video_path = resolve_loop_video_path(args.loop_video)
    raw_titles = args.title if args.title else [file_stem(path) for path in audio_paths]
    if args.title and len(args.title) != len(audio_paths):
        raise RuntimeError("When using --title, provide exactly one --title per --audio.")
    display_titles = display_track_titles(
        [{"title": title, "duration_seconds": 0} for title in raw_titles]
    )
    lyrics_items = resolve_lyrics_items(len(audio_paths), lyrics=args.lyrics or [], lyrics_files=args.lyrics_file or [])
    style_items = resolve_style_items(len(audio_paths), styles=args.style or [])
    if not cover_path and not args.release_id and not args.allow_generated_draft_cover:
        raise RuntimeError(
            "auto-publish-playlist requires --cover when creating a new Playlist Release. "
            "Generate a final 16:9 cover image first, then pass --cover ABSOLUTE_FINAL_COVER_IMAGE_PATH."
        )
    if not thumbnail_path and not args.release_id and not args.allow_cover_as_thumbnail:
        raise RuntimeError(
            "auto-publish-playlist requires --thumbnail when creating a new Playlist Release. "
            "Generate a YouTube thumbnail with readable text first, then pass --thumbnail ABSOLUTE_THUMBNAIL_IMAGE_PATH. "
            "Only pass --allow-cover-as-thumbnail if the human explicitly wants one image for both video and thumbnail."
        )
    if not args.release_id:
        require_pop_family_lyrics(
            lyrics_items=lyrics_items,
            context="auto-publish-playlist",
            concept_values=[
                args.release_title,
                raw_titles,
                args.description,
                args.prompt,
                args.style,
                args.tags,
                args.youtube_channel_title,
            ],
        )

    release = (
        get_release(client, args.release_id)
        if args.release_id
        else create_playlist_release(
            client,
            title=args.release_title or file_stem(audio_paths[0]),
            target_duration_seconds=args.target_seconds,
            description=args.description,
        )
    )
    if release["workspace_mode"] != "playlist":
        raise RuntimeError("auto-publish-playlist requires a Playlist Release, not a Single Release.")
    require_reupload_confirmation(args, release, action="auto-publish-playlist")
    if not cover_path and not release_has_uploaded_cover(release) and not args.allow_generated_draft_cover:
        raise RuntimeError(
            "auto-publish-playlist requires a final 16:9 cover image before YouTube upload. "
            "Pass --cover ABSOLUTE_FINAL_COVER_IMAGE_PATH, or upload a final cover to the release first. "
            "Only pass --allow-generated-draft-cover if the human explicitly accepts a placeholder cover."
        )
    if not thumbnail_path and not release_has_uploaded_thumbnail(release) and not args.allow_cover_as_thumbnail:
        raise RuntimeError(
            "auto-publish-playlist requires a YouTube thumbnail image before YouTube upload. "
            "Pass --thumbnail ABSOLUTE_THUMBNAIL_IMAGE_PATH, or upload a final thumbnail to the release first. "
            "Only pass --allow-cover-as-thumbnail if the human explicitly wants to reuse the video cover as the YouTube thumbnail."
        )
    require_pop_family_lyrics(
        lyrics_items=lyrics_items,
        context="auto-publish-playlist",
        concept_values=[
            release.get("title"),
            raw_titles,
            args.release_title,
            args.description,
            args.prompt,
            args.style,
            args.tags,
            args.youtube_channel_title,
        ],
    )

    if loop_video_path:
        content_type = mimetypes.guess_type(str(loop_video_path))[0] or "video/mp4"
        with loop_video_path.open("rb") as handle:
            release = request_json(
                client,
                "POST",
                f"/playlists/{release['id']}/loop-video/upload",
                data={
                    "actor": args.actor,
                    "smooth_loop": str(not args.hard_loop_video).lower(),
                },
                files={"loop_video_file": (loop_video_path.name, handle, content_type)},
            )

    uploaded_tracks = []
    failed_uploads: list[dict[str, str]] = []
    for audio_path, track_title, lyrics, style in zip(audio_paths, display_titles, lyrics_items, style_items):
        try:
            track = upload_audio_file_to_release(
                client,
                release_id=release["id"],
                audio_path=audio_path,
                title=track_title,
                prompt=args.prompt,
                tags=args.tags,
                lyrics=lyrics,
                style=style,
                cover_path=None,
                dispatch_review=False,
            )
            require_playlist_track_duration(track, args=args, context="auto-publish-playlist")
            approved = approve_track_to_playlist(
                client,
                track_id=track["id"],
                release_id=release["id"],
                actor=args.actor,
            )
        except Exception as exc:  # noqa: BLE001
            failed_uploads.append(
                {
                    "title": track_title,
                    "audio_path": str(audio_path),
                    "error": str(exc),
                }
            )
            continue
        uploaded_tracks.append(
            {
                "id": approved["id"],
                "title": approved["title"],
                "status": approved["status"],
                "duration_seconds": approved["duration_seconds"],
                "lyrics_present": bool((approved.get("metadata_json") or {}).get("lyrics")),
                "style": (approved.get("metadata_json") or {}).get("style") or "",
                "style_present": bool((approved.get("metadata_json") or {}).get("style")),
            }
        )

    if failed_uploads:
        notice = upload_failure_notice(
            release=release,
            failures=failed_uploads,
            uploaded_count=len(uploaded_tracks),
            action="auto-publish-playlist",
        )
        slack_result = notify_slack(client, notice)
        raise RuntimeError(
            f"{len(failed_uploads)} audio upload(s) failed after {MAX_AUDIO_UPLOAD_ATTEMPTS} attempts; "
            f"uploaded {len(uploaded_tracks)} remaining track(s); render/publish stopped. "
            f"Slack notified: {bool(slack_result.get('ok'))}."
        )

    release = get_release(client, release["id"])
    require_release_playlist_track_durations(
        release,
        args=args,
        context="auto-publish-playlist existing playlist track check",
    )

    release = request_json(
        client,
        "POST",
        f"/playlists/{release['id']}/render-audio",
        json={"actor": args.actor},
    )
    release = wait_for_release(
        client,
        release["id"],
        stage="audio render",
        timeout_seconds=args.wait_timeout_seconds,
        poll_seconds=args.poll_seconds,
        predicate=lambda item: bool(item.get("output_audio_path")),
    )

    if cover_path:
        content_type = mimetypes.guess_type(str(cover_path))[0] or "image/png"
        with cover_path.open("rb") as handle:
            release = request_json(
                client,
                "POST",
                f"/playlists/{release['id']}/cover/upload",
                data={"actor": args.actor},
                files={"cover_file": (cover_path.name, handle, content_type)},
            )
    elif release_has_uploaded_cover(release):
        release = get_release(client, release["id"])
    elif args.allow_generated_draft_cover:
        release = request_json(
            client,
            "POST",
            f"/playlists/{release['id']}/cover/generate",
            json={"actor": args.actor, "regenerate": False},
        )
    else:
        raise RuntimeError("Final cover image is required before cover approval.")

    if thumbnail_path:
        content_type = mimetypes.guess_type(str(thumbnail_path))[0] or "image/png"
        with thumbnail_path.open("rb") as handle:
            release = request_json(
                client,
                "POST",
                f"/playlists/{release['id']}/thumbnail/upload",
                data={"actor": args.actor},
                files={"thumbnail_file": (thumbnail_path.name, handle, content_type)},
            )
    elif release_has_uploaded_thumbnail(release):
        release = get_release(client, release["id"])
    elif args.allow_cover_as_thumbnail:
        release = get_release(client, release["id"])
    else:
        raise RuntimeError("Final YouTube thumbnail image is required before cover approval.")

    release = request_json(
        client,
        "POST",
        f"/playlists/{release['id']}/cover/approve",
        json={
            "actor": args.actor,
            "approved": True,
            "note": "Auto-approved cover for private playlist publishing.",
        },
    )
    release = request_json(
        client,
        "POST",
        f"/playlists/{release['id']}/video/render",
        json={"actor": args.actor},
    )
    release = wait_for_release(
        client,
        release["id"],
        stage="video render",
        timeout_seconds=args.wait_timeout_seconds,
        poll_seconds=args.poll_seconds,
        predicate=lambda item: bool(item.get("output_video_path")) and bool(item.get("youtube_title")),
    )

    if not release.get("youtube_title") or not release.get("youtube_description"):
        release = request_json(
            client,
            "POST",
            f"/playlists/{release['id']}/metadata/generate",
            json={"actor": args.actor},
        )
    release = approve_generated_metadata(client, release=release, actor=args.actor)

    youtube_channel_title = infer_youtube_channel_title(args)
    channel_id = resolve_youtube_channel_id(
        client,
        title=youtube_channel_title,
        channel_id=args.youtube_channel_id,
    )
    release = request_json(
        client,
        "POST",
        f"/playlists/{release['id']}/approve-publish",
        json={
            "actor": args.actor,
            "youtube_channel_id": channel_id,
            "note": f"Auto-publish private playlist to {youtube_channel_title}.",
            "force_under_target": args.force_under_target,
        },
    )
    release = wait_for_release(
        client,
        release["id"],
        stage="YouTube private upload",
        timeout_seconds=args.wait_timeout_seconds,
        poll_seconds=args.poll_seconds,
        predicate=lambda item: bool(item.get("youtube_video_id")) or item.get("workflow_state") == "ready_for_youtube_auth",
    )

    return {
        "ok": True,
        "action": "auto-publish-playlist",
        "release": {
            "id": release["id"],
            "title": release["title"],
            "workflow_state": release["workflow_state"],
            "actual_duration_seconds": release["actual_duration_seconds"],
            "output_audio_path": release.get("output_audio_path"),
            "output_video_path": release.get("output_video_path"),
            "loop_video_path": release.get("loop_video_path"),
            "youtube_thumbnail_path": release.get("youtube_thumbnail_path"),
            "youtube_title": release.get("youtube_title"),
            "youtube_video_id": release.get("youtube_video_id"),
            "youtube_channel_id": channel_id,
            "youtube_channel_title": youtube_channel_title,
        },
        "uploaded_tracks": uploaded_tracks,
        "privacy": "private (from AIMP_YOUTUBE_PRIVACY_STATUS)",
        "next": "Listen to the private YouTube upload. If it is good, change visibility to Public in YouTube Studio.",
    }


def auto_publish_single(client: httpx.Client, args: argparse.Namespace) -> dict[str, Any]:
    audio_paths = [Path(value).expanduser().resolve() for value in args.audio]
    if len(audio_paths) != 1:
        raise RuntimeError("auto-publish-single publishes exactly one final song. Run it once per good Suno output.")
    for audio_path in audio_paths:
        if not audio_path.exists():
            raise RuntimeError(f"Audio file does not exist: {audio_path}")
        if not audio_path.is_file():
            raise RuntimeError(f"Audio path is not a file: {audio_path}")
    cover_path = resolve_cover_path(args.cover)
    thumbnail_path = resolve_thumbnail_path(args.thumbnail)
    loop_video_path = resolve_loop_video_path(args.loop_video)
    raw_titles = args.title if args.title else [file_stem(path) for path in audio_paths]
    if args.title and len(args.title) != len(audio_paths):
        raise RuntimeError("When using --title, provide exactly one --title per --audio.")
    track_titles = display_track_titles(
        [{"title": title, "duration_seconds": 0} for title in raw_titles]
    )
    lyrics_items = resolve_lyrics_items(len(audio_paths), lyrics=args.lyrics or [], lyrics_files=args.lyrics_file or [])
    style_items = resolve_style_items(len(audio_paths), styles=args.style or [])
    if not cover_path and not args.release_id and not args.allow_generated_draft_cover:
        raise RuntimeError(
            "auto-publish-single requires --cover when creating a new Single Release. "
            "Generate a final 16:9 cover image with only the large, readable lower-left channel-name brand label first, then pass --cover ABSOLUTE_FINAL_COVER_IMAGE_PATH."
        )
    if not thumbnail_path and not args.release_id and not args.allow_cover_as_thumbnail:
        raise RuntimeError(
            "auto-publish-single requires --thumbnail when creating a new Single Release. "
            "Generate a YouTube thumbnail with readable text first, then pass --thumbnail ABSOLUTE_THUMBNAIL_IMAGE_PATH."
        )
    if not args.release_id:
        require_pop_family_lyrics(
            lyrics_items=lyrics_items,
            context="auto-publish-single",
            concept_values=[
                args.release_title,
                raw_titles,
                args.description,
                args.prompt,
                args.style,
                args.tags,
                args.youtube_channel_title,
            ],
        )

    release = (
        get_release(client, args.release_id)
        if args.release_id
        else create_single_release(
            client,
            args.release_title or file_stem(audio_paths[0]),
            description=args.description or "Automatic private single release created by OpenClaw.",
        )
    )
    if release["workspace_mode"] != "single_track_video":
        raise RuntimeError("auto-publish-single requires a Single Release, not a Playlist Release.")
    require_reupload_confirmation(args, release, action="auto-publish-single")
    if release.get("tracks"):
        raise RuntimeError(
            "auto-publish-single requires an empty Single Release because it publishes one final song. "
            "Run without --release-id, or create a fresh Single Release for this Suno output."
        )
    if not cover_path and not release_has_uploaded_cover(release) and not args.allow_generated_draft_cover:
        raise RuntimeError(
            "auto-publish-single requires a final 16:9 cover image before YouTube upload. "
            "Pass --cover ABSOLUTE_FINAL_COVER_IMAGE_PATH, or upload a final cover to the release first."
        )
    if not thumbnail_path and not release_has_uploaded_thumbnail(release) and not args.allow_cover_as_thumbnail:
        raise RuntimeError(
            "auto-publish-single requires a YouTube thumbnail image before YouTube upload. "
            "Pass --thumbnail ABSOLUTE_THUMBNAIL_IMAGE_PATH, or upload a final thumbnail to the release first."
        )
    require_pop_family_lyrics(
        lyrics_items=lyrics_items,
        context="auto-publish-single",
        concept_values=[
            release.get("title"),
            raw_titles,
            args.release_title,
            args.description,
            args.prompt,
            args.style,
            args.tags,
            args.youtube_channel_title,
        ],
    )

    if loop_video_path:
        content_type = mimetypes.guess_type(str(loop_video_path))[0] or "video/mp4"
        with loop_video_path.open("rb") as handle:
            release = request_json(
                client,
                "POST",
                f"/playlists/{release['id']}/loop-video/upload",
                data={
                    "actor": args.actor,
                    "smooth_loop": str(not args.hard_loop_video).lower(),
                },
                files={"loop_video_file": (loop_video_path.name, handle, content_type)},
            )

    uploaded_tracks = []
    for audio_path, track_title, lyrics, style in zip(audio_paths, track_titles, lyrics_items, style_items):
        try:
            track = upload_audio_file_to_release(
                client,
                release_id=release["id"],
                audio_path=audio_path,
                title=track_title,
                prompt=args.prompt,
                tags=args.tags,
                lyrics=lyrics,
                style=style,
                cover_path=None,
                dispatch_review=False,
            )
            approved = approve_track_to_release(
                client,
                track_id=track["id"],
                release_id=release["id"],
                actor=args.actor,
                rationale="Auto-approved for private single publishing explicitly requested by the human.",
            )
        except Exception as exc:  # noqa: BLE001
            notify_slack(
                client,
                upload_failure_notice(
                    release=release,
                    failures=[{"title": track_title, "audio_path": str(audio_path), "error": str(exc)}],
                    uploaded_count=0,
                    action="auto-publish-single",
                ),
            )
            raise
        uploaded_tracks.append(
            {
                "id": approved["id"],
                "title": approved["title"],
                "status": approved["status"],
                "duration_seconds": approved["duration_seconds"],
                "lyrics_present": bool((approved.get("metadata_json") or {}).get("lyrics")),
                "style": (approved.get("metadata_json") or {}).get("style") or "",
                "style_present": bool((approved.get("metadata_json") or {}).get("style")),
            }
        )

    release = request_json(
        client,
        "POST",
        f"/playlists/{release['id']}/render-audio",
        json={"actor": args.actor},
    )
    release = wait_for_release(
        client,
        release["id"],
        stage="single audio render",
        timeout_seconds=args.wait_timeout_seconds,
        poll_seconds=args.poll_seconds,
        predicate=lambda item: bool(item.get("output_audio_path")),
    )

    if cover_path:
        content_type = mimetypes.guess_type(str(cover_path))[0] or "image/png"
        with cover_path.open("rb") as handle:
            release = request_json(
                client,
                "POST",
                f"/playlists/{release['id']}/cover/upload",
                data={"actor": args.actor},
                files={"cover_file": (cover_path.name, handle, content_type)},
            )
    elif release_has_uploaded_cover(release):
        release = get_release(client, release["id"])
    elif args.allow_generated_draft_cover:
        release = request_json(
            client,
            "POST",
            f"/playlists/{release['id']}/cover/generate",
            json={"actor": args.actor, "regenerate": False},
        )
    else:
        raise RuntimeError("Final cover image is required before cover approval.")

    if thumbnail_path:
        content_type = mimetypes.guess_type(str(thumbnail_path))[0] or "image/png"
        with thumbnail_path.open("rb") as handle:
            release = request_json(
                client,
                "POST",
                f"/playlists/{release['id']}/thumbnail/upload",
                data={"actor": args.actor},
                files={"thumbnail_file": (thumbnail_path.name, handle, content_type)},
            )
    elif release_has_uploaded_thumbnail(release):
        release = get_release(client, release["id"])
    elif args.allow_cover_as_thumbnail:
        release = get_release(client, release["id"])
    else:
        raise RuntimeError("Final YouTube thumbnail image is required before cover approval.")

    release = request_json(
        client,
        "POST",
        f"/playlists/{release['id']}/cover/approve",
        json={
            "actor": args.actor,
            "approved": True,
            "note": "Auto-approved cover for private single publishing.",
        },
    )
    release = request_json(
        client,
        "POST",
        f"/playlists/{release['id']}/video/render",
        json={"actor": args.actor},
    )
    release = wait_for_release(
        client,
        release["id"],
        stage="single video render",
        timeout_seconds=args.wait_timeout_seconds,
        poll_seconds=args.poll_seconds,
        predicate=lambda item: bool(item.get("output_video_path")) and bool(item.get("youtube_title")),
    )

    if not release.get("youtube_title") or not release.get("youtube_description"):
        release = request_json(
            client,
            "POST",
            f"/playlists/{release['id']}/metadata/generate",
            json={"actor": args.actor},
        )
    release = approve_generated_metadata(client, release=release, actor=args.actor)

    youtube_channel_title = infer_youtube_channel_title(args)
    channel_id = resolve_youtube_channel_id(
        client,
        title=youtube_channel_title,
        channel_id=args.youtube_channel_id,
    )
    release = request_json(
        client,
        "POST",
        f"/playlists/{release['id']}/approve-publish",
        json={
            "actor": args.actor,
            "youtube_channel_id": channel_id,
            "note": f"Auto-publish private single to {youtube_channel_title}.",
        },
    )
    release = wait_for_release(
        client,
        release["id"],
        stage="YouTube private single upload",
        timeout_seconds=args.wait_timeout_seconds,
        poll_seconds=args.poll_seconds,
        predicate=lambda item: bool(item.get("youtube_video_id")) or item.get("workflow_state") == "ready_for_youtube_auth",
    )

    return {
        "ok": True,
        "action": "auto-publish-single",
        "release": {
            "id": release["id"],
            "title": release["title"],
            "workflow_state": release["workflow_state"],
            "actual_duration_seconds": release["actual_duration_seconds"],
            "output_audio_path": release.get("output_audio_path"),
            "output_video_path": release.get("output_video_path"),
            "loop_video_path": release.get("loop_video_path"),
            "youtube_thumbnail_path": release.get("youtube_thumbnail_path"),
            "youtube_title": release.get("youtube_title"),
            "youtube_video_id": release.get("youtube_video_id"),
            "youtube_channel_id": channel_id,
            "youtube_channel_title": youtube_channel_title,
        },
        "uploaded_tracks": uploaded_tracks,
        "privacy": "private (from AIMP_YOUTUBE_PRIVACY_STATUS)",
        "next": "Listen to the private YouTube upload. If it is good, change visibility to Public in YouTube Studio.",
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


def upload_thumbnail(client: httpx.Client, args: argparse.Namespace) -> dict[str, Any]:
    release = resolve_release(client, release_id=args.release_id, release_title=args.release_title)
    release_id = release["id"]
    thumbnail_path = resolve_thumbnail_path(args.thumbnail)
    if not thumbnail_path:
        raise RuntimeError("Use --thumbnail.")

    content_type = mimetypes.guess_type(str(thumbnail_path))[0] or "image/png"
    with thumbnail_path.open("rb") as handle:
        release = request_json(
            client,
            "POST",
            f"/playlists/{release_id}/thumbnail/upload",
            data={"actor": args.actor},
            files={"thumbnail_file": (thumbnail_path.name, handle, content_type)},
        )
    return {
        "ok": True,
        "action": "upload-thumbnail",
        "release": {
            "id": release["id"],
            "title": release["title"],
            "workflow_state": release["workflow_state"],
            "youtube_thumbnail_path": release.get("youtube_thumbnail_path"),
            "youtube_thumbnail_source": release.get("youtube_thumbnail_source"),
        },
        "next": "Use this thumbnail for the next YouTube publish/re-upload.",
    }


def upload_loop_video(client: httpx.Client, args: argparse.Namespace) -> dict[str, Any]:
    release = resolve_release(client, release_id=args.release_id, release_title=args.release_title)
    release_id = release["id"]
    loop_video_path = resolve_loop_video_path(args.loop_video)
    if not loop_video_path:
        raise RuntimeError("Use --loop-video.")

    content_type = mimetypes.guess_type(str(loop_video_path))[0] or "video/mp4"
    with loop_video_path.open("rb") as handle:
        release = request_json(
            client,
            "POST",
            f"/playlists/{release_id}/loop-video/upload",
            data={
                "actor": args.actor,
                "smooth_loop": str(not args.hard_loop).lower(),
            },
            files={"loop_video_file": (loop_video_path.name, handle, content_type)},
        )
    return {
        "ok": True,
        "action": "upload-loop-video",
        "release": {
            "id": release["id"],
            "title": release["title"],
            "workflow_state": release["workflow_state"],
            "loop_video_path": release.get("loop_video_path"),
            "loop_video_source": release.get("loop_video_source"),
            "loop_video_smooth": release.get("loop_video_smooth"),
        },
        "next": "This visual clip will be used during the next video render.",
    }


def metadata_context(client: httpx.Client, args: argparse.Namespace) -> dict[str, Any]:
    release = resolve_release(client, release_id=args.release_id, release_title=args.release_title)
    timeline = release_timeline(release)
    total_seconds = sum(item["duration_seconds"] for item in timeline)
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
            "youtube_localizations": release.get("youtube_localizations") or {},
        },
        "timeline": timeline,
        "timestamp_lines": timestamp_lines,
        "display_timestamp_lines": display_timestamp_lines,
        "total_seconds": total_seconds,
        "total_duration": format_timestamp(total_seconds, force_hours=total_seconds >= 3600),
        "instructions": (
            "Use timestamps and row order exactly. Prefer display_timestamp_lines for metadata so A/B suffixes are not shown. "
            "If total_seconds is 3600 or greater, keep every timestamp in HH:MM:SS form such as 00:00:00 and 01:02:03 so YouTube can link chapters past one hour. "
            "If you rewrite a displayed title, keep its timestamp fixed. "
            "For Japan/J-pop/Tokyo Daydream Radio releases, write localized timeline rows as follows: Korean description uses Japanese title plus Korean translation in parentheses, Japanese description uses Japanese title only, English description uses English translated title only, and Spanish description uses Spanish translated title only. "
            "Use each track's style field as Suno generation context for later thumbnails, loop video, and metadata. "
            "Write tags as comma-separated plain tags without # symbols. "
            "For Tokyo/J-pop/Japan releases, write Korean, Japanese, English, and Spanish title/description versions and pass them to approve-metadata."
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


def read_optional_text(value: str, file_value: str, *, label: str) -> str:
    if file_value:
        path = Path(file_value).expanduser().resolve()
        if not path.exists():
            raise RuntimeError(f"{label} file does not exist: {path}")
        if not path.is_file():
            raise RuntimeError(f"{label} path is not a file: {path}")
        return path.read_text(encoding="utf-8").strip()
    return (value or "").strip()


def metadata_localizations_from_args(args: argparse.Namespace, *, title: str, description: str) -> dict[str, dict[str, str]]:
    localizations = {
        "ko": {
            "title": read_optional_text(args.ko_title, "", label="Korean title") or title,
            "description": read_optional_text(args.ko_description, args.ko_description_file, label="Korean description")
            or description,
        },
        "ja": {
            "title": read_optional_text(args.ja_title, "", label="Japanese title"),
            "description": read_optional_text(args.ja_description, args.ja_description_file, label="Japanese description"),
        },
        "en": {
            "title": read_optional_text(args.en_title, "", label="English title"),
            "description": read_optional_text(args.en_description, args.en_description_file, label="English description"),
        },
        "es": {
            "title": read_optional_text(args.es_title, "", label="Spanish title"),
            "description": read_optional_text(args.es_description, args.es_description_file, label="Spanish description"),
        },
    }
    return {
        language: payload
        for language, payload in localizations.items()
        if payload["title"] and payload["description"]
    }


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
    localizations = metadata_localizations_from_args(args, title=title, description=description)

    release = request_json(
        client,
        "POST",
        f"/playlists/{release_id}/metadata/approve",
        json={
            "actor": args.actor,
            "title": title,
            "description": description,
            "tags": tags,
            "default_language": "ko",
            "localizations": localizations,
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
            "youtube_localizations": release.get("youtube_localizations") or {},
        },
        "next": "Human can choose Publish Channel and approve publish/re-upload in the web UI.",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Upload OpenClaw-generated music assets to the local AI Music app.")
    parser.add_argument("--api-base", default=None, help=f"API base URL. Default: {DEFAULT_API_BASE}")

    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list-releases", help="List visible releases and ids.")
    list_parser.set_defaults(func=list_releases)

    create_parser = subparsers.add_parser(
        "create-release",
        help="Create an empty Single or Playlist Release workspace before generating Suno audio.",
    )
    create_parser.add_argument("--release-title", required=True, help="Release/workspace title to create before Suno generation.")
    create_parser.add_argument(
        "--workspace-mode",
        choices=["single", "single_track_video", "playlist"],
        required=True,
        help="Use single for one standalone song candidate set, or playlist for a multi-song mix.",
    )
    create_parser.add_argument("--target-seconds", type=int, default=3600, help="Playlist target duration. Ignored for single releases.")
    create_parser.add_argument("--description", default="", help="Short concept description for the release.")
    create_parser.set_defaults(func=create_release)

    context_parser = subparsers.add_parser(
        "metadata-context",
        help="Return release context and final-order timestamps for OpenClaw YouTube metadata writing.",
    )
    context_parser.add_argument("--release-id", default="", help="Existing release id.")
    context_parser.add_argument("--release-title", default="", help="Existing release title.")
    context_parser.set_defaults(func=metadata_context)

    profile_parser = subparsers.add_parser(
        "channel-profile",
        help="Infer the target YouTube channel and return the channel-specific OpenClaw visual profile doc.",
    )
    profile_parser.add_argument("--release-title", default="", help="Release title or human request title.")
    profile_parser.add_argument("--description", default="", help="Release concept description.")
    profile_parser.add_argument("--prompt", default="", help="Suno/image/video prompt or concept.")
    profile_parser.add_argument("--tags", default="", help="Comma-separated concept tags.")
    profile_parser.add_argument(
        "--youtube-channel-title",
        default="",
        help="Explicit target channel title. Overrides automatic inference and visual routing.",
    )
    profile_parser.set_defaults(func=channel_profile)

    audio_parser = subparsers.add_parser("upload-audio", help="Upload an audio file to an existing release or new single.")
    audio_parser.add_argument("--audio", required=True, help="Path to generated audio file.")
    audio_parser.add_argument("--title", default="", help="Track title. Defaults to audio filename stem.")
    audio_parser.add_argument("--prompt", default="", help="Prompt or generation note.")
    audio_parser.add_argument("--style", default="", help="Suno style/settings used to generate this audio.")
    audio_parser.add_argument("--tags", default="", help="Comma-separated tags.")
    audio_parser.add_argument("--lyrics", default="", help="Optional lyrics or content notes for this audio. Empty is allowed.")
    audio_parser.add_argument("--lyrics-file", default="", help="Optional UTF-8 text file containing lyrics or content notes.")
    audio_parser.add_argument("--cover", default="", help="Optional cover image file to upload with this audio.")
    audio_parser.add_argument("--new-single", action="store_true", help="Create a new Single Release from this audio.")
    audio_parser.add_argument("--release-id", default="", help="Existing release id.")
    audio_parser.add_argument("--release-title", default="", help="Existing release title, or new release title with --new-single.")
    audio_parser.add_argument("--pending-review", action="store_true", help="For Playlist Releases only, skip the default auto-approve behavior.")
    audio_parser.add_argument("--max-track-seconds", type=int, default=DEFAULT_MAX_PLAYLIST_TRACK_SECONDS, help="Maximum auto-approved Playlist Release track length. Default: 260.")
    audio_parser.add_argument("--allow-long-track", action="store_true", help="Allow a playlist track longer than --max-track-seconds. Use only with explicit human approval.")
    audio_parser.add_argument("--actor", default="openclaw", help="Actor name recorded when playlist uploads are auto-approved.")
    audio_parser.set_defaults(func=upload_audio)

    candidates_parser = subparsers.add_parser(
        "upload-single-candidates",
        help="Create a Single Release and upload one or two Suno candidate tracks.",
    )
    candidates_parser.add_argument("--audio", action="append", required=True, help="Candidate audio path. Repeat up to two times.")
    candidates_parser.add_argument("--title", action="append", default=[], help="Candidate title. Repeat in the same order as --audio.")
    candidates_parser.add_argument("--cover", action="append", default=[], help="Optional candidate cover path. Repeat once for a shared cover or once per --audio.")
    candidates_parser.add_argument("--release-id", default="", help="Existing Single Release workspace id created before Suno generation.")
    candidates_parser.add_argument("--release-title", default="", help="Single release title. Defaults to first audio filename stem.")
    candidates_parser.add_argument("--prompt", default="", help="Prompt or generation note shared by the candidates.")
    candidates_parser.add_argument("--style", action="append", default=[], help="Suno style/settings. Repeat once per --audio, or provide one shared value.")
    candidates_parser.add_argument("--tags", default="", help="Comma-separated tags shared by the candidates.")
    candidates_parser.add_argument("--lyrics", action="append", default=[], help="Optional lyrics/content notes. Repeat once per --audio, or provide one shared value.")
    candidates_parser.add_argument("--lyrics-file", action="append", default=[], help="Optional UTF-8 lyrics file. Repeat once per --audio, or provide one shared file.")
    candidates_parser.set_defaults(func=upload_single_candidates)

    auto_playlist_parser = subparsers.add_parser(
        "auto-publish-playlist",
        help="Upload playlist tracks, auto-approve them, render, generate metadata, and private-publish to YouTube.",
    )
    auto_playlist_parser.add_argument("--audio", action="append", required=True, help="Generated playlist audio path. Repeat for every track.")
    auto_playlist_parser.add_argument("--title", action="append", default=[], help="Optional track title. Repeat in the same order as --audio.")
    auto_playlist_parser.add_argument("--cover", default="", help="Required final 16:9 playlist cover image unless an uploaded final cover already exists on the release.")
    auto_playlist_parser.add_argument("--thumbnail", default="", help="Required YouTube thumbnail image with readable title/use-case text unless an uploaded thumbnail already exists on the release.")
    auto_playlist_parser.add_argument("--loop-video", default="", help="Optional 8 second visual clip generated by Dreamina/Seedance for the rendered video.")
    auto_playlist_parser.add_argument("--hard-loop-video", action="store_true", help="Use direct clip reuse instead of the default smoothed render.")
    auto_playlist_parser.add_argument("--allow-generated-draft-cover", action="store_true", help="Explicitly allow the app's placeholder draft cover. Do not use unless the human accepts it.")
    auto_playlist_parser.add_argument("--allow-cover-as-thumbnail", action="store_true", help="Reuse the video cover as the YouTube thumbnail. Do not use unless the human accepts one image for both roles.")
    auto_playlist_parser.add_argument("--release-id", default="", help="Existing Playlist Release id. If omitted, a new release is created.")
    auto_playlist_parser.add_argument("--release-title", default="", help="New Playlist Release title. Defaults to first audio filename stem.")
    auto_playlist_parser.add_argument("--description", default="", help="Release description used for metadata generation.")
    auto_playlist_parser.add_argument("--prompt", default="", help="Prompt or generation note shared by uploaded tracks.")
    auto_playlist_parser.add_argument("--style", action="append", default=[], help="Suno style/settings. Repeat once per --audio, or provide one shared value.")
    auto_playlist_parser.add_argument("--tags", default="", help="Comma-separated tags shared by uploaded tracks.")
    auto_playlist_parser.add_argument("--lyrics", action="append", default=[], help="Optional lyrics/content notes. Repeat once per --audio, or provide one shared value.")
    auto_playlist_parser.add_argument("--lyrics-file", action="append", default=[], help="Optional UTF-8 lyrics file. Repeat once per --audio, or provide one shared file.")
    auto_playlist_parser.add_argument("--target-seconds", type=int, default=3600, help="Playlist target duration. Default: 3600.")
    auto_playlist_parser.add_argument("--max-track-seconds", type=int, default=DEFAULT_MAX_PLAYLIST_TRACK_SECONDS, help="Maximum allowed duration for each playlist track. Default: 260.")
    auto_playlist_parser.add_argument("--allow-long-track", action="store_true", help="Allow playlist tracks longer than --max-track-seconds. Use only with explicit human approval.")
    auto_playlist_parser.add_argument("--youtube-channel-title", default="", help="Connected YouTube channel title. Default: inferred from release; J-pop/Tokyo/city-pop releases use Tokyo Daydream Radio, otherwise Soft Hour Radio.")
    auto_playlist_parser.add_argument("--youtube-channel-id", default="", help="Optional explicit YouTube channel id. Overrides title lookup.")
    auto_playlist_parser.add_argument("--force-under-target", action="store_true", help="Allow publish even if approved duration is under target.")
    auto_playlist_parser.add_argument("--allow-reupload", action="store_true", help="Allow uploading an existing release that already has a YouTube video id. Use only when the human explicitly requests a duplicate/replacement upload.")
    auto_playlist_parser.add_argument("--actor", default="openclaw:auto-playlist", help="Actor name recorded in histories.")
    auto_playlist_parser.add_argument("--wait-timeout-seconds", type=int, default=21600, help="Max wait per long stage. Default: 6 hours.")
    auto_playlist_parser.add_argument("--poll-seconds", type=float, default=10.0, help="Polling interval while waiting for background jobs.")
    auto_playlist_parser.set_defaults(func=auto_publish_playlist)

    auto_single_parser = subparsers.add_parser(
        "auto-publish-single",
        help="Upload one final single, auto-approve, render, generate metadata, and private-publish to YouTube.",
    )
    auto_single_parser.add_argument("--audio", action="append", required=True, help="Generated single audio path. Use exactly one; run this command again for a second good Suno output.")
    auto_single_parser.add_argument("--title", action="append", default=[], help="Optional track title. Repeat in the same order as --audio.")
    auto_single_parser.add_argument("--cover", default="", help="Required final 16:9 cover image with only the large, readable lower-left channel-name brand label unless an uploaded final cover already exists on the release.")
    auto_single_parser.add_argument("--thumbnail", default="", help="Required YouTube thumbnail image with readable text unless an uploaded thumbnail already exists on the release.")
    auto_single_parser.add_argument("--loop-video", default="", help="Optional 8 second visual clip generated by Dreamina/Seedance for the rendered video.")
    auto_single_parser.add_argument("--hard-loop-video", action="store_true", help="Use direct clip reuse instead of the default smoothed render.")
    auto_single_parser.add_argument("--allow-generated-draft-cover", action="store_true", help="Explicitly allow the app's placeholder draft cover. Do not use unless the human accepts it.")
    auto_single_parser.add_argument("--allow-cover-as-thumbnail", action="store_true", help="Reuse the video cover as the YouTube thumbnail. Do not use unless the human accepts one image for both roles.")
    auto_single_parser.add_argument("--release-id", default="", help="Existing Single Release id. If omitted, a new release is created.")
    auto_single_parser.add_argument("--release-title", default="", help="New Single Release title. Defaults to first audio filename stem.")
    auto_single_parser.add_argument("--description", default="", help="Release description used for metadata generation.")
    auto_single_parser.add_argument("--prompt", default="", help="Prompt or generation note shared by uploaded tracks.")
    auto_single_parser.add_argument("--style", action="append", default=[], help="Suno style/settings for this final song. Provide one value.")
    auto_single_parser.add_argument("--tags", default="", help="Comma-separated tags shared by uploaded tracks.")
    auto_single_parser.add_argument("--lyrics", action="append", default=[], help="Optional lyrics/content notes. Repeat once per --audio, or provide one shared value.")
    auto_single_parser.add_argument("--lyrics-file", action="append", default=[], help="Optional UTF-8 lyrics file. Repeat once per --audio, or provide one shared file.")
    auto_single_parser.add_argument("--youtube-channel-title", default="", help="Connected YouTube channel title. Default: inferred from release; J-pop/Tokyo/city-pop releases use Tokyo Daydream Radio, otherwise Soft Hour Radio.")
    auto_single_parser.add_argument("--youtube-channel-id", default="", help="Optional explicit YouTube channel id. Overrides title lookup.")
    auto_single_parser.add_argument("--allow-reupload", action="store_true", help="Allow uploading an existing release that already has a YouTube video id. Use only when the human explicitly requests a duplicate/replacement upload.")
    auto_single_parser.add_argument("--actor", default="openclaw:auto-single", help="Actor name recorded in histories.")
    auto_single_parser.add_argument("--wait-timeout-seconds", type=int, default=21600, help="Max wait per long stage. Default: 6 hours.")
    auto_single_parser.add_argument("--poll-seconds", type=float, default=10.0, help="Polling interval while waiting for background jobs.")
    auto_single_parser.set_defaults(func=auto_publish_single)

    cover_parser = subparsers.add_parser("upload-cover", help="Upload a 16:9 cover image for a release.")
    cover_parser.add_argument("--cover", required=True, help="Path to cover image file: jpg, png, or webp.")
    cover_parser.add_argument("--release-id", default="", help="Existing release id.")
    cover_parser.add_argument("--release-title", default="", help="Existing release title.")
    cover_parser.add_argument("--actor", default="openclaw", help="Actor name recorded in release history.")
    cover_parser.set_defaults(func=upload_cover)

    thumbnail_parser = subparsers.add_parser("upload-thumbnail", help="Upload a YouTube thumbnail image for a release.")
    thumbnail_parser.add_argument("--thumbnail", required=True, help="Path to YouTube thumbnail image: jpg, png, or webp.")
    thumbnail_parser.add_argument("--release-id", default="", help="Existing release id.")
    thumbnail_parser.add_argument("--release-title", default="", help="Existing release title.")
    thumbnail_parser.add_argument("--actor", default="openclaw", help="Actor name recorded in release history.")
    thumbnail_parser.set_defaults(func=upload_thumbnail)

    loop_video_parser = subparsers.add_parser("upload-loop-video", help="Upload a short visual loop clip for a release.")
    loop_video_parser.add_argument("--loop-video", required=True, help="Path to an 8 second loop video: mp4, mov, m4v, or webm.")
    loop_video_parser.add_argument("--release-id", default="", help="Existing release id.")
    loop_video_parser.add_argument("--release-title", default="", help="Existing release title.")
    loop_video_parser.add_argument("--hard-loop", action="store_true", help="Use direct clip reuse instead of the default smoothed render.")
    loop_video_parser.add_argument("--actor", default="openclaw", help="Actor name recorded in release history.")
    loop_video_parser.set_defaults(func=upload_loop_video)

    slack_notify_parser = subparsers.add_parser(
        "slack-notify",
        help="Post a plain Slack progress/failure message through the app's configured Slack bot.",
    )
    slack_notify_parser.add_argument("--text", required=True, help="Slack message text to post.")
    slack_notify_parser.add_argument("--channel-id", default="", help="Optional Slack channel id override.")
    slack_notify_parser.add_argument("--team-id", default="", help="Optional Slack team id for installed workspace lookup.")
    slack_notify_parser.set_defaults(func=slack_notify_command)

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
    metadata_parser.add_argument("--ko-title", default="", help="Korean localized YouTube title. Defaults to --title.")
    metadata_parser.add_argument("--ko-description", default="", help="Korean localized YouTube description. Defaults to --description.")
    metadata_parser.add_argument("--ko-description-file", default="", help="UTF-8 Korean description file.")
    metadata_parser.add_argument("--ja-title", default="", help="Japanese localized YouTube title.")
    metadata_parser.add_argument("--ja-description", default="", help="Japanese localized YouTube description. Prefer --ja-description-file for multiline copy.")
    metadata_parser.add_argument("--ja-description-file", default="", help="UTF-8 Japanese description file.")
    metadata_parser.add_argument("--en-title", default="", help="English localized YouTube title.")
    metadata_parser.add_argument("--en-description", default="", help="English localized YouTube description. Prefer --en-description-file for multiline copy.")
    metadata_parser.add_argument("--en-description-file", default="", help="UTF-8 English description file.")
    metadata_parser.add_argument("--es-title", default="", help="Spanish localized YouTube title.")
    metadata_parser.add_argument("--es-description", default="", help="Spanish localized YouTube description. Prefer --es-description-file for multiline copy.")
    metadata_parser.add_argument("--es-description-file", default="", help="UTF-8 Spanish description file.")
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
