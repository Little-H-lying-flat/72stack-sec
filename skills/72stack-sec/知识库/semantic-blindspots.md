# 语义盲区回灌库（发现引擎的记忆）

> 用途：每次**确认命中**或**明确漏报**后追加一行，供后续开场读「易漏问句」。  
> 不是 payload 库。禁止在本文件写利用步骤/PoC/具体攻击命令。  
> 进 `打穿短表` 手法行仍只认 `D:\dsh-72stack-sec\rules/hunt-iter.md`；本文件只积累候选与问句。
> 何时写、covered 门闩见同目录 `回灌闭环.md`。

## 怎么用

1. 任务收尾或中危+ 落盘后：主控追加本表；安全档也可由 `evolve_apply --auto-safe` 追加同目录 `semantic-blindspots.auto.md`（机器不改本主表）。
2. 新任务威胁模型阶段：扫本表 **和** `.auto.md`「业务/栈」相关行，把「应多问的语义疑问」写进本站 `suspects.md` 头部。
3. 同一根因重复 2 次以上 → 开 hunt-iter 评估是否进短表（不在本文件直接改短表）。

## 字段说明

| 列 | 含义 |
|----|------|
| 日期 | YYYY-MM-DD |
| 类型 | 命中 / 漏报 / 误报 |
| 业务·栈 | 如 电商·Spring / 广告后台·SPA |
| 语义疑问（应问而未问清） | 一句话：服务端信什么？哪道防线假的？ |
| 对象形态 | 如 hidden 金额、密文 id、发签口、存储代理 key |
| 根因标签 | 如 BOLA / 模板中和 / 会话票外泄（CWE 可选） |
| 回灌动作 | 已写入 suspects 模板 / 待 hunt-iter / 已进短表 |
| 任务指针 | 任务短名或报告标题（勿贴敏感实值） |

## 回灌日志

| 日期 | 类型 | 业务·栈 | 语义疑问（应问而未问清） | 对象形态 | 根因标签 | 回灌动作 | 任务指针 |
|------|------|---------|--------------------------|----------|----------|----------|----------|
| 2026-09-10 | 种子 | — | （开场样例）认证后每个 id 参数是否服务端按会话取主体？ | path/query 中的 id/pk | BOLA | 待实战填充 | 设计初始化 |

| 2026-09-10 | 命中 | 特效开放平台·Web/CMS | 目录/列表过滤是否等于详情授权？未上架 id 详情是否仍出全文？ | homepage textContent?id= | 未授权读（列表≠详情） | 已写入 suspects 复盘 | 快手 effect 未上架教程 |
| 2026-09-10 | 命中 | 特效开放平台·灵感池 | 列表没有的自增 id、状态已删除时，详情是否仍回正文/指南/运营字段？ | hotMining pool/detail?id= | BOLA/可见性 | 已写入 suspects 复盘 | 快手 effect 已删除灵感 |

