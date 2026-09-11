---
name: skill
description: |
  SRC 漏洞挖掘 + 白盒 0day。Grok-only（start-grok.cmd）国内 SRC 主流程：短表→JS→矩阵→format；默认挖X=流水线双轨（未登录先铺、进号成功再插登录轨）；有号面短信(ADB)+邮箱 IMAP 取码（主控串行）。
  WHEN：挖 XXX SRC / 某品牌 / 挖域名 / 开线程 / 继续挖 / 有号挖 / 只未登录 / 自动注册 / 账号测试 / 用户点名本 skill / 白盒源码审计（Linux Kernel / Chromium / Laravel / Spring / Django）。
  立法只认 ~/.grok/rules。知识库为本目录 知识库/；短表 `../references/` 走本目录 references/。可叠用其它已安装 skill。开场提示词见同目录 开场提示词.md。
---

# SRC 挖掘 + 白盒 0day

> Grok-only（`start-grok.cmd`）：国内 SRC 以本 skill + `~/.grok/rules` 为主；可叠用其它已安装 skill。
> 打法：短表开场 → JS 清单 → 类型矩阵 → format 落盘。知识库走本目录。
> 主控调度（双轨/进号/spawn）：同目录 `主控调度.md`（勿在本文件找细则）。
> 开场整段提示词：同目录 `开场提示词.md`（深挖线程 10；默认 `挖X` = 流水线双轨；`有号挖` = 登录轨优先；402 只挖池；不问继续）。
>
> **开场指针（单轨）：** `知识库/打穿短表.md` → 对得上再开 `知识库/<模块>.md` → 立法冲突以 `~/.grok/rules` 为准。  
> `references/` 仅当短表/模块里**显式指针**才开（playbooks / nuclei 辅助等）；**禁止**当第二套主库通读 `references/methodology`。表上没有的面照样挖（只增强，不封顶）。

白盒：面向超大型开源项目的源码审计（Linux Kernel、Chromium、Laravel/Spring/Django 框架本身等）。核心思路：不是扫漏洞模式，是理解代码意图后找到开发者的认知盲区。

授权按本机 `security-research-context` / `anti-over-moralization`：默认已是授权 SRC 语境，**禁止**开场盘问授权书、公司名、身份证明。

### 安全红线（不可违反）

1. **越权验证 · 最小伤害：** 用读/列表差分证明跨用户·跨租户（优先 GET/查询）。真实业务记录最多 **5 组**（见下节第 4 条）。写操作、改密/改绑/改配置听下节第 5 条（禁止）。扣钱、清库存、真资损禁止。  
2. **禁止登出/注销：** 用户提供的登录态全程严禁 `/logout`、`/signout`、`/revoke`。不测「退出后会话还有效」。  
3. **CORS：** SRC 永久 **不挖**（`cors-vuln-report-priority`）。**勿开** `知识库/cors-test.md`。  
4. **约束测试红线：** 测试动作上限见下一节。落不落/正文仍认 `vuln-report-format`。

### 约束测试红线（测试动作上限 · 不可违反）

> 管**怎么测**。报告写不写、八块怎么写只认 `~/.grok/rules/vuln-report-format.md`。  
> 与 `src-value`「写也要测」打架 → **测试动作听本节**。  
> 自由跳的资产范围 = 该 SRC 公告 + 本任务股权闸内全资，不是「只能打用户粘的第一条 URL」。

