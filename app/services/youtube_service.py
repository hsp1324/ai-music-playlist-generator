import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow, InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image

from app.config import Settings
from app.models.playlist import Playlist
from app.utils.youtube_localizations import (
    DEFAULT_YOUTUBE_LANGUAGE,
    localizations_for_youtube_api,
    normalize_youtube_language,
    normalize_youtube_localizations,
)


YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
YOUTUBE_READONLY_SCOPE = "https://www.googleapis.com/auth/youtube.readonly"
YOUTUBE_SCOPES = [YOUTUBE_UPLOAD_SCOPE, YOUTUBE_READONLY_SCOPE]
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"
YOUTUBE_THUMBNAIL_MAX_BYTES = 2 * 1024 * 1024


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
        channels = registry.get("channels", [])
        selected_channel_id = registry.get("selected_channel_id")
        selected_channel = self._find_channel(channels, selected_channel_id)
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
            "client_secrets_path": self.settings.youtube_client_secrets_path or None,
            "token_path": str(self._token_path_for_channel(selected_channel_id)),
            "redirect_uri": self.redirect_uri,
            "error": selected_token_status.get("error") or legacy_token_status.get("error"),
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
    ) -> YouTubeUploadResult:
        credentials = self._load_credentials(youtube_channel_id=youtube_channel_id)
        if not playlist.output_video_path:
            raise ValueError("Playlist output_video_path is missing.")

        youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, credentials=credentials)
        default_language = normalize_youtube_language(default_language)
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
        body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags,
                "categoryId": self.settings.youtube_category_id,
                "defaultLanguage": default_language,
            },
            "status": {
                "privacyStatus": self.settings.youtube_privacy_status,
            },
        }
        parts = ["snippet", "status"]
        if api_localizations:
            body["localizations"] = api_localizations
            parts.append("localizations")
        request = youtube.videos().insert(
            part=",".join(parts),
            body=body,
            media_body=MediaFileUpload(playlist.output_video_path, resumable=True),
        )
        response = None
        while response is None:
            _, response = request.next_chunk()

        video_id = response["id"]
        channel = self.get_channel(youtube_channel_id)
        if channel:
            response["upload_channel"] = {
                "id": channel.get("id"),
                "title": channel.get("title"),
            }
        response["default_language"] = default_language
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
            credentials.refresh(GoogleAuthRequest())
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
