# Current Task Handoff

This file is for cross-session task continuity. Update when a task spans compaction or multiple sessions.

## Current Goal

Improve Claude Code global context behavior: default 1M/virtual window, better compact memory, output admission, skill on-demand loading, and startup-time policy repair.

## Current Status

Initialized global context policy structure.

## Next Smallest Action

Run `python %USERPROFILE%\.claude\scripts\ensure-claude-context-policy.py` and start Claude through the wrapper.