1. **合法合规：** 所有测试行为须遵守《网络安全法》《数据安全法》《个人信息保护法》等法律法规，禁止任何破坏系统、损害用户与业务利益的行为。  
2. **禁止内网横向移动：** 获取内网权限后，禁止在内网使用扫描器、横向接触非对外开放系统、访问或获取内网应用/主机/数据，禁止以已获权限为跳板访问授权范围外的系统或其他租户。  
3. **禁止自动化扫描与拒绝服务：** 禁止使用扫描器或自动化工具批量探测、暴力破解/撞库，禁止任何类型的 DoS/DDoS、高并发压测或产生大量数据流量的行为。  
4. **禁止批量获取数据：** 禁止批量读取、爬取、遍历、拖库或全量导出任何业务数据；越权测试以证明读取能力为限，读取真实数据不超过 5 组；注入测试读取表内数据不超过 5 组。  
5. **禁止深层渗透与破坏性操作：** 漏洞验证仅做最小化、无害化 PoC；禁止部署 WebShell、植入后门、执行系统命令等深层渗透行为；禁止任何增删改数据/配置的「写」操作及破坏性 Payload。  
6. **禁止敏感数据下载、外传与留存：** 禁止下载、保存、传播、留存源码、运营数据、用户资料、登录凭证等业务敏感数据（无论是否脱敏）；测试获取的代码/数据等信息须在漏洞确认后立即删除，不得非法留存及使用。  
7. **禁止自行深入验证凭据类漏洞：** 获取 AK/SK、Kubernetes 集群凭证（kube-config、ServiceAccount）等敏感凭据后，禁止自行深入业务验证危害（进业务、横移、改配置、拉工作负载）。  
8. **禁止超出授权范围测试：** 严格限定在公告授权的资产范围（IP、域名、路径、接口）内；禁止对第三方服务、外部 API、CDN 等连带测试。禁止使用违反平台规定或法律法规的文字、图片、视频作为测试素材。  
9. **禁止社工攻击与用户打扰：** 禁止社会工程学、邮件钓鱼、物理近源攻击，禁止使用社工库等非法手段获取信息；禁止向真实用户邮箱、手机、社媒发送测试信息、推送或发起群聊，禁止直接联系真实用户测试。  
10. **禁止逃避审计与瞒报：** 测试全程留痕，禁止删除、伪造测试日志；过程记在任务 `{名}_dig/`，打成了按 format 落 `报告/`。禁止瞒报已确认可写的中危/高危/严重。

**执行时怎么读（防误停、防误扩）：**

| 条 | 仍要做 | 立刻停 |
|----|--------|--------|
| 2 SSRF | 外带 DNS/HTTP、回显、打到自己的监听；证明能出网或打到监听即止 | 进内网当跳板扫端口/扫主机、登非开放系统、碰他租户 |
| 3 探针 | 清单内、有差分面的 curl/python 参数探针（注入/SSRF/XSS） | masscan/nmap 全段、ffuf 整站、nuclei 全量模板、登录框字典爆破、压测/DoS |
| 4 五组 | 换 id 证明他主体；列表用 total/条数差分 | 把全表拉下来、导出文件、真实记录超过 5 条 |
| 5 写/RCE | 读证明越权；RCE/命令类证到 sink 会执行（报错/回显差分）即止 | POST 增删改、改密改绑改配置、WebShell、后门、真跑系统命令、破坏性 payload |
| 6 留存 | 密钥/Cookie **只**进正式 `报告/`（format 要求实值的才写）；JS 提取件留 `js/` 供本任务分析 | 把源码/用户资料/凭证另存外传；dig 里过程敏感件确认后不删 |
| 7 凭据 | format 认钥闸：假值对照 + **不影响线上**的身份/列表一枪。再往业务走禁止 | 拿 AK/SK/kube 进控制台、列桶后继续转账/改配置/进集群干活。连认钥一枪也被当次平台公告禁止 → **不落盘** |
| 8 范围 | 自由跳：SRC 公告 + 股权闸内全资 + 业务流自然带出的同簇 host | 未进站 FOFA 出圈；参股/第三方/CDN/图床当目标深挖 |
| 9 发码 | 本机 ADB/IMAP 取**自己测试号**的码（`sms_code.py` / `email_code.py`） | 给真实用户发短信/邮件/推送、社工库、钓鱼 |
| 10 留痕 | `{名}_dig/` 过程 + `报告/` 正式篇 | 删日志、把已确认的洞藏起来不写 |


### 自动边界（编排上限 · 不可违反）

> P0（2026-09-11）。目标是**可审计 / 可提交 / 伤害可控的发现引擎**，不是影响半径最大化。  
> 约束测试红线管「怎么测」；本节管「**什么可以自动跑、什么必须人在环**」。与红线冲突时两闸都听，取更严。

