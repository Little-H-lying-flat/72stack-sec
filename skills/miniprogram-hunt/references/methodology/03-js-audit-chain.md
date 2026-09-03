# JS 审计流水线 — 脚本预扫 × LLM 精读双层方法论

> Phase 3.0 的 MUST Read。核心原则：**脚本保证覆盖率，你保证准确率**——正则预扫兜底"没漏"，人工精读负责"去伪存真、上下文关联、source→sink 建账"。
> 反幻觉铁律不变：无 file+line+snippet 证据不出条；无抓包/运行时证据只能写「待验证」。

## 1. 精读顺序（成本从低到高）

| 顺位 | 对象 | 看什么 | 为省什么 |
|---|---|---|---|
| 1 | `app.json` | pages/subpackages 全量路由、plugins、permission、`requiredPrivateInfos` | 隐藏页面（admin/debug/test/backdoor/secret/superadmin 关键字）+ 孤立页面（声明了但无任何 navigateTo 引用且不在 tabBar） |
| 2 | `project.config.json` | `urlCheck:false`、appid、setting | 调试配置残留 |
| 3 | 请求封装函数所在文件（`utils/request.js` 类） | BaseURL 常量（多环境 dev/test/prod 分辨）、token 注入点、全局响应拦截器 | **Phase 4 虚假漏洞判定关键证据**：接口"看似未授权"实际全局带 token，须在此确认 |
| 4 | 页面生命周期 `onLoad`/`onShow`/事件函数 | 业务入口、options 参数接收、跳转逻辑 | 业务逻辑面 |
| 5 | 大文件（>500KB，vendor/主逻辑包） | **只 grep 不通读**，命中后读前后 30 行 | 上下文预算 |

## 2. 预扫规则库（脚本层，9 类）

MCP `miniapp_search_code(root, query, regex)` 或 PowerShell `Select-String` 逐类执行：

| 类 | 关键模式 |
|---|---|
| 接口 | `wx\.(request\|uploadFile\|downloadFile)`、`https?://`、`/(api\|v\d)/[\w/${}]`、封装函数名调用点 |
| 密钥/凭证 | `LTAI\w{12,}`、`(accessKey\|secretKey\|appSecret\|AccessKeyId)`、JWT 三段式 `eyJ\w+\.\w+\.\w+`、`-----BEGIN`、`Bearer\s` |
| 加密 | `CryptoJS\.`、`JSEncrypt\|setPublicKey`、`sm[234]\.(doEncrypt\|encrypt\|doDecrypt)`、`forge\.`、`(AES\|DES\|RC4)`、`(mode\|pad)\s*:`、`md5(\|hex_md5` |
| 云开发 | `wx\.cloud\.(init\|callFunction\|uploadFile\|downloadFile\|getTempFileURL)`、`\.collection\(`、`env\s*:` |
| 存储 | `setStorageSync\(`、key 名 `(token\|session\|password\|userInfo\|openid\|unionid)` |
| WebView | `<web-view`、`src=\{\{`、`navigateToMiniProgram`、`bindmessage\|postMessage` |
| 调试残留 | `debug\s*[:=]\s*true`、`vconsole\|eruda`、`console\.log.*(token\|password\|secret\|key)` |
| 越权线索 | 路径模板 `/(user\|order\|id\|member)/\$\{`、`dataset\.`、URL 拼接中的 id 字段（**不限字段名**，认 zsec 换 id 纪律） |
| 敏感 API（只记事实） | `getUserProfile\|getPhoneNumber\|getLocation\|chooseAddress\|getWeRunData` |

大文件按类分批 grep：≤200KB 可通读；200~500KB 先 grep 后读命中区上下文；500KB~1MB 仅 grep；>1MB 只打 Critical/High 类模式（request/storage/web-view/cloud/payment/admin/debug）。

## 3. 去伪存真（LLM 层，四步过滤）

1. **占位符/示例**：值含 example/demo/test/123456、微信官方示例 appid → 丢弃
2. **注释行**：命中行以 `//` 或 `/*` 开头 → 降级为 Info
3. **上下文锚定**：云 AK 类需邻近出现厂商关键词（`aliyun`/`oss`/`huaweicloud` 等）才认定；`config.js`/`env.js` 里 `const SECRET = "..."` 优先当真
4. **同文件批量读**：同一文件多个命中一次性读相关行，不为每条单独开文件

补充语义扫描（正则会漏的）：`sms`/邮件平台凭证需多行关联、Apollo 配置中心（`apollo`+`meta` 组合）、AK/SK 成对出现的关联标注。

