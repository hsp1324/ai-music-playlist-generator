from __future__ import annotations

import asyncio
import inspect
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import Settings
from app.db import SessionLocal
from app.models.enums import JobStatus, JobType, PlaylistStatus, TrackStatus
from app.models.job import Job
from app.models.playlist import Playlist, PlaylistItem
from app.models.track import Track


def _utcnow():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)


@dataclass
class WorkerLoopState:
    running: bool = False
    last_error: str | None = None


class BackgroundJobWorker:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.services = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._state = WorkerLoopState()

    def bind_services(self, services) -> None:
        self.services = services

    def start(self) -> None:
        if not self.settings.worker_autostart or self._thread is not None:
            return
        if self.services is None:
            raise RuntimeError("Background worker is not bound to services.")

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            name="aimp-background-worker",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def process_pending_once(self) -> bool:
        job_id = self._claim_next_job_id()
        if not job_id:
            return False
        self._process_job(job_id)
        return True

    def _run_loop(self) -> None:
        self._state.running = True
        while not self._stop_event.is_set():
            try:
                processed = self.process_pending_once()
                self._state.last_error = None
            except Exception as exc:  # noqa: BLE001
                self._state.last_error = str(exc)
                processed = False
            if not processed:
                self._stop_event.wait(self.settings.worker_poll_interval_seconds)
        self._state.running = False

    def _claim_next_job_id(self) -> str | None:
        with SessionLocal() as db:
            job = db.scalars(
                select(Job)
                .where(
                    Job.status == JobStatus.queued,
                    Job.type.in_([JobType.build_playlist, JobType.build_video, JobType.upload_youtube, JobType.sync_slack]),
                )
                .order_by(Job.created_at.asc())
            ).first()
            if not job:
                return None

            job.status = JobStatus.running
            job.started_at = _utcnow()
            db.add(job)
            db.commit()
            return job.id

    def _process_job(self, job_id: str) -> None:
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
                job.status = JobStatus.succeeded
                job.finished_at = _utcnow()
                db.add(job)
                db.commit()
            except Exception as exc:  # noqa: BLE001
                self._mark_job_failed(db, job, str(exc))

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
        playlist.metadata_json = meta
        playlist.status = PlaylistStatus.building
        db.add(playlist)
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

        output_path = Path(self.settings.playlists_dir) / f"{playlist.id}.mp3"
        rendered_path = self.services.playlist_builder.build_audio(tracks, output_path)
        playlist.output_audio_path = str(rendered_path)

        meta = dict(playlist.metadata_json or {})
        meta["render_ready"] = True
        meta["workflow_state"] = "audio_ready" if meta.get("publish_ready") else "rendered"
        meta.pop("render_error", None)
        meta["note"] = "Audio render completed in background. Generate cover art next."
        playlist.metadata_json = meta
        playlist.status = PlaylistStatus.ready if meta.get("publish_ready") else PlaylistStatus.draft

        job.result_json = {
            **(job.result_json or {}),
            "playlist_id": playlist.id,
            "output_audio_path": playlist.output_audio_path,
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

        workspace_mode = str(meta.get("workspace_mode") or "playlist")
        tracks = [
            item.track
            for item in sorted(playlist.items, key=lambda item: item.order_index)
            if item.track is not None
        ]
        video_path = Path(self.settings.playlists_dir) / f"{playlist.id}.mp4"
        progress_callback = self._build_video_progress_callback(db, job, playlist)
        total_duration_seconds = max(playlist.actual_duration_seconds, 0) or None
        if workspace_mode == "single_track_video" and self.services.dreamina.get_status()["ready"]:
            loop_prompt = self._build_dreamina_prompt(playlist, tracks)
            clip_path = Path(self.settings.playlists_dir) / f"{playlist.id}-dreamina.mp4"
            clip = self.services.dreamina.generate_loop_clip(prompt=loop_prompt)
            downloaded_clip = self.services.dreamina.download_video(clip.video_url, clip_path)
            playlist.output_video_path = str(
                self._call_builder_with_progress(
                    self.services.playlist_builder.build_looped_video,
                    downloaded_clip,
                    audio_path,
                    video_path,
                    progress_callback=progress_callback,
                    total_duration_seconds=total_duration_seconds,
                )
            )
            meta["dreamina_job_id"] = clip.job_id
            meta["dreamina_video_url"] = clip.video_url
            meta["loop_video_path"] = str(downloaded_clip)
        else:
            playlist.output_video_path = str(
                self._call_builder_with_progress(
                    self.services.playlist_builder.build_video,
                    audio_path,
                    Path(cover_image_path),
                    video_path,
                    progress_callback=progress_callback,
                    total_duration_seconds=total_duration_seconds,
                )
            )

        youtube_metadata = self.services.release_metadata.build_youtube_metadata(playlist, tracks)
        meta["youtube_title"] = youtube_metadata.title
        meta["youtube_description"] = youtube_metadata.description
        meta["youtube_tags"] = youtube_metadata.tags
        meta["metadata_approved"] = False
        meta["publish_approved"] = False
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
            "youtube_title": youtube_metadata.title,
            "progress": meta["video_render_progress"],
        }
        db.add(playlist)
        db.add(job)

    @staticmethod
    def _call_builder_with_progress(builder_method, *args, progress_callback, total_duration_seconds):
        signature = inspect.signature(builder_method)
        if "progress_callback" not in signature.parameters:
            return builder_method(*args)
        return builder_method(
            *args,
            progress_callback=progress_callback,
            total_duration_seconds=total_duration_seconds,
        )

    @staticmethod
    def _build_video_progress_callback(db: Session, job: Job, playlist: Playlist):
        def callback(progress: dict) -> None:
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
            meta = dict(playlist.metadata_json or {})
            meta["video_render_progress"] = payload
            meta["note"] = payload["message"]
            playlist.metadata_json = meta
            db.add(job)
            db.add(playlist)
            db.commit()

        return callback

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
        cover_image_path = meta.get("cover_image_path")
        if not cover_image_path or not Path(cover_image_path).exists():
            raise ValueError("Approved cover image is missing on disk.")
        if not meta.get("cover_approved"):
            raise ValueError("Cover image must be approved before final YouTube upload.")
        if not meta.get("metadata_approved"):
            raise ValueError("YouTube metadata must be approved before final YouTube upload.")
        title = str(meta.get("youtube_title") or "").strip()
        description = str(meta.get("youtube_description") or "").strip()
        tags = list(meta.get("youtube_tags") or [])
        if not title or not description:
            raise ValueError("YouTube metadata draft is missing before final YouTube upload.")

        meta["publish_approved"] = True
        meta["publish_approved_by"] = actor
        meta["workflow_state"] = "publish_queued"
        meta["note"] = note

        if self.settings.youtube_auto_upload_on_publish:
            youtube_status = self.services.youtube.get_status()
            if youtube_status["ready"]:
                try:
                    thumbnail_path = str(meta.get("youtube_thumbnail_path") or "").strip() or cover_image_path
                    result = self.services.youtube.upload_playlist_video(
                        playlist,
                        title=title,
                        description=description,
                        tags=tags,
                        thumbnail_path=thumbnail_path,
                        youtube_channel_id=youtube_channel_id,
                    )
                    playlist.youtube_video_id = result.video_id
                    playlist.status = PlaylistStatus.uploaded
                    meta["workflow_state"] = "uploaded"
                    meta["youtube_response"] = result.response
                    if result.response.get("upload_channel"):
                        meta["youtube_channel_id"] = result.response["upload_channel"].get("id")
                        meta["youtube_channel_title"] = result.response["upload_channel"].get("title")
                    meta.pop("youtube_upload_error", None)
                    if result.response.get("thumbnail_upload_error"):
                        meta["youtube_thumbnail_upload_error"] = result.response["thumbnail_upload_error"]
                    else:
                        meta.pop("youtube_thumbnail_upload_error", None)
                    for item in playlist.items:
                        item.track.status = TrackStatus.uploaded
                        db.add(item.track)
                except Exception as exc:  # noqa: BLE001
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
        if tracks:
            track = tracks[0]
            tags = str((track.metadata_json or {}).get("tags") or "").strip()
            return (
                f"Cinematic music visualizer loop for '{track.title}'. "
                f"Prompt mood: {track.prompt}. "
                f"Visual style tags: {tags or 'electronic, atmospheric, neon'}. "
                "Slow camera motion, seamless looping movement, no hard cuts, no subtitles, no text."
            )
        return "Cinematic music visualizer loop, seamless motion, atmospheric lighting, no text."
