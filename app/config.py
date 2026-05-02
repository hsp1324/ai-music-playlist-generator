from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="AIMP_",
        extra="ignore",
    )

    app_name: str = "ai-music-playlist-generator"
    environment: str = "development"
    debug: bool = False
    api_prefix: str = "/api"

    database_url: str = "sqlite:///./storage/app.db"
    storage_root: Path = Path("storage")

    ffmpeg_binary: str = "ffmpeg"
    ffmpeg_stall_timeout_seconds: int = 900
    playlist_target_minutes: int = 60
    crossfade_seconds: float = 2.0

    slack_signing_secret: str = ""
    slack_bot_token: str = ""
    slack_app_token: str = ""
    slack_client_id: str = ""
    slack_client_secret: str = ""
    slack_redirect_uri: str = ""
    slack_scopes: str = (
        "app_mentions:read,channels:history,channels:read,chat:write,commands,files:write,"
        "im:history,im:read,im:write,users:read"
    )
    slack_user_scopes: str = ""
    slack_review_channel_id: str = ""
    slack_enable_signature_verification: bool = False
    slack_single_message_audio_reviews: bool = False
    public_base_url: str = "http://127.0.0.1:8000"
    cache_remote_audio_on_intake: bool = True

    auto_approval_mode: Literal["human", "hybrid", "agent"] = "human"
    mcp_agent_name: str = "approval-agent"
    mcp_review_policy: str = (
        "Approve only high-confidence tracks that fit the playlist identity, "
        "reject weak candidates, and hold uncertain cases."
    )

    mcp_review_url: str = ""
    mcp_api_key: str = ""
    mcp_timeout_seconds: float = 15.0
    mcp_fallback_to_rules: bool = True

    suno_api_base_url: str = "https://api.sunoapi.org"
    suno_api_key: str = ""
    suno_default_model: str = "V5_5"
    suno_provider_mode: Literal["stub", "http", "manual_webhook", "browser_profile"] = "manual_webhook"
    suno_webhook_secret: str = ""
    suno_browser_login_url: str = "https://suno.com/create"
    suno_browser_name: Literal["chromium", "firefox", "webkit"] = "chromium"
    suno_browser_executable_path: str = ""
    suno_session_stale_hours: int = 72

    auto_build_playlists: bool = True
    auto_build_render_audio: bool = True
    auto_build_title_prefix: str = "Auto Playlist"

    youtube_client_secrets_path: str = ""
    youtube_oauth_redirect_uri: str = ""
    youtube_privacy_status: Literal["private", "unlisted", "public"] = "private"
    youtube_category_id: str = "10"
    youtube_contains_synthetic_media: bool = False
    youtube_auto_upload_on_publish: bool = True
    youtube_title_suffix: str = "Official AI Visualizer"
    youtube_default_hashtags: str = "#aimusic #visualizer #electronicmusic"

    codex_metadata_enabled: bool = False
    codex_metadata_command: str = "codex"
    codex_metadata_model: str = ""
    codex_metadata_timeout_seconds: int = 180

    dreamina_provider_mode: Literal["disabled", "useapi"] = "disabled"
    dreamina_api_base_url: str = "https://api.useapi.net/v1/dreamina"
    dreamina_api_token: str = ""
    dreamina_account: str = ""
    dreamina_video_model: str = "seedance-1.5-pro"
    dreamina_video_duration_seconds: int = 8
    dreamina_video_ratio: str = "16:9"
    dreamina_poll_interval_seconds: float = 10.0
    dreamina_timeout_seconds: float = 240.0

    worker_autostart: bool = True
    worker_poll_interval_seconds: float = 2.0

    @property
    def tracks_dir(self) -> Path:
        return self.storage_root / "tracks"

    @property
    def playlists_dir(self) -> Path:
        return self.storage_root / "playlists"

    @property
    def covers_dir(self) -> Path:
        return self.storage_root / "covers"

    @property
    def temp_dir(self) -> Path:
        return self.storage_root / "tmp"

    @property
    def browser_dir(self) -> Path:
        return self.storage_root / "browser"

    @property
    def suno_browser_profile_dir(self) -> Path:
        return self.browser_dir / "suno-profile"

    @property
    def suno_browser_state_path(self) -> Path:
        return self.browser_dir / "suno-session.json"

    @property
    def suno_browser_pid_path(self) -> Path:
        return self.browser_dir / "suno-login.pid"

    @property
    def suno_browser_log_path(self) -> Path:
        return self.browser_dir / "suno-login.log"

    @property
    def youtube_token_path(self) -> Path:
        return self.browser_dir / "youtube-token.json"

    def ensure_storage_dirs(self) -> None:
        self.storage_root.mkdir(parents=True, exist_ok=True)
        self.tracks_dir.mkdir(parents=True, exist_ok=True)
        self.playlists_dir.mkdir(parents=True, exist_ok=True)
        self.covers_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.browser_dir.mkdir(parents=True, exist_ok=True)
        self.suno_browser_profile_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
