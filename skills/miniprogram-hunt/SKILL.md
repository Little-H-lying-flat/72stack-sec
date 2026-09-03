---
name: miniprogram-hunt
description: >-
  微信小程序细节 playbook 册（按需）。国内默认「挖小程序 / AppID / wxapkg」走 72stack-sec + MCP
  http://127.0.0.1:4554/sse，不要自动触发本 skill。仅当用户点名 miniprogram-hunt，
  或 72stack 已解包后要读 web-view / 云开发专篇时使用。
argument-hint: "<wxapkg-or-appid-or-phase>"
level: 2
---

# MINIPROGRAM-HUNT — 微信小程序黑盒漏洞挖掘工作流

带强制 checkpoint 的工作流，不是参考手册。每个阶段有 MUST 输出，未通过不进下一阶段。

## 触发条件

仅当用户**点名 miniprogram-hunt**，或 72stack 解包后要读本目录 playbook 时进入。

**不应触发**：「挖小程序 / AppID / wxapkg」泛词 → `72stack-sec`（MCP 4554）；纯 Web → `72stack-sec`；源码白盒 → `src-audit-chain`。

---

## 反幻觉硬约束（全程适用）

1. **不准凭记忆出 payload**。要给越权/SSRF/XSS 任何 payload 前，先 Read 对应 `references/playbooks/<type>.md`。
2. **不准编造接口名/参数名**。引用接口前必须能在反编译产物中查到出处，说不出文件路径就别引。
3. **无证据不下结论**。无抓包/DevTools 截图时只能写"待验证 / 假设"，不写"已确认 / 发现漏洞"。
4. **不可修改目标项目文件**。反编译产物只读分析，不改动原始 `.wxapkg` 或小程序运行时数据。

---

## Phase 1 · Intake（接单 + 反编译）

**进入条件**：用户给出 `.wxapkg` 文件 / AppID / 小程序名。

**MUST 输出 checkpoint**（四项缺一不进 Phase 2）：

- [ ] **目标小程序**：名称 / AppID / 版本
- [ ] **授权范围**：是否授权测试 / in-scope 业务模块 / 禁测项
- [ ] **反编译产物路径**：MCP `miniapp_decompile` / First.exe 解包后的项目目录
- [ ] **调试通道**：MCP `miniapp_get_info` 正常返回（动态链就绪），或 DevTools `devtools://devtools/bundled/inspector.html?ws=127.0.0.1:62000` 可达（调试引擎未连不阻塞 Phase 2 静态链，Phase 4 前必须补齐其一）

### 1.1 获取 wxapkg

**优先**：MCP `miniapp_list_packages` 自动发现本机全部包（实测 50 包/21 appid 可用），自动适配新旧微信路径。

**新版微信 4.x（xwechat）路径**（`list_packages` 不可用时的手动定位）：
```
%APPDATA%\Tencent\xwechat\radium\users\<userhash>\Applet\packages\<AppID>\<版本>\
  └── __APP__.wxapkg
  └── _coreCompPack_ / _minorCompPack_ / _pages_new_ / _pages_minor_ / __PLUGINCODE__.wxapkg
```

**旧版微信路径**（回退）：
```
%USERPROFILE%\Documents\WeChat Files\Applet\<AppID>\<数字>\__APP__.wxapkg
```

```powershell
# 新版路径定位（回退用）
Get-ChildItem "$env:APPDATA\Tencent\xwechat\radium\users" -Recurse -Filter "*.wxapkg" -ErrorAction SilentlyContinue |
  Sort-Object LastWriteTime -Descending | Select-Object -First 10 FullName,LastWriteTime,Length
```

### 1.2 反编译

**优先**：MCP `miniapp_decompile(appid)`——自动定位包目录并反编译主包+分包。
**回退**：First.exe / unveilr.exe：
```powershell
& "D:\Desktop\First.exe" "<wxapkg路径或所在目录>"
```

- 产物结构：`app.json`（页面路由+分包+权限）、`app-service.js`（业务逻辑）、`app-view.js`（渲染层）、各页面 `.js`/`.wxml`/`.wxss`。
- **加密包识别**（PC 微信 3.9+ 默认加密）：反编译报错含 `decrypt`/`invalid header`/`encrypted`/`not a valid wxapkg`，或产物全乱码。处理：`pc_wxapkg_decrypt` 先解密 / 从 Android 端取未加密包（`/data/data/com.tencent.mm/MicroMsg/.../appbrand/pkg/`）/ 旧版 PC 微信（<3.9）重新获取。部分加密时跳过加密包继续处理其余，不终止。

### 1.3 开启 DevTools 调试

