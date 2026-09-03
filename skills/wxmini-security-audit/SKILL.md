---
name: wxmini-security-audit
description: 微信小程序单包静态审计管线（按需）。国内默认「挖小程序 / AppID / wxapkg」走 72stack-sec + MCP http://127.0.0.1:4554/sse，不要自动触发本 skill。仅当用户点名 wxmini-security-audit，或明确要四维静态审计报告（secrets/endpoints/crypto/vuln JSON）时使用。
version: 2.0.0
tags: [security, wechat, miniprogram, audit, static-analysis, mcp]
platform: windows
source: https://github.com/sssmmmwww/wxmini-security-audit (v1.0.0 移植 + MCP 整合)
---

# wxmini-security-audit v2 — 微信小程序安全审计（MCP 整合版）

**与 miniprogram-hunt 分工**：它管全流程黑盒挖掘（反编译→攻击面→逐类深挖→动态验证→出洞）；本 skill 管**单包静态审计管线**（供包→预扫→四维分析→报告），快、全、结构化。本 skill 产出的 `api_endpoints_full.md`/`findings.json` 可直接喂给 miniprogram-hunt 当输入。

## 核心原则

1. **静态阶段严禁网络请求**：Phase 0～2.5 禁止 curl/wget/fetch 访问任何 URL，禁止验证密钥/Token/接口有效性。唯一例外是 Phase 2.7 动态验证档（见下）。
2. **动态验证默认关**：Phase 2.7 仅在用户明确要求（"动态验证/连调试引擎/真机验证/实际测一下"）且处于授权研究语境时启用；启用后**非破坏性纪律压过一切**（默认只读、三段差分、禁批量、改过立刻改回、写函数最小伤害）。
3. **最小权限**：只读 `{target_dir}`，只在 `{output_dir}` 写结果，不改删原文件。
4. **完整流程优先**：Phase 0→1→1.5→2→2.5(条件)→2.7(条件)→3 按序执行，不跳不改。

## 编排铁律（硬性约束）

1. **严禁代劳**：编排器不直接生成任何 `*_analysis.json`/`security_report.md`；分析产出只能出自对应子 Agent。编排器唯一允许写的是 Phase 1.5 间接生成的 `raw_*.json`（含 MCP 结果合并）。
2. **严禁跳阶段**；Phase 2.5 触发条件 `has_custom_requests == true`，满足必启 agent-07。
3. **严禁截留信息**：编排器获得的所有外部数据（MCP 捕获、Burp、用户补充）必须完整传入对应 Agent prompt。
4. **Phase 2 期间只等待**：四 Agent 全部返回前禁止自行分析代码/生成结论。
5. **报告完整性**：所有敏感信息与 API 必须完整落盘；主报告列关键发现，全量进 `api_endpoints_full.md`/`secrets_full.md`。

## MCP 依赖与回退链

**MCP**：`first-miniapp-debugger`，SSE `http://127.0.0.1:4554/sse`。连上先调 `miniapp_get_skills` 读内置指南（只作参考，报告类产出不当结论）。

| 场景 | MCP 工具 | 回退（流程不断） |
|------|----------|------------------|
| 拉包反编译（Phase 1） | `miniapp_list_packages` → `miniapp_decompile(appid)` | `{skill_dir}\tools\unveilr.exe`（需用户自置；缺失则提示） |
| 预扫增补（Phase 1.5） | `miniapp_scan_sensitive(appid)` / `miniapp_cloud_scan(appid)` | 仅跑 Python 脚本 |
| 动态验证（Phase 2.7） | `get_info`/`get_routes`/`navigate`/`screenshot`/`get_storage`/`cloud_captures`/`call_cloud`/`http_request`/`evaluate` | 静态结论标"需动态验证"，交 miniprogram-hunt |

