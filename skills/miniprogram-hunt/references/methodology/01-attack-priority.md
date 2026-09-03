# 攻击优先级决策

当 Phase 2 攻击面建图完成但不知先打哪个时，按以下优先级排序：

## 优先级矩阵

| 信号 | 优先级 | 原因 |
|---|---|---|
| 硬编码 AppSecret / 云开发 env | P0 | 直接可利用，危害最大 |
| 接口无鉴权拦截器 | P0 | 直接未授权访问 |
| web-view url 来源可控 | P1 | 可能加载任意外部页面 + JSBridge |
| 用户态 ID 可遍历 | P1 | 水平越权，直接拿数据 |
| 支付金额前端可控 | P1 | 直接经济危害 |
| 优惠卷并发无幂等 | P2 | 需并发测试 |
| Storage 敏感数据 | P2 | 需配合其他漏洞利用 |
| 活动抽奖概率前端控 | P2 | 需实际验证后端是否校验 |
| 调试 console.log 泄露 | P3 | 信息泄露，低危 |

## 决策流程

1. **先看鉴权**：全局拦截器是否存在？哪些接口绕过拦截器直接调 `wx.request`？→ 优先打这些
2. **再看密钥**：硬编码 AppSecret / 云开发 env 存在吗？→ 存在就 P0
3. **再看用户态 ID**：接口参数含 userId/orderId 等可遍历 ID？→ 优先 IDOR
4. **再看 WebView**：web-view 的 url 可控？→ 优先打白名单绕过
5. **最后看业务逻辑**：支付/优惠/提现流程 → 按业务价值排序

## 卡壳信号

- "找不到鉴权拦截器" → 可能在 `app.js` 的 `wx.request` 全局重写，grep `wx.request =` 或 `Request.prototype`
- "找不到 API" → 可能在分包 `pkg-*.js`，检查 `app.json` 的 `subPackages` 分包路径
- "token 来源不明" → 追踪 `login` / `wx.login` / `wx.getUserInfo` 调用链