| 2026-09-10 | 命中 | 1win·WordPress | WP REST 插件路由是否误挂成公开可写？ | send-pages-info REST | 未授权写 | 已批量回灌 | 1win.com.bj 与 1win.com.tr WordPress send-pages-info 接口匿名未授权任意创建、复制、删除官网页面 |
| 2026-09-10 | 命中 | 1win·Roundcube | webmail 日志目录是否误配为匿名可列可下？ | Roundcube 日志路径 | 未授权读/配置暴露 | 已批量回灌 | 1win.com.ua Roundcube 匿名未授权读取发信日志与错误日志 |
| 2026-09-10 | 命中 | 猎聘系·Rivers | 落地页配置接口是否把内部规则正文当公开配置？ | Rivers 落地页配置 | 未授权读 | 已批量回灌 | 多猎Rivers落地页配置匿名未授权批量读取RCN内部规则正文 |
| 2026-09-10 | 命中 | 华为GTS·ECCS | 坐席个人队列订阅/投递是否鉴权到会话主体？ | 坐席消息队列 | 未授权读写 | 已批量回灌 | 华为GTS ECCS客户服务中心匿名未授权读写任意坐席消息队列 |
| 2026-09-10 | 命中 | 可灵国际·Web API | 公开榜单/精选接口是否把登录邮箱等非展示字段一并吐出？ | rankingBoard/curatedSkits 回包 userEmail | 过量数据暴露/未授权读 | 已批量回灌 | 可灵国际 Kling.ai 匿名未授权排行榜精选接口批量泄露他人邮箱 |
| 2026-09-10 | 命中 | 菠萝BOLO·创作台 | 图片代理/_next/image/download 是否把任意内网 URL 当可信源？ | 图片URL/对象存储代理 | SSRF | 已批量回灌 | 快手菠萝BOLO创作台匿名未授权SSRF可批量读取内网对象存储他人素材图 |
| 2026-09-10 | 命中 | 磁力建站·广告落地 | 未发布/草稿中间页 id 详情是否仍出全文与包名下载址？ | 中间页 detail?id= | 未授权读（列表≠详情） | 已批量回灌 | 快手磁力建站匿名未授权批量读取他人未发布中间页正文 |
| 2026-09-10 | 命中 | 磁力聚星·活动 | 活动日历登录墙后的 activityId 详情是否匿名仍出运营人与权益配置？ | activityId 详情 | 未授权读 | 已批量回灌 | 快手磁力聚星匿名未授权批量读取活动详情及内部运营人账号 |
| 2026-09-10 | 命中 | 磁力聚星·H5任务 | 任务列表墙是否被误当成详情口授权？missionId 枚举是否出投放文案？ | missionId 详情 | 未授权读（列表≠详情） | 已批量回灌 | 快手磁力聚星H5匿名未授权批量读取他人快任务详情正文 |
| 2026-09-10 | 命中 | 磁力追踪·门店 | 门店/落地表单配置接口是否校验广告主归属？ | 门店/表单配置 | 未授权读/PII | 已批量回灌 | 快手磁力追踪匿名未授权批量读取他人广告主门店及落地表单配置 |
| 2026-09-10 | 命中 | 电商官网·服务商 | 下架/隐藏状态是否只挡列表不挡详情正文？ | 服务商档案 id | 可见性/状态旁路 | 已批量回灌 | 快手电商官网匿名未授权批量读取他人已下架服务商档案正文 |
| 2026-09-10 | 命中 | 广告私信·商户 | 私信工作台商户档案是否只信 ksUserId 路由键？ | ksUserId→商户档案 | 未授权读 | 已批量回灌 | 快手广告私信工作台匿名未授权批量读取他人商户档案 |
| 2026-09-10 | 命中 | 直播机构·通知结算 | 机构/公会通知接口是否把结算联系人当公开字段返回？ | 通知/联系人列表 | 未授权读/PII | 已批量回灌 | 快手机构服务平台匿名未授权批量读取他人公会通知及结算联系人 |
| 2026-09-10 | 命中 | 主站/支付·微信OAuth | OAuth 回调是否校验 state.url 为本域？code 是否原样外带？ | state.url + oauth code | 开放重定向/OAuth | 已批量回灌 | 快手双域登录OAuth回调任意重定向劫持官方授权码 |
| 2026-09-10 | 命中 | 小店·三方审核 | 审核台通讯录/处理人字段是否对任意登录角色开放？ | 处理人邮箱字段 | BOLA/过量暴露 | 已批量回灌 | 快手小店三方审核台越权读取内部员工姓名与企业邮箱 |
| 2026-09-10 | 命中 | 小店·三方审核 | 三方审核工单 id 是否仅按登录主体鉴权还是裸 id？ | 审核工单 id | BOLA | 已批量回灌 | 快手小店三方审核台越权读取他人主播带货审核工单正文 |
| 2026-09-10 | 命中 | 小店·物流商 | 物流商工作台运单号/id 是否绑定当前物流商主体？ | 运单号/轨迹查询 | BOLA | 已批量回灌 | 快手小店物流商工作台越权批量查询他人运单轨迹 |
| 2026-09-10 | 命中 | 直播开放平台·公告 | 未发布公告 id 详情是否仍出全文？ | 公告 detail id | 未授权读（列表≠详情） | 已批量回灌 | 快手直播开放平台越权读取未发布公告正文 |
| 2026-09-10 | 命中 | AI开放平台·文档 | 文档中心登录墙是否挡住正文接口还是只挡页面？ | 内部文档/SDK 正文 | 未授权读 | 已批量回灌 | 快手AI开放平台匿名未授权批量读取内部技术文档及SDK正文 |
| 2026-09-10 | 命中 | 快影国际·api-proxy | api-proxy 是否校验目标仅公网业务域？corp/loopback 是否被信？ | api-proxy URL | SSRF | 已批量回灌 | 快影国际 ky.kwai.com 匿名未授权SSRF可通过api-proxy访问内网corp域名与本机服务 |
| 2026-09-10 | 命中 | 腾讯云·CloudBase低代码 | 官方低代码数据源是否默认可匿名读用户表字段？ | 低代码用户表手机/邮箱 | 未授权读/PII | 已批量回灌 | 腾讯云开发CloudBase官方低代码环境匿名未授权批量读取他人用户手机号与企业邮箱 |
| 2026-09-10 | 命中 | 小红书·服务商 | 服务商详情/证照接口是否匿名可按 spId 枚举？ | spId→联系人/证照 | 未授权读/PII | 已批量回灌 | 小红书电商服务商后台匿名未授权批量获取他人服务商联系人手机邮箱及营业执照 |
| 2026-09-10 | 命中 | 小红书·客服IM | 长连接网关是否把前端写死 token 当会话凭证？ | 前端写死 IM token | 硬编码凭证/未授权 | 已批量回灌 | 小红书客服长连接网关匿名未授权使用前端写死令牌建立官方客服IM会话 |
| 2026-09-10 | 命中 | 小红书·灵犀 | 内部知识库正文接口是否与页面登录墙同源鉴权？ | 知识库正文 | 未授权读 | 已批量回灌 | 小红书灵犀平台匿名未授权批量读取内部员工权限申请知识库正文 |
| 2026-09-10 | 命中 | 小红书·蒲公英 | 跨站开放接口回包是否夹带可当主站内容票的 xsec_token？ | xsec_token | 凭证外泄 | 已批量回灌 | 小红书蒲公英平台匿名接口泄露主站笔记访问凭证xsec_token |
| 2026-09-10 | 命中 | 小红书·设计中心 | 运营配置写接口是否完全无鉴权？写是否等于信任客户端？ | 运营配置写接口 | 未授权写 | 已批量回灌 | 小红书设计中心运营配置接口匿名未授权任意写入 |
| 2026-09-12 | 命中 | 小红书·pages2 KV | 运营配置 `/data/{key}` 写口换 sibling host 是否仍匿名可写？CDN 对 400 的 Cache Hit 是否让「先 GET 再 POST」看起来没落库？ | `/data/{key}` GET/POST + name 字段 | 未授权写（sibling host） | 已写入 suspects；中危不进短表 | 小红书pages2运营配置接口匿名未授权任意写入 |
| 2026-09-10 | 命中 | 小红书·DIBP | AI会话/分享链接签发是否校验对象归属？ | AI会话/分享链接 | 未授权读/BOLA | 已批量回灌 | 小红书DIBP平台匿名未授权批量获取内部员工企业邮箱及AI会话并签发他人分享链接 |
| 2026-09-10 | 命中 | 小红书·Web | 该 id/票是授权凭证还是仅路由键？换他人值差分是什么？ | 对象 id | BOLA/未授权读 | 已批量回灌 | 小红书kratos投放工作台匿名未授权批量获取他人投放报警规则员工企业邮箱及投放创建任务 |
| 2026-09-10 | 命中 | 小红书·picasso | 静态资源桶是否把内部问卷/指标当可枚举公开对象？ | picasso 桶对象 | 未授权读/对象存储 | 已批量回灌 | 小红书picasso静态资源桶匿名未授权批量获取他人问卷表及内部指标正文 |
| 2026-09-10 | 命中 | 中通·邮局H5 | H5 配置下发是否把收件人PII写进可匿名拉取的配置？ | Apollo/配置下发 PII | 未授权读/PII | 已批量回灌 | 中通邮局H5匿名未授权读取配置出他人姓名手机住址 |
| 2026-09-10 | 命中 | 中通·在线客服 | 客服会话流/底单接口是否绑定会话票还是可枚举？ | 客服会话/签收底单 | 未授权读/PII | 已批量回灌 | 中通在线客服匿名未授权实时批量读取他人客服会话正文及签收底单 |
| 2026-09-10 | 命中 | 中通·Teambition | 文档中心登录墙是否挡住正文 API？ | 内部 API 文档正文 | 未授权读 | 已批量回灌 | 中通Teambition文档中心匿名未授权读取登录墙后的内部API文档正文 |
| 2026-09-10 | 命中 | Vercel·MCP/通道 | OAuth metadata / postMessage 是否校验 Origin 与 Host？ | OAuth metadata / postMessage | Origin/Host 校验缺失 | 已批量回灌 | AI SDK MCP OAuth 发现匿名请求内网授权服务器元数据 |
| 2026-09-10 | 命中 | Vercel OSS·工具链 | 不可信字段（tag/URL/lang/导出名）是否被拼进 shell 或当模块执行？ | 生成器/CLI 拼接点 | 命令注入 | 已批量回灌 | autoship 把 changeset 说明和 GitHub owner 拼进 shell 可在本机执行任意命令 |
| 2026-09-10 | 命中 | CodeFlicker·账单 | 账单接口是信 JWT 主体还是信 kwaipilot-username 头？ | kwaipilot-username 请求头 | 混淆代理身份/BOLA | 已批量回灌 | CodeFlicker越权通过kwaipilot-username请求头批量读取并操作他人账单账户 |
| 2026-09-10 | 命中 | Vercel OSS | 该入口信任的外部输入是否可变成文件/执行/凭证外带？ | 工具入口参数 | 供应链/未授权 | 已批量回灌 | crossws uWebSockets 适配器匿名未授权读到其他 namespace 房间的消息 |
| 2026-09-10 | 命中 | Remitly·Help CMS | 预发 CMS 数据集是否仍挂匿名可读 token？登录墙是否只挡站点壳？ | Sanity 预发库正文 | 未授权读/预发暴露 | 已批量回灌 | help.remitly.com Sanity预发布库匿名未授权批量读内部客服知识库正文 |
| 2026-09-10 | 命中 | HostGator Studio·存储 | 对象存储列表/下载是否把公开读权限当成租户隔离？ | 素材桶 key/list | 未授权读/对象存储 | 已批量回灌 | HostGator Studio 素材桶匿名未授权批量列出并下载他人设计图 |
| 2026-09-10 | 命中 | HostGator Studio·网关 | from-image-url 是否对任意 URL 服务端拉取且无租户票？ | from-image-url | SSRF | 已批量回灌 | HostGator Studio 网关 from-image-url 匿名未授权 SSRF |
| 2026-09-10 | 命中 | HostGator·问卷 | 答卷 id 是否仅路由键？匿名是否可批量读他人答卷？ | 问卷/答卷 id | 未授权读 | 已批量回灌 | HostGator问卷接口匿名未授权批量读取他人答卷 |
| 2026-09-10 | 命中 | Vercel·Nitro/Workflow | 开发/预设任务入口是否默认匿名可调？ | 任务/workflow 入口 | 未授权执行 | 已批量回灌 | Nitro 开发服务器匿名未授权读取虚拟模块并执行任务 |
| 2026-09-10 | 命中 | Nuxt·DevTools | 开发态 RPC 是否对局域网匿名开放且无鉴权？ | DevTools RPC | 未授权 RCE | 已批量回灌 | Nuxt DevTools 匿名未授权 RPC 可读任意文件并在开发机执行命令 |
| 2026-09-10 | 命中 | QQ钱包·商户平台 | 商户安全手机查询是否绑定登录商户主体？ | 商户号→安全手机 | BOLA/PII | 已批量回灌 | QQ钱包商户平台匿名未授权批量查询他人商户绑定安全手机号 |
| 2026-09-10 | 命中 | Rapyd·Web | 该 id/票是授权凭证还是仅路由键？换他人值差分是什么？ | 对象 id | BOLA/未授权读 | 已批量回灌 | Rapyd 手机端 Client Portal 匿名未授权批量读取他人商户 SSO 身份源 |
| 2026-09-10 | 命中 | Varonis·商城 | 订单/地址 id 是否仅路由键？ | 收货地址对象 | 未授权读/PII | 已批量回灌 | store.varonis.com 匿名未授权任意读取他人收货地址姓名手机住址 |
| 2026-09-10 | 命中 | Varonis·Swag | 客户邮箱字段接口是否校验归属？ | 客户邮箱 | 未授权读/PII | 已批量回灌 | swag.varonis.com 匿名未授权任意读取他人客户邮箱 |
| 2026-09-10 | 命中 | Varonis·Swag | 私信线程 id 是否绑定会话用户？ | 私信线程 | BOLA | 已批量回灌 | swag.varonis.com 匿名未授权任意读取他人站内私信 |
| 2026-09-10 | 命中 | Turborepo·CLI | remote cache URL 是否完全信任项目配置并外带用户 token？ | turbo.json remote cache | 凭证外带 | 已批量回灌 | Turborepo CLI 会把用户 TURBO_TOKEN 发到 turbo.json 指定的任意 remote cache 地址 |
| 2026-09-10 | 命中 | Varonis·内容门户 | 文档/课程可见性是否只挡壳不挡 API？ | 文档/课程对象 | 未授权读 | 已批量回灌 | Varonis API 文档站匿名未授权读取登录墙后的 API 指南及接口参考正文 |
| 2026-09-10 | 命中 | Wolt·Control Tower | Control Tower 写接口是否完全无鉴权？ | 城市位置写删 | 未授权写 | 已批量回灌 | Wolt Control Tower 匿名未授权任意删除城市位置 |
| 2026-09-10 | 命中 | Wolt·payment | payment-service 写卡接口是否暴露在无鉴权面？ | 原始卡号写入 | 未授权写/支付敏感 | 已批量回灌 | Wolt payment-service 匿名未授权批量写入原始卡号 |
| 2026-09-10 | 命中 | Vercel OSS·HTTP客户端 | 跨源 302 是否剥离 Authorization/Cookie？URL 拉取是否挡内网？ | redirect follow / fetch URL | SSRF/凭证泄露 | 已批量回灌 | @emulators/linear GraphQL treats unauthenticated requests as admin — webhook ret… |

