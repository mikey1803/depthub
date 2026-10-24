"""Write version.json (used by the footer badge and the deploy history).

Jenkins sets BUILD_NUMBER and GIT_COMMIT. Anything missing falls back to git
or to a placeholder, so this also works on a laptop.

Usage: python scripts/make_version.py
"""
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def git(*args):
    try:
        result = subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def main():
    commit = os.environ.get("GIT_COMMIT") or git("rev-parse", "HEAD") or "unknown"
    version = {
        "build": os.environ.get("BUILD_NUMBER", "0"),
        "commit": commit,
        "commit_short": commit[:7],
        "message": git("log", "-1", "--pretty=%s") or "unknown",
        "author": git("log", "-1", "--pretty=%an") or "unknown",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    (ROOT / "version.json").write_text(json.dumps(version, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote version.json: v{version['build']} commit {version['commit_short']}")


if __name__ == "__main__":
    main()
