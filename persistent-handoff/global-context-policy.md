# Global Context Policy

Purpose: widen Claude Code usable context while preserving model capability and reducing bad compaction experiences.

## Context Admission Control

Do not hard-ban long context. Default to controlled admission:

1. Preserve raw evidence on disk when command/test/log output is long.
2. Put only summary, path, exit code, key findings, and line ranges in the main chat.
3. Re-read raw evidence by line range when a decision depends on missing context.
4. Do not edit code based only on a lossy summary when the relevant evidence is absent.

Default long-output flow:

```text
raw output -> save to file
main context -> summary + path + key line ranges
need more -> range-read the saved file
```

## Skill Loading Policy

Use skills on demand, not by preloading every skill body.

Load a skill when:
- the user explicitly names it, for example `$all-search-stack`;
- the task clearly matches the skill description;
- a project entry rule requires it, for example `skills/SKILL.md`.

After loading `SKILL.md`, load only directly relevant references/scripts/assets. Do not bulk-load reference folders.

## Subagent Policy

Use subagents for broad exploration, large searches, and log summarization. The main session must keep decision-critical evidence snippets, paths, line numbers, and uncertainty notes.

## Compact Policy

Compact handoff should be medium-detail, not minimal. Preserve reasoning skeleton and evidence map, not raw noise.

## Model-Driven Captured Command Use

The human should not need to remember `ccrun`.

When the assistant/model is about to run a command likely to produce long output, it should prefer:

```powershell
ccrun "<command>"
```

or the direct script form:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "%USERPROFILE%\.claude\scripts\ccrun.ps1" "<command>"
```

Use normal direct commands for short, low-output checks such as `git status`, `dir`, `where`, or version probes.

If the user asks for the full output, provide/export the saved log path instead of pasting the full log into the main context.
