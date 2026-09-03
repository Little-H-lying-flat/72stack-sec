# wxmini-security-audit v2（MCP 整合版）

微信小程序全自动安全审计 skill。移植自 [sssmmmwww/wxmini-security-audit](https://github.com/sssmmmwww/wxmini-security-audit)（v1.0.0，MIT），针对本机 ZCode 环境与 `first-miniapp-debugger` MCP 做了整合优化。

## 相对上游的改动（v1 → v2）

| 改动 | 说明 |
|------|------|
| **供包 MCP 优先** | Phase 1 优先走 `first-miniapp-debugger`（SSE `127.0.0.1:4554/sse`）的 `miniapp_list_packages` → `miniapp_decompile` 直接从本机微信拉包；unveilr.exe 降为兜底（本机未内置，需自置于 `tools\`）。用户只给 appid 不给目录时自动 `USE_MCP` 模式 |
| **坑位写死** | First.exe 引擎仅支持微信 PC ≤3.9.x；`get_info` 失败 ≠ MCP 不可用，静态拉包链不依赖 engine |
| **双源预扫** | Phase 1.5 在上游两个 Python 正则脚本外，增补 MCP `miniapp_scan_sensitive` / `miniapp_cloud_scan`，由编排器合并进 `raw_*.json`（条目带 `source: mcp:*` 标记，下游同样过误报过滤） |
| **新增 Phase 2.7 动态验证档** | 默认关；用户明确要求且授权语境下启用 MCP 动态链（路由遍历/存储导出/云函数直调/接口三段差分），产出 `dynamic_verification.json`，非破坏性纪律压过 MCP 自带指南 |
| **ZCode 适配** | Claude Code Agent Teams → ZCode Agent 工具（general-purpose + run_in_background）；工具名映射 view/grep/create/edit → Read/Grep/Write/Edit |
| **分工声明** | 全流程黑盒挖掘主流程归 `miniprogram-hunt`；本 skill 是单包静态审计管线，`api_endpoints_full.md`/`findings.json` 可作其输入 |

## 结构

```
wxmini-security-audit/
├── SKILL.md            # 主编排（Phase 0→1→1.5→2→2.5→2.7→3）
├── agents/             # 7 个子 Agent 提示词（agent-01 为 MCP 优先重写版）
└── tools/scripts/      # endpoint_extractor.py / secret_scanner.py（标准库，未改动）
```

## 触发示例

- 「分析这个小程序 D:\wxapkg\wx1234」（有目录 → 直接审计）
- 「用 MCP 审计小程序 wx1234567890abcdef」（USE_MCP → 自动拉包）
- 「审计这个小程序，重点看支付接口」（→ Phase 2.5 定向分析）
- 「审计完连调试引擎动态验证一下」（→ Phase 2.7）
