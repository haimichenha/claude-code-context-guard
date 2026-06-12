# Claude Code Context Guard

A small Windows-oriented guard for improving Claude Code context behavior without committing secrets or local databases.

It provides:

- startup-time repair for `opus[1m]`, `permissions.defaultMode=auto`, and cc-switch provider settings;
- optional managed 1.2M client-side context window with `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=72` when the installed Claude Code package still exposes a JavaScript `cli.js` bundle;
- ordinary-provider fallback window patch from 200k to 300k on JavaScript `cli.js` builds, so 72% auto-compact triggers around 201.6k instead of ~130k;
- local 1M alias for routed `gpt-5.5` sessions on JavaScript `cli.js` builds without changing the actual API model name to `gpt-5.5[1m]`;
- automatic fallback to safe 1M when context-length errors are detected;
- medium-detail compact handoff policy;
- model-driven captured-output workflow through `ccrun`;
- long-term semantic memory structure for `/dev-docs-update` without changing its responsibility;
- persistent `/rename` UX patch on JavaScript `cli.js` builds so `/rename <name>` is shown and `/rename [name]` input strips the outer brackets;
- optional live transcript monitor patch on JavaScript `cli.js` builds so `Ctrl+O` transcript uses live message/tool streams instead of a frozen entry snapshot.

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

This repository stores scripts and templates that recreate the behavior. On older Claude Code installs that include a JavaScript `cli.js` bundle, the startup guard patches the installed bundle at launch time; updating Claude Code may overwrite local patches, and the guard should re-apply them on the next `claude`/`claude-c` start. On newer native-binary installs that ship `bin/claude.exe` without `cli.js`, the guard keeps the wrapper, settings, environment files, compact handoff, and `ccrun` workflow active, but skips bundle-only patches and reports that mode during validation.

## Claude Code native binary compatibility

Claude Code 2.1.173 and newer Windows packages may install as:

```text
%APPDATA%\npm\node_modules\@anthropic-ai\claude-code\bin\claude.exe
```

with no root `cli.js`. In this mode:

- available: startup settings repair, `permissions.defaultMode=auto`, `autoCompactWindow` settings, environment files, compact handoff templates, persistent notes, `claude-c`, and `ccrun`;
- unavailable until a supported native configuration hook is found: JavaScript bundle internals patch, `gpt-5.5` local 1M alias patch, ordinary fallback 300k bundle patch, `/rename` UX patch, and live transcript monitor patch.

Validation treats those bundle-only checks as `[SKIP]` instead of failing with a traceback.

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


## AS-aware compact profile

If this machine also uses `all-search-stack` `/AS`, install the AS-aware compact template so compaction preserves requirement IDs, repository freshness, governance reminders, known-good state, failed paths, staging candidates, missing measurements, and the next smallest action.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -AsAwareCompact
```

This copies `persistent-handoff/compact-template.as.md` to `%USERPROFILE%\.claude\persistent-handoff\compact-template.md` and keeps a copy as `compact-template.as.md`.

## Live transcript monitor

Claude Code's fullscreen transcript can freeze the message/tool list at the moment `Ctrl+O` is opened. The live monitor patch changes the installed JS bundle so the transcript reads the current message and streaming-tool arrays while it remains open. It also keeps `transcript:toggleShowAll` active during virtual scrolling.

Install applies this patch by default when the installed Claude Code package still contains a JavaScript `cli.js` bundle:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
```

Skip only the live-monitor patch:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -NoLiveMonitorPatch
```

Apply or validate it manually:

```powershell
python $env:USERPROFILE\.claude\scripts\ensure-claude-live-monitor.py
python $env:USERPROFILE\.claude\scripts\validate-claude-live-monitor.py
```

The script backs up the installed bundle before patching, for example:

```text
cli.js.bak-live-monitor-YYYYMMDD-HHMMSS
```

If Anthropic changes the minified bundle shape, validation will fail instead of guessing. If Anthropic ships only a native binary, validation reports `[SKIP]` for this patch because there is no JavaScript bundle to modify.

## Verify

```powershell
python $env:USERPROFILE\.claude\scripts\validate-claude-context-policy.py
python $env:USERPROFILE\.claude\scripts\validate-claude-live-monitor.py
```

Expected experimental mode output includes:

```text
[OK] settings autoCompactWindow: 1200000
[OK] cli [1m]/gpt-5.5 alias returns 1.2m
[OK] ordinary fallback window 300k
[OK] /rename strips optional brackets
[CALC] compact_threshold~=849,600 tokens
[RESULT] PASS
```

On native-binary Claude Code builds, expected output includes:

```text
[OK] Claude Code install mode: native-binary version=...
[INFO] cli.js patch checks are skipped because this Claude Code build ships bin/claude.exe
[INFO] threshold calculations describe configured settings; native binary enforcement is not verified
[SKIP] cli [1m]/gpt-5.5 alias returns 1.2m: native binary install has no patchable cli.js
[RESULT] PASS
```

## Disable / enable managed 1.2M

```powershell
python $env:USERPROFILE\.claude\scripts\ensure-claude-context-policy.py --disable-experimental
python $env:USERPROFILE\.claude\scripts\ensure-claude-context-policy.py --enable-experimental
```

## Notes

The managed 1.2M window is not intended to push requests to 1.18M tokens. With `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=72`, the target auto-compact threshold is around 849.6K tokens. If a session is routed to `gpt-5.5`, the guard treats that local model string as 1M-capable in JavaScript `cli.js` builds while still sending `gpt-5.5` to the API. If a session falls back to any other non-`[1m]` model path, the guard raises Claude Code's ordinary fallback window to 300K so auto-compact occurs around 201.6K rather than around 130K. These bundle-level behavior changes require a JavaScript `cli.js` install; native-binary installs keep the surrounding compact policy and settings but cannot apply these bundle patches.
