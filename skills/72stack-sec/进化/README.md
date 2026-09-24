# 发现进化环（Self-Evolving Discovery Loop）

> **不是**无界 Self-Evolving Kill Chain。  
> **是**有闸的经验闭环：实战 DONE / 闸红 / 中危+ → episode → proposal → **安全档自动追加问句** / 其余人审 → 下一席生效。  
> 立法仍认 `~/.grok/rules` + 72stack 红线 / 自动边界。进化**不得**放宽五组、禁写、CORS-不挖、人在环。

## 谁跑

| 角色 | 做什么 |
|------|--------|
| 执行腿 | **禁止**跑进化脚本、禁止改盲区库/skill/rules。只交合格 DONE。 |
| 主控 | **工作流必跑**：收单 / `p2_gate`（默认内挂）/ `mark_covered` → `evolve_hook`；波末扫 pending proposals。 |
| 人 | 审 `dispatch_bias` / `report_checklist` / `done_fix` / hunt-iter；把稳定问句提升进主表。短表只认 hunt-iter。 |

## 工作流焊点（已接）

```text
执行腿 DONE
   → 主控收单（缺号/带出host/卡住对照）
   → p2_gate（默认末步 evolve_hook） ──┐
   → mark_covered（内跑 p2）            ├──→ 任务根 进化/episodes.jsonl + proposals/
   → 显式 evolve_hook --task-root      ──┘
   → evolve_apply --auto-safe（默认）追加 知识库/semantic-blindspots.auto.md
   → 其余 kind / hunt-iter 人审；suspects 头仍须引用（auto 行 ≠ 已引用）
```

- `p2_gate --no-evolve`：例外跳过（默认不要关）。
- `p2_gate --evolve-strict`：进化失败也 FAIL（默认关，避免挡 covered）。
- 跳过进化环 = 编排缺步，不是「可选优化」。
- `evolve_hook --no-auto-safe`：只出 proposal 不追加（默认不要关）。

## 目录

### 任务根（账本旁，可提交进任务夹）

```text
D:\SRC挖洞\{目标}_SRC挖洞\进化\
  episodes.jsonl          # 一行一个 episode（追加）
  proposals\              # 待审提案（md/json）
  applied\                # 已 merge / auto 归档
  auto_probe_recipes.md   # 卡住换路任务内自动层
  STATE.md                # 可选：上次跑时间 / dry-run 记录
```

### 本 skill 树（真源说明 + schema）

```text
进化/
  README.md               # 本文件
  schema.md               # 字段说明
  examples\               # 样例 episode / proposal（无真实 Cookie）
scripts/
  episode_from_done.py
  evolve_propose.py
  evolve_apply.py
```

## 触发（最小集）

| 事件 | 脚本行为 |
|------|----------|
| 扫到 DONE* | 抽 episode 追加 jsonl |
| 报告路径含中危/高危/严重 或 DONE 写「已落盘」 | proposal：盲区库候选 + 回灌提醒 |
| `卡住对照=` 非 N/A瘦壳 且含失败信号 | proposal：探针顺序 / 换路 |
| p2/闸红话术（可选输入） | proposal：NEXT 合规检查提醒 |

## 黑名单（禁止进化自动做）

- 改 `~/.grok/rules` 红线、取消 CORS-不挖、放宽批量/写操作  
- 改 `SKILL.md` / `主控调度.md` / `线程必读.md` / `打穿短表.md` / 主表 `semantic-blindspots.md`  
- 执行腿自 FOFA、自改轨、自过盾  
- 把 payload / Cookie / 真实 PII 写入 episode、proposal 或 auto 层  
- 删行、改假点、改算成门槛

## 与回灌闭环关系

本环 = `知识库/回灌闭环.md` 的**机器助手**：多做结构化记忆与提案，安全档自动追加 `.auto.md` 问句，**不替代** suspects 头引用与 covered 门闩。  
covered 前仍要：中危+ 主表或 auto 层有行、suspects 头引用、P3 自问。

## 命令速查

```bat
cd /d D:\SRC工作区\pi-dig\agent\skills\72stack-sec\scripts

python episode_from_done.py --task-root "D:\SRC挖洞\携程_V3_SRC挖洞"
python evolve_propose.py --task-root "D:\SRC挖洞\携程_V3_SRC挖洞"
python evolve_apply.py --task-root "D:\SRC挖洞\携程_V3_SRC挖洞" --auto-safe --dry-run
python evolve_apply.py --task-root "D:\SRC挖洞\携程_V3_SRC挖洞" --auto-safe
python evolve_apply.py --task-root "D:\SRC挖洞\携程_V3_SRC挖洞" --list
python evolve_apply.py --task-root "D:\SRC挖洞\携程_V3_SRC挖洞" --approve prop_xxx
python evolve_apply.py --task-root "D:\SRC挖洞\携程_V3_SRC挖洞" --apply --id <proposal_id>
```

`--auto-safe` 只追加 `知识库/semantic-blindspots.auto.md`（去重）；默认尝试 git commit **仅该文件**。`--no-git` 跳过。

## 安全句

进化层 KPI = **下一席多问对一句 / 少假 covered**，不是影响半径最大、不是递归自我增强 harness。