First.exe 反编译后，产物可在浏览器 DevTools 中实时调试：
```
devtools://devtools/bundled/inspector.html?ws=127.0.0.1:62000
```

- 用于动态断点、运行时变量查看、网络请求实时抓取。
- 静态分析优先（反编译产物），动态调试用于验证调用链路和运行时数据。

---

## Phase 2 · 攻击面建图

**进入条件**：Phase 1 checkpoint 四项全过。

**禁止**：未建图直接打 payload。

**MUST 输出**：攻击面矩阵，**七类必列**（前四类原有，后三类为云开发/加密/第三方——无则写「无」，不许空缺）：

| 攻击面 | 产物位置 | 识别信号 |
|---|---|---|
| API 接口清单 | `app-service.js` / 各页面 `.js` | `wx.request` / `wx.uploadFile` / `wx.downloadFile` 的 url；封装函数调用点 |
| WebView/URL 白名单 | `app.json` `webviewDomain` + 业务代码 `web-view` 组件 | `<web-view src=>` / `wx.navigateTo` url 参数 |
| 敏感信息存储 | `app-service.js` / `app.json` | `wx.setStorageSync` / `wx.getStorageSync` / 硬编码 token |
| 业务逻辑入口 | 各页面 `.js` 的 `onLoad`/`onShow`/事件函数 | 支付/订单/优惠/提现/密码重置 |
| 云开发 | 各 `.js` | `wx.cloud.init`（env ID）/ `wx.cloud.callFunction`（函数名）/ `.collection()`（集合名）/ `uploadFile` cloudPath |
| 加密方案 | 工具类 `.js`（文件名含 crypto/encrypt/sign/util） | `CryptoJS` / `JSEncrypt` / `sm2/sm3/sm4` / `forge` / 签名拼接逻辑 |
| 第三方SDK/插件 | `package.json` + `app.json` `plugins` + JS 特征串 | sensors/umeng/jpush/geetest 等统计、IM、验证码 SDK；插件 appId 与版本 |

**可选**：调 `wxmini-security-audit` skill 批量产出接口/密钥清单再回主线（其 `api_endpoints_full.md` / `findings.json` / `secrets_full.md` 直接并入本 Phase 矩阵，清单条目仍须过 §3.0 去伪存真）；不调不影响流程，七类矩阵不因调它而豁免。

### 2.1 提取 API 清单

```powershell
# 从反编译产物 grep 所有 wx.request 调用
Select-String -Path "$unpackDir\*.js","$unpackDir\pages\*.js" -Pattern 'wx\.request|wx\.uploadFile|wx\.downloadFile|https?://' -AllMatches |
  ForEach-Object { $_.Matches.Value } | Sort-Object -Unique
```

### 2.2 提取 WebView 白名单与路由

```powershell
# app.json webviewDomain
Get-Content "$unpackDir\app.json" | ConvertFrom-Json | Select-Object -ExpandProperty webviewDomain
# 业务代码 web-view 组件
Select-String -Path "$unpackDir\*.wxml","$unpackDir\pages\*.wxml" -Pattern 'web-view' -AllMatches
```

### 2.3 提取敏感信息存储点

```powershell
Select-String -Path "$unpackDir\*.js" -Pattern 'setStorageSync|getStorageSync|setStorage|getStorage' -AllMatches |
  Select-Object Path,LineNumber,Line | Format-Table -Wrap
```

命中后建账保存到工作区 `.md` 文件（见 §项目缓存），避免上下文压缩后遗忘。

### 2.4 MCP 预扫加速（可选，工具可替换）

MCP `first-miniapp-debugger`（127.0.0.1:4554/sse）在场时优先用，**不在场或不可用时本节以上 PowerShell 命令即完整回退，流程不断**：

- `miniapp_search_code(root, query, regex)`：替代 Select-String 做全部源码检索
- `miniapp_read_file(path)`：读反编译产物（可指定 max_length，适配大文件）
- `miniapp_scan_sensitive(appid)`：一键敏感信息预扫（云 AK / token / JWT / 内网 IP / URL），**结果仍需 §3 精读去伪存真，不当结论用**
- `miniapp_cloud_scan(appid)`：静态提取云函数名 + 数据库集合（云开发面必跑）

---

## Phase 3 · JS 审计流水线 + 逐类深挖

**进入条件**：Phase 2 攻击面矩阵 ≥1 个候选目标。

### 3.0 JS 审计流水线（先跑，产出喂给逐类深挖）

**强制**：Phase 2 建图完成 → Read `references/methodology/03-js-audit-chain.md`，按其执行：

