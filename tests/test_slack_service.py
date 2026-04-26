from app.config import Settings
from app.models.enums import TrackStatus
from app.models.slack_installation import SlackInstallation
from app.models.track import Track
from app.services.slack_installation_store import SlackInstallationStore
from app.services.slack_service import SlackService


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
    assert link_texts == ["Listen", "Cover"]


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
    assert "Track Approved" in rendered
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
