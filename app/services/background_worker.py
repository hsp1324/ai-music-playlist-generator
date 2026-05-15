from __future__ import annotations

import asyncio
import inspect
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.orm import Session, selectinload

from app.config import Settings
from app.db import SessionLocal
from app.models.enums import JobStatus, JobType, PlaylistStatus, TrackStatus
from app.models.job import Job
from app.models.playlist import Playlist, PlaylistItem
from app.models.track import Track
from app.utils.youtube_localizations import (
    ensure_playlist_localization_title_prefix,
    ensure_playlist_title_prefix,
    normalize_youtube_language,
    normalize_youtube_localizations,
)
from app.utils.youtube_metadata_state import apply_generated_youtube_metadata, has_youtube_metadata
from app.utils.openclaw_slack_loop import (
    get_auto_loop_control_state,
    post_backlog_queue_request,
    post_next_playlist_request,
    record_auto_loop_upload,
)
from app.utils.ops_notifications import notify_youtube_publish_completed
from app.utils.local_video_cleanup import cleanup_public_uploaded_local_videos
from app.utils.timeline import build_rendered_timeline_snapshot
from app.workflows.openclaw_runtime import (
    build_openclaw_backlog_summary,
    evaluate_openclaw_backlog_scheduler,
    get_openclaw_lock_status,
    record_openclaw_backlog_scheduler_request,
)


def _utcnow():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)


def _playlist_track_ids(playlist: Playlist) -> list[str]:
    return [
        item.track_id
        for item in sorted(playlist.items, key=lambda item: item.order_index)
        if item.track_id
    ]


def _track_timeline_dict(track: Track) -> dict:
    meta = track.metadata_json or {}
    return {
        "id": track.id,
        "title": track.title,
        "duration_seconds": track.duration_seconds,
        "lyrics": str(meta.get("lyrics") or ""),
        "style": str(meta.get("style") or ""),
        "prompt": track.prompt or "",
        "tags": meta.get("tags") or "",
    }


def _rendered_snapshot_matches_current_tracks(playlist: Playlist, key: str) -> bool:
    rendered_track_ids = (playlist.metadata_json or {}).get(key)
    if not rendered_track_ids:
        return True
    return list(rendered_track_ids) == _playlist_track_ids(playlist)


def _is_long_video_verification_upload_error(error_text: str, playlist: Playlist) -> bool:
    meta = dict(playlist.metadata_json or {})
    duration_seconds = max(
        int(playlist.actual_duration_seconds or 0),
        int(float(meta.get("rendered_duration_seconds") or 0)),
    )
    if duration_seconds < 14 * 60:
        return False
    normalized = error_text.lower()
    duration_markers = (
        "15 minute",
        "15-minute",
        "fifteen minute",
        "longer than 15",
        "longer than fifteen",
        "too long",
        "video duration",
        "duration too long",
        "long video",
        "long videos",
        "uploadlimitexceeded",
        "upload limit",
        "exceeded the number of videos",
    )
    verification_markers = (
        "verify",
        "verified",
        "verification",
        "phone",
        "account",
        "longer than 15",
        "15 minute",
        "15-minute",
        "uploadlimitexceeded",
        "upload limit",
    )
    return any(marker in normalized for marker in duration_markers) and any(
        marker in normalized for marker in verification_markers
    )


@dataclass
class WorkerLoopState:
    running: bool = False
    last_error: str | None = None


