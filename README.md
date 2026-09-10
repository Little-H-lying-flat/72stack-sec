# 72stack-sec

面向**已授权 SRC / 漏洞赏金**场景的 AI Agent 军规与技能包。

产品一句话：**语义审计发现引擎 + 三道门闩 + 双轨调度**；payload / 知识模块只是「有靶子才确认」的弹药，不是发现引擎本身。

> 仅用于你拥有书面授权或平台规则明确允许的目标。禁止未授权测试、批量破坏性扫描、内网横向与资损操作。

## 命名对齐（必读）

| 名字 | 指什么 | 不要当成 |
|------|--------|----------|
| **72stack-sec** | GitHub 仓库 / 对外产品名 | 本机 Grok 运行时目录名 |
| **`skills/72stack-sec/`** | 本仓库内的主 skill 源码树 | `~/.grok/skills/` 下的安装名 |
| **`~/.grok/skills/skill`** | Grok 本机**当前实战安装目录**（文件夹名就叫 `skill`） | 与仓库内 `skills/72stack-sec/` 同源 |
| **主控调度.md** | 双轨 / 进号 / spawn / covered 细则 | 写在 `SKILL.md` 里的长文（已抽离） |

线程必读：以本 skill 为主，可叠用其它已安装 skill；对外产品名仍叫 72stack-sec。

## 核心能力（与本机 P0/P1 对齐）

1. **语义发现引擎**  
   表单三问 / 接口三问 → 每站 `suspects.md` 靶子清单；确认只打清单，禁止按百科整站盲扫。
2. **三道门闩（概念）**  
   - 覆盖率硬闸：无 `suspects`（或未声明瘦壳 N/A）禁止写 `covered`  
   - 危害 / 证据定性（报告 format）  
   - 约束测试红线（最小伤害、读≤5 组、禁写破坏等）
3. **流水线双轨**  
   未登录轨 `DONE_anon` + 有会话轨 `DONE_auth`；缺号行驱动进号；详见 `主控调度.md`。
4. **跨任务记忆**  
   `知识库/semantic-blindspots.md`：命中 / 漏报回灌（不写利用步骤）。
5. **辅助脚本**  
   `suspects_coverage_check.py`、`pending_from_done.py`、`auth_flow.py`、`report_format_check.py` 等。

## 仓库结构

```
72stack-sec/
├── README.md                 ← 你正在读的对外说明
├── NAMING.md                 ← 命名对照（精简版亦见于上文）
├── skills/
│   ├── 72stack-sec/          ← 主 skill（真源：本机 ~/.grok/skills/skill）
│   ├── miniprogram-hunt/ / wxmini-security-audit/
│   ├── src-audit-chain/ / jsrc-report/
│   └── env-setup/
├── hooks/
├── mcp-servers/
└── sms-bridge/
```

本机 Grok 实战目录（可能由安装/同步脚本落到）：

```
~/.grok/skills/skill/
├── SKILL.md                  # 红线 + 指针（薄）
├── 主控调度.md               # 双轨调度（厚）
├── 线程必读.md / 开场提示词.md
├── 知识库/                   # 短表 + 模块（对得上再开）
├── references/               # 仅显式指针；methodology 默认 ARCHIVE
├── scripts/                  # 覆盖率检查 / 进号 / 报告闸
└── 设计-做强路线.md          # P0/P1/P2 设计备忘
```

若仓库源与本机安装树暂时不一致：以**本机 `~/.grok/skills/skill` 实战能力为准**，用本 README 的产品叙事对外；同步策略见 `NAMING.md`。

## 快速开始（授权 SRC）

1. 确认目标在平台公告授权范围内。  
2. 主控阅读：`SKILL.md` 红线 → `主控调度.md` → 开场提示词。  
3. 每 host 落 `suspects.md`（模板见 `references/templates/suspects-template.md`）。  
4. covered 前跑：

```bash
python scripts/suspects_coverage_check.py --host-dir "{dig}/{host}"
```

5. 中危+ 确认或明确漏报 → 追加一行 `知识库/semantic-blindspots.md`。

## 明确不做什么

- 不提供未授权攻击教程，不把 nuclei 全量扫升为主路径。  
- README / 设计文档不收录利用步骤、payload、PoC。  
- CORS 默认不挖（国内 SRC 价值策略）；具体立法以 `~/.grok/rules` 为准。

## License

仓库描述标注 MIT；若根目录尚未放置 `LICENSE` 文件，请补齐 SPDX 文本后再对外宣称。

## 状态

- P0：suspects 硬闸 + 盲区回灌 + methodology 通读封条  
- P1：`主控调度.md` 抽离、`SKILL.md` 压薄、覆盖率检查脚本  
- P2：本 README / 命名对齐（进行中）