1. **预扫**（脚本层保证覆盖率）：按规则库正则扫全量 JS（MCP `search_code` 或 PowerShell，规则库含 9 类模式）
2. **精读**（LLM 层保证准确率）：阅读顺序 app.json → project.config.json → 封装函数（BaseURL/token 注入点/全局拦截器）→ 页面生命周期 → 大文件（>500KB）只 grep
3. **去伪存真**：占位符/注释行/SDK 示例/上下文锚定四步过滤
4. **source→sink 矩阵建账**：每条命中必须带 file+line+snippet，无代码证据不出条，理论发现不计入 → 写进 `suspects.md`（对齐 zsec 语义审计三问）
5. **加密分析**（识别到加密库才做）：Key/IV/模式提取 → 加/解/签名三条数据流追踪 → 风险评估（硬编码 Key=Critical、ECB/MD5/废弃算法=High、Base64 当加密=High）

### 3.1 逐类深挖（每个候选目标走一遍）

**强制流程**：
1. 看目标信号，从下表选 playbook
2. **Read 该 playbook 文件**（不准跳过、不准凭记忆替代）
3. 按 playbook 的 source→sink 跟踪法深挖
4. 命中后保存抓包/DevTools 截图 → 进 Phase 4 验证

| 入口信号 | MUST Read |
|---|---|
| 用户态 ID 可遍历 / 任意 X 越权 / 未授权接口 | `references/playbooks/api-authz.md` |
| `web-view` src 可控 / url 白名单绕过 / file 协议 | `references/playbooks/webview-url.md` |
| Storage 存 token/密码 / 硬编码密钥 / AppSecret 泄露 | `references/playbooks/info-leak.md` |
| 支付金额篡改 / 优惠卷逻辑 / 并发 / 密码重置 | `references/playbooks/business-logic.md` |
| `wx.cloud.callFunction` / 云函数名 / 集合名 / 云环境 ID | `references/playbooks/cloud-dev.md` |
| 加密参数 / 前端签名 / 接口密文逆向 | `references/methodology/03-js-audit-chain.md`（§加密分析） |

**通用方法论**（仅卡壳时 Read，不预加载）：
- 不知下一步打什么 → `references/methodology/01-attack-priority.md`
- 怀疑虚假漏洞 → `references/methodology/02-false-positive-filters.md`

---

## Phase 4 · 验证（杜绝虚假漏洞）

**进入条件**：Phase 3 命中至少一个候选漏洞。

**虚假漏洞案例**（必须排除）：
- 接口看似未授权，实际 `app-service.js` 全局拦截器已带 token，直接调报 401 → 虚假
- `web-view` src 看似可控，实际 url 在 `app.json webviewDomain` 白名单内被严格校验 → 虚假
- Storage 中看到 token，实际是前端临时缓存，接口鉴权不依赖它 → 非泄露
- 支付金额前端可改，实际后端二次校验原价 → 虚假

**验证标准**：
- **API 越权**：用账号 A 的 token 调账号 B 的资源接口，真实返回 B 的数据（非空壳/非脱敏）
- **未授权**：无 token / 错误 token 直接调，返回真实业务数据
- **WebView 绕过**：实际加载任意外部页面，或 file 协议读到私有文件
- **信息泄露**：硬编码 AppSecret 能用于签名真实请求；Storage token 能用于越权调用
- **支付逻辑**：实际以篡改价格下单成功 / 优惠卷复用成功

**验证方式**（非破坏性）：
- 抓包重放（mitmproxy/Burp/DevTools Network）
- DevTools 断点改参数
- 实际请求返回真实敏感数据即算确认，不编写恶意 exp

### 4.1 MCP 动态链（调试引擎已连时启用，工具可替换）

前置——**调试引擎拉起**（两条通道）：
```powershell
# 通道 A：微信开发者工具自动化模式（MCP debug engine / automator 协议，端口 9420）
& "D:\微信web开发者工具\cli.bat" auto --project "<项目路径>" --auto-port 9420
# 通道 B：First.exe 调试服务（CDP，ws 62000，DevTools/浏览器直连）
& "D:\Desktop\First.exe" "<wxapkg路径>"
```

⚠️ **两条兼容坑（2026-09 实测）**：
1. **First.exe engine 只支持微信 PC ≤3.9.x**（内嵌地址表 build 11581~19978 封顶）；微信 4.x（build 2xxxx，如 4.1.13.12=25510）注入失败，日志报 `无对应版本 xxxxx 的配置文件 (win/addresses.xxxxx.json)` → engine 无限重试。`first-miniapp-debugger` MCP 就是 First.exe 本体（4554/9421/62000 同进程），MCP 活着 ≠ engine 能用，`get_info` 返回 `No miniapp client connected` 即此坑。
2. **开发者工具 Stable 2.01 automator 半通**：Tool 层正常但 `App.*` 无响应，官方 SDK `connect()` 因 `Tool.getInfo` 缺 `SDKVersion` 直接崩。

