# 云安全 / 云授权项目 — 决策索引

> 视角:目标跑在云上(国内绝大多数是阿里云 / 腾讯云),或项目授权了云上环境(账号 / 集群 / 资源)。本文件是**云授权项目的黑盒主 playbook**,聚焦云控制面、身份(IAM/RAM/CAM)、对象存储、K8s 的黑盒攻击面。**从 SSRF 打元数据的路径不在这里**——那属于 SSRF 入口链路,见 [`../ssrf-cache-host/11-cloud.md`](../ssrf-cache-host/11-cloud.md)。

---

## 子文件路由(Phase 4 读哪一份?)

| 入口信号 | MUST Read |
|---|---|
| 项目 scope 含云账号 / 资源 / 集群;或资产侧要判断目标用哪家云、控制面是否暴露 | `10-recon-exposure.md` |
| 已持有云凭据(AK/SK/STS,来自泄露 / 元数据 / 代码);或要评估凭据能提到多高 | `20-iam.md` |
| 资产里有对象存储(oss-*.aliyuncs.com / *.myqcloud.com / *.obs.* / *.s3.*);或要深挖 bucket | `30-object-storage.md` |
| 资产里有 K8s(6443 / 10250 / 10255 / 2379 / Dashboard / ingress);或已进 Pod | `40-k8s.md` |
| SSRF 已确认,想打元数据拿临时凭据 | `../ssrf-cache-host/11-cloud.md`(不在本 playbook) |

---

## 1. 一句话说清

云授权项目打的是**配置和身份**,不是传统 Web 漏洞:bucket 权限错配、IAM 过权、K8s 组件未授权、控制面暴露。价值天花板:只读枚举证明接管能力 = Critical($5k–$50k 国际 / 国内 SRC 严重)。

**与 Web playbook 的关系**:`?url=` 型 SSRF 是"Web 漏洞 → 云"的桥,归 ssrf-cache-host;本 playbook 处理"目标本身是云资产"的场景。

---

## 2. 云授权项目的 Intake 增量(Phase 1 必问)

云项目 scope 的粒度比 Web 细一个数量级,四项 checkpoint 之外**必须**再确认:

- [ ] **Scope 粒度**:云账号 ID / 资源 ARN / K8s 集群名 / VPC 网段——逐条列,模糊的("生产环境")要问清
- [ ] **凭据提供方式**:甲方发测试 AK?还是只给控制台只读账号?或者纯黑盒(仅给域名)?
- [ ] **允许的动作**:只读枚举是否够?能否创建临时资源(Lambda / Pod / Object)?能否对非测试环境操作?
- [ ] **检测告知**:是否要求先申报源 IP / 测试窗口(云厂商风控会把枚举当入侵,CloudTrail / ActionTrail 全程留痕)
- [ ] **清理义务**:测试资源用完即删,命名统一带 `security-test-` 前缀并留清单

**默认红线**(甲方没明说也成立):只读优先;不删不改生产数据;不创建持久化后门;不停实例;不下载超出证明所需的批量数据。

---

## 3. 黑盒第一步:云资产识别与控制面发现

完整探针在 [`10-recon-exposure.md`](10-recon-exposure.md)。快速决策树:

```
子域 / IP 拿到
  → CNAME / 证书 SAN / favicon hash 判云厂商(aliyuncs / myqcloud / amazonaws / googleusercontent)
  → 对象存储域名? → 30-object-storage.md
  → 6443 / 10250 / 2379 / Dashboard? → 40-k8s.md
  → 控制台 / API 网关 / 函数计算 endpoint 暴露? → 10-recon-exposure.md
  → JS / 抓包里泄露 AK / STS? → 20-iam.md(凭据验证) + methodology/07-js-recon.md
  → Web 层发现 SSRF? → ../ssrf-cache-host/11-cloud.md(元数据链路)
```

---

## 4. 通用方法论:凭据为轴

云攻击面的一切围绕**凭据的获取与放大**:

```
获取入口(任一)
  ├─ 黑盒: bucket 错配 / 控制面暴露 / JS 泄露 AK / GitHub dorks(Phase 2)
  ├─ Web 桥: SSRF → 元数据 → 临时凭据(→ ssrf-cache-host/11-cloud.md)
  └─ 甲方: 授权测试 AK
       ↓
凭据验证(sts get-caller-identity / get-account-alias,只读)
       ↓
权限枚举(enumerate-iam / Pacu,只读 Action)
       ↓
提权路径评估(→ 20-iam.md)
       ↓
影响证明(读到一条敏感数据 / 列出一个敏感 bucket 即停)
```

**证据纪律**:每一步只读 API 调用都要留 CLI 记录(带时间戳);影响证明"能读到"即停,见 [`../../methodology/03-evidence-discipline.md`](../../methodology/03-evidence-discipline.md)。

---

## 5. 价值参考

| 场景 | 严重度 |
|---|---|
| 匿名可写 bucket(可挂静态站 / 覆盖分发文件) | Critical |
| 匿名可读 bucket 含备份数据库 / 凭据 | High–Critical |
| 未授权 K8s API 可列 secrets / 建 Pod | Critical |
| 低权限 AK → 管理员(IAM 提权链) | High–Critical |
| 控制面 / API 网关未授权 | High |
| bucket 接管(CNAME 悬挂) | High(子域接管) |

---

## 6. 不要做的事(云项目红线)

- **禁**:拿凭据后调任何写操作 API(`delete-*` / `update-*` / `put-*` / `create-*` 除测试资源外)
- **禁**:下载数据库备份到本地超 1–2 条样本。证明可读即可,列出文件名 + 读出一条脱敏记录
- **禁**:用目标凭据访问第三方服务(用目标 AK 调第三方 SaaS = 数据外带,直接违规)
- **禁**:K8s 里建带 hostPath 的特权 Pod 来"演示逃逸"——除非 scope 明确允许,用 SSRR / SelfSubjectAccessReview 证明权限即可
- **禁**:枚举不限速。云 API 有配额也有风控,IAM 枚举 5–10 QPS 封顶
- **禁**:测试完不清理。创建的 bucket / 对象 / Pod / 函数必须在报告前删除并附删除证据

---

## 相关 MCP 工具

云项目主要靠 CLI 与 HTTP,浏览器侧工具用于控制面暴露探测与 JS 泄露搜集:

| 工具 | 调用时机 |
|---|---|
| `mcp__jshook__js_format` / `mcp__jshook__ast_search` | SPA bundle 里找 AK / STS / endpoint(配合 methodology/07-js-recon.md) |
| `mcp__jshook__network_get_requests` | 抓包里找对象存储域名 / STS 临时凭据下发 |

完整映射:[`../../tools/mcp-jshook.md`](../../tools/mcp-jshook.md)

---

完整 Payload 库见同级子文件。
