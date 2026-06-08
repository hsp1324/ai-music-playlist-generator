from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable, Mapping
from typing import Any


GENRE_TOKEN_VERSION = 4
GENRE_TOKEN_METADATA_KEY = "genre_tokens"
GENRE_TOKEN_VERSION_METADATA_KEY = "genre_token_version"
GENRE_TOKEN_HASH_METADATA_KEY = "genre_token_source_hash"
AI_GENRE_TOKEN_VERSION = 1
AI_GENRE_TOKEN_METADATA_KEY = "ai_genre_tokens"
AI_GENRE_TOKEN_VERSION_METADATA_KEY = "ai_genre_token_version"
AI_GENRE_TOKEN_HASH_METADATA_KEY = "ai_genre_token_source_hash"
AI_GENRE_LABEL_METADATA_KEY = "ai_genre_label"
AI_GENRE_CONFIDENCE_METADATA_KEY = "ai_genre_confidence"

GENRE_PATTERNS: dict[str, tuple[str, ...]] = {
    "afro-house": ("afro house", "afro-house"),
    "afrobeats": ("afrobeats", "afrobeat"),
    "afropop": ("afropop", "afro pop", "afro-pop"),
    "alt-pop": ("alt pop", "alt-pop", "alternative pop"),
    "amapiano": ("amapiano", "amapiano-pop", "amapiano pop"),
    "americana": ("americana", "americana pop"),
    "anime": ("anime", "anime-pop", "anime pop"),
    "bachata": ("bachata",),
    "ballad": ("ballad", "발라드"),
    "bass-house": ("bass house", "bass-house"),
    "bgm": ("bgm", "background music", "no-vocal", "no vocal", "instrumental", "무보컬", "연주곡"),
    "bedroom-pop": ("bedroom pop", "bedroom-pop"),
    "boom-bap": ("boom bap", "boom-bap", "boombap", "붐뱁"),
    "cinematic": ("cinematic", "film score", "movie ost", "trailer", "epic", "heroic"),
    "city-pop": ("city pop", "city-pop", "citypop", "시티팝"),
    "club": ("club", "party", "festival", "rave"),
    "country-pop": ("country pop", "country-pop"),
    "cumbia": ("cumbia",),
    "dance-pop": ("dance pop", "dance-pop", "idol pop", "idol-pop", "댄스팝", "아이돌"),
    "deep-house": ("deep house", "deep-house"),
    "disco": ("disco", "disco-pop", "disco pop"),
    "dnb": ("dnb", "drum and bass", "drum & bass", "liquid dnb"),
    "edm": ("edm", "electronic dance"),
    "folk": ("folk", "folk-pop", "folk pop", "acoustic", "어쿠스틱"),
    "funk": ("funk", "funk-pop", "funk pop"),
    "game": ("game bgm", "game music", "arcade", "rpg", "gaming"),
    "gospel": ("gospel",),
    "hip-hop": (
        "hip hop",
        "hip-hop",
        "boom bap",
        "boom-bap",
        "boombap",
        "rap-pop",
        "rap pop",
        "trap",
        "trap-pop",
        "trap pop",
        "rap",
        "랩",
        "힙합",
        "붐뱁",
        "트랩",
    ),
    "house": ("house",),
    "indie-pop": ("indie pop", "indie-pop"),
    "jazz": ("jazz", "재즈"),
    "jpop": ("j-pop", "jpop", "japanese pop", "제이팝"),
    "kpop": ("k-pop", "kpop", "korean pop", "케이팝", "한국어 팝"),
    "latin-pop": ("latin pop", "pop latino", "spanish pop"),
    "lofi": ("lofi", "lo-fi", "로파이"),
    "melodic-techno": ("melodic techno", "melodic-techno"),
    "neo-soul": ("neo soul", "neo-soul"),
    "orchestral": ("orchestra", "orchestral", "symphonic"),
    "piano": ("piano", "keys", "피아노"),
    "pop": ("pop",),
    "pop-punk": ("pop punk", "pop-punk"),
    "pop-rock": ("pop rock", "pop-rock", "팝록"),
    "rap-pop": ("rap pop", "rap-pop", "sung rap", "sung-rap"),
    "reggaeton": ("reggaeton", "urbano"),
    "rnb": ("r&b", "rnb", "neo soul", "neo-soul", "soul", "알앤비", "소울"),
    "salsa": ("salsa",),
    "scripture": ("scripture", "worship", "prayer", "bible"),
    "singer-songwriter": ("singer songwriter", "singer-songwriter"),
    "solo-piano": ("solo piano", "piano solo", "felt piano", "피아노 솔로", "솔로 피아노"),
    "soft-rock": ("soft rock", "soft-rock", "adult contemporary", "adult-contemporary"),
    "street-pop": ("street pop", "street-pop", "dark street-pop", "dark street pop"),
    "synth-pop": ("synth pop", "synth-pop", "신스팝"),
    "tech-house": ("tech house", "tech-house"),
    "techno": ("techno",),
    "trap": ("trap", "trap-pop", "trap pop", "trap-soul", "trap soul", "808", "트랩"),
    "trance": ("trance",),
    "tropical-house": ("tropical house", "tropical-house"),
    "uk-garage": ("uk garage", "uk-garage", "garage"),
    "urbano": ("urbano", "urbano latino"),
    "y2k-pop": ("y2k pop", "y2k-pop", "recession pop", "recession-pop"),
}

