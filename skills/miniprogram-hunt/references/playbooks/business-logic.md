# 支付 / 业务逻辑 Playbook

## 攻击面识别

小程序业务逻辑漏洞集中在：支付、优惠卷/积分、订单、密码重置、提现、活动参与。

```powershell
# 提取支付/订单相关接口
Select-String -Path "$unpackDir\**\*.js" -Pattern 'pay|order|coupon|point|score|prize|withdraw|recharge|transfer' -CaseSensitive:$false -List |
  Select-Object Path | Format-Table -Auto
# 提取金额/数量参数
Select-String -Path "$unpackDir\**\*.js" -Pattern 'amount|price|money|fee|count|num|quantity' -CaseSensitive:$false |
  Select-Object Path,LineNumber,Line | Format-Table -Wrap
```

## 漏洞挖掘路径

### 路径 A：支付金额篡改

**source**：前端提交的金额参数
**sink**：后端直接用前端金额，未二次校验原价

**测试**：
1. 正常下单流程，DevTools Network 抓到支付请求
2. 修改金额参数为 0.01 或负数
3. 支付成功 → 确认

**常见参数**：
- `amount` / `price` / `totalFee` / `money`
- `data: {orderId: xxx, amount: 100}` → 改 `amount: 0.01`
- URL 参数 `?price=100` → 改 `?price=1`

**关键判断**：
- 后端是否调用微信支付统一下单 API 重新生成金额 → 若是，前端篡改无效
- 后端是否校验订单原价 vs 提交金额 → 若否，可篡改

### 路径 B：优惠卷/积分逻辑

**1. 优惠卷复用（并发）**
```powershell
# 找领卷/用卷接口
Select-String -Path "$unpackDir\**\*.js" -Pattern 'coupon|receive|use|exchange' -CaseSensitive:$false -List
```
- 同一优惠卷并发领取多次 → 若无幂等 → 确认
- 同一优惠卷并发使用多次 → 若无校验 → 确认

**2. 积分/余额篡改**
- 前端显示的积分余额是否用于后端扣减校验
- 提现金额是否前端可控

**3. 优惠卷 IDOR**
- `?couponId=100` 改为 `?couponId=101` → 领取他人/未公开优惠卷

### 路径 C：订单逻辑

**1. 订单越权**
- 查看他人订单：`?orderId=xxx` 改为他人订单 ID
- 取消他人订单：账号 A token + 账号 B orderId

**2. 订单状态篡改**
- 前端改 `status` 参数绕过支付直接完成订单
- 改 `quantity` 为负数导致总价为负

**3. 库存并发**
- 限量商品并发下单，超卖

### 路径 D：密码重置

**1. 验证码爆破**
- 短信验证码 4 位 → 暴力枚举（需配合无速率限制）
- 验证码复用：同一 code 多次提交

**2. 重置越权**
```powershell
Select-String -Path "$unpackDir\**\*.js" -Pattern 'reset|password|verify|code|sms|captcha' -CaseSensitive:$false -List
```
- 重置流程 step1 验证手机号 A，step2 提交时改 userId 为 B → 若后端不绑定 → 越权重置

### 路径 E：活动/抽奖逻辑

**1. 抽奖概率篡改**
- 前端控制抽奖结果（`prizeLevel` 参数）→ 后端是否校验
- 抽奖次数无限制 → 无速率限制

**2. 活动参与越权**
- 活动结束前端隐藏入口，接口仍可调 → 后端未校验活动状态
- 活动限购数量前端校验，接口不校验 → 超量参与

### 路径 F：提现逻辑

**1. 提现金额篡改**
- 前端 `amount` 可改为超过余额 → 若后端不校验余额 → 套现
- 负数提现 → 增加余额

**2. 提现地址越权**
- 改 `accountId` 提现到他人账户

## 虚假漏洞排除

- 支付金额前端改了，但后端调微信统一下单 API 重新生成金额 → 篡改无效（微信支付规范）
- 优惠卷领取看似无限制，实际后端有用户维度幂等 → 非复用
- 订单状态前端改，后端按 DB 状态流转校验 → 无效
- 验证码爆破被速率限制拦截 → 非可利用
- 活动接口返回成功但实际资源未发放（空壳响应）→ 非真实漏洞

## 证据要求

- 支付篡改：篡改前后的请求对比 + 实际支付成功截图
- 优惠卷复用：并发请求时间线 + 重复领取成功的响应
- 订单越权：A token + B orderId 返回 B 订单数据
- 密码重置：重置成功后用新密码登录 B 账户成功
