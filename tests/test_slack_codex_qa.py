import os

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.main import create_app
from app.models.enums import JobStatus, JobType
from app.models.job import Job


def create_isolated_client(tmp_path) -> TestClient:
    os.environ["AIMP_STORAGE_ROOT"] = str(tmp_path / "storage")
    os.environ["AIMP_DATABASE_URL"] = f"sqlite:///{tmp_path / 'app.db'}"
    os.environ["AIMP_WORKER_AUTOSTART"] = "false"
    os.environ["AIMP_SLACK_OPS_CHANNEL_ID"] = "COPS"
    os.environ["AIMP_SLACK_BOT_TOKEN"] = "xoxb-test"
    os.environ.pop("AIMP_SLACK_CODEX_QA_CHANNEL_ID", None)
    os.environ.pop("AIMP_SLACK_CODEX_QA_ENABLED", None)
    os.environ.pop("AIMP_SLACK_ENABLE_SIGNATURE_VERIFICATION", None)
    get_settings.cache_clear()
    return TestClient(create_app())


def clear_isolated_env() -> None:
    for key in (
        "AIMP_STORAGE_ROOT",
        "AIMP_DATABASE_URL",
        "AIMP_WORKER_AUTOSTART",
        "AIMP_SLACK_OPS_CHANNEL_ID",
        "AIMP_SLACK_BOT_TOKEN",
        "AIMP_SLACK_CODEX_QA_CHANNEL_ID",
        "AIMP_SLACK_CODEX_QA_ENABLED",
        "AIMP_SLACK_ENABLE_SIGNATURE_VERIFICATION",
    ):
        os.environ.pop(key, None)
    get_settings.cache_clear()


def test_slack_human_ops_message_queues_codex_qa_job(tmp_path) -> None:
    client = create_isolated_client(tmp_path)
    try:
        response = client.post(
            "/api/slack/events",
            json={
                "type": "event_callback",
                "team_id": "T1",
                "event": {
                    "type": "message",
                    "channel": "COPS",
                    "user": "U1",
                    "ts": "1710000000.000100",
                    "text": "지금 큐 상태 알려줘",
                },
            },
        )
        assert response.status_code == 200
        assert response.json()["slack_codex_qa"]["queued"] is True

        with SessionLocal() as db:
            job = db.scalar(select(Job).where(Job.type == JobType.slack_codex_qa))
            assert job is not None
            assert job.status == JobStatus.queued
            assert job.payload_json["channel_id"] == "COPS"
            assert job.payload_json["thread_ts"] == "1710000000.000100"
            assert job.payload_json["text"] == "지금 큐 상태 알려줘"
    finally:
        clear_isolated_env()


def test_slack_bot_ops_message_does_not_queue_codex_qa_job(tmp_path) -> None:
    client = create_isolated_client(tmp_path)
    try:
        response = client.post(
            "/api/slack/events",
            json={
                "type": "event_callback",
                "team_id": "T1",
                "event": {
                    "type": "message",
                    "channel": "COPS",
                    "bot_id": "B1",
                    "subtype": "bot_message",
                    "ts": "1710000000.000200",
                    "text": "Render worker completed",
                },
            },
        )
        assert response.status_code == 200
        assert response.json() == {"ok": True}

        with SessionLocal() as db:
            assert db.scalar(select(Job).where(Job.type == JobType.slack_codex_qa)) is None
    finally:
        clear_isolated_env()


def test_slack_codex_qa_job_posts_answer_in_thread(tmp_path, monkeypatch) -> None:
    client = create_isolated_client(tmp_path)
    posted = {}

    async def fake_post_plain_message(**kwargs):
        posted.update(kwargs)

        class Result:
            ok = True
            channel = kwargs["channel"]
            ts = "1710000000.000300"
            raw = {"ok": True}

        return Result()

    def fake_run_answer(settings, *, user_text, user_id=None):
        assert user_text == "용량 괜찮아?"
        assert user_id == "U1"
        return "현재 디스크 사용률은 정상입니다."

    monkeypatch.setattr(client.app.state.services.slack, "post_plain_message", fake_post_plain_message)
    monkeypatch.setattr("app.services.slack_codex_qa.run_slack_codex_answer", fake_run_answer)

    try:
        with SessionLocal() as db:
            job = Job(
                type=JobType.slack_codex_qa,
                status=JobStatus.queued,
                source="slack:codex_qa",
                payload_json={
                    "team_id": "T1",
                    "channel_id": "COPS",
                    "thread_ts": "1710000000.000250",
                    "message_ts": "1710000000.000250",
                    "user_id": "U1",
                    "text": "용량 괜찮아?",
                },
                result_json={},
            )
            db.add(job)
            db.commit()

        assert client.app.state.services.worker.process_pending_once(job_types=(JobType.slack_codex_qa,)) is True
        assert posted["text"] == "현재 디스크 사용률은 정상입니다."
        assert posted["channel"] == "COPS"
        assert posted["thread_ts"] == "1710000000.000250"

        with SessionLocal() as db:
            finished = db.scalar(select(Job).where(Job.type == JobType.slack_codex_qa))
            assert finished.status == JobStatus.succeeded
            assert finished.result_json["slack_post"]["ok"] is True
    finally:
        clear_isolated_env()
