# WebView / URL 白名单 Playbook

## 攻击面识别

微信小程序的 WebView 攻击面来自 `<web-view>` 组件加载外部页面：

```powershell
# 提取所有 web-view 组件
Select-String -Path "$unpackDir\**\*.wxml" -Pattern '<web-view' -AllMatches |
  Select-Object Path,LineNumber,Line | Format-Table -Wrap
# 提取 app.json 白名单
Get-Content "$unpackDir\app.json" | ConvertFrom-Json | Select-Object -ExpandProperty webviewDomain
# 提取 navigateTo / redirectTo 的 url 参数
Select-String -Path "$unpackDir\**\*.js" -Pattern 'navigateTo|redirectTo|switchTab|reLaunch' -Context 0,5 |
  ForEach-Object { $_.Line + ($_.Context.PostContext -join "`n") } | Out-String
```

**识别信号**：
- `<web-view src="{{url}}">` — url 来自页面参数或接口返回
- `wx.navigateTo({url: '/pages/webview/index?url=' + xxx})` — url 拼接可控
- `app.json` 中 `webviewDomain` 白名单列表

## 漏洞挖掘路径

### 路径 A：白名单域绕过

微信对 `<web-view>` 加载的域名有白名单校验（`app.json webviewDomain`）。绕过点：

**1. 域名校验逻辑缺陷**
- `https://www.target.com` 在白名单 → 测 `https://www.target.com.evil.com` 是否绕过
- `https://target.com` 白名单 → 测 `https://target.com@evil.com`
- 子域通配：白名单 `*.target.com` → 确认 `evil.target.com` 是否可控

**2. 跳转链绕过**
白名单域 A 页面内 `location.href = 'https://evil.com'` 或 `window.open` → 实际加载 evil 页面。

**3. 协议绕过**
- 白名单只校验 https → 测 `http://` 是否被允许
- 测 `javascript:` / `data:` 协议是否被过滤

### 路径 B：url 参数注入

**source**：页面 `onLoad(options)` 的 `options.url` / 接口返回的 url
**sink**：`<web-view src="{{url}}">` 直接渲染

```powershell
# 找 url 参数传递链
Select-String -Path "$unpackDir\**\*.js" -Pattern 'onLoad.*url|options\.url|setData.*url|src.*url' -CaseSensitive:$false |
  Select-Object Path,LineNumber,Line | Format-Table -Wrap
```

**测试**：
1. 找到 webview 页面路由（如 `/pages/webview/index`）
2. 构造 `?url=https://evil.com` 或 `?url=javascript:alert(1)`
3. 若加载外部页面 → 结合 JSBridge 扩大危害

### 路径 C：file 协议 / 本地文件读取

部分小程序 webview 配置不当允许 file 协议：
- `web-view src="file:///data/data/.../shared_prefs/token.xml"`
- `web-view src="file:///etc/hosts"`

微信默认禁止 file 协议，但自定义实现或低版本可能未禁。

### 路径 D：JSBridge 滥用

WebView 内暴露的 JS 接口（`wx.miniProgram.postMessage` / 自定义注入对象）：

```powershell
# 找 JSBridge 注入点
Select-String -Path "$unpackDir\**\*.js" -Pattern 'addJavascriptInterface|window\.|postMessage|invoke|evaluateJavascript' -CaseSensitive:$false |
  Select-Object Path,LineNumber,Line | Format-Table -Wrap
```

**测试**：
1. webview 加载攻击者可控页面
2. 页面内调用 `wx.miniProgram.postMessage` / `wx.miniProgram.navigateBack` 等
3. 若有自定义注入对象（`window.appBridge.xxx`），测能否触发敏感操作

## 虚假漏洞排除

- `<web-view src="{{url}}">` url 看似可控，但 url 在 setData 前被白名单校验函数过滤 → 虚假
- 白名单严格，`@` / 子域绕过都 403 → 非绕过
- `javascript:` / `data:` 协议被微信运行时过滤 → 虚假
- file 协议被微信禁止 → 非漏洞（微信默认行为）
- webview 加载外部页面但无 JSBridge 且不携带小程序鉴权 → 仅钓鱼，低危

## 证据要求

- 实际在 webview 中加载任意外部页面（截图）
- 或 file 协议读到私有文件（截图）
- 或 JSBridge 触发敏感操作（截图 + 调用链）
