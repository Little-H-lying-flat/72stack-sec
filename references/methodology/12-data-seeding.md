# 无数据变有数据 — 造数管线(空态解锁)

> 定位:测试时页面/接口空数据挡路——空列表没法测渲染类 XSS、没有资源 id 没法测详情页 IDOR、没有记录没法测分页/筛选/导出。本文件是**造数阶梯**:三层手段把"无数据"变"有数据",并规定每层产出能进证据链到什么程度。
> **证据铁律(先于一切)**:服务端造数(L1)产生的数据是真数据,可进证据链;前端拦截(L2)和 DOM 直填(L3)只影响你自己的浏览器,**凡 confirmed 判定必须回到服务端真实响应 / 落库检查**(三段差分照走,`03-evidence-discipline.md`)。伪造数据本身永远不作为漏洞证据——"拦截注入的 payload 显示出来了"≠ 存储型 XSS confirmed。

---

## 1. 触发场景

| 空态信号 | 被挡住的测试 |
|---|---|
| 列表/表格空、`"total": 0` | 存储型 XSS 的展示链、渲染 sink、前端模板转义验证 |
| 无任何业务资源(订单/留言/文件/收藏) | 详情页 IDOR、任意改/删、状态流转 |
| 分页/筛选/排序/导出/报表 | 越权批量、导出范围、注入点(排序字段) |
| 长表单(10+ 字段)逐项手填慢 | 注册/创建类流程、批量参数、Mass Assignment |

---

## 2. 三层阶梯(选择规则:能 L1 不 L2,能 L2 不 L3)

| 层 | 手段 | 数据真伪 | 能做什么 / 不能做什么 |
|---|---|---|---|
| **L1 服务端造数** | 回放创建接口批量种数据(§3) | **真**(落库) | 所有视图可见、可做 IDOR/越权的资源源、可进证据链;不能碰真实用户数据 |
| **L2 响应拦截注入** | hook fetch/XHR 把空响应替换成生成行(§4) | 假(仅本浏览器) | 测前端渲染 sink / 前端逻辑 / 打通"列表→详情"UI 链;**不能证明服务端漏洞** |
| **L3 DOM 直填** | 直接向页面插 HTML/填表(§5) | 假(仅本浏览器) | 确认"这条 UI 链路通不通";证据价值最低,不出 confirmed |

L2/L3 观察到的任何疑似漏洞,出报告前必须用 L1 造真数据复验一遍。

---

## 3. L1:服务端种子工厂(首选)

**核心动作**:抓一次"创建"请求(下单/留言/发帖/上传),curl 循环回放,字段值换生成值:

```bash
# 从 Burp/抓包导出的创建请求,循环 N 次并替换字段值
for i in 1 2 3 4 5; do
  curl -s -X POST "$BASE/api/message" -H "Cookie: $A_COOKIE" \
    -d "title=[TEST]第${i}条&content=seed-$(openssl rand -hex 4)&phone=138$(printf '%08d' RANDOM)" \
    -o /dev/null -w "%{http_code} "
done
```

**字段值生成映射**(无 faker 时手写,faker 生态见 §6):

| 字段名信号 | 生成规则 |
|---|---|
| `name/uname/realname` | 中文姓名:张伟/李娜/王芳 + 随机序号 |
| `phone/mobile/tel` | 138/139/186 段 + 8 位随机 |
| `email/mail` | `test+<n>@example.test`(用保留域,不投递) |
| `idcard/certno` | 测试格式串 `[TEST]1101011990010000XX`,不做真号 |
| `amount/price/money` | 0.01 / 1.00 / 99.99 小额组合 |
| `addr/address` | `[TEST]测试地址-<n>号` |

**环境注记(Windows/GitBash 实测摩擦)**:curl `-d` 内联含中文的 JSON 会被 shell 编码破坏(目标报 400 bad json,整批作废)——CN 字段值造数改用 UTF-8 脚本文件发:python seeder(urllib/requests)或 `curl -d @payload.json`(文件以 UTF-8 写),不再用内联 `-d "中文"`。

**与 11 号管线 §4.7 的衔接**:IDOR/越权队列项开打前的 seed 四步(双号注册 → A 号建订单/留言/收藏各 ≥1 带 `[TEST]` 标记 → id 清单入 scope.md `next:` 节 → B 会话限样本遍历)由本节供弹药——seed 造不出来/数量不够时按 §3 批量回放,造数请求同样走 §4.1 节流阶梯。

**数量与占位红线**:每类 3–10 条够用;分页测试 ≤2 页;导出用最小时间范围;新数据会置顶到真实用户可见列表——共享环境选低峰并在报告注明造数行为。

---

## 4. L2:响应拦截注入(MockJS 思路)