**产品定位：** 编排更强、边界更硬、发现面更齐——**禁止**把本 skill 做成「全自动打穿生产」。

| 可自动（主控编排） | 禁自动（默认停，须用户点头才破例） |
|--------------------|--------------------------------------|
| 派轨 / 空席补席 / 一种子闭环换种 | 无人值守跨租户试探、批量拖会话仓 / 令牌集 |
| `pending_from_done` / `auth_flow` 串行进号（自己的测试号） | 无上限打线上、扫描器式全站喷参 |
| suspects 覆盖闸、DONE 字段检查、验票差分（`scripts/p2_gate.py`） | 把「影响半径最大」当成功标准的连招 |
| 盲区库回灌提醒、短表开场认法几枪 | 线程发码/注册/登录；空 cookie 开登录轨 |
| 身份一枪 + 半径勾选（见 suspects / DONE_auth） | 高危拟进、新公网面、换生产号、动防火墙/服务器——**须用户确认** |

人在环保险丝：高危拟进、要发码、开新公网面、换生产号、动服务器/防火墙 → Agent 只建议，不越级执行。

### 自由跳节奏红线（与 `~/.grok/rules/dig-scope-workflow.md` §1.0.1 / §1.6 对齐 · 不可违反）

模糊目标（只给集团名、没有 URL 清单）且用户未叫停时：

0. **「挖」+ 集团/品牌名：** 起手短表（和自由跳并行）。磁盘有 `*src经验.md` 才开专篇，没有不算缺。认到编程台 / Codex RPC 打开 `知识库/cloud-ide-codex-rce-chain.md`。**禁报假点 ≠ 根域永封**（工商公示不报，新 path 照打）。  
1. **起手落盘** `资产/种子队列.md`：用户词 + 业务名/品牌 + SRC 范围域 + 全资子公司域（多条），禁止队列只有原词一条  
2. **一种子闭环（§1.0.1）：** 搜一个种子 → 去重去废去非存活 → 剩下的活面全部挖完 → 才标 done → **立刻**搜下一条 pending。禁止多种子一次搜完再挖  
3. **禁止**停工问：「要不要继续？」「其它品牌要不要也挖？」「下一步您看？」  
   **禁止**用「本波产出 / sid 池收口 / 本轮完成」当终章停转。CLI 里无 tool_calls 的纯文本 = 整场停机。  
4. **一轮搜完 ≠ 任务结束**；「本种子收工」= 该种子剩余活面已挖完，**同一回合**搜下一条 pending，不是整场收工，也不是 FOFA 条数到手就换种  
5. **主控回合闸：** 空席未填满、或还有 leftover / 无 DONE_auth 的 cookie / pending 种子 → **本回合必须再 spawn 或跑进号脚本**，禁止纯文本收口。开场闸达标 ≠ 可以停。只有用户叫停 / 锁面簇做完 / 环境全线不可用才真停。  
6. **打开是登录页：** 先找业务面（本 host 网关或跳转后的 host）。登录表单看得见的打通或证伪就停；繁琐验证 / 别人的身份页 / 同皮壳不耗。清单里有发会话 / 重置 / 改绑 / 换票 → `dig-scope` §4.2.2（有入口勾，无入口 N/A）。看见登录页不是换资产。**不是登录相关一律不管**（`dig-scope` §4.1.1）。  
   默认 `挖X` 走下节流水线双轨：未登录轨挖未登录；干净口回单进号后插登录轨。`只未登录` / `没号挖` = 不开登录轨。`有号挖` / `只登录` = 登录轨优先；未进号肥面只派一眼未登录轨回单，不跑全矩阵。禁止把「要发码」写成放弃。covered 口径见下节。  
7. **进站打法**只认 `dig-scope` §4。本文件不另写一套。  

挖什么：`src-value-hunting`。正式报告只认 `vuln-report-format.md`。任务目录：`desktop-task-folder`。CORS 不挖：`cors-vuln-report-priority`。与知识库冲突时 **以 rules 为准**。

