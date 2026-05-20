param(
  [Parameter(ValueFromRemainingArguments=$true)]
  [string[]]$CommandArgs
)

$ErrorActionPreference = 'Continue'
$root = Join-Path (Get-Location) '.claude-output'
$logDir = Join-Path $root 'logs'
$sumDir = Join-Path $root 'summaries'
New-Item -ItemType Directory -Force -Path $logDir,$sumDir | Out-Null
$ts = Get-Date -Format 'yyyyMMdd-HHmmss'
$cmdText = ($CommandArgs -join ' ')
if ([string]::IsNullOrWhiteSpace($cmdText)) {
  Write-Host 'Usage: ccrun <command...>'
  exit 2
}
$safeName = ($cmdText -replace '[^a-zA-Z0-9_.-]+','_')
if ($safeName.Length -gt 60) { $safeName = $safeName.Substring(0,60) }
$logPath = Join-Path $logDir "$ts-$safeName.log"
$summaryPath = Join-Path $sumDir "$ts-$safeName.summary.md"

$start = Get-Date
# Run through PowerShell so pipes/quotes still work when passed as a string.
$output = & powershell -NoProfile -ExecutionPolicy Bypass -Command $cmdText 2>&1
$exit = $LASTEXITCODE
$end = Get-Date
$text = ($output | ForEach-Object { $_.ToString() }) -join [Environment]::NewLine
$text | Set-Content -Encoding UTF8 -Path $logPath
[string[]]$lines = if ($text.Length -eq 0) { @() } else { $text -split "`r?`n" }
$lineCount = $lines.Count
$patterns = 'error|failed|fail|fatal|exception|traceback|undefined reference|cannot find|not found|warning|警告|错误|失败'
$hits = @()
for ($i=0; $i -lt $lines.Count; $i++) {
  if ([regex]::IsMatch([string]$lines[$i], $patterns, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)) { $hits += [pscustomobject]@{Line=$i+1; Text=$lines[$i]} }
}
$head = $lines | Select-Object -First 40
$tail = $lines | Select-Object -Last 80
$key = @($hits | Select-Object -First 30)

$summary = New-Object System.Collections.Generic.List[string]
$summary.Add('# ccrun Output Summary')
$summary.Add('')
$summary.Add("- command: ``$cmdText``")
$summary.Add("- exit_code: $exit")
$summary.Add("- started: $($start.ToString('s'))")
$summary.Add("- duration_seconds: $([math]::Round(($end-$start).TotalSeconds,2))")
$summary.Add("- full_output: ``$logPath``")
$summary.Add("- lines: $lineCount")
$summary.Add('')
$summary.Add('## Key Findings')
if (@($key).Count -eq 0) { $summary.Add('- No obvious error/warning patterns found.') } else { foreach($m in $key){ $summary.Add("- line $($m.Line): $($m.Text)") } }
$summary.Add('')
$summary.Add('## Suggested Ranges')
if (@($key).Count -gt 0) { foreach($m in ($key | Select-Object -First 5)){ $a=[Math]::Max(1,$m.Line-20); $b=[Math]::Min($lineCount,$m.Line+20); $summary.Add("- lines $a-$b around line $($m.Line)") } } else { $summary.Add('- tail lines '+[Math]::Max(1,$lineCount-80)+'-'+$lineCount) }
$summary.Add('')
$summary.Add('## Tail Preview')
$summary.Add('```text')
foreach($l in $tail){ $summary.Add($l) }
$summary.Add('```')
$summary -join [Environment]::NewLine | Set-Content -Encoding UTF8 -Path $summaryPath

# Print concise summary to main context.
Get-Content -Raw $summaryPath
exit $exit