原理:不改服务端,hook 页面的 fetch / XHR / axios,把空数组/空对象替换成生成行,让前端走完整渲染路径。

**三条落地路径**(按可用性降级选用):

1. **jshook MCP**:`mcp__jshook__network_intercept` 拦截响应改写(工具清单见 `../tools/mcp-jshook.md` network 域);
2. **CDP 启动注入**(browser-harness 会话,SessionScript 先例):`Page.addScriptToEvaluateOnNewDocument` 注入 fetch+XHR hook,刷新后持续生效——对"登录后跳转才拉数据"的 SPA 最稳;
3. **页面 console 快速过载**(手测兜底):当场覆写 `window.fetch`,等价 MockJS 的拦规则。

```javascript
// MockJS 风格规则模板(console 路径示例):空列表 → 20 条生成行
const _f = window.fetch;
window.fetch = async (...a) => {
  const r = await _f(...a);
  const ct = r.headers.get("content-type") || "";
  if (ct.includes("json") && a[0].toString().includes("/api/list")) {
    const j = await r.json();
    if (!j.data?.length) j.data = Array.from({length: 20}, (_, i) => ({
      id: 900000 + i, title: `[TEST]种子${i}`,
      content: `<img src=x onerror=alert(1)>`,
      user: {id: 7, name: "张伟"} }));
    return new Response(JSON.stringify(j), {headers: {"content-type": "application/json"}});
  }
  return r;
};
```

**适用**:前端模板转义验证(列表页渲染 `content` 是否 encode)、前端逻辑漏洞(前端算价/前端权限判断)、SPA"详情页必须从列表点进去"的 UI 链打通。

**硬警告**:存储型 XSS 必须 payload 真落库。拦截注入后页面上 payload 显示了,只能记 "UI 渲染确认(candidate)",落库验证另走 L1 用真数据提交一次。

**hook 存活矩阵(dogfood 实测)**:CDP `addScriptToEvaluateOnNewDocument` 注入跨 reload 持续;页面 console / 内部浏览器 evaluate 注入**不跨 reload**——无 CDP 环境用 SPA 内路由切换保 hook(reload 前完成观察),或接受"hook 失效后立即转 L1 复验"的节奏。**sink 语义判读**:观察渲染时分 text / HTML sink——实测 `textContent` 渲染的 payload 只显示不执行,**显示 ≠ 可利用**;HTML sink 才进 candidate。

---

## 5. L3:DOM 直填 + 表单自动填充

- **DOM 直填**:`insertAdjacentHTML` 造渲染态,只判"这条展示链路通不通",证据价值最低。
- **长表单自动填充**:按 §3 字段映射生成值 → browser-harness/jshook 自动逐字段填(`page_inject_script` / `page_evaluate`)→ 提交一次;比 AI 填充扩展可控、可留痕。
- **AI form filler 扩展**(LLM 识别表单一键填充):仅当无 MCP 环境的人工协作 fallback 用;自动环境下不用第三方扩展——不可控的注入面本身就是风险。

---

## 6. 工具生态索引(参考,本库不内置)

| 生态工具 | 定位 | 对应本 skill 用法 |
|---|---|---|
| [@faker-js/faker](https://github.com/faker-js/faker) | JS 生态最强伪造数据生成库 | §3 生成器:node 脚本批量生成字段值;CDN 注入后 `faker.person.fullName()` 等供 console 用 |
| [MockJS](https://github.com/nuysoft/Mock) | 拦 Ajax 按规则返回假数据,不改前端代码 | §4 规则模板的思路原型;有 jshook/CDP 时不需要引它的运行时 |
| Chrome 扩展 Mock Injector 类 | 检测 DOM 为空自动插 HTML/数据 | 对应 L3;仅无 MCP 环境的协作 fallback |
| AI form filler 类扩展 | LLM 识别表单/数据区一键填假数据 | 对应 §5 手测辅助;自动化环境不用 |

---

## 7. 红线

- **伪造数据不进证据链**:L2/L3 只解锁路径,confirmed 判定一律以服务端真实响应/落库为准。
- **[TEST] 标记**:服务端造数全部带 `[TEST]` 前缀;测完能删则删,不能删在报告"测试行为声明"里列明。
- **不碰真实用户数据**:造数只用自己的测试账号;不在共享列表挤占真实用户可见位。
- **限速与收敛**:批量造数走节流阶梯;每类 3–10 条;不分页拉爆、不做全量枚举式造数。
- **拦截注入只作用于自己会话**:hook 脚本不含外发、不碰其他用户/其他 tab 的会话。
- **导出/报表类造数**先核对 compliance 与该 playbook 样本控制红线(导出最小范围,拉 1 条样本即停)。
