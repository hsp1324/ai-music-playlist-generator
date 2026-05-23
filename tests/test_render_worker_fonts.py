from __future__ import annotations

from scripts import render_worker


class _FakeFcMatchResult:
    def __init__(self, stdout: str) -> None:
        self.returncode = 0
        self.stdout = stdout


def test_detect_cjk_lyric_font_prefers_japanese_font_for_kana(monkeypatch) -> None:
    monkeypatch.delenv("AIMP_RENDER_WORKER_CJK_FONT", raising=False)
    monkeypatch.delenv("AIMP_RENDER_WORKER_JAPANESE_FONT", raising=False)
    monkeypatch.setattr(render_worker.shutil, "which", lambda _name: "/usr/bin/fc-match")

    calls: list[str] = []

    def fake_run(cmd, **_kwargs):  # noqa: ANN001
        candidate = cmd[-1]
        calls.append(candidate)
        if candidate == "Yu Gothic":
            return _FakeFcMatchResult("Yu Gothic|/fonts/YuGothR.ttc\n")
        return _FakeFcMatchResult("DejaVu Sans|/fonts/DejaVuSans.ttf\n")

    monkeypatch.setattr(render_worker.subprocess, "run", fake_run)

    assert render_worker.detect_cjk_lyric_font("夜風に揺れるメロディ") == "Yu Gothic"
    assert "Yu Gothic" in calls
    candidates = render_worker.cjk_font_candidates_for_text("夜風に揺れるメロディ")
    assert candidates.index("Yu Gothic") < candidates.index("Noto Sans KR")


def test_detect_cjk_lyric_font_prefers_korean_font_for_hangul(monkeypatch) -> None:
    monkeypatch.delenv("AIMP_RENDER_WORKER_CJK_FONT", raising=False)
    monkeypatch.delenv("AIMP_RENDER_WORKER_KOREAN_FONT", raising=False)
    monkeypatch.setattr(render_worker.shutil, "which", lambda _name: "/usr/bin/fc-match")

    calls: list[str] = []

    def fake_run(cmd, **_kwargs):  # noqa: ANN001
        candidate = cmd[-1]
        calls.append(candidate)
        if candidate == "Noto Sans KR":
            return _FakeFcMatchResult("Noto Sans KR|/fonts/NotoSansKR-VF.ttf\n")
        if candidate == "Yu Gothic":
            return _FakeFcMatchResult("Yu Gothic|/fonts/YuGothR.ttc\n")
        return _FakeFcMatchResult("DejaVu Sans|/fonts/DejaVuSans.ttf\n")

    monkeypatch.setattr(render_worker.subprocess, "run", fake_run)

    assert render_worker.detect_cjk_lyric_font("밤길에 피어나는 노래") == "Noto Sans KR"
    assert "Yu Gothic" not in calls


def test_lyric_text_for_font_detection_includes_track_lyrics() -> None:
    text = render_worker.lyric_text_for_font_detection(
        {
            "lyric_tracks": [
                {"title": "Track", "lyrics": "港の灯り\n君と走る"},
            ],
            "lyric_cues": [{"text": "fallback line"}],
        }
    )

    assert "港の灯り" in text
    assert "fallback line" in text
