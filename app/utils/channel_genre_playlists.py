from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ChannelGenreRule:
    style_lane: str
    broad_genre: str
    playlist_titles: tuple[str, ...]
    keywords: tuple[str, ...]
    title_only: bool = False


@dataclass(frozen=True)
class ChannelGenreClassification:
    channel_title: str | None = None
    style_lane: str | None = None
    broad_genre: str | None = None
    playlist_titles: tuple[str, ...] = ()
    matched_keywords: tuple[str, ...] = ()


CHANNEL_TITLE_ALIASES = {
    "ai썰전": "Club Bloom",
    "ai sseoljeon": "Club Bloom",
    "the old verse": "BibliaCanto",
    "old verse": "BibliaCanto",
    "biblia canto": "BibliaCanto",
    "bibliacanto": "BibliaCanto",
    "the new verse": "불송",
    "new verse": "불송",
    "bulsong": "불송",
}


CHANNEL_GENRE_RULES: dict[str, tuple[ChannelGenreRule, ...]] = {
    "haruharu": (
        ChannelGenreRule(
            "K-pop boom bap / rap-pop",
            "K-pop Hip-Hop",
            ("K-pop Hip-Hop",),
            ("boom bap", "boombap", "붐뱁"),
        ),
        ChannelGenreRule(
            "K-pop trap / rap-pop",
            "K-pop Hip-Hop",
            ("K-pop Hip-Hop",),
            ("trap", "트랩", "808", "rap-pop", "rap pop", "랩팝", "랩", "rap", "힙합", "hip-hop", "hip hop", "street-pop", "street pop", "스트릿"),
        ),
        ChannelGenreRule(
            "Korean R&B pop",
            "Korean R&B",
            ("Korean R&B",),
            ("korean r&b", "korean rnb", "r&b", "rnb", "알앤비"),
        ),
        ChannelGenreRule(
            "K-pop soul / neo-soul pop",
            "Korean R&B",
            ("Korean R&B",),
            ("neo-soul", "neo soul", "soul", "소울"),
        ),
        ChannelGenreRule(
            "K-pop ballad-pop",
            "K-pop Ballads",
            ("K-pop Ballads",),
            ("ballad", "발라드", "이별", "breakup"),
        ),
        ChannelGenreRule(
            "K-pop synth-pop",
            "K-pop Synth-Pop",
            ("K-pop Synth-Pop",),
            ("city-pop", "city pop", "citypop", "시티팝", "synth-pop", "synth pop", "신스팝", "neon", "네온"),
        ),
        ChannelGenreRule(
            "K-pop pop-rock",
            "K-pop Pop-Rock",
            ("K-pop Pop-Rock",),
            ("pop-rock", "pop rock", "팝록", "guitar pop", "기타 팝"),
        ),
        ChannelGenreRule(
            "K-pop dance-pop / idol-pop",
            "K-pop Dance-Pop",
            ("K-pop Dance-Pop",),
            ("dance-pop", "dance pop", "댄스팝", "idol-pop", "idol pop", "아이돌", "running", "러닝", "workout", "운동", "party", "파티", "외출 준비", "getting ready", "신나는"),
        ),
        ChannelGenreRule(
            "mainstream Korean pop",
            "K-pop Mixes",
            ("K-pop Mixes",),
            ("k-pop", "kpop", "케이팝", "한국어 팝", "korean pop"),
        ),
    ),
    "soft hour radio": (
        ChannelGenreRule(
            "solo piano BGM",
            "Piano BGM",
            ("Piano BGM",),
            (
                "solo piano",
                "piano solo",
                "felt piano",
                "quiet piano",
                "upright piano",
                "piano",
                "피아노",
                "솔로 피아노",
                "피아노 솔로",
                "연주곡",
                "study",
                "공부",
                "focus",
                "집중",
                "work",
                "업무",
                "작업",
                "reading",
                "독서",
                "cafe",
                "카페",
                "sleep",
                "수면",
                "잠들",
                "relax",
                "휴식",
                "bgm",
                "background",
                "무보컬",
                "가사 없는",
                "instrumental",
            ),
        ),
    ),
    "sundaze": (
        ChannelGenreRule(
            "pop hip-hop / rap-pop",
            "Pop Hip-Hop",
            ("Pop Hip-Hop",),
            ("pop hip-hop", "pop hip hop", "rap-pop", "rap pop", "sung-rap", "sung rap", "trap-pop", "trap pop", "808"),
        ),
        ChannelGenreRule(
            "Pop R&B",
            "Pop R&B",
            ("Pop R&B",),
            ("pop r&b", "pop rnb", "r&b", "rnb", "soul-pop", "soul pop", "neo-soul", "neo soul"),
        ),
        ChannelGenreRule("dance-pop", "Dance-Pop", ("Dance-Pop",), ("dance-pop", "dance pop", "party", "workout", "running")),
        ChannelGenreRule("synth-pop", "Synth-Pop", ("Synth-Pop",), ("synth-pop", "synth pop", "neon")),
        ChannelGenreRule("pop-rock / guitar pop", "Pop-Rock", ("Pop-Rock",), ("pop-rock", "pop rock", "guitar pop")),
        ChannelGenreRule("country pop", "Country Pop", ("Country Pop",), ("country pop", "country-pop")),
        ChannelGenreRule(
            "Americana / folk-pop",
            "Americana & Folk Pop",
            ("Americana & Folk Pop",),
            ("americana", "folk-pop", "folk pop", "singer-songwriter", "singer songwriter"),
        ),
        ChannelGenreRule(
            "indie / bedroom / alt-pop",
            "Indie & Alt Pop",
            ("Indie & Alt Pop",),
            ("indie pop", "indie-pop", "bedroom pop", "bedroom-pop", "alt-pop", "alt pop"),
        ),
        ChannelGenreRule(
            "acoustic / ballad pop",
            "Acoustic & Ballad Pop",
            ("Acoustic & Ballad Pop",),
            ("acoustic pop", "ballad", "heartbreak", "rainy bedroom"),
        ),
        ChannelGenreRule(
            "Afropop / Amapiano-pop",
            "Afropop & Amapiano",
            ("Afropop & Amapiano",),
            ("afropop", "afro pop", "afrobeats", "amapiano"),
        ),
        ChannelGenreRule(
            "feel-good English pop",
            "English Pop",
            ("English Pop",),
            ("english pop", "american pop", "feel-good pop", "feel good pop", "sunny pop", "weekend pop", "pop mix"),
        ),
    ),
    "solwave radio": (
        ChannelGenreRule("reggaeton pop", "Reggaeton & Urbano", ("Reggaeton & Urbano",), ("reggaeton", "reggaetón")),
        ChannelGenreRule("urbano latino", "Reggaeton & Urbano", ("Reggaeton & Urbano",), ("urbano", "urban latino")),
        ChannelGenreRule("bachata pop", "Bachata Pop", ("Bachata Pop",), ("bachata",)),
        ChannelGenreRule("salsa pop", "Salsa & Cumbia Pop", ("Salsa & Cumbia Pop",), ("salsa",)),
        ChannelGenreRule("cumbia pop", "Salsa & Cumbia Pop", ("Salsa & Cumbia Pop",), ("cumbia", "쿰비아")),
        ChannelGenreRule(
            "Latin R&B / Spanish R&B",
            "Latin R&B & Soul",
            ("Latin R&B & Soul",),
            ("latin r&b", "spanish r&b", "r&b", "rnb", "latin soul", "neo-soul", "neo soul"),
        ),
        ChannelGenreRule("Latin pop-rock", "Latin Pop-Rock", ("Latin Pop-Rock",), ("pop-rock latino", "latin pop-rock", "pop rock latino")),
        ChannelGenreRule("Pop Latino", "Pop Latino", ("Pop Latino",), ("pop latino", "latin pop", "spanish pop", "verano latino")),
    ),
    "club bloom": (
        ChannelGenreRule("deep house", "House Music", ("House Music",), ("deep house",)),
        ChannelGenreRule("tech house", "House Music", ("House Music",), ("tech house",)),
        ChannelGenreRule("progressive house", "House Music", ("House Music",), ("progressive house",)),
        ChannelGenreRule("future house", "House Music", ("House Music",), ("future house",)),
        ChannelGenreRule("bass house", "Bass Music", ("Bass Music",), ("bass house",)),
        ChannelGenreRule("UK garage", "Bass Music", ("Bass Music",), ("uk garage", "garage")),
        ChannelGenreRule("drum and bass", "Drum & Bass", ("Drum & Bass",), ("drum and bass", "dnb", "liquid dnb")),
        ChannelGenreRule("melodic techno", "Techno", ("Techno",), ("melodic techno",)),
        ChannelGenreRule("peak-time techno", "Techno", ("Techno",), ("peak-time techno", "peak time techno", "techno")),
        ChannelGenreRule("trance / progressive trance", "Trance", ("Trance",), ("progressive trance", "trance")),
        ChannelGenreRule("afro house", "Afro & Tropical House", ("Afro & Tropical House",), ("afro house",)),
        ChannelGenreRule("tropical house", "Afro & Tropical House", ("Afro & Tropical House",), ("tropical house",)),
        ChannelGenreRule("synthwave club", "Synthwave Club", ("Synthwave Club",), ("synthwave",)),
        ChannelGenreRule("trap EDM", "EDM & Festival", ("EDM & Festival",), ("hype trap", "trap edm")),
        ChannelGenreRule("festival / big-room EDM", "EDM & Festival", ("EDM & Festival",), ("festival edm", "big room", "big-room", "electro house", "edm")),
    ),
    "tokyo daydream radio": (
        ChannelGenreRule("J-pop city-pop / synth-pop", "J-pop City & Synth-Pop", ("J-pop City & Synth-Pop",), ("city-pop", "city pop", "시티팝", "synth-pop", "synth pop", "신스팝", "neon", "네온")),
        ChannelGenreRule("J-pop dance-pop", "J-pop Dance-Pop", ("J-pop Dance-Pop",), ("dance-pop", "dance pop", "댄스팝", "night out", "나이트", "party")),
        ChannelGenreRule("J-pop pop-rock", "J-pop Pop-Rock", ("J-pop Pop-Rock",), ("pop-rock", "pop rock", "팝록", "guitar pop", "기타 팝")),
        ChannelGenreRule("anime-pop / arcade J-pop", "Anime & Arcade Pop", ("Anime & Arcade Pop",), ("anime", "anime-pop", "anime pop", "arcade", "오락실", "game")),
        ChannelGenreRule("mainstream J-pop", "J-pop Mixes", ("J-pop Mixes",), ("j-pop", "jpop", "japanese pop", "제이팝")),
    ),
    "cinematic pulse": (
        ChannelGenreRule("dark fantasy orchestra", "Dark Fantasy Cinematic", ("Dark Fantasy Cinematic",), ("dark fantasy", "fantasy orchestra")),
        ChannelGenreRule("sci-fi action score", "Sci-Fi Action Cinematic", ("Sci-Fi Action Cinematic",), ("sci-fi", "sci fi", "cyber", "combat")),
        ChannelGenreRule("emotional film score", "Emotional Film Score", ("Emotional Film Score",), ("emotional", "piano", "hopeful", "strings")),
        ChannelGenreRule("mystery tension score", "Mystery & Tension Score", ("Mystery & Tension Score",), ("mystery", "tension", "suspense")),
        ChannelGenreRule("gentle game orchestra", "Game Orchestra", ("Game Orchestra",), ("game orchestra", "game score", "anime rpg", "action rpg", "fantasy game ost", "soft orchestra", "gentle orchestra", "sweet orchestra")),
        ChannelGenreRule("epic trailer orchestra", "Epic Trailer Music", ("Epic Trailer Music",), ("trailer", "epic", "battle", "orchestra", "cinematic")),
    ),
    "storylight ost": (
        ChannelGenreRule("cute arcade OST", "Cute Game OST", ("Cute Game OST",), ("cute arcade", "arcade", "cute game")),
        ChannelGenreRule("fantasy RPG town music", "Fantasy RPG OST", ("Fantasy RPG OST",), ("fantasy rpg", "rpg", "town music", "village")),
        ChannelGenreRule("anime game BGM", "Anime Game BGM", ("Anime Game BGM",), ("anime", "game bgm", "japanese-style")),
        ChannelGenreRule("cozy story OST", "Cozy Story OST", ("Cozy Story OST",), ("cozy", "storybook", "reading", "whimsical")),
    ),
    "불송": (
        ChannelGenreRule(
            "legacy source-explicit Bulsong",
            "Bulsong Source-Evident Releases",
            ("불송",),
            (
                "불교",
                "불경",
                "법구경",
                "반야심경",
                "금강경",
                "묘법연화경",
                "법화경",
                "경전",
                "부처",
                "부처님",
                "보살",
                "스님",
                "법문",
                "자비",
                "가르침",
                "업보",
                "윤회",
                "해탈",
                "열반",
                "사성제",
                "팔정도",
                "삼도",
                "무상",
                "무아",
                "buddhist",
                "dharma",
                "dhammapada",
                "heart sutra",
                "diamond sutra",
                "lotus sutra",
            ),
            title_only=True,
        ),
        ChannelGenreRule(
            "mainstream Korean hip-hop / rap-pop",
            "Korean Hip-Hop",
            ("노래",),
            (
                "hip-hop",
                "hip hop",
                "rap",
                "boom bap",
                "trap-soul",
                "trap soul",
                "drill",
                "phonk",
                "rap-pop",
                "rap pop",
                "랩",
                "힙합",
                "붐뱁",
                "트랩",
            ),
        ),
        ChannelGenreRule(
            "mainstream Korean R&B / soul",
            "Korean R&B",
            ("노래",),
            ("r&b", "rnb", "soul", "neo-soul", "neo soul", "알앤비", "소울"),
        ),
        ChannelGenreRule(
            "mainstream Korean piano vocal ballad",
            "Korean Ballad",
            ("노래",),
            (
                "piano ballad",
                "piano vocal",
                "quiet piano vocal",
                "piano-only ballad",
                "simple piano accompaniment",
                "ballad",
                "피아노 발라드",
                "피아노 보컬",
                "피아노 반주",
                "잔잔한 피아노",
                "발라드",
            ),
        ),
        ChannelGenreRule(
            "mainstream Korean art pop / electronic",
            "Korean Alternative Pop",
            ("노래",),
            (
                "trip-hop",
                "trip hop",
                "glitch-hop",
                "glitch hop",
                "drum and bass",
                "dnb",
                "uk garage",
                "hyperpop",
                "art-pop",
                "art pop",
                "electronica",
                "dark pop",
                "pop",
                "트립합",
                "글리치",
                "드럼앤베이스",
                "하이퍼팝",
                "아트팝",
                "일렉트로닉",
            ),
        ),
    ),
}

