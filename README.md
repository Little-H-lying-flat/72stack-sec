**中文** · [English](README.en.md)

# 72stack-sec

这是一个给 SRC、众测和 Bug bounty 用的 Claude Code skill。

简单说，就是你给它一个目标，它会按一套固定流程帮你推进漏洞挖掘：先确认目标范围，再做信息收集和资产枚举，然后进入漏洞测试，最后整理报告。

```text
intake → recon → enum → hunt → report
```

项目内置了一批从公开来源整理的知识库，包括：

- 20 类攻击 playbook（含云安全 / K8s / 对象存储子 playbook）
- 310 个结构化 payload
- WAF / EDR 绕过变体
- HackerOne 已披露 High / Critical hacktivity 数据
- WooYun 历史案例统计残余
- 常见国产组件指纹和默认凭据

## 安装

Marketplace：

```bash
/plugin marketplace add Little-H-lying-flat/72stack-sec
/plugin install 72stack-sec@72stack-sec
```

Git：

```bash
git clone https://github.com/Little-H-lying-flat/72stack-sec.git ~/.claude/skills/72stack-sec
```

## 目录结构

```text
references/
  methodology/    五阶段流程、攻击优先级、绕过工具集、证据规则、2026 一线方法论汇编、JS 侦察与 Vue SPA 路由最大化、JS 反调试突破与加密参数 Hook（无限 debugger / CryptoJS / RSA / 国密）、多 agent 编排（设计稿）、目标工作区与执行台账、目标原型路由、全自动无人值守整站管线
  playbooks/      每类漏洞一个文件，包含真实 H1 案例和 payload；cloud/ 为云安全子 playbook（云授权项目 / IAM / 对象存储 / K8s）
  industry/       银行/金融、电信/ISP 垂直场景 playbook
  dictionaries/   国产组件指纹和默认凭据
  sources/        外部思路源路由：国内实战社区（先知/奇安信攻防/跳跳糖/FreeBuf/看雪）、国外平台（PortSwigger/Exploit-DB/HTB/H1 Blog/PayloadsAllTheThings）、官方漏洞库（NVD/AVD/Seebug/CNVD），含 dork 与 NVD API 检索模板
  templates/      CVSS 4.0 报告模板
  h1-reports/     HackerOne High/Critical 披露案例（原始 2887 + 2026-08 增量，分类索引 2836 条/144 类），并按 weakness 分组
  payloader/      310 个结构化 payload、176 个原始 WAF/EDR 绕过 payload、114 个工具命令
```

playbook 是主要入口。所有 playbook 都按黑盒视角编写，默认你只有 URL，没有源码。

每个 playbook 都围绕同一套问题展开：

- 去哪里找入口
- 用什么 payload 测
- 观察哪些响应特征
- 如何判断影响
- 如何提高漏洞价值
- 哪些行为不能做

整体思路不是堆 payload，而是把测试动作、证据留存和报告输出串起来。

## MCP 工具集成

本 skill 集成本地 MCP 服务器作为工具层，让 Claude 在 hunt 阶段能直接调用浏览器自动化、CDP 调试、网络拦截、JS hook、AST 反混淆、Frida 内存验证、WASM 逆向、Source map 重构、Android adb 桥接、SSL pinning 绕过等能力。

