import asyncio
import hashlib
import hmac
import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlencode
from typing import Any

import httpx

from app.config import Settings
from app.models.slack_installation import SlackInstallation
from app.models.track import Track


@dataclass
class SlackPostResult:
    ok: bool
    channel: str | None = None
    ts: str | None = None
    raw: dict[str, Any] | None = None


@dataclass
class SlackOAuthResult:
    ok: bool
    raw: dict[str, Any]


@dataclass
class SlackFileUploadResult:
    ok: bool
    file_id: str | None = None
    channel: str | None = None
    ts: str | None = None
    raw: dict[str, Any] | None = None


@dataclass
class SlackUpdateResult:
    ok: bool
    raw: dict[str, Any] | None = None


class SlackService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def build_install_url(self, state: str | None = None) -> str:
        if not self.settings.slack_client_id:
            raise ValueError("slack_client_id is not configured.")

        params = {
            "client_id": self.settings.slack_client_id,
            "scope": self.settings.slack_scopes,
        }
        if self.settings.slack_user_scopes:
            params["user_scope"] = self.settings.slack_user_scopes
        if self.settings.slack_redirect_uri:
            params["redirect_uri"] = self.settings.slack_redirect_uri
        if state:
            params["state"] = state
        return f"https://slack.com/oauth/v2/authorize?{urlencode(params)}"

    def verify_signature(self, headers: Mapping[str, str], raw_body: bytes) -> bool:
        if not self.settings.slack_enable_signature_verification:
            return True

        timestamp = headers.get("x-slack-request-timestamp", "")
        signature = headers.get("x-slack-signature", "")
        if not timestamp or not signature or not self.settings.slack_signing_secret:
            return False

        if abs(time.time() - int(timestamp)) > 60 * 5:
            return False

        sig_basestring = f"v0:{timestamp}:{raw_body.decode('utf-8')}"
        digest = hmac.new(
            self.settings.slack_signing_secret.encode("utf-8"),
            sig_basestring.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        expected = f"v0={digest}"
        return hmac.compare_digest(expected, signature)

    def build_track_review_blocks(self, track: Track) -> list[dict[str, Any]]:
        value_prefix = f"track:{track.id}"
        metadata = track.metadata_json or {}
        workspace_title = metadata.get("pending_workspace_title") or metadata.get("pending_workspace_id") or "Unassigned"
        link_buttons: list[dict[str, Any]] = []
        if track.preview_url:
            link_buttons.append(self._link_button("Listen", track.preview_url))
        if track.audio_path and track.audio_path.startswith(("http://", "https://")):
            link_buttons.append(self._link_button("Audio", track.audio_path))
        image_url = metadata.get("image_url")
        if image_url:
            link_buttons.append(self._link_button("Cover", image_url))

        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "Track Review"},
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*{track.title}*\n"
                        f"Workspace: `{workspace_title}`"
                    ),
                },
            },
        ]
        if link_buttons:
            blocks.append(
                {
                    "type": "actions",
                    "elements": link_buttons,
                }
            )
        blocks.append(
            {
                "type": "actions",
                "elements": [
                    self._button("Approve", f"{value_prefix}:approve", style="primary"),
                    self._button("Hold", f"{value_prefix}:hold"),
                    self._button("Reject", f"{value_prefix}:reject", style="danger"),
                ],
            },
        )
        return blocks

    def build_track_decision_blocks(
        self,
        track: Track,
        *,
        decision: str,
        actor: str,
        workspace_title: str | None = None,
        note: str | None = None,
    ) -> list[dict[str, Any]]:
        metadata = track.metadata_json or {}
        resolved_workspace = (
            workspace_title
            or metadata.get("pending_workspace_title")
            or metadata.get("pending_workspace_id")
            or "Unassigned"
        )
        status_label = {
            "approve": "Approved",
            "hold": "On Hold",
            "reject": "Rejected",
            "regenerate": "On Hold",
        }.get(decision, decision.title())
        link_buttons: list[dict[str, Any]] = []
        if track.preview_url:
            link_buttons.append(self._link_button("Listen", track.preview_url))
        if track.audio_path and track.audio_path.startswith(("http://", "https://")):
            link_buttons.append(self._link_button("Audio", track.audio_path))
        image_url = metadata.get("image_url")
        if image_url:
            link_buttons.append(self._link_button("Cover", image_url))

        blocks: list[dict[str, Any]] = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": status_label},
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*{track.title}*\n"
                        f"Workspace: `{resolved_workspace}`"
                    ),
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Decision by `{self._short_text(actor, 80)}`",
                    }
                ],
            },
        ]
        if note:
            blocks.append(
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": self._short_text(note, 180),
                        }
                    ],
                }
            )
        if link_buttons:
            blocks.append({"type": "actions", "elements": link_buttons})
        return blocks

    def build_app_home_blocks(self, stats: dict[str, int]) -> list[dict[str, Any]]:
        return [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "AI Music Ops Dashboard"},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Pending Review*\n{stats.get('pending_review', 0)}"},
                    {"type": "mrkdwn", "text": f"*Approved*\n{stats.get('approved', 0)}"},
                    {"type": "mrkdwn", "text": f"*Rejected*\n{stats.get('rejected', 0)}"},
                    {"type": "mrkdwn", "text": f"*Held*\n{stats.get('held', 0)}"},
                ],
            },
            {
                "type": "actions",
                "elements": [
                    self._button("Build Approved Playlist", "system:build_playlist", style="primary"),
                    self._button("Refresh Dashboard", "system:refresh_dashboard"),
                ],
            },
        ]

    async def exchange_code_for_installation(self, code: str) -> SlackOAuthResult:
        if not self.settings.slack_client_id or not self.settings.slack_client_secret:
            return SlackOAuthResult(ok=False, raw={"error": "slack_client_credentials_missing"})

        payload = {
            "client_id": self.settings.slack_client_id,
            "client_secret": self.settings.slack_client_secret,
            "code": code,
        }
        if self.settings.slack_redirect_uri:
            payload["redirect_uri"] = self.settings.slack_redirect_uri

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post("https://slack.com/api/oauth.v2.access", data=payload)
            data = response.json()
            return SlackOAuthResult(ok=bool(data.get("ok")), raw=data)

    async def post_review_message(
        self,
        track: Track,
        *,
        token: str | None = None,
        channel: str | None = None,
    ) -> SlackPostResult:
        channel = channel or self.settings.slack_review_channel_id
        auth_token = token or self.settings.slack_bot_token
        if not auth_token or not channel:
            return SlackPostResult(ok=False, raw={"reason": "slack_bot_token or slack_review_channel_id missing"})

        payload = {
            "channel": channel,
            "text": f"Track review requested for {track.title}",
            "blocks": self.build_track_review_blocks(track),
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://slack.com/api/chat.postMessage",
                headers={
                    "Authorization": f"Bearer {auth_token}",
                    "Content-Type": "application/json; charset=utf-8",
                },
                json=payload,
            )
            data = response.json()
            return SlackPostResult(
                ok=bool(data.get("ok")),
                channel=data.get("channel"),
                ts=data.get("ts"),
                raw=data,
            )

    async def update_review_message(
        self,
        track: Track,
        *,
        decision: str,
        actor: str,
        token: str | None = None,
        channel: str | None = None,
        ts: str | None = None,
        workspace_title: str | None = None,
        note: str | None = None,
    ) -> SlackUpdateResult:
        auth_token = token or self.settings.slack_bot_token
        target_channel = channel or track.slack_channel_id
        target_ts = ts or track.slack_message_ts
        if not auth_token or not target_channel or not target_ts:
            return SlackUpdateResult(
                ok=False,
                raw={"error": "missing_bot_token_channel_or_ts"},
            )

        status_label = {
            "approve": "approved",
            "hold": "put on hold",
            "reject": "rejected",
            "regenerate": "put on hold",
        }.get(decision, decision)
        payload = {
            "channel": target_channel,
            "ts": target_ts,
            "text": f"Track {status_label}: {track.title}",
            "blocks": self.build_track_decision_blocks(
                track,
                decision=decision,
                actor=actor,
                workspace_title=workspace_title,
                note=note,
            ),
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://slack.com/api/chat.update",
                headers={
                    "Authorization": f"Bearer {auth_token}",
                    "Content-Type": "application/json; charset=utf-8",
                },
                json=payload,
            )
            data = response.json()
        return SlackUpdateResult(ok=bool(data.get("ok")), raw=data)

    async def post_review_message_with_local_audio(
        self,
        track: Track,
        *,
        token: str | None = None,
        channel: str | None = None,
    ) -> SlackPostResult:
        auth_token = token or self.settings.slack_bot_token
        target_channel = channel or self.settings.slack_review_channel_id
        if not auth_token or not target_channel:
            return SlackPostResult(ok=False, raw={"reason": "slack_bot_token or slack_review_channel_id missing"})
        if not track.audio_path:
            return SlackPostResult(ok=False, raw={"reason": "track_audio_path_missing"})

        upload_result = await self.upload_local_audio_file(
            file_path=track.audio_path,
            title=track.title,
            token=auth_token,
            channel=target_channel,
            initial_comment=f"Audio preview: {track.title}",
        )
        if not upload_result.ok:
            return SlackPostResult(ok=False, raw={"upload": upload_result.raw})

        message_channel = upload_result.channel or target_channel
        if upload_result.file_id:
            message_channel, _ = await self.find_uploaded_file_message(
                file_id=upload_result.file_id,
                token=auth_token,
                channel=message_channel,
                text_marker=f"Audio preview: {track.title}",
            )

        post_result = await self.post_review_message(
            track,
            token=auth_token,
            channel=message_channel or target_channel,
        )
        if not post_result.ok:
            if upload_result.file_id:
                await self.delete_file(file_id=upload_result.file_id, token=auth_token)
            return SlackPostResult(
                ok=False,
                channel=message_channel or target_channel,
                raw={"error": "review_message_post_failed", "upload": upload_result.raw, "post": post_result.raw},
            )

        return SlackPostResult(
            ok=True,
            channel=post_result.channel,
            ts=post_result.ts,
            raw={"upload": upload_result.raw, "post": post_result.raw},
        )

    async def update_review_request_message(
        self,
        track: Track,
        *,
        token: str | None = None,
        channel: str | None = None,
        ts: str | None = None,
    ) -> SlackUpdateResult:
        auth_token = token or self.settings.slack_bot_token
        target_channel = channel or track.slack_channel_id
        target_ts = ts or track.slack_message_ts
        if not auth_token or not target_channel or not target_ts:
            return SlackUpdateResult(
                ok=False,
                raw={"error": "missing_bot_token_channel_or_ts"},
            )

        payload = {
            "channel": target_channel,
            "ts": target_ts,
            "text": f"Track review requested: {track.title}",
            "blocks": self.build_track_review_blocks(track),
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://slack.com/api/chat.update",
                headers={
                    "Authorization": f"Bearer {auth_token}",
                    "Content-Type": "application/json; charset=utf-8",
                },
                json=payload,
            )
            data = response.json()
            return SlackUpdateResult(ok=bool(data.get("ok")), raw=data)

    async def upload_local_audio_file(
        self,
        *,
        file_path: str,
        title: str,
        token: str,
        channel: str,
        thread_ts: str | None = None,
        initial_comment: str | None = None,
    ) -> SlackFileUploadResult:
        path = Path(file_path)
        if not path.exists():
            return SlackFileUploadResult(ok=False, raw={"error": "file_not_found", "path": file_path})

        file_size = path.stat().st_size
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            upload_ticket_response = await client.post(
                "https://slack.com/api/files.getUploadURLExternal",
                headers={
                    "Authorization": f"Bearer {token}",
                },
                data={
                    "filename": path.name,
                    "length": str(file_size),
                },
            )
            upload_ticket = upload_ticket_response.json()
            if not upload_ticket.get("ok"):
                return SlackFileUploadResult(ok=False, raw=upload_ticket)

            upload_url = upload_ticket["upload_url"]
            file_id = upload_ticket["file_id"]
            file_bytes = path.read_bytes()
            binary_upload_response = await client.post(
                upload_url,
                headers={"Content-Type": "application/octet-stream"},
                content=file_bytes,
            )
            if binary_upload_response.status_code != 200:
                return SlackFileUploadResult(
                    ok=False,
                    file_id=file_id,
                    raw={
                        "error": "binary_upload_failed",
                        "status_code": binary_upload_response.status_code,
                        "body": binary_upload_response.text,
                    },
                )

            completion_payload: dict[str, Any] = {
                "files": [{"id": file_id, "title": title}],
                "channel_id": channel,
            }
            if thread_ts:
                completion_payload["thread_ts"] = thread_ts
            if initial_comment:
                completion_payload["initial_comment"] = initial_comment

            completion_response = await client.post(
                "https://slack.com/api/files.completeUploadExternal",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json; charset=utf-8",
                },
                json=completion_payload,
            )
            completion_data = completion_response.json()
            shared_channel, shared_ts = self._extract_file_share_location(completion_data, fallback_channel=channel)
            return SlackFileUploadResult(
                ok=bool(completion_data.get("ok")),
                file_id=file_id,
                channel=shared_channel,
                ts=shared_ts,
                raw=completion_data,
            )

    async def find_uploaded_file_message(
        self,
        *,
        file_id: str,
        token: str,
        channel: str,
        text_marker: str | None = None,
        attempts: int = 5,
        delay_seconds: float = 1.0,
    ) -> tuple[str | None, str | None]:
        for attempt in range(attempts):
            if attempt:
                await asyncio.sleep(delay_seconds)
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    "https://slack.com/api/conversations.history",
                    headers={"Authorization": f"Bearer {token}"},
                    data={
                        "channel": channel,
                        "limit": "25",
                    },
                )
                data = response.json()
            found_channel, found_ts = self._extract_file_message_from_history(
                data,
                file_id=file_id,
                channel=channel,
                text_marker=text_marker,
            )
            if found_ts:
                return found_channel, found_ts
            if not data.get("ok") and data.get("error") in {"missing_scope", "not_in_channel", "channel_not_found"}:
                return channel, None
        return channel, None

    async def delete_file(
        self,
        *,
        file_id: str,
        token: str | None = None,
    ) -> dict[str, Any]:
        auth_token = token or self.settings.slack_bot_token
        if not auth_token:
            return {"ok": False, "error": "missing_bot_token"}

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://slack.com/api/files.delete",
                headers={"Authorization": f"Bearer {auth_token}"},
                data={"file": file_id},
            )
            return response.json()

    async def publish_app_home(
        self,
        *,
        user_id: str,
        stats: dict[str, int],
        token: str | None = None,
    ) -> dict[str, Any]:
        auth_token = token or self.settings.slack_bot_token
        if not auth_token:
            return {"ok": False, "error": "missing_bot_token"}

        payload = {
            "user_id": user_id,
            "view": {
                "type": "home",
                "blocks": self.build_app_home_blocks(stats),
            },
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://slack.com/api/views.publish",
                headers={
                    "Authorization": f"Bearer {auth_token}",
                    "Content-Type": "application/json; charset=utf-8",
                },
                json=payload,
            )
            return response.json()

    async def post_ops_message(
        self,
        *,
        text: str,
        token: str | None = None,
        channel: str | None = None,
    ) -> SlackPostResult:
        auth_token = token or self.settings.slack_bot_token
        target_channel = channel or self.settings.slack_review_channel_id
        if not auth_token or not target_channel:
            return SlackPostResult(ok=False, raw={"error": "missing_bot_token_or_channel"})

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://slack.com/api/chat.postMessage",
                headers={
                    "Authorization": f"Bearer {auth_token}",
                    "Content-Type": "application/json; charset=utf-8",
                },
                json={
                    "channel": target_channel,
                    "text": text,
                },
            )
            data = response.json()
            return SlackPostResult(
                ok=bool(data.get("ok")),
                channel=data.get("channel"),
                ts=data.get("ts"),
                raw=data,
            )

    @staticmethod
    def installation_from_oauth(payload: dict[str, Any]) -> SlackInstallation | None:
        access_token = payload.get("access_token")
        team = payload.get("team") or {}
        authed_user = payload.get("authed_user") or {}
        if not access_token or not team.get("id"):
            return None

        return SlackInstallation(
            team_id=team["id"],
            team_name=team.get("name"),
            enterprise_id=(payload.get("enterprise") or {}).get("id"),
            app_id=payload.get("app_id"),
            bot_user_id=payload.get("bot_user_id"),
            bot_token=access_token,
            scope=payload.get("scope"),
            installed_by_user_id=authed_user.get("id"),
            is_active=True,
        )

    @staticmethod
    def parse_track_action(action_value: str) -> tuple[str, str] | None:
        parts = action_value.split(":")
        if len(parts) != 3 or parts[0] != "track":
            return None
        return parts[1], parts[2]

    @staticmethod
    def parse_system_action(action_value: str) -> str | None:
        parts = action_value.split(":")
        if len(parts) != 2 or parts[0] != "system":
            return None
        return parts[1]

    @staticmethod
    def _button(text: str, value: str, style: str | None = None) -> dict[str, Any]:
        button = {
            "type": "button",
            "text": {"type": "plain_text", "text": text, "emoji": True},
            "value": value,
            "action_id": value,
        }
        if style:
            button["style"] = style
        return button

    @staticmethod
    def _link_button(text: str, url: str) -> dict[str, Any]:
        return {
            "type": "button",
            "text": {"type": "plain_text", "text": text, "emoji": True},
            "url": url,
            "action_id": f"link:{text.lower()}",
        }

    @staticmethod
    def _format_duration(seconds: int | None) -> str:
        if not seconds:
            return "0:00"
        minutes, remaining = divmod(round(seconds), 60)
        return f"{minutes}:{remaining:02d}"

    @staticmethod
    def _short_text(value: str, max_length: int) -> str:
        normalized = " ".join(str(value).split())
        if len(normalized) <= max_length:
            return normalized
        return f"{normalized[: max_length - 1].rstrip()}..."

    @staticmethod
    def _extract_file_share_location(
        payload: dict[str, Any],
        *,
        fallback_channel: str | None,
    ) -> tuple[str | None, str | None]:
        files = payload.get("files")
        if not isinstance(files, list):
            return fallback_channel, None

        for file_info in files:
            shares = file_info.get("shares") if isinstance(file_info, dict) else None
            if not isinstance(shares, dict):
                continue
            for share_group in ("public", "private"):
                channels = shares.get(share_group)
                if not isinstance(channels, dict):
                    continue
                for channel_id, entries in channels.items():
                    if not isinstance(entries, list) or not entries:
                        continue
                    ts = entries[0].get("ts") if isinstance(entries[0], dict) else None
                    if ts:
                        return channel_id, ts

        return fallback_channel, None

    @staticmethod
    def _extract_file_message_from_history(
        payload: dict[str, Any],
        *,
        file_id: str,
        channel: str | None,
        text_marker: str | None = None,
    ) -> tuple[str | None, str | None]:
        messages = payload.get("messages")
        if not isinstance(messages, list):
            return channel, None

        for message in messages:
            if not isinstance(message, dict):
                continue
            files = message.get("files")
            has_file = (
                isinstance(files, list)
                and any(isinstance(file_info, dict) and file_info.get("id") == file_id for file_info in files)
            )
            has_marker = bool(text_marker and text_marker in str(message.get("text") or ""))
            if has_file or has_marker:
                return channel, message.get("ts")

        return channel, None
