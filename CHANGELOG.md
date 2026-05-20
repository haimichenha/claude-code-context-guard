# Changelog

## 0.1.1

- Add persistent `/rename` patch to the startup guard and validator.
- Harden context-error rollback scanner to avoid disabling 1.4M from conversation text that merely mentions `prompt_too_long` or `API 413`.

## 0.1.0

- Initial export of Claude Code context guard scripts.
- Startup ensure for `opus[1m]`, auto permissions, cc-switch repair, virtual 1.4M, and fallback.
- `ccrun` captured-output wrapper.
- Three-layer memory policy templates.
