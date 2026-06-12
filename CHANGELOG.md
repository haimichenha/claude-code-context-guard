
## 2026-06-12

- Added native-binary compatibility detection for Claude Code installs that ship `bin/claude.exe` without root `cli.js`.
- Changed validators to skip bundle-only checks on native-binary installs instead of crashing on a missing `cli.js`.
- Documented which guard features still work in native-binary mode and which require a JavaScript `cli.js` bundle.
- Changed the active managed context window target to 1.2M while keeping context-error fallback at safe 1M.
- Changed the startup guard target model default from `opus[1m]` to `opus` and made validation read the target from state.

## 2026-06-03

- Added live transcript monitor patch scripts.
- Added `install.ps1 -NoLiveMonitorPatch` to opt out of the live `Ctrl+O` transcript patch.
- Documented manual live monitor install/validation and backup behavior.

## 2026-06-01

- Added optional AS-aware compact template for `all-search-stack` workflows.
- Added `install.ps1 -AsAwareCompact` to install the AS-aware template as the active Claude compact handoff.

# Changelog

## 0.1.3

- Treat routed `gpt-5.5` sessions as 1M-capable in local Claude Code context accounting without changing the API model string.

## 0.1.2

- Raise ordinary non-`[1m]` fallback context window from 200K to 300K, making 72% auto-compact trigger around 201.6K.

## 0.1.1

- Add persistent `/rename` patch to the startup guard and validator.
- Harden context-error rollback scanner to avoid disabling 1.4M from conversation text that merely mentions `prompt_too_long` or `API 413`.

## 0.1.0

- Initial export of Claude Code context guard scripts.
- Startup ensure for `opus[1m]`, auto permissions, cc-switch repair, virtual 1.4M, and fallback.
- `ccrun` captured-output wrapper.
- Three-layer memory policy templates.
