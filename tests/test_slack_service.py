import asyncio

from app.config import Settings
from app.models.enums import TrackStatus
from app.models.slack_installation import SlackInstallation
from app.models.track import Track
from app.services.slack_installation_store import SlackInstallationStore
from app.services.slack_service import SlackFileUploadResult, SlackPostResult, SlackService


def test_build_install_url_includes_required_fields() -> None:
    settings = Settings(
        slack_client_id="123456",
        slack_redirect_uri="https://example.com/api/slack/oauth/callback",
        slack_scopes="chat:write,commands",
        slack_user_scopes="users:read",
    )
    service = SlackService(settings)

    url = service.build_install_url(state="abc123")

    assert "client_id=123456" in url
    assert "scope=chat%3Awrite%2Ccommands" in url
    assert "redirect_uri=https%3A%2F%2Fexample.com%2Fapi%2Fslack%2Foauth%2Fcallback" in url
    assert "user_scope=users%3Aread" in url
    assert "state=abc123" in url


def test_installation_from_oauth_payload() -> None:
    payload = {
        "ok": True,
        "access_token": "xoxb-test",
        "app_id": "A123",
        "bot_user_id": "U123",
        "scope": "chat:write,commands",
        "team": {"id": "T123", "name": "Example Team"},
        "enterprise": {"id": "E123"},
        "authed_user": {"id": "U999"},
    }

    installation = SlackService.installation_from_oauth(payload)

    assert installation is not None
    assert installation.team_id == "T123"
    assert installation.team_name == "Example Team"
    assert installation.bot_token == "xoxb-test"
    assert installation.installed_by_user_id == "U999"


def test_installation_store_upsert_updates_existing_record() -> None:
    from app.db import SessionLocal, init_db

    store = SlackInstallationStore()
    init_db()
    db = SessionLocal()
    try:
        first = SlackInstallation(
            team_id="T123",
            team_name="Team One",
            bot_token="xoxb-one",
            installed_by_user_id="U111",
        )
        saved = store.upsert_installation(db, first)
        db.commit()
        db.refresh(saved)

        second = SlackInstallation(
            team_id="T123",
            team_name="Team Two",
            bot_token="xoxb-two",
            installed_by_user_id="U222",
        )
        updated = store.upsert_installation(db, second)
        db.commit()
        db.refresh(updated)

        assert updated.id == saved.id
        assert updated.team_name == "Team Two"
        assert updated.bot_token == "xoxb-two"
        assert updated.installed_by_user_id == "U222"
    finally:
        db.close()


def test_build_track_review_blocks_include_media_links() -> None:
    service = SlackService(Settings())
    track = Track(
        id="track-1",
        title="Night Drive",
        prompt="synthwave highway",
        duration_seconds=120,
        audio_path="storage/tracks/track-1.mp3",
        preview_url="https://example.com/preview",
        status=TrackStatus.pending_review,
        metadata_json={"image_url": "https://example.com/cover.jpg"},
    )

    blocks = service.build_track_review_blocks(track)
    actions_blocks = [block for block in blocks if block["type"] == "actions"]

    assert len(actions_blocks) == 2
    link_texts = [element["text"]["text"] for element in actions_blocks[0]["elements"]]
    assert link_texts == ["Listen"]


def test_build_track_review_blocks_do_not_add_cover_button() -> None:
    service = SlackService(Settings(public_base_url="https://music.example.com"))
    track = Track(
        id="track-1",
        title="Local Cover",
        prompt="",
        duration_seconds=120,
        audio_path="storage/tracks/local-cover.mp3",
        preview_url=None,
        status=TrackStatus.pending_review,
        metadata_json={"image_url": "storage/covers/가녀린 날개-cover.jpg"},
    )

    blocks = service.build_track_review_blocks(track)
    button_texts = [
        element["text"]["text"]
        for block in blocks
        if block["type"] == "actions"
        for element in block["elements"]
    ]

    assert "Cover" not in button_texts


