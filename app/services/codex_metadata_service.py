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
from app.utils.youtube_localizations import (
    ensure_playlist_localization_title_prefix,
    ensure_playlist_title_prefix,
    normalize_youtube_language,
    normalize_youtube_localizations,
    sanitize_youtube_copy,
)
from app.utils.timeline import timeline_from_track_dicts


SPANISH_METADATA_KEYWORDS = (
    "solwave radio",
    "latin pop",
    "spanish pop",
    "spanish vocal",
    "reggaeton",
    "reggaetón",
    "bachata",
    "salsa",
    "cumbia",
    "urbano latino",
    "pop latino",
    "musica latina",
    "música latina",
    "verano latino",
    "라틴",
    "라틴팝",
    "레게톤",
    "스페니쉬",
    "스페인어",
    "스페인어 팝",
)
ENGLISH_POP_METADATA_KEYWORDS = (
    "sundaze",
    "english pop",
    "american pop",
    "us pop",
    "uk pop",
    "western pop",
    "mainstream pop",
    "pop song",
    "pop vocal",
    "미국 팝",
    "미국팝",
    "영어 팝",
    "영어팝",
    "팝송",
)


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
        default_language = self._infer_metadata_default_language(playlist, tracks)
        prompt = self._build_prompt(playlist, tracks, default_language=default_language)
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
            workspace_mode = str((playlist.metadata_json or {}).get("workspace_mode") or "playlist")
            is_playlist_release = workspace_mode != "single_track_video"
            title = ensure_playlist_title_prefix(payload.get("title"), is_playlist=is_playlist_release)
            description = self._clean_description_timestamps(
                sanitize_youtube_copy(payload.get("description")).strip(),
                playlist,
                tracks,
            )
            tags = self._normalize_tags(payload.get("tags") or [])
            if not title or not description:
                raise RuntimeError("codex returned empty title or description")
            localizations = ensure_playlist_localization_title_prefix(
                normalize_youtube_localizations(
                    payload.get("localizations"),
                    default_title=title,
                    default_description=description,
                    default_language=default_language,
                ),
                is_playlist=is_playlist_release,
            )
            localizations = self._normalize_localization_timestamps(localizations, playlist, tracks)
            return YouTubeMetadata(
                title=title[:100],
                description=description,
                tags=tags or ["ai music", "playlist", "background music"],
                provider="codex",
                localizations=localizations,
                default_language=default_language,
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

    def _build_prompt(self, playlist: Playlist, tracks: list[Track], *, default_language: str) -> str:
        default_language = normalize_youtube_language(default_language)
        context = self._metadata_context(playlist, tracks, default_language=default_language)
        return "\n".join(
            [
                "You are writing YouTube metadata for an AI music release dashboard.",
                "Return only JSON that matches the provided output schema.",
                "",
                "Rules:",
                "- Do not run shell commands or inspect files; use only the release context JSON below.",
                f"- The main upload metadata language is {default_language}. Write the top-level title and description in that language.",
                "- If the main language is ko, the ko localization must match the top-level title/description.",
                "- If the main language is en, the en localization must match the top-level title/description.",
                "- If the main language is es, the es localization must match the top-level title/description.",
                "- In Korean title/description/localizations, never use the transliterated words '인스트루멘털', '인스투르멘털', or '인스트루멘탈'. Use natural Korean such as 'BGM', '가사 없는 BGM', '보컬 없는 BGM', or '연주곡' instead.",
                "- Also write localized YouTube metadata for Korean, Japanese, English, Spanish, Vietnamese, Thai, Hindi, Simplified Chinese, and Traditional Chinese in localizations. Use language keys exactly: ko, ja, en, es, vi, th, hi, zh-CN, zh-TW.",
                "- Localizations that are not the main language should be natural translations/adaptations, not machine-looking literal copies.",
                "- For Solwave Radio, Latin pop, Spanish pop, reggaeton, bachata, salsa, cumbia, urbano latino, or Spanish-language pop releases, write the main metadata in Spanish and keep lyrics/title language Spanish-forward.",
                "- For sundaze, English pop, American pop, US/UK pop, western pop, or mainstream English pop releases, write the main metadata in English and keep lyrics/title language English-forward.",
                "- Keep title under 100 characters.",
                "- For playlist releases, every YouTube title in every language must start exactly with '[playlist]'.",
                "- After '[playlist]', do not repeat playlist nouns such as '플레이리스트', 'Playlist', 'プレイリスト', or 'lista de reproducción'. Use music/mix/radio wording instead.",
                "- Do not add process/tool details like OpenClaw, Suno, Codex, or AI workflow unless the release title explicitly asks for it.",
                "- For playlist releases, put listening use cases directly in the title, not only the description. Prefer titles like: <study/walk/drive/rest use case> + <mood/genre/duration> | <secondary use cases>.",
                "- For BGM playlists, the title should answer why someone would click now: studying, working, walking, driving, reading, sleeping, or resting.",
                "- For Japan/J-pop/Tokyo Daydream Radio titles, do not over-emphasize the language. Prefer 'J-POP', 'Tokyo', city-pop, mood, and listening use cases. Avoid Korean title phrases like '일본어 J-pop', '일본어 보컬', or '일본어 카페 재즈' unless the human explicitly asks to highlight the language. If language matters, mention it naturally in the description instead.",
                "- For sundaze and Solwave Radio, titles should feel like curated editorial or Essential playlists, not raw workspace names. Use a vivid situation/emotion plus channel genre identity plus listening use case.",
                "- Avoid short generic pop-channel labels like 'Golden Hour Drive Pop', 'Ruta Dorada Pop', 'English Pop', 'Spanish Pop', or 'Latin Pop' by themselves.",
                "- Good sundaze title example: [playlist] Sunset Highway Pop Drive | Windows Down Road Trip Music.",
                "- Good Solwave Radio title example: [playlist] Pop Latino para Ruta al Atardecer | Carretera, Verano y Buenas Vibras.",
                "- For playlist releases, do not append 'Official AI Visualizer' or similar branding to the title.",
                "- For playlist releases, the description must follow this structure:",
                "  1. One short mood paragraph in the main upload metadata language.",
                "  2. One short paragraph in the main upload metadata language about sound, atmosphere, and use cases.",
                "  3. A heading exactly like: 🎧 Recommended for",
                "  4. One slash-separated use-case line in the main upload metadata language.",
                "  5. A timestamped tracklist using the fixed start times and playback order from timeline.",
                "  6. One final hashtag line with 5-8 relevant hashtags.",
                "- For single-track releases, write as one standalone song/release.",
                "- For single-track releases, do not present the release as a playlist and do not include a timestamp tracklist unless the release title explicitly asks for it.",
                "- Use prompt, style, tags, and lyrics as private creative context; do not paste raw generation settings into the public description.",
                "- For timestamped tracklists, use each timeline item's start exactly and keep the same row order.",
                "- If release.timeline_timestamp_format is HH:MM:SS, keep every timestamp in that exact three-part form, including 00:00:00 at the first row and 01:00:00+ for rows past one hour.",
                "- For Japan/J-pop/Tokyo Daydream Radio releases, write localized timeline rows this way: Korean description = Japanese title plus Korean translation in parentheses, Japanese description = Japanese title only, and English, Spanish, Vietnamese, Thai, Hindi, Simplified Chinese, and Traditional Chinese descriptions = translated title text only.",
                "- Example Korean timeline row for a Japan release: 00:03:22 海辺のきらめき (해변의 반짝임). Example Japanese: 00:03:22 海辺のきらめき. Example English: 00:03:22 Seaside Sparkle. Example Spanish: 00:03:22 Destello junto al mar.",
                "- Do not show A/B, 1/2, or artificial pair labels in metadata titles. If two tracks read like variants of the same title, rewrite only the displayed title text so each row is unique and natural.",
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

    def _metadata_context(
        self,
        playlist: Playlist,
        tracks: list[Track],
        *,
        default_language: str | None = None,
    ) -> dict[str, Any]:
        meta = playlist.metadata_json or {}
        timeline = timeline_from_track_dicts(
            self._track_timeline_dicts(tracks),
            meta.get("rendered_timeline") or [],
        )
        total_seconds = 0
        if timeline:
            last = timeline[-1]
            total_seconds = int(last["start_seconds"]) + int(last["duration_seconds"])
        force_hours = total_seconds >= 3600

        return {
            "release": {
                "id": playlist.id,
                "title": playlist.title,
                "description": meta.get("description"),
                "workspace_mode": meta.get("workspace_mode") or "playlist",
                "actual_duration_seconds": playlist.actual_duration_seconds,
                "target_duration_seconds": playlist.target_duration_seconds,
                "default_hashtags": self.settings.youtube_default_hashtags,
                "youtube_channel_title": meta.get("youtube_channel_title"),
            },
            "metadata_default_language": normalize_youtube_language(default_language),
            "timeline_timestamp_format": "HH:MM:SS" if force_hours else "MM:SS",
            "timeline": timeline,
            "display_timestamp_lines": [f"{item['start']} {item['display_title_hint']}" for item in timeline],
            "raw_timestamp_lines": [f"{item['start']} {item['title']}" for item in timeline],
        }

    def _infer_metadata_default_language(self, playlist: Playlist, tracks: list[Track]) -> str:
        meta = playlist.metadata_json or {}
        haystack = " ".join(
            [
                playlist.title,
                str(meta.get("description") or ""),
                str(meta.get("youtube_channel_title") or ""),
                str(meta.get("youtube_channel_id") or ""),
                " ".join(track.title for track in tracks),
                " ".join(str(track.prompt or "") for track in tracks),
                " ".join(str((track.metadata_json or {}).get("tags") or "") for track in tracks),
                " ".join(str((track.metadata_json or {}).get("style") or "") for track in tracks),
            ]
        ).lower()
        if any(keyword in haystack for keyword in SPANISH_METADATA_KEYWORDS):
            return "es"
        if any(keyword in haystack for keyword in ENGLISH_POP_METADATA_KEYWORDS):
            return "en"
        return "ko"

    def _clean_description_timestamps(self, description: str, playlist: Playlist, tracks: list[Track]) -> str:
        timeline = self._metadata_context(playlist, tracks)["timeline"]
        replacements: dict[str, tuple[str, str, str]] = {}
        force_hours = sum(max(int(item["duration_seconds"] or 0), 0) for item in timeline) >= 3600
        for item in timeline:
            start_seconds = int(item["start_seconds"])
            canonical_start = str(item["start"])
            replacements[canonical_start] = (str(item["title"]), str(item["display_title_hint"]), canonical_start)
            replacements[self._format_timestamp(start_seconds, force_hours=not force_hours)] = (
                str(item["title"]),
                str(item["display_title_hint"]),
                canonical_start,
            )
            replacements[self._format_unpadded_hour_timestamp(start_seconds)] = (
                str(item["title"]),
                str(item["display_title_hint"]),
                canonical_start,
            )

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
            original_title, display_title, canonical_start = replacements[start]
            if line_title.strip() == original_title or self._has_trailing_ab_label(line_title):
                cleaned_lines.append(f"{canonical_start} {display_title}")
            else:
                cleaned_lines.append(f"{canonical_start} {line_title}")
        return "\n".join(cleaned_lines).strip()

    def _normalize_localization_timestamps(
        self,
        localizations: dict[str, dict[str, str]],
        playlist: Playlist,
        tracks: list[Track],
    ) -> dict[str, dict[str, str]]:
        if not localizations:
            return localizations
        timestamp_map = self._timestamp_aliases(playlist, tracks)
        normalized: dict[str, dict[str, str]] = {}
        for language, payload in localizations.items():
            description_lines = []
            for line in str(payload.get("description") or "").splitlines():
                match = re.match(r"^(\d{1,2}:\d{2}(?::\d{2})?)\s+(.+)$", line.strip())
                if match and match.group(1) in timestamp_map:
                    description_lines.append(f"{timestamp_map[match.group(1)]} {match.group(2)}")
                else:
                    description_lines.append(line)
            normalized[language] = {
                "title": str(payload.get("title") or "").strip()[:100],
                "description": "\n".join(description_lines).strip(),
            }
        return normalized

    def _timestamp_aliases(self, playlist: Playlist, tracks: list[Track]) -> dict[str, str]:
        aliases: dict[str, str] = {}
        timeline = self._metadata_context(playlist, tracks)["timeline"]
        force_hours = sum(max(int(item["duration_seconds"] or 0), 0) for item in timeline) >= 3600
        for item in timeline:
            start_seconds = int(item["start_seconds"])
            canonical_start = str(item["start"])
            aliases[canonical_start] = canonical_start
            aliases[self._format_timestamp(start_seconds, force_hours=not force_hours)] = canonical_start
            aliases[self._format_unpadded_hour_timestamp(start_seconds)] = canonical_start
        return aliases

    def _track_timeline_dicts(self, tracks: list[Track]) -> list[dict[str, Any]]:
        values = []
        for track in tracks:
            meta = track.metadata_json or {}
            values.append(
                {
                    "id": track.id,
                    "title": track.title,
                    "duration_seconds": track.duration_seconds,
                    "prompt": track.prompt,
                    "tags": meta.get("tags"),
                    "lyrics": str(meta.get("lyrics") or ""),
                    "style": str(meta.get("style") or ""),
                }
            )
        return values

    def _has_trailing_ab_label(self, title: str) -> bool:
        return bool(re.search(r"\s*(?:[-_]\s*)?\(?[AB]\)?$", title.strip(), flags=re.IGNORECASE))

    def _json_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "additionalProperties": False,
            "required": ["title", "description", "tags", "localizations"],
            "properties": {
                "title": {"type": "string", "minLength": 1, "maxLength": 100},
                "description": {"type": "string", "minLength": 1},
                "tags": {
                    "type": "array",
                    "items": {"type": "string", "minLength": 1},
                    "maxItems": 15,
                },
                "localizations": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["ko", "ja", "en", "es", "vi", "th", "hi", "zh-CN", "zh-TW"],
                    "properties": {
                        "ko": {"$ref": "#/$defs/localizedMetadata"},
                        "ja": {"$ref": "#/$defs/localizedMetadata"},
                        "en": {"$ref": "#/$defs/localizedMetadata"},
                        "es": {"$ref": "#/$defs/localizedMetadata"},
                        "vi": {"$ref": "#/$defs/localizedMetadata"},
                        "th": {"$ref": "#/$defs/localizedMetadata"},
                        "hi": {"$ref": "#/$defs/localizedMetadata"},
                        "zh-CN": {"$ref": "#/$defs/localizedMetadata"},
                        "zh-TW": {"$ref": "#/$defs/localizedMetadata"},
                    },
                },
            },
            "$defs": {
                "localizedMetadata": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["title", "description"],
                    "properties": {
                        "title": {"type": "string", "minLength": 1, "maxLength": 100},
                        "description": {"type": "string", "minLength": 1},
                    },
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

    def _format_timestamp(self, seconds: int, *, force_hours: bool = False) -> str:
        seconds = max(seconds, 0)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        remainder = seconds % 60
        if force_hours:
            return f"{hours:02d}:{minutes:02d}:{remainder:02d}"
        if hours:
            return f"{hours}:{minutes:02d}:{remainder:02d}"
        return f"{minutes:02d}:{remainder:02d}"

    def _format_unpadded_hour_timestamp(self, seconds: int) -> str:
        seconds = max(seconds, 0)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        remainder = seconds % 60
        return f"{hours}:{minutes:02d}:{remainder:02d}"

    def _format_duration(self, seconds: int) -> str:
        minutes = max(seconds, 0) // 60
        remainder = max(seconds, 0) % 60
        return f"{minutes}:{remainder:02d}"

    def _short_error(self, exc: Exception) -> str:
        text = str(exc).strip().replace("\n", " ")
        if not text:
            return exc.__class__.__name__
        return text[:300]