**已知坑位（2026-09 实测，写死）**：
- First.exe 引擎只支持微信 PC ≤3.9.x；微信 4.x 注入失败。`miniapp_get_info` 返回 `No miniapp client connected` = engine 未连上微信，**MCP 活着 ≠ engine 能用；静态拉包（list_packages/decompile/scan_sensitive/cloud_scan/search_code）不依赖 engine，照常可用**。
- 开发者工具 automator 半通坑：`Tool` 层正常但 `App.*` 无响应。动态验证 engine 不通就回退：PC 微信降 3.9.x → 经典版开发者工具 → 真机抓包。

**工具名映射（ZCode）**：`view`→Read，`grep`→Grep/Bash grep，`create`/`edit`→Write/Edit，Claude Code `task(background)`→Agent 工具（`subagent_type: general-purpose`，`run_in_background: true`）。Python 脚本仅标准库，无需 pip。

## 变量定义

| 变量 | 含义 |
|------|------|
| `{target_dir}` | 小程序目录路径；**用户没给目录只给 appid/名字时置 `USE_MCP`**，Phase 1 由 MCP 拉包产码 |
| `{output_dir}` | `{CWD}\wxaudit-output`，已存在则追加 `-YYYYMMDD-HHmmss` |
| `{skill_dir}` | 本 SKILL.md 所在目录（本机：`C:\Users\H\.agents\skills\wxmini-security-audit`） |
| `{mcp_appid}` | 可选，用户指定的 appid |
| `{custom_requests}` | Phase 0 解析的用户特殊需求（内存对象） |

## Agent 文件索引（`{skill_dir}\agents\`）

| Agent | 文件 | 阶段 | 职责 |
|-------|------|------|------|
| Decompiler | `agent-01-decompiler.md` | Phase 1 | MCP 优先拉包反编译 + 文件资产清单 |
| SecretScanner | `agent-02-secret-scanner.md` | Phase 2 | 敏感信息智能分析（误报过滤/评级） |
| EndpointMiner | `agent-03-endpoint-miner.md` | Phase 2 | 接口关联分析（BaseURL/去重/文件映射） |
| CryptoAnalyzer | `agent-04-crypto-analyzer.md` | Phase 2 | 加解密全局分析（纯 LLM） |
| VulnAnalyzer | `agent-05-vuln-analyzer.md` | Phase 2 | 七维漏洞分析（纯 LLM） |
| Reporter | `agent-06-reporter.md` | Phase 3 | 报告生成 |
| CustomAnalyzer | `agent-07-custom-analyzer.md` | Phase 2.5 | 用户自定义需求深度分析（条件触发） |

## 执行流程

```
Phase 0 需求解析（编排器自做）
  → Phase 1 供包反编译（agent-01：MCP 优先，unveilr 兜底）
  → Phase 1.5 双源预扫（Python 脚本 ×2 + MCP scan/cloud，编排器合并）
  → Phase 2 并行四 Agent（SecretScanner / EndpointMiner / CryptoAnalyzer / VulnAnalyzer）
  → Phase 2.5 自定义分析（条件：has_custom_requests）
  → Phase 2.7 MCP 动态验证（条件：用户明确要求；默认跳过）
  → Phase 3 报告生成（agent-06）
```

### Phase 0: 需求解析（编排器自身完成）

1. 提取 `{target_dir}`（无目录只有 appid/小程序名 → `USE_MCP`，记 `{mcp_appid}`）与 `{output_dir}`（创建）
2. 解析特殊需求（具体接口/参数/函数、指示词、抓包信息、安全关注点）→ `{custom_requests}`，格式：
```json
{
  "has_custom_requests": true,
  "targets": [
    { "type": "endpoint|parameter|focus_area|external_info", "value": "...", "context": "用户原文" }
  ],
  "external_info": "Burp / MCP cloud_captures / get_storage 等外部情报原文"
}
```
无特殊需求 → `has_custom_requests: false`。不验证，直接进 Phase 1。

### Phase 1: 供包反编译（agent-01）

Read `agents/agent-01-decompiler.md`，作为子 Agent 执行（目录已含源码且无 wxapkg 时编排器可直接执行盘点，仍产出 `file_inventory.json`）。