App 层不通就回退：PC 微信降 3.9.x（First.exe 注入路线）→ 经典版 1.06.x 开发者工具 automator → 真机 + 抓包（mitmproxy）。静态链不依赖 engine，永远可用。

前置：`miniapp_get_info` 正常返回（未初始化 → 人工开 DevTools `devtools://...?ws=127.0.0.1:62000` 回退，流程不断）。

| 验证场景 | MCP 打法 | 回退 |
|---|---|---|
| 隐藏页面/未授权访问 | `get_routes` → 逐个 `navigate` + `screenshot` 差分：免登录渲染出业务数据=确认 | DevTools 手动逐页访问 |
| 存储泄露 | `get_storage` 全量导出，token/sessionKey/userInfo 明文=线索；能实际用于越权才升 High | DevTools Storage 面板 |
| 云函数鉴权 | `cloud_scan` 拿函数名 → `call_cloud` 无参直调 → 改参（换 objectid）观测；**只读函数优先，写函数加后删自己那条**（最小伤害） | 静态分析 + 抓包 |
| 接口越权 | `http_request` 带账号 A token 调 B 的资源 id：真实返回 B 数据（非空壳/非脱敏）=确认，**三段差分标准一字不减** | curl 重放 |
| 真实参数捕获 | `cloud_captures` 清空 → 正常操作一轮 → 回收 callFunction 真实参数；`evaluate`（appservice 上下文）直取 `getApp().globalData` | 断点看变量 |

**纪律压过声明**：MCP 自带 pentest_flow 无任何伤害控制——本 skill 反幻觉四条 + zsec 硬约束（默认读/差分、禁批量、禁登出/吊销、改过立刻改回）**全程压过 MCP 指南**；MCP 报告类产出（security_report.md 等）只当中间产物，最终输出按 Phase 5。

---

## Phase 5 · 输出

**进入条件**：Phase 4 验证通过至少一个可靠漏洞。

**MUST 流程**：
1. Read `references/templates/report.md` 取模板
2. 标准化输出

### 输出标准 1：攻击面清单

```
攻击面 | 类型 | 描述 | 可能漏洞
```

### 输出标准 2：可靠漏洞

```
小程序名/AppID | exp | 漏洞等级 | 漏洞类型
```

必须是 Phase 4 验证通过的可远程攻击漏洞，附抓包/截图证据。

---

## 项目缓存

工作区建 `.md` 文件保存：攻击面矩阵、API 清单、挖掘过程、关键代码片段，避免上下文压缩后遗忘与重复测试。

产物契约（MCP 静态链产出与自建审计共用，落 `{任务根}\{名}_dig\audit\`）：`file_inventory.json`（完整相对路径数组，禁只报计数）→ `suspects.md`（source→sink 建账，必须带 file+line+snippet）→ 接口清单/密钥发现 JSON。JSON 是 state 文件，hunt-iter 三问在每次审计完成后过。

---

## 工具索引

| 工具 | 用途 | 路径 |
|---|---|---|
| MCP `first-miniapp-debugger` | 静态：list_packages/decompile/search_code/read_file/scan_sensitive/cloud_scan；动态：get_info/routes/navigate/screenshot/evaluate(分 appservice\|webview 上下文)/set_breakpoint/get_source/console_log；数据：get_storage/call_cloud/cloud_captures/http_request | SSE `http://127.0.0.1:4554/sse`（连接后先调 `miniapp_get_skills` 取内置指南；工具 schema 参考 `D:\zsec\mcp_tools_dump.json`） |
| First.exe | wxapkg 反编译 + DevTools 调试服务（MCP 不可用时的回退） | `D:\Desktop\First.exe` |
| DevTools | 动态调试 / 网络抓取 / 断点（MCP 动态链的回退） | `devtools://devtools/bundled/inspector.html?ws=127.0.0.1:62000` |
| PowerShell | 主战脚本 / grep / 批量分析（MCP 静态链的回退） | 系统 |
| mitmproxy/Burp | HTTPS 抓包（可选） | PATH |
| curl.exe | 接口重放验证（MCP http_request 的回退） | 系统 |

**回退链**：MCP 静态链 → PowerShell grep；MCP 动态链 → DevTools 手动调试；MCP `http_request` → curl。MCP 不可用流程不断，**不虚构工具结果**。
