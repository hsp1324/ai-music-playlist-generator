from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config import Settings
from app.models.playlist import Playlist
from app.models.track import Track
from app.utils.lyric_captions import (
    build_srt_from_lyric_cues,
    cue_texts,
    lyric_cues_with_translated_texts,
)
from app.utils.lyric_subtitles import build_word_aligned_line_lyric_cues, lyric_lines_from_text
from app.utils.youtube_localizations import (
    SUPPORTED_YOUTUBE_LANGUAGES,
    YOUTUBE_LANGUAGE_ALIASES,
    normalize_youtube_language,
)


LANGUAGE_NAMES = {
    "ko": "Korean",
    "ja": "Japanese",
    "en": "English",
    "es": "Spanish",
    "vi": "Vietnamese",
    "th": "Thai",
    "hi": "Hindi",
    "fil": "Filipino",
    "id": "Indonesian",
    "tr": "Turkish",
    "pt-BR": "Brazilian Portuguese",
    "pt-PT": "European Portuguese",
    "fr": "French",
    "de": "German",
    "ar": "Arabic",
    "zh-CN": "Simplified Chinese",
    "zh-TW": "Traditional Chinese",
}

WHISPER_LANGUAGE_ALIASES = {
    "pt-BR": "pt",
    "pt-PT": "pt",
    "zh-CN": "zh",
    "zh-TW": "zh",
    "fil": "tl",
}


@dataclass
class LyricCaptionBuildResult:
    caption_tracks: dict[str, str]
    source_language: str
    cue_count: int
    translation_error: str | None = None
    skipped_reason: str | None = None


