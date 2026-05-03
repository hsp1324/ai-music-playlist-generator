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
from app.utils.youtube_localizations import (
    DEFAULT_YOUTUBE_LANGUAGE,
    normalize_youtube_language,
    normalize_youtube_localizations,
)
from app.utils.openclaw_slack_loop import post_next_playlist_request


def _utcnow():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)


def _playlist_track_ids(playlist: Playlist) -> list[str]:
    return [
        item.track_id
        for item in sorted(playlist.items, key=lambda item: item.order_index)
        if item.track_id
    ]


def _rendered_snapshot_matches_current_tracks(playlist: Playlist, key: str) -> bool:
    rendered_track_ids = (playlist.metadata_json or {}).get(key)
    if not rendered_track_ids:
        return True
    return list(rendered_track_ids) == _playlist_track_ids(playlist)


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

        rendered_track_ids = [track.id for track in tracks]
        output_path = Path(self.settings.playlists_dir) / f"{playlist.id}.mp3"
        rendered_path = self.services.playlist_builder.build_audio(tracks, output_path)
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
        if loop_video_path and Path(loop_video_path).exists():
            playlist.output_video_path = str(
                self._call_builder_with_progress(
                    self.services.playlist_builder.build_looped_video,
                    Path(loop_video_path),
                    audio_path,
                    video_path,
                    smooth_loop=bool(meta.get("loop_video_smooth", True)),
                    progress_callback=progress_callback,
                    total_duration_seconds=total_duration_seconds,
                )
            )
            meta["loop_video_render_mode"] = "smooth-forward-crossfade" if meta.get("loop_video_smooth", True) else "hard-loop"
        elif workspace_mode == "single_track_video" and self.services.dreamina.get_status()["ready"]:
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
                    smooth_loop=True,
                    progress_callback=progress_callback,
                    total_duration_seconds=total_duration_seconds,
                )
            )
            meta["dreamina_job_id"] = clip.job_id
            meta["dreamina_video_url"] = clip.video_url
            meta["loop_video_path"] = str(downloaded_clip)
            meta["loop_video_source"] = "dreamina-useapi"
            meta["loop_video_smooth"] = True
            meta["loop_video_render_mode"] = "smooth-forward-crossfade"
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
        tracks = [
            item.track
            for item in sorted(playlist.items, key=lambda item: item.order_index)
            if item.track is not None
        ]
        youtube_metadata = self.services.release_metadata.build_youtube_metadata(playlist, tracks)
        render_meta = meta
        meta = self._current_playlist_meta(db, playlist.id, fallback=meta)
        for key in (
            "dreamina_job_id",
            "dreamina_video_url",
            "loop_video_path",
            "loop_video_render_mode",
            "loop_video_smooth",
            "loop_video_source",
        ):
            if key in render_meta:
                meta[key] = render_meta[key]
        meta["youtube_title"] = youtube_metadata.title
        meta["youtube_description"] = youtube_metadata.description
        meta["youtube_tags"] = youtube_metadata.tags
        meta["youtube_default_language"] = normalize_youtube_language(
            getattr(youtube_metadata, "default_language", DEFAULT_YOUTUBE_LANGUAGE)
        )
        meta["youtube_localizations"] = normalize_youtube_localizations(
            getattr(youtube_metadata, "localizations", {}),
            default_title=youtube_metadata.title,
            default_description=youtube_metadata.description,
            default_language=meta["youtube_default_language"],
        )
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
            "youtube_title": youtube_metadata.title,
            "progress": meta["video_render_progress"],
        }
        db.add(playlist)
        db.add(job)

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
        if not _rendered_snapshot_matches_current_tracks(playlist, "rendered_video_track_ids"):
            raise ValueError("Rendered video is stale because the track list changed. Re-render video before final YouTube upload.")
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
        default_language = normalize_youtube_language(meta.get("youtube_default_language"))
        localizations = normalize_youtube_localizations(
            meta.get("youtube_localizations"),
            default_title=title,
            default_description=description,
            default_language=default_language,
        )
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
                        localizations=localizations,
                        default_language=default_language,
                    )
                    uploaded_video_path = playlist.output_video_path
                    playlist.youtube_video_id = result.video_id
                    playlist.status = PlaylistStatus.uploaded
                    meta["workflow_state"] = "uploaded"
                    meta["youtube_response"] = result.response
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
                    if self.settings.openclaw_auto_request_next_on_publish:
                        sent_for_video_id = str(meta.get("openclaw_next_request_youtube_video_id") or "").strip()
                        if playlist.youtube_video_id and sent_for_video_id != playlist.youtube_video_id:
                            try:
                                next_request_result = asyncio.run(
                                    post_next_playlist_request(
                                        db,
                                        self.services,
                                        playlist,
                                    )
                                )
                            except Exception as slack_exc:  # noqa: BLE001
                                next_request_result = {"ok": False, "error": str(slack_exc)}
                            meta["openclaw_next_request"] = next_request_result
                            meta["openclaw_next_request_at"] = _utcnow().isoformat()
                            if next_request_result.get("ok"):
                                meta["openclaw_next_request_youtube_video_id"] = playlist.youtube_video_id
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
        is_tokyo_visual = BackgroundJobWorker._uses_tokyo_daydream_visuals(playlist, tracks)
        channel_title = str(meta.get("youtube_channel_title") or "").strip()
        if not channel_title:
            channel_title = "Tokyo Daydream Radio" if is_tokyo_visual else "Soft Hour Radio"
        watermark_prompt = (
            f'The uploaded first-frame image contains the exact lower-left channel label "{channel_title}". '
            "Preserve this text exactly for the full clip. Do not rewrite, translate, blur, morph, move, hide, "
            "flicker, or change it. Keep the text area stable and animate only the surrounding scene subtly. "
            "No other text, subtitles, logos, UI, or title words."
        )
        signature_prompt = (
            "Signature composition for Tokyo Daydream Radio/J-pop only: exactly three people seen from behind, "
            "walking away from the camera into the scene. The viewer sees their backs and backs of heads, "
            "not front-facing faces. One continuous forward-moving shot with subtle camera-follow movement from behind, "
            "final moment close to the opening composition without becoming frozen, "
            "stable composition, no repeated segment, no hard cuts, no subtitles, no extra people or characters. "
            f"{watermark_prompt}"
        )
        soft_hour_prompt = (
            "Soft Hour Radio/background-music visual system: calm, restrained visual concept matched to the release. "
            "Let the release concept and first frame decide the subject; do not force a fixed recurring mascot, "
            "character count, scene list, or camera composition. Use subtle motion derived from the first frame. "
            "The final moment should return close to the opening composition without becoming frozen. "
            "No repeated segment, no hard cuts, no subtitles, no logos, no UI. "
            f"{watermark_prompt}"
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
                f"{watermark_prompt}"
            )
        return (
            "Cinematic background-music visualizer shot for Soft Hour Radio: calm, restrained illustrated scene matched to the release concept. "
            "Animated/anime/illustrated style, not photorealistic or live-action. Subtle motion derived from the first frame, final moment close to the opening composition, stable composition, no fixed recurring character/scene template, no repeated segment. "
            f"{watermark_prompt}"
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
            "jpop",
            "japanese pop",
            "city pop",
            "citypop",
            "anime",
            "shibuya",
            "shinjuku",
            "일본",
            "도쿄",
            "제이팝",
            "시티팝",
            "애니",
            "日本",
            "東京",
            "シティポップ",
            "アニメ",
        )
        return any(marker in haystack for marker in tokyo_markers)
