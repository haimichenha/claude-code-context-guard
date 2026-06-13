# CLAUDE_CONTEXT_POLICY_WRAPPER_START
function Invoke-ClaudeContextPolicyEnsure {
    $script = Join-Path $env:USERPROFILE '.claude\scripts\ensure-claude-context-policy.py'
    if (Test-Path $script) { python $script --quiet --no-cli-patch }
    $envScript = Join-Path $env:USERPROFILE '.claude\scripts\context-policy-env.ps1'
    if (Test-Path $envScript) { . $envScript }
    $stabilityScript = Join-Path $env:USERPROFILE '.claude\scripts\claude-stability-repair.ps1'
    if (Test-Path $stabilityScript) { & $stabilityScript -Quiet }
}
function Invoke-ClaudeContextPolicyPostCheck {
    $script = Join-Path $env:USERPROFILE '.claude\scripts\check-claude-context-errors.py'
    if (Test-Path $script) { python $script | Out-Null }
}
function claude {
    $dispatch = Join-Path $env:USERPROFILE '.claude\scripts\claude-dispatch.ps1'
    & $dispatch @args
    exit $LASTEXITCODE
}
function claude-c {
    $dispatch = Join-Path $env:USERPROFILE '.claude\scripts\claude-dispatch.ps1'
    & $dispatch -c @args
    exit $LASTEXITCODE
}
# CLAUDE_CONTEXT_POLICY_WRAPPER_END

# CCRUN_CONTEXT_CAPTURE_START
function ccrun {
    $script = Join-Path $env:USERPROFILE '.claude\scripts\ccrun.ps1'
    & $script @args
}
# CCRUN_CONTEXT_CAPTURE_END

