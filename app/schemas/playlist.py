from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import PlaylistStatus


class PlaylistBuildRequest(BaseModel):
    title: str
    target_duration_seconds: int = Field(default=3600, ge=60)
    execute_render: bool = False


class PlaylistWorkspaceCreateRequest(BaseModel):
    title: str
    target_duration_seconds: int = Field(default=3600, ge=0)
    workspace_mode: str = "playlist"
    auto_publish_when_ready: bool | None = None
    description: str | None = None
    cover_prompt: str | None = None
    dreamina_prompt: str | None = None


class PlaylistPublishApproveRequest(BaseModel):
    actor: str = "web-ui"
    youtube_video_id: str | None = None
    youtube_channel_id: str | None = None
    note: str | None = None
    force_under_target: bool = False


class PlaylistCoverGenerateRequest(BaseModel):
    actor: str = "web-ui"
    regenerate: bool = False


class PlaylistCoverApproveRequest(BaseModel):
    actor: str = "web-ui"
    approved: bool = True
    note: str | None = None


class PlaylistVideoRenderRequest(BaseModel):
    actor: str = "web-ui"


class PlaylistMetadataGenerateRequest(BaseModel):
    actor: str = "web-ui"


class PlaylistMetadataApproveRequest(BaseModel):
    actor: str = "web-ui"
    title: str | None = None
    description: str | None = None
    tags: list[str] | str | None = None
    note: str | None = None


class PlaylistRenderRequest(BaseModel):
    actor: str = "web-ui"


class PlaylistArchiveRequest(BaseModel):
    actor: str = "web-ui"
    archived: bool = True
    revive_rejected: bool = True


class PlaylistTrackReorderRequest(BaseModel):
    track_ids: list[str] = Field(min_length=1)
    actor: str = "web-ui"


class PlaylistUploadMarkRequest(BaseModel):
    youtube_video_id: str | None = None
    output_video_path: str | None = None
    actor: str = "manual-upload"
    note: str | None = None


class PlaylistItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    track_id: str
    order_index: int
    included_duration_seconds: int


class PlaylistTrackRead(BaseModel):
    id: str
    title: str
    duration_seconds: int
    audio_path: str | None
    preview_url: str | None
    image_url: str | None = None
    tags: str | None = None


class PlaylistJobRead(BaseModel):
    id: str
    type: str
    status: str
    source: str
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error_text: str | None = None
    output_audio_path: str | None = None
    output_video_path: str | None = None
    progress: dict[str, Any] | None = None


class PlaylistWorkspaceRead(BaseModel):
    id: str
    title: str
    hidden: bool = False
    status: PlaylistStatus
    workspace_mode: str
    auto_publish_when_ready: bool
    target_duration_seconds: int
    actual_duration_seconds: int
    progress_ratio: float
    description: str | None
    cover_prompt: str | None
    dreamina_prompt: str | None
    workflow_state: str
    publish_ready: bool
    publish_approved: bool
    cover_approved: bool = False
    metadata_approved: bool = False
    output_audio_path: str | None
    output_video_path: str | None
    cover_image_path: str | None
    youtube_title: str | None = None
    youtube_description: str | None = None
    youtube_tags: list[str] = []
    metadata_provider: str | None = None
    metadata_generation_error: str | None = None
    youtube_video_id: str | None
    note: str | None = None
    render_job: PlaylistJobRead | None = None
    created_at: datetime
    updated_at: datetime
    tracks: list[PlaylistTrackRead]


class PlaylistRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    status: PlaylistStatus
    target_duration_seconds: int
    actual_duration_seconds: int
    output_audio_path: str | None
    output_video_path: str | None
    youtube_video_id: str | None
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    items: list[PlaylistItemRead] = []
