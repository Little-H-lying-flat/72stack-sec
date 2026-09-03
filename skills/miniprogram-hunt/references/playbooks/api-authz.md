# API 越权 / 未授权访问 Playbook

## 攻击面识别

从反编译产物提取所有 API 调用，识别鉴权模型：

```powershell
# 提取所有 wx.request 调用及 url
Select-String -Path "$unpackDir\*.js","$unpackDir\pages\**\*.js" -Pattern 'wx\.request\(' -Context 0,15 |
  ForEach-Object { $_.Context.PostContext + $_.Line } | Out-String
```

**识别信号**：
- `wx.request({url: 'https://api.target.com/user/order/detail', data: {orderId: xxx}})`
- 全局拦截器在 `app-service.js`：`wx.request` 被 wrapper 包装，自动注入 `Authorization` / `token` / `cookie` header
- 用户态 ID 参数：`userId` / `uid` / `memberId` / `orderId` / `addressId` / `cardId`

## 鉴权模型分析

### 1. 全局拦截器定位

```powershell
# 找 wx.request 的全局包装器（通常在 app-service.js 或 utils/request.js）
Select-String -Path "$unpackDir\**\*.js" -Pattern 'wx\.request' -List |
  Select-Object Path | Format-Table -Auto
# 找 header 注入逻辑
Select-String -Path "$unpackDir\**\*.js" -Pattern 'header|Authorization|token|cookie|session' -CaseSensitive:$false |
  Select-Object Path,LineNumber,Line | Format-Table -Wrap
```

### 2. token 来源追踪

```powershell
# token 从哪来
Select-String -Path "$unpackDir\**\*.js" -Pattern 'getStorageSync\(.{0,30}(token|session|auth|login)' -CaseSensitive:$false |
  Select-Object Path,LineNumber,Line | Format-Table -Wrap
```

## 漏洞挖掘路径

### 路径 A：水平越权（IDOR）

**source**：用户可控的 ID 参数（url query / body / path）
**sink**：后端按该 ID 查询资源，未校验归属

**测试**：
1. 账号 A 登录，正常请求获取自己的资源，记录 ID 与 token
2. 改 ID 为账号 B 的资源 ID，用 A 的 token 重放
3. 返回 B 的真实数据 → 确认

**常见 ID 位置**：
- `?userId=` / `?uid=` / `?memberId=`
- `/order/detail?orderId=` / `/address/get?id=`
- POST body `{userId: x, cardId: y}`

### 路径 B：未授权访问

**source**：无 token / 错误 token 直接调接口
**sink**：后端未校验鉴权

**测试**：
1. 从反编译产物拿到 API url 与参数结构
2. 不带 token 直接 curl 调用
3. 返回真实业务数据 → 确认

```powershell
# 无 token 重放
curl.exe -k "https://api.target.com/user/list" -H "Content-Type: application/json"
```

### 路径 C：垂直越权

**source**：普通用户 token 调管理员接口
**sink**：后端只校验登录态，不校验角色

**识别管理员接口信号**：
- url 含 `/admin/` / `/manage/` / `/backend/`
- 接口名含 `delete` / `audit` / `approve` / `reset`
- 反编译产物中权限判断函数：`checkRole` / `isAdmin` / `hasPermission`

## 越权 payload 库

**水平越权 ID 替换**：
```
原: ?userId=10001  →  改: ?userId=10002
原: ?orderId=A2023xxx  →  改: ?orderId=A2023yyy（他人订单）
原: body {"cardId":"111"}  →  改: body {"cardId":"222"}
```

**未授权重放**：
```
去 Authorization header
去 token query 参数
置 Authorization: Bearer invalid
```

**批量 ID 遍历**：
```
userId=10001..10010  逐个请求看返回
orderId 时间戳+序号枚举
手机号遍历（如接口以手机号为 key）
```

## 虚假漏洞排除

- 接口返回 401/403 → 鉴权生效，非未授权
- 返回空壳 data（`{code:0,data:{}}`）但无真实数据 → 可能是空数据兜底，非越权
- 返回脱敏数据（手机号 138****8888）→ 非完整越权，降级处理
- ID 替换后返回 404 → 后端有归属校验，非 IDOR
- 全局拦截器自动带 token，手动 curl 漏带 → 误判，需从 DevTools Network 复制完整请求

## 证据要求

- 账号 A 的 token + A 的 ID → 正常返回（证明 token 有效）
- 账号 A 的 token + B 的 ID → 返回 B 真实数据（证明越权）
- 抓包/DevTools Network 截图保存
