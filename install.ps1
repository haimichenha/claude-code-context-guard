param(
  [switch]$NoCliPatch,
  [switch]$AsAwareCompact
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
$claude = Join-Path $env:USERPROFILE '.claude'
$scripts = Join-Path $claude 'scripts'
$handoff = Join-Path $claude 'persistent-handoff'
New-Item -ItemType Directory -Force -Path $scripts,$handoff | Out-Null
Copy-Item -Force (Join-Path $repo 'scripts\ensure-claude-context-policy.py') (Join-Path $scripts 'ensure-claude-context-policy.py')
Copy-Item -Force (Join-Path $repo 'scripts\check-claude-context-errors.py') (Join-Path $scripts 'check-claude-context-errors.py')
Copy-Item -Force (Join-Path $repo 'scripts\validate-claude-context-policy.py') (Join-Path $scripts 'validate-claude-context-policy.py')
Copy-Item -Force (Join-Path $repo 'scripts\ccrun.ps1') (Join-Path $scripts 'ccrun.ps1')
Copy-Item -Force (Join-Path $repo 'persistent-handoff\global-context-policy.md') (Join-Path $handoff 'global-context-policy.md')
$compactTemplate = if ($AsAwareCompact) { Join-Path $repo 'persistent-handoff\compact-template.as.md' } else { Join-Path $repo 'persistent-handoff\compact-template.md' }
Copy-Item -Force $compactTemplate (Join-Path $handoff 'compact-template.md')
if (Test-Path (Join-Path $repo 'persistent-handoff\compact-template.as.md')) {
  Copy-Item -Force (Join-Path $repo 'persistent-handoff\compact-template.as.md') (Join-Path $handoff 'compact-template.as.md')
}
Copy-Item -Force (Join-Path $repo 'persistent-handoff\verified-facts.md') (Join-Path $handoff 'verified-facts.md')
if (!(Test-Path (Join-Path $handoff 'current-task-handoff.md'))) {
  Copy-Item -Force (Join-Path $repo 'persistent-handoff\current-task-handoff.example.md') (Join-Path $handoff 'current-task-handoff.md')
}
$npm = Join-Path $env:APPDATA 'npm'
New-Item -ItemType Directory -Force -Path $npm | Out-Null
Copy-Item -Force (Join-Path $repo 'wrappers\claude-c.cmd') (Join-Path $npm 'claude-c.cmd')
Copy-Item -Force (Join-Path $repo 'wrappers\claude-c.ps1') (Join-Path $npm 'claude-c.ps1')
Copy-Item -Force (Join-Path $repo 'wrappers\ccrun.cmd') (Join-Path $npm 'ccrun.cmd')
Copy-Item -Force (Join-Path $repo 'wrappers\ccrun.ps1') (Join-Path $npm 'ccrun.ps1')
$bin = Join-Path $env:USERPROFILE 'bin'
New-Item -ItemType Directory -Force -Path $bin | Out-Null
Copy-Item -Force (Join-Path $repo 'wrappers\ccrun.cmd') (Join-Path $bin 'ccrun.cmd')
Copy-Item -Force (Join-Path $repo 'wrappers\ccrun.ps1') (Join-Path $bin 'ccrun.ps1')
$profile = $PROFILE.CurrentUserCurrentHost
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $profile) | Out-Null
$snippet = Get-Content -Raw (Join-Path $repo 'powershell\Microsoft.PowerShell_profile.snippet.ps1')
$existing = if (Test-Path $profile) { Get-Content -Raw $profile } else { '' }
foreach($pair in @(@('CLAUDE_CONTEXT_POLICY_WRAPPER_START','CLAUDE_CONTEXT_POLICY_WRAPPER_END'),@('CCRUN_CONTEXT_CAPTURE_START','CCRUN_CONTEXT_CAPTURE_END'))){
  $start = '# ' + $pair[0]; $end = '# ' + $pair[1]
  if ($snippet.Contains($start) -and $snippet.Contains($end)) {
    $block = $start + $snippet.Split($start,2)[1].Split($end,2)[0] + $end
    if ($existing.Contains($start) -and $existing.Contains($end)) {
      $existing = $existing.Split($start,2)[0] + $block + $existing.Split($end,2)[1]
    } else {
      $existing = $existing.TrimEnd() + "`n`n" + $block + "`n"
    }
  }
}
Set-Content -Encoding UTF8 -Path $profile -Value $existing
$ensureArgs = @()
if ($NoCliPatch) { $ensureArgs += '--no-cli-patch' }
python (Join-Path $scripts 'ensure-claude-context-policy.py') @ensureArgs
Write-Host 'Install complete. Open a new PowerShell window, then run: claude or claude-c'
