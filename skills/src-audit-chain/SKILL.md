---
name: src-audit-chain
description: >-
  源码安全审计主流程 skill（代码审计优先）。用于本地/开源 Web 源码的通用漏洞审计：
  鉴权缺失、SSRF、XSS、RCE/间接执行、敏感配置、打后台链路；可选 FOFA 指纹与
  去重案例门槛；输出前强制多视角本地验证。当用户要求源码审计、通用洞判断、
  写 FOFA 语法、打后台链路、验证后汇总、或把审计流程做成 skill 时使用。
---

# SRC-AUDIT-CHAIN

**源码驱动、通用洞优先** 的安全审计流水线。

核心原则：

1. **代码审计是主线**，测绘（FOFA）是辅线。
2. 优先找 **CWE 级通用漏洞**（Auth / SSRF / XSS / RCE / 信息泄露），再谈产品特有逻辑。
3. 结论必须先 **多视角本地验证**，再汇总输出。
4. 不编造 FOFA 数量；精确指纹 0 命中不阻断源码结论。

```
        ┌─────────────────────────────────────────┐
        │  P0 定位源码 / 栈 / 授权范围              │
        └─────────────────┬───────────────────────┘
                          ▼
        ┌─────────────────────────────────────────┐
        │  P1 指纹提取 → FOFA 语法（可选执行查询）  │
        └─────────────────┬───────────────────────┘
                          ▼
        ┌─────────────────────────────────────────┐
        │  P2 暴露面门槛（默认去重≥20，不阻断主线） │
        └─────────────────┬───────────────────────┘
                          ▼
        ┌─────────────────────────────────────────┐
        │  P3 ★ 入口 / 鉴权 / 信任边界（最高优先）  │
        └─────────────────┬───────────────────────┘
                          ▼
        ┌─────────────────────────────────────────┐
        │  P4 ★ 通用洞矩阵 + XSS/RCE/SSRF 打后台   │
        └─────────────────┬───────────────────────┘
                          ▼
        ┌─────────────────────────────────────────┐
        │  P5 ★ 多视角本地验证（输出前强制）        │
        └─────────────────┬───────────────────────┘
                          ▼
        ┌─────────────────────────────────────────┐
        │  P6 汇总报告（Confirmed/Likely/Info）    │
        └─────────────────┬───────────────────────┘
                          ▼
        ┌─────────────────────────────────────────┐
        │  P7 流程反馈写回 skill（可选）            │
        └─────────────────────────────────────────┘
```

---

## Trust Boundary

- 仅授权目标、合法研究、防御验证、自有/开源源码审计。
- “可控输入”≠漏洞；必须有 **source→sink** 或 **安全控制缺失** 证据。
- FOFA 只做指纹与暴露统计；**不对未授权第三方实例利用**。
- 动态验证：只读、最小影响优先；禁止破坏性操作。
- API Key 从本地配置读取，禁止把 key 写入报告正文。

---

## When to Use

| 触发 | 动作 |
|---|---|
| “源码审计 / code audit” | 跑完整 P0–P6 |
| “有没有通用性漏洞” | 重点 P3–P4 + [generic-vuln-matrix.md](references/generic-vuln-matrix.md) |
| “写 FOFA 语法 / 去重 20+” | P1–P2；无 key 则标 Needs FOFA |
| “XSS/RCE/SSRF 打后台” | P4 + [chain-patterns.md](references/chain-patterns.md) |
| “验证后再输出” | 强制 P5 |
| “做成 skill / 优化流程” | P7 回写本目录 |

可与 `/hack` 体系配合：细节下钻到 XSS/SSRF/CMDi/Z3r0 专题；**本 skill 负责流程编排与通用洞主线**。

---

## P0 — 定位源码与范围

1. 工作区无业务代码时：搜同级/近期项目，**向用户确认路径**，禁止空目录硬审。
2. 识别：语言、框架、入口文件、配置、默认端口、旁路服务端口、部署方式。
3. 授权：仅静态 / 可本地动态 / 允许测绘查询。

```markdown
- 目标路径：
- 产品名 / 版本线索：
- 技术栈：
- 入口文件：
- 默认端口 / 绑定地址：
- 授权范围：static | local-dynamic | fofa-stats
```

---

## P1 — 指纹 → FOFA 语法

从源码提 **低误报** 指纹（详见 [fingerprint-playbook.md](references/fingerprint-playbook.md)）：

