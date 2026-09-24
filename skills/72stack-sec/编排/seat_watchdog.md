# 席位看门狗（seat_watchdog）

> 治 **假满席**：腿已 DONE、seats 仍 doing、主控不在线 → 整场像停机。  
> 本组件把「收尸 → 放席 → 填 pending → 写出 spawn 提示」焊成**可 cron/主控每回合必跑**的脚本。  
> 脚本默认不自己开腿。写出 `编排/_spawn_batch.json` + `seat_prompts/`。主控按 batch 用 **`spawn_subsession`** 开子对话（禁止 `spawn_session` 开新席），然后 `yield_to_subsessions`。

> **不管登录旁路。** 有盾要约 / timeout / `_auth_spawn_batch` 由 **`login_gate.py`** 负责（见 `login_lane.md`）。主控每回合 **先 gate 后 watchdog**。本组件只保目标席数内的未登录（及历史已占 seats 的轨），**禁止**把 auth_wait 填进 seats 1–10。

## 闭环

```text
seats.md doing
    │
    ├─ dig/{host}/DONE_anon|DONE_auth 已存在 ──→ 收尸：状态=done，清 sid
    │                                              leftover 表行 doing→done（尽力）
    ├─ 无 DONE 且 dig 目录 mtime > stall 分钟 ──→ 标记 recycle（重派或备注超时）
    │
    └─ 空席 / 已收尸席
            │
            └─ leftover pending（非 cdn/登录墙策略）──→ 填 seats doing
                                                      写 seat_prompts + _spawn_batch.json
                                                      更新 NEXT.md = 补席
```

## 谁跑

| 角色 | 动作 |
|------|------|
| 主控每回合开头/收单后 | `python seat_watchdog.py --task-root {任务根}` |
| cron / 外挂（可选） | 同上 `--apply`；spawn 由外挂读 `_spawn_batch.json` |
| 执行腿 | **禁止**跑 watchdog、禁止改 seats |

## 命令

```bat
cd /d D:\dsh-72stack-sec\skills\72stack-sec\scripts

python seat_watchdog.py --task-root "D:\SRC挖洞\小红书_V3_SRC挖洞" --dry-run
python seat_watchdog.py --task-root "D:\SRC挖洞\小红书_V3_SRC挖洞" --apply
python seat_watchdog.py --task-root "…" --apply --stall-minutes 45 --max-seats 10
python seat_watchdog.py --task-root "…" --apply --set-sid 3=01a0cd37-xxxx
```

## 与其它脚本

| 脚本 | 关系 |
|------|------|
| `login_gate.py` | **先跑**；登录旁路不占 10；本组件不读 login_jobs |
| `seat_stall_check.py` | 只读告警；watchdog **动手** |
| `evolve_hook.py` | 收尸后可 `--evolve` 顺带跑（默认开） |
| `p2_gate` / `mark_covered` | 不管 seats；covered 仍走焊闸 |
| `mark_covered` | 瘦壳 covered 后 leftover/done 由主控或 watchdog 收尸对齐 |

## 不做什么

- 不发码、不 FOFA、不改 covered_hosts  
- 不把 CDN/cold 填进席位（备注含 cdn/图床/71edge/xhscdn 等跳过）  
- 默认不把纯登录墙 host 优先填席（备注含 SSO/登录墙 且策略 `--prefer-biz`）  
- 不替代人在环高危拟进  

## 退出码

- 0：无动作或已成功 apply  
- 1：有收尸/待 spawn（dry-run 时也 1，方便主控发现「该补席」）  
- 2：参数/无 seats
