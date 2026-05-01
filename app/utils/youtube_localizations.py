from __future__ import annotations

from typing import Any


DEFAULT_YOUTUBE_LANGUAGE = "ko"
SUPPORTED_YOUTUBE_LANGUAGES = ("ko", "ja", "en")


def normalize_youtube_language(value: Any, *, fallback: str = DEFAULT_YOUTUBE_LANGUAGE) -> str:
    language = str(value or "").strip().lower().replace("_", "-")
    if language in SUPPORTED_YOUTUBE_LANGUAGES:
        return language
    return fallback


def normalize_youtube_localizations(
    value: Any,
    *,
    default_title: str | None = None,
    default_description: str | None = None,
    default_language: str = DEFAULT_YOUTUBE_LANGUAGE,
) -> dict[str, dict[str, str]]:
    default_language = normalize_youtube_language(default_language)
    result: dict[str, dict[str, str]] = {}
    if isinstance(value, dict):
        for raw_language, raw_payload in value.items():
            language = normalize_youtube_language(raw_language, fallback="")
            if language not in SUPPORTED_YOUTUBE_LANGUAGES or not isinstance(raw_payload, dict):
                continue
            title = str(raw_payload.get("title") or "").strip()
            description = str(raw_payload.get("description") or "").strip()
            if title and description:
                result[language] = {
                    "title": title[:100],
                    "description": description,
                }

    fallback_title = str(default_title or "").strip()
    fallback_description = str(default_description or "").strip()
    if fallback_title and fallback_description and default_language not in result:
        result[default_language] = {
            "title": fallback_title[:100],
            "description": fallback_description,
        }
    return {language: result[language] for language in SUPPORTED_YOUTUBE_LANGUAGES if language in result}


def localizations_for_youtube_api(
    localizations: dict[str, dict[str, str]],
    *,
    default_language: str = DEFAULT_YOUTUBE_LANGUAGE,
) -> dict[str, dict[str, str]]:
    default_language = normalize_youtube_language(default_language)
    return {
        language: payload
        for language, payload in normalize_youtube_localizations(localizations).items()
        if language != default_language
    }
