import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_state(path: Path, storage_state: dict, browser_name: str, login_url: str) -> None:
    cookies = storage_state.get("cookies", [])
    payload = {
        "saved_at": utcnow_iso(),
        "browser_name": browser_name,
        "login_url": login_url,
        "cookie_count": len(cookies),
        "domains": sorted({cookie.get("domain", "") for cookie in cookies}),
        "cookies": cookies,
        "origins": storage_state.get("origins", []),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile-dir", required=True)
    parser.add_argument("--state-path", required=True)
    parser.add_argument("--pid-path", required=True)
    parser.add_argument("--login-url", required=True)
    parser.add_argument("--browser-name", default="chromium")
    parser.add_argument("--browser-executable-path", default="")
    args = parser.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        Path(args.state_path).write_text(
            json.dumps(
                {
                    "saved_at": utcnow_iso(),
                    "error": "playwright_not_installed",
                    "message": str(exc),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        raise SystemExit(1)

    profile_dir = Path(args.profile_dir)
    state_path = Path(args.state_path)
    pid_path = Path(args.pid_path)

    with sync_playwright() as playwright:
        browser_type = getattr(playwright, args.browser_name)
        launch_kwargs = {
            "user_data_dir": str(profile_dir),
            "headless": False,
        }
        if args.browser_executable_path:
            launch_kwargs["executable_path"] = args.browser_executable_path

        context = browser_type.launch_persistent_context(**launch_kwargs)
        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(args.login_url, wait_until="domcontentloaded")
            while True:
                if not context.pages:
                    break
                try:
                    still_open = any(not current_page.is_closed() for current_page in context.pages)
                except Exception:
                    still_open = False
                if not still_open:
                    break
                time.sleep(5)
            write_state(state_path, context.storage_state(), args.browser_name, args.login_url)
        finally:
            pid_path.unlink(missing_ok=True)
            context.close()


if __name__ == "__main__":
    main()
