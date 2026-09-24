# 人工过盾续挖队列

> AI **不**过滑块/图形/实名（不 OCR）。遇盾：登录轨 N/A，把**值得进号的肥面**记入本表。  
> 运行时旁路：主控 `login_gate.py`（不占目标席数 10）。见 skill `编排/login_lane.md`。  
> 你本地过盾 → 落 `session.cookie` → 主控开 **auth_exec** 有会话旁路。瘦壳/同皮登录墙 **不要**进表。

## 你怎么续（人）

1. 优先看 `编排/login_offer.md`（gate 当前要约；同时最多 1 个）。无 offer 时再扫本表 `状态=waiting|offered` 且 `优先=高`。
2. 同盾族可共用一次登录（备注写清）。
3. 浏览器过盾拿到会话。
4. 把 cookie 存到 `{dig}/{host}/session.cookie`（优先 Netscape/`curl -b` 能吃的格式；JSON `*_st` 也要在文件里）。
5. `资产/accounts.md` 补一行（目标/通道/cookie路径/备注=人工过盾）。
6. 状态改 `ready`，或对话：`过盾续挖 {host}` / `登录好了 {host}`，或  
   `python scripts/login_gate.py --task-root {根} --confirm-ready --host {host}`
7. 主控：身份一枪（`身份=`+`半径=`）→ spawn `本轨=有会话`（旁路=login_lane）→ 完成后 `done`。
8. 明确没号：`login_gate ... --skip --host {host}` → `skip`/`no_account`。到期未登由 gate 标 `timeout`（冷却后可再要约），**不必**你操作。

## 队列

| host | 盾 | 同盾族 | 优先 | 发码/提交口摘要 | cookie路径 | 进号后主业 | 状态 | 备注 |
|------|----|--------|------|-----------------|------------|------------|------|------|
| （示例）ad.example.com | 滑块 | passport aid=1402 | 高 | POST /passport/web/send_code/ | {dig}/ad.example.com/session.cookie | 对象图/换 id | waiting | auth_flow exit3；未登录已 §4.3 |

**状态：**

| 状态 | 含义 |
|------|------|
| `waiting` | 等人；尚未要约 |
| `offered` | gate 已要约（见 login_offer.md），deadline 内 |
| `ready` | cookie 已落，须插 auth_exec |
| `doing` | 有会话腿进行中 |
| `done` | 本 host 登录轨收口 |
| `timeout` | 要约到期无人；冷却中 |
| `skip` / `no_account` | 人明确放弃/无号 |
| `fail_shield` | 有文件但探活仍未登录 |

## 主控写入规则

- 触发：`auth_flow` 退出 3，或缺号行 `盾=滑块|图形|实名` 且本站判定为**肥面干净口**。
- 同盾族已有一行 waiting/offered → 新 host 只追加「同族」备注或合并到同盾族列，禁止刷屏重复优先。
- 未登录矩阵该做的继续做；本表**不阻塞** 10 席未登录保满，只阻塞「假装有会话」。
- 每回合 `login_gate.py --apply` 先于 `seat_watchdog.py`。
- 飞书员工 / 门神 / 供应商邀约：默认 manual_only，不自动 offer（可手推）。
