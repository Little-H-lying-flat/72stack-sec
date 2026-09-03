# 靶场 / 全自动 · Phase 1–5

> **仅当入口分流走到「靶场」或「全自动完整站」时才 Read。**
> 国内默认「挖 XXX SRC / 某品牌」**禁止**把本文件当主流程，也不把 4.5 语义审计当必做。
> 入口：`SKILL.md` 分流表。国内报告只认 `~/.grok/rules/vuln-report-format.md`。

靶场（juice-shop / testfire / mlecms）：Phase 1–5 + `python scripts/gate_check.py --work <dir> --tier formal`。
全自动完整站 + URL：先 `11-fullauto-pipeline.md`（默认 `tier=practice`），本文件作 Phase 细节补页。

---

## Phase 1 · Intake

五项 checkpoint 逐条确认（默认已是授权语境，禁止开场盘问授权书）：in-scope / out-of-scope / 规则 / 时间盒 / 建账（格式见 `09-target-workspace.md`）。全自动模式：五项落 mission 块（`11-fullauto-pipeline.md` §1），缺项一次问完。

## Phase 2 · Recon（被动侦察）

不发包给目标。MUST 输出来源 ≥3 的资产清单：CT 日志 / Wayback / GitHub dorks / FOFA / SecurityTrails / ASN。

## Phase 3 · Enum

MUST 输出活资产矩阵（域→端口→服务→指纹→JS endpoint）。工具回退链见 `11-fullauto-pipeline.md` §1.1 preflight。
**条件触发 Read**：国产 OA/中间件指纹→`dictionaries/chinese-srcfingerprints.md`+`default-credentials-cn.md`；银行/电信→`industry/`；云/K8s→`playbooks/cloud/`。

## Phase 4 · Hunt

**4.5 语义审计 = 靶场发现主引擎（本文件范围内必做，国内默认线不做）**：理论发现不计入（CORS/SourceMap/安全头/内网IP/孤立 Stack Trace——现象不是漏洞，14 §7 铁律）；先威胁建模（业务/技术栈/攻击面三认知，SPA/无权限页→JS 优先，见 14 §0），再表单型目标按 `14-semantic-audit.md` 三问；SPA/API 型用其 §5 接口三问 → 产出 `suspects.md`；confirmed 必须 `src: S-xx` 因果链引用（§6）。

**payload 确认（懒加载）**：对 suspects 每条按其映射类只 Read 对应 playbook 的命中场景节。撞型仍以知识库为准（见 `知识库/同型对照.md`），下表是靶场确认弹药的 playbook 展开。

| 入口信号 | Read |
|---|---|
| Actuator/Swagger/弱密码 | `playbooks/unauth-access.md` |
| .git/.env/路径列举 | `playbooks/info-disclosure.md` |
| 越权/IDOR/任意 X | `playbooks/arbitrary-x-authz.md` |
| 密码重置/支付/验证码 | `playbooks/logic-flaws/00-index.md` |
| OAuth/JWT | `playbooks/oauth-saml-jwt/00-index.md` |
| SAML | `playbooks/oauth-saml-jwt/11-saml.md` |
| REST API/BOLA | `playbooks/api-rest/00-index.md` |
| 输入进 DB | `playbooks/sqli.md` |
| 反序列化/XXE | `playbooks/rce/00-index.md` |
| SSTI | `playbooks/rce/14-ssti.md` |
| 框架 RCE | `playbooks/rce/10-framework.md` |
| URL 入参/缓存 | `playbooks/ssrf-cache-host/00-index.md` |
| 路径参数/LFI | `playbooks/path-traversal/00-index.md` |
| 上传点 | `playbooks/file-upload/00-index.md` |
| 输入回显 HTML/JS | `playbooks/xss/00-index.md` |
| 反代 TE/CL | `playbooks/http-smuggling.md` |
| GraphQL | `playbooks/graphql.md` |
| 并发/TOCTOU | `playbooks/race-conditions.md` |
| APK/IPA | `playbooks/mobile.md` |
| LLM/prompt 入口 | `playbooks/llm-prompt-injection/00-index.md` |
| 云资产/对象存储 | `playbooks/cloud/00-index.md` |

`dos.md` 不进默认表。`intranet-postexp/` **仅用户明说内网/已有 shell** 才 Read。

目录式 playbook 先读 00-index（子路由），再读命中子文件。命中→三段差分（`03-evidence-discipline.md` §3）→confirmed；去重与同根因合并（09 §2）。
**confirmed 后必问：这一步能链到什么？**（01 §3.6）；formal 档 Critical 目标导向（01 §3.7）。

**懒加载通用方法论**（卡壳才读）：01 / 02 / 04 / 05 / 06 / 07 / 08 / 09 / 10 / 11 / 12 / 13 / 14。

**探针哨兵**：连续 3 发同形失败即熔断跳项；响应异常模式暂停复核；疑似越 scope 立即停链路（11 §4.0）。
**出口检查（靶场/formal）**：`python scripts/gate_check.py --work <dir> --tier formal` 四查全绿才可宣布测完。国内默认不跑四查；全自动用 `--tier practice`。
**门闩分级（11 §2.1）**：`tier: practice` 只跑 gate_check practice + 差分；`tier: formal` 才拉满危害定性门+盲测+docx。门闩时间>挖洞时间=档位用错。

出 scope → 立即停，回 Phase 1 重核。

## Phase 5 · Report（靶场/平台 docx）

国内 SRC 正式报告**不走本节**，只认 `~/.grok/rules/vuln-report-format.md`。

0. findings.md 的 confirmed（经危害定性受理）行=提交清单
1. Read `references/compliance.md`
2. 仅 JSRC / 用户点名 docx：Read `references/templates/report-format.md`，写 gen_report_vN.py；报告落 report_dir，**不入任何 git**
3. 要素：标题 ≤80 字（endpoint+类型）/重现步骤（完整包）/影响+修复（CVSS+业务段）
