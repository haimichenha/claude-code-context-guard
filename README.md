# Claude Code Context Guard

A small Windows-oriented guard for improving Claude Code context behavior without committing secrets or local databases.

It provides:

- startup-time repair for `opus[1m]`, `permissions.defaultMode=auto`, and cc-switch provider settings;
- optional virtual 1.4M client-side context patch with `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=72`;
- ordinary-provider fallback window patch from 200k to 300k, so 72% auto-compact triggers around 201.6k instead of ~130k;
- automatic fallback to safe 1M when context-length errors are detected;
- medium-detail compact handoff policy;
- model-driven captured-output workflow through `ccrun`;
- long-term semantic memory structure for `/dev-docs-update` without changing its responsibility;
- persistent `/rename` UX patch so `/rename <name>` is shown and `/rename [name]` input strips the outer brackets.

## Architecture

Three memory layers:

1. **Compact Handoff** — current task continuity after compaction.
2. **Long-Term Semantic Memory** — `/dev-docs-update` and persistent notes for strategy/pitfall/workflow/preference/exception/fact.
3. **Raw Evidence Layer** — long logs/search/command output saved to disk; main context receives summary, path, key lines, and ranges.

## What not to commit

Do not commit:

- `~/.cc-switch/cc-switch.db` or any database;
- `~/.claude/settings.json` if it contains tokens/endpoints;
- patched Claude Code `cli.js`;
- logs, checkpoints, backups, `.claude-output/`;
- API keys, bearer tokens, cookies, sessions, OAuth data.

This repository stores scripts and templates that recreate the behavior. The startup guard patches the installed Claude Code bundle at launch time; updating Claude Code may overwrite local patches, and the guard should re-apply them on the next `claude`/`claude-c` start.

## Install

From the repo root in PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
```

Then open a new PowerShell window and use:

```powershell
claude
claude-c
```

For long-output commands the assistant should proactively use:

```powershell
ccrun "pio run"
ccrun "pytest"
ccrun "npm test"
```

The human should not need to remember `ccrun`; it is a model-side captured-output strategy.

## Verify

```powershell
python $env:USERPROFILE\.claude\scripts\validate-claude-context-policy.py
```

Expected experimental mode output includes:

```text
[OK] settings autoCompactWindow: 1400000
[OK] cli [1m] returns 1.4m
[OK] ordinary fallback window 300k
[OK] /rename strips optional brackets
[CALC] compact_threshold≈993,600 tokens
[RESULT] PASS
```

## Disable / enable virtual 1.4M

```powershell
python $env:USERPROFILE\.claude\scripts\ensure-claude-context-policy.py --disable-experimental
python $env:USERPROFILE\.claude\scripts\ensure-claude-context-policy.py --enable-experimental
```

## Notes

The virtual 1.4M patch is not intended to push requests to 1.36M tokens. With `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=72`, the target auto-compact threshold is around 993.6K tokens, closer to a practical 1M boundary than the default ~967K. If a session falls back to a non-`[1m]` model path, the guard raises Claude Code's ordinary fallback window to 300K so auto-compact occurs around 201.6K rather than around 130K.