TRACK_GENRE_METADATA_FIELDS = (
    "style",
    "genre",
    "suno_style",
    "music_style",
    "tags",
)


def _metadata_text_values(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for nested in value.values():
            yield from _metadata_text_values(nested)
    elif isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray)):
        for nested in value:
            yield from _metadata_text_values(nested)


def _needle_matches_text(needle: str, *, raw_text: str, normalized_text: str) -> bool:
    clean_needle = str(needle or "").strip().lower()
    if not clean_needle:
        return False
    if re.search(r"[가-힣]", clean_needle):
        return clean_needle in raw_text
    normalized_needle = re.sub(r"[^a-z0-9&+-]+", " ", clean_needle).strip()
    return bool(normalized_needle and f" {normalized_needle} " in normalized_text)


def extract_genre_tokens_from_values(values: Iterable[Any]) -> tuple[str, ...]:
    flat_values = [text for value in values for text in _metadata_text_values(value)]
    raw_text = " ".join(str(value or "").lower() for value in flat_values)
    normalized_text = " " + re.sub(r"[^a-z0-9&+-]+", " ", raw_text) + " "
    tokens = {
        token
        for token, needles in GENRE_PATTERNS.items()
        if any(_needle_matches_text(needle, raw_text=raw_text, normalized_text=normalized_text) for needle in needles)
    }
    _apply_contextual_token_rules(tokens, raw_text=raw_text, normalized_text=normalized_text)
    return tuple(sorted(tokens))


def _has_any_phrase(phrases: Iterable[str], *, raw_text: str, normalized_text: str) -> bool:
    return any(_needle_matches_text(phrase, raw_text=raw_text, normalized_text=normalized_text) for phrase in phrases)


def _apply_contextual_token_rules(tokens: set[str], *, raw_text: str, normalized_text: str) -> None:
    korean_context = _has_any_phrase(
        ("korean", "korea", "seoul", "hongdae", "itaewon", "한국", "한국어", "서울", "홍대", "이태원"),
        raw_text=raw_text,
        normalized_text=normalized_text,
    )
    if korean_context and tokens & {
        "ballad",
        "boom-bap",
        "city-pop",
        "dance-pop",
        "hip-hop",
        "neo-soul",
        "pop",
        "pop-rock",
        "rap-pop",
        "rnb",
        "street-pop",
        "synth-pop",
        "trap",
    }:
        tokens.add("kpop")

    japan_context = _has_any_phrase(
        ("japanese", "japan", "tokyo", "shibuya", "shinjuku", "일본", "도쿄", "시부야", "신주쿠"),
        raw_text=raw_text,
        normalized_text=normalized_text,
    )
    if japan_context and tokens & {
        "anime",
        "boom-bap",
        "city-pop",
        "dance-pop",
        "hip-hop",
        "neo-soul",
        "pop",
        "pop-rock",
        "rap-pop",
        "rnb",
        "street-pop",
        "synth-pop",
        "trap",
    }:
        tokens.add("jpop")


def track_genre_token_values(*, title: str, prompt: str, metadata: Mapping[str, Any]) -> list[Any]:
    values: list[Any] = [title, prompt]
    values.extend(metadata.get(field) for field in TRACK_GENRE_METADATA_FIELDS)
    return values


def track_genre_token_source_hash(*, title: str, prompt: str, metadata: Mapping[str, Any]) -> str:
    source = "\n".join(str(value or "") for value in track_genre_token_values(title=title, prompt=prompt, metadata=metadata))
    return hashlib.sha1(source.encode("utf-8")).hexdigest()


def track_genre_tokens(*, title: str, prompt: str, metadata: Mapping[str, Any]) -> tuple[str, ...]:
    return extract_genre_tokens_from_values(track_genre_token_values(title=title, prompt=prompt, metadata=metadata))


