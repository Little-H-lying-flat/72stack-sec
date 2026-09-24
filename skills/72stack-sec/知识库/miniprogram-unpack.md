# 微信小程序：拆包 = 测绘

> 不是新打法。拆包对标 FOFA：主控串行、不占 10 席。抽出的 `wx.request` / host 进本种子 leftover，席位仍打 HTTP。短表枪照认（openId、写死 token、云函数 catalog、代调 IdP）。
> 一种子闭环：只收**本种子/锁面**小程序。禁止全网爬微信、禁止按 appid 批量从 CDN 拉任意包。

## 用哪套解包（GitHub，不进 skill 仓库）

本机装，不 vendoring。GUI 给人扫缓存；CLI 给主控解已解密的 `.wxapkg`。

| 项目 | 星数量级 | 干什么 | 谁用 |
|------|----------|--------|------|
| [wux1an/wxapkg](https://github.com/wux1an/wxapkg) | ~4k | **首选。** Win/mac GUI：扫 PC 微信安装目录、解密、解包、美化 | 人，本机 |
| [qwerty472123/wxappUnpacker](https://github.com/qwerty472123/wxappUnpacker) | ~4.5k（archived） | Node 解包还原目录；经典 CLI | 主控有 Node 时 |
| [BlackTrace/pc_wxapkg_decrypt](https://github.com/BlackTrace/pc_wxapkg_decrypt) | ~700 | **只解密** PC 微信加密 wxapkg，不解包 | 主控补解密 |
| [sjatsh/unwxapkg](https://github.com/sjatsh/unwxapkg) | ~200 | 已解密 `.wxapkg` 解包 CLI | 主控 |

推荐组合：人用 **wux1an** 扫本机微信缓存 → 解出源码目录 → 主控跑 `scripts/mp_extract_urls.py` 抽 URL。没有 GUI 时：BlackTrace 解密 + unwxapkg/wxappUnpacker 解包。

解包结果落到任务 `js/{appid}/anon/`（对标 Web JS）。禁止把整包反编译树外传。

## 批量拿包：只能三层（锁面内）

真正能自动批量的是 **层 0**。层 1 是半自动。层 2 少次查询。没有「全微信下载器」。

### 层 0 — 本种子 Web 资产里抠 appid（可自动）

已挖的 H5/JS/报告里扫：

- `wx[a-f0-9]{16}`
- `servicewechat.com/wx…`
- `__wxConfig` / `appId`

脚本：`python scripts/mp_queue.py --root {任务根}` → upsert `资产/miniprograms.md`。

有 appid **不等于**有包。下一步：人在微信打开该小程序（锁面品牌），让缓存落地，再走层 1。禁止写「拿 appid 去微信 CDN 批量拉包」当默认能力。

### 层 1 — 本机微信缓存（半自动，批量 = 你打开过的）

研究者用微信搜本种子品牌/产品名，点开锁面小程序。包会落到本机：

- PC 微信：`WeChat Files` / `Applet` / 新版微信文档目录（wux1an 会扫）
- 手机：已有 ADB 通道时，本机微信 `appbrand/pkg`（**自己的测试机**）

然后 wux1an 扫描解密解包。这是目前最稳的「一批包」，上限是你点开过的那些，不是全网。

### 层 2 — 品牌词少次搜（禁止当 FOFA 翻页）

本种子产品名（主站、奇巴布、随刻…）在微信搜一搜 / 官网二维码。几次即可。禁止把搜一搜 API 写成 leftover 翻页，禁止多种子小程序连搜。

## 进流水线（收单）

表：`资产/miniprograms.md`。状态：`skip` / `pending_triage` / `waiting_open` / `cached` / `unpacked` / `in_leftover`。

1. 收单 `mp_queue.py`（0 席，不挡翻页/保满）
2. `waiting_open` 且锁面=是 → 人微信打开；说「小程序已打开 {名}」
3. 缓存命中 → `cached` → CLI 解到 `js/{appid}/anon/` → `unpacked`
4. `mp_extract_urls.py` → 锁面 host 进 leftover（`面=mp`）；已在打的 H5 域不重开席 → `in_leftover`
5. 无 `本轨=小程序`。`wx.login` = 盾
6. `pending_triage` 不准当 waiting_open；第三方 SDK → `skip`

## 禁止

- 全网爬微信小程序、按类目翻页下载
- 未打开、未授权去拉别人的包当测绘进度
- 拆包线程占满 10 席
- 把小程序当新漏洞类型（洞仍在 API；认短表）
- Frida/模拟器磨微信登录（人在环）
