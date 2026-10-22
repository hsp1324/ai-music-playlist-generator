#!/usr/bin/env python3
"""Install the self-contained Suno Studio skill without touching runtime state."""

import argparse
from pathlib import Path
import shutil
import sys


def install(workspace: Path) -> Path:
    source = Path(__file__).resolve().parents[1] / "skills" / "suno-studio-acquisition"
    destination = workspace.expanduser().resolve() / "skills" / source.name
    if source == destination:
        return destination
    # Copy only the maintained bundle; preserve any unrelated user files and all
    # recovery state, which belongs in the runtime checkout's storage directory.
    for relative in ("SKILL.md", "references/studio-download.md", "scripts/recovery_state.py"):
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / relative, target)
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path.home() / ".openclaw" / "workspace")
    args = parser.parse_args()
    try:
        print(f"Installed skill: {install(args.workspace)}")
        return 0
    except OSError as exc:
        print(f"Skill installation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
