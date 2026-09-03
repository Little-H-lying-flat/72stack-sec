$ErrorActionPreference = "Stop"
try { $null = [Console]::In.ReadToEnd() } catch {}

$marker = Join-Path $env:USERPROFILE ".agents\.dig_active"
if (Test-Path $marker) {
  $ageH = ((Get-Date) - (Get-Item $marker).LastWriteTime).TotalHours
  if ($ageH -le 24) {
    $root = (Get-Content -LiteralPath $marker -Raw -Encoding UTF8).Trim()
    $obj = @{
      decision = "block"
      reason = "挖洞任务进行中(任务根: $root)。读 资产/种子队列.md(含补记),取下一条 pending 继续;全部收口、或用户已明确叫停时,删除标记文件 $marker 后即可停工。"
    }
    [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false
    Write-Output ($obj | ConvertTo-Json -Compress)
  }
}
exit 0
