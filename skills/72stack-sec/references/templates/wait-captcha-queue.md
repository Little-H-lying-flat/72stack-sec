# 人工过盾续挖队列

> AI **不**过滑块/图形/实名（不 OCR）。遇盾：登录轨 N/A，把**值得进号的肥面**记入本表。  
> 你本地过盾 → 落 `session.cookie` → 主控开有会话轨。瘦壳/同皮登录墙 **不要**进表。

## 你怎么续（人）

1. 只挑表里 `状态=waiting` 且 `优先=高` 的 host（同盾族可共用一次登录时在备注写清）。
2. 浏览器过盾拿到会话。
3. 把 cookie 存到 `{dig}/{host}/session.cookie`（优先 Netscape/`curl -b` 能吃的格式；JSON `*_st` 也要在文件里）。
4. `资产/accounts.md` 补一行（目标/通道/cookie路径/备注=人工过盾）。
5. 把本行 `状态` 改成 `ready`（或对话说「过盾续挖 {host}」）。
6. 主控：身份一枪（`身份=`+`半径=`）→ spawn `本轨=有会话`；完成后改 `done`。

## 队列

| host | 盾 | 同盾族 | 优先 | 发码/提交口摘要 | cookie路径 | 进号后主业 | 状态 | 备注 |
|------|----|--------|------|-----------------|------------|------------|------|------|
| （示例）ad.example.com | 滑块 | passport aid=1402 | 高 | POST /passport/web/send_code/ | {dig}/ad.example.com/session.cookie | 对象图/换 id | waiting | auth_flow exit3；未登录已 §4.3 |

状态：`waiting`（等你过盾）| `ready`（cookie 已落）| `doing` | `done` | `skip`（放弃进号）

## 主控写入规则

- 触发：`auth_flow` 退出 3，或缺号行 `盾=滑块|图形|实名` 且本站判定为**肥面干净口**。
- 同盾族已有一行 waiting → 新 host 只追加「同族」备注或合并到同盾族列，禁止刷屏重复优先。
- 未登录矩阵该做的继续做；本表不阻塞换席，只阻塞「假装有会话」。
