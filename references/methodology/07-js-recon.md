# JS 侦察 — 前端资产里的 endpoint 与密钥 `js-recon`

> 定位:现代 SPA(React/Vue/Next/Nuxt)的 bundle 是 **endpoint、隐藏路由、密钥的第一来源**。前端的"隐藏"只是 UI 隐藏——路由/接口/权限判断全在 JS 里裸奔。
> 铁律(呼应 06 §5):**前端可见 ≠ 后端允许**。JS 里发现的每个 endpoint 都必须按匿名/低权/越权三层验证后端行为,前端校验是 theater。

---

## 1. JS 资产收集

| 来源 | 手法 |
|---|---|
| 页面内 | 所有 `<script src>`、`link rel=preload/prefetch`、动态 import() |
| 爬取 | katana / hakrawler / gospider 对目标域爬 js;`-js` 类参数保留 js 链接 |
| 历史 | waybackurls / gau 拉**历史快照里的 js**——下线页面的 js 指向未下线的接口,经典金矿 |
| Dork | `site:target.com ext:js` / `site:target.com inurl:.js` |
| 子域联动 | httpx 探活的子域全部过一遍 js 提取(每个 SPA 都是一座矿) |

## 2. Source Map 还原(生产环境忘删 .map = 直接读源码)

```
1. 看 js 尾部: //# sourceMappingURL=app.js.map
2. 直接探测: 对每个 js 加 .map 后缀请求(200 即中)
3. 还原: shuji / unmap / sourcemapper → 还原出原始目录结构与源文件
4. 价值排序: src/api/ 目录(全部接口定义) > src/store(状态与权限逻辑) > src/config(环境配置) > 注释
```

还原出的 api 目录=完整的接口清单,比任何正则都全。**报告注意**:source map 暴露本身多数平台按低危收,但其导出的接口/密钥按实际影响定级。

## 3. Webpack Chunk 遍历

- 命名规律:`app.[hash].js`、`{N}.{hash}.chunk.js`、`static/js/{N}.{hash}.chunk.js`
- 遍历法:从 runtime(manifest)chunk 里拿全量 chunk 映射;或对 chunk id 做数字递增尝试(`1.js`~`500.js`,配合 hash 才有效,无 hash 直接试)
- 框架数据负载:`__NEXT_DATA__`(Next)、`__NUXT__`(Nuxt)——页面级 props 里常有 API base、用户上下文、内部配置
- 路由提取:react-router/vue-router 的路由表是明文数组——**admin/dashboard/internal 等隐藏路由**直接从路由表读,然后逐个验证后端鉴权(路由隐藏≠授权)。Vue SPA 另有一类"JS 里定义了但 router 实例未注册"的动态路由,插件拿不到,见 §8

## 4. Endpoint / 密钥正则清单(对 bundle 直接 grep)

```
# endpoint
/api/[a-zA-Z0-9_/-]+      fetch\(["']       axios\.(get|post|put|delete)
baseURL                    graphql           /v[0-9]/[a-z]+/

# 云凭据(对应 11-cloud.md 接管链)
AKIA[0-9A-Z]{16}                      # AWS
LTAI[0-9A-Za-z]{12,}                  # 阿里云 AK
AKID[0-9A-Za-z]{13,}                  # 腾讯云
AIza[0-9A-Za-z_-]{35}                 # Google API key
sk-[a-zA-Z0-9]{20,}                   # OpenAI 风格 key
ghp_[A-Za-z0-9]{36} / github_pat_     # GitHub PAT
xox[baprs]-                           # Slack token

# 其他敏感物
eyJ[A-Za-z0-9_-]{10,}\.eyJ            # JWT 硬编码
(25[0-5]|10\.|172\.(1[6-9]|2[0-9]|3[01])\.|192\.168\.)  # 内网 IP
https?://[a-z-]+\.(internal|local|corp)[^"']*   # 内部域名
password|secret|token|api[_-]?key      # 配置字段名(再人工核)
```

工具化:gitleaks/trufflehog 思路直接对 bundle 目录跑;LLM 分诊(06 §5)适合做"端点聚类+可疑度排序",人只看 top。

## 5. 第三方与全局配置