FALLBACK_BROAD_GENRES = {
    "K-pop Mixes",
    "Calm BGM",
    "English Pop",
    "Pop Latino",
    "J-pop Mixes",
}


def canonical_channel_title(value: Any) -> str | None:
    clean = str(value or "").strip()
    if not clean:
        return None
    return CHANNEL_TITLE_ALIASES.get(clean.lower(), clean)


def channel_genre_taxonomy() -> dict[str, tuple[ChannelGenreRule, ...]]:
    return CHANNEL_GENRE_RULES


def _metadata_text_values(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for nested in value.values():
            yield from _metadata_text_values(nested)
    elif isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray)):
        for nested in value:
            yield from _metadata_text_values(nested)


def _track_text(track: Any) -> str:
    meta = getattr(track, "metadata_json", None) or {}
    values: list[Any] = [
        getattr(track, "title", ""),
        getattr(track, "prompt", ""),
        meta.get("style"),
        meta.get("genre"),
        meta.get("suno_style"),
        meta.get("music_style"),
        meta.get("tags"),
    ]
    return " ".join(str(item or "") for value in values for item in _metadata_text_values(value)).lower()


def _classification_haystack(meta: Mapping[str, Any], *, title: str = "") -> str:
    response = meta.get("youtube_response") if isinstance(meta.get("youtube_response"), Mapping) else {}
    snippet = response.get("snippet") if isinstance(response.get("snippet"), Mapping) else {}
    values: list[Any] = [
        title,
        meta.get("youtube_title"),
        meta.get("title"),
        meta.get("description"),
        meta.get("youtube_description"),
        meta.get("youtube_tags"),
        meta.get("music_lane"),
        meta.get("release_music_lane"),
        meta.get("style_lane"),
        snippet.get("title"),
        snippet.get("description"),
        snippet.get("tags"),
    ]
    return " ".join(str(item or "") for value in values for item in _metadata_text_values(value)).lower()