| 优先级 | 来源 |
|---|---|
| 1 | `<title>` 全等长标题 |
| 2 | 产品名 + 独特功能文案双锚点 |
| 3 | 独特 API 路径 / 静态资源 |
| 4 | 默认端口（仅辅助） |
| 5 | icon_hash / header（可选） |

输出：

```text
# Primary
title="EXACT_TITLE"

# Secondary
body="UNIQUE_A" && body="UNIQUE_B"

# Tertiary（功能锚点）
body="FEATURE_X" && body="FEATURE_Y"

# 过宽语法（仅对照，不计入产品案例）
title="SHORT_NAME"
```

规则：

- 主语法必须高精确；过宽 `title=短名` 只作噪声对照。
- 同步记录易误报词（通用英文名、NAS、博彩同名等）。

---

## P2 — 暴露面门槛（辅线，不阻断）

默认阈值：**去重后 ≥ 20**（`ip:port` 优先）。

| 精确指纹去重 | 决策 |
|---|---|
| ≥ 20 | 标注高暴露；源码洞 + 批量价值都高 |
| 1–19 | 低暴露；源码审计照常 |
| 0 | 未入测绘/私有化；**源码结论仍有效** |
| 无法查询 | `Needs FOFA`，**禁止编造** |

查询操作见 [fofa-ops.md](references/fofa-ops.md)。  
脚本：`scripts/fofa_query.py`（key 从 FofaViewer `config.properties` 或环境变量读取）。

**重要**：过宽语法命中 ≠ 产品案例。必须抽样看 title/body 是否匹配产品指纹。

---

## P3 — 入口 / 鉴权 / 信任边界（主线最高优先）

### 3.1 入口枚举

- HTTP routes / Blueprint / Controller / Router
- WebSocket / SocketIO 事件
- 第二进程/旁路端口（service manager、agent、MCP、debug）
- 静态与 `send_from_directory` / 下载 / 上传

### 3.2 鉴权（先于一切注入类）

检查：

- 全局 `before_request` / middleware / gateway auth
- 登录、Session、JWT、API Key、Basic Auth
- 管理 API 是否匿名 200
- CORS、CSRF、WebSocket origin
- 绑定：`0.0.0.0` vs `127.0.0.1`

**判定模板**：

```
无鉴权 + 管理能力外露 (+ 可选 0.0.0.0)
→ CWE-306 缺失认证 → 直接后台接管（Chain A）
```

这是最常见的 **通用根因**。后续 XSS/RCE/SSRF 是加重链，不是唯一路径。

### 3.3 信任源

用户输入、Header、上传、配置写回、DB 回显、爬虫入库、Webhook、Agent 工具参数。

---

## P4 — 通用洞矩阵 + 打后台

先跑通用矩阵（详见 [generic-vuln-matrix.md](references/generic-vuln-matrix.md)），再深挖三类高价值链。

### 4.0 通用洞优先序

```
1. 缺失认证 / 未授权管理接口     CWE-306 / 284
2. 敏感配置/密钥泄露与可写       CWE-200 / 312 / 732
3. SSRF（尤其 full-read）        CWE-918
4. 存储/反射 XSS                 CWE-79
5. 命令执行 / 间接 RCE           CWE-78
6. 路径穿越 / 任意文件           CWE-22
7. 注入类（SQLi/NoSQLi/SSTI）    按栈出现再挖
8. 硬编码密钥 / 过宽 CORS        CWE-798 / 942
```

### 4.1 XSS

| 找 | 说明 |
|---|---|
| 模板未转义 | 服务端反射 |
| `.html()` / 模板字符串拼 DOM | 前端；**属性 `data-*=${x}` 常漏** |
| 爬虫/用户内容入库再展示 | 二阶存储 XSS |
| 有会话 vs 无鉴权 | 有会话→打管理员；无鉴权→降级但仍记 |

### 4.2 SSRF

| 找 | 说明 |
|---|---|
| replay / proxy / webhook / 预览 / 截图 / 导入 URL | 经典入口 |
| 只校验 `http(s)` 无私网拒绝 | 高危 |
| 回显 body | full-read |
| `verify=False` + 跟跳 | 加重 |

打后台：`127.0.0.1` 管理端口、CDP、云元数据、Redis、Docker…

### 4.3 RCE / 等价