测绘节奏只认 `dig-scope` 一种子闭环。FOFA 语法最短备忘在 `知识库/recon-methodology.md` 文首，**不是**本技能开场。搜资产用 MCP `fofa`，不要自己 curl。三账号（主号 → backup → backup2）在 `~/.grok/config.toml` + `fofa.py` 自动切，限流闸认 `dig-scope` §2.1.4。**禁止**把 email / key 写进本文件或对话。

### 有号面 / 主控调度（指针）

> **整段调度只认同目录 `主控调度.md`。** 本 SKILL 不重复双轨/进号/spawn 细则。  
> 开场：主控 Read `主控调度.md`；线程只拿 `线程必读.md`。  
> 口令速查：`挖X`=流水线双轨；`只未登录`/`没号挖`=仅未登录轨；`有号挖`/`只登录`=登录轨优先。  
> covered / 缺号行 / auth_flow / spawn 必贴块 → 全部见 `主控调度.md`。  
> 写 `covered_hosts` 前还须过下面 **suspects 覆盖率硬闸**。

### suspects 覆盖率硬闸（发现引擎 · 不可违反）

> 发现主路径认 `references/methodology/14-semantic-audit.md`（仅此篇作指针）+ 本站 `{dig}/{host}/suspects.md`。  
> 模板：`references/templates/suspects-template.md`。跨任务记忆：`知识库/semantic-blindspots.md`。

1. **有结构提取的站**必须落 `suspects.md`（威胁模型头 + S-xx 行）。瘦壳一眼证伪可写 `suspects: N/A 瘦壳` 一行原因。  
2. **covered 前自检**（主控写 covered_hosts 之前）：表单字段三问 / 接口三问 /（有会话则）认证后面 / 平凡分页参 / **信任边界（凭证作用域+半径）** —— 未勾满且无 N/A+原因 → **禁止**写 covered。有会话轨 `DONE_auth` 缺 `身份=` 或 `半径=` → **禁止** covered。  
3. **确认只打清单**：禁止按知识库模块对整站盲扫；无 S-xx 映射则先补语义疑问再测。  
4. **回灌闭环（P3）**：中危+ 确认或明确漏报 → **同回合**追加 `知识库/semantic-blindspots.md` 一行；操典见 `知识库/回灌闭环.md`。有中危+/漏报却无盲区行 → **禁止 covered**。禁止写利用步骤/敏感实值。**令牌类（P1）**：涉及 cookie/`*_st`/passToken/OIDC/会话仓/跨租户 id 的中危+ → 同回合强制回灌，并引用「令牌绑谁/能到哪/跨租户墙」问句之一。  
5. **开站引用**：新建 `suspects.md` 时威胁模型头须引用盲区库相关问句（或 N/A+原因）；模板已含该勾选。  
6. **假测完判定**：无 suspects（或未声明 N/A）却写本站矩阵「已测完」= 违规，退回补清单。  
7. **短表进阶**：同一根因盲区 ≥2 次 → 走 `hunt-iter`，不在本文件改打穿短表。

---

## 对得上再开

进站先短表；对得上就打开对应模块。磁盘有 `*src经验.md` 才并行打开，没有不算缺。进站打法认 `dig-scope` §4；力气先砸哪认 `src-value` §1.1；每类怎么打认 `src-value` §3。打开模块 ≠ 只测表上那一枪。

