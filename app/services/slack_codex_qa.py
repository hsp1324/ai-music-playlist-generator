from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from app.config import Settings


def build_slack_codex_prompt(*, user_text: str, user_id: str | None = None) -> str:
    now = datetime.now(timezone.utc).isoformat()
    speaker = user_id or "slack-user"
    return "\n".join(
        [
            "You are Codex answering a Slack question for the ai-music-playlist-generator operator.",
            "Answer in Korean unless the user explicitly asks for another language.",
            "Return only the final Slack answer. Do not include internal reasoning, progress logs, or command transcripts.",
            "Keep the answer concise and operational. If you inspected repo or local state, summarize only the useful result.",
            "This Slack bridge is read-only: do not edit files, commit, push, restart services, publish videos, or mutate data.",
            "You may read local repo files and run safe read-only inspection commands if needed.",
            "If a requested action would require changing state, explain that it must be done from the normal Codex session.",
            f"Current UTC time: {now}",
            f"Slack user: {speaker}",
            "",
            "User message:",
            user_text.strip(),
        ]
    )


def resolve_codex_command(settings: Settings) -> str:
    command = settings.slack_codex_qa_command.strip() or settings.codex_metadata_command.strip() or "codex"
    if "/" in command:
        if Path(command).exists():
            return command
        raise RuntimeError(f"codex command not found: {command}")
    resolved = shutil.which(command)
    if not resolved:
        raise RuntimeError(f"codex command not found: {command}")
    return resolved


def run_slack_codex_answer(settings: Settings, *, user_text: str, user_id: str | None = None) -> str:
    command = resolve_codex_command(settings)
    prompt = build_slack_codex_prompt(user_text=user_text, user_id=user_id)
    project_root = Path(__file__).resolve().parents[2]
    timeout = max(int(settings.slack_codex_qa_timeout_seconds or 0), 30)

    with tempfile.TemporaryDirectory(prefix="aimp-slack-codex-") as temp_dir:
        output_path = Path(temp_dir) / "answer.txt"
        cmd = [
            command,
            "exec",
            "--ephemeral",
            "--sandbox",
            "read-only",
            "--cd",
            str(project_root),
            "--color",
            "never",
            "-o",
            str(output_path),
        ]
        if settings.slack_codex_qa_model.strip():
            cmd.extend(["--model", settings.slack_codex_qa_model.strip()])
        cmd.append("-")

        env = dict(os.environ)
        env["NO_COLOR"] = "1"
        result = subprocess.run(
            cmd,
            input=prompt,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
            cwd=project_root,
            env=env,
        )
        if result.returncode != 0:
            stderr = (result.stderr or result.stdout or "").strip()
            raise RuntimeError(stderr or f"codex exited with status {result.returncode}")

        if output_path.exists():
            answer = output_path.read_text(encoding="utf-8").strip()
        else:
            answer = result.stdout.strip()
        if not answer:
            raise RuntimeError("codex returned an empty answer")
        return truncate_slack_answer(answer, max_chars=settings.slack_codex_qa_max_answer_chars)


def truncate_slack_answer(answer: str, *, max_chars: int) -> str:
    clean = answer.strip()
    limit = max(int(max_chars or 0), 500)
    if len(clean) <= limit:
        return clean
    return clean[: limit - 30].rstrip() + "\n\n...(truncated)"