| 2026-09-10 | 命中 | 宇树·UnifoLM 论坛 | 富文本 content 入库是否零过滤？详情/评论渲染是否未消毒直插（如 dangerouslySetInnerHTML）？ | 帖子/话题/评论 content HTML | 存储型 XSS | 已批量回灌 | 宇树 unifolm 存储型XSS（正文/评论） |
| 2026-09-10 | 命中 | 宇树·统一账号 | 论坛等业务签发的 token 是否跨 security/钱包等面通用？XSS 窃票是否等于跨业务接管？ | localStorage token / token 请求头 | 会话票跨业务无隔离 | 已批量回灌 | 宇树 unifolm XSS 升链统一账号 |
| 2026-09-10 | 命中 | 宇树·UnifoLM 前端 | 构建产物是否硬编码**有效**第三方 API Key（无后端代理）？ | 前端 JS Bearer/sk | 敏感信息泄露/硬编码密钥 | 已批量回灌 | 宇树 unifolm DeepSeek Key 硬编码 |
| 2026-09-10 | 命中 | 宇树·UniStore | 应用商店上传签名/OSS 直传是否允许可执行内容类型，对象 URL 是否被同源当页面执行？ | 上传签名口 + OSS 对象 | 存储型 XSS/上传 | 已批量回灌 | 宇树 UniStore 匿名上传存储XSS |

