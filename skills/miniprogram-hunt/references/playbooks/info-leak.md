# 敏感信息泄露 Playbook

## 攻击面识别

小程序敏感信息泄露三大来源：硬编码、Storage 存储、接口响应过度暴露。

```powershell
# 硬编码密钥/Token/AppSecret
Select-String -Path "$unpackDir\**\*.js","$unpackDir\**\*.json" -Pattern 'secret|appsecret|app_secret|apikey|api_key|accesskey|access_key|password|passwd|token|privatekey|private_key' -CaseSensitive:$false |
  Select-Object Path,LineNumber,Line | Format-Table -Wrap

# Storage 存储点
Select-String -Path "$unpackDir\**\*.js" -Pattern 'setStorageSync|getStorageSync|setStorage|getStorage' |
  Select-Object Path,LineNumber,Line | Format-Table -Wrap
```

## 漏洞挖掘路径

### 路径 A：硬编码密钥泄露

**AppSecret 泄露**（高危）：
```powershell
Select-String -Path "$unpackDir\**\*.js" -Pattern 'appsecret|app_secret|AppSecret' -CaseSensitive:$false
```

小程序 AppSecret 用于签名服务端请求（如 `wx.login` code 换 session）。AppSecret 泄露可：
- 伪造服务端签名调用微信开放平台接口
- 获取用户 openid/session_key
- 解密用户敏感数据（手机号/运动数据等）

**测试**：
1. 反编译产物中找到硬编码 AppSecret
2. 用该 AppSecret + 公开 AppID 构造签名请求到微信 API
3. 成功响应 → 确认

**其他硬编码**：
- 云开发环境 ID：`env: 'cloud-xxx'` → 可能未授权访问云资源
- 第三方 API key：地图/短信/支付密钥 → 滥用或越权
- 数据库连接串（云开发）：直接读写数据库

### 路径 B：Storage 敏感数据存储

```powershell
# 提取所有 setStorageSync 的 key
Select-String -Path "$unpackDir\**\*.js" -Pattern "setStorageSync\(['""]([^'""]+)" -AllMatches |
  ForEach-Object { $_.Matches.Groups[1].Value } | Sort-Object -Unique
```

**危险存储**：
- `setStorageSync('token', xxx)` — token 存本地，若被 XSS 或其他漏洞读取可扩大
- `setStorageSync('password', xxx)` — 密码明文存本地
- `setStorageSync('userInfo', xxx)` — 含手机号/身份证等

**测试**：
1. DevTools Application → Storage 查看 wx 存储内容
2. 确认是否明文存储敏感数据
3. 评估是否有其他漏洞（XSS/WebView）可读取这些数据

### 路径 C：接口响应过度暴露

**source**：API 返回的 JSON
**sink**：响应中包含不必要的敏感字段

**测试**：
1. 正常调用用户信息接口
2. 检查响应字段：是否返回 `password` / `idCard` / `balance` / `appSecret` / 内部状态
3. 接口返回 AppSecret / 内部密钥 → 高危
4. 返回他人手机号/身份证（需配合越权）→ 高危

### 路径 D：云开发未授权

小程序云开发（`wx.cloud`）配置不当：
```powershell
Select-String -Path "$unpackDir\**\*.js" -Pattern 'wx\.cloud|cloud\.' -CaseSensitive:$false |
  Select-Object Path,LineNumber,Line | Format-Table -Wrap
```

**测试**：
1. 反编译产物拿到 `env` 环境 ID
2. 构造小程序或脚本，用相同 env 初始化 `wx.cloud`
3. 调用云函数 / 读写数据库 → 若无鉴权 → 确认

### 路径 E：源码注释 / 调试信息

```powershell
# 注释中的敏感信息
Select-String -Path "$unpackDir\**\*.js" -Pattern '//.*(TODO|test|debug|temp|hack|password|secret)' -CaseSensitive:$false |
  Select-Object Path,LineNumber,Line | Format-Table -Wrap
# 调试 console.log 泄露
Select-String -Path "$unpackDir\**\*.js" -Pattern 'console\.log.*(token|secret|password|key|data)' -CaseSensitive:$false
```

## 虚假漏洞排除

- Storage 中有 token，但接口鉴权不依赖它（用 header Authorization）→ Storage 泄露无直接危害
- 硬编码字符串看似 AppSecret，实际是测试值 / 已废弃 → 需实际请求验证
- 接口返回手机号已脱敏（138****8888）→ 非完整泄露
- 云开发 env 公开，但云函数/数据库有安全规则 → 非未授权

## 证据要求

- 硬编码密钥：反编译源码截图 + 实际请求验证可用
- Storage 敏感数据：DevTools Storage 截图
- 接口过度暴露：抓包响应截图，标注敏感字段
- 云开发未授权：用泄露 env 实际调用成功的截图
