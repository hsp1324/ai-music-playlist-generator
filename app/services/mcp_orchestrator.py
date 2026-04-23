from dataclasses import dataclass
from typing import Protocol

import httpx

from app.config import Settings
from app.models.enums import DecisionValue
from app.models.track import Track


@dataclass
class ReviewDecision:
    decision: DecisionValue
    confidence: float | None
    rationale: str
    actor: str


class DecisionEngine(Protocol):
    def review_track(self, track: Track) -> ReviewDecision:
        ...


class MCPReadyDecisionEngine:
    """
    Stub decision engine with the same interface a future MCP-backed agent will use.

    Today it runs simple rules from track metadata.
    Later it can be replaced with:
    - an MCP client
    - a Slack-native agent action layer
    - a retrieval/policy-enhanced approval engine
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def review_track(self, track: Track) -> ReviewDecision:
        if self.settings.mcp_review_url:
            remote_decision = self._review_via_http(track)
            if remote_decision is not None:
                return remote_decision
            if not self.settings.mcp_fallback_to_rules:
                return ReviewDecision(
                    decision=DecisionValue.hold,
                    confidence=None,
                    rationale="Remote MCP review failed and fallback-to-rules is disabled.",
                    actor=self.settings.mcp_agent_name,
                )

        return self._review_via_rules(track)

    def _review_via_http(self, track: Track) -> ReviewDecision | None:
        payload = {
            "track": {
                "id": track.id,
                "title": track.title,
                "prompt": track.prompt,
                "duration_seconds": track.duration_seconds,
                "audio_path": track.audio_path,
                "preview_url": track.preview_url,
                "metadata": track.metadata_json,
            },
            "policy": self.settings.mcp_review_policy,
            "mode": self.settings.auto_approval_mode,
        }
        headers = {"Content-Type": "application/json"}
        if self.settings.mcp_api_key:
            headers["Authorization"] = f"Bearer {self.settings.mcp_api_key}"

        try:
            with httpx.Client(timeout=self.settings.mcp_timeout_seconds) as client:
                response = client.post(self.settings.mcp_review_url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
        except Exception:  # noqa: BLE001
            return None

        decision_text = data.get("decision")
        if decision_text not in {item.value for item in DecisionValue}:
            return None

        confidence = data.get("confidence")
        return ReviewDecision(
            decision=DecisionValue(decision_text),
            confidence=float(confidence) if confidence is not None else None,
            rationale=data.get("rationale") or "Remote MCP review returned no rationale.",
            actor=data.get("actor") or self.settings.mcp_agent_name,
        )

    def _review_via_rules(self, track: Track) -> ReviewDecision:
        score = track.metadata_json.get("model_score")
        if score is None:
            return ReviewDecision(
                decision=DecisionValue.hold,
                confidence=None,
                rationale=(
                    "No model_score provided. Human review is still required until the "
                    "MCP policy engine is connected."
                ),
                actor=self.settings.mcp_agent_name,
            )

        if score >= 0.85:
            return ReviewDecision(
                decision=DecisionValue.approve,
                confidence=float(score),
                rationale="Rule-based proxy approved the candidate because model_score >= 0.85.",
                actor=self.settings.mcp_agent_name,
            )

        if score <= 0.35:
            return ReviewDecision(
                decision=DecisionValue.reject,
                confidence=float(score),
                rationale="Rule-based proxy rejected the candidate because model_score <= 0.35.",
                actor=self.settings.mcp_agent_name,
            )

        return ReviewDecision(
            decision=DecisionValue.hold,
            confidence=float(score),
            rationale="Rule-based proxy marked the candidate as uncertain and held it for review.",
            actor=self.settings.mcp_agent_name,
        )
