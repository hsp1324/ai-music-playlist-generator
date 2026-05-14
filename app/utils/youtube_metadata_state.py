from __future__ import annotations

from typing import Any

from app.utils.youtube_localizations import (
    DEFAULT_YOUTUBE_LANGUAGE,
    ensure_playlist_localization_title_prefix,
    normalize_youtube_language,
    normalize_youtube_localizations,
)


def has_youtube_metadata(meta: dict[str, Any]) -> bool:
    return bool(
        str(meta.get("youtube_title") or "").strip()
        and str(meta.get("youtube_description") or "").strip()
    )


def apply_generated_youtube_metadata(
    meta: dict[str, Any],
    youtube_metadata: Any,
    *,
    is_playlist_release: bool,
) -> None:
    meta["youtube_title"] = youtube_metadata.title
    meta["youtube_description"] = youtube_metadata.description
    meta["youtube_tags"] = youtube_metadata.tags
    meta["youtube_default_language"] = normalize_youtube_language(
        getattr(youtube_metadata, "default_language", DEFAULT_YOUTUBE_LANGUAGE)
    )
    meta["youtube_localizations"] = ensure_playlist_localization_title_prefix(
        normalize_youtube_localizations(
            getattr(youtube_metadata, "localizations", {}),
            default_title=meta["youtube_title"],
            default_description=youtube_metadata.description,
            default_language=meta["youtube_default_language"],
        ),
        is_playlist=is_playlist_release,
    )
    meta["metadata_provider"] = getattr(youtube_metadata, "provider", "template")
    if getattr(youtube_metadata, "error", None):
        meta["metadata_generation_error"] = youtube_metadata.error
    else:
        meta.pop("metadata_generation_error", None)
