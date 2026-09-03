# 小程序漏洞报告模板

## 漏洞标题

[小程序名] [接口/功能] [漏洞类型]

示例：XX小程序 用户订单接口 水平越权（IDOR）

## 漏洞等级

- 高危：RCE / 越权获取敏感数据 / 支付金额篡改 / AppSecret 泄露
- 中危：未授权访问普通数据 / 存储型 XSS / 优惠卷复用
- 低危：信息泄露（脱敏）/ 钓鱼加载

## 漏洞类型

API 越权 / 未授权访问 / WebView 白名单绕过 / 敏感信息泄露 / 支付逻辑 / 业务逻辑

## 影响范围

- 小程序名：XXX
- AppID：wxXXXXXXXXXX
- 版本：vX.X.X
- 涉及接口/页面：`/api/xxx` / `pages/xxx`

## 漏洞描述

[一句话说明漏洞本质 + 危害]

## 重现步骤

1. 登录小程序，进入 XXX 页面
2. DevTools Network 抓取请求
3. [具体操作步骤]
4. [参数修改说明]

```
POST /api/xxx HTTP/1.1
Host: api.target.com
Authorization: Bearer <A的token>
Content-Type: application/json

{"userId": "<B的userId>"}
```

5. [预期 vs 实际结果]

## 证据

- [截图1：正常请求响应]
- [截图2：越权请求响应]
- [反编译源码位置：`pages/xxx/xxx.js:42`]

## 修复建议

- [针对性修复建议]

## 反编译源码佐证

```javascript
// 文件: app-service.js:1234
// 接口调用，userId 来自前端无后端校验
wx.request({
  url: 'https://api.target.com/user/order/detail',
  data: { orderId: options.orderId },  // ← 用户可控
  success: function(res) { ... }
})
```