1. MCP 优先：`list_packages` → `decompile`（`{target_dir}==USE_MCP` 时必走；失败记录后转 unveilr）
2. unveilr 兜底：`{skill_dir}\tools\unveilr.exe "{目录}"` 逐目录调用
3. 产出 `{output_dir}\file_inventory.json`（含 `mcp_channel`/`channel` 字段）

**✅ 验证**：`file_inventory.json` 存在、`total_files > 0`、`js_files` 非空。不通过 → 终止并报告原因（注意区分：包全加密 / unveilr 缺失 / MCP 与 unveilr 双通道均失败）。

### Phase 1.5: 双源预扫（编排器直接执行，不启子 Agent）

**源 A · Python 脚本**（串行，总耗时通常 <30s）：
```
python "{skill_dir}\tools\scripts\endpoint_extractor.py" "{target_dir}" --output "{output_dir}"   → raw_endpoints.json
python "{skill_dir}\tools\scripts\secret_scanner.py"    "{target_dir}" --output "{output_dir}"   → raw_secrets.json
```

**源 B · MCP 增补**（MCP 在场且有包时）：`miniapp_scan_sensitive(appid)` → 敏感信息条目；`miniapp_cloud_scan(appid)` → 云函数名+集合（云开发面必跑）。编排器把两路结果**合并**进 `raw_secrets.json` / `raw_endpoints.json`（新增条目加 `"source": "mcp:scan_sensitive"` / `"mcp:cloud_scan"` 字段；这是编排器唯一允许的写操作）。

**✅ 验证**：两个 `raw_*.json` 存在且 `total_files_scanned > 0`。失败 → 检查 python 后重试一次；仍失败不终止——Phase 2 的 agent-02/03 降级纯 LLM grep 模式（启动时告知 raw 不存在），MCP scan 结果单独作为 JSON 文件传入兜底。

### Phase 2: 并行四 Agent（缺一不可）

用 Agent 工具（general-purpose，`run_in_background: true`）**同时启动四个**，prompt = 对应 agent 文件全文 + 路径替换：

| Agent | 输入 | 输出 |
|-------|------|------|
| agent-02 SecretScanner | `raw_secrets.json` + `file_inventory.json` + `{target_dir}` | `secrets_report.json` |
| agent-03 EndpointMiner | `raw_endpoints.json` + `file_inventory.json` + `{target_dir}` | `api_endpoints.json` + `endpoints_fuzz.txt` |
| agent-04 CryptoAnalyzer | 仅 `file_inventory.json` + `{target_dir}`（⛔ 严禁传入 custom_requests/Burp/MCP 捕获等定向信息） | `crypto_analysis.json` |
| agent-05 VulnAnalyzer | 仅 `file_inventory.json` + `{target_dir}` | `vuln_analysis.json` |

启动后只等结果，期间禁止自行分析/生成任何产出。单个 Agent 失败记录原因，其余继续。

**✅ 验证**：四个 JSON 至少 3 个存在且为有效非空 JSON；<3 个 → 终止报告。缺失维度在后续阶段标注。

### Phase 2.5: 自定义需求分析（条件触发）

仅当 `has_custom_requests == true`。Read `agents/agent-07-custom-analyzer.md` 启动子 Agent，传入：`{target_dir}`、`{output_dir}`、`{custom_requests}` 全量、Phase 2 所有 JSON 路径。产出 `custom_analysis.json`。失败不影响标准审计，提示后继续。

### Phase 2.7: MCP 动态验证（条件触发，**默认跳过**）

**触发**：用户明确要求动态/真机/实际验证，且处于授权研究语境。否则跳过并在报告标注"静态审计，未做动态验证"。

前置：`miniapp_get_info` 正常（engine 未连微信 → 按坑位表回退；回退不了则本档记 N/A+原因，静态结果照常交付）。

