$ErrorActionPreference = 'Continue'

function Invoke-QuietPython($ScriptPath, [string[]]$ArgsList) {
  if (Test-Path -LiteralPath $ScriptPath) {
    python $ScriptPath @ArgsList *> $null
  }
}

function Get-ClaudeProjectNameCandidates($Path) {
  $full = [System.IO.Path]::GetFullPath($Path).TrimEnd('\', '/')
  if ($full -match '^([A-Za-z]):[\\/](.*)$') {
    $drive = $matches[1]
    $rest = $matches[2]
    $safeRest = ($rest -replace '[\\/:\s]+', '-')
    $safeRest = ($safeRest -replace '[^A-Za-z0-9._-]+', '-').Trim('-')
    $drives = @($drive, $drive.ToUpperInvariant(), $drive.ToLowerInvariant()) | Select-Object -Unique
    foreach ($d in $drives) {
      if ($safeRest) { "$d--$safeRest" } else { "$d--" }
    }
    return
  }
  ($full -replace '[\\/:\s]+', '-' -replace '[^A-Za-z0-9._-]+', '-').Trim('-')
}

function Get-LatestSessionInDirectory($Directory) {
  if (-not (Test-Path -LiteralPath $Directory)) { return $null }
  Get-ChildItem -LiteralPath $Directory -Filter '*.jsonl' -File -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
}

function Resolve-ClaudeContinueArgs([string[]]$ArgsList) {
  if (-not $ArgsList) { return @() }
  if ($ArgsList -contains '-h' -or $ArgsList -contains '--help') { return @($ArgsList) }
  if ($ArgsList -contains '-r' -or $ArgsList -contains '--resume') { return @($ArgsList) }

  $continueIndex = -1
  for ($i = 0; $i -lt $ArgsList.Count; $i++) {
    if ($ArgsList[$i] -eq '-c' -or $ArgsList[$i] -eq '--continue') {
      $continueIndex = $i
      break
    }
  }
  if ($continueIndex -lt 0) { return @($ArgsList) }

  $projectsRoot = Join-Path $env:USERPROFILE '.claude\projects'
  if (-not (Test-Path -LiteralPath $projectsRoot)) { return @($ArgsList) }

  $projectNames = @(Get-ClaudeProjectNameCandidates (Get-Location).ProviderPath)
  foreach ($name in $projectNames) {
    $currentSession = Get-LatestSessionInDirectory (Join-Path $projectsRoot $name)
    if ($currentSession) { return @($ArgsList) }
  }

  $prefixMatches = @()
  foreach ($name in $projectNames) {
    $prefixMatches += Get-ChildItem -LiteralPath $projectsRoot -Directory -ErrorAction SilentlyContinue |
      Where-Object { $_.Name -ieq $name -or $_.Name -ilike "$name-*" } |
      ForEach-Object { Get-LatestSessionInDirectory $_.FullName } |
      Where-Object { $_ }
  }
  $latest = $prefixMatches | Sort-Object LastWriteTime -Descending | Select-Object -First 1

  if (-not $latest) {
    $latest = Get-ChildItem -LiteralPath $projectsRoot -Directory -ErrorAction SilentlyContinue |
      ForEach-Object { Get-LatestSessionInDirectory $_.FullName } |
      Where-Object { $_ } |
      Sort-Object LastWriteTime -Descending |
      Select-Object -First 1
  }
  if (-not $latest) { return @($ArgsList) }

  $resolved = @()
  for ($i = 0; $i -lt $ArgsList.Count; $i++) {
    if ($i -eq $continueIndex) {
      $resolved += '--resume'
      $resolved += [System.IO.Path]::GetFileNameWithoutExtension($latest.Name)
    } else {
      $resolved += $ArgsList[$i]
    }
  }
  return $resolved
}

$ensure = Join-Path $env:USERPROFILE '.claude\scripts\ensure-claude-context-policy.py'
$live = Join-Path $env:USERPROFILE '.claude\scripts\ensure-claude-live-monitor.py'
$envPs1 = Join-Path $env:USERPROFILE '.claude\scripts\context-policy-env.ps1'
$stability = Join-Path $env:USERPROFILE '.claude\scripts\claude-stability-repair.ps1'
$postCheck = Join-Path $env:USERPROFILE '.claude\scripts\check-claude-context-errors.py'
$claudeCmd = Join-Path $env:APPDATA 'npm\claude.cmd'

Invoke-QuietPython $ensure @('--quiet', '--no-cli-patch')
Invoke-QuietPython $live @('--quiet')
if (Test-Path -LiteralPath $envPs1) { . $envPs1 }
if (Test-Path -LiteralPath $stability) { & $stability -Quiet }

$claudeArgs = @($args)
if ($claudeArgs.Count -gt 0 -and $claudeArgs[0] -ieq 'code') {
  if ($claudeArgs.Count -gt 1) { $claudeArgs = @($claudeArgs[1..($claudeArgs.Count - 1)]) } else { $claudeArgs = @() }
}

$claudeArgs = @(Resolve-ClaudeContinueArgs $claudeArgs)

$hasPermissionMode = $claudeArgs -contains '--permission-mode'
$hasDangerousSkip = $claudeArgs -contains '--dangerously-skip-permissions'
$hasAllowDangerous = $claudeArgs -contains '--allow-dangerously-skip-permissions'
if (-not ($hasPermissionMode -or $hasDangerousSkip -or $hasAllowDangerous)) {
  $claudeArgs = @('--permission-mode', 'auto') + $claudeArgs
}

& $claudeCmd @claudeArgs
$code = $LASTEXITCODE
Invoke-QuietPython $postCheck @()
exit $code
