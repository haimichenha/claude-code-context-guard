# Long-Term Semantic Memory

This file complements `/dev-docs-update`. It is not facts-only; it may store strategy, pitfall, workflow, preference, exception, and fact items.

## Suggested Memory Item Structure

```md
## Memory Item

type: fact | strategy | pitfall | workflow | preference | exception
scope:
summary:
rationale:
evidence: required for type=fact; optional for others
when_to_apply:
when_not_to_apply:
last_verified:
```

## Memory Item

type: strategy
scope: claude-code-context
summary: Use startup-time context policy repair so cc-switch or Claude Code updates do not permanently remove context settings.
rationale: cc-switch can rewrite Claude settings; startup wrappers can re-apply deterministic settings before each session.
when_to_apply: launching Claude Code through `claude` or `claude-c`.
when_not_to_apply: one-off debugging where the user explicitly disables the wrapper.
last_verified: 2026-05-20

## Memory Item

type: workflow
scope: large-output-handling
summary: Save raw output to file, send summary/path/key lines to the main context, and re-read ranges only when needed.
rationale: Preserves evidence without filling the active model context with logs.
when_to_apply: long shell/test/build/search/log output.
when_not_to_apply: short output that is already decision-critical.
last_verified: 2026-05-20
```
