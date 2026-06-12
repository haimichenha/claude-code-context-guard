#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT = Path.home() / ".claude" / "scripts" / "ensure-claude-live-monitor.py"
LOCAL_SCRIPT = Path(__file__).with_name("ensure-claude-live-monitor.py")


def main() -> int:
    script = LOCAL_SCRIPT if LOCAL_SCRIPT.exists() else SCRIPT
    return subprocess.call([sys.executable, str(script), "--validate"])


if __name__ == "__main__":
    raise SystemExit(main())
