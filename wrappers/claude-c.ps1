#!/usr/bin/env pwsh
$script = Join-Path $env:USERPROFILE '.claude\scripts\ensure-claude-context-policy.py'
if (Test-Path $script) { python $script --quiet }
$env:CLAUDE_AUTOCOMPACT_PCT_OVERRIDE = '72'
$env:CLAUDE_CODE_AUTO_COMPACT_WINDOW = '1400000'
& (Join-Path $env:APPDATA 'npm\claude.cmd') --permission-mode auto -c @args
exit $LASTEXITCODE