| 找 | 说明 |
|---|---|
| `os.system` / `subprocess` / `shell=True` | 直接 |
| 配置可写路径 + 启动服务读路径 | 间接 RCE |
| CLI 工具用户 args（nmap 等） | 参数注入/内网扫描 |
| SSTI / pickle / 表达式 | 按栈 |

无稳定直达时标 **Likely**，不要把“参数进 nmap”直接写成稳定 RCE。

### 4.4 打后台链路（必报）

见 [chain-patterns.md](references/chain-patterns.md)：

| ID | 模式 |
|---|---|
| A | 无鉴权直达后台 |
| B | 配置/密钥泄露扩权 |
| C | SSRF → 本机/内网管理面 |
| D | 存储 XSS → 管理员会话 |
| E | 配置篡改 → 进程启动 → 间接 RCE |
| F | A/B/C 组合 |

每条链写清：**前置条件 → 步骤 → 后台能力 → 状态**。

可选加载专题：`xss-cross-site-scripting`、`ssrf-server-side-request-forgery`、`cmdi-command-injection`、`z3r0-code-audit`。

---

## P5 — 多视角本地验证（输出前强制）

**未验证不得写 Confirmed。**

每个候选至少 3 个视角：

| 视角 | 验证 |
|---|---|
| V1 静态可达 | 路由无鉴权？参数到 sink？ |
| V2 控制缺失 | 无 allowlist/escape/authz？ |
| V3 数据流闭环 | source 实际影响 sink（含前端）？ |
| V4 利用条件 | 绑定、端口、依赖服务默认开启？ |
| V5 反证 | 隐藏中间件、仅 localhost、框架自动 escape？ |

推荐命令：

```bash
python scripts/verify_sinks.py --root <SRC>
python scripts/audit_generic_scan.py --root <SRC>
```

状态机：

| State | 含义 |
|---|---|
| Confirmed | ≥3 视角一致 + 代码证据 |
| Likely | 强证据，差动态一步 |
| Informational | 弱点明确，利用条件苛刻 |
| Not Reproduced | 反证成立 |
| Needs FOFA | 仅数量待查 |

---

## P6 — 汇总输出

使用 [report-template.md](references/report-template.md)。结构固定：

1. 范围与栈  
2. FOFA（语法 + 精确去重结论，可 0）  
3. 攻击面地图（鉴权/绑定/入口）  
4. **通用漏洞表（主）**  
5. 打后台链路  
6. 验证记录  
7. 否决项  
8. 修复优先级  

报告语气：技术、可复核、区分 Confirmed/Likely；不夸大 FOFA。

---

## P7 — Skill 反馈

实战后可更新：

- `references/generic-vuln-matrix.md` — 新通用检查项  
- `references/chain-patterns.md` — 新链路  
- `references/fingerprint-playbook.md` — 新指纹字段  
- `scripts/*` — 新自动检查  
- 本 `SKILL.md` — 流程缺口  

---

## Agent Operating Rules

1. **代码审计主线**；FOFA 失败/0 命中不停止审计。  
2. **先鉴权与绑定**，再 XSS/RCE/SSRF。  
3. **通用洞优先**于冷门逻辑洞。  
4. **FOFA 数量不造假**；过宽语法命中要人工判误报。  
5. **输出前验证**；脚本优先。  
6. Key 只读本地配置；报告不回显完整 key。  
7. 对未授权第三方：只给指纹与源码结论，不提供定向利用操作步骤指向活体目标。  

---

## Quick Start

```text
按 src-audit-chain 审计 <源码路径>：
1) 代码审计为主，判断通用性漏洞（Auth/SSRF/XSS/RCE/配置泄露）
2) 提取 FOFA 语法；有 key 则查精确指纹去重是否≥20（不阻断）
3) 梳理打后台链路
4) 多视角本地验证后再汇总
```

```text
只做通用洞：按 src-audit-chain 的 P3–P5 审计 <路径>，输出 CWE 对照表与修复优先级。
```

---

## 目录结构

```
src-audit-chain/
├── SKILL.md
├── references/
│   ├── generic-vuln-matrix.md
│   ├── chain-patterns.md
│   ├── fingerprint-playbook.md
│   ├── fofa-ops.md
│   └── report-template.md
└── scripts/
    ├── verify_sinks.py
    ├── audit_generic_scan.py
    └── fofa_query.py
```
