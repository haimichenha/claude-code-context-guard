#!/usr/bin/env pwsh
$script = Join-Path $env:USERPROFILE '.claude\scripts\ccrun.ps1'
& $script @args
exit $LASTEXITCODE
