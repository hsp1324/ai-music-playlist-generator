#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import socket
import sys
import time
from pathlib import Path
from typing import Any

import httpx

from app.config import Settings
from app.services.playlist_builder import FFMpegPlaylistBuilder


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Poll the AI Music app for queued video render jobs and render them on this machine."
    )
    parser.add_argument(
        "--api-base",
        default=os.environ.get("AIMP_LOCAL_API_BASE") or "http://127.0.0.1:8000/api",
        help="AI Music API base URL, including /api.",
    )
    parser.add_argument(
        "--worker-id",
        default=os.environ.get("AIMP_RENDER_WORKER_ID") or f"{socket.gethostname()}-{os.getpid()}",
        help="Stable worker name shown in render progress.",
    )
    parser.add_argument(
        "--work-dir",
        default=os.environ.get("AIMP_RENDER_WORKER_DIR") or "storage/render-worker",
        help="Local directory for downloaded assets and temporary rendered output.",
    )
    parser.add_argument(
        "--poll-seconds",
        type=float,
        default=float(os.environ.get("AIMP_RENDER_WORKER_POLL_SECONDS") or 30),
        help="Seconds to wait between empty queue polls.",
    )
    parser.add_argument(
        "--heartbeat-seconds",
        type=float,
        default=float(os.environ.get("AIMP_RENDER_WORKER_HEARTBEAT_SECONDS") or 10),
        help="Minimum seconds between progress heartbeat posts.",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("AIMP_RENDER_WORKER_SHARED_TOKEN") or "",
        help="Shared render-worker token. Prefer the env var instead of a shell history value.",
    )
    parser.add_argument("--once", action="store_true", help="Poll once and exit after one job or an empty queue.")
    return parser.parse_args()


def api_url(api_base: str, path: str) -> str:
    return f"{api_base.rstrip('/')}/{path.lstrip('/')}"


def token_headers(token: str) -> dict[str, str]:
    if not token:
        return {}
    return {"X-AIMP-Render-Worker-Token": token}


def download_asset(
    client: httpx.Client,
    *,
    api_base: str,
    token: str,
    lease_token: str,
    asset: dict[str, Any],
    destination: Path,
) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with client.stream(
        "GET",
        api_url(api_base, asset["path"]),
        params={"lease_token": lease_token},
        headers=token_headers(token),
    ) as response:
        response.raise_for_status()
        with destination.open("wb") as handle:
            for chunk in response.iter_bytes():
                if chunk:
                    handle.write(chunk)
    if not destination.exists() or destination.stat().st_size == 0:
        raise RuntimeError(f"Downloaded render asset is empty: {destination}")
    return destination


def post_heartbeat(
    client: httpx.Client,
    *,
    api_base: str,
    token: str,
    job_id: str,
    lease_token: str,
    worker_id: str,
    progress: dict[str, Any] | None = None,
    message: str | None = None,
) -> None:
    response = client.post(
        api_url(api_base, f"render-worker/jobs/{job_id}/heartbeat"),
        headers=token_headers(token),
        json={
            "lease_token": lease_token,
            "worker_id": worker_id,
            "progress": progress or {},
            "message": message,
        },
    )
    response.raise_for_status()


def post_failure(
    client: httpx.Client,
    *,
    api_base: str,
    token: str,
    job_id: str,
    lease_token: str,
    worker_id: str,
    error_text: str,
) -> None:
    response = client.post(
        api_url(api_base, f"render-worker/jobs/{job_id}/fail"),
        headers=token_headers(token),
        json={
            "lease_token": lease_token,
            "worker_id": worker_id,
            "error_text": error_text[:4000],
        },
    )
    response.raise_for_status()


def post_completion(
    client: httpx.Client,
    *,
    api_base: str,
    token: str,
    job_id: str,
    lease_token: str,
    worker_id: str,
    output_path: Path,
) -> dict[str, Any]:
    with output_path.open("rb") as handle:
        response = client.post(
            api_url(api_base, f"render-worker/jobs/{job_id}/complete"),
            headers=token_headers(token),
            data={"lease_token": lease_token, "worker_id": worker_id},
            files={"output_file": (output_path.name, handle, "video/mp4")},
            timeout=None,
        )
    response.raise_for_status()
    return response.json()


def claim_job(client: httpx.Client, *, api_base: str, token: str, worker_id: str) -> dict[str, Any] | None:
    response = client.post(
        api_url(api_base, "render-worker/claim"),
        headers=token_headers(token),
        json={
            "worker_id": worker_id,
            "capabilities": ["ffmpeg", "loop-video", "spectrum-overlay"],
        },
    )
    response.raise_for_status()
    payload = response.json()
    return payload if payload.get("has_job") else None


