import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.config import Settings


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class SunoSessionStatus:
    provider_mode: str
    state: str
    authenticated: bool
    browser_open: bool
    needs_login: bool
    cookie_count: int
    message: str
    last_synced_at: str | None
    stale_after_hours: int
    profile_dir: str
    state_path: str
    log_path: str


class SunoBrowserSessionService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def get_status(self) -> SunoSessionStatus:
        browser_open = self._browser_open()
        payload = self._read_state_payload()
        cookies = payload.get("cookies") or []
        last_synced_at = payload.get("saved_at")
        authenticated = self._has_auth_cookies(cookies)
        stale = self._is_stale(last_synced_at)
        forced_login_required = bool(payload.get("forced_login_required_at"))

        if forced_login_required:
            state = "needs_login"
            message = "Session was explicitly marked as expired. Re-login is required."
        elif browser_open and authenticated:
            state = "active"
            message = "Suno browser session is active."
        elif browser_open:
            state = "login_in_progress"
            message = "Login window is open. Complete login in the browser."
        elif authenticated and not stale:
            state = "ready"
            message = "Stored browser session is ready."
        elif authenticated and stale:
            state = "stale"
            message = "Stored browser session looks stale. Re-login is recommended."
        else:
            state = "needs_login"
            message = "No reusable Suno browser session found."

        needs_login = state in {"needs_login", "stale"}
        return SunoSessionStatus(
            provider_mode=self.settings.suno_provider_mode,
            state=state,
            authenticated=authenticated and not stale,
            browser_open=browser_open,
            needs_login=needs_login,
            cookie_count=len(cookies),
            message=message,
            last_synced_at=last_synced_at,
            stale_after_hours=self.settings.suno_session_stale_hours,
            profile_dir=str(self.settings.suno_browser_profile_dir),
            state_path=str(self.settings.suno_browser_state_path),
            log_path=str(self.settings.suno_browser_log_path),
        )

    def open_login_window(self) -> dict[str, Any]:
        current = self.get_status()
        if current.browser_open:
            return {
                "ok": True,
                "launched": False,
                "message": "Login window already open.",
                "status": current.__dict__,
            }

        log_handle = self.settings.suno_browser_log_path.open("a", encoding="utf-8")
        command = [
            sys.executable,
            "-m",
            "app.scripts.suno_login_window",
            "--profile-dir",
            str(self.settings.suno_browser_profile_dir),
            "--state-path",
            str(self.settings.suno_browser_state_path),
            "--pid-path",
            str(self.settings.suno_browser_pid_path),
            "--login-url",
            self.settings.suno_browser_login_url,
            "--browser-name",
            self.settings.suno_browser_name,
        ]
        if self.settings.suno_browser_executable_path:
            command.extend(["--browser-executable-path", self.settings.suno_browser_executable_path])

        process = subprocess.Popen(
            command,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            cwd=Path(__file__).resolve().parents[2],
        )
        self.settings.suno_browser_pid_path.write_text(str(process.pid), encoding="utf-8")
        return {
            "ok": True,
            "launched": True,
            "pid": process.pid,
            "message": "Suno login browser launched.",
            "status": self.get_status().__dict__,
        }

    def read_storage_state(self) -> dict[str, Any]:
        return self._read_state_payload()

    def mark_login_required(self) -> SunoSessionStatus:
        payload = self._read_state_payload()
        payload["forced_login_required_at"] = utcnow().isoformat()
        self.settings.suno_browser_state_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return self.get_status()

    def _read_state_payload(self) -> dict[str, Any]:
        path = self.settings.suno_browser_state_path
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    @staticmethod
    def _has_auth_cookies(cookies: list[dict[str, Any]]) -> bool:
        for cookie in cookies:
            domain = str(cookie.get("domain", ""))
            if "suno" in domain or "clerk" in domain:
                return True
        return False

    def _is_stale(self, last_synced_at: str | None) -> bool:
        if not last_synced_at:
            return True
        try:
            synced = datetime.fromisoformat(last_synced_at)
        except ValueError:
            return True
        if synced.tzinfo is None:
            synced = synced.replace(tzinfo=timezone.utc)
        return utcnow() - synced > timedelta(hours=self.settings.suno_session_stale_hours)

    def _browser_open(self) -> bool:
        pid_path = self.settings.suno_browser_pid_path
        if not pid_path.exists():
            return False
        try:
            pid = int(pid_path.read_text(encoding="utf-8").strip())
        except ValueError:
            pid_path.unlink(missing_ok=True)
            return False

        try:
            os.kill(pid, 0)
        except OSError:
            pid_path.unlink(missing_ok=True)
            return False

        try:
            stat = subprocess.check_output(
                ["ps", "-o", "stat=", "-p", str(pid)],
                text=True,
            ).strip()
        except Exception:
            stat = ""

        if not stat or "Z" in stat:
            pid_path.unlink(missing_ok=True)
            return False
        return True
