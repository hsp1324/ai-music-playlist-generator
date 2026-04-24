from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from app.config import Settings


@dataclass
class DreaminaVideoResult:
    job_id: str
    provider_response: dict[str, Any]
    video_url: str


class DreaminaService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def get_status(self) -> dict[str, Any]:
        configured = (
            self.settings.dreamina_provider_mode == "useapi"
            and bool(self.settings.dreamina_api_token)
            and bool(self.settings.dreamina_account)
        )
        return {
            "provider_mode": self.settings.dreamina_provider_mode,
            "configured": configured,
            "ready": configured,
            "account": self.settings.dreamina_account or None,
        }

    def generate_loop_clip(
        self,
        *,
        prompt: str,
    ) -> DreaminaVideoResult:
        if self.settings.dreamina_provider_mode != "useapi":
            raise ValueError("Dreamina provider is disabled.")
        if not self.settings.dreamina_api_token:
            raise ValueError("Dreamina API token is missing.")
        if not self.settings.dreamina_account:
            raise ValueError("Dreamina account is missing.")

        headers = {
            "Authorization": f"Bearer {self.settings.dreamina_api_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "account": self.settings.dreamina_account,
            "prompt": prompt,
            "model": self.settings.dreamina_video_model,
            "ratio": self.settings.dreamina_video_ratio,
            "duration": self.settings.dreamina_video_duration_seconds,
        }
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{self.settings.dreamina_api_base_url}/videos",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

            job_id = data.get("jobid")
            if not job_id:
                raise ValueError(f"Dreamina job ID missing in response: {data}")

            deadline = time.monotonic() + self.settings.dreamina_timeout_seconds
            while time.monotonic() < deadline:
                poll_response = client.get(
                    f"{self.settings.dreamina_api_base_url}/videos/{job_id}",
                    headers={"Authorization": f"Bearer {self.settings.dreamina_api_token}"},
                )
                poll_response.raise_for_status()
                job_payload = poll_response.json()
                status = str(job_payload.get("status") or "").lower()
                if status == "completed":
                    video_url = (
                        (job_payload.get("response") or {}).get("videoUrl")
                        or (job_payload.get("response") or {}).get("url")
                    )
                    if not video_url:
                        raise ValueError(f"Dreamina completed without video URL: {job_payload}")
                    return DreaminaVideoResult(
                        job_id=job_id,
                        provider_response=job_payload,
                        video_url=video_url,
                    )
                if status == "failed":
                    raise ValueError(job_payload.get("error") or f"Dreamina generation failed: {job_payload}")
                time.sleep(self.settings.dreamina_poll_interval_seconds)

        raise TimeoutError("Dreamina video generation timed out.")

    def download_video(self, video_url: str, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with httpx.stream("GET", video_url, follow_redirects=True, timeout=120.0) as response:
            response.raise_for_status()
            with output_path.open("wb") as handle:
                for chunk in response.iter_bytes():
                    handle.write(chunk)
        return output_path