def normalize_genre_token(value: Any) -> str:
    token = re.sub(r"[^a-z0-9가-힣&+-]+", "-", str(value or "").strip().lower())
    token = re.sub(r"-+", "-", token).strip("-")
    aliases = {
        "citypop": "city-pop",
        "city-pop-kpop": "city-pop",
        "k-pop": "kpop",
        "j-pop": "jpop",
        "afro-pop": "afropop",
        "amapiano-pop": "amapiano",
        "americana-pop": "americana",
        "boombap": "boom-bap",
        "country": "country-pop",
        "r-b": "rnb",
        "rnb": "rnb",
        "hiphop": "hip-hop",
        "hip-hop-pop": "rap-pop",
        "trap-pop": "trap",
    }
    return aliases.get(token, token)


def normalize_genre_tokens(values: Iterable[Any]) -> tuple[str, ...]:
    return tuple(sorted({token for value in values if (token := normalize_genre_token(value))}))


def update_track_genre_token_metadata(
    metadata: Mapping[str, Any] | None,
    *,
    title: str,
    prompt: str,
) -> dict[str, Any]:
    updated = dict(metadata or {})
    tokens = track_genre_tokens(title=title, prompt=prompt, metadata=updated)
    updated[GENRE_TOKEN_METADATA_KEY] = list(tokens)
    updated[GENRE_TOKEN_VERSION_METADATA_KEY] = GENRE_TOKEN_VERSION
    updated[GENRE_TOKEN_HASH_METADATA_KEY] = track_genre_token_source_hash(
        title=title,
        prompt=prompt,
        metadata=updated,
    )
    return updated


def current_ai_genre_tokens(
    metadata: Mapping[str, Any] | None,
    *,
    title: str,
    prompt: str,
) -> tuple[str, ...]:
    meta = dict(metadata or {})
    expected_hash = track_genre_token_source_hash(title=title, prompt=prompt, metadata=meta)
    if (
        meta.get(AI_GENRE_TOKEN_VERSION_METADATA_KEY) != AI_GENRE_TOKEN_VERSION
        or meta.get(AI_GENRE_TOKEN_HASH_METADATA_KEY) != expected_hash
    ):
        return ()
    return normalize_genre_tokens(meta.get(AI_GENRE_TOKEN_METADATA_KEY) or [])


def update_track_ai_genre_token_metadata(
    metadata: Mapping[str, Any] | None,
    *,
    title: str,
    prompt: str,
    tokens: Iterable[Any],
    label: str | None = None,
    confidence: float | int | None = None,
    provider: str = "codex",
) -> dict[str, Any]:
    updated = dict(metadata or {})
    normalized_tokens = normalize_genre_tokens(tokens)
    updated[AI_GENRE_TOKEN_METADATA_KEY] = list(normalized_tokens)
    updated[AI_GENRE_TOKEN_VERSION_METADATA_KEY] = AI_GENRE_TOKEN_VERSION
    updated[AI_GENRE_TOKEN_HASH_METADATA_KEY] = track_genre_token_source_hash(
        title=title,
        prompt=prompt,
        metadata=updated,
    )
    updated["ai_genre_provider"] = provider
    if label is not None:
        updated[AI_GENRE_LABEL_METADATA_KEY] = str(label or "").strip()
    if confidence is not None:
        try:
            updated[AI_GENRE_CONFIDENCE_METADATA_KEY] = max(0.0, min(float(confidence), 1.0))
        except (TypeError, ValueError):
            pass
    return updated


def cached_track_genre_tokens(track: Any, *, update_missing: bool = True) -> tuple[str, ...]:
    metadata = dict(getattr(track, "metadata_json", None) or {})
    title = str(getattr(track, "title", "") or "")
    prompt = str(getattr(track, "prompt", "") or "")
    expected_hash = track_genre_token_source_hash(title=title, prompt=prompt, metadata=metadata)
    cached_tokens = metadata.get(GENRE_TOKEN_METADATA_KEY)
    if (
        metadata.get(GENRE_TOKEN_VERSION_METADATA_KEY) == GENRE_TOKEN_VERSION
        and metadata.get(GENRE_TOKEN_HASH_METADATA_KEY) == expected_hash
        and isinstance(cached_tokens, list)
    ):
        rule_tokens = normalize_genre_tokens(cached_tokens)
        ai_tokens = current_ai_genre_tokens(metadata, title=title, prompt=prompt)
        return normalize_genre_tokens([*rule_tokens, *ai_tokens])

    tokens = track_genre_tokens(title=title, prompt=prompt, metadata=metadata)
    if update_missing:
        metadata[GENRE_TOKEN_METADATA_KEY] = list(tokens)
        metadata[GENRE_TOKEN_VERSION_METADATA_KEY] = GENRE_TOKEN_VERSION
        metadata[GENRE_TOKEN_HASH_METADATA_KEY] = expected_hash
        track.metadata_json = metadata
    ai_tokens = current_ai_genre_tokens(metadata, title=title, prompt=prompt)
    return normalize_genre_tokens([*tokens, *ai_tokens])