**当前主选**：[jshookmcp](https://github.com/vmoranv/jshookmcp) 0.3.0（134 工具精选 / 386 全集 / 36 域），完整索引与场景映射见 [`references/tools/mcp-jshook.md`](references/tools/mcp-jshook.md)。

7 个高关联 playbook（`xss` / `rce` / `ssrf-cache-host` / `mobile` / `oauth-saml-jwt` / `api-rest` / `file-upload`）末尾各有 `## 相关 MCP 工具` 反向锚点，指明该攻击面下应该调哪些 jshook 工具、何时调。

## TODO

- 支持引入更多 tools
- 多 agent 执行工作流（设计稿：[references/methodology/08-multi-agent.md](references/methodology/08-multi-agent.md)，默认关闭，待实战验证后启用）

## 触发关键词

skill 内置触发词包括：

- bug bounty、HackerOne、SRC 挖洞、漏洞赏金、众测
- WAF bypass、绕过 WAF
- 如何测试某个 endpoint / API / 参数
- 任意账号、任意修改、任意删除
- 密码重置、找回密码
- 默认凭据、Actuator、暴露的管理后台
- 无限 debugger、反调试绕过、加密参数 / sign / aes hook、国密 SM2/3/4
- 组件历史漏洞 / CVE / PoC 查询，先知 / 奇安信攻防社区 / 跳跳糖 / FreeBuf / 看雪 / PortSwigger / Exploit-DB 思路检索
- 全自动跑完整站、无人值守挖洞、整站自动化漏洞测试

也可以显式调用：

```text
/72stack-sec:72stack-sec <target>   # Marketplace 插件安装
/72stack-sec <target>              # Plain git standalone skill
```

## Playbook 列表

| Playbook | 嵌入 H1 案例数 |
|---|---:|
| arbitrary-x-authz（IDOR / 任意账户 / 提权） | 465 |
| rce（反序列化 / SSTI / XXE / 框架） | 385 |
| xss | 335 |
| info-disclosure | 319 |
| oauth-saml-jwt | 240 |
| logic-flaws（CSRF / 点击劫持 / 支付） | 234 |
| path-traversal / LFI / RFI | 163 |
| sqli | 147 |
| dos | 138 |
| ssrf-cache-host | 108 |
| unauth-access（默认凭据 / Actuator / 暴露服务） | 46 |
| http-smuggling / CRLF | 38 |
| api-rest / WebSocket | 15 |
| file-upload | 8 |
| mobile（Android / iOS） | 8 |
| race-conditions | 5 |
| llm-prompt-injection | 1 |
| graphql | 1 |
| intranet-postexp（内网 / 后渗透速查） | — |
| cloud（云授权 / IAM / 对象存储 / K8s） | 14 |

## 更新日志

### 2026-08-31

- 社区文章精读吸收（按 sources 路由实读 4 篇，嵌入 5 个 playbook，playbook 计数不变）：[LobeChat SSRF 盲区审计](https://xz.aliyun.com/news/92685) → `ssrf-cache-host` 盲打判定 oracle + 代理型/转发型 + 修复完整性审计（补丁 diff → 同类 sink 盘点）；[RAGFlow 三洞审计](https://xz.aliyun.com/news/92668) → `rce/14-ssti` Jinja2 实战案例（canvas DSL 两步注入 / cycler 链 / 换行绕过 / 版本窗口）、`path-traversal` §9 Zip Slip→sitecustomize 持久化 RCE、`arbitrary-x-authz` §3.3-A uuid1 推导 API key；[Vitest Browser Mode 权限绕过](https://xz.aliyun.com/news/92704) → `unauth-access` §2.5 开发态 / 测试框架服务暴露新面（读 / 写 / 删 / 延迟外带四原语）；[验签缺陷任意登录](https://forum.butian.net/share/4994)（摘要层）→ `arbitrary-x-authz` §3.3-B Sign 自签名 + 缓存串会话。`knowledge-sources.md` 新增 §5 已吸收清单（落点索引，防重复精读）；不可达源（PortSwigger / 跳跳糖 / CNVD）均标实测口径

### 2026-08-30

- 新增 [references/sources/knowledge-sources.md](references/sources/knowledge-sources.md)：外部思路源路由——国内实战社区（先知 / 奇安信攻防 / 跳跳糖 / FreeBuf / 看雪，配套阿里云漏洞库 AVD）、国外平台（PortSwigger Web Security Academy / PayloadsAllTheThings / Exploit-DB / Hack The Box / HackerOne Blog）、官方漏洞库（NVD API 2.0 无 key 直连 / CVE.org / Seebug / CNVD / CNNVD）；全部 URL 当日实测（JS 渲染搜索与反爬站点标 dork 兜底口径），含场景路由、dork 与 NVD API 检索模板、引文纪律
- 11 号管线 Juice Shop 首战校准：§4.4 公共共享实例纪律（503+托管商错误页签名 = 实例级故障立即停全部流量，单发记录不复测，恢复签名=特征端点字节数）+ §3 第 8 条 js-recon 端点提取三模式（引号字符串 + 模板字符串 + 懒加载 chunk，单模式必漏）；首战 F-01 /ftp/ 目录列表 / F-02 memories 邮箱泄露 confirmed，实例 crash-loop 转恢复监控
- 11 号管线第 17 轮"另一个站"发现校准：新增 §3.1 同域多站发现流程（权威源=业主门户导航页 / 端口非常见段补扫 / 结构路径字典，三层全阴性=资产清单终态）+ §4.5 整站级 env-broken 处理（统一错误签名 → 全队列降级 + 恢复监控 3min×3 次 + 重置窗口=暴露窗口做 install/备份残留扫描）；实测 73 端口 / 53 路径 / 导航页 2 RANGE 全阴性，mlecms 整站 686B 坏签名转监控
- 11 号管线优化轮：§1.1 preflight 固化为可执行脚本 [`scripts/preflight.py`](scripts/preflight.py)（markdown 表直贴 scope.md / `--json` / `--probe-target`；本机 dogfood 3/8 OK 与实测一致）、§2 state 写时机=队列项边界、新增 §4.7 双账号 seed 预置动作、§7 JSRC 目标路由 jsrc-report skill
- 11 号管线第 16 轮全流程验证校准 5 处：§3 侦察产物 scope 纪律（非 in_scope 域只记录不探测）、§4.5 repro 前置端点活性检查（env-broken 不产生假阴性）+ 0B 窗口三档退避 blocked 不判阴性、§5.1 标准动作 ③证据判读 grep 内建 `-a`（GB2312）、§8 队列 asset 字段=完整可请求 URL（裸路径两实例）、§7 覆盖率矩阵=state.json status 投影；reverify/repro 队列类首跑 9/12 confirmed 存活
- 11 号管线靶场首跑校准 8 处补丁：产物隔离（报告/work/证据永不入 git 远端）、mission `report_dir` + §1.1 preflight 工具矩阵（实测缺 nuclei/browser-harness 的回退链）、§4.1 节流阶梯量化（8→15→30→60s）、§4.5 reverify 拆 repro/oob（OOB 回调轮询防假阴性）、§4.6 账号缺口降级不提问、§5.1 消费性判别标准动作（id=/pid= 参数名教训 + 区分"未消费/数字归一"）、§7 报告落 report_dir、§8 evidence 同轮前缀核对（中断会话遗留防重复）
- 11 号管线吸收 GitHub 三模式：RefPentester 自反思循环 → 新增 §5 反思循环（项级三行反思每个队列项收尾必做：试了什么 / 看到什么信号含阴性 / 下一步假设；深度反思 R=2 轮上限，四步复盘 → 归因 → 修正计划 ≤3 条 → 小批试错，猜测探针不豁免证据先行；类级信号跨项复用，结论强制落盘）；HackingBuddyGPT 有限步数 → 队列项 budget（15 探针或 20 分钟先到为准，防单资产吃光时间盒）；CAI 双模式 → mission 块 `mode` 字段（full / checkpoint，接力不重问）；硬停 / 终局 / 接力顺延 §6–§8
- 新增 [`methodology/11-fullauto-pipeline.md`](references/methodology/11-fullauto-pipeline.md)：全自动无人值守整站管线——scope.md mission 块一次性授权（缺项才问一次）、hunt 队列按原型路由自动生成（parked 探针主队列清空后补跑）、异常自愈四级不停机（WAF 限流 → 卡壳换路 → candidate 差分自动确认 → 节流错峰）、复现复核轮交叉执行、仅 4 类硬停（出 scope / 授权疑问 / 时间盒用尽 / 工具全挂）、终局一次性输出覆盖率矩阵 + 台账 + docx 草稿 + 人工终审清单（提交永远人工）、跨会话接力靠 state.json；SKILL.md Phase 1 增加全自动模式入口，触发词同步
- 校对轮：对照 AntiDebug_Breaker README 原文逐条核验 §9 判据，三处措辞精确化（eval 作用域报错适用面 / 时间差检测特征不仅限三种 / hook close·history 口径），§8 补清守卫作用域（仅 beforeEach + beforeResolve）、清跳转仍跳排障、"未检测到 Vue Router ≠ 非 Vue"注记，补 SpiderDemo 靶场
- 吸收 [AntiDebug_Breaker](https://github.com/0xsdeo/AntiDebug_Breaker)（0xsdeo，404 星链）：`methodology/07-js-recon.md` 新增 §9 反调试突破与运行时 Hook——反调试信号识别表（无限 debugger / console 清除重写 / 关页跳转 / 时间差 / 尺寸检测）、AntiDebug_Breaker 插件开关映射 + 无插件手动兜底、CryptoJS / JSEncrypt / 国密 SM2/3/4 加密参数重放链（前端加密不是鉴权）、运行时观察 hooks；§8 Vue 插件行同步
- 实战会话 +2条（logic-flaws §3.3 新增"空会话验证码"ASP GetCode 模式，注册+登录双口实测绕过）
- 实战会话 +2条（02 §2.1 "先画像再选技"过滤器画像法；path-traversal switch 分发签名；compliance 补支付网关 scope 规则；logic-flaws 空会话验证码适用面扩展至全部 verifycode 口）

- **云安全子 playbook**（`playbooks/cloud/`，5 文件）：云授权项目 Intake 增量、控制面暴露识别、IAM/RAM/CAM 提权、对象存储深挖、K8s 黑盒入口；含 14 条 H1 云案例与 WSTG/CWE 映射
- **6 个 nuclei 云初筛模板**；顺带修复全部既有模板 description 的 YAML 引号问题（此前 nuclei 实际无法加载）
- payloader 云安全 4 → 9 条（新增国内云元数据 / 对象存储错配 / 凭据验证 / K8s 未授权），payload 总数 305 → 310
- compliance.md 增补云授权红线；SKILL.md Phase 3/4 增加云路由；enterprise-src-hunt 增加云专项交叉引用
- Phase 4 加固：命中后强制三段差分确认 + 同 endpoint 同漏洞类去重抑制（借鉴 CyberStrike 的 3-gate / duplicate suppression）
- 报告模板增加 WSTG / CWE 字段
- 新增多 agent 执行工作流设计稿（`methodology/08-multi-agent.md`，默认关闭，待实战验证）
- 新增 `methodology/09-target-workspace.md`：目标工作区四件套、findings 台账（去重登记簿落地）、**Phase 4 出口检查（覆盖率门闩）**、跨会话续作；Phase 1 checkpoint 增加"建账"项；修复 code-audit 失效引用 → src-audit-chain；补充 jshook 不可用时的回退说明
- 新增 `methodology/10-archetype-routing.md`：七大目标原型（Java 管理面 / SPA+API / 传统站 / 小程序 / 云上 / 官网 / 已有入口）→ 有序 playbook 序列 + 时间盒分配；compliance.md 增补国内法律边界；evidence 增加 sha256 完整性清单
- 仓库自检入 CI：`scripts/validate.py`（链接 / nuclei YAML / 计数一致性）+ GitHub Actions；SKILL 与 enterprise-src-hunt 明确"流程 vs 弹药库"分工；10 号文件时间盒与 05 模板对齐；Phase 5 从台账起草

## 数据来源

- HackerOne hacktivity feed：HackerOne High/Critical 披露报告（原始 2887 + 2026-08 增量共 2951 份唯一案例），来源为公开 hacktivity 数据。
- WooYun 历史档案：覆盖 88,636 条案例，仅保留参数频率、案例 ID 和 bypass 模式等统计残余。
- Payloader：310 条结构化 payload + 176 个原始 WAF / EDR 绕过 payload + 114 条工具命令，原仓库为 `3516634930/Payloader`（云安全 9 条中 5 条为本库编写，见其文件头溯源标注）。
- 外部思路源（`references/sources/`）：仅收录公开站点的检索路由（搜索 URL 格式 / dork 模板 / NVD API 端点），不抓取、不镜像任何社区内容；各站点直连状态为 2026-08-30 实测。

本项目只整理、翻译和重组公开资料，不包含专有数据，也不抓取需要认证的内容。

## 红线

每个 playbook 末尾都写了具体的边界，下面是抽出来的几个最常踩的点：

- **样本控制**：SQLi 探测到库名 / 版本即可证明，不要 dump 数据；IDOR、Mongo / ES 拉数据 1–3 条样本就够，别全量。
- **测试账号自演**：越权、密码重置、JWT 伪造、redirect_uri、XSS 盲打全部用自己注册的两个号互测，**不要碰陌生人的账号**——即使能。
- **只读，不写**：拿到 RCE 只跑 `id` / `whoami` / `uname -a`；Redis / Mongo 默认未授权只 `info` / `ping` / `db.version()`；任意文件读看到 `root:x:` 一行即停，不读 `/etc/shadow`。
- **不真做副作用动作**：不真发短信、不真扣款、不真发邮件、不真退款、不真覆盖文件、不真改公告 / 邮件模板。证明接口能调通 + 200 即停。
- **DoS / 并发**：单次复现 ≤ 60s，串行做 5 次足够。竞态并发 50–100，绝不 1000+。短信 / 邮件不限速这种，发到自己手机 5–10 次为止。
- **不留物**：webshell、heapdump、备份、dump 出来的源码——本地保存，报告后立即删除，不要 push 到 GitHub / 第三方网盘。
- **凭据：拿到不用**：泄露的 AWS / Stripe / 数据库凭据，仅 `sts get-caller-identity` / 看 banner 验证，绝不用来扣款 / 发邮件 / 连接生产库。
- **报告里所有 PII 脱敏**：手机号、邮箱、用户名、token、cookie 留前 2 + 后 2，必要时附 sha256 指纹证明拿到过原文。
- **OOB 验证**：不要使用公开的公共 DNSLog 平台，使用厂商提供的 SSRF 测试平台，或自架 interactsh / 自有 DNSLog。
- **没抓包就没发现**：所有断言都要有 HTTP 包 / 截图 / 视频，不要凭"应该"提交。

具体到每类漏洞还有更细的限制（DoS 类最敏感、上传不留 webshell、读类只读 1 条样本等），看对应 playbook 的最后一节。

## 友情链接
[linuxdo](https://linux.do/)
## License

MIT。

数据来源均为公开资料。本项目主要做资料整理、翻译、归类，并封装成适合黑盒漏洞挖掘使用的 Claude Code skill。