- CDN 上的老组件:jQuery <3.5(xss)、老版本 moment/lodash(原型链)——`retire.js` / 指纹比对
- `window.config` / `window.__INITIAL_STATE__`:全局配置常塞内部 RPC 地址、功能开关、灰度配置
- 上传/预览组件的 bucket 地址:转 `11-cloud.md` 的 `cn-object-storage` 打对象存储

## 6. 后端验证矩阵(js-recon 的收口)

| JS 里的发现 | 验证动作 | 出口 |
|---|---|---|
| 隐藏路由 /admin | 匿名直访 + 低权账户访问,看**后端**返回 | 前端隐藏但后端拦→信息泄露(低);后端放行→越权(P1) |
| 未文档化 endpoint | 匿名 OPTIONS/GET 探测 → 带低权 token 测 | 按 BOLA/未授权定级,进 `api-rest/` |
| 硬编码密钥 | 验证有效性(最小请求,如 sts get-caller-identity) | 有效→按云凭据接管链(11-cloud.md) |
| source map | 还原→接口清单回填第 1-3 步 | 循环放大,直到无新 endpoint |

## 7. 流水线示例

```
katana -u https://target -d 3 -jc | grep -oE 'https?://[^" ]+\.js' | sort -u > js.txt
while read u; do curl -s "$u" -o "js/$(echo $u | md5sum | cut -c1-8).js"; done < js.txt
grep -rhoE '(AKIA[0-9A-Z]{16}|LTAI[0-9A-Za-z]{12,}|/api/[a-zA-Z0-9_/-]+)' js/ | sort -u
# → 人工/LLM 分诊 → 后端验证矩阵
```

## 8. Vue SPA 路由最大化(已加载 vs 未加载路由)

> 适用:Vue 2/3 + vue-router 后台系统。核心认知:**Vue Crack / vue-devtools 类插件调的是 `getRoutes()`,只返回"已加载"路由**。做权限分离的后台(典型如 JeeSite)实例化 router 时只注册 `/login`、`/tokenLogin`;`/dashboard`、`/system` 等业务路由在 JS 里 component 都写好了却未注册,登录后由路由守卫按角色 `addRoute()` 动态补——未授权状态下插件看不见、直访 404。

**第一步:差集法找出"定义了但未加载"的路由**

| 步骤 | 动作 |
|---|---|
| 1 | 插件 / 控制台 `getRoutes()` 存档 = 已加载集 |
| 2 | 全量 js bundle 提取路由定义(findsomething 或直接 grep,正则见下) |
| 3 | 差集 = JS 里有、getRoutes() 没有 → 未加载路由,通常正是权限分离藏起来的后台模块 |

```
path:\s*['"]\/[a-zA-Z0-9_:\/-]+['"]
name:\s*['"][A-Za-z][A-Za-z0-9]*['"]
component:\s*\(\)\s*=>\s*import\(['"][^'"]+['"]\)
```

**第二步:手动加载未加载路由(无可靠自动化)**

| 方案 | 操作 | 缺陷 |
|---|---|---|
| addRoute | 控制台 / 改 js 拿 router 实例 → `addRoute(路由对象)` | 须实际访问一次该路由触发解析后,`getRoutes()` 才返回 |
| 塞路由表(推荐) | 改 js,把未加载路由对象并进 `createRouter({routes:[...]})` 的路由表再实例化 | 一次改完,插件直接可见全部路由 |

自动化止步于差集清单:模块化 import 的路由定义在模块局部作用域,油猴注入拿不到;后端接口返回路由表的方案同理。加载这步必须手动改 JS。

**第三步:进了路由被弹回 /login(路由守卫)三解法**