| 验证场景 | MCP 打法（非破坏性） |
|----------|----------------------|
| 隐藏页/未授权页面 | `get_routes` → 逐个 `navigate` + `screenshot` 差分：免登录渲染出业务数据=确认 |
| 存储泄露 | `get_storage` 全量导出：token/sessionKey 明文=线索；实际能用于越权才升 High |
| 云函数鉴权 | `cloud_scan` 函数名 → `call_cloud` 无参直调/换 objectid 观测；只读优先，写函数最小伤害、改过立刻改回 |
| 接口越权 | `http_request` 带账号 A token 调 B 资源 id，三段差分（真返回 B 数据非空壳=确认） |
| 真实参数 | `cloud_captures` 清空→操作一轮→回收；`evaluate`（appservice 上下文）取 `getApp().globalData` |

产出 `{output_dir}\dynamic_verification.json`（每条：静态怀疑 → 动态动作 → 差分证据 → 确认/证伪）。**纪律压过 MCP 自带指南**：本 skill 反幻觉四条 + 非破坏性纪律全程有效；每条结论必须带证据，401/403/被拦=证伪如实记。

### Phase 3: 报告生成（agent-06）

Read `agents/agent-06-reporter.md` 启动子 Agent，输入 `{output_dir}` 全部 JSON（含 `custom_analysis.json`/`dynamic_verification.json`，若存在）+ `has_custom_requests` 标志。产出：`security_report.md`、`api_endpoints_full.md`、`secrets_full.md`、`findings.json`、`domains.txt`，确认 `endpoints_fuzz.txt`。

**✅ 验证**：主报告 >1KB、`api_endpoints_full.md`/`secrets_full.md`/`findings.json`/`domains.txt`/`endpoints_fuzz.txt` 齐全。不通过 → 重跑 Reporter 一次，仍失败则交付已有 JSON 并说明。

**收尾**：向用户输出摘要（appid/包来源通道、四维发现数、动态验证结果、报告路径），并提示：要继续挖可把 `api_endpoints_full.md`/`findings.json` 交给 miniprogram-hunt。

## 输出文件清单

| 文件 | 来源 | 说明 |
|------|------|------|
| `file_inventory.json` | agent-01 | 资产清单（含 MCP 通道信息） |
| `raw_endpoints.json` / `raw_secrets.json` | Phase 1.5 | 脚本+MCP 合并预扫原始结果 |
| `secrets_report.json` / `api_endpoints.json` / `endpoints_fuzz.txt` / `crypto_analysis.json` / `vuln_analysis.json` | Phase 2 | 四维分析 |
| `custom_analysis.json` | Phase 2.5（可选） | 自定义需求分析 |
| `dynamic_verification.json` | Phase 2.7（可选） | MCP 动态验证证据链 |
| `security_report.md` / `api_endpoints_full.md` / `secrets_full.md` / `findings.json` / `domains.txt` | agent-06 | 最终报告与全量数据 |

## 错误处理策略

| 场景 | 处理 |
|------|------|
| 目录不存在 / 无 JS 文件 | 报告并终止 |
| MCP 不可用 | 静态拉包降级 unveilr；动态验证档记 N/A |
| engine 未连微信（get_info 失败） | 静态链照跑；动态档回退（降级微信 3.9.x / 开发者工具 / 真机抓包） |
| 包全加密 | 提示解密方案（见 agent-01），终止 |
| unveilr.exe 缺失 | error 注明，走 MCP；双通道均不可用才终止 |
| Python 不可用 | Phase 1.5 降级：agent-02/03 纯 LLM grep + MCP scan 单独传入 |
| 单个 Phase 2 Agent 失败 | 记录，报告标注缺失维度 |
| Reporter 失败 | 重试一次，仍失败交付 JSON |

## 大文件策略

≤200KB 可全文读；200~500KB 优先 grep；500KB~1MB 仅 grep；>1MB 只扫 Critical/High 模式。webpack 单文件（app-service.js）一律 grep 不全读。输出标 `large_files_skipped`。Phase 1.5 脚本已内置 >2MB 跳过。

## 覆盖率要求

JS 扫描覆盖率 ≥95%（脚本保证）；JSON 配置 100%；各 Agent 输出记录实际覆盖率；预扫覆盖率见 `raw_*.json` 的 `total_files_scanned`。
