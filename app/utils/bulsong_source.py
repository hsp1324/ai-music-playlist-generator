from datetime import datetime, timezone
from typing import Any


BULSONG_SOURCE_MAP_FIELDS = (
    "source_name",
    "source_section_or_reference",
    "core_teaching",
    "ordinary_language_paraphrase",
    "verse_hook_expression",
)


def validate_bulsong_source_map(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("Bulsong tracks require a source map object.")

    normalized = dict(value)
    missing = []
    for field in BULSONG_SOURCE_MAP_FIELDS:
        text = str(value.get(field) or "").strip()
        if not text:
            missing.append(field)
        else:
            normalized[field] = text
    if missing:
        raise ValueError(
            "Bulsong source map is missing required fields: " + ", ".join(missing)
        )
    return normalized


def bulsong_quality_monitoring_enabled(metadata: dict[str, Any] | None) -> bool:
    meta = metadata or {}
    target_channel = str(meta.get("target_youtube_channel_title") or "").strip().casefold()
    return bool(
        meta.get("bulsong_quality_monitoring_enabled")
        or meta.get("bulsong_source_fidelity_required")
        or target_channel in {"불송", "bulsong"}
    )


def make_bulsong_quality_warning(
    *,
    code: str,
    stage: str,
    message: str,
    track_id: str | None = None,
    track_title: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    detected_at = datetime.now(timezone.utc).isoformat()
    warning: dict[str, Any] = {
        "code": code,
        "severity": "warning",
        "stage": stage,
        "message": message,
        "detected_at": detected_at,
        "last_detected_at": detected_at,
        "occurrences": 1,
    }
    if track_id:
        warning["track_id"] = track_id
    if track_title:
        warning["track_title"] = track_title
    if details:
        warning["details"] = details
    return warning


def append_bulsong_quality_warning(
    metadata: dict[str, Any],
    warning: dict[str, Any],
    *,
    limit: int = 200,
) -> dict[str, Any]:
    warnings = [
        dict(value)
        for value in metadata.get("bulsong_quality_warnings") or []
        if isinstance(value, dict)
    ]
    warning_key = (
        warning.get("code"),
        warning.get("stage"),
        warning.get("track_id"),
        warning.get("message"),
    )
    for existing in reversed(warnings):
        existing_key = (
            existing.get("code"),
            existing.get("stage"),
            existing.get("track_id"),
            existing.get("message"),
        )
        if existing_key != warning_key:
            continue
        existing["last_detected_at"] = warning.get("last_detected_at") or warning.get(
            "detected_at"
        )
        existing["occurrences"] = int(existing.get("occurrences") or 1) + 1
        if warning.get("details"):
            existing["details"] = warning["details"]
        metadata["bulsong_quality_warnings"] = warnings[-limit:]
        return existing

    warnings.append(dict(warning))
    metadata["bulsong_quality_warnings"] = warnings[-limit:]
    return warning