- hook router 的 `push / replace / go` 三个方法——改 js 在 createRouter 之后直接置空最稳
- 白名单伪造:把目标路由塞进路由守卫的 whitelist 数组——**前提是该路由已加载**,未加载路由改白名单照样 404,仍要走第二步
- 插件:[AntiDebug_Breaker](https://github.com/0xsdeo/AntiDebug_Breaker)(获取路由 / 清跳转 / 清守卫——**仅全局前置 beforeEach + 全局解析 beforeResolve** / 激活 Vue Devtools / React 路由;Vue2 配 devtools v5、Vue3 配 devtools,两个 devtools 不能同开)——完整反调试与加密 Hook 能力表见 §9
- 插件清跳转后仍跳:站点调的可能不是 vue router 的跳转方法(→ 开 hook close / hook history,或 §9 通杀方案定位跳转函数后置空),也可能脚本注入前就已完成跳转(→ 手动替换 js)
- 插件未检测到 Vue Router ≠ 不是 Vue 站点——只能说明站点没使用 vue-router,路由提取回退 §8 差集法

**多 router 实例**:一个页面可挂多个 Vue 实例、多个 Router;有的插件扫到一个 Vue 实例就 return,漏掉真正挂 router 的那个——验证时遍历全部实例。

**收口**:路由能进 ≠ 后端放行。所有加载出的路由按 §6 验证矩阵打——匿名直访 + 低权 token 看接口行为;路由可达 + 接口未授权 = P1 链(进 `arbitrary-x-authz.md`)。

## 9. 反调试突破与运行时 Hook(挡在"分析"与"重放"前面的第一堵墙)

> 适用两类卡点:① 目标 JS 开了反调试,DevTools 打不开 / 一打开就跳转关页——§1–§5 的分析全被挡;② 接口参数是密文(sign / token / encryptData / aes),不会生成就没法伪造重放——§6 验证矩阵跑不了。**核心认知:前端加密不是鉴权**——Hook 拿到明文+算法只是起点,伪造请求打过去后端是否真校验才是漏洞本体。

### 9.1 信号 → 防护类型识别

| 现象 | 防护类型 |
|---|---|
| 页面反复断在 debugger | 无限 debugger(eval / Function / Function.prototype.constructor 三种核心构造方式) |
| 控制台输出被频繁清空 | console.clear 重写 |
| console.log 打不出东西 / 输出被篡改 | console.log 重写 |
| 打开 DevTools 后页面自动关闭 | close 重写检测 |
| 打开 DevTools 后跳回首页或 github.io 类无关页 | location / history 跳转检测;伴随"频繁 clear + 海量 console 输出"特征时属运行时间差检测 |
| DevTools 停靠后页面行为异常 / 报错 | 窗口尺寸检测(innerWidth / innerHeight / outerWidth / outerHeight 差值) |
| 接口参数密文且每次请求都变 | 前端加密 / 签名 → 9.3 |

### 9.2 绕过:首选插件,手动兜底

首选 [AntiDebug_Breaker](https://github.com/0xsdeo/AntiDebug_Breaker)(404 星链计划;基于 Hook_JS 库的 Chrome 插件,商店直装或 chrome://extensions 开发者模式加载未打包)。**使用注意:不支持 Firefox;开/关任何脚本都必须刷新页面才生效;更新时先移除旧版再导入。**各开关练手:官方靶场 [SpiderDemo](https://www.spiderdemo.cn)。

| 插件开关 | 破的是 | 备注 |
|---|---|---|
| 绕过 Debugger | 无限 debugger | hook eval / Function / constructor 三路;**部分**站点因 eval 作用域报错 → 换 Firefox 调(Firefox 本身忽略 debugger 语句);极少数站点有特殊反制(故意引发报错或依旧 debugger),需针对性解决 |
| hook clear / hook log | console 清空 / console.log 重写 | 常需同开 |
| Hook table | 运行时间差检测 | 特征:频繁 clear + 海量 console 输出,随后 location.href 跳转(一般跳 github.io)——**不仅限这三种特征**,按实际判断是否启用 |
| hook close / hook history | 反调试关闭当前页 / 返回上一页或某个特定历史页 | |
| Fixed window size | 窗口尺寸检测 | 固定 innerHeight 660 / innerWidth 1366 / outerHeight 760 / outerWidth 1400 |
| 页面跳转JS代码定位通杀方案 | 一切页面跳转 | CC11001100 方案:阻断跳转留在当前页 + 定位跳转代码位置 |
| Hook CryptoJS / JSEncrypt / SM-crypto | 加密参数 | 见 9.3 |
| Hook 区(cookie/XHR/fetch/storage/JSON/Promise/随机数时间) | 运行时观察 | 见 9.4 |
| Vue / React 获取路由 | SPA 路由 | 只拿**已加载**路由;未加载路由仍走 §8 差集法 |

**手动兜底**(无插件时;AI 协作场景 = AI 出步骤指导用户逐条操作,不虚构操作结果):

| 防护 | 手动破法 |
|---|---|
| 无限 debugger | Sources 面板定位 debugger 语句行右键 → **Never pause here**(最通用);或断到构造点前一层 hook 掉 eval / Function |
| console 清空 / 重写 | 改用断点看变量,不依赖打印;清空类直接 `console.clear = () => {}` 覆写 |
| 关页面 / 跳转 | `window.close = () => {}`;跳转对 location 赋值处下断点(或 Event Listener Breakpoints)后置空 |
| 尺寸检测 | DevTools 独立窗口(undock)先绕开停靠差异;必要时 defineProperty 覆写 innerWidth / outerHeight getter |
| 加密参数 | 9.3 手动模板;须在站点脚本加载**前**注入(控制台来不及 → Tampermonkey `@run-at document-start`) |

### 9.3 加密参数定位与伪造(密文重放链)

| 加密库 | 插件开关 | 控制台输出 |
|---|---|---|
| CryptoJS(全部对称 & 哈希 & HMAC:AES / DES / 3DES / MD5 / SHA 系) | Hook CryptoJS | 每次调用打印算法 + key / iv / mode / padding + 明文密文 |
| JSEncrypt RSA | Hook JSEncrypt | encrypt:公钥 + 原文 + 密文;decrypt:私钥 + 原文 + 明文 |
| sm-crypto 国密 SM2 / SM3 / SM4 | Hook SM-crypto | 调用参数与结果(银行 / 电信 / 政务目标高频,呼应 `banking-finance.md`) |

流程:发现密文参数 → 开对应 hook(**没输出先排查站点是否重写了 console.log → 开 hook log**)→ 复现一次请求 → 从打印拿明文 + 算法 + key/iv → 本地按同算法构造任意参数重放 → **后端行为定漏洞**。典型命中:前端加密但后端收到什么解什么,伪造请求体直接打 IDOR / SQLi(进 `arbitrary-x-authz.md` / `sqli.md`);登录密码 RSA 公钥加密的站点,密文可重放测认证缺陷(进 `logic-flaws/`)。

手动 hook 模板(CryptoJS.AES 例,其余库同理包一层):

```js
const _enc = CryptoJS.AES.encrypt;
CryptoJS.AES.encrypt = function (msg, key, cfg) {
  console.log('[AES.encrypt]', String(msg), String(key), cfg);
  const out = _enc.apply(this, arguments);
  console.log('[AES.encrypt out]', out.toString());
  return out;
};
```

### 9.4 运行时观察(定位 token / 签名从哪来)

插件 Hook 区按需开:document.cookie(按 name 过滤)、XHR.open(按 URL 过滤)、setRequestHeader(按 header 名过滤)、fetch、localStorage / sessionStorage(setItem/getItem/removeItem/clear)、JSON.parse(可按特定 JSON 过滤)、JSON.stringify、Promise(打印 resolve 参数定位异步回调)、Math.random / Date.now / performance.now(固定返回值)。价值:① 每次 XHR / fetch 实际带了什么头和参数一目了然——直接定位签名与鉴权 token 的生成点;② 固定随机数和时间后,同一密文**稳定复现**,这是脚本化重放的前提;③ JSON.parse 截获后端返回的敏感结构。

**收口**:Hook 所得(明文 / key / 伪造请求)全部仍是假设——按 §6 验证矩阵打后端才立 finding;证据链按 `03-evidence-discipline.md`。红线:Hook 仅用于理解算法与构造自有测试请求,不监听、不盗用真实用户会话数据。

来源:公开常用手法整理(katana/gau/waybackurls 等 README、hakrawler、各 JS 侦察公开文章、Spade sec 公众号《最大化获取Vue框架(SPA类型)下的路由》(0xsdeo));§9 反调试与 Hook 整理自 AntiDebug_Breaker README(0xsdeo,404 星链计划)及其引用的 Hook_JS / vue-force-dev / page-redirect-code-location-hook(CC11001100)/ hook log(Yosan)/ SM hook 思路(魔法少女☆ホシノ)等公开项目,无未披露内容。
