import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow, InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from PIL import Image

from app.config import Settings
from app.models.playlist import Playlist
from app.utils.youtube_localizations import (
    DEFAULT_YOUTUBE_LANGUAGE,
    YOUTUBE_LANGUAGE_ALIASES,
    localizations_for_youtube_api,
    normalize_youtube_language,
    normalize_youtube_localizations,
    sanitize_youtube_copy,
)


YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
YOUTUBE_READONLY_SCOPE = "https://www.googleapis.com/auth/youtube.readonly"
YOUTUBE_UPDATE_SCOPE = "https://www.googleapis.com/auth/youtube.force-ssl"
YOUTUBE_SCOPES = [YOUTUBE_UPLOAD_SCOPE, YOUTUBE_READONLY_SCOPE, YOUTUBE_UPDATE_SCOPE]
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"
YOUTUBE_THUMBNAIL_MAX_BYTES = 2 * 1024 * 1024
YOUTUBE_DURATION_PATTERN = re.compile(
    r"^P(?:\d+Y)?(?:\d+M)?(?:\d+W)?(?:\d+D)?"
    r"(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?)?$"
)


@dataclass
class YouTubeUploadResult:
    video_id: str
    response: dict[str, Any]


class YouTubeService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def get_status(self) -> dict[str, Any]:
        configured = bool(self.settings.youtube_client_secrets_path) and Path(
            self.settings.youtube_client_secrets_path
        ).exists()
        registry = self._read_channel_registry()
        raw_channels = registry.get("channels", [])
        channels = [self._public_channel_payload(channel) for channel in raw_channels]
        selected_channel_id = registry.get("selected_channel_id")
        selected_channel = self._find_channel(raw_channels, selected_channel_id)
        selected_token_status = self._inspect_token(self._channel_token_path(selected_channel_id)) if selected_channel_id else {
            "authenticated": False
        }
        legacy_token_status = self._inspect_token()
        authenticated = selected_token_status["authenticated"] or legacy_token_status["authenticated"]
        ready = configured and authenticated
        return {
            "configured": configured,
            "authenticated": authenticated,
            "ready": ready,
            "channels": channels,
            "selected_channel_id": selected_channel_id,
            "selected_channel_title": selected_channel.get("title") if selected_channel else None,
            "redirect_uri": self.redirect_uri,
            "error": selected_token_status.get("error") or legacy_token_status.get("error"),
        }

    @staticmethod
    def _public_channel_payload(channel: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value
            for key, value in channel.items()
            if key not in {"token_path"}
        }

    @property
    def redirect_uri(self) -> str:
        if self.settings.youtube_oauth_redirect_uri:
            return self.settings.youtube_oauth_redirect_uri
        base_url = self.settings.public_base_url.rstrip("/")
        api_prefix = self.settings.api_prefix.rstrip("/")
        return f"{base_url}{api_prefix}/youtube/oauth/callback"

    @property
    def oauth_session_path(self) -> Path:
        return self.settings.browser_dir / "youtube-oauth-session.json"

    @property
    def channel_registry_path(self) -> Path:
        return self.settings.browser_dir / "youtube-channels.json"

    @property
    def channel_tokens_dir(self) -> Path:
        return self.settings.browser_dir / "youtube-channel-tokens"

    def build_authorization_url(self, playlist_id: str | None = None) -> dict[str, Any]:
        client_secrets = Path(self.settings.youtube_client_secrets_path)
        if not client_secrets.exists():
            raise FileNotFoundError("YouTube client secrets file is not configured.")

        flow = Flow.from_client_secrets_file(
            str(client_secrets),
            scopes=YOUTUBE_SCOPES,
            redirect_uri=self.redirect_uri,
        )
        authorization_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="false",
            prompt="consent",
        )
        self.oauth_session_path.parent.mkdir(parents=True, exist_ok=True)
        session_payload = {
            "state": state,
            "code_verifier": flow.code_verifier,
            "redirect_uri": self.redirect_uri,
        }
        if playlist_id:
            session_payload["playlist_id"] = playlist_id
        self.oauth_session_path.write_text(json.dumps(session_payload), encoding="utf-8")
        return {
            "authorization_url": authorization_url,
            "state": state,
            "redirect_uri": self.redirect_uri,
            "playlist_id": playlist_id,
        }

    def exchange_web_code(self, code: str, state: str | None = None) -> dict[str, Any]:
        client_secrets = Path(self.settings.youtube_client_secrets_path)
        if not client_secrets.exists():
            raise FileNotFoundError("YouTube client secrets file is not configured.")
        if not self.oauth_session_path.exists():
            raise ValueError("YouTube OAuth session is missing. Start Connect YouTube again.")

        session = json.loads(self.oauth_session_path.read_text(encoding="utf-8"))
        expected_state = session.get("state")
        if state and expected_state and state != expected_state:
            raise ValueError("YouTube OAuth state did not match. Start Connect YouTube again.")

        flow = Flow.from_client_secrets_file(
            str(client_secrets),
            scopes=YOUTUBE_SCOPES,
            redirect_uri=session.get("redirect_uri") or self.redirect_uri,
        )
        flow.code_verifier = session.get("code_verifier")
        # The same Google OAuth client is also used by oauth2-proxy for login.
        # Google can return those harmless OIDC scopes with the YouTube scope,
        # so keep oauthlib from rejecting the callback solely for extra scopes.
        previous_relax_scope = os.environ.get("OAUTHLIB_RELAX_TOKEN_SCOPE")
        os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"
        try:
            flow.fetch_token(code=code)
        finally:
            if previous_relax_scope is None:
                os.environ.pop("OAUTHLIB_RELAX_TOKEN_SCOPE", None)
            else:
                os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = previous_relax_scope
        credentials = flow.credentials
        playlist_id = session.get("playlist_id")
        channel = self._fetch_authenticated_channel(credentials)
        channel_id = channel["id"]
        channel_token_path = self._channel_token_path(channel_id)
        channel_token_path.parent.mkdir(parents=True, exist_ok=True)
        channel_token_path.write_text(credentials.to_json(), encoding="utf-8")
        self._upsert_channel(channel, token_path=channel_token_path)
        self.settings.youtube_token_path.parent.mkdir(parents=True, exist_ok=True)
        self.settings.youtube_token_path.write_text(credentials.to_json(), encoding="utf-8")
        self.oauth_session_path.unlink(missing_ok=True)
        status = self.get_status()
        status["channel_id"] = channel_id
        status["channel_title"] = channel.get("title")
        if playlist_id:
            status["playlist_id"] = playlist_id
        return status

    def authenticate_local(self) -> dict[str, Any]:
        client_secrets = Path(self.settings.youtube_client_secrets_path)
        if not client_secrets.exists():
            raise FileNotFoundError("YouTube client secrets file is not configured.")

        flow = InstalledAppFlow.from_client_secrets_file(
            str(client_secrets),
            scopes=YOUTUBE_SCOPES,
        )
        credentials = flow.run_local_server(port=0, open_browser=True)
        channel = self._fetch_authenticated_channel(credentials)
        channel_token_path = self._channel_token_path(channel["id"])
        channel_token_path.parent.mkdir(parents=True, exist_ok=True)
        channel_token_path.write_text(credentials.to_json(), encoding="utf-8")
        self._upsert_channel(channel, token_path=channel_token_path)
        self.settings.youtube_token_path.write_text(credentials.to_json(), encoding="utf-8")
        return self.get_status()

    def select_channel(self, channel_id: str) -> dict[str, Any]:
        registry = self._read_channel_registry()
        channels = registry.get("channels", [])
        channel = self._find_channel(channels, channel_id)
        if not channel:
            raise ValueError("YouTube channel is not connected. Connect it first.")
        if not self._channel_token_path(channel_id).exists():
            raise ValueError("YouTube channel token is missing. Reconnect this channel.")
        registry["selected_channel_id"] = channel_id
        self._write_channel_registry(registry)
        return self.get_status()

    def list_channel_uploads(self, *, channel_id: str, max_results: int = 20) -> list[dict[str, Any]]:
        credentials = self._load_credentials(youtube_channel_id=channel_id)
        youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, credentials=credentials)
        channel_response = youtube.channels().list(part="snippet,contentDetails", mine=True).execute()
        channel_items = channel_response.get("items") or []
        if not channel_items:
            raise ValueError("No YouTube channel was returned for this token.")
        channel_item = channel_items[0]
        actual_channel_id = channel_item.get("id")
        if actual_channel_id and actual_channel_id != channel_id:
            raise ValueError(f"Selected token belongs to {actual_channel_id}, not {channel_id}.")

        related_playlists = ((channel_item.get("contentDetails") or {}).get("relatedPlaylists") or {})
        uploads_playlist_id = related_playlists.get("uploads")
        if not uploads_playlist_id:
            raise ValueError("YouTube uploads playlist was not returned for this channel.")

        wanted = max(1, min(int(max_results or 20), 50))
        playlist_items: list[dict[str, Any]] = []
        request = youtube.playlistItems().list(
            part="snippet,contentDetails",
            playlistId=uploads_playlist_id,
            maxResults=min(wanted, 50),
        )
        while request is not None and len(playlist_items) < wanted:
            response = request.execute()
            playlist_items.extend(response.get("items") or [])
            if len(playlist_items) >= wanted:
                break
            request = youtube.playlistItems().list_next(request, response)

        video_ids = [
            str((item.get("contentDetails") or {}).get("videoId") or "").strip()
            for item in playlist_items[:wanted]
        ]
        video_ids = [video_id for video_id in video_ids if video_id]
        if not video_ids:
            return []

        videos: list[dict[str, Any]] = []
        for index in range(0, len(video_ids), 50):
            response = youtube.videos().list(
                part="snippet,status,contentDetails,localizations",
                id=",".join(video_ids[index : index + 50]),
                maxResults=50,
            ).execute()
            videos.extend(response.get("items") or [])

        by_id = {item.get("id"): item for item in videos}
        uploads: list[dict[str, Any]] = []
        for video_id in video_ids:
            item = by_id.get(video_id)
            if not item:
                continue
            snippet = item.get("snippet") or {}
            status = item.get("status") or {}
            content_details = item.get("contentDetails") or {}
            thumbnails = snippet.get("thumbnails") or {}
            thumbnail = (
                thumbnails.get("maxres")
                or thumbnails.get("standard")
                or thumbnails.get("high")
                or thumbnails.get("medium")
                or thumbnails.get("default")
                or {}
            )
            uploads.append(
                {
                    "video_id": video_id,
                    "title": snippet.get("title") or video_id,
                    "description": snippet.get("description") or "",
                    "tags": list(snippet.get("tags") or []),
                    "published_at": snippet.get("publishedAt"),
                    "channel_id": snippet.get("channelId") or channel_id,
                    "channel_title": snippet.get("channelTitle"),
                    "default_language": snippet.get("defaultLanguage") or snippet.get("defaultAudioLanguage"),
                    "default_audio_language": snippet.get("defaultAudioLanguage"),
                    "privacy_status": status.get("privacyStatus"),
                    "duration": content_details.get("duration"),
                    "duration_seconds": self._parse_iso8601_duration_seconds(content_details.get("duration")),
                    "thumbnail_url": thumbnail.get("url"),
                    "localizations": item.get("localizations") or {},
                }
            )
        return uploads

    def find_or_create_playlist(
        self,
        *,
        youtube_channel_id: str,
        title: str,
        description: str = "",
        privacy_status: str = "public",
    ) -> dict[str, Any]:
        normalized_title = sanitize_youtube_copy(title).strip()
        if not normalized_title:
            raise ValueError("YouTube playlist title is required.")

        credentials = self._load_credentials(youtube_channel_id=youtube_channel_id)
        youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, credentials=credentials)

        request = youtube.playlists().list(part="snippet,status", mine=True, maxResults=50)
        while request is not None:
            response = request.execute()
            for item in response.get("items") or []:
                snippet = item.get("snippet") or {}
                if str(snippet.get("title") or "").strip().casefold() == normalized_title.casefold():
                    return {
                        "id": item.get("id"),
                        "title": snippet.get("title") or normalized_title,
                        "created": False,
                    }
            request = youtube.playlists().list_next(request, response)

        body = {
            "snippet": {
                "title": normalized_title[:150],
                "description": sanitize_youtube_copy(description).strip(),
            },
            "status": {"privacyStatus": privacy_status},
        }
        result = youtube.playlists().insert(part="snippet,status", body=body).execute()
        snippet = result.get("snippet") or {}
        return {
            "id": result.get("id"),
            "title": snippet.get("title") or normalized_title,
            "created": True,
        }

    def add_video_to_playlist(
        self,
        *,
        youtube_channel_id: str,
        playlist_id: str,
        video_id: str,
    ) -> dict[str, Any]:
        normalized_playlist_id = str(playlist_id or "").strip()
        normalized_video_id = str(video_id or "").strip()
        if not normalized_playlist_id or not normalized_video_id:
            raise ValueError("YouTube playlist id and video id are required.")

        credentials = self._load_credentials(youtube_channel_id=youtube_channel_id)
        youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, credentials=credentials)

        existing = youtube.playlistItems().list(
            part="id,contentDetails",
            playlistId=normalized_playlist_id,
            videoId=normalized_video_id,
            maxResults=1,
        ).execute()
        items = existing.get("items") or []
        if items:
            return {
                "id": items[0].get("id"),
                "playlist_id": normalized_playlist_id,
                "video_id": normalized_video_id,
                "created": False,
            }

        result = youtube.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": normalized_playlist_id,
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": normalized_video_id,
                    },
                },
            },
        ).execute()
        return {
            "id": result.get("id"),
            "playlist_id": normalized_playlist_id,
            "video_id": normalized_video_id,
            "created": True,
        }

    def ensure_video_in_playlists(
        self,
        *,
        youtube_channel_id: str,
        video_id: str,
        playlist_titles: list[str],
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        seen_titles: set[str] = set()
        for title in playlist_titles:
            normalized_title = sanitize_youtube_copy(title).strip()
            if not normalized_title:
                continue
            title_key = normalized_title.casefold()
            if title_key in seen_titles:
                continue
            seen_titles.add(title_key)
            playlist = self.find_or_create_playlist(
                youtube_channel_id=youtube_channel_id,
                title=normalized_title,
                description=f"Curated {normalized_title} releases.",
            )
            item = self.add_video_to_playlist(
                youtube_channel_id=youtube_channel_id,
                playlist_id=str(playlist.get("id") or ""),
                video_id=video_id,
            )
            results.append(
                {
                    "playlist_id": playlist.get("id"),
                    "playlist_title": playlist.get("title") or normalized_title,
                    "playlist_created": bool(playlist.get("created")),
                    "playlist_item_id": item.get("id"),
                    "playlist_item_created": bool(item.get("created")),
                }
            )
        return results

    def update_video_metadata(
        self,
        *,
        video_id: str,
        title: str,
        description: str,
        tags: list[str],
        youtube_channel_id: str | None = None,
        localizations: dict[str, dict[str, str]] | None = None,
        default_language: str = DEFAULT_YOUTUBE_LANGUAGE,
    ) -> dict[str, Any]:
        credentials = self._load_credentials(youtube_channel_id=youtube_channel_id)
        youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, credentials=credentials)
        response = youtube.videos().list(part="snippet,localizations", id=video_id).execute()
        items = response.get("items") or []
        if not items:
            raise ValueError(f"YouTube video not found: {video_id}")

        item = items[0]
        snippet = dict(item.get("snippet") or {})
        default_language = normalize_youtube_language(default_language or snippet.get("defaultLanguage"))
        normalized_localizations = normalize_youtube_localizations(
            localizations,
            default_title=title,
            default_description=description,
            default_language=default_language,
        )
        default_copy = normalized_localizations.get(default_language)
        if default_copy:
            title = default_copy["title"]
            description = default_copy["description"]

        body_snippet = {
            "title": sanitize_youtube_copy(title).strip()[:100],
            "description": sanitize_youtube_copy(description).strip(),
            "categoryId": str(snippet.get("categoryId") or self.settings.youtube_category_id),
            "tags": tags,
            "defaultLanguage": default_language,
        }
        if snippet.get("defaultAudioLanguage"):
            body_snippet["defaultAudioLanguage"] = snippet["defaultAudioLanguage"]

        api_localizations = localizations_for_youtube_api(
            normalized_localizations,
            default_language=default_language,
        )
        result = youtube.videos().update(
            part="snippet,localizations",
            body={
                "id": video_id,
                "snippet": body_snippet,
                "localizations": api_localizations,
            },
        ).execute()
        return {
            "id": result.get("id") or video_id,
            "snippet": body_snippet,
            "localizations": normalized_localizations,
        }

    def upload_playlist_video(
        self,
        playlist: Playlist,
        *,
        title: str,
        description: str,
        tags: list[str],
        thumbnail_path: str | None = None,
        youtube_channel_id: str | None = None,
        localizations: dict[str, dict[str, str]] | None = None,
        default_language: str = DEFAULT_YOUTUBE_LANGUAGE,
        scheduled_publish_at: datetime | None = None,
        privacy_status: str | None = None,
    ) -> YouTubeUploadResult:
        credentials = self._load_credentials(youtube_channel_id=youtube_channel_id)
        if not playlist.output_video_path:
            raise ValueError("Playlist output_video_path is missing.")

        youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, credentials=credentials)
        default_language = normalize_youtube_language(default_language)
        title = sanitize_youtube_copy(title)[:100]
        description = sanitize_youtube_copy(description)
        normalized_localizations = normalize_youtube_localizations(
            localizations,
            default_title=title,
            default_description=description,
            default_language=default_language,
        )
        default_copy = normalized_localizations.get(default_language)
        if default_copy:
            title = default_copy["title"]
            description = default_copy["description"]
        api_localizations = localizations_for_youtube_api(
            normalized_localizations,
            default_language=default_language,
        )
        status = {
            "privacyStatus": privacy_status or self.settings.youtube_privacy_status,
            "containsSyntheticMedia": self.settings.youtube_contains_synthetic_media,
            "selfDeclaredMadeForKids": False,
        }
        if scheduled_publish_at is not None:
            scheduled_publish_at = scheduled_publish_at.astimezone(timezone.utc).replace(microsecond=0)
            status["privacyStatus"] = "private"
            status["publishAt"] = scheduled_publish_at.isoformat().replace("+00:00", "Z")

        body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags,
                "categoryId": self.settings.youtube_category_id,
                "defaultLanguage": default_language,
            },
            "status": status,
        }
        default_audio_language = self._infer_default_audio_language(
            title=title,
            description=description,
            tags=tags,
        )
        if default_audio_language:
            body["snippet"]["defaultAudioLanguage"] = default_audio_language
        parts = ["snippet", "status"]
        if api_localizations:
            body["localizations"] = api_localizations
            parts.append("localizations")
        try:
            response = self._execute_video_insert(
                youtube,
                parts=parts,
                body=body,
                video_path=playlist.output_video_path,
            )
        except HttpError as exc:
            if default_audio_language and self._is_default_audio_language_rejected(exc):
                body["snippet"].pop("defaultAudioLanguage", None)
                default_audio_language = None
                response = self._execute_video_insert(
                    youtube,
                    parts=parts,
                    body=body,
                    video_path=playlist.output_video_path,
                )
            else:
                raise

        video_id = response["id"]
        channel = self.get_channel(youtube_channel_id)
        if channel:
            response["upload_channel"] = {
                "id": channel.get("id"),
                "title": channel.get("title"),
            }
        response["default_language"] = default_language
        if scheduled_publish_at is not None:
            response["scheduled_publish_at"] = scheduled_publish_at.isoformat()
        if default_audio_language:
            response["default_audio_language"] = default_audio_language
        if normalized_localizations:
            response["localizations"] = normalized_localizations
        if thumbnail_path and Path(thumbnail_path).exists():
            thumbnail_upload_path = self._prepare_thumbnail_upload(thumbnail_path)
            try:
                youtube.thumbnails().set(
                    videoId=video_id,
                    media_body=MediaFileUpload(str(thumbnail_upload_path)),
                ).execute()
            except Exception as exc:  # noqa: BLE001
                response["thumbnail_upload_error"] = str(exc)

        return YouTubeUploadResult(video_id=video_id, response=response)

    def replace_video_caption_track(
        self,
        *,
        video_id: str,
        language: str,
        caption_path: str | Path,
        youtube_channel_id: str | None = None,
        name: str = "Lyrics",
        is_draft: bool = False,
    ) -> dict[str, Any]:
        normalized_video_id = str(video_id or "").strip()
        raw_language = str(language or "").strip()
        raw_language_key = raw_language.lower().replace("_", "-")
        normalized_language = YOUTUBE_LANGUAGE_ALIASES.get(raw_language_key, raw_language)
        if not normalized_video_id:
            raise ValueError("YouTube video id is required.")
        if not normalized_language:
            raise ValueError("Caption language is required.")
        path = Path(caption_path)
        if not path.exists():
            raise FileNotFoundError(f"Caption file does not exist: {path}")

        credentials = self._load_credentials(youtube_channel_id=youtube_channel_id)
        youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, credentials=credentials)
        for caption in self._list_video_captions(youtube, normalized_video_id):
            snippet = caption.get("snippet") or {}
            if str(snippet.get("language") or "").strip().lower() != normalized_language.lower():
                continue
            if str(snippet.get("name") or "").strip() not in {"", name}:
                continue
            caption_id = str(caption.get("id") or "").strip()
            if caption_id:
                youtube.captions().delete(id=caption_id).execute()

        body = {
            "snippet": {
                "videoId": normalized_video_id,
                "language": normalized_language,
                "name": name[:150],
                "isDraft": bool(is_draft),
            }
        }
        result = youtube.captions().insert(
            part="snippet",
            body=body,
            media_body=MediaFileUpload(str(path), mimetype="application/x-subrip", resumable=True),
        ).execute()
        return {
            "id": result.get("id"),
            "language": normalized_language,
            "name": (result.get("snippet") or {}).get("name") or name,
            "is_draft": bool((result.get("snippet") or {}).get("isDraft", is_draft)),
        }

    def _list_video_captions(self, youtube: Any, video_id: str) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        request = youtube.captions().list(part="snippet", videoId=video_id)
        while request is not None:
            response = request.execute()
            items.extend(response.get("items") or [])
            request = youtube.captions().list_next(request, response)
        return items

    def _execute_video_insert(
        self,
        youtube: Any,
        *,
        parts: list[str],
        body: dict[str, Any],
        video_path: str,
    ) -> dict[str, Any]:
        request = youtube.videos().insert(
            part=",".join(parts),
            body=body,
            media_body=MediaFileUpload(video_path, resumable=True),
        )
        response = None
        while response is None:
            _, response = request.next_chunk()
        return response

    def _is_default_audio_language_rejected(self, exc: HttpError) -> bool:
        if getattr(exc.resp, "status", None) not in {400, 403}:
            return False
        error_text = str(exc).lower()
        return "defaultaudiolanguage" in error_text or "default audio language" in error_text

    def _infer_default_audio_language(
        self,
        *,
        title: str,
        description: str,
        tags: list[str],
    ) -> str | None:
        haystack = " ".join([title, description, " ".join(tags)]).lower()
        no_vocal_markers = (
            "instrumental",
            "bgm",
            "no-vocal",
            "no vocal",
            "no vocals",
            "without vocals",
            "background music",
            "가사 없는",
            "보컬 없는",
            "연주곡",
            "歌なし",
            "インスト",
        )
        if any(marker in haystack for marker in no_vocal_markers):
            return None
        language_markers = (
            (
                "ja",
                (
                    "j-pop",
                    "jpop",
                    "japanese pop",
                    "japanese vocal",
                    "japanese vocals",
                    "japanese lyrics",
                    "일본어 보컬",
                    "일본어 노래",
                    "日本語ボーカル",
                    "日本語歌詞",
                ),
            ),
            (
                "ko",
                (
                    "k-pop",
                    "kpop",
                    "korean pop",
                    "korean vocal",
                    "korean vocals",
                    "korean lyrics",
                    "한국어 보컬",
                    "한국어 노래",
                ),
            ),
            (
                "es",
                (
                    "spanish pop",
                    "spanish vocal",
                    "spanish vocals",
                    "spanish lyrics",
                    "español",
                    "voz española",
                    "letra española",
                ),
            ),
            ("en", ("english pop", "english vocal", "english vocals", "english lyrics")),
        )
        for language, markers in language_markers:
            if any(marker in haystack for marker in markers):
                return language
        return None

    def _parse_iso8601_duration_seconds(self, value: str | None) -> int:
        if not value:
            return 0
        match = YOUTUBE_DURATION_PATTERN.match(value)
        if not match:
            return 0
        return (
            int(match.group("hours") or 0) * 3600
            + int(match.group("minutes") or 0) * 60
            + int(match.group("seconds") or 0)
        )

    def _prepare_thumbnail_upload(self, thumbnail_path: str) -> Path:
        source = Path(thumbnail_path)
        if source.stat().st_size <= YOUTUBE_THUMBNAIL_MAX_BYTES:
            return source

        cache_dir = self.settings.browser_dir / "youtube-thumbnails"
        cache_dir.mkdir(parents=True, exist_ok=True)
        output = cache_dir / f"{source.stem}-youtube.jpg"

        with Image.open(source) as image:
            image = image.convert("RGB")
            for bounds in [(1280, 720), (1024, 576), (854, 480)]:
                candidate = image.copy()
                candidate.thumbnail(bounds, Image.Resampling.LANCZOS)
                for quality in range(90, 34, -5):
                    candidate.save(output, "JPEG", quality=quality, optimize=True, progressive=True)
                    if output.stat().st_size <= YOUTUBE_THUMBNAIL_MAX_BYTES:
                        return output

        raise ValueError("YouTube thumbnail must be 2MB or smaller after compression.")

    def get_channel(self, channel_id: str | None) -> dict[str, Any] | None:
        registry = self._read_channel_registry()
        channels = registry.get("channels", [])
        if channel_id:
            return self._find_channel(channels, channel_id)
        selected_channel_id = registry.get("selected_channel_id")
        if selected_channel_id:
            return self._find_channel(channels, selected_channel_id)
        return None

    def _load_credentials(self, youtube_channel_id: str | None = None) -> Credentials:
        token_path = self._token_path_for_channel(youtube_channel_id)
        if not token_path.exists():
            raise FileNotFoundError("Selected YouTube channel token is missing. Connect this channel first.")

        credentials = Credentials.from_authorized_user_file(
            str(token_path),
            scopes=YOUTUBE_SCOPES if youtube_channel_id else [YOUTUBE_UPLOAD_SCOPE],
        )
        if credentials.expired and credentials.refresh_token:
            try:
                credentials.refresh(GoogleAuthRequest())
            except RefreshError as exc:
                raise ValueError("Stored YouTube channel token expired or was revoked. Connect this channel again.") from exc
            token_path.write_text(credentials.to_json(), encoding="utf-8")
        if not credentials.valid:
            raise ValueError("Stored YouTube credentials are invalid. Reconnect YouTube.")
        return credentials

    def _inspect_token(self, token_path: Path | None = None) -> dict[str, Any]:
        token_path = token_path or self.settings.youtube_token_path
        if not token_path.exists():
            return {"authenticated": False}

        try:
            credentials = Credentials.from_authorized_user_file(
                str(token_path),
                scopes=[YOUTUBE_UPLOAD_SCOPE],
            )
        except Exception as exc:  # noqa: BLE001
            return {
                "authenticated": False,
                "error": f"Stored YouTube token could not be read: {exc}",
            }

        return {
            "authenticated": bool(credentials.valid or credentials.refresh_token),
        }

    def _fetch_authenticated_channel(self, credentials: Credentials) -> dict[str, Any]:
        youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, credentials=credentials)
        response = youtube.channels().list(part="snippet", mine=True).execute()
        items = response.get("items") or []
        if not items:
            raise ValueError("No YouTube channel was returned for this Google account.")
        item = items[0]
        snippet = item.get("snippet") or {}
        thumbnails = snippet.get("thumbnails") or {}
        thumbnail = thumbnails.get("default") or thumbnails.get("medium") or thumbnails.get("high") or {}
        return {
            "id": item["id"],
            "title": snippet.get("title") or item["id"],
            "thumbnail_url": thumbnail.get("url"),
        }

    def _read_channel_registry(self) -> dict[str, Any]:
        if not self.channel_registry_path.exists():
            return {"selected_channel_id": None, "channels": []}
        try:
            data = json.loads(self.channel_registry_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"selected_channel_id": None, "channels": []}
        return {
            "selected_channel_id": data.get("selected_channel_id"),
            "channels": list(data.get("channels") or []),
        }

    def _write_channel_registry(self, registry: dict[str, Any]) -> None:
        self.channel_registry_path.parent.mkdir(parents=True, exist_ok=True)
        self.channel_registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")

    def _upsert_channel(self, channel: dict[str, Any], *, token_path: Path) -> None:
        registry = self._read_channel_registry()
        channels = [item for item in registry.get("channels", []) if item.get("id") != channel["id"]]
        channels.append(
            {
                **channel,
                "token_path": str(token_path),
                "connected_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        channels.sort(key=lambda item: str(item.get("title") or "").lower())
        registry["channels"] = channels
        registry["selected_channel_id"] = channel["id"]
        self._write_channel_registry(registry)

    def _find_channel(self, channels: list[dict[str, Any]], channel_id: str | None) -> dict[str, Any] | None:
        if not channel_id:
            return None
        return next((channel for channel in channels if channel.get("id") == channel_id), None)

    def _channel_token_path(self, channel_id: str | None) -> Path:
        if not channel_id:
            return self.settings.youtube_token_path
        safe_channel_id = "".join(char for char in channel_id if char.isalnum() or char in {"-", "_"})
        if not safe_channel_id:
            raise ValueError("Invalid YouTube channel id.")
        return self.channel_tokens_dir / f"{safe_channel_id}.json"

    def _token_path_for_channel(self, channel_id: str | None) -> Path:
        if channel_id:
            return self._channel_token_path(channel_id)
        registry = self._read_channel_registry()
        selected_channel_id = registry.get("selected_channel_id")
        if selected_channel_id and self._channel_token_path(selected_channel_id).exists():
            return self._channel_token_path(selected_channel_id)
        return self.settings.youtube_token_path