def test_build_track_decision_blocks_remove_review_buttons() -> None:
    service = SlackService(Settings())
    track = Track(
        id="track-1",
        title="Night Drive",
        prompt="synthwave highway",
        duration_seconds=120,
        audio_path="https://example.com/night-drive.mp3",
        preview_url=None,
        status=TrackStatus.approved,
        metadata_json={"pending_workspace_title": "summer"},
    )

    blocks = service.build_track_decision_blocks(
        track,
        decision="approve",
        actor="slack-reviewer",
        workspace_title="summer",
        note="Assigned to workspace `summer`.",
    )

    rendered = str(blocks)
    assert "Approved" in rendered
    assert "slack-reviewer" in rendered
    button_texts = [
        element["text"]["text"]
        for block in blocks
        if block["type"] == "actions"
        for element in block["elements"]
    ]
    assert "Approve" not in button_texts
    assert "Hold" not in button_texts
    assert "Reject" not in button_texts
    assert "Revert to Queue" in button_texts
    assert "Cover" not in button_texts


def test_complete_upload_payload_can_attach_review_blocks_to_file_message() -> None:
    blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": "Review this track"}}]

    payload = SlackService._build_complete_upload_payload(
        file_id="F123",
        title="Uploaded Track",
        channel="C123",
        blocks=blocks,
    )

    assert payload["files"] == [{"id": "F123", "title": "Uploaded Track"}]
    assert payload["channel_id"] == "C123"
    assert payload["blocks"] == blocks
    assert "initial_comment" not in payload


def test_complete_upload_payload_keeps_initial_comment_as_fallback() -> None:
    blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": "Review this track"}}]

    payload = SlackService._build_complete_upload_payload(
        file_id="F123",
        title="Uploaded Track",
        channel="C123",
        initial_comment="Audio preview: Uploaded Track",
        blocks=blocks,
    )

    assert payload["initial_comment"] == "Audio preview: Uploaded Track"
    assert "blocks" not in payload


def test_post_review_message_with_local_audio_uses_single_file_message(tmp_path) -> None:
    audio_path = tmp_path / "single-message.mp3"
    audio_path.write_bytes(b"fake-audio")
    service = SlackService(
        Settings(
            slack_bot_token="xoxb-test",
            slack_review_channel_id="C123",
            slack_single_message_audio_reviews=True,
        )
    )
    track = Track(
        id="track-1",
        title="Single Message",
        prompt="",
        duration_seconds=120,
        audio_path=str(audio_path),
        status=TrackStatus.pending_review,
        metadata_json={"pending_workspace_title": "butter-fly"},
    )
    upload_call = {}

    async def fake_upload_local_audio_file(**kwargs):
        upload_call.update(kwargs)
        return SlackFileUploadResult(
            ok=True,
            file_id="F123",
            channel="C123",
            ts="1777000000.000300",
            raw={"ok": True},
        )

    async def fake_post_review_message(*args, **kwargs):
        raise AssertionError("separate review message should not be posted")

    service.upload_local_audio_file = fake_upload_local_audio_file
    service.post_review_message = fake_post_review_message

    result = asyncio.run(service.post_review_message_with_local_audio(track))

    assert result.ok is True
    assert result.channel == "C123"
    assert result.ts == "1777000000.000300"
    assert upload_call["channel"] == "C123"
    assert upload_call["blocks"]
    assert "initial_comment" not in upload_call
    rendered = str(upload_call["blocks"])
    assert "Approve" in rendered
    assert "Hold" in rendered
    assert "Reject" in rendered


