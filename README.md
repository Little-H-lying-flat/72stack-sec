**中文** · [English](README.en.md)

# 72stack-sec

黑盒漏洞挖掘的 AI agent skill——**"带军规挖"**：纪律、门闩、方法论骨架全给，弹药库懒加载，发现与构造交给模型判断。适用于 Claude Code / ZCode / Codex 等可读 markdown 的 agent。

给它一个目标，它按流程推进：确认范围 → 被动侦察 → 资产枚举 → **语义审计找靶子** → 按需查弹药验证 → 危害定性 → 报告。

```text
intake → recon → enum → semantic-audit → hunt → report
                └─ suspects.md(靶子清单) ─┘
```

## 为什么这样设计

四战役产出溯源的结论：~90% 的 findings 来自**结构提取后的语义审视**（"这个 hidden 字段服务端信吗？""这个验证码真的被校验吗？"），payload 库直接命中 ≈ 0。所以本 skill 的核心是 **14-semantic-audit（发现主引擎）**：表单三问 / 接口三问 → `suspects.md` 靶子清单 → 才按 playbook 查确认弹药。payload 盲扫不是打法。

## 三道门闩（全部实战验证）

| 门闩 | 拦截什么 | 实证 |
|---|---|---|
| **gate_check.py 四查硬门** | "假测完"（预算没记账/证据覆盖不全/引用散佚） | 首跑抓出 17 轮未记账 |
| **危害定性门**（三问+下限表+反驳者子代理） | "定级通胀"（confirmed ≠ 有危害） | 20 项复核：受理 7 / 降级 10 / 驳回 3 |
| **零上下文盲测**（可选，默认关闭） | "报告不可复现"（SRC 拒稿头号原因） | 首跑 6/6 PASS 并抓出报告 2 缺陷 |

**门闩分级**：mission 块 `tier: practice`（默认，靶场：四查+语义审计+差分）/ `tier: formal`（平台提交：全套反驳者+盲测+docx）。门闩时间 > 挖洞时间 = 档位用错。

## 零上下文盲测（可选，默认关闭）

把 confirmed 漏洞写成零上下文《AI 待复现报告》，交全新会话的 AI 子代理按报告字面复现——**只测危害定性门受理的项**（驳回/clean 项不是漏洞，不浪费额度）。启动条件：用户明示要求 / findings 将进正式平台提交。执行提示词模板见 [`references/templates/ai-repro-executor-prompt.md`](references/templates/ai-repro-executor-prompt.md)；执行等级三级（subagent 全盲 / 机械脚本 / 自查）必须在结果文件首行标注。实战：testfire 6/6 PASS、aiwadongdemumu 9 项 11 PASS/0 FAIL（抓出报告问题 9 条实时回填）。

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
SKILL.md           入口(102 行:框架+硬约束+流程骨架+路由表)
CHANGELOG.md       完整变更史
scripts/
  gate_check.py    收工完整性四查硬门(--json/--legacy/--no-findings)
  preflight.py     工具矩阵自检(§1.1,--probe-target/--json)
  validate.py      仓库自检(CI 用)
references/
  methodology/     00 索引、01 攻击优先级(含 §3.5 危害定性门)、02 绕过、03 证据纪律、04 控制缺失、05 时间盒、06 2026 打法、07 JS 侦察与反调试、08 多 agent(含 Bypass-Miner)、09 台账、10 原型路由、11 全自动管线(含门闩分级)、12 数据播种、13 接口 fuzz、14 语义审计(表单三问 §1-4 / 接口三问 §5)
  playbooks/       20 类攻击 playbook(含真实 H1 案例)；cloud/ 云安全子 playbook
  industry/        银行/电信垂直
  dictionaries/    国产组件指纹、默认凭据
  templates/       report-format(docx)、ai-repro-executor-prompt、adversary-reviewer-prompt 等
  sources/         外部思路源路由(先知/跳跳糖/PortSwigger/PATT/NVD)
  h1-reports/      HackerOne High/Critical 披露案例(2887+ 增量,按 weakness 分组 146 文件)
  payloader/       310 结构化 payload、176 WAF/EDR 绕过、114 工具命令
```

## 快速上手（全自动模式）

对 agent 说：**"全自动跑完整站 + 目标 URL"**——它按 11 号管线执行：mission 块一次性授权（缺项才问一次）→ preflight 工具矩阵 → 被动侦察 → 结构提取 → 语义审计出 suspects → 按需查 playbook 验证 → 收工跑 gate_check 四查 → 台账交付。报告/台账/证据永不入 git。

## 数据规模

- 结构化 payload 总数 310(含 176 WAF/EDR 绕过)+ 114 工具命令
- HackerOne High/Critical 案例 2951 份（分类索引 2836 条/144 类）
- WooYun 88,636 案例统计残余（参数频率/绕过模式）
- 国产 OA/中间件指纹 + 默认凭据库
- 银行/电信垂直 playbook
- JS 反调试突破 + 加密参数 Hook（CryptoJS/RSA/国密 SM2/3/4）

## 数据来源

- HackerOne hacktivity feed（公开披露数据）
- WooYun 历史档案（仅统计残余）
- Payloader：原仓库 `3516634930/Payloader`
- 借鉴致谢：RefPentester 自反思循环 / HackingBuddyGPT 有限步数 / CAI 双模式 / WindFtsy 门禁与分工思想 / CyberStrike 3-gate 术语（均为思路借鉴，代码自研）

本项目只整理、翻译和重组公开资料，不包含专有数据。

## 红线

每个 playbook 末尾有类型特定红线，最常踩的：

- **样本控制**：SQLi 到库名即停；IDOR 取 1-3 条样本，别全量
- **自演**：越权/密码重置/JWT 全部用自己注册的两个号，不碰真实用户
- **只读不写**：RCE 只跑 `id`/`whoami`；任意文件读看到 `root:x:` 即停
- **不做副作用**：不真发短信/扣款/退款；接口调通即停
- **不留物**：webshell/heapdump 本地保存报告后删除，不 push
- **PII 脱敏**：报告里 token/手机号留前 2 后 2
- **报告/台账/证据永不入 git 远端**

## License

MIT。数据来源均为公开资料。