| 目标特征 | 优先测试模块 |
|---------|------------|
| 有用户体系（注册/登录） | `知识库/idor-test.md`（越权）+ `知识库/authbypass-test.md`（任意登录/接管，§4.2.2）|
| 有搜索/筛选功能 | `知识库/injection-test.md`（注入）|
| 有文件上传 | `知识库/file-upload-test.md` |
| 有内容请求/预览功能 | `知识库/ssrf-test.md` |
| 有评论/留言/富文本 | `知识库/xss-test.md` |
| 有支付/优惠券/积分 | `知识库/logic-test.md` + `知识库/race-condition-test.md` |
| 接口返回字段多 | `知识库/info-leak-test.md` |
| GraphQL 接口 | `知识库/graphql-test.md` |
| OAuth/JWT/SAML 认证 | `知识库/oauth-jwt-test.md` |
| WebSocket 实时通信 | `知识库/websocket-test.md` |
| API 网关/微服务架构 | `知识库/api-gateway-test.md` |
| CDN/缓存服务 | `知识库/cache-poisoning-test.md` |
| AI/LLM 功能 | 对话口工具真执行走 `知识库/agent-tool-exec-test.md`。**禁开** `llm-security-test.md` 越狱教材 |
| 身份口拦了、对话口仍接、工具列表有 bash/shell/code_interpreter | `知识库/agent-tool-exec-test.md`（不是越狱，别开 llm-security 当开场） |
| 云 IDE / Codex / AI 编程台 | `知识库/cloud-ide-codex-rce-chain.md`（弱口令→/codex-api/rpc RCE） |
| 前后端分离架构 | `知识库/http-smuggling-test.md` |
| 返回 401/403 | 先分清：登录页 → §4.1.1 找业务面，认证口走 §4.2.2；**不要**开 `401-403-bypass` 磨登录 HTML。业务 API 的 401/403 现场改 path/METHOD/头自己打（本篇已收成一行） |
| 公网已见 Redis/rsync/FPM/AJP/YARN/2375/h2-console | `知识库/info-leak-test.md` §五（见了才打）+ 对应 `ssrf`/`jndi`/`path-traversal` |
| 有 CORS / 跨域接口 | **跳过**（不挖，**勿开** `cors-test.md`）；转注入/越权等 |
| 有状态变更写操作 | `知识库/csrf-test.md` |
| 有 WAF 拦截 | `知识库/waf-bypass.md` |
| 路径/下载/读文件 | `知识库/path-traversal-lfi-test.md` |
| XML / 文件解析 | `知识库/xxe-test.md` |
| Java 反序列化 / 中间件 | `知识库/deserialization-test.md` + `知识库/jndi-injection-test.md` |
| 子域/资产接管线索 | `知识库/subdomain-takeover-test.md` |
| Host / 缓存 CDN | `知识库/http-host-header-test.md` + `知识库/cache-poisoning-test.md` |

### WAF 拦了再开

有差分面的参被拦了，再开 `知识库/waf-bypass.md`，换编码 / 换位置。  
**禁止**开场对每个 path 丢 `'` 当 WAF 检测。

### nuclei（辅助，不是主路径）

主路径认 `dig-scope` §4，**不是**扫漏洞。  
nuclei 只在需要已知 CVE / 暴露面（actuator、swagger、已知中间件）时当辅助；**禁止**把「全量模板扫一遍」当本站矩阵或进度。需要时自己收窄模板，不要当开场必跑。

JS 逆向细节 → `知识库/js-reverse-guide.md`。打开目标按 `dig-scope` §4 抽 path+钥匙、回包进清单。未登录轨下到 `js/{host}/anon/`；登录轨换 sid 抽后台包到 `js/{host}/{sid}/`，先读 anon、只补新 chunk（见该篇「登录后懒加载」）。

中危、高危、严重，确认了立刻按 `vuln-report-format` 落 `报告/`。中危升链、换站认 `dig-scope` §4.3。进不进短表只认 `hunt-iter`。未登录轨交付 = 迭代 + 缺号行（`DONE_anon`）；登录轨交付 = 迭代 + 身份行（`DONE_auth`）。测试动作上限认「约束测试红线」。禁止破坏性利用、真资损、登出用户会话。

### 报告版式 / 拟进扫描（可选辅助 · 不定级）

落盘前可跑版式闸（八块标签、全角＃、等级字面、匿名闸粗检）；**失败先改报告再交**。不定级、不替代 `vuln-report-format` 正文，也不验 curl 是否真打通。

```
python "{skill_dir}\scripts\pending_from_done.py" --root "Desktop\{任务}_SRC挖洞"
python "{skill_dir}\scripts\report_format_check.py" --dir "Desktop\{任务}_SRC挖洞\报告"
python "{skill_dir}\scripts\done_iter_scan.py" --only-real
```

