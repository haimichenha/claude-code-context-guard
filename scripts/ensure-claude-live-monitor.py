#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
from datetime import datetime
from pathlib import Path

HOME = Path.home()
NPM_ROOT = Path(os.environ.get("APPDATA", str(HOME / "AppData" / "Roaming"))) / "npm"
CLAUDE_CODE_DIR = NPM_ROOT / "node_modules" / "@anthropic-ai" / "claude-code"
CLI_JS = CLAUDE_CODE_DIR / "cli.js"

PATCH_MARKER = "CLAUDE_LIVE_MONITOR_PATCHED"

TRANSCRIPT_SNAPSHOT = (
    "kA8=$7?_K.slice(0,$7.messagesLength):_K,"
    "Te8=$7?_q.slice(0,$7.streamingToolUsesLength):_q"
)
TRANSCRIPT_LIVE = "kA8=_K,Te8=_q"

SHOW_ALL_GATED = (
    'G1("transcript:toggleShowAll",P,{context:"Transcript",isActive:f&&!w})'
)
SHOW_ALL_LIVE = (
    'G1("transcript:toggleShowAll",P,{context:"Transcript",isActive:f})'
)


def stamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def backup(path: Path) -> Path:
    bak = path.with_name(f"{path.name}.bak-live-monitor-{stamp()}")
    shutil.copy2(path, bak)
    return bak


def patch_text(text: str) -> tuple[str, list[str]]:
    actions: list[str] = []

    if TRANSCRIPT_SNAPSHOT in text:
        text = text.replace(TRANSCRIPT_SNAPSHOT, TRANSCRIPT_LIVE, 1)
        actions.append("transcript uses live messages/tool streams instead of frozen slices")
    elif TRANSCRIPT_LIVE in text:
        actions.append("transcript live patch already present")
    else:
        raise RuntimeError("transcript snapshot pattern not found; Claude Code build may have changed")

    if SHOW_ALL_GATED in text:
        text = text.replace(SHOW_ALL_GATED, SHOW_ALL_LIVE, 1)
        actions.append("transcript:toggleShowAll remains active during virtual scroll")
    elif SHOW_ALL_LIVE in text:
        actions.append("show-all active patch already present")
    else:
        raise RuntimeError("toggleShowAll gating pattern not found; Claude Code build may have changed")

    return text, actions


def validate_text(text: str) -> list[str]:
    failures: list[str] = []
    if TRANSCRIPT_SNAPSHOT in text:
        failures.append("snapshot transcript slice is still present")
    if TRANSCRIPT_LIVE not in text:
        failures.append("live transcript assignment is missing")
    if SHOW_ALL_GATED in text:
        failures.append("virtual-scroll show-all gate is still present")
    if SHOW_ALL_LIVE not in text:
        failures.append("show-all active assignment is missing")
    return failures


def main() -> int:
    ap = argparse.ArgumentParser(description="Patch Claude Code transcript to update live while open.")
    ap.add_argument("--validate", action="store_true", help="Only validate the installed cli.js")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    if not CLI_JS.exists():
        print(f"[live-monitor] missing Claude Code cli.js: {CLI_JS}")
        return 2

    text = CLI_JS.read_text(encoding="utf-8", errors="replace")

    if args.validate:
        failures = validate_text(text)
        if failures:
            for f in failures:
                print(f"[FAIL] {f}")
            return 1
        print("[RESULT] PASS: Claude Code live transcript monitor patch is present")
        return 0

    new_text, actions = patch_text(text)
    if new_text != text:
        bak = backup(CLI_JS)
        CLI_JS.write_text(new_text, encoding="utf-8", newline="")
        if not args.quiet:
            print(f"[live-monitor] backup: {bak}")
    elif not args.quiet:
        print("[live-monitor] no file changes needed")

    failures = validate_text(CLI_JS.read_text(encoding="utf-8", errors="replace"))
    for a in actions:
        if not args.quiet:
            print(f"[OK] {a}")
    if failures:
        for f in failures:
            print(f"[FAIL] {f}")
        return 1
    if not args.quiet:
        print("[RESULT] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