class BackgroundJobWorker:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.services = None
        self._thread: threading.Thread | None = None
        self._upload_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._state = WorkerLoopState()
        self._upload_state = WorkerLoopState()
        self._last_openclaw_backlog_scheduler_check = 0.0
        self._last_local_video_cleanup_check = 0.0

    def bind_services(self, services) -> None:
        self.services = services

    def start(self) -> None:
        if not self.settings.worker_autostart or self._thread is not None or self._upload_thread is not None:
            return
        if self.services is None:
            raise RuntimeError("Background worker is not bound to services.")

        self.recover_interrupted_jobs()
        self._stop_event.clear()
        render_job_types = [JobType.build_playlist, JobType.sync_slack]
        if self.settings.video_render_execution_mode != "external":
            render_job_types.insert(1, JobType.build_video)
        self._thread = threading.Thread(
            target=self._run_loop,
            kwargs={
                "job_types": tuple(render_job_types),
                "state": self._state,
                "run_backlog_scheduler": True,
            },
            name="aimp-background-worker",
            daemon=True,
        )
        self._upload_thread = threading.Thread(
            target=self._run_loop,
            kwargs={
                "job_types": (JobType.upload_youtube,),
                "state": self._upload_state,
                "run_backlog_scheduler": False,
            },
            name="aimp-upload-worker",
            daemon=True,
        )
        self._thread.start()
        self._upload_thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None
        if self._upload_thread is not None:
            self._upload_thread.join(timeout=5)
            self._upload_thread = None

    def process_pending_once(self, job_types: tuple[JobType, ...] | None = None) -> bool:
        job_id = self._claim_next_job_id(job_types)
        if not job_id:
            return False
        self._process_job(job_id)
        return True

    def recover_interrupted_jobs(self) -> dict[str, int]:
        counts = {
            "requeued": 0,
            "failed_uploads": 0,
            "completed_uploads": 0,
        }
        with SessionLocal() as db:
            jobs = db.scalars(
                select(Job)
                .options(selectinload(Job.playlist))
                .where(
                    Job.status == JobStatus.running,
                    Job.type.in_([JobType.build_playlist, JobType.build_video, JobType.upload_youtube, JobType.sync_slack]),
                )
            ).all()
            now = _utcnow()
            for job in jobs:
                result = dict(job.result_json or {})
                result["interrupted_worker_recovered_at"] = now.isoformat()
                result["interrupted_worker_previous_source"] = job.source

                if job.type == JobType.upload_youtube:
                    playlist = job.playlist
                    if playlist and playlist.youtube_video_id:
                        job.status = JobStatus.succeeded
                        job.finished_at = now
                        result["interrupted_worker_resolution"] = "already_uploaded"
                        counts["completed_uploads"] += 1
                    else:
                        message = (
                            "Background YouTube upload was interrupted before completion. "
                            "Retry publish to start a fresh upload."
                        )
                        job.status = JobStatus.failed
                        job.finished_at = now
                        job.error_text = message
                        result["interrupted_worker_resolution"] = "failed_requires_retry"
                        counts["failed_uploads"] += 1
                        if playlist:
                            meta = dict(playlist.metadata_json or {})
                            playlist.status = PlaylistStatus.ready
                            meta["workflow_state"] = "youtube_upload_failed"
                            meta["note"] = message
                            meta["youtube_upload_error"] = message
                            meta["publish_approved"] = False
                            playlist.metadata_json = meta
                            db.add(playlist)
                elif (
                    job.type == JobType.build_video
                    and self.settings.video_render_execution_mode == "external"
                    and isinstance(result.get("external_render_worker"), dict)
                ):
                    result["interrupted_worker_resolution"] = "kept_external_render_claim"
                    db.add(job)
                    continue
                else:
                    job.status = JobStatus.queued
                    job.started_at = None
                    job.finished_at = None
                    job.error_text = None
                    result["interrupted_worker_resolution"] = "requeued"
                    counts["requeued"] += 1
                    if job.playlist:
                        meta = dict(job.playlist.metadata_json or {})
                        if job.type == JobType.build_playlist:
                            meta["workflow_state"] = "render_queued"
                            meta["note"] = "Interrupted audio render was requeued after worker restart."
                            meta["audio_render_progress"] = {
                                **dict(meta.get("audio_render_progress") or {}),
                                "stage": "audio_render",
                                "status": "queued",
                                "message": meta["note"],
                                "updated_at": now.isoformat(),
                            }
                            job.playlist.status = PlaylistStatus.building
                        elif job.type == JobType.build_video:
                            meta["workflow_state"] = "video_queued"
                            meta["note"] = "Interrupted video render was requeued after worker restart."
                            meta["video_render_progress"] = {
                                **dict(meta.get("video_render_progress") or {}),
                                "stage": "video_render",
                                "status": "queued",
                                "message": meta["note"],
                                "updated_at": now.isoformat(),
                            }
                            job.playlist.status = PlaylistStatus.building
                        job.playlist.metadata_json = meta
                        db.add(job.playlist)

                job.result_json = result
                db.add(job)
            if any(counts.values()):
                db.commit()
        return counts

    def _run_loop(
        self,
        *,
        job_types: tuple[JobType, ...],
        state: WorkerLoopState,
        run_backlog_scheduler: bool,
    ) -> None:
        state.running = True
        while not self._stop_event.is_set():
            try:
                processed = self.process_pending_once(job_types)
                state.last_error = None
            except Exception as exc:  # noqa: BLE001
                state.last_error = str(exc)
                processed = False
            if run_backlog_scheduler:
                try:
                    self._maybe_cleanup_public_uploaded_local_videos()
                except Exception as exc:  # noqa: BLE001
                    state.last_error = str(exc)
            if not processed and run_backlog_scheduler:
                self._maybe_request_openclaw_backlog()
            if not processed:
                self._stop_event.wait(self.settings.worker_poll_interval_seconds)
        state.running = False

    def _maybe_cleanup_public_uploaded_local_videos(self) -> None:
        if self.services is None or not self.settings.local_video_cleanup_enabled:
            return
        now = time.monotonic()
        interval = max(float(self.settings.local_video_cleanup_interval_seconds or 0), 30.0)
        if now - self._last_local_video_cleanup_check < interval:
            return
        self._last_local_video_cleanup_check = now
        with SessionLocal() as db:
            cleanup_public_uploaded_local_videos(db, self.settings)

    def _maybe_request_openclaw_backlog(self) -> None:
        if not self.settings.openclaw_backlog_scheduler_enabled or self.services is None:
            return
        now = time.monotonic()
        interval = max(float(self.settings.openclaw_backlog_scheduler_interval_seconds or 0), 30.0)
        if now - self._last_openclaw_backlog_scheduler_check < interval:
            return
        self._last_openclaw_backlog_scheduler_check = now

        with SessionLocal() as db:
            evaluation = evaluate_openclaw_backlog_scheduler(db, self.services)
            if not evaluation.get("should_request"):
                return
            try:
                result = asyncio.run(
                    post_backlog_queue_request(
                        db,
                        self.services,
                        reason=str(evaluation.get("reason") or "scheduler"),
                        backlog_summary=evaluation.get("summary"),
                    )
                )
            except Exception as exc:  # noqa: BLE001
                result = {"ok": False, "error": str(exc)}
            record_openclaw_backlog_scheduler_request(
                storage_root=self.settings.storage_root,
                result={
                    **evaluation,
                    "slack": {key: result.get(key) for key in ("ok", "channel", "ts", "error")},
                },
            )

    def _claim_next_job_id(self, job_types: tuple[JobType, ...] | None = None) -> str | None:
        with SessionLocal() as db:
            claimable_job_types = job_types or (
                JobType.build_playlist,
                JobType.build_video,
                JobType.upload_youtube,
                JobType.sync_slack,
            )
            if self.settings.video_render_execution_mode == "external":
                claimable_job_types = tuple(
                    job_type for job_type in claimable_job_types if job_type != JobType.build_video
                )
                if not claimable_job_types:
                    return None
            candidate_ids = db.scalars(
                select(Job.id)
                .where(
                    Job.status == JobStatus.queued,
                    Job.type.in_(claimable_job_types),
                )
                .order_by(Job.created_at.asc())
                .limit(10)
            ).all()
            for candidate_id in candidate_ids:
                result = db.execute(
                    update(Job)
                    .where(Job.id == candidate_id, Job.status == JobStatus.queued)
                    .values(status=JobStatus.running, started_at=_utcnow())
                )
                db.commit()
                if result.rowcount == 1:
                    return candidate_id
            return None

    def _process_job(self, job_id: str) -> None:
        post_commit_openclaw_request: dict | None = None
        with SessionLocal() as db:
            job = db.get(Job, job_id)
            if not job:
                return

            try:
                if job.type == JobType.build_playlist:
                    self._process_build_playlist_job(db, job)
                elif job.type == JobType.build_video:
                    self._process_build_video_job(db, job)
                elif job.type == JobType.upload_youtube:
                    self._process_publish_job(db, job)
                elif job.type == JobType.sync_slack:
                    self._process_sync_slack_job(db, job)
                else:
                    raise ValueError(f"Unsupported background job type: {job.type.value}")
                if job.type == JobType.upload_youtube:
                    post_commit_openclaw_request = dict(
                        (job.result_json or {}).get("post_commit_openclaw_request") or {}
                    ) or None
                job.status = JobStatus.succeeded
                job.finished_at = _utcnow()
                db.add(job)
                db.commit()
            except Exception as exc:  # noqa: BLE001
                self._mark_job_failed(db, job, str(exc))
                post_commit_openclaw_request = None
        if post_commit_openclaw_request:
            self._request_openclaw_for_publish_event(**post_commit_openclaw_request)

    def _process_build_playlist_job(self, db: Session, job: Job) -> None:
        playlist = db.scalars(
            select(Playlist)
            .options(selectinload(Playlist.items).selectinload(PlaylistItem.track))
            .where(Playlist.id == job.playlist_id)
        ).first()
        if not playlist:
            raise ValueError("Playlist not found for build job.")

        tracks = [
            item.track
            for item in sorted(playlist.items, key=lambda item: item.order_index)
            if item.track is not None
        ]
        if not tracks:
            raise ValueError("Playlist has no tracks to render.")

        meta = dict(playlist.metadata_json or {})
        meta["workflow_state"] = "rendering"
        meta["render_ready"] = False
        meta["note"] = f"Rendering audio for {len(tracks)} approved tracks."
        meta["audio_render_progress"] = {
            "stage": "audio_render",
            "progress_ratio": 0.0,
            "percent": 0.0,
            "processed_seconds": 0,
            "total_seconds": playlist.actual_duration_seconds,
            "message": meta["note"],
            "updated_at": _utcnow().isoformat(),
        }
        playlist.metadata_json = meta
        playlist.status = PlaylistStatus.building
        job.result_json = {
            **(job.result_json or {}),
            "playlist_id": playlist.id,
            "progress": meta["audio_render_progress"],
        }
        db.add(playlist)
        db.add(job)
        db.commit()
        db.refresh(playlist)

        missing = [
            track.id
            for track in tracks
            if not track.audio_path
            or track.audio_path.startswith(("http://", "https://"))
            or not Path(track.audio_path).exists()
        ]
        if missing:
            raise ValueError(f"Playlist contains non-renderable tracks: {', '.join(missing)}")

        rendered_track_ids = [track.id for track in tracks]
        rendered_track_dicts = [_track_timeline_dict(track) for track in tracks]
        rendered_track_durations = []
        rendered_track_duration_sources = []
        for track in tracks:
            probed_duration = self.services.playlist_builder._probe_media_duration(Path(track.audio_path))
            if probed_duration > 0:
                rendered_track_durations.append(probed_duration)
                rendered_track_duration_sources.append("ffprobe")
            else:
                rendered_track_durations.append(float(track.duration_seconds or 0))
                rendered_track_duration_sources.append("track_duration")
        rendered_timeline = build_rendered_timeline_snapshot(
            rendered_track_dicts,
            rendered_track_durations,
            rendered_track_duration_sources,
        )
        output_path = Path(self.settings.playlists_dir) / f"{playlist.id}.mp3"
        progress_callback = self._build_audio_progress_callback(db, job, playlist)
        rendered_path = self._call_builder_with_progress(
            self.services.playlist_builder.build_audio,
            tracks,
            output_path,
            progress_callback=progress_callback,
            total_duration_seconds=sum(rendered_track_durations),
        )
        db.expire_all()
        playlist = db.scalars(
            select(Playlist)
            .options(selectinload(Playlist.items).selectinload(PlaylistItem.track))
            .where(Playlist.id == job.playlist_id)
        ).first()
        if not playlist:
            raise ValueError("Playlist not found after audio render.")
        current_track_ids = _playlist_track_ids(playlist)
        if current_track_ids != rendered_track_ids:
            meta = dict(playlist.metadata_json or {})
            meta["render_ready"] = False
            meta["workflow_state"] = "render_queued"
            meta["note"] = "Track list changed while audio was rendering. Re-render queued with the current track order."
            meta["stale_audio_render"] = {
                "rendered_track_ids": rendered_track_ids,
                "current_track_ids": current_track_ids,
                "detected_at": _utcnow().isoformat(),
            }
            meta.pop("rendered_track_ids", None)
            meta.pop("rendered_track_count", None)
            meta.pop("rendered_duration_seconds", None)
            meta.pop("rendered_timeline", None)
            meta.pop("rendered_video_track_ids", None)
            meta.pop("rendered_video_track_count", None)
            playlist.output_audio_path = None
            playlist.output_video_path = None
            playlist.status = PlaylistStatus.building
            playlist.metadata_json = meta
            job.result_json = {
                **(job.result_json or {}),
                "playlist_id": playlist.id,
                "stale_output_audio_path": str(rendered_path),
                "requeued": True,
                "rendered_track_ids": rendered_track_ids,
                "current_track_ids": current_track_ids,
            }
            db.add(playlist)
            db.add(job)
            db.add(
                Job(
                    type=JobType.build_playlist,
                    status=JobStatus.queued,
                    source="system:stale-render-retry",
                    payload_json={
                        "playlist_id": playlist.id,
                        "trigger": "track-list-changed-during-render",
                    },
                    result_json={},
                    playlist=playlist,
                )
            )
            return

        playlist.output_audio_path = str(rendered_path)

        meta = dict(playlist.metadata_json or {})
        meta["render_ready"] = True
        meta["rendered_track_ids"] = rendered_track_ids
        meta["rendered_track_count"] = len(rendered_track_ids)
        meta["rendered_duration_seconds"] = playlist.actual_duration_seconds
        meta["rendered_timeline"] = rendered_timeline
        meta["audio_render_progress"] = {
            **dict(meta.get("audio_render_progress") or {}),
            "stage": "audio_render",
            "progress_ratio": 1.0,
            "percent": 100.0,
            "processed_seconds": playlist.actual_duration_seconds,
            "total_seconds": playlist.actual_duration_seconds,
            "message": "Audio render complete.",
            "status": "end",
            "updated_at": _utcnow().isoformat(),
        }
        meta.pop("stale_audio_render", None)
        meta["workflow_state"] = "audio_ready" if meta.get("publish_ready") else "rendered"
        meta.pop("render_error", None)
        meta["note"] = "Audio render completed in background. Generate cover art next."
        playlist.metadata_json = meta
        playlist.status = PlaylistStatus.ready if meta.get("publish_ready") else PlaylistStatus.draft

        job.result_json = {
            **(job.result_json or {}),
            "playlist_id": playlist.id,
            "output_audio_path": playlist.output_audio_path,
            "progress": meta["audio_render_progress"],
        }
        db.add(playlist)
        db.add(job)
        auto_publish_job = self._queue_auto_publish_job(
            db,
            playlist,
            note="Auto-publish queued after background render completed.",
        )
        if auto_publish_job is not None:
            db.add(auto_publish_job)

    def _process_build_video_job(self, db: Session, job: Job) -> None:
        playlist = db.scalars(
            select(Playlist)
            .options(selectinload(Playlist.items).selectinload(PlaylistItem.track))
            .where(Playlist.id == job.playlist_id)
        ).first()
        if not playlist:
            raise ValueError("Playlist not found for video build job.")

        meta = dict(playlist.metadata_json or {})
        if not playlist.output_audio_path:
            raise ValueError("Playlist audio has not been rendered yet.")
        audio_path = Path(playlist.output_audio_path)
        if not audio_path.exists():
            raise ValueError("Rendered playlist audio file is missing on disk.")
        cover_image_path = meta.get("cover_image_path")
        if not cover_image_path or not Path(cover_image_path).exists():
            raise ValueError("Approved cover image is missing on disk.")
        if not meta.get("cover_approved"):
            raise ValueError("Cover image must be approved before video render.")
        if not _rendered_snapshot_matches_current_tracks(playlist, "rendered_track_ids"):
            raise ValueError("Rendered audio is stale because the track list changed. Re-render audio before video render.")
        video_track_ids = _playlist_track_ids(playlist)

        meta["workflow_state"] = "video_rendering"
        meta["note"] = "Rendering release video."
        meta.pop("video_build_error", None)
        meta["video_render_progress"] = {
            "stage": "video_render",
            "progress_ratio": 0.0,
            "percent": 0.0,
            "processed_seconds": 0.0,
            "total_seconds": playlist.actual_duration_seconds or None,
            "eta_seconds": None,
            "message": "Video render started.",
            "updated_at": _utcnow().isoformat(),
        }
        playlist.metadata_json = meta
        playlist.status = PlaylistStatus.building
        db.add(playlist)
        db.commit()
        db.refresh(playlist)
        self._request_openclaw_for_video_event(
            playlist_id=playlist.id,
            job_id=job.id,
            event="video_render_started",
            reason="video_render_started",
        )

        workspace_mode = str(meta.get("workspace_mode") or "playlist")
        tracks = [
            item.track
            for item in sorted(playlist.items, key=lambda item: item.order_index)
            if item.track is not None
        ]
        video_path = Path(self.settings.playlists_dir) / f"{playlist.id}.mp4"
        progress_callback = self._build_video_progress_callback(db, job, playlist)
        total_duration_seconds = max(playlist.actual_duration_seconds, 0) or None
        loop_video_path = str(meta.get("loop_video_path") or "").strip()
        allow_still_image_fallback = bool((job.payload_json or {}).get("allow_still_image_fallback"))
        video_spectrum_overlay_style = str(
            (job.payload_json or {}).get("video_spectrum_overlay_style")
            or meta.get("video_spectrum_overlay_style")
            or "bars"
        )
        if loop_video_path and Path(loop_video_path).exists():
            playlist.output_video_path = str(
                self._call_builder_with_progress(
                    self.services.playlist_builder.build_looped_video,
                    Path(loop_video_path),
                    audio_path,
                    video_path,
                    smooth_loop=bool(meta.get("loop_video_smooth", True)),
                    spectrum_overlay_style=video_spectrum_overlay_style,
                    progress_callback=progress_callback,
                    total_duration_seconds=total_duration_seconds,
                )
            )
            meta["loop_video_render_mode"] = "smooth-forward-crossfade" if meta.get("loop_video_smooth", True) else "hard-loop"
        elif allow_still_image_fallback:
            playlist.output_video_path = str(
                self._call_builder_with_progress(
                    self.services.playlist_builder.build_video,
                    audio_path,
                    Path(cover_image_path),
                    video_path,
                    spectrum_overlay_style=video_spectrum_overlay_style,
                    progress_callback=progress_callback,
                    total_duration_seconds=total_duration_seconds,
                )
            )
            meta["loop_video_render_mode"] = "still-image-fallback"
        else:
            raise ValueError("Uploaded 8 second loop video is required before video render.")

        rendered_video_path = playlist.output_video_path
        db.expire_all()
        playlist = db.scalars(
            select(Playlist)
            .options(selectinload(Playlist.items).selectinload(PlaylistItem.track))
            .where(Playlist.id == job.playlist_id)
        ).first()
        if not playlist:
            raise ValueError("Playlist not found after video render.")
        current_track_ids = _playlist_track_ids(playlist)
        if current_track_ids != video_track_ids:
            meta = dict(playlist.metadata_json or {})
            meta["metadata_approved"] = False
            meta["publish_approved"] = False
            meta["workflow_state"] = "pending_audio_render"
            meta["note"] = "Track list changed while video was rendering. Re-render audio/video before publishing."
            meta["stale_video_render"] = {
                "rendered_track_ids": video_track_ids,
                "current_track_ids": current_track_ids,
                "detected_at": _utcnow().isoformat(),
            }
            meta.pop("rendered_video_track_ids", None)
            meta.pop("rendered_video_track_count", None)
            playlist.output_video_path = None
            playlist.status = PlaylistStatus.ready
            playlist.metadata_json = meta
            job.result_json = {
                **(job.result_json or {}),
                "playlist_id": playlist.id,
                "stale_output_video_path": rendered_video_path,
                "rendered_track_ids": video_track_ids,
                "current_track_ids": current_track_ids,
            }
            db.add(playlist)
            db.add(job)
            return

        playlist.output_video_path = rendered_video_path
        meta["video_spectrum_overlay_style"] = video_spectrum_overlay_style
        tracks = [
            item.track
            for item in sorted(playlist.items, key=lambda item: item.order_index)
            if item.track is not None
        ]
        render_meta = meta
        meta = self._current_playlist_meta(db, playlist.id, fallback=meta)
        for key in (
            "dreamina_job_id",
            "dreamina_video_url",
            "loop_video_path",
            "loop_video_render_mode",
            "loop_video_smooth",
            "loop_video_source",
            "video_spectrum_overlay_style",
        ):
            if key in render_meta:
                meta[key] = render_meta[key]
        is_playlist_release = str(meta.get("workspace_mode") or "playlist") != "single_track_video"
        if has_youtube_metadata(meta):
            meta["youtube_metadata_preserved_after_video_render"] = True
        else:
            youtube_metadata = self.services.release_metadata.build_youtube_metadata(playlist, tracks)
            apply_generated_youtube_metadata(
                meta,
                youtube_metadata,
                is_playlist_release=is_playlist_release,
            )
            meta["youtube_title"] = ensure_playlist_title_prefix(
                meta["youtube_title"],
                is_playlist=is_playlist_release,
            )
            meta["youtube_metadata_preserved_after_video_render"] = False
        meta["metadata_approved"] = False
        meta["publish_approved"] = False
        meta["rendered_video_track_ids"] = video_track_ids
        meta["rendered_video_track_count"] = len(video_track_ids)
        meta.pop("stale_video_render", None)
        meta["workflow_state"] = "metadata_review"
        meta["note"] = "Video render completed. Review YouTube metadata next."
        meta["video_render_progress"] = {
            **dict(meta.get("video_render_progress") or {}),
            "stage": "video_render",
            "progress_ratio": 1.0,
            "percent": 100.0,
            "eta_seconds": 0,
            "status": "end",
            "message": "Video render completed.",
            "updated_at": _utcnow().isoformat(),
        }
        playlist.metadata_json = meta
        playlist.status = PlaylistStatus.ready

        job.result_json = {
            **(job.result_json or {}),
            "playlist_id": playlist.id,
            "cover_image_path": cover_image_path,
            "output_video_path": playlist.output_video_path,
            "youtube_title": meta["youtube_title"],
            "progress": meta["video_render_progress"],
        }
        db.add(playlist)
        db.add(job)
        db.commit()
        db.refresh(playlist)
        self._request_openclaw_for_video_event(
            playlist_id=playlist.id,
            job_id=job.id,
            event="video_render_completed",
            reason="video_render_completed",
        )

    @staticmethod
    def _call_builder_with_progress(builder_method, *args, progress_callback, total_duration_seconds, **kwargs):
        signature = inspect.signature(builder_method)
        supported_kwargs = {
            key: value
            for key, value in kwargs.items()
            if key in signature.parameters
        }
        if "progress_callback" in signature.parameters:
            supported_kwargs["progress_callback"] = progress_callback
            supported_kwargs["total_duration_seconds"] = total_duration_seconds
        return builder_method(*args, **supported_kwargs)

    @staticmethod
    def _current_playlist_meta(db: Session, playlist_id: str, *, fallback: dict) -> dict:
        current = db.execute(
            select(Playlist.metadata_json).where(Playlist.id == playlist_id)
        ).scalar_one_or_none()
        return dict(current or fallback or {})

    @staticmethod
    def _build_audio_progress_callback(db: Session, job: Job, playlist: Playlist):
        def callback(progress: dict) -> None:
            try:
                payload = {
                    **progress,
                    "message": BackgroundJobWorker._format_audio_progress_message(progress),
                    "updated_at": _utcnow().isoformat(),
                }
                job.result_json = {
                    **(job.result_json or {}),
                    "playlist_id": playlist.id,
                    "progress": payload,
                }
                meta = BackgroundJobWorker._current_playlist_meta(
                    db,
                    playlist.id,
                    fallback=dict(playlist.metadata_json or {}),
                )
                meta["audio_render_progress"] = payload
                meta["note"] = payload["message"]
                playlist.metadata_json = meta
                db.add(job)
                db.add(playlist)
                db.commit()
            except Exception:  # noqa: BLE001
                db.rollback()

        return callback

    @staticmethod
    def _build_video_progress_callback(db: Session, job: Job, playlist: Playlist):
        def callback(progress: dict) -> None:
            try:
                payload = {
                    **progress,
                    "message": BackgroundJobWorker._format_video_progress_message(progress),
                    "updated_at": _utcnow().isoformat(),
                }
                job.result_json = {
                    **(job.result_json or {}),
                    "playlist_id": playlist.id,
                    "progress": payload,
                }
                meta = BackgroundJobWorker._current_playlist_meta(
                    db,
                    playlist.id,
                    fallback=dict(playlist.metadata_json or {}),
                )
                meta["video_render_progress"] = payload
                meta["note"] = payload["message"]
                playlist.metadata_json = meta
                db.add(job)
                db.add(playlist)
                db.commit()
            except Exception:  # noqa: BLE001
                db.rollback()

        return callback

    @staticmethod
    def _format_audio_progress_message(progress: dict) -> str:
        percent = progress.get("percent")
        processed = progress.get("processed_seconds")
        total = progress.get("total_seconds")
        eta = progress.get("eta_seconds")
        pieces = ["Rendering playlist audio"]
        if isinstance(percent, (int, float)):
            pieces.append(f"{percent:.1f}%")
        if isinstance(processed, (int, float)) and isinstance(total, (int, float)) and total > 0:
            pieces.append(f"{BackgroundJobWorker._format_seconds(processed)} / {BackgroundJobWorker._format_seconds(total)}")
        if isinstance(eta, (int, float)):
            pieces.append(f"about {BackgroundJobWorker._format_seconds(eta)} remaining")
        return " · ".join(pieces) + "."

    @staticmethod
    def _format_video_progress_message(progress: dict) -> str:
        percent = progress.get("percent")
        processed = progress.get("processed_seconds")
        total = progress.get("total_seconds")
        eta = progress.get("eta_seconds")
        pieces = ["Rendering release video"]
        if isinstance(percent, (int, float)):
            pieces.append(f"{percent:.1f}%")
        if isinstance(processed, (int, float)) and isinstance(total, (int, float)) and total > 0:
            pieces.append(f"{BackgroundJobWorker._format_seconds(processed)} / {BackgroundJobWorker._format_seconds(total)}")
        if isinstance(eta, (int, float)):
            pieces.append(f"about {BackgroundJobWorker._format_seconds(eta)} remaining")
        return " · ".join(pieces) + "."

    @staticmethod
    def _format_seconds(seconds: int | float) -> str:
        total = max(int(seconds), 0)
        hours, remainder = divmod(total, 3600)
        minutes, secs = divmod(remainder, 60)
        if hours:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"

    def _process_sync_slack_job(self, db: Session, job: Job) -> None:
        if not job.track_id:
            raise ValueError("Slack sync job is missing track_id.")

        track = db.get(Track, job.track_id)
        if not track:
            raise ValueError("Track not found for Slack sync job.")

        from app.workflows.review_dispatch import dispatch_track_review

        updated = asyncio.run(dispatch_track_review(db, self.services, track))
        job.result_json = {
            **(job.result_json or {}),
            "track_id": updated.id,
            "track_status": updated.status.value,
            "slack_channel_id": updated.slack_channel_id,
            "slack_message_ts": updated.slack_message_ts,
        }

    def _process_publish_job(self, db: Session, job: Job) -> None:
        playlist = db.scalars(
            select(Playlist)
            .options(selectinload(Playlist.items).selectinload(PlaylistItem.track))
            .where(Playlist.id == job.playlist_id)
        ).first()
        if not playlist:
            raise ValueError("Playlist not found for publish job.")

        meta = dict(playlist.metadata_json or {})
        actor = (job.payload_json or {}).get("actor") or "background-worker"
        note = (job.payload_json or {}).get("note")
        force_under_target = bool((job.payload_json or {}).get("force_under_target"))
        youtube_channel_id = (job.payload_json or {}).get("youtube_channel_id") or meta.get("youtube_channel_id")

        if not playlist.items:
            raise ValueError("Playlist has no tracks to publish.")
        under_target = playlist.actual_duration_seconds < playlist.target_duration_seconds
        if not meta.get("publish_ready") and not (force_under_target and under_target):
            raise ValueError("Playlist has not reached its target duration yet.")
        if under_target and not force_under_target:
            raise ValueError("Playlist has not reached its target duration yet.")
        if force_under_target and under_target:
            meta["publish_ready"] = True
            meta["publish_under_target_confirmed"] = True
            meta["publish_under_target_confirmed_by"] = actor
            meta["publish_under_target_confirmed_at"] = _utcnow().isoformat()
        if not playlist.output_video_path or not Path(playlist.output_video_path).exists():
            raise ValueError("Rendered video is required before final YouTube upload.")
        if not _rendered_snapshot_matches_current_tracks(playlist, "rendered_video_track_ids"):
            raise ValueError("Rendered video is stale because the track list changed. Re-render video before final YouTube upload.")
        cover_image_path = meta.get("cover_image_path")
        if not cover_image_path or not Path(cover_image_path).exists():
            raise ValueError("Approved cover image is missing on disk.")
        if not meta.get("cover_approved"):
            raise ValueError("Cover image must be approved before final YouTube upload.")
        if not meta.get("metadata_approved"):
            raise ValueError("YouTube metadata must be approved before final YouTube upload.")
        is_playlist_release = str(meta.get("workspace_mode") or "playlist") != "single_track_video"
        title = ensure_playlist_title_prefix(
            meta.get("youtube_title"),
            is_playlist=is_playlist_release,
        )
        description = str(meta.get("youtube_description") or "").strip()
        tags = list(meta.get("youtube_tags") or [])
        default_language = normalize_youtube_language(meta.get("youtube_default_language"))
        localizations = ensure_playlist_localization_title_prefix(
            normalize_youtube_localizations(
                meta.get("youtube_localizations"),
                default_title=title,
                default_description=description,
                default_language=default_language,
            ),
            is_playlist=is_playlist_release,
        )
        if not title or not description:
            raise ValueError("YouTube metadata draft is missing before final YouTube upload.")
        meta["youtube_title"] = title
        meta["youtube_localizations"] = localizations

        meta["publish_approved"] = True
        meta["publish_approved_by"] = actor
        meta["workflow_state"] = "publish_queued"
        meta["note"] = note

        if self.settings.youtube_auto_upload_on_publish:
            youtube_status = self.services.youtube.get_status()
            if youtube_status["ready"]:
                try:
                    from app.workflows.playlist_automation import (
                        next_youtube_scheduled_publish_at,
                        youtube_schedule_metadata,
                    )

                    thumbnail_path = str(meta.get("youtube_thumbnail_path") or "").strip() or cover_image_path
                    scheduled_publish_at = next_youtube_scheduled_publish_at(
                        db,
                        self.services,
                        youtube_channel_id=youtube_channel_id,
                        youtube_channel_title=meta.get("youtube_channel_title"),
                    )
                    result = self.services.youtube.upload_playlist_video(
                        playlist,
                        title=title,
                        description=description,
                        tags=tags,
                        thumbnail_path=thumbnail_path,
                        youtube_channel_id=youtube_channel_id,
                        localizations=localizations,
                        default_language=default_language,
                        scheduled_publish_at=scheduled_publish_at,
                    )
                    uploaded_video_path = playlist.output_video_path
                    playlist.youtube_video_id = result.video_id
                    playlist.status = PlaylistStatus.uploaded
                    meta["workflow_state"] = "uploaded"
                    meta["youtube_response"] = result.response
                    meta.update(youtube_schedule_metadata(self.services, scheduled_publish_at))
                    response_snippet = result.response.get("snippet") if isinstance(result.response, dict) else {}
                    meta["youtube_published_at"] = (
                        response_snippet.get("publishedAt")
                        if isinstance(response_snippet, dict) and response_snippet.get("publishedAt")
                        else _utcnow().isoformat()
                    )
                    cleanup = self._delete_uploaded_video_file(uploaded_video_path)
                    if cleanup["deleted"]:
                        playlist.output_video_path = None
                        meta["local_video_deleted_after_youtube_upload"] = cleanup["path"]
                        meta["local_video_deleted_at"] = _utcnow().isoformat()
                        meta.pop("local_video_cleanup_error", None)
                    elif cleanup.get("error"):
                        meta["local_video_cleanup_error"] = cleanup["error"]
                    if result.response.get("upload_channel"):
                        meta["youtube_channel_id"] = result.response["upload_channel"].get("id")
                        meta["youtube_channel_title"] = result.response["upload_channel"].get("title")
                    meta.pop("youtube_upload_error", None)
                    if result.response.get("thumbnail_upload_error"):
                        meta["youtube_thumbnail_upload_error"] = result.response["thumbnail_upload_error"]
                    else:
                        meta.pop("youtube_thumbnail_upload_error", None)
                    if result.response.get("localizations_upload_error"):
                        meta["youtube_localizations_upload_error"] = result.response["localizations_upload_error"]
                    else:
                        meta.pop("youtube_localizations_upload_error", None)
                    for item in playlist.items:
                        item.track.status = TrackStatus.uploaded
                        db.add(item.track)
                    notify_youtube_publish_completed(
                        db,
                        self.services,
                        playlist=playlist,
                        youtube_video_id=playlist.youtube_video_id or "",
                        channel_title=meta.get("youtube_channel_title"),
                        scheduled_publish_at=meta.get("youtube_scheduled_publish_at"),
                    )
                    if self.settings.openclaw_auto_request_next_on_publish:
                        job.result_json = {
                            **(job.result_json or {}),
                            "post_commit_openclaw_request": {
                                "playlist_id": playlist.id,
                                "youtube_video_id": playlist.youtube_video_id or "",
                                "reason": "publish_completed",
                            },
                        }
                except Exception as exc:  # noqa: BLE001
                    if _is_long_video_verification_upload_error(str(exc), playlist):
                        playlist.status = PlaylistStatus.ready
                        meta["workflow_state"] = "youtube_upload_deferred_verification"
                        meta["note"] = (
                            "YouTube account verification appears to block this long video upload. "
                            "The rendered release is kept for later manual upload/retry, and automation may continue."
                        )
                        meta["youtube_upload_error"] = str(exc)
                        meta["youtube_upload_deferred_reason"] = "long_video_phone_verification"
                        meta["youtube_upload_deferred_at"] = _utcnow().isoformat()
                        if self.settings.openclaw_auto_request_next_on_publish:
                            job.result_json = {
                                **(job.result_json or {}),
                                "post_commit_openclaw_request": {
                                    "playlist_id": playlist.id,
                                    "youtube_video_id": "",
                                    "reason": "upload_deferred_verification",
                                },
                            }
                        playlist.metadata_json = meta
                        db.add(playlist)
                        return
                    playlist.status = PlaylistStatus.ready
                    meta["workflow_state"] = "youtube_upload_failed"
                    meta["note"] = f"Automatic YouTube upload failed: {exc}"
                    meta["youtube_upload_error"] = str(exc)
                    playlist.metadata_json = meta
                    db.add(playlist)
                    raise
            else:
                playlist.status = PlaylistStatus.ready
                meta["workflow_state"] = "ready_for_youtube_auth"
                meta["note"] = (
                    f"{note} " if note else ""
                ) + "Connect YouTube in the web app to enable automatic upload."
        else:
            playlist.status = PlaylistStatus.ready
            meta["workflow_state"] = "ready_for_youtube"

        playlist.metadata_json = meta
        job.result_json = {
            **(job.result_json or {}),
            "playlist_id": playlist.id,
            "cover_image_path": cover_image_path,
            "output_video_path": playlist.output_video_path,
            "youtube_video_id": playlist.youtube_video_id,
            "youtube_title": title,
        }
        db.add(playlist)
        db.add(job)

    @staticmethod
    def _delete_uploaded_video_file(video_path: str | None) -> dict:
        if not video_path:
            return {"deleted": False, "path": None}
        path = Path(video_path)
        if not path.exists():
            return {"deleted": False, "path": str(path)}
        try:
            path.unlink()
        except OSError as exc:
            return {"deleted": False, "path": str(path), "error": str(exc)}
        return {"deleted": True, "path": str(path)}

    def _mark_job_failed(self, db: Session, job: Job, error_text: str) -> None:
        playlist = db.get(Playlist, job.playlist_id) if job.playlist_id else None
        if playlist:
            meta = dict(playlist.metadata_json or {})
            if job.type == JobType.build_playlist:
                playlist.status = PlaylistStatus.draft
                meta["workflow_state"] = "render_failed"
                meta["render_ready"] = False
                meta["render_error"] = error_text
                meta["note"] = f"Background render failed: {error_text}"
                meta["audio_render_progress"] = {
                    **dict(meta.get("audio_render_progress") or {}),
                    "status": "failed",
                    "message": meta["note"],
                    "updated_at": _utcnow().isoformat(),
                }
            elif job.type == JobType.build_video:
                playlist.status = PlaylistStatus.ready
                meta["workflow_state"] = "video_build_failed"
                meta["video_build_error"] = error_text
                meta["note"] = f"Background video render failed: {error_text}"
                meta["video_render_progress"] = {
                    **dict(meta.get("video_render_progress") or {}),
                    "status": "failed",
                    "message": meta["note"],
                    "updated_at": _utcnow().isoformat(),
                }
            elif job.type == JobType.upload_youtube:
                playlist.status = PlaylistStatus.ready
                if meta.get("workflow_state") not in {"video_build_failed", "youtube_upload_failed"}:
                    meta["workflow_state"] = "publish_failed"
                    meta["note"] = f"Background publish failed: {error_text}"
            playlist.metadata_json = meta
            db.add(playlist)

        job.status = JobStatus.failed
        job.error_text = error_text
        job.finished_at = _utcnow()
        db.add(job)
        db.commit()

    def _request_openclaw_for_video_event(self, *, playlist_id: str, job_id: str, event: str, reason: str) -> None:
        if not self.settings.openclaw_request_next_on_video_render_events:
            return
        if not self.settings.openclaw_slack_channel_id.strip():
            return
        if self.services is None:
            return

        thread = threading.Thread(
            target=self._post_openclaw_video_event_request_when_unlocked,
            name=f"openclaw-{event}-{playlist_id[:8]}",
            kwargs={
                "playlist_id": playlist_id,
                "job_id": job_id,
                "event": event,
                "reason": reason,
            },
            daemon=True,
        )
        thread.start()

    def _request_openclaw_for_publish_event(self, *, playlist_id: str, youtube_video_id: str, reason: str) -> None:
        if not self.settings.openclaw_auto_request_next_on_publish:
            return
        if not self.settings.openclaw_slack_channel_id.strip():
            return
        if self.services is None:
            return

        thread = threading.Thread(
            target=self._post_openclaw_publish_event_request_when_unlocked,
            name=f"openclaw-{reason}-{playlist_id[:8]}",
            kwargs={
                "playlist_id": playlist_id,
                "youtube_video_id": youtube_video_id,
                "reason": reason,
            },
            daemon=True,
        )
        thread.start()

    def _post_openclaw_publish_event_request_when_unlocked(
        self,
        *,
        playlist_id: str,
        youtube_video_id: str,
        reason: str,
    ) -> None:
        if self.services is None:
            return

        lock_wait_deadline = time.monotonic() + max(float(self.settings.openclaw_lock_ttl_seconds or 0), 60.0) + 300.0
        while time.monotonic() < lock_wait_deadline:
            lock_status = get_openclaw_lock_status(self.settings.storage_root)
            if not lock_status.get("active"):
                break
            time.sleep(10.0)
        else:
            self._record_openclaw_publish_event_request(
                playlist_id=playlist_id,
                youtube_video_id=youtube_video_id,
                reason=reason,
                result={"ok": False, "skipped": True, "reason": "openclaw_lock_still_active"},
            )
            return

        loop_state = get_auto_loop_control_state(storage_root=self.settings.storage_root)
        if loop_state.get("stopped"):
            self._record_openclaw_publish_event_request(
                playlist_id=playlist_id,
                youtube_video_id=youtube_video_id,
                reason=reason,
                result={"ok": False, "skipped": True, "reason": "auto_loop_stopped", "loop_state": loop_state},
            )
            return

        with SessionLocal() as db:
            playlist = db.get(Playlist, playlist_id)
            if not playlist:
                return
            meta = dict(playlist.metadata_json or {})
            if reason == "publish_completed":
                sent_key = "openclaw_next_request_youtube_video_id"
                if youtube_video_id and str(meta.get(sent_key) or "").strip() == youtube_video_id:
                    return
            else:
                sent_key = "openclaw_next_request_deferred_playlist_id"
                if str(meta.get(sent_key) or "").strip() == playlist_id:
                    return

            if reason == "publish_completed":
                try:
                    loop_state = record_auto_loop_upload(
                        storage_root=self.settings.storage_root,
                        max_uploads=self.settings.openclaw_auto_request_next_max_uploads,
                        channel_id=self.settings.openclaw_slack_channel_id,
                        trigger_prefix=self.settings.openclaw_slack_trigger_prefix,
                        playlist_id=playlist_id,
                        youtube_video_id=youtube_video_id,
                    )
                except Exception as loop_exc:  # noqa: BLE001
                    loop_state = {
                        "enabled": True,
                        "should_request_next": False,
                        "reason": "loop_state_error",
                        "error": str(loop_exc),
                    }
            else:
                loop_state = {
                    "enabled": True,
                    "limited": max(0, int(self.settings.openclaw_auto_request_next_max_uploads or 0)) > 0,
                    "max_uploads": max(0, int(self.settings.openclaw_auto_request_next_max_uploads or 0)),
                    "should_request_next": True,
                    "reason": reason,
                }
            meta["openclaw_auto_loop"] = loop_state
            if not loop_state.get("should_request_next"):
                result = {
                    "ok": False,
                    "skipped": True,
                    "reason": loop_state.get("reason"),
                    "completed_uploads": loop_state.get("completed_uploads"),
                    "max_uploads": loop_state.get("max_uploads"),
                    "remaining_uploads": loop_state.get("remaining_uploads"),
                }
            else:
                try:
                    if self.settings.openclaw_request_next_on_video_render_events:
                        summary = build_openclaw_backlog_summary(db, self.services)
                        result = asyncio.run(
                            post_backlog_queue_request(
                                db,
                                self.services,
                                reason=reason,
                                backlog_summary=summary,
                            )
                        )
                    else:
                        result = asyncio.run(post_next_playlist_request(db, self.services, playlist))
                except Exception as slack_exc:  # noqa: BLE001
                    result = {"ok": False, "error": str(slack_exc)}

            meta["openclaw_next_request"] = result
            meta["openclaw_next_request_at"] = _utcnow().isoformat()
            if result.get("ok"):
                if reason == "publish_completed" and youtube_video_id:
                    meta["openclaw_next_request_youtube_video_id"] = youtube_video_id
                elif reason != "publish_completed":
                    meta["openclaw_next_request_deferred_playlist_id"] = playlist_id
                record_openclaw_backlog_scheduler_request(
                    storage_root=self.settings.storage_root,
                    result={
                        "reason": reason,
                        "playlist_id": playlist_id,
                        "youtube_video_id": youtube_video_id,
                        "slack": {key: result.get(key) for key in ("ok", "channel", "ts")},
                    },
                )
            playlist.metadata_json = meta
            db.add(playlist)
            db.commit()

    def _post_openclaw_video_event_request_when_unlocked(
        self,
        *,
        playlist_id: str,
        job_id: str,
        event: str,
        reason: str,
    ) -> None:
        if self.services is None:
            return

        lock_wait_deadline = time.monotonic() + max(float(self.settings.openclaw_lock_ttl_seconds or 0), 60.0) + 300.0
        while time.monotonic() < lock_wait_deadline:
            lock_status = get_openclaw_lock_status(self.settings.storage_root)
            if not lock_status.get("active"):
                break
            time.sleep(10.0)
        else:
            self._record_openclaw_video_event_request(
                playlist_id=playlist_id,
                job_id=job_id,
                event=event,
                result={"ok": False, "skipped": True, "reason": "openclaw_lock_still_active"},
            )
            return

        loop_state = get_auto_loop_control_state(storage_root=self.settings.storage_root)
        if loop_state.get("stopped"):
            self._record_openclaw_video_event_request(
                playlist_id=playlist_id,
                job_id=job_id,
                event=event,
                result={"ok": False, "skipped": True, "reason": "auto_loop_stopped", "loop_state": loop_state},
            )
            return

        with SessionLocal() as db:
            playlist = db.get(Playlist, playlist_id)
            if not playlist:
                return
            meta = dict(playlist.metadata_json or {})
            job_key = f"openclaw_{event}_request_job_id"
            if str(meta.get(job_key) or "") == job_id:
                return

            summary = build_openclaw_backlog_summary(db, self.services)
            try:
                result = asyncio.run(
                    post_backlog_queue_request(
                        db,
                        self.services,
                        reason=reason,
                        backlog_summary=summary,
                    )
                )
            except Exception as exc:  # noqa: BLE001
                result = {"ok": False, "error": str(exc)}

            meta[f"openclaw_{event}_request"] = result
            meta[f"openclaw_{event}_request_at"] = _utcnow().isoformat()
            if result.get("ok"):
                meta[job_key] = job_id
                record_openclaw_backlog_scheduler_request(
                    storage_root=self.settings.storage_root,
                    result={
                        "reason": reason,
                        "playlist_id": playlist_id,
                        "job_id": job_id,
                        "slack": {key: result.get(key) for key in ("ok", "channel", "ts")},
                    },
                )
            playlist.metadata_json = meta
            db.add(playlist)
            db.commit()

    def _record_openclaw_video_event_request(
        self,
        *,
        playlist_id: str,
        job_id: str,
        event: str,
        result: dict,
    ) -> None:
        with SessionLocal() as db:
            playlist = db.get(Playlist, playlist_id)
            if not playlist:
                return
            meta = dict(playlist.metadata_json or {})
            meta[f"openclaw_{event}_request"] = result
            meta[f"openclaw_{event}_request_at"] = _utcnow().isoformat()
            meta[f"openclaw_{event}_request_job_id"] = job_id
            playlist.metadata_json = meta
            db.add(playlist)
            db.commit()

    def _record_openclaw_publish_event_request(
        self,
        *,
        playlist_id: str,
        youtube_video_id: str,
        reason: str,
        result: dict,
    ) -> None:
        with SessionLocal() as db:
            playlist = db.get(Playlist, playlist_id)
            if not playlist:
                return
            meta = dict(playlist.metadata_json or {})
            meta["openclaw_next_request"] = result
            meta["openclaw_next_request_at"] = _utcnow().isoformat()
            meta["openclaw_next_request_reason"] = reason
            if youtube_video_id:
                meta["openclaw_next_request_youtube_video_id"] = youtube_video_id
            playlist.metadata_json = meta
            db.add(playlist)
            db.commit()

    @staticmethod
    def _queue_auto_publish_job(db: Session, playlist: Playlist, *, note: str) -> Job | None:
        meta = dict(playlist.metadata_json or {})
        if not meta.get("publish_ready"):
            return None
        if not meta.get("auto_publish_when_ready"):
            return None
        if not playlist.output_video_path or not Path(playlist.output_video_path).exists():
            return None
        if not meta.get("cover_approved") or not meta.get("metadata_approved"):
            return None

        active_job = db.scalars(
            select(Job).where(
                Job.playlist_id == playlist.id,
                Job.type == JobType.upload_youtube,
                Job.status.in_([JobStatus.queued, JobStatus.running]),
            )
        ).first()
        if active_job:
            return active_job

        meta["publish_approved"] = True
        meta["publish_approved_by"] = "system:auto-publish"
        meta["workflow_state"] = "publish_queued"
        meta["note"] = note
        playlist.metadata_json = meta
        playlist.status = PlaylistStatus.ready
        db.add(playlist)

        job = Job(
            type=JobType.upload_youtube,
            status=JobStatus.queued,
            source="system:auto-publish",
            payload_json={
                "playlist_id": playlist.id,
                "actor": "system:auto-publish",
                "note": note,
            },
            result_json={},
            playlist=playlist,
        )
        return job

    @staticmethod
    def _build_dreamina_prompt(playlist: Playlist, tracks: list) -> str:
        meta = dict(playlist.metadata_json or {})
        explicit_prompt = str(meta.get("dreamina_prompt") or "").strip()
        if explicit_prompt:
            return explicit_prompt
        is_tokyo_visual = BackgroundJobWorker._uses_tokyo_daydream_visuals(playlist, tracks)
        channel_title = str(meta.get("youtube_channel_title") or "").strip()
        if not channel_title:
            channel_title = "Tokyo Daydream Radio" if is_tokyo_visual else "Soft Hour Radio"
        channel_label_prompt = (
            f'The uploaded first-frame image contains the exact large, readable lower-left channel brand label "{channel_title}". '
            "It should be the same visual scale as the channel-brand line used on the YouTube thumbnail, roughly 18-24% of image width or 5-6% of image height for text cap height. "
            "Preserve this text exactly for the full clip. Do not rewrite, translate, blur, morph, move, hide, "
            "shrink, flicker, or change it. Keep the text area stable and animate the surrounding scene naturally. "
            "No other text, subtitles, logos, UI, or title words."
        )
        signature_prompt = (
            "Signature composition for Tokyo Daydream Radio/J-pop only: exactly three people seen from behind, "
            "walking away from the camera into the scene. The viewer sees their backs and backs of heads, "
            "not front-facing faces. One continuous forward-moving shot with subtle camera-follow movement from behind, "
            "final moment close to the opening composition while maintaining natural motion, "
            "stable composition, no repeated segment, no hard cuts, no subtitles, no extra people or characters. "
            f"{channel_label_prompt}"
        )
        soft_hour_prompt = (
            "Soft Hour Radio/background-music visual system: calm, restrained visual concept matched to the release. "
            "Let the release concept and first frame decide the subject; do not force a fixed recurring mascot, "
            "character count, scene list, or camera composition. Use motion derived from the first frame. "
            "Keep the camera locked in the same crop and framing for the full clip; no zoom, push-in, pull-back, dolly, camera breathing, drift, camera follow, or parallax camera movement. "
            "Animate several environmental layers already present or naturally implied by the first frame with calm but clearly visible motion, such as leaves swaying, grass or curtains moving in a breeze, water/rain reflections, warm light shimmer, drifting dust motes, smoke, steam, or fireflies. "
            "Keep continuous visible motion throughout the full clip while preserving the calm long-listening mood. "
            "The final moment should preserve the same crop, framing, camera distance, lighting, palette, and subject placement; only ambient details may differ. "
            "No repeated segment, no hard cuts, no subtitles, no logos, no UI. "
            f"{channel_label_prompt}"
        )
        if tracks:
            track = tracks[0]
            track_meta = track.metadata_json or {}
            tags = str(track_meta.get("tags") or "").strip()
            lyrics = str(track_meta.get("lyrics") or "").strip()
            style = str(track_meta.get("style") or "").strip()
            lyrics_context = f" Lyrics/content context: {lyrics[:800]}." if lyrics else ""
            style_context = f" Suno style/settings: {style[:500]}." if style else ""
            return (
                f"Cinematic music visualizer shot for '{track.title}'. "
                f"Prompt mood: {track.prompt}. "
                f"{lyrics_context}"
                f"{style_context}"
                f"Visual style tags: {tags or 'electronic, atmospheric, neon'}. "
                "Use animated, anime, illustrated, or stylized visual language. Do not use photorealistic, live-action, documentary, camera-photo, or realistic human footage. "
                f"{signature_prompt if is_tokyo_visual else soft_hour_prompt}"
            )
        if is_tokyo_visual:
            return (
                "Cinematic music visualizer shot for Tokyo Daydream Radio/J-pop with exactly three people seen from behind walking away from the camera into the scene, "
                "animated/anime/illustrated style, not photorealistic or live-action, "
                "one continuous forward-moving take with subtle camera-follow movement from behind, atmospheric lighting, final moment close to the opening composition, no repeated segment. "
                f"{channel_label_prompt}"
            )
        return (
            "Cinematic background-music visualizer shot for Soft Hour Radio: calm, restrained illustrated scene matched to the release concept. "
            "Animated/anime/illustrated style, not photorealistic or live-action. Locked camera with the same crop and framing for the full clip; no zoom, push-in, pull-back, dolly, camera breathing, drift, camera follow, or parallax camera movement. Calm but clearly visible ambient motion across several environmental layers derived from the first frame, stable composition, no fixed recurring character/scene template, no repeated segment, continuous visible motion throughout the full clip. "
            f"{channel_label_prompt}"
        )

    @staticmethod
    def _uses_tokyo_daydream_visuals(playlist: Playlist, tracks: list) -> bool:
        meta = dict(playlist.metadata_json or {})
        haystack_parts = [
            playlist.title,
            str(meta.get("description") or ""),
            str(meta.get("youtube_channel_title") or ""),
            str(meta.get("youtube_title") or ""),
        ]
        channel_title = str(meta.get("youtube_channel_title") or "").strip().lower()
        if channel_title == "soft hour radio":
            return False
        if channel_title == "tokyo daydream radio":
            return True
        for track in tracks:
            track_meta = getattr(track, "metadata_json", None) or {}
            haystack_parts.extend(
                [
                    getattr(track, "title", ""),
                    getattr(track, "prompt", ""),
                    str(track_meta.get("tags") or ""),
                    str(track_meta.get("style") or ""),
                ]
            )
        haystack = " ".join(str(part or "") for part in haystack_parts).lower()
        tokyo_markers = (
            "tokyo daydream radio",
            "tokyo",
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
            "city pop",
            "citypop",
            "anime",
            "shibuya",
            "shinjuku",
            "도쿄",
            "제이팝",
            "시티팝",
            "애니",
            "東京",
            "jポップ",
            "シティポップ",
            "アニメ",
        )
        return any(marker in haystack for marker in tokyo_markers)
