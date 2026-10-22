import contextlib
import importlib.util
import io
import json
from pathlib import Path
import wave

import pytest

from scripts.install_suno_studio_skill import install


SCRIPT = Path(__file__).resolve().parents[1] / "skills/suno-studio-acquisition/scripts/recovery_state.py"
SPEC = importlib.util.spec_from_file_location("suno_studio_recovery", SCRIPT)
recovery = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(recovery)
SOURCE_A = "11111111-1111-4111-8111-111111111111"
SOURCE_B = "22222222-2222-4222-8222-222222222222"


def call(state, *arguments):
    output, error = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
        code = recovery.main(["--state", str(state), *map(str, arguments)])
    return code, json.loads(error.getvalue() if code else output.getvalue())


def original(sid=SOURCE_A, **extra):
    return {"source_id": sid, "source_url": f"https://suno.com/song/{sid}",
            "model": "v6", "model_evidence": "original song-details v6 screenshot", "title": "Same Title", **extra}


def inventory(tmp_path, state, rows):
    page = tmp_path / "page.json"
    page.write_text(json.dumps(rows))
    return call(state, "inventory", "--manifest", page, "--cursor", "page-2-original-anchor")


@pytest.fixture
def state(tmp_path):
    path = tmp_path / "runtime" / "recovery.json"
    assert call(path, "init", "--batch-id", "one-time", "--workspace", "playlist_openclaw_desktop",
                "--cutoff", "original-ID-at-start")[0] == 0
    return path


