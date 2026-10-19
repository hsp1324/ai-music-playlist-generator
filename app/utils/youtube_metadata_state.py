from __future__ import annotations

from typing import Any

from app.utils.youtube_localizations import (
    DEFAULT_YOUTUBE_LANGUAGE,
    ensure_youtube_description_request_cta,
    ensure_playlist_localization_title_prefix,
    normalize_youtube_language,
    normalize_youtube_localizations,
    single_release_youtube_title,
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
    single_track_title: str | None = None,
) -> None:
    meta["youtube_title"] = youtube_metadata.title
    meta["youtube_description"] = youtube_metadata.description
    meta["youtube_tags"] = youtube_metadata.tags
    meta["youtube_default_language"] = normalize_youtube_language(
        getattr(youtube_metadata, "default_language", DEFAULT_YOUTUBE_LANGUAGE)
    )
    meta["youtube_description"] = ensure_youtube_description_request_cta(
        meta["youtube_description"],
        language=meta["youtube_default_language"],
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
    for language, localized_copy in meta["youtube_localizations"].items():
        localized_copy["description"] = ensure_youtube_description_request_cta(
            localized_copy.get("description"),
            language=language,
        )
    if not is_playlist_release and single_track_title:
        fixed_title = single_release_youtube_title(single_track_title)
        meta["youtube_title"] = fixed_title
        for localized_copy in meta["youtube_localizations"].values():
            localized_copy["title"] = fixed_title
    meta["metadata_provider"] = getattr(youtube_metadata, "provider", "template")
    if getattr(youtube_metadata, "error", None):
        meta["metadata_generation_error"] = youtube_metadata.error
    else:
        meta.pop("metadata_generation_error", None)