def _title_haystack(meta: Mapping[str, Any], *, title: str = "") -> str:
    response = meta.get("youtube_response") if isinstance(meta.get("youtube_response"), Mapping) else {}
    snippet = response.get("snippet") if isinstance(response.get("snippet"), Mapping) else {}
    values: list[Any] = [
        title,
        meta.get("youtube_title"),
        meta.get("title"),
        snippet.get("title"),
    ]
    return " ".join(str(item or "") for value in values for item in _metadata_text_values(value)).lower()


def _match_rule(rule: ChannelGenreRule, haystack: str) -> tuple[str, ...]:
    return tuple(keyword for keyword in rule.keywords if keyword in haystack)


def infer_channel_genre_classification(
    meta: Mapping[str, Any],
    *,
    title: str = "",
    tracks: Iterable[Any] | None = None,
) -> ChannelGenreClassification:
    channel_title = canonical_channel_title(
        meta.get("youtube_channel_title")
        or meta.get("target_youtube_channel_title")
        or meta.get("scripture_channel_title")
        or meta.get("channel")
    )
    if not channel_title:
        return ChannelGenreClassification()
    rules = CHANNEL_GENRE_RULES.get(channel_title.lower())
    if not rules:
        return ChannelGenreClassification(channel_title=channel_title)

    title_haystack = _title_haystack(meta, title=title)
    specific_rules = tuple(rule for rule in rules if rule.broad_genre not in FALLBACK_BROAD_GENRES)
    fallback_rules = tuple(rule for rule in rules if rule.broad_genre in FALLBACK_BROAD_GENRES)
    for rule in specific_rules:
        matched = _match_rule(rule, title_haystack)
        if matched:
            return ChannelGenreClassification(
                channel_title=channel_title,
                style_lane=rule.style_lane,
                broad_genre=rule.broad_genre,
                playlist_titles=rule.playlist_titles,
                matched_keywords=matched,
            )
    for rule in fallback_rules:
        matched = _match_rule(rule, title_haystack)
        if matched:
            return ChannelGenreClassification(
                channel_title=channel_title,
                style_lane=rule.style_lane,
                broad_genre=rule.broad_genre,
                playlist_titles=rule.playlist_titles,
                matched_keywords=matched,
            )

    haystack = _classification_haystack(meta, title=title)
    for rule in specific_rules:
        if rule.title_only:
            continue
        matched = _match_rule(rule, haystack)
        if matched:
            return ChannelGenreClassification(
                channel_title=channel_title,
                style_lane=rule.style_lane,
                broad_genre=rule.broad_genre,
                playlist_titles=rule.playlist_titles,
                matched_keywords=matched,
            )

    track_texts = [_track_text(track) for track in tracks or []]
    if track_texts:
        minimum_matching_tracks = max(1, int(len(track_texts) * 0.5 + 0.999))
        best_rule: ChannelGenreRule | None = None
        best_matches: tuple[str, ...] = ()
        best_count = 0
        for rule in specific_rules:
            if rule.title_only:
                continue
            rule_matches: list[str] = []
            count = 0
            for track_text in track_texts:
                matched = _match_rule(rule, track_text)
                if matched:
                    count += 1
                    rule_matches.extend(matched)
            if count > best_count:
                best_rule = rule
                best_count = count
                best_matches = tuple(dict.fromkeys(rule_matches))
        if best_rule and best_count >= minimum_matching_tracks:
            return ChannelGenreClassification(
                channel_title=channel_title,
                style_lane=best_rule.style_lane,
                broad_genre=best_rule.broad_genre,
                playlist_titles=best_rule.playlist_titles,
                matched_keywords=best_matches,
            )

    for rule in fallback_rules:
        matched = _match_rule(rule, haystack)
        if matched:
            return ChannelGenreClassification(
                channel_title=channel_title,
                style_lane=rule.style_lane,
                broad_genre=rule.broad_genre,
                playlist_titles=rule.playlist_titles,
                matched_keywords=matched,
            )
    if channel_title == "불송":
        return ChannelGenreClassification(
            channel_title=channel_title,
            style_lane="mainstream Bulsong vocal songs",
            broad_genre="Bulsong Songs",
            playlist_titles=("노래",),
        )
    return ChannelGenreClassification(channel_title=channel_title)


def apply_channel_genre_classification(
    meta: dict[str, Any],
    classification: ChannelGenreClassification,
) -> None:
    if not classification.channel_title:
        return
    meta["channel_genre_channel_title"] = classification.channel_title
    if classification.style_lane:
        meta["channel_style_lane"] = classification.style_lane
    if classification.broad_genre:
        meta["channel_broad_genre"] = classification.broad_genre
    if classification.playlist_titles:
        meta["youtube_genre_playlist_titles"] = list(classification.playlist_titles)
    if classification.matched_keywords:
        meta["channel_genre_matched_keywords"] = list(classification.matched_keywords)
