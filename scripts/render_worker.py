#!/usr/bin/env python3
"""External video render worker.

The main app owns DB state and YouTube publishing. This worker only claims
queued video-render jobs, downloads render assets, renders the MP4 locally, and
uploads the final MP4 back with resumable chunks.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import socket
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

from app.config import Settings
from app.services.playlist_builder import FFMpegPlaylistBuilder
from app.utils.lyric_subtitles import build_word_aligned_line_lyric_cues

DEFAULT_API_BASE = "http://127.0.0.1:8000/api"
COMPLETED_JOB_MARKER = ".render-worker-uploaded.json"
ACTIVE_JOB_MARKER = ".render-worker-active.json"


def infer_worker_profile(worker_id: str, hostname: str) -> str:
    explicit = os.environ.get("AIMP_RENDER_WORKER_PROFILE", "").strip().lower()
    if explicit:
        return explicit
    haystack = f"{worker_id} {hostname} {os.uname().machine}".lower()
    if any(token in haystack for token in ("desktop", "gpu", "rtx", "workstation", "home")):
        return "desktop"
    if any(token in haystack for token in ("oracle", "instance", "oci", "arm", "aarch64")):
        return "oracle"
    return "standard"


def max_render_height_for_profile(profile: str) -> int:
    explicit = os.environ.get("AIMP_RENDER_WORKER_MAX_RENDER_HEIGHT", "").strip()
    if explicit.isdigit():
        return int(explicit)
    if profile == "desktop":
        return 1440
    if profile == "oracle":
        return 720
    return 1080


def normalize_api_base(value: str | None) -> str:
    base = (value or os.environ.get("AIMP_RENDER_WORKER_API_BASE") or os.environ.get("AIMP_LOCAL_API_BASE") or DEFAULT_API_BASE).rstrip("/")
    if not base.endswith("/api"):
        base = f"{base}/api"
    return base


def auth_headers(token: str) -> dict[str, str]:
    return {"X-Render-Worker-Token": token}


def print_json(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2), flush=True)


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def disk_usage_target(path: Path) -> Path:
    candidate = path
    while not candidate.exists() and candidate != candidate.parent:
        candidate = candidate.parent
    return candidate


def disk_usage_percent(path: Path) -> float:
    usage = shutil.disk_usage(disk_usage_target(path))
    if usage.total <= 0:
        return 0.0
    return usage.used / usage.total * 100.0


def directory_size_bytes(path: Path) -> int:
    total = 0
    for item in path.rglob("*"):
        if item.is_file():
            try:
                total += item.stat().st_size
            except OSError:
                continue
    return total


def latest_mtime(path: Path) -> float:
    latest = 0.0
    try:
        latest = path.stat().st_mtime
    except OSError:
        return latest
    for item in path.rglob("*"):
        try:
            latest = max(latest, item.stat().st_mtime)
        except OSError:
            continue
    return latest


def format_duration(seconds: Any) -> str:
    if seconds is None:
        return "--:--"
    try:
        remaining = max(int(float(seconds)), 0)
    except (TypeError, ValueError):
        return "--:--"
    hours, remainder = divmod(remaining, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def progress_bar(percent: Any, *, width: int = 32) -> str:
    try:
        value = max(0.0, min(float(percent), 100.0))
    except (TypeError, ValueError):
        value = 0.0
    filled = int(round((value / 100.0) * width))
    return f"[{'#' * filled}{'-' * (width - filled)}]"


def print_progress_line(progress: dict[str, Any]) -> None:
    percent = progress.get("upload_percent")
    if percent is None:
        percent = progress.get("percent")
    stage = str(progress.get("stage") or "video_render")
    status = str(progress.get("status") or "running")
    eta = format_duration(progress.get("eta_seconds"))
    processed = progress.get("processed_seconds")
    total = progress.get("total_seconds")
    seconds = ""
    if processed is not None and total is not None:
        seconds = f" {format_duration(processed)}/{format_duration(total)}"
    try:
        percent_value = float(percent)
        percent_text = f"{percent_value:5.1f}%"
    except (TypeError, ValueError):
        percent_value = 0.0
        percent_text = "  0.0%"
    print(
        f"\r{progress_bar(percent)} {percent_text} {stage}:{status}{seconds} ETA {eta}",
        end="",
        flush=True,
    )
    if status == "end" or percent_value >= 100:
        print(flush=True)


def request_json(client: httpx.Client, method: str, url: str, *, token: str, **kwargs) -> Any:
    headers = dict(kwargs.pop("headers", {}) or {})
    headers.update(auth_headers(token))
    response = client.request(method, url, headers=headers, **kwargs)
    try:
        payload = response.json()
    except ValueError:
        payload = response.text
    if response.is_error:
        detail = payload.get("detail") if isinstance(payload, dict) else payload
        raise RuntimeError(f"{response.status_code} {response.reason_phrase}: {detail}")
    return payload


def client_timeout_from_seconds(value: float) -> httpx.Timeout:
    seconds = float(value)
    if seconds <= 0:
        return httpx.Timeout(None)
    return httpx.Timeout(timeout=seconds, connect=min(seconds, 30.0))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_asset(client: httpx.Client, *, token: str, asset: dict[str, Any], destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    expected_size = int(asset.get("size_bytes") or 0)
    if destination.exists() and expected_size > 0 and destination.stat().st_size == expected_size:
        return destination

    temp_path = destination.with_suffix(destination.suffix + ".download")
    with client.stream("GET", asset["url"], headers=auth_headers(token)) as response:
        if response.is_error:
            raise RuntimeError(f"download failed: {response.status_code} {response.text}")
        with temp_path.open("wb") as handle:
            for chunk in response.iter_bytes():
                if chunk:
                    handle.write(chunk)
    if expected_size > 0 and temp_path.stat().st_size != expected_size:
        raise RuntimeError(
            f"downloaded size mismatch for {asset.get('filename')}: {temp_path.stat().st_size} != {expected_size}"
        )
    temp_path.replace(destination)
    return destination


def mark_job_uploaded(job: dict[str, Any], video_path: Path) -> None:
    marker_path = video_path.parent / COMPLETED_JOB_MARKER
    payload = {
        "job_id": job.get("id"),
        "playlist_id": job.get("playlist_id"),
        "title": job.get("title"),
        "video_path": str(video_path),
        "size_bytes": video_path.stat().st_size if video_path.exists() else None,
        "uploaded_to_webapp_at": utcnow_iso(),
    }
    marker_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    clear_job_active(video_path.parent)


def mark_job_active(job: dict[str, Any], job_dir: Path, worker_id: str) -> None:
    marker_path = job_dir / ACTIVE_JOB_MARKER
    payload = {
        "job_id": job.get("id"),
        "playlist_id": job.get("playlist_id"),
        "title": job.get("title"),
        "worker_id": worker_id,
        "active_at": utcnow_iso(),
    }
    marker_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def clear_job_active(job_dir: Path) -> None:
    try:
        (job_dir / ACTIVE_JOB_MARKER).unlink(missing_ok=True)
    except OSError:
        pass


def uploaded_job_cache_candidates(cache_dir: Path, *, orphan_age_hours: float = 24.0) -> list[dict[str, Any]]:
    jobs_dir = cache_dir / "jobs"
    if not jobs_dir.exists():
        return []

    candidates: list[dict[str, Any]] = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max(float(orphan_age_hours), 0.0))
    for job_dir in jobs_dir.iterdir():
        if not job_dir.is_dir():
            continue
        marker_path = job_dir / COMPLETED_JOB_MARKER
        marker: dict[str, Any] = {}
        completed_at: datetime
        cleanup_reason = "uploaded_marker"
        uploaded_to_webapp_at: str | None = None

        if marker_path.exists():
            try:
                marker = json.loads(marker_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                marker = {}
            try:
                marker_mtime = marker_path.stat().st_mtime
            except OSError:
                marker_mtime = time.time()
            completed_at = parse_datetime(marker.get("uploaded_to_webapp_at")) or datetime.fromtimestamp(
                marker_mtime,
                tz=timezone.utc,
            )
            uploaded_to_webapp_at = completed_at.isoformat()
        else:
            if orphan_age_hours <= 0:
                continue
            newest_mtime = latest_mtime(job_dir)
            completed_at = datetime.fromtimestamp(newest_mtime, tz=timezone.utc)
            if completed_at > cutoff:
                continue
            cleanup_reason = "stale_unmarked_cache"

        try:
            active_marker = json.loads((job_dir / ACTIVE_JOB_MARKER).read_text(encoding="utf-8"))
        except OSError:
            active_marker = {}
        except ValueError:
            active_marker = {}

        candidates.append(
            {
                "job_id": marker.get("job_id") or job_dir.name,
                "playlist_id": marker.get("playlist_id"),
                "title": marker.get("title"),
                "path": job_dir,
                "completed_at": completed_at,
                "cleanup_reason": cleanup_reason,
                "uploaded_to_webapp_at": uploaded_to_webapp_at,
                "active_marker": active_marker,
                "size_bytes": directory_size_bytes(job_dir),
            }
        )
    return sorted(candidates, key=lambda item: item["completed_at"])


def cleanup_uploaded_job_cache(
    cache_dir: Path,
    threshold_percent: float,
    *,
    orphan_age_hours: float = 24.0,
) -> dict[str, Any]:
    threshold = max(0.0, min(float(threshold_percent), 100.0))
    before_percent = disk_usage_percent(cache_dir)
    result: dict[str, Any] = {
        "ok": True,
        "threshold_percent": threshold,
        "orphan_age_hours": max(float(orphan_age_hours), 0.0),
        "disk_usage_before_percent": round(before_percent, 2),
        "disk_usage_after_percent": round(before_percent, 2),
        "deleted_count": 0,
        "deleted_bytes": 0,
        "deleted": [],
        "errors": [],
        "skipped": False,
    }
    if before_percent <= threshold:
        result["skipped"] = True
        result["reason"] = "below_threshold"
        return result

    for candidate in uploaded_job_cache_candidates(cache_dir, orphan_age_hours=orphan_age_hours):
        current_percent = disk_usage_percent(cache_dir)
        if current_percent <= threshold:
            break
        try:
            shutil.rmtree(candidate["path"])
        except OSError as exc:
            result["errors"].append(
                {
                    "job_id": candidate["job_id"],
                    "path": str(candidate["path"]),
                    "error": str(exc),
                }
            )
            continue
        result["deleted_count"] += 1
        result["deleted_bytes"] += int(candidate["size_bytes"] or 0)
        result["deleted"].append(
            {
                "job_id": candidate["job_id"],
                "playlist_id": candidate["playlist_id"],
                "title": candidate["title"],
                "path": str(candidate["path"]),
                "size_bytes": candidate["size_bytes"],
                "cleanup_reason": candidate["cleanup_reason"],
                "last_modified_at": candidate["completed_at"].isoformat(),
                "uploaded_to_webapp_at": candidate["uploaded_to_webapp_at"],
            }
        )

    after_percent = disk_usage_percent(cache_dir)
    result["disk_usage_after_percent"] = round(after_percent, 2)
    return result


def maybe_cleanup_uploaded_job_cache(args: argparse.Namespace) -> dict[str, Any] | None:
    cleanup = cleanup_uploaded_job_cache(
        args.cache_dir,
        args.cache_cleanup_threshold_percent,
        orphan_age_hours=args.cache_cleanup_orphan_age_hours,
    )
    if cleanup["deleted_count"] or cleanup["errors"]:
        print_json({"ok": cleanup["ok"], "cache_cleanup": cleanup})
    return cleanup


def post_progress(
    client: httpx.Client,
    *,
    token: str,
    job_id: str,
    worker_id: str,
    progress: dict[str, Any],
    timeout_seconds: float,
    message: str = "",
) -> None:
    try:
        request_json(
            client,
            "POST",
            f"/render-worker/jobs/{job_id}/progress",
            token=token,
            json={"worker_id": worker_id, "progress": progress, "message": message},
            timeout=max(float(timeout_seconds), 1.0),
        )
    except Exception as exc:  # noqa: BLE001
        print(f"progress update failed: {exc}", file=sys.stderr, flush=True)


def render_job(
    client: httpx.Client,
    *,
    token: str,
    worker_id: str,
    job: dict[str, Any],
    cache_dir: Path,
    ffmpeg_binary: str,
    progress_timeout_seconds: float,
) -> Path:
    job_id = job["id"]
    job_dir = cache_dir / "jobs" / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    mark_job_active(job, job_dir, worker_id)

    assets = job["assets"]
    audio_path = download_asset(
        client,
        token=token,
        asset=assets["audio"],
        destination=job_dir / assets["audio"]["filename"],
    )
    cover_path = download_asset(
        client,
        token=token,
        asset=assets["cover"],
        destination=job_dir / assets["cover"]["filename"],
    )
    loop_video_path = None
    if "loop_video" in assets:
        loop_video_path = download_asset(
            client,
            token=token,
            asset=assets["loop_video"],
            destination=job_dir / assets["loop_video"]["filename"],
        )

    settings = Settings(
        storage_root=cache_dir / "storage",
        ffmpeg_binary=ffmpeg_binary,
    )
    settings.ensure_storage_dirs()
    builder = FFMpegPlaylistBuilder(settings)
    render = job["render"]
    output_path = job_dir / render["output_filename"]
    total_duration_seconds = render.get("total_duration_seconds")
    spectrum_style = render.get("video_spectrum_overlay_style") or "bars"
    render_resolution = render.get("video_render_resolution") or "720p"
    lyric_overlay_style = render.get("video_lyrics_overlay_style") or "auto"
    lyric_cues = render.get("lyric_cues") or []
    if (
        render.get("video_lyrics_overlay_enabled")
        and not lyric_cues
        and str(render.get("video_lyrics_alignment_mode") or "whisper").lower().replace("-", "_") == "whisper"
    ):
        print("Building line lyric cues with faster-whisper alignment...", flush=True)
        lyric_cues = build_word_aligned_line_lyric_cues(
            list(render.get("lyric_tracks") or []),
            list(render.get("rendered_timeline") or []),
            audio_path=audio_path,
            model_size=str(render.get("video_lyrics_alignment_model") or "tiny"),
            language=str(render.get("video_lyrics_alignment_language") or "").strip() or None,
            min_score=float(render.get("video_lyrics_alignment_min_score") or 0.34),
            max_end_seconds=total_duration_seconds,
        )
        print(f"Built {len(lyric_cues)} aligned lyric cues.", flush=True)

    def callback(progress: dict[str, Any]) -> None:
        post_progress(
            client,
            token=token,
            job_id=job_id,
            worker_id=worker_id,
            progress=progress,
            timeout_seconds=progress_timeout_seconds,
        )
        print_progress_line(progress)

    if render["mode"] == "loop_video":
        if loop_video_path is None:
            raise RuntimeError("loop video render was requested but no loop video asset was provided")
        builder.build_looped_video(
            loop_video_path,
            audio_path,
            output_path,
            smooth_loop=bool(render.get("smooth_loop", True)),
            render_resolution=render_resolution,
            spectrum_overlay_style=spectrum_style,
            lyric_cues=lyric_cues,
            lyric_overlay_style=lyric_overlay_style,
            progress_callback=callback,
            total_duration_seconds=total_duration_seconds,
        )
    else:
        builder.build_video(
            audio_path,
            cover_path,
            output_path,
            render_resolution=render_resolution,
            spectrum_overlay_style=spectrum_style,
            lyric_cues=lyric_cues,
            lyric_overlay_style=lyric_overlay_style,
            progress_callback=callback,
            total_duration_seconds=total_duration_seconds,
        )
    return output_path


def upload_rendered_video(
    client: httpx.Client,
    *,
    token: str,
    worker_id: str,
    job_id: str,
    video_path: Path,
    chunk_size: int,
) -> None:
    total = video_path.stat().st_size
    print(f"\nPreparing upload checksum for {video_path.name} ({total:,} bytes)...", flush=True)
    checksum = sha256_file(video_path)
    chunk_size = max(int(chunk_size), 1024 * 1024)

    while True:
        status_payload = request_json(
            client,
            "GET",
            f"/render-worker/jobs/{job_id}/upload-status",
            token=token,
        )
        offset = int(status_payload.get("received_bytes") or 0)
        if offset > total:
            raise RuntimeError(f"remote upload offset {offset} is larger than local file size {total}")
        if offset == total:
            break

        with video_path.open("rb") as handle:
            handle.seek(offset)
            chunk = handle.read(chunk_size)
        if not chunk:
            break
        start = offset
        end = offset + len(chunk) - 1
        headers = {
            "Content-Range": f"bytes {start}-{end}/{total}",
            "Content-Type": "application/octet-stream",
        }
        try:
            request_json(
                client,
                "PUT",
                f"/render-worker/jobs/{job_id}/upload",
                token=token,
                content=chunk,
                headers=headers,
            )
        except RuntimeError as exc:
            print(f"chunk upload retrying after error: {exc}", file=sys.stderr, flush=True)
            time.sleep(3)
        uploaded = end + 1
        print_progress_line(
            {
                "stage": "video_upload",
                "status": "uploading",
                "upload_percent": round((uploaded / total) * 100, 1) if total else 100.0,
                "eta_seconds": None,
            }
        )

    request_json(
        client,
        "POST",
        f"/render-worker/jobs/{job_id}/complete",
        token=token,
        json={
            "worker_id": worker_id,
            "size_bytes": total,
            "sha256": checksum,
            "message": "External video render completed and uploaded.",
        },
    )


def run_once(client: httpx.Client, args: argparse.Namespace) -> bool:
    hostname = socket.gethostname()
    worker_profile = args.worker_profile or infer_worker_profile(args.worker_id, hostname)
    max_render_height = max_render_height_for_profile(worker_profile)
    claim = request_json(
        client,
        "POST",
        "/render-worker/jobs/claim",
        token=args.token,
        json={
            "worker_id": args.worker_id,
            "hostname": hostname,
            "capabilities": {
                "ffmpeg": args.ffmpeg,
                "chunk_size_bytes": args.chunk_size_bytes,
                "worker_profile": worker_profile,
                "max_render_height": max_render_height,
            },
        },
    )
    job = claim.get("job")
    if not job:
        print_json({"ok": True, "worked": False, "message": "No queued video render jobs."})
        return False

    print_json(
        {
            "ok": True,
            "worked": True,
            "claimed_job": {
                "id": job["id"],
                "playlist_id": job["playlist_id"],
                "title": job["title"],
                "mode": job["render"]["mode"],
                "spectrum": job["render"].get("video_spectrum_overlay_style"),
                "render_resolution": job["render"].get("video_render_resolution"),
                "worker_profile": worker_profile,
            },
        }
    )
    rendered = render_job(
        client,
        token=args.token,
        worker_id=args.worker_id,
        job=job,
        cache_dir=args.cache_dir,
        ffmpeg_binary=args.ffmpeg,
        progress_timeout_seconds=args.progress_timeout_seconds,
    )
    upload_rendered_video(
        client,
        token=args.token,
        worker_id=args.worker_id,
        job_id=job["id"],
        video_path=rendered,
        chunk_size=args.chunk_size_bytes,
    )
    mark_job_uploaded(job, rendered)
    cache_cleanup = cleanup_uploaded_job_cache(
        args.cache_dir,
        args.cache_cleanup_threshold_percent,
        orphan_age_hours=args.cache_cleanup_orphan_age_hours,
    )
    print_json(
        {
            "ok": True,
            "completed_job_id": job["id"],
            "output": str(rendered),
            "cache_cleanup": cache_cleanup,
        }
    )
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run an external AI Music video render worker.")
    parser.add_argument("--api-base", default=normalize_api_base(None), help="App API base URL, e.g. https://host/api.")
    parser.add_argument("--token", default=os.environ.get("AIMP_RENDER_WORKER_SHARED_TOKEN", ""), help="Render worker shared token.")
    parser.add_argument("--worker-id", default=f"{socket.gethostname()}-{os.getpid()}", help="Stable worker id. Reuse it to resume a claimed job.")
    parser.add_argument("--cache-dir", type=Path, default=Path(".render-worker"), help="Local cache/work directory.")
    parser.add_argument("--ffmpeg", default=os.environ.get("AIMP_FFMPEG_BINARY", "ffmpeg"), help="ffmpeg executable.")
    parser.add_argument(
        "--worker-profile",
        default=os.environ.get("AIMP_RENDER_WORKER_PROFILE", ""),
        help="Render worker profile. Default auto-detects from worker id / hostname; desktop prefers 1080p/2k jobs, oracle prefers 720p jobs.",
    )
    parser.add_argument("--chunk-size-bytes", type=int, default=int(os.environ.get("AIMP_RENDER_WORKER_UPLOAD_CHUNK_BYTES", 8 * 1024 * 1024)))
    parser.add_argument(
        "--progress-timeout-seconds",
        type=float,
        default=float(os.environ.get("AIMP_RENDER_WORKER_PROGRESS_TIMEOUT_SECONDS", 10)),
        help="Maximum seconds to wait for best-effort progress updates before continuing the render.",
    )
    parser.add_argument(
        "--api-timeout-seconds",
        type=float,
        default=float(os.environ.get("AIMP_RENDER_WORKER_API_TIMEOUT_SECONDS", 300)),
        help="Maximum idle seconds for render-worker API calls such as claim, asset download, upload-status, upload chunks, and complete. Use 0 for no timeout.",
    )
    parser.add_argument(
        "--cache-cleanup-threshold-percent",
        type=float,
        default=float(os.environ.get("AIMP_RENDER_WORKER_CACHE_CLEANUP_DISK_THRESHOLD_PERCENT", 50)),
        help="Delete successfully uploaded job cache directories, oldest first, when cache disk usage is above this percent.",
    )
    parser.add_argument(
        "--cache-cleanup-orphan-age-hours",
        type=float,
        default=float(os.environ.get("AIMP_RENDER_WORKER_CACHE_CLEANUP_ORPHAN_AGE_HOURS", 24)),
        help="Also delete unmarked worker job cache directories older than this many hours when disk cleanup runs.",
    )
    parser.add_argument("--poll-seconds", type=float, default=20.0, help="Seconds to wait between polls.")
    parser.add_argument("--once", action="store_true", help="Process at most one job and exit.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.api_base = normalize_api_base(args.api_base)
    if not args.token:
        raise SystemExit("AIMP_RENDER_WORKER_SHARED_TOKEN or --token is required.")
    timeout = client_timeout_from_seconds(args.api_timeout_seconds)
    with httpx.Client(base_url=args.api_base, timeout=timeout, follow_redirects=True) as client:
        while True:
            try:
                maybe_cleanup_uploaded_job_cache(args)
                worked = run_once(client, args)
            except KeyboardInterrupt:
                raise
            except Exception as exc:  # noqa: BLE001
                print_json({"ok": False, "error": str(exc)})
                worked = False
            if args.once:
                return 0
            if not worked:
                time.sleep(max(float(args.poll_seconds), 1.0))


if __name__ == "__main__":
    raise SystemExit(main())
