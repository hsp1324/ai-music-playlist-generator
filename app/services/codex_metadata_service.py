from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Any

from app.config import Settings
from app.models.playlist import Playlist
from app.models.track import Track
from app.services.release_metadata_service import ReleaseMetadataService, YouTubeMetadata


class CodexMetadataService(ReleaseMetadataService):
    """Generate YouTube metadata with Codex CLI, falling back to deterministic templates."""

    def __init__(self, settings: Settings, fallback: ReleaseMetadataService) -> None:
        self.settings = settings
        self.fallback = fallback
        self._lock = threading.Lock()
        self._project_root = Path(__file__).resolve().parents[2]

    def build_youtube_metadata(self, playlist: Playlist, tracks: list[Track]) -> YouTubeMetadata:
        if not self.settings.codex_metadata_enabled:
            return self.fallback.build_youtube_metadata(playlist, tracks)

        acquired = self._lock.acquire(blocking=False)
        if not acquired:
            return self._fallback_with_error(
                playlist,
                tracks,
                "Codex metadata generation is already running; used template fallback.",
            )

        try:
            return self._build_with_codex(playlist, tracks)
        except Exception as exc:
            return self._fallback_with_error(
                playlist,
                tracks,
                f"Codex metadata generation failed: {self._short_error(exc)}",
            )
        finally:
            self._lock.release()

    def _build_with_codex(self, playlist: Playlist, tracks: list[Track]) -> YouTubeMetadata:
        command = self._resolve_codex_command()
        prompt = self._build_prompt(playlist, tracks)
        schema = self._json_schema()
        timeout = max(int(self.settings.codex_metadata_timeout_seconds), 30)

        with tempfile.TemporaryDirectory(prefix="aimp-codex-metadata-") as temp_dir:
            temp_path = Path(temp_dir)
            output_path = temp_path / "metadata.json"
            schema_path = temp_path / "schema.json"
            schema_path.write_text(json.dumps(schema, ensure_ascii=False), encoding="utf-8")

            cmd = [
                command,
                "exec",
                "--ephemeral",
                "--sandbox",
                "read-only",
                "--cd",
                str(self._project_root),
                "--output-schema",
                str(schema_path),
                "-o",
                str(output_path),
            ]
            if self.settings.codex_metadata_model.strip():
                cmd.extend(["--model", self.settings.codex_metadata_model.strip()])
            cmd.append("-")

            env = dict(os.environ)
            env["NO_COLOR"] = "1"
            result = subprocess.run(
                cmd,
                input=prompt,
                text=True,
                capture_output=True,
                timeout=timeout,
                check=False,
                cwd=self._project_root,
                env=env,
            )
            if result.returncode != 0:
                stderr = result.stderr.strip() or result.stdout.strip()
                raise RuntimeError(stderr or f"codex exited with status {result.returncode}")
            if not output_path.exists():
                raise RuntimeError("codex did not write a metadata output file")

            payload = self._parse_json_output(output_path.read_text(encoding="utf-8"))
            title = str(payload.get("title") or "").strip()
            description = self._clean_description_timestamps(
                str(payload.get("description") or "").strip(),
                tracks,
            )
            tags = self._normalize_tags(payload.get("tags") or [])
            if not title or not description:
                raise RuntimeError("codex returned empty title or description")
            return YouTubeMetadata(
                title=title[:100],
                description=description,
                tags=tags or ["ai music", "playlist", "background music"],
                provider="codex",
            )

    def _fallback_with_error(self, playlist: Playlist, tracks: list[Track], error: str) -> YouTubeMetadata:
        metadata = self.fallback.build_youtube_metadata(playlist, tracks)
        return YouTubeMetadata(
            title=metadata.title,
            description=metadata.description,
            tags=metadata.tags,
            provider="template",
            error=error,
        )

    def _resolve_codex_command(self) -> str:
        command = self.settings.codex_metadata_command.strip() or "codex"
        if "/" in command:
            if Path(command).exists():
                return command
            raise RuntimeError(f"codex command not found: {command}")
        resolved = shutil.which(command)
        if not resolved:
            raise RuntimeError(f"codex command not found: {command}")
        return resolved

    def _build_prompt(self, playlist: Playlist, tracks: list[Track]) -> str:
        context = self._metadata_context(playlist, tracks)
        return "\n".join(
            [
                "You are writing YouTube metadata for an AI music release dashboard.",
                "Return only JSON that matches the provided output schema.",
                "",
                "Rules:",
                "- Do not run shell commands or inspect files; use only the release context JSON below.",
                "- Write primarily in Korean unless the release title strongly suggests another language.",
                "- Keep title under 100 characters.",
                "- Do not add process/tool details like OpenClaw, Suno, Codex, or AI workflow unless the release title explicitly asks for it.",
                "- For playlist releases, write the title like: <mood/genre/duration> | <listening use cases>.",
                "- For playlist releases, do not append 'Official AI Visualizer' or similar branding to the title.",
                "- For playlist releases, the description must follow this structure:",
                "  1. One short Korean mood paragraph.",
                "  2. One short Korean paragraph about sound, atmosphere, and use cases.",
                "  3. A heading exactly like: 🎧 Recommended for",
                "  4. One slash-separated Korean use-case line.",
                "  5. A timestamped tracklist using the fixed start times and playback order from timeline.",
                "  6. One final hashtag line with 5-8 relevant hashtags.",
                "- For single-track releases, keep the same clean YouTube style but no timestamp list is required unless useful.",
                "- For timestamped tracklists, use each timeline item's start exactly and keep the same row order.",
                "- Do not show trailing A/B labels in metadata titles. If two tracks share the same base title after removing A/B, rewrite only the displayed title text so each row is unique and natural.",
                "- Use display_title_hint as a starting point, but you may make the displayed titles more natural while preserving each row's timestamp.",
                "- Timestamp positions are fixed playback positions. Never swap timestamps between tracks to make titles alphabetical or A/B ordered.",
                "- If a track title is later corrected, only the title text should change; the timestamp and playback position must stay fixed.",
                "- Do not invent, remove, rename, or reorder tracks.",
                "- Tags must be plain strings without # symbols, no more than 15 tags.",
                "- Do not include Markdown code fences.",
                "",
                "Release context JSON:",
                json.dumps(context, ensure_ascii=False, indent=2),
            ]
        )

    def _metadata_context(self, playlist: Playlist, tracks: list[Track]) -> dict[str, Any]:
        meta = playlist.metadata_json or {}
        timeline = []
        offset = 0
        display_titles = self._display_track_titles(tracks)
        for index, (track, display_title) in enumerate(zip(tracks, display_titles), start=1):
            track_meta = track.metadata_json or {}
            duration = max(int(track.duration_seconds or 0), 0)
            timeline.append(
                {
                    "index": index,
                    "start": self._format_timestamp(offset),
                    "title": track.title,
                    "display_title_hint": display_title,
                    "duration_seconds": duration,
                    "duration": self._format_duration(duration),
                    "prompt": track.prompt,
                    "tags": track_meta.get("tags"),
                }
            )
            offset += duration

        return {
            "release": {
                "id": playlist.id,
                "title": playlist.title,
                "description": meta.get("description"),
                "workspace_mode": meta.get("workspace_mode") or "playlist",
                "actual_duration_seconds": playlist.actual_duration_seconds,
                "target_duration_seconds": playlist.target_duration_seconds,
                "default_hashtags": self.settings.youtube_default_hashtags,
            },
            "timeline": timeline,
            "display_timestamp_lines": [f"{item['start']} {item['display_title_hint']}" for item in timeline],
            "raw_timestamp_lines": [f"{item['start']} {item['title']}" for item in timeline],
        }

    def _clean_description_timestamps(self, description: str, tracks: list[Track]) -> str:
        display_titles = self._display_track_titles(tracks)
        offset = 0
        replacements: dict[str, tuple[str, str]] = {}
        for track, display_title in zip(tracks, display_titles):
            start = self._format_timestamp(offset)
            replacements[start] = (track.title, display_title)
            offset += max(int(track.duration_seconds or 0), 0)

        cleaned_lines = []
        for line in description.splitlines():
            match = re.match(r"^(\d{1,2}:\d{2}(?::\d{2})?)\s+(.+)$", line.strip())
            if not match:
                cleaned_lines.append(line)
                continue
            start, line_title = match.groups()
            if start not in replacements:
                cleaned_lines.append(line)
                continue
            original_title, display_title = replacements[start]
            if line_title.strip() == original_title or self._has_trailing_ab_label(line_title):
                cleaned_lines.append(f"{start} {display_title}")
            else:
                cleaned_lines.append(line)
        return "\n".join(cleaned_lines).strip()

    def _has_trailing_ab_label(self, title: str) -> bool:
        return bool(re.search(r"\s*(?:[-_]\s*)?\(?[AB]\)?$", title.strip(), flags=re.IGNORECASE))

    def _json_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "additionalProperties": False,
            "required": ["title", "description", "tags"],
            "properties": {
                "title": {"type": "string", "minLength": 1, "maxLength": 100},
                "description": {"type": "string", "minLength": 1},
                "tags": {
                    "type": "array",
                    "items": {"type": "string", "minLength": 1},
                    "maxItems": 15,
                },
            },
        }

    def _parse_json_output(self, raw: str) -> dict[str, Any]:
        text = raw.strip()
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            fenced = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
            if fenced:
                payload = json.loads(fenced.group(1).strip())
            else:
                start = text.find("{")
                end = text.rfind("}")
                if start < 0 or end <= start:
                    raise
                payload = json.loads(text[start : end + 1])
        if not isinstance(payload, dict):
            raise RuntimeError("codex metadata output must be a JSON object")
        return payload

    def _normalize_tags(self, value: Any) -> list[str]:
        candidates = value.split(",") if isinstance(value, str) else list(value or [])
        normalized: list[str] = []
        seen: set[str] = set()
        for candidate in candidates:
            tag = str(candidate).strip().lstrip("#").strip()
            if not tag:
                continue
            key = tag.lower()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(tag)
        return normalized[:15]

    def _format_timestamp(self, seconds: int) -> str:
        seconds = max(seconds, 0)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        remainder = seconds % 60
        if hours:
            return f"{hours}:{minutes:02d}:{remainder:02d}"
        return f"{minutes:02d}:{remainder:02d}"

    def _format_duration(self, seconds: int) -> str:
        minutes = max(seconds, 0) // 60
        remainder = max(seconds, 0) % 60
        return f"{minutes}:{remainder:02d}"

    def _short_error(self, exc: Exception) -> str:
        text = str(exc).strip().replace("\n", " ")
        if not text:
            return exc.__class__.__name__
        return text[:300]
