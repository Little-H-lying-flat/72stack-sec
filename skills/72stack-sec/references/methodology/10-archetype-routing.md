# 目标原型路由——先定型,再打点

> 视角:猎人面对的不是"漏洞类列表",是一个**有形态的目标**。01-attack-priority 管"哪个洞值钱",本文件管"这个目标该按什么顺序打"。Phase 3 资产矩阵完成后、Phase 4 选 playbook 前,先定型。

---

## 1. 用法

1. 对照 §2 的识别信号,给资产矩阵里的每个候选目标**判一个原型**(混合形态取主形态,次形态作补充行)
2. 按 §2 该原型的 playbook 序列依序打,每类打完出口检查(09-target-workspace §3)
3. 序列是**优先级排序**不是封闭清单——中途命中高价值入口(如拿到 shell)即切换原型

---

## 2. 七个原型

### A. Java 管理面 / 中间件裸露

**识别**:8080/8081 端口、`/actuator`、`/druid`、Shiro rememberMe cookie、国产 OA 指纹(weaver/seeyon/tongda/landray/yongyou/kingdee)、hikvision/dahua 设备页。

**序列**:`unauth-access`(默认凭据/heapdump) → `rce/`(框架反序列化/SSTI) → `info-disclosure`(.env/备份) → `sqli`

**理由**:管理面默认凭据与已知组件 CVE 是国内 SRC 最高产的入口,全部可 nuclei 初筛(`references/tools/nuclei-templates/`)。命中 Actuator/heapdump → 走密码提取链,常见 1 包到 P0。

### B. Vue/React SPA + REST API + 前后端分离后台

**识别**:SPA bundle(`app.[hash].js`)、`/api/*` JSON、JWT/Authorization header、菜单由接口下发。

**序列**:`methodology/07-js-recon`(全量路由/隐藏路由/JS 密钥) → `api-rest/`(BOLA/Mass Assignment) → `arbitrary-x-authz`(IDOR/越权) → `logic-flaws/`

**理由**:这类目标前端藏信息,后端靠鉴权。JS 差集路由(§8)常直接暴露未授权后台路径;API 层 IDOR 是国内众测数量最大的洞。**双账号是硬前提**——接单时确认可注册两个账号。

### C. 传统服务端渲染站(PHP/ThinkPHP/JSP)

**识别**:.php/.jsp 后缀、ThinkPHP 报错页、`/index.php?m=` 路由、老站目录结构。

**序列前先做**:确定应用**真实根**——从 base href / 静态资源路径 / Set-Cookie path 判断 CMS 实际部署目录。CMS 常被部署在任意子目录(实战案例:MLECMS 整站部署在 `/mlecms/upload/` 下),按域名根拼 admin/install 字典会全 404。

**版本号即线索**:指纹直出版本号(如 MLECMS v2.3 的 copyright 头)→ 先检索公开漏洞库(exploit-db / seebug / 厂商历史公告,以实际检索结果为准,不凭记忆引编号)再决定自挖顺序——2010 年代国产 CMS 的已知洞密度通常远高于新挖产出。

**序列**:`info-disclosure`(.git/.svn/备份/源码泄漏) → `sqli`(老站参数化差) → `file-upload`(后台上传) → `rce/10-framework`(ThinkPHP 系)

**理由**:老站的价值在"泄露面大 + 补丁慢"。.git/备份泄露直接进 01 的升级链(源码 → hardcoded secret → P0)。

### D. 微信小程序 + 后端 API

**识别**:业务以小程序为主、App 抓包见 wx 接口、目标提供小程序码。

**序列**:MCP `http://127.0.0.1:4554/sse`（`list_packages` → `decompile` → 静态扫）拿接口/密钥/appid → 72stack 短表+知识库打后端（常漏鉴权）→ 支付/兑换/IDOR。`web-view`/云开发细节才读 miniprogram-hunt 对应 playbook。

**理由**:小程序前端的反编译产物 = 完整 API 文档;后端常按"小程序调的都可信"假设开发,未授权接口密度高。code-secret/第三方 AK 常在配置里。动态要 `get_info`；微信 4.x 动态常废，静态照打。

### E. 云上资产为主

**识别**:资产矩阵命中 `*.oss-* / *.myqcloud.com / *.amazonaws.com`、6443/10250/2379 端口、函数计算 endpoint。

