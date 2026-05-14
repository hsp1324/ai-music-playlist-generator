from typing import Any

from pydantic import BaseModel, Field


class RenderWorkerClaimRequest(BaseModel):
    worker_id: str = "render-worker"
    capabilities: list[str] = Field(default_factory=list)


class RenderWorkerHeartbeatRequest(BaseModel):
    lease_token: str
    worker_id: str = "render-worker"
    progress: dict[str, Any] = Field(default_factory=dict)
    message: str | None = None


class RenderWorkerFailRequest(BaseModel):
    lease_token: str
    worker_id: str = "render-worker"
    error_text: str


class RenderWorkerResponse(BaseModel):
    ok: bool
    message: str | None = None
    job_id: str | None = None
    playlist_id: str | None = None
    workflow_state: str | None = None
    output_video_path: str | None = None
