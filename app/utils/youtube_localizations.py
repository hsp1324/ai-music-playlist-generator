from __future__ import annotations

import re
from typing import Any


DEFAULT_YOUTUBE_LANGUAGE = "ko"
SUPPORTED_YOUTUBE_LANGUAGES = (
    "ko",
    "ja",
    "en",
    "es",
    "vi",
    "th",
    "hi",
    "fil",
    "id",
    "tr",
    "pt-BR",
    "pt-PT",
    "fr",
    "de",
    "ar",
    "zh-CN",
    "zh-TW",
)
YOUTUBE_LANGUAGE_ALIASES = {
    "ko": "ko",
    "kr": "ko",
    "korean": "ko",
    "ja": "ja",
    "jp": "ja",
    "japanese": "ja",
    "en": "en",
    "english": "en",
    "es": "es",
    "spanish": "es",
    "vi": "vi",
    "vn": "vi",
    "vietnamese": "vi",
    "th": "th",
    "thai": "th",
    "hi": "hi",
    "hindi": "hi",
    "india": "hi",
    "indian": "hi",
    "fil": "fil",
    "filipino": "fil",
    "tagalog": "fil",
    "tl": "fil",
    "id": "id",
    "indonesian": "id",
    "bahasa": "id",
    "bahasa-indonesia": "id",
    "tr": "tr",
    "turkish": "tr",
    "turkiye": "tr",
    "türkiye": "tr",
    "pt": "pt-BR",
    "pt-br": "pt-BR",
    "portuguese": "pt-BR",
    "brazilian-portuguese": "pt-BR",
    "portuguese-brazil": "pt-BR",
    "pt-pt": "pt-PT",
    "portuguese-portugal": "pt-PT",
    "portugal-portuguese": "pt-PT",
    "european-portuguese": "pt-PT",
    "fr": "fr",
    "french": "fr",
    "de": "de",
    "german": "de",
    "ar": "ar",
    "ar-eg": "ar",
    "arabic": "ar",
    "egypt": "ar",
    "egyptian": "ar",
    "egyptian-arabic": "ar",
    "zh": "zh-CN",
    "zh-cn": "zh-CN",
    "chinese": "zh-CN",
    "chinese-simplified": "zh-CN",
    "simplified-chinese": "zh-CN",
    "zh-tw": "zh-TW",
    "tw": "zh-TW",
    "taiwan": "zh-TW",
    "taiwanese": "zh-TW",
    "traditional-chinese": "zh-TW",
    "chinese-traditional": "zh-TW",
}
PLAYLIST_TITLE_PREFIX = "[playlist]"
SINGLE_RELEASE_TITLE_SUFFIX = "AI 음원 싱글곡"
YOUTUBE_DESCRIPTION_REQUEST_CTA = {
    "ko": "댓글로 듣고 싶은 음악 스타일을 남겨주세요. 다음 플레이리스트로 만들어 드릴게요.",
    "ja": "コメントで聴きたい音楽スタイルを教えてください。次のプレイリストとしてお届けします。",
    "en": "Leave the music style you'd like to hear in the comments. We'll turn it into a future playlist.",
    "es": "Cuéntanos en los comentarios qué estilo de música quieres escuchar. Lo convertiremos en una próxima playlist.",
    "vi": "Hãy để lại phong cách âm nhạc bạn muốn nghe trong phần bình luận. Chúng tôi sẽ biến nó thành một playlist sắp tới.",
    "th": "บอกสไตล์เพลงที่คุณอยากฟังไว้ในคอมเมนต์ แล้วเราจะนำไปทำเป็นเพลย์ลิสต์ถัดไป",
    "hi": "कमेंट में बताएं कि आप किस तरह का संगीत सुनना चाहते हैं। हम उसे आने वाली प्लेलिस्ट में बनाएंगे।",
    "fil": "I-comment ang music style na gusto mong marinig. Gagawin namin itong isa sa mga susunod na playlist.",
    "id": "Tulis gaya musik yang ingin kamu dengar di komentar. Kami akan membuatnya menjadi playlist berikutnya.",
    "tr": "Dinlemek istediğiniz müzik tarzını yorumlara yazın. Onu gelecek çalma listelerimizden birine dönüştürelim.",
    "pt-BR": "Conte nos comentários qual estilo musical você quer ouvir. Vamos transformá-lo em uma próxima playlist.",
    "pt-PT": "Diz nos comentários que estilo musical gostarias de ouvir. Vamos transformá-lo numa próxima playlist.",
    "fr": "Indiquez en commentaire le style de musique que vous aimeriez écouter. Nous en ferons une prochaine playlist.",
    "de": "Schreib uns in die Kommentare, welchen Musikstil du hören möchtest. Wir machen daraus eine der nächsten Playlists.",
    "ar": "اكتب في التعليقات نوع الموسيقى الذي تود سماعه، وسنحوّله إلى قائمة تشغيل قادمة.",
    "zh-CN": "请在评论区告诉我们你想听的音乐风格，我们会把它做成接下来的播放列表。",
    "zh-TW": "請在留言區告訴我們你想聽的音樂風格，我們會把它做成接下來的播放清單。",
}


