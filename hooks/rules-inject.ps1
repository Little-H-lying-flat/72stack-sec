$ErrorActionPreference = "Stop"
try { $null = [Console]::In.ReadToEnd() } catch {}

$agents = Join-Path $env:USERPROFILE ".grok\AGENTS.md"
if (-not (Test-Path $agents)) { exit 0 }

$digest = (Get-Content -LiteralPath $agents -Raw -Encoding UTF8).Trim()
$adapt = @"
---
**ZCode 本机适配**（压过上方 Grok 专属条目）：
- 浏览器：control-browser（非 Playwright MCP）；任务根：D:\Desktop\SRC\{任务}_SRC挖洞\（72stack 新线）
- skill 入口：72stack-sec（一句话开工五步）；并行线程子代理：src-thread-digger
- 闸门：开工写 %USERPROFILE%\.agents\.dig_active\<任务根名>.flag；收口删自己的 flag
- rules 全文在 %USERPROFILE%\.grokules\，按需 Read；当次指令压过默认
"@

$obj = @{
  hookSpecificOutput = @{
    hookEventName = "SessionStart"
    additionalContext = ($digest + "`n`n" + $adapt)
  }
}
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false
Write-Output ($obj | ConvertTo-Json -Compress -Depth 6)
exit 0