def render_job(client: httpx.Client, args: argparse.Namespace, manifest: dict[str, Any]) -> None:
    job_id = manifest["job_id"]
    lease_token = manifest["lease_token"]
    work_dir = Path(args.work_dir) / job_id
    assets_dir = work_dir / "assets"
    output_dir = work_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    post_heartbeat(
        client,
        api_base=args.api_base,
        token=args.token,
        job_id=job_id,
        lease_token=lease_token,
        worker_id=args.worker_id,
        message=f"External render worker {args.worker_id} is downloading assets.",
    )
    assets = manifest["assets"]
    audio_path = download_asset(
        client,
        api_base=args.api_base,
        token=args.token,
        lease_token=lease_token,
        asset=assets["audio"],
        destination=assets_dir / assets["audio"]["filename"],
    )
    cover_path = download_asset(
        client,
        api_base=args.api_base,
        token=args.token,
        lease_token=lease_token,
        asset=assets["cover"],
        destination=assets_dir / assets["cover"]["filename"],
    )
    loop_video_path = None
    if "loop_video" in assets:
        loop_video_path = download_asset(
            client,
            api_base=args.api_base,
            token=args.token,
            lease_token=lease_token,
            asset=assets["loop_video"],
            destination=assets_dir / assets["loop_video"]["filename"],
        )

    settings = Settings(storage_root=work_dir / "local-storage")
    settings.ensure_storage_dirs()
    builder = FFMpegPlaylistBuilder(settings)
    render = manifest["render"]
    output_path = output_dir / render["output_filename"]
    last_heartbeat = 0.0

    def progress_callback(progress: dict[str, Any]) -> None:
        nonlocal last_heartbeat
        now = time.monotonic()
        if progress.get("status") != "end" and now - last_heartbeat < args.heartbeat_seconds:
            return
        last_heartbeat = now
        post_heartbeat(
            client,
            api_base=args.api_base,
            token=args.token,
            job_id=job_id,
            lease_token=lease_token,
            worker_id=args.worker_id,
            progress=progress,
        )

    post_heartbeat(
        client,
        api_base=args.api_base,
        token=args.token,
        job_id=job_id,
        lease_token=lease_token,
        worker_id=args.worker_id,
        message=f"External render worker {args.worker_id} started ffmpeg.",
    )
    if loop_video_path:
        builder.build_looped_video(
            loop_video_path,
            audio_path,
            output_path,
            smooth_loop=bool(render.get("smooth_loop", True)),
            spectrum_overlay_style=render.get("spectrum_overlay_style"),
            total_duration_seconds=render.get("total_duration_seconds"),
            progress_callback=progress_callback,
        )
    else:
        builder.build_video(
            audio_path,
            cover_path,
            output_path,
            spectrum_overlay_style=render.get("spectrum_overlay_style"),
            total_duration_seconds=render.get("total_duration_seconds"),
            progress_callback=progress_callback,
        )

    result = post_completion(
        client,
        api_base=args.api_base,
        token=args.token,
        job_id=job_id,
        lease_token=lease_token,
        worker_id=args.worker_id,
        output_path=output_path,
    )
    print(f"completed {job_id}: {result}", flush=True)


def main() -> int:
    args = parse_args()
    Path(args.work_dir).mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=None) as client:
        while True:
            try:
                manifest = claim_job(
                    client,
                    api_base=args.api_base,
                    token=args.token,
                    worker_id=args.worker_id,
                )
                if not manifest:
                    print("no queued video render jobs", flush=True)
                    if args.once:
                        return 0
                    time.sleep(max(args.poll_seconds, 1))
                    continue
                print(
                    f"claimed {manifest['job_id']} for playlist {manifest['playlist_id']}: {manifest['title']}",
                    flush=True,
                )
                try:
                    render_job(client, args, manifest)
                except Exception as exc:  # noqa: BLE001
                    print(f"render failed for {manifest['job_id']}: {exc}", file=sys.stderr, flush=True)
                    try:
                        post_failure(
                            client,
                            api_base=args.api_base,
                            token=args.token,
                            job_id=manifest["job_id"],
                            lease_token=manifest["lease_token"],
                            worker_id=args.worker_id,
                            error_text=str(exc),
                        )
                    except Exception as failure_exc:  # noqa: BLE001
                        print(f"failed to report render failure: {failure_exc}", file=sys.stderr, flush=True)
                    if args.once:
                        return 1
            except KeyboardInterrupt:
                return 130
            except Exception as exc:  # noqa: BLE001
                print(f"worker poll error: {exc}", file=sys.stderr, flush=True)
                if args.once:
                    return 1
                time.sleep(max(args.poll_seconds, 1))


if __name__ == "__main__":
    raise SystemExit(main())
