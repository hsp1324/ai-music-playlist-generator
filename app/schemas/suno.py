from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SunoGenerationCreateRequest(BaseModel):
    title: str | None = None
    prompt: str
    custom_mode: bool = False
    instrumental: bool = False
    model: str | None = None
    style: str | None = None
    exclude_style: str | None = None
    callback_url: str | None = None
    persona_id: str | None = None
    persona_model: str | None = None
    negative_tags: str | None = None
    vocal_gender: str | None = None
    style_weight: float | None = Field(default=None, ge=0, le=1, multiple_of=0.01)
    weirdness_constraint: float | None = Field(default=None, ge=0, le=1, multiple_of=0.01)
    audio_weight: float | None = Field(default=None, ge=0, le=1, multiple_of=0.01)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("vocal_gender", mode="before")
    @classmethod
    def normalize_vocal_gender(cls, value: Any) -> str | None:
        clean = str(value or "").strip().lower()
        if not clean:
            return None
        aliases = {"m": "m", "male": "m", "man": "m", "f": "f", "female": "f", "woman": "f"}
        if clean not in aliases:
            raise ValueError("vocal_gender must be male/female or m/f")
        return aliases[clean]


class SunoWebhookTrackPayload(BaseModel):
    id: str | None = None
    audio_url: str | None = None
    source_audio_url: str | None = None
    stream_audio_url: str | None = None
    source_stream_audio_url: str | None = None
    image_url: str | None = None
    source_image_url: str | None = None
    prompt: str | None = None
    model_name: str | None = None
    title: str | None = None
    tags: str | None = None
    create_time: str | int | None = Field(default=None, alias="createTime")
    duration: float | None = None

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class SunoWebhookCallbackData(BaseModel):
    callback_type: str | None = Field(default=None, alias="callbackType")
    task_id: str | None = Field(default=None, alias="task_id")
    data: list[SunoWebhookTrackPayload] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class SunoWebhookRequest(BaseModel):
    code: int | None = None
    msg: str | None = None
    data: SunoWebhookCallbackData | None = None

    provider_job_id: str | None = None
    source_track_id: str | None = None
    title: str | None = None
    prompt: str | None = None
    duration_seconds: int = 0
    audio_path: str | None = None
    preview_url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(populate_by_name=True, extra="allow")
