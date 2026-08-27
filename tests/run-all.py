#!/usr/bin/env python3
"""Run every available Cognitive OS suite with UTC timestamps.

The runner deliberately records environment and command output instead of
hiding failures behind a single aggregate status. Device-only Maestro coverage
is reported separately when Maestro is not installed.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "test-results"
STAMP = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
LOG_PATH = RESULTS / f"test-run-{STAMP}.log"

COMMANDS = [
    ("runtime Python unittest", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"] , ROOT),
    ("agent-service pytest", ["/tmp/cognitive-os-testenv/bin/pytest", "-q"], ROOT / "reference/scaffold/agent-service"),
    ("backend Jest", ["npm", "test", "--", "--runInBand"], ROOT / "reference/scaffold/backend"),
    ("web production build", ["npm", "run", "build"], ROOT / "reference/scaffold/web"),
    ("web Playwright Chromium", ["npx", "playwright", "test", "--config=playwright.config.js", "--reporter=line"], ROOT / "reference/scaffold/web"),
    ("mobile Expo Doctor", ["npx", "expo-doctor"], ROOT / "reference/scaffold/mobile"),
    ("mobile Expo web export", ["npm", "run", "export:web"], ROOT / "reference/scaffold/mobile"),
    ("mobile web Playwright", ["npx", "playwright", "test", "tests/mobile-web.spec.js", "--config=playwright.mobile.config.js", "--reporter=line"], ROOT / "reference/scaffold/web"),
]


def write(log, message: str) -> None:
    line = f"[{datetime.now(timezone.utc).isoformat(timespec='milliseconds')}] {message}\n"
    print(line, end="")
    log.write(line)
    log.flush()


def main() -> int:
    RESULTS.mkdir(parents=True, exist_ok=True)
    failures = 0
    with LOG_PATH.open("w", encoding="utf-8") as log:
        write(log, f"Cognitive OS clean-room run {STAMP}")
        write(log, f"python={platform.python_version()} node={shutil.which('node') or 'unavailable'}")
        write(log, f"playwright={shutil.which('playwright') or 'unavailable'} maestro={shutil.which('maestro') or 'unavailable'} adb={shutil.which('adb') or 'unavailable'}")
        write(log, f"root={ROOT}")
        for label, command, cwd in COMMANDS:
            if command[0].startswith("/tmp/") and not Path(command[0]).exists():
                write(log, f"SKIP {label}: missing isolated pytest executable")
                failures += 1
                continue
            write(log, f"START {label}: {' '.join(command)} (cwd={cwd})")
            result = subprocess.run(command, cwd=cwd, env=os.environ.copy(), text=True, capture_output=True)
            if result.stdout:
                log.write(result.stdout)
                print(result.stdout, end="")
            if result.stderr:
                log.write(result.stderr)
                print(result.stderr, end="", file=sys.stderr)
            if result.returncode:
                failures += 1
                write(log, f"FAIL {label}: exit={result.returncode}")
            else:
                write(log, f"PASS {label}")
        if shutil.which("maestro") is None:
            write(log, "NOT_APPLICABLE Maestro native-device flows: Maestro is not installed in this environment")
        write(log, f"SUMMARY failures={failures} log={LOG_PATH}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
