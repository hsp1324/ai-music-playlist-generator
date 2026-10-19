import asyncio
import subprocess
import threading

import httpx
import pytest

from app.config import get_settings
from app.db import SessionLocal
from app.main import create_app
from app.models.enums import JobStatus, JobType
from app.models.job import Job
from app.models.playlist import Playlist
from app.routes import render_worker as render_worker_routes
from app.routes import tracks as track_routes


@pytest.mark.parametrize("slow_stage", ["media", "database"])
def test_slow_track_intake_does_not_block_health(tmp_path, monkeypatch, slow_stage: str) -> None:
    monkeypatch.setenv("AIMP_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    monkeypatch.setenv("AIMP_STORAGE_ROOT", str(tmp_path / "storage"))
    monkeypatch.setenv("AIMP_WORKER_AUTOSTART", "false")
    monkeypatch.setenv("AIMP_CACHE_REMOTE_AUDIO_ON_INTAKE", "false")
    get_settings.cache_clear()
    app = create_app()
    entered = threading.Event()
    release = threading.Event()

    def wait_for_release():
        entered.set()
        if not release.wait(5):
            raise AssertionError("test intake stage was not released")

    if slow_stage == "media":
        def slow_media_probe(_audio_path, _duration):
            wait_for_release()
            return 12

        monkeypatch.setattr(track_routes, "_resolve_audio_duration_seconds", slow_media_probe)
    else:
        original_create = track_routes._create_track_record

        def slow_database_save(db, payload):
            wait_for_release()
            return original_create(db, payload)

        monkeypatch.setattr(track_routes, "_create_track_record", slow_database_save)

    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            upload = asyncio.create_task(
                client.post("/api/tracks", json={"title": "Responsive intake", "prompt": "test"})
            )
            try:
                assert await asyncio.to_thread(entered.wait, 3)
                health = await asyncio.wait_for(client.get("/health"), timeout=2)
                assert health.status_code == 200
            finally:
                release.set()
            created = await asyncio.wait_for(upload, timeout=5)
            assert created.status_code == 201

    try:
        asyncio.run(scenario())
    finally:
        release.set()
        get_settings.cache_clear()


def test_audio_probe_has_bounded_runtime(monkeypatch) -> None:
    def timed_out(*_args, **kwargs):
        assert kwargs["timeout"] == track_routes.FFPROBE_TIMEOUT_SECONDS
        raise subprocess.TimeoutExpired(cmd="ffprobe", timeout=kwargs["timeout"])

    monkeypatch.setattr(track_routes.subprocess, "run", timed_out)
    assert track_routes._probe_duration_seconds("/tmp/test-audio.mp3") is None


def test_slow_render_upload_disk_check_does_not_block_health(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AIMP_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    monkeypatch.setenv("AIMP_STORAGE_ROOT", str(tmp_path / "storage"))
    monkeypatch.setenv("AIMP_WORKER_AUTOSTART", "false")
    get_settings.cache_clear()
    app = create_app()
    app.state.settings.render_worker_shared_token = "test-render-token"
    with SessionLocal() as db:
        playlist = Playlist(title="Render upload responsiveness", metadata_json={})
        db.add(playlist)
        db.flush()
        job = Job(type=JobType.build_video, status=JobStatus.running, playlist_id=playlist.id)
        db.add(job)
        db.commit()
        job_id = job.id

    entered = threading.Event()
    release = threading.Event()
    original_prepare = render_worker_routes._prepare_render_upload_chunk

    def slow_disk_check(*args):
        entered.set()
        if not release.wait(5):
            raise AssertionError("test disk check was not released")
        return original_prepare(*args)

    monkeypatch.setattr(render_worker_routes, "_prepare_render_upload_chunk", slow_disk_check)

    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            upload = asyncio.create_task(
                client.put(
                    f"/api/render-worker/jobs/{job_id}/upload",
                    headers={
                        "X-Render-Worker-Token": "test-render-token",
                        "Content-Range": "bytes 0-2/3",
                    },
                    content=b"abc",
                )
            )
            try:
                assert await asyncio.to_thread(entered.wait, 3)
                health = await asyncio.wait_for(client.get("/health"), timeout=2)
                assert health.status_code == 200
            finally:
                release.set()
            uploaded = await asyncio.wait_for(upload, timeout=5)
            assert uploaded.status_code == 200
            assert uploaded.json()["complete"] is True

    try:
        asyncio.run(scenario())
    finally:
        release.set()
        get_settings.cache_clear()