```
python "{skill_dir}\scripts\suspects_coverage_check.py" --host-dir "{dig}\{host}"
python "{skill_dir}\scripts\suspects_coverage_check.py" --dig-root "{dig}" --only-fail
python "{skill_dir}\scripts\blindspot_remind.py" --host-dir "{dig}\{host}"
python "{skill_dir}\scripts\blindspot_remind.py" --dig-root "{dig}" --strict-suspects-header
```

covered 前建议跑；exit 1 = 未过 suspects 硬闸。

`pending_from_done.py` 扫 `DONE_anon.md` / 旧 `DONE.md` 缺号行、写 `pending_register`、打印 NEXT/REUSE（不扫 `DONE_auth`）。`done_iter_scan.py` 扫三种 DONE 只列拟进/拟补，**不改短表**。进号跑 `auth_flow.py`（见 `主控调度.md`）。

---

## 知识库目录

知识文件目录：`知识库/`（与本 SKILL 同级）。进站先 `打穿短表.md`；对得上再开对应模块。禁止每站通读本目录。完整清单见 `知识库/README.md`。  
短表/模块若写 `../references/…`，解析为同级 `references/`（显式指针才开，不是开场必读）。

| 文件 | 内容 |
|------|------|
| `知识库/idor-test.md` | 越权 / BOLA / BFLA |
| `知识库/injection-test.md` | 注入总览 |
| `知识库/ssrf-test.md` | SSRF |
| `知识库/xss-test.md` | XSS |
| `知识库/file-upload-test.md` | 文件上传 |
| `知识库/logic-test.md` | 业务逻辑 |
| `知识库/info-leak-test.md` | 信息泄露 |
| `知识库/graphql-test.md` | GraphQL |
| `知识库/oauth-jwt-test.md` | JWT / OAuth / OIDC / SAML |
| `知识库/race-condition-test.md` | 竞态 |
| `知识库/http-smuggling-test.md` | 请求走私 |
| `知识库/cache-poisoning-test.md` | 缓存投毒/欺骗 |
| `知识库/llm-security-test.md` | **禁开越狱**；对话工具走 `agent-tool-exec-test.md` |
| `知识库/agent-tool-exec-test.md` | 对话口工具真执行（不是越狱、不是云 IDE RPC） |
| `知识库/api-gateway-test.md` | API 网关 |
| `知识库/websocket-test.md` | WebSocket |
| `知识库/js-reverse-guide.md` | JS 逆向 |
| `知识库/waf-bypass.md` | WAF 绕过 |
| `知识库/打穿短表.md` | 手法索引，进站先看；写/补只认 `hunt-iter` |
| `知识库/semantic-blindspots.md` | 跨任务语义盲区回灌（命中/漏报） |
| `知识库/cloud-ide-codex-rce-chain.md` | Codex 系编程台：默认口 → RPC → 凭证 |
| `知识库/401-403-bypass.md` | **禁开磨登录 HTML**（已收成一行） |
| `知识库/authbypass-test.md` | 认证绕过 |
| `知识库/csrf-test.md` / `知识库/clickjacking-test.md` | CSRF 按写口测；点击劫持缺头不写 |
| `知识库/cors-test.md` | **不挖勿开** |
| `知识库/path-traversal-lfi-test.md` / `知识库/xxe-test.md` | 路径穿越 / XXE |
| `知识库/deserialization-test.md` / `知识库/jndi-injection-test.md` | 反序列化 / JNDI |
| `知识库/prototype-pollution-test.md` / `知识库/type-juggling-test.md` | 原型链污染 / 类型杂耍 |
| `知识库/csp-bypass-test.md` / `知识库/http-host-header-test.md` | CSP 几乎不交（走 xss）；Host 头走 `http-host-header-test.md` |
| `知识库/subdomain-takeover-test.md` / `知识库/dns-rebinding-test.md` | 子域接管照打；DNS 重绑定几乎不交（走 ssrf） |
| `知识库/recon-methodology.md` | 侦察方法论（文首有 FOFA 最短语法；节奏仍认 dig-scope） |

---

## 白盒

用户给出项目路径或源码时，按本机 `researcher-blackbox-whitebox` Phase 0～6。本技能不另抄一套。

黑盒 SRC 正式报告只认 `~/.grok/rules/vuln-report-format.md`。