def test_post_review_message_with_remote_audio_uploads_file_preview() -> None:
    service = SlackService(Settings(slack_bot_token="xoxb-test", slack_review_channel_id="C123"))
    track = Track(
        id="track-1",
        title="Remote Suno Track",
        prompt="",
        duration_seconds=120,
        audio_path="https://cdn1.suno.ai/remote-track.mp3",
        status=TrackStatus.pending_review,
        metadata_json={"pending_workspace_title": "sleep tide"},
    )
    upload_call = {}

    async def fake_upload_remote_audio_file(**kwargs):
        upload_call.update(kwargs)
        return SlackFileUploadResult(
            ok=True,
            file_id="F123",
            channel="C123",
            ts="1777000000.000300",
            raw={"ok": True},
        )

    async def fake_find_uploaded_file_message(**kwargs):
        return "C123", "1777000000.000300"

    async def fake_post_review_message(track, **kwargs):
        return SlackPostResult(
            ok=True,
            channel="C123",
            ts="1777000000.000400",
            raw={"ok": True},
        )

    service.upload_remote_audio_file = fake_upload_remote_audio_file
    service.find_uploaded_file_message = fake_find_uploaded_file_message
    service.post_review_message = fake_post_review_message

    result = asyncio.run(service.post_review_message_with_audio_upload(track))

    assert result.ok is True
    assert result.channel == "C123"
    assert result.ts == "1777000000.000400"
    assert upload_call["audio_url"] == "https://cdn1.suno.ai/remote-track.mp3"
    assert upload_call["initial_comment"] == "Audio preview: Remote Suno Track"


def test_post_review_message_with_local_audio_defaults_to_separate_review_message(tmp_path) -> None:
    audio_path = tmp_path / "two-message.mp3"
    audio_path.write_bytes(b"fake-audio")
    service = SlackService(Settings(slack_bot_token="xoxb-test", slack_review_channel_id="C123"))
    track = Track(
        id="track-1",
        title="Two Message",
        prompt="",
        duration_seconds=120,
        audio_path=str(audio_path),
        status=TrackStatus.pending_review,
        metadata_json={"pending_workspace_title": "butter-fly"},
    )
    upload_call = {}

    async def fake_upload_local_audio_file(**kwargs):
        upload_call.update(kwargs)
        return SlackFileUploadResult(
            ok=True,
            file_id="F123",
            channel="C123",
            ts="1777000000.000300",
            raw={"ok": True},
        )

    async def fake_find_uploaded_file_message(**kwargs):
        return "C123", "1777000000.000300"

    async def fake_post_review_message(track, **kwargs):
        return SlackPostResult(
            ok=True,
            channel="C123",
            ts="1777000000.000400",
            raw={"ok": True},
        )

    service.upload_local_audio_file = fake_upload_local_audio_file
    service.find_uploaded_file_message = fake_find_uploaded_file_message
    service.post_review_message = fake_post_review_message

    result = asyncio.run(service.post_review_message_with_local_audio(track))

    assert result.ok is True
    assert result.channel == "C123"
    assert result.ts == "1777000000.000400"
    assert upload_call["initial_comment"] == "Audio preview: Two Message"
    assert "blocks" not in upload_call


def test_remote_audio_filename_uses_url_name_or_safe_title() -> None:
    assert (
        SlackService._remote_audio_filename("https://cdn1.suno.ai/f007d9a3-9727-4ea4.mp3?download=1", "Sleep Tide")
        == "f007d9a3-9727-4ea4.mp3"
    )
    assert SlackService._remote_audio_filename("https://cdn1.suno.ai/audio", "Sleep Tide 18 A") == "Sleep-Tide-18-A.mp3"


def test_extract_file_share_location_from_complete_upload_payload() -> None:
    payload = {
        "files": [
            {
                "shares": {
                    "public": {
                        "C123": [
                            {
                                "ts": "1777000000.000100",
                            }
                        ]
                    }
                }
            }
        ]
    }

    channel, ts = SlackService._extract_file_share_location(payload, fallback_channel="C999")

    assert channel == "C123"
    assert ts == "1777000000.000100"


def test_extract_file_message_from_history_matches_uploaded_file() -> None:
    payload = {
        "ok": True,
        "messages": [
            {
                "ts": "1777000000.000200",
                "text": "Track review",
                "files": [{"id": "F123"}],
            }
        ],
    }

    channel, ts = SlackService._extract_file_message_from_history(
        payload,
        file_id="F123",
        channel="C123",
    )

    assert channel == "C123"
    assert ts == "1777000000.000200"