@pytest.fixture
def audio(tmp_path):
    path = tmp_path / "full-mix.wav"
    with wave.open(str(path), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(8000)
        stream.writeframes(b"\x00\x00" * 16000)
    return path


def record(state, audio, sid=SOURCE_A, expected=2):
    return call(state, "record", "--source-id", sid, "--audio", audio,
                "--expected-seconds", expected, "--studio-url", "https://suno.com/studio/project")


def accept(tmp_path, state, sid=SOURCE_A, track_id="app-track-a", status="approved"):
    receipt = tmp_path / f"{sid}-receipt.json"
    receipt.write_text(json.dumps({"ok": True, "track": {"id": track_id, "status": status}}))
    return call(state, "accept", "--source-id", sid, "--receipt", receipt)


def test_status_does_not_initialize_or_scan(tmp_path):
    state = tmp_path / "not-created" / "recovery.json"
    code, result = call(state, "status")
    assert code == 0
    assert result == {"phase": "uninitialized", "action": "needs_initial_inventory", "scan_library": False}
    assert not state.parent.exists()


def test_inventory_resumes_by_source_id_without_resetting_saved_progress(tmp_path, state, audio):
    assert inventory(tmp_path, state, [original()])[0] == 0
    assert record(state, audio)[0] == 0
    assert inventory(tmp_path, state, [original(), original(SOURCE_B)])[0] == 0
    code, result = call(state, "status")
    assert code == 0
    assert result["counts"]["saved"] == 1
    assert result["counts"]["pending"] == 1
    assert result["cursor"] == "page-2-original-anchor"
    assert result["workspace"] == "playlist_openclaw_desktop"
    assert result["cutoff"] == "original-ID-at-start"
    code, pending = call(state, "pending", "--limit", "1")
    assert len(pending["tracks"]) == 1
    assert pending["tracks"][0]["status"] == "saved"
    assert pending["tracks"][0]["audio"]["path"] == str(audio.resolve())


def test_failed_page_does_not_commit_a_partial_inventory(tmp_path, state):
    before = state.read_bytes()
    bad = original(SOURCE_B, source_url="https://example.com/not-the-original")
    assert inventory(tmp_path, state, [original(), bad])[0] == 1
    assert state.read_bytes() == before


def test_pending_or_blocked_sources_cannot_be_marked_complete(tmp_path, state):
    assert inventory(tmp_path, state, [original()])[0] == 0
    assert call(state, "complete")[0] == 1
    assert call(state, "seal", "--evidence", "Reached end of frozen workspace scope at original ID")[0] == 0
    assert call(state, "complete")[0] == 1
    assert call(state, "block", "--source-id", SOURCE_A, "--reason", "Official download timed out")[0] == 0
    assert call(state, "complete")[0] == 1
    assert call(state, "status")[1]["scan_library"] is False
    assert inventory(tmp_path, state, [original(SOURCE_B)])[0] == 1


def test_record_rejects_corrupt_or_cropped_audio_and_preserves_pending(tmp_path, state, audio):
    assert inventory(tmp_path, state, [original()])[0] == 0
    corrupt = tmp_path / "not-audio.wav"
    corrupt.write_text("<html>download was not received</html>")
    assert record(state, corrupt)[0] == 1
    assert record(state, audio, expected=240)[0] == 1
    assert call(state, "status")[1]["counts"]["pending"] == 1
    assert record(state, audio)[0] == 0
    saved = json.loads(state.read_text())["tracks"][SOURCE_A]["audio"]
    assert saved["duration_seconds"] == 2
    assert saved["full_decode"] is True
    assert saved["sha256"] == recovery.fingerprint(audio)
    assert record(state, audio)[0] == 1


def test_ingestion_requires_an_actual_approved_receipt_and_distinct_app_track_ids(tmp_path, state, audio):
    assert inventory(tmp_path, state, [original(), original(SOURCE_B)])[0] == 0
    assert accept(tmp_path, state)[0] == 1
    assert record(state, audio)[0] == 0
    assert accept(tmp_path, state, status="pending_review")[0] == 1
    assert accept(tmp_path, state)[0] == 0
    assert record(state, audio, SOURCE_B)[0] == 0
    assert accept(tmp_path, state, SOURCE_B)[0] == 1
    assert accept(tmp_path, state, SOURCE_B, track_id="app-track-b")[0] == 0


@pytest.mark.parametrize("change_before_accept", [True, False])
def test_changed_files_cannot_complete_recovery(tmp_path, state, audio, change_before_accept):
    assert inventory(tmp_path, state, [original()])[0] == 0
    assert call(state, "seal", "--evidence", "Confirmed end of original workspace inventory")[0] == 0
    assert record(state, audio)[0] == 0
    if not change_before_accept:
        assert accept(tmp_path, state)[0] == 0
    audio.write_bytes(b"truncated")
    if change_before_accept:
        assert accept(tmp_path, state)[0] == 1
    assert call(state, "complete")[0] == 1
    assert call(state, "status")[1]["phase"] == "recovering"


def test_completed_recovery_never_reopens_or_rechecks_historical_files(tmp_path, state, audio):
    assert inventory(tmp_path, state, [original()])[0] == 0
    assert call(state, "seal", "--evidence", "Confirmed complete frozen-scope inventory")[0] == 0
    assert record(state, audio)[0] == 0
    assert accept(tmp_path, state)[0] == 0
    code, result = call(state, "complete")
    assert code == 0
    assert result["action"] == "fresh_production"
    assert result["scan_library"] is False
    marker = result["completed_at"]
    audio.unlink()  # Later artifact cleanup must not trigger another historical scan.
    assert call(state, "status")[1]["completed_at"] == marker
    assert call(state, "pending")[1]["tracks"] == []
    assert inventory(tmp_path, state, [original(SOURCE_B)])[0] == 1
    assert call(state, "block", "--source-id", SOURCE_A, "--reason", "new batch failed")[0] == 1
    assert call(state, "init", "--batch-id", "one-time", "--workspace", "playlist_openclaw_desktop",
                "--cutoff", "original-ID-at-start")[1]["phase"] == "complete"
    assert call(state, "init", "--batch-id", "restart-again", "--workspace", "playlist_openclaw_desktop",
                "--cutoff", "later")[0] == 1


def test_non_v6_exclusions_are_explicit_and_never_downloaded(tmp_path, state, audio):
    assert inventory(tmp_path, state, [original(model="v5.5")])[0] == 1
    assert inventory(tmp_path, state, [original(model="v5.5", exclusion_reason="Original model is legacy")])[0] == 0
    assert record(state, audio)[0] == 1
    assert call(state, "status")[1]["counts"]["excluded"] == 1


def test_explicit_human_cancellation_preserves_pending_without_fake_completion(tmp_path, state):
    assert inventory(tmp_path, state, [original()])[0] == 0
    code, result = call(state, "cancel", "--reason", "Human cancelled historical scan; resume ordinary production")
    assert code == 0
    assert result["phase"] == "cancelled" and result["action"] == "fresh_production"
    assert result["scan_library"] is False and result["completed_at"] is None
    assert result["counts"]["pending"] == 1 and result["cancelled_at"]
    assert call(state, "pending")[1]["tracks"] == []
    assert inventory(tmp_path, state, [original(SOURCE_B)])[0] == 1
    assert call(state, "complete")[0] == 1


def test_install_is_self_contained_and_preserves_completion_state(tmp_path):
    workspace = tmp_path / "openclaw-workspace"
    state = workspace / "storage" / "suno-studio-recovery.json"
    state.parent.mkdir(parents=True)
    state.write_text('{"phase":"complete"}')
    destination = install(workspace)
    assert (destination / "SKILL.md").is_file()
    assert (destination / "references/studio-download.md").is_file()
    assert (destination / "scripts/recovery_state.py").read_bytes() == SCRIPT.read_bytes()
    personal_note = destination / "personal-note.txt"
    personal_note.write_text("keep this")
    install(workspace)
    assert personal_note.read_text() == "keep this"
    assert state.read_text() == '{"phase":"complete"}'