## 4. source→sink 矩阵（建账进 suspects.md）

| source（污点起点） | sink（危险终点） | 漏洞类型 | 对应打法 |
|---|---|---|---|
| 页面参数 `options.*` / `dataset.*` | `wx.request` url 路径/查询含 id | IDOR | 换 id 差分，不限字段名 |
| 页面参数 / 用户输入 | `web-view src` | 任意跳转/钓鱼 | 白名单校验真实性验证 |
| 页面参数 | `navigateToMiniProgram` appId/path | 跳转劫持 | 改参观测目标 |
| 硬编码 Key/IV | 全局加解密函数 | 加密失效 | 泄露 Key 解密重放（§5） |
| storage 中 token | 接口重放 | 会话利用/越权 | A token 调 B 资源差分 |
| 云函数名/集合名 | `wx.cloud.callFunction` | 云函数未授权/参数越权 | 见 `playbooks/cloud-dev.md` |
| 前端价格/优惠计算 | `wx.requestPayment` / 下单接口 | 支付逻辑 | 标记"需后端验证"→ Phase 4 实测 |
| WebView postMessage | 敏感操作函数 | 消息伪造 | 追 bindmessage 处理链 |
| 响应数据 → `setClipboardData` / console 日志 | — | 信息泄露 | 记录级 |

建账规则：每条必须带 file+line+snippet；同一接口多处命中合并记 occurrences；对齐 zsec 语义审计三问（参数服务端信吗 / 声明鉴权真在吗 / 数据流去哪）；**理论发现不计入**。

## 5. 加密分析（识别到加密库才做）

### 5.1 参数提取

对每个加密调用提取：算法与模式（AES/DES/RSA/SM2/SM4 + ECB/CBC/GCM + Pkcs7/Zero）、Key（硬编码值/动态生成逻辑 + 编码格式 UTF-8/Hex/Base64）、IV（同上）、公私钥完整 PEM、输出编码。

### 5.2 三条数据流追踪

- **加密流**：用户输入 → 数据组装 → 加密函数 → 编码 → 发到哪个接口哪个字段
- **解密流**：接口响应 → 解码 → 解密函数 → 使用
- **签名流**：参数排序 → 拼接 → 加盐 → Hash → 签名参数（记录算法/排序规则/盐值）

### 5.3 风险评估基线

| 场景 | 级别 |
|---|---|
| Key+IV 均硬编码 / 前后端共用同一密钥 | Critical |
| 仅 Key 硬编码 | Critical |
| ECB 模式 / MD5 存密码 / 废弃算法（DES/RC4）/ Base64 当加密 / 加密但不签名 / 密钥派生=md5(固定串) | High |
| 无随机 IV / 时间戳签名无有效期（重放） | High / Medium |
| RSA 公钥加密（正常）/ 动态 Key 从服务端取 | Info / Medium |

混淆代码按特征字符串识别（不看函数名）；一个方案多接口共用时关联标注。

## 6. 定向深挖（用户点名/抓包线索触发）

| 目标类型 | 打法 |
|---|---|
| endpoint（接口路径） | 定位全部调用点 → 参数表（名/类型/来源/是否加密/前端校验）→ 加密关联 → 请求头 → 响应处理 |
| parameter（参数名） | 正向追踪（赋值来源→处理函数→最终字段）+ 反向追踪（哪些接口用此参数及角色）；来源五类标注：用户输入/页面参数/存储/硬编码/计算值 |
| focus_area（领域） | 支付/认证/泄露/越权/文件/第三方，从矩阵表捞全部相关行补深 |
| burp_info（抓包发现） | **代码层面验证**：用户观察（如 amount 可篡改）→ 查前端有无签名/校验 → 出「代码确认/不一致」结论，不重复抓包 |
| function（函数名） | 定义 → 调用方 → 被调用方 → 调用链图 |

## 7. 工具对应（可替换）

| 步骤 | MCP 工具 | 回退 |
|---|---|---|
| 预扫 | `miniapp_search_code` / `miniapp_scan_sensitive` | PowerShell Select-String + §2 规则库 |
| 读源码 | `miniapp_read_file`（max_length 适配大文件） | Read 工具 / Get-Content |
| 云开发静态面 | `miniapp_cloud_scan` | grep §2 云开发类模式 |
| 产物清单 | `file_inventory.json` 契约（完整路径数组，禁只报计数） | PowerShell 递归统计 |
