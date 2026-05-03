from __future__ import annotations

from typing import Any


DEFAULT_YOUTUBE_LANGUAGE = "ko"
SUPPORTED_YOUTUBE_LANGUAGES = ("ko", "ja", "en", "es")


def sanitize_youtube_copy(value: Any) -> str:
    text = str(value or "")
    replacements = (
        ("가사가 없는 인스투르멘털 음악", "가사가 없는 BGM"),
        ("가사가 없는 인스트루멘털 음악", "가사가 없는 BGM"),
        ("보컬 없는 인스투르멘털 음악", "보컬 없는 BGM"),
        ("보컬 없는 인스트루멘털 음악", "보컬 없는 BGM"),
        ("J-pop 감성 인스투르멘털", "J-pop 감성 BGM"),
        ("J-pop 감성 인스트루멘털", "J-pop 감성 BGM"),
        ("인스투르멘털 J-pop", "가사 없는 J-pop 감성 BGM"),
        ("인스트루멘털 J-pop", "가사 없는 J-pop 감성 BGM"),
        ("인스투르멘털 음악", "가사 없는 BGM"),
        ("인스트루멘털 음악", "가사 없는 BGM"),
        ("인스투르멘털 플레이리스트", "BGM 플레이리스트"),
        ("인스트루멘털 플레이리스트", "BGM 플레이리스트"),
        ("인스투르멘탈", "BGM"),
        ("인스트루멘탈", "BGM"),
        ("인스투르멘털", "BGM"),
        ("인스트루멘털", "BGM"),
    )
    for source, target in replacements:
        text = text.replace(source, target)
    return text


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
            title = sanitize_youtube_copy(raw_payload.get("title")).strip()
            description = sanitize_youtube_copy(raw_payload.get("description")).strip()
            if title and description:
                result[language] = {
                    "title": title[:100],
                    "description": description,
                }

    fallback_title = sanitize_youtube_copy(default_title).strip()
    fallback_description = sanitize_youtube_copy(default_description).strip()
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
