# 登录旁路（login_lane）

> 有盾进号的人在环旁路：**不占目标席数 10**（与升链同级溢出）。  
> 真源：`资产/人工过盾续挖.md`。  
> 期1 编排：`login_gate.py`。期2 本机：`login_ui.py`（通知 / 弹浏览器 / 等 cookie）。  
> 执行腿 **禁止** 跑本组件、禁止改过盾表。AI **不** OCR、不拖滑块。

## 完整闭环（成功结束）

```text
login_gate --apply
    → waiting 要约 offered（≤wait_max）→ login_offer.md
    → [期2] login_ui --watch（默认 --auto-cookie）
         通知你 + **Playwright 专用浏览器窗口**
    → 你过盾登录（AI 不操作）
    → **全量导出 cookie**（含 toutiao 等通行证域）
    → **业务探活一枪**（user/info / check_login…）PASS 才 ready
    → _auth_spawn_batch → 有会话席
    → 主控 spawn 本轨=有会话（旁路，不占 10）
    → DONE_auth → gate 收 done
```

失败合法终态：`timeout`（到期）/ `skip`（你没号）/ `fail_shield`（cookie 无效）。

**seat_watchdog 只管 seats 1–10 未登录保满。** 顺序：先 `login_gate`，后 `seat_watchdog`。

## 默认参数

| 键 | 默认 | 含义 |
|----|------|------|
| `enabled` | 1 | 0=整条关闭（只未登录） |
| `wait_max` | 1 | 同时 offered 上限 |
| `exec_max` | 2 | 同时有会话旁路上限 |
| `deadline_min` | 12 | 要约时限（分钟） |
| `cooldown_timeout_h` | 6 | timeout 冷却 |
| `notify_on_offer` | 0 | 1=gate apply 新要约时自动 `login_ui --once` |
| `probe_required` | 1 | cookie 后必须业务探活才 ready（P0） |
| `manual_only` | 飞书员工/门神/供应商… | 不自动 offer |

任务根覆盖：`编排/login_lane.json`。

## 命令

```bat
cd /d D:\dsh-72stack-sec\skills\72stack-sec\scripts

rem —— 期1 编排 ——
python login_gate.py --task-root "D:\SRC挖洞\字节跳动_V3_SRC挖洞" --apply
python login_gate.py --task-root "…" --apply --notify

rem —— 期2 本机（你在本机跑）——
rem 推荐：自动开窗 + 自动抓 cookie
python login_ui.py --task-root "…" --watch --force-notify
rem 或双击 login_ui_watch.cmd

rem 仅通知/系统浏览器（不自动抓）
python login_ui.py --task-root "…" --once
python login_ui.py --task-root "…" --watch --no-auto-cookie

rem 后备：手拷 Cookie 头
python login_ui.py --task-root "…" --watch --import-header "sessionid=...; ..."
python login_gate.py --task-root "…" --import-header --host HOST --header "a=1; b=2"
python login_gate.py --task-root "…" --skip --host HOST
```

### 你怎么交 cookie

1. **默认自动（推荐）**  
   `login_ui.py --watch` → 弹出 **Chromium 专用窗** → 你登录 → 脚本侦测到会话 cookie 后 **自动写入** `session.cookie` 并 `confirm-ready`。  
   登录完也可在终端按 **D/Enter** 立刻导出；**S** = skip。
2. **后备手拷：** DevTools 复制 Cookie 头 → `--import-header "a=b; c=d"`
3. **文件：** Netscape 导出 → `login_gate --import-cookie --file ...`

> 为什么不能静默读你日常 Chrome？系统浏览器 cookie 加密/锁定，且不能在你不知情时读登录态。专用窗 = 你显式登录 + 自动导出，合规可控。

## 产物

| 路径 | 内容 |
|------|------|
| `编排/login_jobs.jsonl` | job 运行时 |
| `编排/login_offer.md` | 当前要约（人看） |
| `编排/login_ui_state.json` | 已通知去重 |
| `编排/auth_seats.md` | 有会话旁路席 |
| `编排/_auth_spawn_batch.json` | spawn 有会话 batch |
| `编排/auth_seat_prompts/` | prompt 文本 |

## 与其它脚本

| 脚本 | 关系 |
|------|------|
| `login_ui.py` | 期2 通知/弹窗/等 cookie |
| `seat_watchdog.py` | 后跑；不管 login |
| `closure_debt.py` | offered/timeout/ready 债 |
| `ready_resume_check.py` | ready 须 NEXT 或 auth batch |
| `auth_flow.py` | 无盾干净口；不进本旁路 |

## 退出码

### login_gate
- 0：无待办  
- 1：有 offer / timeout / 待 auth spawn  
- 2：参数

### login_ui
- 0：ready 成功或无要约  
- 1：timeout / confirm 失败  
- 2：参数  
- 3：用户 skip（S）