| 2026-09-10 | 命中 | 通用·服务端拉 URL | 后缀白名单若用 urlparse 取 hostname、请求用 urllib3，二者对 `\` 是否一致？单 `@` 放行是否等于请求也打到白名单？ | 可控拉取 URL + 域名后缀白名单 | SSRF/解析器差分 | 已写入短表+ssrf-test | 公号文：一次有意思的ssrf绕过 |

| 2026-09-10 | 命中 | 配置中心·多作用域鉴权 | 管理写接口是否落在默认关闭的 Open 作用域？Admin 对照口拒绝时，用户/角色/权限写口是否仍放行？ | @Secured apiType / 多 Filter | 鉴权作用域错配 | 已写入短表+authbypass | Nacos 3.x 鉴权作用域错配分析 |
| 2026-09-11 | 命中 | 数据科学协作·Frappe 市场 | 未登录市场列表是否过滤上架？git 克隆 URI 是否把账密当字段吐给前端？这把克隆口令绑一个仓还是组织？ | Agent/模型市场 list + codeup_git_uri | 未授权读/凭证外泄 | 已写入短表+info-leak | 理想连山模型市场匿名未授权读取未发布Agent并泄露Codeup仓库克隆凭证 |
| 2026-09-11 | 命中 | 数据科学协作·Frappe Desk | 游客共享租户 Desk Viewer 对 User 是否全表 select？文档 get 403 时 get_list/get_value 是否仍出他人手机？ | User doctype list/get_value | BOLA/过量暴露 | 已回灌 | 理想连山游客租户越权批量读取他人用户姓名邮箱与手机号 |
| 2026-09-11 | 命中 | 巨量引擎·试玩素材后端 | 列表口的广告主号是授权还是路由键？哨兵 0/-1 是否整表未过审正文？ | aadvid/advId 列表 | 未授权读/哨兵租户 | 已写入 suspects | 巨量引擎试玩素材后端匿名未授权批量读取他人试玩素材详情及审核正文 |
| 2026-09-11 | 命中 | 巨量引擎·试玩素材广告平台后端 | 同 list 口换 host 是否仍信 aadvid=-1？ | playable-ad-platform /api/playable/list | 未授权读/哨兵租户 | 已有短表不进新行 | 巨量引擎试玩素材广告平台后端匿名未授权批量读取他人试玩素材详情及审核正文 |
| 2026-09-11 | 命中 | 巨量算数·洞察 CMS | 列表可见性是否只挡列表不挡未上架详情正文和附件？ | insight id + status=1 | 未授权读（列表≠详情） | 已写入 suspects | 巨量算数匿名未授权批量读取他人未发布洞察报告正文及附件 |
| 2026-09-11 | 命中 | 抖音创作者中心·洞察 CMS | 同 insight 详情口换 host 是否仍出未上架 PDF？ | creator /api/v2/insight/{id} | 未授权读（列表≠详情） | 已有短表不进新行 | 抖音创作者中心匿名未授权批量读取他人未发布洞察报告正文及附件 |
| 2026-09-11 | 命中 | 巨量引擎·品牌橱窗 | 列表可见性参是否信客户端枚举（含 DELETE/已删除）？前端不带的状态服务端是否仍出未上架正文？ | status_list 产品列表 | 未授权读（列表过滤当授权） | 已写入 suspects | 巨量引擎品牌橱窗匿名未授权批量读取已删除广告产品详情 |
| 2026-09-11 | 命中 | 巨量引擎·帮助 CMS | 默认对外 space 是否等于全部知识库授权？spaceId=-1 / 跨空间检索是否仍出内部/测试库正文？详情无权限时检索是否仍带正文？ | spaceId=-1 + keyWord/detail | 未授权读/内部知识库 | 已写入 suspects；拟补短表内部话术打法 | 巨量引擎帮助中心匿名未授权批量读取内部知识库正文 |
| 2026-09-11 | 命中 | 巨量学·企业直播观看页 | 未登录 permission 是否明文下发自定义登录 SecretKey？这把钥绑谁、能到哪（进房 JWT / 点播回放）？ | permission.SecretKey + HMAC Sign | 令牌半径/未授权读 | 已写入 suspects；拟补短表云录制分享 | 巨量学直播匿名未授权进入直播间并批量读取内部培训回放正文 |
| 2026-09-11 | 命中 | 巨量引擎·SparkStone | 列表可见性是否只挡广场卡片、不挡未发布/测试态任务正文？taskStatus=1/40 是否服务端信客户端？ | taskStatus 任务列表/详情 | 未授权读（列表过滤当授权） | 已写入 suspects | 巨量引擎SparkStone专家数据平台匿名未授权批量读取未发布任务正文 |
| 2026-09-11 | 命中 | 小鹏·收银台发票 | 发票抬头联想是否把开票库当公开补全、不要登录？回包是否夹带银行账号和开票手机？ | associate/head entName | 未授权读/PII | 已进短表（公司名/抬头自动完成） | 小鹏收银台发票抬头联想 |
| 2026-09-11 | 命中 | 小鹏·购车配置器 | 列表可见性参缺省或哨兵 0 是否把「仅内部可见」方案当不过滤？ | financial/products pageId | 未授权读（列表过滤当授权） | 已写入 suspects 复盘 | 小鹏购车配置器内部金融方案 |
| 2026-09-11 | 命中 | 小鹏·保险理赔门户 | 后台用户分页列表是否误挂成匿名可读？登录墙是否只挡 SPA 不挡 `/api/caseUser`？ | caseUser/pageQueryList | 未授权读/内部账号 | 已写入 suspects 复盘 | 小鹏保险理赔门户内部账号列表 |
| 2026-09-11 | 命中 | 小鹏·云影像/PACS | 医院号/患者 id 是授权还是路由键？未登录 `/api/hospital/{id}/patients` 是否出身份证手机和报告正文？ | hospitalId + patients/doctors | 未授权读/PII/医疗正文 | 已写入 suspects 复盘；不进短表（名单未登录出整表已有同类） | 小鹏云影像诊断系统患者身份证手机报告 |
| 2026-09-11 | 命中 | 火山引擎·Agent 开发者社区 | 公开 innertop 列表把草稿做成可查询 Status，未登录是否仍出未发布赛事详情/评分正文？ | CompetitionPub Status=草稿 + SubPublicID 详情 | 未授权读（列表过滤当授权） | 已有短表不进新行 | 火山引擎Agent开发者社区匿名未授权批量读取未发布火山杯草稿赛事 |
| 2026-09-11 | 命中 | 火山引擎·文档中心 PlatformFE | 文档壳/preview 闸是否等于搜索 FullContent 与默认详情附件鉴权？隐藏 Status 是否只挡页面？ | type=preview 401 vs openSearchNew FullContent + getDocDetail Status=5 + CDN 直链 | 未授权读（列表≠详情） | 已补短表文档站语义搜索 | 火山引擎文档中心匿名未授权读取隐藏发布测试库正文及内部后端设计文档 |
| 2026-09-11 | 命中 | 火山引擎·veImageX 体验 | 云产品体验/测速口未登录领 STS 时，票是否可调 GetCallerIdentity 问出 AccountId？策略是否超出一次性上传签？ | GetSpeedtestUploadToken → STS 临时 AK/SK | 未授权读/云临时钥 | 已有短表演示号领云钥不进新行 | veImageX体验版匿名未授权领取云临时钥并问出火山账号身份 |
| 2026-09-11 | 命中 | 火山引擎·vaka AI 搜索 | 生产 API 是否信客户端环境/灰度头（前端生产包不带）从而切换租户或数据集？ | from-ark-exp 头 + list_v3 | 未授权读（客户端头当鉴权） | 待 hunt-iter | 火山引擎vaka AI搜索匿名未授权批量读取他人团队知识库文档摘要 |

| 2026-09-17 | 命中 | 携程·旅游百事通BST | 公告中转未登录时，来源校验是吃 body.source 还是自定义头（如 x-tour-auth-from）？空包+来源头是否仍出 isOnline=F 未发布正文？ | queryBulletin + x-tour-auth-from | 未授权读（列表过滤当授权/来源头） | 已补短表/idor 第25步 | 携程_V3 旅游百事通bst匿名未授权批量读取他人供应商内部公告正文及未发布签证费结算规则 |
| 2026-09-17 | 命中 | 携程·度假供应商VBK | 帮助详情壳 302 登录时，检索/LLM/必须阅读公告详情是否仍匿名出内部正文和附件直链？ | searchArticle + getLLMAnswer + viewBulletin | 未授权读（登录墙≠正文 API） | 已有短表文档站语义搜索不进新行 | 携程_V3 度假供应商平台vbooking匿名未授权读取内部帮助中心知识库正文及必须阅读供应商公告 |
| 2026-09-17 | 命中 | 携程·内容中心学院 | 学院 SPA 302 登录是否等于课程目录/列表 API 也闸？附件 PDF 直链是否仍匿名可读？ | getCourseDirectorys + getCoursesList + PDF | 未授权读（登录墙≠正文 API） | 已补短表文档站语义搜索打哪 | 携程_V3 内容中心匿名未授权批量读取创作者学院内部培训课程正文及附件 |
| 2026-09-17 | 命中 | 携程·开放平台联盟 | 联盟直播中心登录墙是否挡住选品货盘 API？同中心机票/度假闸了，酒店货盘是否漏？ | 14984/selectionCenterHotelProductList | 未授权读（登录墙≠货盘 API） | 中危不进短表 | 携程_V3 开放平台联盟匿名未授权读取直播选品中心酒店货盘佣金与GMV |
| 2026-09-17 | 命中 | 携程·程易行 | 入驻写口是否只验前端写死 MD5 盐、不验登录也不验真短信码？过签是否等于能写审核队列？ | companyRegister/submitInfo + checkHasSubmit | 未授权写（客户端签名当鉴权） | 中危不进短表 | 携程_V3 程易行匿名未授权提交车企入驻申请 |
| 2026-09-17 | 命中 | 携程·招聘门户 | 公开列表/关键字搜 0 条是否等于详情也闸？同一口 fromId/职位编号是否仍出未上架/测试岗全文？ | getJobAd condition.fromId | 未授权读（列表过滤≠详情授权） | 已补短表/idor 列表过滤详情不闸 | 携程_V3 招聘careers匿名未授权批量读取未上架职位详情正文 |

## 高频问句速查（从本表提炼，可增不可灌 payload）
- 列表/目录的可见性过滤，是否被错误当成详情口的授权？（未上架/已删除仍出全文）

- 这个 id/ticket/sign 是**授权凭证**还是**仅路由键**？换他人值后差分是什么？
- 字段在客户端可见/可改，服务端是否**重算或从会话取**？
- 「有校验外观」的防线（验证码/审核/验签）失败时是**硬拒绝**还是**软忽略**？
- 未登录详情/配置是否夹带**可当会话或内容票**的串？
- 登录后懒加载 chunk 是否比 anon 包多出**商家/租户对象图**？
- 草稿/未发布/下架/已删除状态，是否只挡**列表**不挡**详情正文**？
- 图片代理 / `_next/image` / `api-proxy` / `from-image-url` 是否把任意 URL 当可信拉取源（内网/corp/loopback）？
- 公开榜单/精选/橱窗接口是否把**非展示字段**（邮箱、运营人、内部 id）一并吐出？
- 列表可见性参缺省或哨兵 0，是否把「仅内部可见」方案当不过滤？
- 后台用户/账号分页列表是否未登录就出整表工号姓名？登录墙是否只挡 SPA 不挡 `/api/*User*`？
- 登录墙/文档壳是否只挡页面，**正文 API** 仍匿名可读？
- 「我的物流/已购/订单」缺参或缺会话时，是拒绝还是吐整表？
- 公开主页/用户资料口是否把 CRM/wecom 内部运营标签当 FinalInfo 一并吐出？
- 行程分享/出图口未登录换可遍历订单号，是否仍签发分享票并带入住日期？
- 同中心多货盘/多品类口，是不是只闸了一部分、漏了一条名单？
- 入驻/申请写口是否只验前端写死盐、不验登录也不验真短信码？
- 公告口报「访问来源无效」时，来源是 body 字段还是自定义请求头？
- 客户端可控头/字段（如自定义 username）是否被服务端当成**身份主体**？
- OAuth/`state.url`/callback 是否校验为本域，code 是否原样外带？
- 前端写死的 token/密钥是否可被当成**会话凭证**直接建连？
- 配置下发（Apollo/低代码数据源）是否把 **PII** 写进可匿名拉取的配置？
- 富文本入库是否**零过滤**，前端渲染是否**未消毒直插**（存储型 XSS）？
- 业务 token 是否存在 **localStorage/自定义头** 且跨多个子业务通用？
- 前端构建产物是否硬编码**有效**第三方 API Key（应走后端代理）？
- 对象存储直传是否允许 HTML/SVG 等可执行 MIME，并被同源打开执行？
- 服务端拉 URL 的白名单：校验用的解析器与真正发请求的库，对 `@` / `\` 是否同一套规则？
- 多 Filter/多 apiType 鉴权：管理写口是否漏标、掉进默认不鉴权作用域？
- skip_auth/webhook 豁免正则是否匹配**完整 URI（含 query）**且未锚定？
- 白名单校验解析失败时，是拒绝还是**静默跳过**仍出站？
- 多 IdP 的 state/nonce/pkce cookie 是否绑定 provider？
- OAuth state 是否同时满足：高熵、绑会话、跨 CLI/网页不互换？
- MCP/OAuth 401 的 resource_metadata 是否先 fetch 再验同源？
- Mermaid/图渲染是否在 sanitize 之前就执行 HTML 事件？

- Desk/低代码 Viewer：文档 get 403 时，get_list / get_value / select 是否仍出他人手机？
- 这张票/令牌**绑的是谁**（本号、本店、本租户，还是供应商下游）？
- 令牌**能到哪**（单接口、整 sid 后台、还是跨产品线）？过期/吊销后下游是否仍通？
- 换 `tenantId`/`shopId`/`Account-Id` 后，是会话绑死本号，还是出现**跨租户墙缺口**？
- 会话仓 / 刷新票 / 多 sid 换票：换票成功是否仍等于**无业务身份**（空户）？
- GET 被 WAF 405 时，同 path POST 空包是否仍抠到 Controller 写方法并进 ORM？id 从会话取还是信客户端？
- 网关 IP 白名单若只拦字面 path，Spring `.json`/`.do` 后缀是否仍进同一写方法？
## 与 suspects 的关系

- `suspects.md` = **本站**发现清单（任务目录）。
- 本文件 = **跨任务**记忆（skill 知识库）。
- 确认后：suspects 行标 `confirmed`，并在本表加一行「命中」。
- 测完才发现该问没问：本表加「漏报」，并补进该站 suspects（即便已 DONE，写补丁节）。

| 2026-09-10 | 命中 | 店长直聘·H5反爬 | 前端跳转/回调写死的域名后缀白名单，其域当前是否仍归公司所有、是否定期审计？ | 滑块页 redirect 白名单 + reason 文案 | 开放重定向/白名单脱管域 | 已写入 suspects 复盘 | 店长直聘H5滑块验证页redirect白名单含可注册域名致开放重定向钓鱼 |
| 2026-09-10 | 命中 | 快手本地生活·商家中心登录轨 | 服务端代拉口是否「先拉取后校验」——回包错误文本（类型/尺寸不符）能否单独当带内拉取证明？OOB 零命中时是否就敢判半条？ | 换唯一外带地址 + 回包「图片宽度不能低于50」带内证明，OOB 回连连判 | 盲SSRF实锤（生产侧出口回连，okhttp UA） | 报告已落；同根因扩 llsp/data 两 host | 快手生活服务商家中心图片代拉接口盲SSRF（服务端可请求任意外部URL） |
| 2026-09-12 | 命中 | 小鹏·消息中心UAT | 多前缀网关按 path 拆鉴权时，管理前缀（/logan/** 类）是否漏挂同一 appId 签名闸？管理视角是否由请求参数 isAdmin/roleId 自报决定？推送/撤回写口是否校验调用方凭证？ | 同 artifact 生产 sibling spec 被 WAF、UAT spec 全开；/logan/ 匿名 total=4.6w | 消息中台管理族匿名未授权读+写面（中危，报告已落） | 已写入 suspects；生产同口 WAF 拦未复现 | 小鹏消息中心UAT /logan/** 管理族绕过网关签名闸匿名读推送风控记录并开放推送撤回写面 |
| 2026-09-12 | 命中 | 理想·MinIO Console | 活动站根域 NXDOMAIN / 443 死后，同 IP 上的 MinIO Console 是否仍对公网开放？发行默认口是否还被生产认？ | Console `/api/v1/login` 默认口 + `/api/v1/buckets` | 组件默认口/对象存储管理面 | 已写入 suspects；不进短表（无新认的通用枪） | 理想超充惊喜来电MinIO控制台默认口进入管理员会话并列出存储桶 |
| 2026-09-12 | 命中 | 理想·访客邀约打印 | 打印/设备口的 `ip`/`host` 是否信客户端？未登录 JSON 是否仍拿该地址出站？耗时/回文能否当连通性探针？ | POST `/api/print/visitor` + ip | SSRF（客户端地址当出站目标） | 已写入 suspects；中危不进短表 | 理想访客邀约H5匿名未授权通过打印接口连接任意IP打印机 |
| 2026-09-12 | 命中 | 小鹏·数字售后VOSS staging | 客户端身份头（xp-uid）是否被服务端当成登录主体？生产 sibling 的客户端头闸卸掉后，业务 JSON 口是否仍匿名可读？这把头绑谁、换数字是否换成他人手机住址？ | 业务 JSON 口 + xp-uid/XP-UID 头 | 自定义身份头当会话/未授权读/PII | 已补短表「自定义身份头当会话」打哪；令牌半径问句 | 小鹏数字售后VOSS测试环境匿名未授权批量读取他人维保联系人姓名手机住址 |
| 2026-09-12 | 命中 | 小鹏·骁龙 Pandora Docker staging | GET 被 WAF 405 时，同 path 的 POST 空包是否仍打到 *ConfigController.addXxx 并进 Hibernate？accountId 是会话主体还是客户端路由键？删除口是否同样不要登录？ | POST/DELETE `/configs` + accountId | 未授权写（测试环境配置口漏鉴权） | 已写入 suspects 复盘；中危不进短表 | 小鹏骁龙Pandora Docker测试环境平台配置接口匿名未授权新增与删除 |
| 2026-09-12 | 命中 | 小鹏·骁龙 Pandora Docker 生产 | 网关 IP 白名单若只拦字面 `/configs`，Spring 后缀 `/configs.json` `/configs.do` 空 POST 是否仍抠到同一 Controller 并进 Hibernate？生产 sibling 的 IP 闸是否等于应用鉴权？ | POST/DELETE `/configs.json` + accountId | 未授权写（网关字面 path 闸 vs Spring 后缀匹配） | 已写入 suspects；中危不进短表 | 小鹏骁龙Pandora Docker生产环境平台配置接口匿名未授权新增与删除 |
| 2026-09-12 | 命中 | 携程·度假供应商VBK | 登录墙/帮助详情壳是否只挡页面，检索/LLM 正文 API 仍匿名可读？ | searchStreamTrigger + getLLMAnswer | 未授权读（列表≠详情/内部知识库） | 已写入 suspects；拟补短表文档站语义搜索 | 携程度假供应商平台vbooking匿名未授权读取内部帮助中心知识库正文及飞单处罚规则 |
| 2026-09-12 | 命中 | 携程·旅游百事通BST | 公告页中转「当前用户未登录」是否等于列表/详情 API 也闸？queryBulletin 空标题是否仍出 isOnline=F 未发布稿，viewBulletin 是否仍出正文和附件链？ | queryBulletin + viewBulletin + isOnline=F | 未授权读（列表过滤当授权/未发布公告） | 已写入 suspects；拟补短表列表过滤详情不闸 | 携程旅游百事通bst匿名未授权批量读取他人供应商内部公告正文及未发布签证费结算规则 |
| 2026-09-12 | 命中 | 小米·海外招聘 CMS | 公开轮播只挂部分数字 id 时，详情口换列表没有的邻号是否仍出未发布测试稿/宣讲全文？ | careerDetail?id= | 未授权读（列表≠详情） | 已有短表不进新行 | Xiaomi Careers匿名未授权批量读取未发布校园招聘活动详情正文 |
| 2026-09-12 | 命中 | 小米电视·H5 CMS | 福利页 JS 写死的 page-config/actinfo 数字 id，列表未挂时详情是否仍出测试稿、online=0、运营勿动模板全文？ | page-config/{id} / actinfo/get/{actId} | 未授权读（列表≠详情） | 已有短表不进新行 | 小米电视H5匿名未授权批量读取测试及已下线红包雨活动配置 |
| 2026-09-12 | 命中 | 抖店·源头好货 H5 | 公开货盘抄到的 supplierId/shopId 是授权还是路由键？未登录打联系人/资质是否仍出手机和执照原图？ | showSupplierInfoForDistributor?supplierId= / queryContactInfo?shopId= | 未授权读/PII（id 当路由键） | 已写入 suspects；不进短表（无新认的通用枪） | 抖货源头好货匿名未授权批量读取他人供应商联系人手机及营业执照 |
| 2026-09-12 | 命中 | 抖店·源头好货 H5 | 未登录 shopLoginInfo 是否下发真实店铺号？供销订单列表是否按登录主体过滤，还是空参就出他店单和运单？ | shopLoginInfo.mainShopId + channelTrade/orderList | 未授权读（列表未绑会话/租户键） | 已写入 suspects；中危不进短表 | 抖货源头好货匿名未授权批量读取他人分销订单及运单号 |
| 2026-09-13 | 命中 | 携程·信息安全部问卷 | 问卷详情数字 id 是授权还是路由键？登录墙是否只挡 SPA、不挡 `/api/safe_audit` 详情？匿名读到的是内部评审题干还是已填答卷？ | questionnaireId 详情 | 未授权读（id 当路由键/内部问卷模型） | 已写入 suspects；不进短表（无新认的通用枪） | 携程信息安全部问卷系统匿名未授权批量读取内部安全评估问卷正文 |
| 2026-09-13 | 命中 | 携程·TripPal 管理后台 | 游客/OAuth 换票 callback 的 `code` 是否当 HTML 原文拼进 inline script？HTML 先闭合 `</script>` 是否比 JS 字符串转义先发生？管理员 `/redirect` WAF 是否等于游客 `/toTouristsLogin` 也闸？ | toTouristsLogin?code= | 反射 XSS（换票页拼 HTML） | 已写入 suspects；中危不进短表 | 携程TripPal管理后台游客换票页匿名反射型XSS |
| 2026-09-13 | 命中 | 小红书·资质审核 edith list | 登录墙/`请登录` 是否只挡 SPA 和 `/api/qual/*`？缺分页空列表、带 `pageNum` 是否仍匿名出全量待审名单？详情 path 404 是否等于名单也闸？ | `/api/edith/life/merchant/apply/list?pageNum=` | 未授权读（分页当鉴权） | 已写入 suspects；中危不进短表 | 小红书资质审核平台匿名未授权批量获取他人本地生活商家入驻申请 |
| 2026-09-13 | 命中 | 携程·集团官网 CMS | 官网前台空标题/SSR 无正文是否等于详情 API 也闸？列表只出 publishStatus=1 时，详情换列表没有的 id 是否仍出 publishStatus=0 全文和编辑工号？ | findArticlesInfo + id | 未授权读（列表过滤≠详情授权/未发布稿） | 已写入 suspects；补短表列表过滤详情不闸别停 | 携程集团官网匿名未授权读取未发布媒体稿正文 |
| 2026-09-13 | 命中 | 滴滴·社会招聘门户 | 对外列表用 JR 编号滤掉已下架时，详情数字 id 是否仍出 jdStatus=3 岗位职责/任职要求全文？ | /job/front/list vs /job/front/view/{id} | 未授权读（列表过滤≠详情授权/已下架正文） | 已有短表不进新行 | 滴滴招聘门户匿名未授权批量读取已下架职位详情正文 |
| 2026-09-14 | 命中 | 荣耀·亲选商家运营台 | 商家台「所有业务口要会话」是否等于网关上的平台参数查询口也闸？前端 becode 头当业务路由键时，/sop/* 参数服务是否被当配置面漏在鉴权矩阵外？空 body 是否就出整表？ | POST /sop/modulesParamService/queryModulesParams 空 body | 未授权读（平台配置整表/内部员工邮箱/邀请码模板/店铺映射） | 已写入 suspects；中危不进短表 | 荣耀亲选商家运营台匿名未授权读取平台内部运营配置及员工邮箱 |
| 2026-09-14 | 漏报 | 荣耀·Honor ID CAS | service=/loginUrl= 白名单在边缘层是「包含 honor.com 子串」弱匹配（honor.com.evil.example 302 过闸存活整条 pre-auth 链）——应用层回落默认 service 兜住了发放环节；其他 SSO 接入方的应用层是否都有这道兜底？边缘弱白名单+应用层校验「双闸」是否被当成互备而双双放松？ | /CAS/remoteLogin?service= | 令牌半径（ST 发放锚定） | suspects 补丁节已记；未成报（链断于应用层） | 荣耀CAS service 白名单边缘弱匹配（发放环节应用层兜底） |
| 2026-09-14 | 命中 | 荣耀·Honor ID IDM_W | isExsitUser 的 existAccountFlag 与 getUserAccInfo operType=5 是否构成未登录账号枚举 oracle？掩码回包是否仍泄露账号状态/类型？ | isExsitUser + getUserAccInfo(operType=5) | 用户枚举 oracle | 已写入 suspects；低危不单独成报 | 荣耀ID账号域未登录用户枚举原语 |
| 2026-09-15 | 命中 | 荣耀·云空间 | 文件内容口的闸谱（未登录→会话→2FA→参数校验→归属）逐层回码不同——后续站排号是否都先画闸谱再判「票死」？AGW 缺浏览器 UA/origin 头会不会假报票死？HttpOnly 键没进会话文件是不是「会话失效」的真因？ | fileproxy/files/content 等内容口 | 会话闸谱方法论（40024→40014→20002→归属） | 已写入 suspects 补丁节；S-1 空户不可枚举收口 | 荣耀云空间内容口闸谱与归属层不可达（空户） |
| 2026-09-15 | 命中 | 荣耀·YOYO 客服 | 会话态无参口 mcpQueryUserinfo 是否把「userId+新签 JWT+手机号明文」拼进身份交接 URL？这类交接 URL 是否就是后续 clientLogin 的登录凭证（URL 进日志/Referer 即泄露会话）？ | GET /venus/sso/mcpQueryUserinfo | 令牌半径/凭证交接 URL 明文 | 已写入 suspects；涉令牌中危，S-01 升链候选 | 荣耀YOYO客服mcpQueryUserinfo身份交接URL携带明文手机号与新签JWT |
| 2026-09-15 | 漏报 | 荣耀·YOYO SSO | authorizeUriV2 对 yoyo_uri 签发端不校验（外域原样嵌 redirect_uri）——半链实锤；但 clientLoginV2 交接端对 http 目标 500，凭证投递未证实。「签发不校验+交接报错」的组合在其他 SSO 是否也存在（签发端宽松≠可利用，交接端才是闸）？ | /venus/sso/authorizeUriV2 + /venus/sso/clientLoginV2 | 开放重定向半链/凭证交接 | suspects 补丁节；不单独成报 | 荣耀YOYO authorizeUriV2 签发端不校验回跳域（交接端 500 挡路） |
| 2026-09-15 | 命中 | 荣耀·俱乐部 Discuz | 编辑器「恢复已保存内容」这类辅助口（loadsave/autosave/preview）是否在鉴权矩阵外？草稿保存成功≠草稿不可读——按 pid 匿名直读是否回显未公开全文？pid 自增是否可批量？ | GET forum.php?mod=misc&action=loadsave&pid= | 未授权读（辅助口漏鉴权/未公开正文+批量） | 高危已成报（【双十一】俱乐部 loadsave） | 荣耀俱乐部loadsave接口未授权批量读取他人未公开草稿正文 |
| 2026-09-16 | 命中 | 喜马拉雅·广告CMS | 列表只出 ONLINE 时，详情是否仍信数字 id 吐 OFFLINE/测试稿全文？ | POST /ad-market/ad/case/query?id= | 未授权读（列表≠详情） | 已有短表不进新行 | 喜马拉雅广告投放平台匿名未授权批量读取他人未上线广告案例详情正文 |
| 2026-09-16 | 命中 | 喜马拉雅·开放平台文档 | 未登录文档详情是否下发线上联调 AppSecret？内容网关是否真挂测试应用 IP 白名单？ | /api-docs/document?id= + HMAC sig | 令牌半径/凭证外泄 | 已有短表不进新行 | 喜马拉雅开放平台文档匿名未授权读取联调AppSecret并可现签生产内容接口 |
| 2026-09-16 | 命中 | 喜马拉雅·C端播放 | 未登录播放详情是否仍 isAuthorized 并下发 playUrlList？前端 AES 钥解开后假 sign 是否 403？ | /mobile-playpage/track/v3/baseInfo + playUrlList | 令牌半径/未授权读 | 已补短表详情吐内容访问票 | 喜马拉雅主站匿名未授权批量获取他人付费声音播放地址并下载全文音频 |
| 2026-09-16 | 命中 | 喜马拉雅·A+配音 | 列表默认可见性是否等于详情授权？viewStatusId 改成已完结/制作中是否吐未上墙任务正文和内部邮箱？ | GET /api/requirement/query?viewStatusId= + /detail | 未授权读（列表≠详情） | 已有短表不进新行 | 喜马拉雅A+配音平台匿名未授权批量读取他人已完结及制作中配音任务详情正文 |
| 2026-09-16 | 命中 | 喜马拉雅·小喜马试听 | JSON sampleDuration=180 是否等于文件截断？playPath 走 redirect/free/play 后 audiopay 体积是否仍是正片？ | POST /mobile/album/trackRecord/querySampleTrack | 令牌半径/未授权读 | 已补短表详情吐内容访问票 | 喜马拉雅小喜马xxm匿名未授权批量获取他人付费声音播放地址并下载全文音频 |
| 2026-09-16 | 命中 | 喜马拉雅·HAS | 前端写死长期 JWT 是否生产认？假 JWT decode error、真票是否出身份+内部 demo 音色？ | GET /has/v1/user/info + /has/vc/api/v1/voices | 令牌半径 | 已有短表不进新行 | 喜马拉雅音频智能底座HAS匿名未授权使用前端写死JWT读取业务身份与内部demo音色 |
| 2026-09-16 | 命中 | 喜马拉雅·开放支付 | 联调钥现签后，梯度价口是否接受任意 uid 回已购/待付差分？ | POST /omp-payment-open-api/get_gradient_activity_price_info | 未授权读（换 id） | 不进短表 | 喜马拉雅开放支付梯度价接口匿名未授权查询他人是否已购买付费声音 |
| 2026-09-16 | 命中 | 喜马拉雅·会员H5 | 会员资料口是否把 query uid 当路由键，未登录换号是否出昵称/到期/累计？ | GET /business-vip-level-h5-web/api/profile?uid= | 未授权读（换 id） | 不进短表 | 喜马拉雅会员等级H5匿名未授权读取他人会员资料 |
| 2026-09-16 | 命中 | 喜马拉雅·开放API | 联调 secret 换 client_credentials 是否只出 uid=0 应用票？用户口是否仍 102/610？ | POST /oauth2/secure_access_token | 令牌半径 | 不进短表 | api.ximalaya.com DONE_anon |
| 2026-09-16 | 命中 | 喜马拉雅·cupload | 前端写死 HMAC+占位 token 时，换 /backend/ 分片合并是否绕开 clamper-token 登录闸？CDN 对 HTML 是否按 text/html 打开？ | POST /upload/file/backend/blk + /upload/merge/backend/mkfile | 未授权写/存储XSS | 中危不进短表 | 喜马拉雅cupload匿名未授权任意上传HTML至官方CDN |
| 2026-09-16 | 命中 | 喜马拉雅·城文销售 | 运营 toolbox 是否无登录仍出他号手机、供应商对公卡？ | /toolbox/xmly/account/query + /toolbox/supplier-search/page | 未授权读 | 不进短表 | 城文销售两篇高危 |
| 2026-09-16 | 命中 | 喜马拉雅·会员成长 | 成长明细是否把 query uid 当路由键？ | GET /business-vip-level-h5-web/api/growth/detail?uid= | 未授权读（换 id） | 不进短表 | 喜马拉雅会员站匿名未授权批量读取他人会员成长明细 |
| 2026-09-16 | 命中 | 喜马拉雅·system网关 | UNPath 壳是否漏挂会员 H5，uid 当路由键？ | GET system.ximalaya.com/business-vip-level-h5-web/api/profile?uid= | 未授权读 | 不进短表 | 喜马拉雅system网关匿名未授权批量读取他人会员资料及成长明细 |
| 2026-09-16 | 命中 | 喜马拉雅·直播WSA | 广场只出在播时，已结束详情是否仍 hasAuth=false 却下发完整 playbackPath？COS Range 是否正片体积？ | GET /diablo-web/v1/live/record/detail?id= | 未授权读（列表≠详情+内容票） | 已有短表不进新行 | 喜马拉雅直播WSA匿名未授权批量获取他人课程直播回放正片 |
| 2026-09-16 | 命中 | 喜马拉雅·活动营 | HMAC 钥是否就是 timestamp？path 带 h5noCheck 时假签失败、真签是否出成员手机？ | GET .../h5noCheck/.../getSearchList | 令牌半径/未授权读 | 已补短表写死签名盐 | 喜马拉雅活动营匿名未授权批量读取他人红旗活动战队成员手机号 |
| 2026-09-16 | 命中 | 喜马拉雅·广告私信 | 登录墙是否只挡 /ad-mission/ 页面，imChat 读写口是否信客户端 fromUid？ | POST createRelationMsg + GET getContactsByUid | 未授权写/读 | 中危不进短表 | 喜马拉雅消息中心匿名未授权向任意账号写入并读取广告私信联系人 |
- 2026-09-16 蚂蚁(appstore.alipay.com) 命中｜同皮老橱窗 velocity 模板是否共用 hash→jQuery selector 直连件（无过滤 $(location.hash) 直达低版 jQuery 选择器 buildFragment 分支）：本站实证（jQuery 1.7.2、无 CSP、主域内执行）；后续对同皮老橱窗页先比对 inline JS 模板注释（uitpl/FD:106 类）再测 hash 面。
| 2026-09-19 | 命中 | 唯品会·visapp 统一工作平台 | 业务会话票（encrypt 头）存 Web Storage（sessionStorage.__token__）且无 HttpOnly，经自定义头透传+vipoa:// 原生桥+castgc 主站态同仓——JSONP callback 反射即可窃票换会话？跨产品线 token 通用半径/吊销是否独立？ | POST /biwapp/*（encrypt 头）+ JSONP /agencys/selectAgencys | 令牌半径/XSS | 中危不进短表 | visapp 匿名 JSONP 反射 XSS 可窃 Web Storage 会话令牌 |
| 2026-09-20 | 命中 | 唯品会·VOP 开放平台 | 公告列表可见性（当前挂出 111 条）是否等于详情授权？列表没有的自增 id 详情是否仍出未上架管理/对接全文？ | GET /api/announcement/list vs /api/announcement/get?id= | 未授权读（列表≠详情） | 已有短表不进新行 | 唯品会VIP开放平台匿名未授权批量读取未上架平台公告正文 |
| 2026-09-20 | 命中 | 唯品会·唯享客 jingxuan | 登录墙 JSON「请登录」是否等于列表 API 也闸？客户端旗 notNeedLogin=true / preview 是否被服务端当成授权，从而吐登录墙后的佣金/GMV 规则？ | GET /api/v1/activity/list?notNeedLogin=true | 未授权读（客户端旗当鉴权） | 中危不进短表 | 唯品会唯享客匿名未授权读取登录墙后的推广活动佣金与GMV奖励规则 |
| 2026-09-20 | 命中 | 唯品会·公益 H5 | 对外目录 537 条（id 326–1072）是否等于详情授权？列表没有的 charityId 详情是否仍出 state=0 未上架/测试全文？ | POST /api/charity/charityMain/getCharityDetail | 未授权读（列表≠详情） | 已有短表不进新行 | 唯品会公益H5匿名未授权批量读取未上架及测试公益项目详情正文 |
| 2026-09-20 | 命中 | 美团·牵牛花商家中台 | 客服门户签发口的 openId/appKey 是会话主体还是客户端路由键？签出的 cs_signature 绑谁、换 openId 是否换成他人客服身份？ | POST /customer/getCustomerServiceUrl openId + kf init cs_signature | 令牌半径/未授权读 | 中危不进短表 | 牵牛花匿名未授权任意读取他人客服门户账号身份 |
| 2026-09-20 | 命中 | 美团·大学学院 SPA | 公开搜索 total=0 / 课 needLogin=1 是否等于详情和导学 RPC 也闸？前端上架旗是否被服务端当成授权？ | tdx 详情 RPC + 导学 guide RPC + X-Tenant | 未授权读（列表≠详情） | 已补短表学院/培训 SPA 打哪 | 美团大学匿名未授权批量读取未上架认证课详情与内部商家培训正文 |
| 2026-09-20 | 命中 | 美团·海盐 IoT 中台 | Shepherd `/gw` 按 path 拆鉴权时，同前缀少数写口是否漏挂员工 SSO（其它口 50102、该族 POST 匿名 code=0 且落库）？ | POST /gw/datawarehouse/v1/preOpeningTraffic/submitInspection | 未授权写 | 中危不进短表 | 海盐平台匿名未授权任意写入开业客流巡检记录 |
| 2026-09-20 | 命中 | 美团·餐饮课堂 | 公开搜索 total=0 / 播放已下线是否等于详情也闸？status=0 已下架课详情是否仍出课纲？ | GET /gw/xueyuan/course/detail?courseId= | 未授权读（列表≠详情） | 已有短表不进新行；中危不进短表 | 美团餐饮课堂匿名未授权读取已下架培训课详情与课纲 |
| 2026-09-20 | 命中 | 美团·餐饮课堂 | 「我的物流/已购」缺参或缺会话时，是拒绝还是吐整表下单名和住址？手机号后四位是本账号二次确认还是可省略？ | GET /gw/xueyuan/logistics/list 缺 mobileLast4 | 未授权读（缺参整表） | 中危不进短表（omit 无新认） | 美团餐饮课堂匿名未授权批量读取他人图书订单姓名与收货地址 |
| 2026-09-20 | 命中 | 美团·开店入驻门户 | 报名写口前端 enableLogin / needCheckCode=false 是否被服务端当成鉴权？未登录能否落审核队列？ | POST /sapi/client/v1/tmcgeneralclientservice_submitregrecord | 未授权写（客户端旗当鉴权） | 中危不进短表 | 开店入驻门户匿名未授权提交客满满合作商报名 |
| 2026-09-20 | 命中 | 美团·招聘 ATS | 列表/关键字只出 jobStatus=000 在招时，详情换列表没有的 jobUnionId 是否仍出 jobStatus=001 已下线 JD 全文？ | POST /api/official/job/getJobList vs getJobDetail | 未授权读（列表≠详情） | 已有短表不进新行 | 美团招聘官网匿名未授权批量读取未上架职位详情 |
| 2026-09-20 | 命中 | 美团·供应商准入 | 列表只出 PUBLISHING 公示中时，详情换已下架/已撤销 projectNo 是否仍出采购需求全文和对接邮箱？ | POST /api/xt/project/getProjectList vs getProjectInfo | 未授权读（列表≠详情） | 已有短表不进新行 | 美团供应商准入门户匿名未授权批量读取已下架及已撤销公开招募项目详情 |
| 2026-09-20 | 命中 | 美团·民宿 | 公开主页/用户资料口是否把 CRM/wecom scene 内部运营标签当 FinalInfo 一并吐出？ | GET /user/api/v1/user/info/{userId} | 未授权读（内部标签） | 中危不进短表 | 美团民宿匿名未授权批量读取他人房东内部运营标签与主页资料 |
| 2026-09-20 | 命中 | 美团·民宿 lite | 行程分享出图口未登录换可遍历 orderId 是否仍签发 shareToken 并带入住日期/片区？Web 跳护照是否等于票作废？ | POST /ad/api/v1/delivery/getShareImage | 未授权读（令牌半径未兑现） | 中危不进短表 | 美团民宿lite匿名未授权批量读取他人订单入住日期与行程分享票 |
| 2026-09-20 | 命中 | 美团·客满满 C 端 | 匿名拼团详情 activityId 不绑店、预览审核失败是否等于详情也闸？门店 telephone 是否随详情下发？ | GET /rest/saas/grouppurchase/queryActivityDetails | 未授权读（租户隔离） | 不进短表（自增 id 通用枪） | 客满满C端拼团匿名未授权批量读取他店拼团详情与门店手机号 |
| 2026-09-20 | 命中 | 美团·Banmore | 未登录 getkmsvalue 是否按 name 下发网关 HMAC 盐？假盐失败、真盐是否过签拉内部素材/模板？ | POST /webapi/configservice/getkmsvalue | 未授权读（配置下发钥） | 进短表 getkmsvalue 行 | 美团Banmore设计平台匿名未授权读取网关签名密钥并批量拉取内部素材库与楼层模板 |
| 2026-09-20 | 命中 | 美团·星视 Claw | 同前缀名单要 SSO Bearer 时，申请写口是否漏挂？未登录 POST 是否 201 进待审批？ | POST /api/seerclaw/access-control/apply | 未授权写（漏挂 SSO） | 中危不进短表 | 星视starvision.meituan.com匿名未授权提交Claw访问权限申请 |
| 2026-09-21 | 命中 | 唯品会·VOP 开放平台 | 公告列表可见性是否等于详情授权？列表没有的自增 id 详情是否仍出未上架管理/巡检全文？（V3 复测仍成立） | GET /api/announcement/list vs /api/announcement/get?id= | 未授权读（列表≠详情） | 已有短表不进新行 | 唯品会_V3 VIP开放平台匿名未授权批量读取已下架平台公告正文 |
| 2026-09-22 | 命中 | 唯品会·公益 H5/charity | 对外目录是否等于详情授权？列表没有的 charityId 详情是否仍出 state=0/2/3 未上架/测试全文？（V3 翻回仍成立） | POST getItemCharityList vs getCharityDetail | 未授权读（列表≠详情） | 已有短表不进新行 | 唯品会_V3 公益H5匿名未授权批量读取未上架及测试公益项目详情正文 |
| 2026-09-22 | 命中 | 携程·信息安全问卷 | 答题页只靠 query 编号时，详情是否仍按会话/邀请票取主体？空号 code=0 是否等于未授权可读真题干？ | GET query_questionnaire_detail?questionnaireId= | 未授权读（列表≠详情/自增 id） | 已有短表不进新行 | 携程_V3 信息安全部问卷系统匿名未授权批量读取内部安全评审题干正文 |
| 2026-09-22 | 命中 | 携程·聚星采购上传 | 前端写死的上传票是否绑登录会话？假票失败、真票是否匿名任意后缀落盘且 HTML 当网页执行？ | ct-access-token + /file/upload | 未授权写（令牌半径） | 待 hunt-iter | 携程_V3 聚星大市场采购gmsrm前端写死上传票匿名任意文件上传且HTML可执行 |
| 2026-09-22 | 命中 | 携程·cbooking改密前置 | 未登录改密类型查询是否按 loginName 回注册态+脱敏手机邮箱？不存在是否 30004？ | getChangePasswordTypesByLoginName | 未授权读（账号枚举） | 待 hunt-iter | 携程_V3 cbooking租车商户端匿名未授权探测账号是否注册并回显脱敏手机邮箱 |
| 2026-09-22 | 命中 | 爱奇艺·奇炬广告门户 | 对外门户「代理商展示」接口是否把联系人手机/办公地址当公开字段下发？登录墙是否只挡投放后台不挡 portal ajax？ | GET /platform/ajax/portal/agencyContact | 未授权读/PII | 已写入 suspects；高危不拟进短表 | 爱奇艺奇炬广告平台匿名未授权批量读取代理商联系人手机号与地址 |
| 2026-09-22 | 命中 | 爱奇艺·奇炬开发者注册 | 「有校验外观」的滑块 token 失败时是硬拒绝还是软忽略仍落库？注册写口是否把 verificationToken 当可空？ | POST /developer/ajax/user/register + verificationToken | 未授权写（滑块软忽略） | 中危不进短表 | 爱奇艺奇炬广告平台匿名未授权开发者注册且滑动验证可绕过 |
| 2026-09-22 | 命中 | 爱奇艺·奇巴布 Skywalker | 网关 key-auth 是否按规范化 path 匹配？在前缀后插入 `;`（matrix）是否仍算同一前缀从而漏挂鉴权、直达 Spring Controller？ | `/prefix;/resource` vs `/prefix/resource` | 鉴权作用域/网关 path 规范化 | 已写入 suspects；中危不进短表 | 爱奇艺奇巴布API网关分号旁路匿名未授权读写任意用户儿童年龄控制 |
| 2026-09-22 | 命中 | 爱奇艺·UGC 认证 API | 业务是否把 X-Forwarded-For / True-Client-IP 的内网字面当成已登录？缺 Cookie 时改头是否仍出他 uid 认证档案？ | XFF/TCIP=127.0.0.1 + uid | 自定义身份头/IP 当会话 | 已写入 suspects；中危不进短表 | 爱奇艺认证服务匿名未授权批量读取他人UGC认证后台配置 |
| 2026-09-22 | 命中 | 爱奇艺·VIP 测试 OpenAPI | 文档站公开的测试 partnerNo/MD5 是否仍被测试域当有效签名？无票正签后订单查询/直充是否出他户会员？生产 sibling 同钥是否仍认？ | 文档 conf 测试钥 + 订单/直充口 | 令牌半径/硬编码钥 | 已写入 suspects；高危不拟进短表 | 爱奇艺会员测试开放接口匿名未授权使用公开文档密钥读取订单并直充会员 |
| 2026-09-22 | 命中 | 爱奇艺·弹幕 myna | 拉黑/名单写口是否只信客户端 uid、空/假 authcookie 仍进 Controller 落库？读口 getList 是否同样按 uid 当路由键？ | blockList add/remove/getList + uid | 未授权写/读（id 当路由键） | 已写入 suspects；中危不进短表 | 爱奇艺弹幕服务匿名未授权读写任意用户拉黑名单 |
| 2026-09-22 | 命中 | 爱奇艺·帮助知识库 API | C 端「有用/无用」写口公开时，同前缀 feedback-info/{id} 读口是否仍要会话/robot 票？公开 enumId 是否被当成回读唯一门槛？游客写号段是否等于客服反馈表？ | GET /knowledge-base-api/feedback-info/{id}?enumId= | 未授权读（写口≠回读鉴权） | 已写入 suspects；中危不进短表 | 爱奇艺帮助知识库API匿名未授权批量读取他人知识反馈userId与原因正文 |
| 2026-09-22 | 命中 | 爱奇艺·文学作者平台 | 前端/协议写「创作前实名」时，建书/草稿写口是否只信 userType=作者、不查 certifyStatus？正式发表卡实名是否等于草稿/建书也卡？ | POST /writer/book/create + /chapter/draft/create vs /chapter/create | 资质闸漏挂（实名只挡发表） | 已写入 suspects；中危不进短表 | 爱奇艺文学作者平台登录后可跳过实名认证创建作品并保存章节草稿 |
| 2026-09-22 | 命中 | 爱奇艺·文学作者平台 | 前端/协议写「创作前实名」时，建书/草稿写口是否只信 userType=作者、不查 certifyStatus？正式发表卡实名是否等于草稿/建书也卡？ | POST /writer/book/create + /chapter/draft/create vs /chapter/create | 资质闸漏挂（实名只挡发表） | 已写入 suspects；中危不进短表 | 爱奇艺文学作者平台登录后可跳过实名认证创建作品并保存章节草稿 |
| 2026-09-22 | 命中 | 爱奇艺·文学作者平台 | 前端/协议写「创作前实名」时，建书/草稿写口是否只信 userType=作者、不查 certifyStatus？正式发表卡实名是否等于草稿/建书也卡？ | POST /writer/book/create + /chapter/draft/create vs /chapter/create | 资质闸漏挂（实名只挡发表） | 已写入 suspects；中危不进短表 | 爱奇艺文学作者平台登录后可跳过实名认证创建作品并保存章节草稿 |
| 2026-09-22 | 命中 | 爱奇艺·投票中台 | 前端写死 HMAC 盐+sourceId 是否被 create 写口当授权？假 authCookie 过签是否仍落库？join 要登录是否等于 create 也要登录？ | GET /vote-api/w/createVote + 写死盐 | 未授权写（写死签名盐） | 已有短表写死签名盐；中危不进新行 | 爱奇艺投票服务匿名未授权使用前端硬编码盐创建投票 |
| 2026-09-22 | 命中 | 爱奇艺·虚拟制作实验室 | 播放密码校验是绑 videoId 还是绑公开 newsConfigId？未加密配置当通行证时，加密片 M3U8 是否仍出全文？ | GET /publish/idp/getM3U8FileContent newsConfigId+videoId | 未授权读（配置 id 当授权/密码闸解耦） | 中危不进短表 | 爱奇艺虚拟制作实验室匿名未授权绕过播放密码拉取科教片M3U8 |
| 2026-09-22 | 命中 | 爱奇艺·数字资产库 | 登录墙是否只挡 SPA，openApi 前缀是否漏挂鉴权？匿名列表/详情是否出源文件目录树和著作权证？下载口 无权限是否等于元数据也闸？ | GET openApi 列表/详情/目录树 | 未授权读（登录墙≠正文 API） | 中危不进短表 | 爱奇艺数字资产库匿名未授权批量读取内部CG资产元数据源文件目录树与著作权证书 |



| 2026-09-23 | 命中 | 爱奇艺·数字资产库 | 下载口「无权限」是否等于预览拉流也闸？openApi video/preview 是否匿名出 M3U8+TS？ | GET /ipddigitalassets/openApi/assets/file/video/preview/{assetsFileId} | 未授权读（下载闸≠预览同权） | 中危不进短表；并入原篇不换皮 | 爱奇艺数字资产库匿名未授权批量读取内部CG资产元数据源文件目录树著作权证书并拉流预览视频 |
| 2026-09-23 | 命中 | 爱奇艺·奇传上传控制面 | 同机 fileinfo 403 时，归档回查 get_archive_finish_result 是否仍匿名出内网 OSS 路径/sha1/role？测试域空库是否等于生产控制面也空？ | GET /get_archive_finish_result?file_id= | 未授权读（写口/fileinfo≠回读鉴权） | 中危不进短表 | 爱奇艺奇传上传控制面匿名未授权读取归档元数据与内网对象存储路径 |
| 2026-09-23 | 命中 | 爱奇艺·Sword协同 | 主 API 全 UA00401 时，同域 /collab-dev 协同画布是否漏挂登录闸？WSS 要票是否等于 HTTP canvas 也要票？ | GET/POST /collab-dev/canvas/api/* | 未授权读/写（协同子服务漏挂） | 中危不进短表 | 爱奇艺Sword测试协同服务匿名未授权读写任意项目画布文档 |
| 2026-09-23 | 命中 | 爱奇艺·奇悦审片 | 审片前端 getUploadApiToken 是否匿名下发奇传 access_token？假票失败、真票是否能 split_upload_request 铸 file_id？与归档无票读是否同根因？ | GET/POST /api/getUploadApiToken | 令牌半径/未授权写（匿名铸上传票） | 高危不拟进短表 | 爱奇艺奇悦审片匿名未授权领取奇传上传access_token并铸造分片上传会话 |
