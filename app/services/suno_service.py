import hashlib
import hmac
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from app.config import Settings


@dataclass
class SunoGenerationRequest:
    prompt: str
    title: str | None = None
    metadata: dict[str, Any] | None = None
    custom_mode: bool = False
    instrumental: bool = False
    model: str | None = None
    style: str | None = None
    callback_url: str | None = None
    persona_id: str | None = None
    persona_model: str | None = None
    negative_tags: str | None = None
    vocal_gender: str | None = None
    style_weight: float | None = None
    weirdness_constraint: float | None = None
    audio_weight: float | None = None


@dataclass
class SunoGenerationResult:
    ok: bool
    provider_job_id: str | None
    raw: dict[str, Any]


@dataclass
class SunoWebhookTrack:
    source_track_id: str | None
    title: str
    prompt: str
    duration_seconds: int
    audio_path: str | None
    preview_url: str | None
    metadata: dict[str, Any]


@dataclass
class SunoWebhookPayload:
    ok: bool
    provider_job_id: str | None
    callback_type: str | None
    error_message: str | None
    tracks: list[SunoWebhookTrack]
    raw: dict[str, Any]


class StubSunoGateway:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def submit_generation_batch(self, requests: list[SunoGenerationRequest]) -> list[SunoGenerationResult]:
        results: list[SunoGenerationResult] = []
        for index, request in enumerate(requests, start=1):
            if self.settings.suno_provider_mode == "http":
                results.append(self._submit_http_request(request))
                continue

            provider_job_id = f"manual-{index}"
            results.append(
                SunoGenerationResult(
                    ok=True,
                    provider_job_id=provider_job_id,
                    raw={
                        "mode": self.settings.suno_provider_mode,
                        "provider_job_id": provider_job_id,
                        "title": request.title,
                    },
                )
            )
        return results

    def get_generation_details(self, task_id: str) -> dict[str, Any]:
        return self._request_json(
            "GET",
            "/api/v1/generate/record-info",
            params={"taskId": task_id},
        )

    def get_remaining_credits(self) -> dict[str, Any]:
        return self._request_json("GET", "/api/v1/generate/credit")

    def download_audio_to_storage(self, source_url: str, *, source_track_id: str | None = None) -> str:
        parsed = urlparse(source_url)
        suffix = Path(parsed.path).suffix or ".mp3"
        basename = source_track_id or hashlib.sha1(source_url.encode("utf-8")).hexdigest()[:16]
        destination = self.settings.tracks_dir / f"{basename}{suffix}"

        with httpx.Client(timeout=120.0, follow_redirects=True) as client:
            with client.stream("GET", source_url) as response:
                response.raise_for_status()
                with destination.open("wb") as output:
                    for chunk in response.iter_bytes():
                        output.write(chunk)

        return str(destination)

    def verify_webhook_signature(self, raw_body: bytes, signature: str | None) -> bool:
        if not self.settings.suno_webhook_secret:
            return True
        if not signature:
            return False

        expected = hmac.new(
            self.settings.suno_webhook_secret.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    def normalize_webhook_payload(self, payload: dict[str, Any]) -> SunoWebhookPayload:
        if isinstance(payload.get("data"), dict) and "task_id" in payload.get("data", {}):
            return self._normalize_sunoapi_callback(payload)
        return self._normalize_legacy_payload(payload)

    def _normalize_legacy_payload(self, payload: dict[str, Any]) -> SunoWebhookPayload:
        metadata = payload.get("metadata") or {}
        metadata.setdefault("lyrics", payload.get("lyrics") or payload.get("lyric") or "")
        duration_seconds = payload.get("duration_seconds") or metadata.get("duration_seconds") or 0
        track = SunoWebhookTrack(
            source_track_id=payload.get("source_track_id"),
            title=payload.get("title") or "Untitled",
            prompt=payload.get("prompt") or "",
            duration_seconds=int(duration_seconds),
            audio_path=payload.get("audio_path"),
            preview_url=payload.get("preview_url"),
            metadata=metadata,
        )
        return SunoWebhookPayload(
            ok=True,
            provider_job_id=payload.get("provider_job_id"),
            callback_type="complete",
            error_message=None,
            tracks=[track],
            raw=payload,
        )

    def _normalize_sunoapi_callback(self, payload: dict[str, Any]) -> SunoWebhookPayload:
        callback = payload.get("data") or {}
        callback_type = callback.get("callbackType")
        task_id = callback.get("task_id")
        code = payload.get("code")
        message = payload.get("msg")

        if code != 200 or callback_type == "error":
            return SunoWebhookPayload(
                ok=False,
                provider_job_id=task_id,
                callback_type=callback_type,
                error_message=message or "Suno callback reported failure",
                tracks=[],
                raw=payload,
            )

        if callback_type != "complete":
            return SunoWebhookPayload(
                ok=True,
                provider_job_id=task_id,
                callback_type=callback_type,
                error_message=None,
                tracks=[],
                raw=payload,
            )

        tracks: list[SunoWebhookTrack] = []
        for item in callback.get("data") or []:
            duration_value = item.get("duration") or 0
            metadata = {
                "provider": "sunoapi",
                "provider_task_id": task_id,
                "callback_type": callback_type,
                "source_audio_url": item.get("source_audio_url"),
                "image_url": item.get("image_url"),
                "source_image_url": item.get("source_image_url"),
                "model_name": item.get("model_name"),
                "tags": item.get("tags"),
                "lyrics": item.get("lyrics") or item.get("lyric") or "",
                "create_time": item.get("createTime"),
            }
            audio_url = item.get("audio_url") or item.get("source_audio_url")
            local_audio_path = None
            if audio_url:
                try:
                    local_audio_path = self.download_audio_to_storage(
                        audio_url,
                        source_track_id=item.get("id"),
                    )
                except Exception:
                    local_audio_path = audio_url

            tracks.append(
                SunoWebhookTrack(
                    source_track_id=item.get("id"),
                    title=item.get("title") or f"Suno Track {len(tracks) + 1}",
                    prompt=item.get("prompt") or "",
                    duration_seconds=int(round(float(duration_value))),
                    audio_path=local_audio_path,
                    preview_url=item.get("stream_audio_url") or item.get("source_stream_audio_url"),
                    metadata=metadata,
                )
            )

        return SunoWebhookPayload(
            ok=True,
            provider_job_id=task_id,
            callback_type=callback_type,
            error_message=None,
            tracks=tracks,
            raw=payload,
        )

    def _submit_http_request(self, request: SunoGenerationRequest) -> SunoGenerationResult:
        if not self.settings.suno_api_base_url or not self.settings.suno_api_key:
            return SunoGenerationResult(
                ok=False,
                provider_job_id=None,
                raw={"error": "suno_api_configuration_missing"},
            )

        callback_url = request.callback_url or self._default_callback_url()
        if not callback_url:
            return SunoGenerationResult(
                ok=False,
                provider_job_id=None,
                raw={"error": "suno_callback_url_missing"},
            )

        payload: dict[str, Any] = {
            "prompt": request.prompt,
            "customMode": request.custom_mode,
            "instrumental": request.instrumental,
            "model": request.model or self.settings.suno_default_model,
            "callBackUrl": callback_url,
        }
        optional_fields = {
            "title": request.title,
            "style": request.style,
            "personaId": request.persona_id,
            "personaModel": request.persona_model,
            "negativeTags": request.negative_tags,
            "vocalGender": request.vocal_gender,
            "styleWeight": request.style_weight,
            "weirdnessConstraint": request.weirdness_constraint,
            "audioWeight": request.audio_weight,
        }
        for key, value in optional_fields.items():
            if value is not None:
                payload[key] = value

        data = self._request_json(
            "POST",
            "/api/v1/generate",
            json=payload,
        )
        provider_job_id = ((data.get("data") or {}) if isinstance(data.get("data"), dict) else {}).get("taskId")
        return SunoGenerationResult(
            ok=data.get("code") == 200 and bool(provider_job_id),
            provider_job_id=provider_job_id,
            raw=data,
        )

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self.settings.suno_api_base_url or not self.settings.suno_api_key:
            return {"code": 500, "msg": "suno_api_configuration_missing"}

        with httpx.Client(timeout=20.0) as client:
            response = client.request(
                method,
                f"{self.settings.suno_api_base_url.rstrip('/')}{path}",
                headers={
                    "Authorization": f"Bearer {self.settings.suno_api_key}",
                    "Content-Type": "application/json",
                },
                params=params,
                json=json,
            )
            try:
                data = response.json()
            except ValueError:
                data = {
                    "code": response.status_code,
                    "msg": response.text,
                }
            if "code" not in data:
                data["code"] = response.status_code
            return data

    def _default_callback_url(self) -> str:
        base_url = self.settings.public_base_url.rstrip("/")
        if not base_url:
            return ""
        return f"{base_url}{self.settings.api_prefix}/suno/webhook"
