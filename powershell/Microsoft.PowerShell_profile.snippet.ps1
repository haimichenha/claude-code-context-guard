# CLAUDE_CONTEXT_POLICY_WRAPPER_START
function Invoke-ClaudeContextPolicyEnsure {
    $script = Join-Path $env:USERPROFILE '.claude\scripts\ensure-claude-context-policy.py'
    if (Test-Path $script) { python $script --quiet }
    $envScript = Join-Path $env:USERPROFILE '.claude\scripts\context-policy-env.ps1'
    if (Test-Path $envScript) { . $envScript }
}
function Invoke-ClaudeContextPolicyPostCheck {
    $script = Join-Path $env:USERPROFILE '.claude\scripts\check-claude-context-errors.py'
    if (Test-Path $script) { python $script | Out-Null }
}
function claude {
    Invoke-ClaudeContextPolicyEnsure
    $claudeCmd = Join-Path $env:APPDATA 'npm\claude.cmd'
    $claudeArgs = @($args)
    if ($claudeArgs.Count -gt 0 -and $claudeArgs[0] -eq 'code') {
        if ($claudeArgs.Count -gt 1) { $claudeArgs = $claudeArgs[1..($claudeArgs.Count - 1)] } else { $claudeArgs = @() }
    }
    $hasPermissionMode = $claudeArgs -contains '--permission-mode'
    $hasDangerousSkip = $claudeArgs -contains '--dangerously-skip-permissions'
    $hasAllowDangerous = $claudeArgs -contains '--allow-dangerously-skip-permissions'
    if ($hasPermissionMode -or $hasDangerousSkip -or $hasAllowDangerous) { & $claudeCmd @claudeArgs } else { & $claudeCmd --permission-mode auto @claudeArgs }
    $code = $LASTEXITCODE
    Invoke-ClaudeContextPolicyPostCheck
    exit $code
}
function claude-c {
    Invoke-ClaudeContextPolicyEnsure
    $claudeCmd = Join-Path $env:APPDATA 'npm\claude.cmd'
    $claudeArgs = @('-c') + @($args)
    if ($claudeArgs -contains '--permission-mode') { & $claudeCmd @claudeArgs } else { & $claudeCmd --permission-mode auto @claudeArgs }
    $code = $LASTEXITCODE
    Invoke-ClaudeContextPolicyPostCheck
    exit $code
}
# CLAUDE_CONTEXT_POLICY_WRAPPER_END

# CCRUN_CONTEXT_CAPTURE_START
function ccrun {
    $script = Join-Path $env:USERPROFILE '.claude\scripts\ccrun.ps1'
    & $script @args
}
# CCRUN_CONTEXT_CAPTURE_END
