from types import SimpleNamespace

from app.models.enums import JobStatus
from app.utils import ops_notifications
from scripts.openclaw_release import upload_failure_notice


def test_upload_failure_notice_defaults_to_korean() -> None:
    notice = upload_failure_notice(
        release={"title": "테스트 릴리스"},
        failures=[{"title": "Broken Track", "audio_path": "/tmp/broken.mp3", "error": "boom"}],
        uploaded_count=2,
        action="auto-publish-playlist",
    )

    assert "*OpenClaw 오디오 업로드 문제*" in notice
    assert "릴리스:" in notice
    assert "동작:" in notice
    assert "남은 업로드 완료 트랙:" in notice
    assert "렌더/게시가 중단되었습니다." in notice


def test_ops_notifications_use_korean_titles_and_labels(monkeypatch) -> None:
    captured: dict[str, str] = {}

    def fake_post_ops_message(*args, **kwargs):
        captured["text"] = kwargs.get("text", "")
        captured["blocks"] = str(kwargs.get("blocks"))
        captured["image_title"] = kwargs.get("image_title", "")
        return {"ok": True}

    monkeypatch.setattr(ops_notifications, "post_ops_message", fake_post_ops_message)

    playlist = SimpleNamespace(title="My Release", metadata_json={})
    job = SimpleNamespace(
        status=JobStatus.queued,
        payload_json={"video_spectrum_overlay_style": "bars", "actor": "bot"},
        result_json={},
    )

    services = SimpleNamespace(settings=SimpleNamespace(video_render_execution_mode="queue"))
    db = SimpleNamespace(add=lambda *args, **kwargs: None, commit=lambda *args, **kwargs: None)
    result = ops_notifications.notify_video_render_queued(db, services, playlist=playlist, job=job)

    assert result["ok"] is True
    assert "비디오 렌더 대기" in captured["text"]
    assert "모드:" in captured["text"]
    assert "비주얼라이저:" in captured["text"]
    assert "요청자:" in captured["text"]
    assert "아트워크" in captured["image_title"]