class LyricCaptionService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._lock = threading.Lock()
        self._project_root = Path(__file__).resolve().parents[2]

    def build_youtube_caption_tracks(
        self,
        playlist: Playlist,
        tracks: list[Track],
        *,
        audio_path: str | Path,
        default_language: str,
    ) -> LyricCaptionBuildResult:
        source_language = normalize_youtube_language(default_language)
        if not self.settings.youtube_lyrics_captions_enabled:
            return LyricCaptionBuildResult({}, source_language, 0, skipped_reason="disabled")

        track_dicts = self._track_dicts_with_lyrics(tracks)
        if not track_dicts:
            return LyricCaptionBuildResult({}, source_language, 0, skipped_reason="no_lyrics")

        meta = playlist.metadata_json or {}
        alignment_language = self._whisper_language(
            str(self.settings.video_lyrics_alignment_language or "").strip() or source_language
        )
        cues = build_word_aligned_line_lyric_cues(
            track_dicts,
            list(meta.get("rendered_timeline") or []),
            audio_path=audio_path,
            model_size=str(self.settings.video_lyrics_alignment_model or "tiny"),
            language=alignment_language,
            min_score=float(self.settings.video_lyrics_alignment_min_score),
            max_end_seconds=playlist.actual_duration_seconds or None,
        )
        if not cues:
            return LyricCaptionBuildResult({}, source_language, 0, skipped_reason="no_aligned_cues")

        languages = self._caption_languages(source_language)
        targets = [language for language in languages if language != source_language]
        translations: dict[str, list[str]] = {}
        translation_error: str | None = None
        if targets:
            try:
                translations = self._translate_cue_texts(cue_texts(cues), source_language, targets)
            except Exception as exc:  # noqa: BLE001
                translation_error = str(exc)

        caption_tracks: dict[str, str] = {}
        source_srt = build_srt_from_lyric_cues(cues)
        if source_srt.strip():
            caption_tracks[source_language] = source_srt
        for language in targets:
            translated_lines = translations.get(language)
            if not translated_lines:
                continue
            srt = build_srt_from_lyric_cues(lyric_cues_with_translated_texts(cues, translated_lines))
            if srt.strip():
                caption_tracks[language] = srt

        return LyricCaptionBuildResult(
            caption_tracks=caption_tracks,
            source_language=source_language,
            cue_count=len(cues),
            translation_error=translation_error,
        )

    def _track_dicts_with_lyrics(self, tracks: list[Track]) -> list[dict[str, Any]]:
        values: list[dict[str, Any]] = []
        has_lyrics = False
        for track in tracks:
            lyrics = str(track.lyrics or "")
            if lyric_lines_from_text(lyrics):
                has_lyrics = True
            values.append(
                {
                    "id": track.id,
                    "title": track.title,
                    "duration_seconds": track.duration_seconds,
                    "lyrics": lyrics,
                }
            )
        return values if has_lyrics else []

    def _caption_languages(self, source_language: str) -> list[str]:
        raw_languages = str(self.settings.youtube_lyrics_captions_languages or "").strip()
        if raw_languages:
            languages = [self._normalize_supported_language(part) for part in raw_languages.replace(";", ",").split(",")]
            languages = [language for language in languages if language in SUPPORTED_YOUTUBE_LANGUAGES]
        else:
            languages = list(SUPPORTED_YOUTUBE_LANGUAGES)
        if source_language in SUPPORTED_YOUTUBE_LANGUAGES and source_language not in languages:
            languages.insert(0, source_language)
        return list(dict.fromkeys(languages))

    def _translate_cue_texts(
        self,
        texts: list[str],
        source_language: str,
        target_languages: list[str],
    ) -> dict[str, list[str]]:
        if not texts or not target_languages:
            return {}
        if not self.settings.youtube_lyrics_captions_translate:
            return {}

        acquired = self._lock.acquire(blocking=False)
        if not acquired:
            raise RuntimeError("Lyric caption translation is already running.")
        try:
            payload = self._run_codex_translation(texts, source_language, target_languages)
        finally:
            self._lock.release()

        translations = payload.get("translations")
        if not isinstance(translations, dict):
            raise RuntimeError("caption translation did not return translations")
        normalized: dict[str, list[str]] = {}
        for language in target_languages:
            values = translations.get(language)
            if not isinstance(values, list) or len(values) != len(texts):
                continue
            cleaned = [str(value or "").strip() for value in values]
            if all(cleaned):
                normalized[language] = cleaned
        missing = [language for language in target_languages if language not in normalized]
        if missing:
            raise RuntimeError(f"caption translation missing languages: {', '.join(missing)}")
        return normalized

    def _run_codex_translation(
        self,
        texts: list[str],
        source_language: str,
        target_languages: list[str],
    ) -> dict[str, Any]:
        command = self._resolve_codex_command()
        timeout = max(int(self.settings.youtube_lyrics_captions_translation_timeout_seconds), 60)
        with tempfile.TemporaryDirectory(prefix="aimp-lyric-captions-") as temp_dir:
            temp_path = Path(temp_dir)
            output_path = temp_path / "captions.json"
            schema_path = temp_path / "schema.json"
            schema_path.write_text(
                json.dumps(self._translation_schema(target_languages, len(texts)), ensure_ascii=False),
                encoding="utf-8",
            )
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
                input=self._translation_prompt(texts, source_language, target_languages),
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
                raise RuntimeError("codex did not write caption translation output")
            return json.loads(output_path.read_text(encoding="utf-8"))

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

    def _translation_prompt(self, texts: list[str], source_language: str, target_languages: list[str]) -> str:
        language_names = {language: LANGUAGE_NAMES.get(language, language) for language in target_languages}
        return "\n".join(
            [
                "Translate song lyric caption lines for YouTube CC tracks.",
                "Return only JSON that matches the provided schema.",
                "",
                "Rules:",
                "- Preserve the exact number of lines for every target language.",
                "- Preserve line order exactly; line i in every target language must translate source line i.",
                "- Do not add timestamps, numbering, explanations, notes, markdown, or quotation marks around lines.",
                "- Translate naturally for singing lyrics and YouTube subtitles; avoid stiff literal translation.",
                "- Keep names, scripture references, Buddhist terms, and repeated hooks natural in the target language.",
                "- If a line is a short repeated hook, translate it consistently.",
                "",
                "Context JSON:",
                json.dumps(
                    {
                        "source_language": source_language,
                        "target_languages": target_languages,
                        "target_language_names": language_names,
                        "lines": texts,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
            ]
        )

    def _translation_schema(self, target_languages: list[str], line_count: int) -> dict[str, Any]:
        return {
            "type": "object",
            "additionalProperties": False,
            "required": ["translations"],
            "properties": {
                "translations": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": target_languages,
                    "properties": {
                        language: {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": line_count,
                            "maxItems": line_count,
                        }
                        for language in target_languages
                    },
                }
            },
        }

    @staticmethod
    def _whisper_language(language: str | None) -> str | None:
        if not language:
            return None
        normalized = LyricCaptionService._normalize_supported_language(language)
        if not normalized:
            return None
        return WHISPER_LANGUAGE_ALIASES.get(normalized, normalized)

    @staticmethod
    def _normalize_supported_language(language: str | None) -> str | None:
        normalized = str(language or "").strip().lower().replace("_", "-")
        if normalized not in YOUTUBE_LANGUAGE_ALIASES:
            return None
        return YOUTUBE_LANGUAGE_ALIASES[normalized]
