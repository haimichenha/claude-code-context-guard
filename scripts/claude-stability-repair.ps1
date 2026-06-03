param(
  [switch]$Quiet,
  [switch]$KillOrphans
)

$ErrorActionPreference = 'SilentlyContinue'
$HomeDir = [Environment]::GetFolderPath('UserProfile')
$SettingsJson = Join-Path $HomeDir '.claude\settings.json'
$StateJson = Join-Path $HomeDir '.claude\context-policy-state.json'
$EnvPs1 = Join-Path $HomeDir '.claude\scripts\context-policy-env.ps1'
$EnvCmd = Join-Path $HomeDir '.claude\scripts\context-policy-env.cmd'
$Window = 800000
$changed = @()

function Read-Json($path) {
  if (-not (Test-Path $path)) { return $null }
  try { return Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json -Depth 100 } catch { return $null }
}
function Write-Json($path, $obj) {
  $obj | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $path -Encoding UTF8
}
function Test-ProcessAlive($processId) {
  if (-not $processId -or $processId -le 0) { return $false }
  return [bool](Get-CimInstance Win32_Process -Filter "ProcessId=$processId")
}

# 保持 800000 上下文，不降低体验。
$settings = Read-Json $SettingsJson
if ($settings) {
  if ($settings.autoCompactWindow -ne $Window) {
    $settings | Add-Member -NotePropertyName autoCompactWindow -NotePropertyValue $Window -Force
    Write-Json $SettingsJson $settings
    $changed += "settings.autoCompactWindow=$Window"
  }
}
$state = Read-Json $StateJson
if ($state) {
  if ($state.virtual_context_window -ne $Window) {
    $state | Add-Member -NotePropertyName virtual_context_window -NotePropertyValue $Window -Force
    Write-Json $StateJson $state
    $changed += "state.virtual_context_window=$Window"
  }
}
"`$env:CLAUDE_CODE_AUTO_COMPACT_WINDOW='$Window'`nRemove-Item Env:CLAUDE_AUTOCOMPACT_PCT_OVERRIDE -ErrorAction SilentlyContinue`n" | Set-Content -LiteralPath $EnvPs1 -Encoding UTF8
"@echo off`r`nset CLAUDE_CODE_AUTO_COMPACT_WINDOW=$Window`r`nset CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=`r`n" | Set-Content -LiteralPath $EnvCmd -Encoding ASCII

if ($KillOrphans) {
  # 1) 清理已经禁用的重型 MCP。
  $heavyPattern = '@flowy11\\imagician|mcp-image-optimizer|@sylphx\\pdf-reader-mcp|google-ai-mode-mcp|mcp-server-git'
  $heavy = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine -match $heavyPattern }
  foreach ($p in $heavy) {
    try { Stop-Process -Id $p.ProcessId -Force; $changed += "killed stale heavy MCP pid=$($p.ProcessId)" } catch {}
  }

  # 2) 清理父进程不存在的孤儿 MCP；不碰有活父进程的当前 Claude 子进程。
  $mcpPattern = 'grok-search|GrokSearch|wechat_search|search_stack_orchestrator|as_state|mcp-server|mcp_image|image-optimizer|pdf-reader|imagician|google-ai-mode'
  $mcp = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine -match $mcpPattern }
  foreach ($p in $mcp) {
    if (-not (Test-ProcessAlive $p.ParentProcessId)) {
      try { Stop-Process -Id $p.ProcessId -Force; $changed += "killed orphan MCP pid=$($p.ProcessId)" } catch {}
    }
  }
}

if (-not $Quiet) {
  if ($changed.Count) { $changed | ForEach-Object { Write-Host "[claude-stability] $_" } }
  else { Write-Host "[claude-stability] ok" }
}

