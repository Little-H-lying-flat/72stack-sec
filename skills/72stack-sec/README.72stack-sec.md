# 72stack-sec

面向**已授权 SRC / 漏洞赏金**场景的 AI Agent 军规与技能包。

产品一句话：**语义审计发现引擎 + 三道门闩 + 双轨调度**；payload / 知识模块只是「有靶子才确认」的弹药，不是发现引擎本身。

> 仅用于你拥有书面授权或平台规则明确允许的目标。禁止未授权测试、批量破坏性扫描、内网横向与资损操作。

## 命名对齐（必读）

| 名字 | 指什么 | 不要当成 |
|------|--------|----------|
| **72stack-sec** | GitHub 仓库 / 对外产品名 | 本机 Grok 运行时目录名 |
| **`skills/72stack-sec/`** | 本仓库内的主 skill 源码树 | `~/.grok/skills/` 下的安装名 |
| **`~/.grok/skills/72stack-sec`** | Grok 本机**当前实战安装目录**（与仓库同名 `72stack-sec`） | 与仓库内 `skills/72stack-sec/` 同源 |
| **主控调度.md** | 双轨 / 进号 / spawn / covered 细则 | 写在 `SKILL.md` 里的长文（已抽离） |

线程必读：以本 skill 为主，可叠用其它已安装 skill；对外产品名仍叫 72stack-sec。

## 核心能力

1. **语义发现引擎**  
   表单三问 / 接口三问 → 每站 `suspects.md` 靶子清单；确认只打清单，禁止按百科整站盲扫。
2. **三道门闩**  
   - 覆盖率硬闸：无 `suspects`（或未声明瘦壳 N/A）禁止写 `covered`  
   - 危害 / 证据定性（报告 format）  
   - 约束测试红线（最小伤害、读≤5 组、禁写破坏等）
3. **流水线双轨**  
   未登录轨 `DONE_anon` + 有会话轨 `DONE_auth`；缺号行驱动进号；详见 `主控调度.md`。
4. **开场认法层（短表）**  
   `知识库/打穿短表.md` 只加「对得上就开枪」的认法与假点；禁止扫表凑枪、禁止加成百科。
5. **人工过盾续挖**  
   AI 不过滑块。肥面遇盾写入任务 `资产/人工过盾续挖.md`；人过盾落 cookie → 主控插登录轨。模板：`references/templates/wait-captcha-queue.md`。
6. **账密本（人翻）**  
   进号 / 设密当场写明文：任务内 `资产/accounts.md` + 本机总本 `~/.grok/accounts/账密本.md`（登录网址 / 账号 / 密码）。`auth_flow.py` / `accounts_book.py` 负责落盘。验证码进号密码列写「验证码进号」；设密统一 `register_profile.json` 的 `login_password`。**禁止把账密本 / `register_profile.json` Read 进对话或提交进仓库。**
7. **跨任务记忆**  
   `知识库/semantic-blindspots.md`：命中 / 漏报回灌（不写利用步骤）。
8. **辅助脚本**  
   `pending_from_done.py`、`auth_flow.py`、`accounts_book.py`、`suspects_coverage_check.py`、`report_format_check.py`、`p2_gate.py`（DONE 字段 + 覆盖闸 + 可选验票 / 空席）。

## 仓库结构

```
72stack-sec/
├── README.md                 ← 你正在读的对外说明
├── NAMING.md                 ← 命名对照
├── skills/
│   ├── 72stack-sec/          ← 主 skill（真源：本机 ~/.grok/skills/72stack-sec）
│   ├── miniprogram-hunt/ / wxmini-security-audit/
│   ├── src-audit-chain/ / jsrc-report/
│   └── env-setup/
├── hooks/
├── mcp-servers/
└── sms-bridge/
```

本机 Grok 实战目录：

```
~/.grok/skills/72stack-sec/
├── SKILL.md                  # 红线 + 自动边界 + 指针（薄）
├── 主控调度.md               # 双轨 / 进号 / 过盾 / 台账（厚）
├── 线程必读.md / 开场提示词.md
├── 知识库/                   # 短表认法层 + 模块（对得上再开）
├── references/templates/     # suspects / 过盾队列 / accounts 空表
├── scripts/                  # 进号 / 账密本 / P2 闸 / 报告闸
└── 设计-做强路线.md

~/.grok/accounts/账密本.md    # 人翻总本（gitignore，不进仓库）
~/.grok/skills/72stack-sec/scripts/register_profile.json  # 本机凭据（gitignore）
```

若仓库源与本机安装树暂时不一致：以**本机 `~/.grok/skills/72stack-sec` 实战能力为准**，用本 README 的产品叙事对外；同步策略见 `NAMING.md`。

## 快速开始（授权 SRC）

1. 确认目标在平台公告授权范围内。  
2. 复制 `scripts/register_profile.json.example` → `register_profile.json`，填手机 / 邮箱授权码 / `login_password`（勿提交）。  
3. 主控阅读：`SKILL.md` 红线 → `主控调度.md` → 开场提示词。  
4. 每 host 落 `suspects.md`（模板见 `references/templates/suspects-template.md`）。  
5. covered 前跑：

```bash
python scripts/suspects_coverage_check.py --host-dir "{dig}/{host}"
python scripts/p2_gate.py --dig-root "{dig}" --with-seat --alerts-only
```

6. 进号成功后看：`{任务根}/资产/accounts.md` 与本机 `~/.grok/accounts/账密本.md`。  
7. 中危+ 确认或明确漏报 → 追加一行 `知识库/semantic-blindspots.md`。

## 明确不做什么

- 不提供未授权攻击教程，不把 nuclei 全量扫升为主路径。  
- README / 设计文档不收录利用步骤、payload、PoC。  
- CORS 默认不挖（国内 SRC 价值策略）；具体立法以 `~/.grok/rules` 为准。  
- 不把 `register_profile.json`、账密本、cookie、真号 / 验证码提交进仓库或读进对话。

## License

MIT（见根目录 `LICENSE`）。

## 状态

- P0：suspects 硬闸 + 盲区回灌 + methodology 通读封条  
- P1：`主控调度.md` 抽离、`SKILL.md` 压薄、覆盖率检查脚本  
- P2：`p2_gate` / 验票差分 / 空席巡检；人工过盾续挖；短表开场认法层；账密本（`accounts_book.py` + `~/.grok/accounts`）  
- 本 README：与上对齐（2026-09-11）
