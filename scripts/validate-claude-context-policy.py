#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import pathlib
import sqlite3

HOME = pathlib.Path.home()
APPDATA = pathlib.Path(os.environ.get("APPDATA", str(HOME / "AppData" / "Roaming")))
CLAUDE_CODE_DIR = APPDATA / "npm" / "node_modules" / "@anthropic-ai" / "claude-code"
CLI = CLAUDE_CODE_DIR / "cli.js"
CLAUDE_EXE = CLAUDE_CODE_DIR / "bin" / "claude.exe"
PKG = CLAUDE_CODE_DIR / "package.json"
SETTINGS = HOME / ".claude" / "settings.json"
STATE = HOME / ".claude" / "context-policy-state.json"
CCDB = HOME / ".cc-switch" / "cc-switch.db"


def ok(name: str, cond: bool, detail: str = "") -> bool:
    print(f"[{'OK' if cond else 'FAIL'}] {name}{(': ' + detail) if detail else ''}")
    return bool(cond)


def skip(name: str, detail: str = "") -> bool:
    print(f"[SKIP] {name}{(': ' + detail) if detail else ''}")
    return True


def load_json(path: pathlib.Path) -> tuple[dict, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except Exception as exc:
        return {}, str(exc)


def package_version() -> str:
    data, err = load_json(PKG)
    if err:
        return "unknown"
    return str(data.get("version", "unknown"))


def check_cli_patch(name: str, needle: str, text: str | None) -> bool:
    if text is None:
        return skip(name, "native binary install has no patchable cli.js")
    return ok(name, needle in text)


def main() -> int:
    passed = True

    settings, settings_err = load_json(SETTINGS)
    state, state_err = load_json(STATE)
    passed &= ok("settings.json readable", settings_err is None, settings_err or str(SETTINGS))
    passed &= ok("context-policy-state.json readable", state_err is None, state_err or str(STATE))

    cli_text: str | None = None
    version = package_version()
    if CLI.exists():
        passed &= ok("Claude Code install mode", True, f"javascript-cli version={version}")
        cli_text = CLI.read_text(encoding="utf-8", errors="replace")
    elif CLAUDE_EXE.exists():
        passed &= ok("Claude Code install mode", True, f"native-binary version={version}")
        print("[INFO] cli.js patch checks are skipped because this Claude Code build ships bin/claude.exe")
        print("[INFO] threshold calculations describe configured settings; native binary enforcement is not verified")
    else:
        passed &= ok("Claude Code install mode", False, f"missing {CLI} and {CLAUDE_EXE}")

    disabled = bool(state.get("experimental_disabled"))
    target_window = 1_000_000 if disabled else 1_200_000
    pct = None if disabled else 72.0

    expected_model = str(state.get("target_model") or "opus")
    passed &= ok(f"model {expected_model}", settings.get("model") == expected_model, str(settings.get("model")))
    passed &= ok(
        "permission auto",
        settings.get("permissions", {}).get("defaultMode") == "auto",
        str(settings.get("permissions", {}).get("defaultMode")),
    )
    passed &= ok(
        "settings autoCompactWindow",
        settings.get("autoCompactWindow") == target_window,
        str(settings.get("autoCompactWindow")),
    )

    if not disabled:
        passed &= ok(
            "pct override 72",
            settings.get("env", {}).get("CLAUDE_AUTOCOMPACT_PCT_OVERRIDE") == "72",
            str(settings.get("env", {}).get("CLAUDE_AUTOCOMPACT_PCT_OVERRIDE")),
        )
        passed &= check_cli_patch(
            "cli [1m]/gpt-5.5 alias returns 1.2m",
            'if(DP(q)||o5(q).includes("gpt-5.5"))return 12e5',
            cli_text,
        )
        passed &= check_cli_patch(
            "cli schema max 1.2m",
            "autoCompactWindow:y.number().int().min(1e5).max(12e5).optional()",
            cli_text,
        )
        passed &= check_cli_patch("cli env max 1.2m", "$LK=12e5", cli_text)
    else:
        passed &= check_cli_patch("cli [1m] returns safe 1m", "if(DP(q))return 1e6", cli_text)

    passed &= check_cli_patch("pct override supported", "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE", cli_text)
    passed &= check_cli_patch("rename usage hint", "Usage: /rename <name>", cli_text)
    if cli_text is not None:
        passed &= ok("rename legacy usage removed", "Usage: /rename [name]" not in cli_text)
    passed &= check_cli_patch(
        "rename strips optional brackets",
        'else z=_.trim().replace(/^\\[(.*)\\]$/,"$1").trim();',
        cli_text,
    )
    passed &= check_cli_patch("rename argumentHint", 'argumentHint:"<name>"', cli_text)
    if cli_text is not None:
        passed &= ok("rename legacy argumentHint removed", 'argumentHint:"[name]"' not in cli_text)
    passed &= check_cli_patch(
        "ordinary fallback window 300k",
        "var DR1=300000,Po6=20000,UO_=32000,QO_=128000,pgq=8000;",
        cli_text,
    )

    reserved_summary = min(20_000, 20_000)
    effective = target_window - reserved_summary
    default_threshold = effective - 13_000
    threshold = int(effective * (pct / 100.0)) if pct else default_threshold
    threshold = min(threshold, default_threshold)
    print(f"[CALC] target_window={target_window:,} effective={effective:,} compact_threshold~={threshold:,} tokens")
    if not disabled:
        print(f"[CALC] old_1m_threshold~=967,000; new_threshold_delta~={threshold - 967000:+,} tokens")
    ordinary_effective = 300_000 - reserved_summary
    ordinary_threshold = int(ordinary_effective * 0.72)
    print(f"[CALC] ordinary_model_window=300,000 ordinary_compact_threshold~={ordinary_threshold:,} tokens")

    if CCDB.exists():
        conn = sqlite3.connect(CCDB)
        try:
            common_row = conn.execute("select value from settings where key='common_config_claude'").fetchone()
            current_row = conn.execute(
                "select settings_config from providers where app_type='claude' and is_current=1"
            ).fetchone()
        finally:
            conn.close()
        if common_row:
            common = json.loads(common_row[0])
            passed &= ok("cc-switch common window", common.get("autoCompactWindow") == target_window, str(common.get("autoCompactWindow")))
        else:
            passed &= ok("cc-switch common window", False, "missing common_config_claude")
        if current_row:
            provider = json.loads(current_row[0])
            passed &= ok("cc-switch current window", provider.get("autoCompactWindow") == target_window, str(provider.get("autoCompactWindow")))
        else:
            passed &= ok("cc-switch current window", False, "missing current Claude provider")

    print("[RESULT]", "PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
