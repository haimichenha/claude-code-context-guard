$dispatch = Join-Path $env:USERPROFILE '.claude\scripts\claude-dispatch.ps1'
& $dispatch @args
exit $LASTEXITCODE
