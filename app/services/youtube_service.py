from dataclasses import dataclass
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from app.config import Settings
from app.models.playlist import Playlist


YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"


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
        token_status = self._inspect_token()
        ready = configured and token_status["authenticated"]
        return {
            "configured": configured,
            "authenticated": token_status["authenticated"],
            "ready": ready,
            "client_secrets_path": self.settings.youtube_client_secrets_path or None,
            "token_path": str(self.settings.youtube_token_path),
            "error": token_status.get("error"),
        }

    def authenticate_local(self) -> dict[str, Any]:
        client_secrets = Path(self.settings.youtube_client_secrets_path)
        if not client_secrets.exists():
            raise FileNotFoundError("YouTube client secrets file is not configured.")

        flow = InstalledAppFlow.from_client_secrets_file(
            str(client_secrets),
            scopes=[YOUTUBE_UPLOAD_SCOPE],
        )
        credentials = flow.run_local_server(port=0, open_browser=True)
        self.settings.youtube_token_path.write_text(credentials.to_json(), encoding="utf-8")
        return self.get_status()

    def upload_playlist_video(
        self,
        playlist: Playlist,
        *,
        title: str,
        description: str,
        tags: list[str],
        thumbnail_path: str | None = None,
    ) -> YouTubeUploadResult:
        credentials = self._load_credentials()
        if not playlist.output_video_path:
            raise ValueError("Playlist output_video_path is missing.")

        youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, credentials=credentials)
        body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags,
                "categoryId": self.settings.youtube_category_id,
            },
            "status": {
                "privacyStatus": self.settings.youtube_privacy_status,
            },
        }
        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=MediaFileUpload(playlist.output_video_path, resumable=True),
        )
        response = None
        while response is None:
            _, response = request.next_chunk()

        video_id = response["id"]
        if thumbnail_path and Path(thumbnail_path).exists():
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path),
            ).execute()

        return YouTubeUploadResult(video_id=video_id, response=response)

    def _load_credentials(self) -> Credentials:
        token_path = self.settings.youtube_token_path
        if not token_path.exists():
            raise FileNotFoundError("YouTube OAuth token is missing. Connect YouTube first.")

        credentials = Credentials.from_authorized_user_file(
            str(token_path),
            scopes=[YOUTUBE_UPLOAD_SCOPE],
        )
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(GoogleAuthRequest())
            token_path.write_text(credentials.to_json(), encoding="utf-8")
        if not credentials.valid:
            raise ValueError("Stored YouTube credentials are invalid. Reconnect YouTube.")
        return credentials

    def _inspect_token(self) -> dict[str, Any]:
        token_path = self.settings.youtube_token_path
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
