$ErrorActionPreference = "Stop"
try { $null = [Console]::In.ReadToEnd() } catch {}

$dir = Join-Path $env:USERPROFILE ".agents\.dig_active"
if (Test-Path $dir) {
  $now = Get-Date
  $flags = @(Get-ChildItem -LiteralPath $dir -Filter *.flag -ErrorAction SilentlyContinue |
    Where-Object { ($now - $_.LastWriteTime).TotalHours -le 24 })
  if ($flags.Count -gt 0) {
    $roots = ($flags | ForEach-Object { (Get-Content -LiteralPath $_.FullName -Raw -Encoding UTF8).Trim() }) -join "  |  "
    $obj = @{
      decision = "block"
      reason = "有挖洞任务进行中(任务根: $roots)。若其中之一是本会话正在挖的目标,读该任务根下 资产/种子队列.md(含补记),取下一条 pending 继续,收口时删除自己在 .dig_active 目录里对应的 .flag;若都不是本会话的任务,直接停工,不要动任何 .flag。flag 超 24 小时自动失效。"
    }
    [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false
    Write-Output ($obj | ConvertTo-Json -Compress)
  }
}
exit 0