def ensure_youtube_description_request_cta(
    value: Any,
    *,
    language: str = DEFAULT_YOUTUBE_LANGUAGE,
) -> str:
    """Keep one localized listener-request call to action as the final paragraph."""
    description = sanitize_youtube_copy(value).strip()
    if not description:
        return description

    cta = YOUTUBE_DESCRIPTION_REQUEST_CTA[normalize_youtube_language(language)]
    known_ctas = set(YOUTUBE_DESCRIPTION_REQUEST_CTA.values())
    lines = [line for line in description.splitlines() if line.strip() not in known_ctas]
    description = "\n".join(lines).strip()
    return f"{description}\n\n{cta}" if description else cta

PUBLIC_TITLE_GARAGE_REPLACEMENTS = (
    (r"(?:UK\s*)?(?:개러지|거라지)", "댄스 음악"),
    (r"(?:UK\s*)?(?:ガラージ|ガレージ)", "ダンスミュージック"),
    (r"(?:UK\s*)?(?:车库音乐|車庫音樂)", "流行舞曲"),
    (r"\b(?:UK\s*)?garage\b", "Dance Music"),
    (r"\bUKG\b", "Dance Music"),
)


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


def sanitize_public_youtube_title(value: Any) -> str:
    """Keep niche garage labels out of public titles without changing style metadata."""

    title = sanitize_youtube_copy(value)
    for pattern, replacement in PUBLIC_TITLE_GARAGE_REPLACEMENTS:
        title = re.sub(pattern, replacement, title, flags=re.IGNORECASE)
    title = re.sub(
        r"\bDance Music(?:\s+Dance Music)+\b",
        "Dance Music",
        title,
        flags=re.IGNORECASE,
    )
    return re.sub(r"\s+", " ", title).strip()


def normalize_playlist_title_body(value: Any) -> str:
    title = re.sub(
        r"^\s*\[playlist\]\s*",
        "",
        sanitize_public_youtube_title(value),
        flags=re.IGNORECASE,
    )
    replacements = (
        (r"듣기\s*좋은\s*플레이\s*리스트", "듣기 좋은 음악"),
        (r"듣는\s*플레이\s*리스트", "듣기 좋은 음악"),
        (r"(\S+용)\s*플레이\s*리스트", r"\1 음악"),
        (r"\b([Ww]ork|[Ss]tudy|[Dd]rive|[Ww]alk|[Ss]leep|[Rr]elax|[Rr]eading|[Rr]unning)\s+[Pp]laylist\b", r"\1 Music"),
        (r"\b[Pp]laylist\s+for\b", "Music for"),
        (r"\b[Pp]laylist\b", "Music"),
        (r"プレイリスト|プレーリスト", "音楽"),
        (r"lista\s+de\s+reproducci[oó]n", "música"),
        (r"플레이\s*리스트", ""),
    )
    for pattern, replacement in replacements:
        title = re.sub(pattern, replacement, title, flags=re.IGNORECASE)
    title = re.sub(r"\s+", " ", title).strip(" |·,-")
    title = re.sub(r"\s+([|·,])", r" \1", title)
    title = re.sub(r"([|·,])\s+", r"\1 ", title)
    return title.strip()


def ensure_playlist_title_prefix(value: Any, *, is_playlist: bool) -> str:
    title = sanitize_public_youtube_title(value)
    if not is_playlist:
        return title[:100]
    title = normalize_playlist_title_body(title)
    if not title:
        return ""
    return f"{PLAYLIST_TITLE_PREFIX} {title}"[:100]


def single_release_youtube_title(value: Any) -> str:
    """Keep standalone releases song-first with the user-approved AI single label."""
    song_title = sanitize_youtube_copy(value).strip()
    suffix = f" | {SINGLE_RELEASE_TITLE_SUFFIX}"
    if song_title.endswith(suffix):
        song_title = song_title[: -len(suffix)].rstrip()
    max_song_title_length = max(100 - len(suffix), 1)
    song_title = song_title[:max_song_title_length].rstrip()
    return f"{song_title}{suffix}" if song_title else SINGLE_RELEASE_TITLE_SUFFIX


def ensure_playlist_localization_title_prefix(
    localizations: dict[str, dict[str, str]],
    *,
    is_playlist: bool,
) -> dict[str, dict[str, str]]:
    if not is_playlist:
        return localizations
    return {
        language: {
            **payload,
            "title": ensure_playlist_title_prefix(payload.get("title"), is_playlist=True),
        }
        for language, payload in localizations.items()
    }


def normalize_youtube_language(value: Any, *, fallback: str = DEFAULT_YOUTUBE_LANGUAGE) -> str:
    language = str(value or "").strip().lower().replace("_", "-")
    if language in YOUTUBE_LANGUAGE_ALIASES:
        return YOUTUBE_LANGUAGE_ALIASES[language]
    fallback_language = str(fallback or "").strip().lower().replace("_", "-")
    if fallback_language in YOUTUBE_LANGUAGE_ALIASES:
        return YOUTUBE_LANGUAGE_ALIASES[fallback_language]
    return DEFAULT_YOUTUBE_LANGUAGE


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
            title = sanitize_public_youtube_title(raw_payload.get("title"))
            description = sanitize_youtube_copy(raw_payload.get("description")).strip()
            if title and description:
                result[language] = {
                    "title": title[:100],
                    "description": description,
                }

    fallback_title = sanitize_public_youtube_title(default_title)
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