**序列**:进 `playbooks/cloud/00-index.md` 按其内部路由走(控制面 → IAM → 对象存储 → K8s);Web 层仍发现 SSRF 则接 `ssrf-cache-host/11-cloud.md` 元数据链。

**理由**:云资产的打法以配置与身份为主轴,与 Web 类 playbook 节奏不同,交给云 playbook 自己的路由。

### F. 官网 / 营销单页(低价值,快速过)

**识别**:纯静态、无登录、无 API、无上传。

**序列**:`info-disclosure`(目录遍历/备份) → `xss/`(反射) → 结束

**理由**:期望值低,**时间盒 30 分钟封顶**,结果大概率是"clean 记入台账"——干净地放弃也是出口检查的合法产出。别在这里烧预算,去 B/A 类。

### G. 已有 shell / 内网入口(中途切换)

**识别**:任一原型打出 RCE / webshell / SSRF→内网。

**序列**:切 `intranet-postexp/`(凭据收集 → 横向) → 凭据回打业务面(密码复用) → 若云上,元数据接 11-cloud

**理由**:入口价值 > 站点价值。拿到内网位后,原型的优先级全部重排为"横向可达什么"。

---

## 3. 时间盒分配(对齐 05 的模板,不另起炉灶)

05-srctimebox 的 4 个模板是**按高危占比排的通用骨架**;本表只写**原型特化点**,其余沿用 05。

- **B 型特化**:05 模板 A 的"抓主要业务流"(0:30–1:30)在 SPA 上具体化为 js-recon 全量路由 + 差集,而非手工点击
- **A 型特化**:05 模板 A 的 0:00–0:30 段(端口扫 + admin 路径 + 默认凭据)即本型的地表层,加跑 nuclei 初筛

| 时段(B 型,6h) | 动作 |
|---|---|
| 0–30min | Phase 1-2:规则确认 + 被动侦察,建账(09) |
| 30–90min | 07-js-recon:全量路由 + 差集 + JS 密钥,顺手记 OSS/API 域 |
| 90–210min | api-rest + IDOR(双账号),命中即走差分 → 台账 |
| 210–270min | logic-flaws(密码重置/支付探针,只读优先;密码重置 4 模式见 05 §2 88% 段) |
| 270–330min | 出口检查(覆盖率矩阵) + Phase 5 |

其余原型:按 05 模板 A/B 骨架 + 本文件 §2 序列拼接;E 型走 cloud/ 内部节奏,F 型 30 分钟封顶。

---

## 4. 与既有文档的关系

| 文档 | 分工 |
|---|---|
| 01-attack-priority | 管单洞**价值**(评分/升级链/降级) |
| 本文件 | 管目标**顺序**(原型 → playbook 序列 → 时间分配) |
| 04-control-gap-hunting | 管卡壳时的"控制缺失"视角,序列内的深挖工具 |
| 09-target-workspace | 序列每步的产出落账;出口检查收口 |


## 5. 技术栈速查(按栈分配第一轮探针,20260831)

判栈后直接对表——每个栈自己的"第一枪":

| 栈 | 高频攻击点(第一轮优先) |
|---|---|
| **Java**(Spring/Tomcat) | Actuator 暴露 / Shiro rememberMe 反序列化 /druid / Struts2 OGNL / Jenkins-CLI |
| **Node/Express** | 原型污染(merge/assign) / SSRF(内置 http) / JWT(node-jsonwebtoken alg 混淆) / 路径穿越(express.static) |
| **PHP**(含 thinkphp) | 文件包含(伪协议) / 反序列化(phar/unserialize) / ThinkPHP RCE 族 / 上传绕过(.php 变体族) / 弱类型 == 碰撞 |
| **Python**(Django/Flask) | SSTI(Jinja2 {{}}) / pickle 反序列化 / debug 页(Werkzeug PIN) / 路径遍历(send_file) |
| **Go** | 路径穿越(stdlib 历史洞) / SSRF(net/http 跟随) / 整数截断(int32)——面窄但别漏 pprof 端点 |
| **前端栈信号** | Angular(白页+bundle)→14 §5;Vue(路由差集)→07 §8;React→源码 map/API 常量 |

> 与 §2 原型的关系:原型决定**打点顺序**,本表决定**每栈的第一枪**;判栈信号来自 Phase 3 指纹。
