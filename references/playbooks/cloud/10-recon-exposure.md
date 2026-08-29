# 云资产识别与控制面暴露 — payload 库

> 父文档:[00-index.md](00-index.md)
> 涵盖:黑盒判断目标用哪家云、云产品公网 endpoint 暴露探测、云凭据(AK)泄露面识别。云授权项目的 Phase 3 Enum 层,产出"云资产矩阵"喂给 20/30/40 子文件。

**WSTG / CWE 映射**(报告时填 `../../templates/report-submission.md` 对应字段;WSTG 标到类级):

| 场景 | WSTG | CWE |
|---|---|---|
| cloud-fingerprint | WSTG-INFO | —(资产测绘,非漏洞) |
| cloud-controlplane | WSTG-CONF | CWE-306(函数计算/控制面未授权) |
| cloud-cred-leak | WSTG-INFO | CWE-200 / CWE-798(前端硬编码 AK) |

---

### 云厂商指纹识别  `cloud-fingerprint`

通过 CNAME / 证书 / 响应特征判断资产归属哪家云、哪个产品线——决定后续打 OSS 还是 K8s 还是元数据链路。
子类:**云资产测绘** · tags: `云安全` `指纹` `测绘` `CNAME`

**前置条件:** 子域 / IP 清单(Phase 3 矩阵)

**攻击链:**

**1. CNAME 特征判云**
_对象存储 / 负载均衡 / CDN 的 CNAME 指向云厂商专属域名_
```
# 逐子域查 CNAME,对照下表
dig +short CNAME {SUB}.{TARGET}

*.oss-{region}.aliyuncs.com          # 阿里 OSS
*.aliyun-waf.org / *.aliyuncs.com    # 阿里云(含 WAF CNAME)
*.cos.ap-{region}.myqcloud.com       # 腾讯 COS
*.clb.myqcloud.com                   # 腾讯 CLB
*.obs.{region}.myhuaweicloud.com     # 华为 OBS
*.s3.{region}.amazonaws.com / *.cloudfront.net   # AWS
*.googleusercontent.com / *.cloud.goog           # GCP
*.azurewebsites.net / *.blob.core.windows.net    # Azure
```

**2. 证书 SAN 与 IP 段**
_直连 IP 时用证书与归属 ASN 判云_
```
openssl s_client -connect {IP}:443 2>/dev/null | openssl x509 -noout -text \
  | grep -A1 "Subject Alternative Name"

# IP 段归属:bgp.he.net 查 ASN
# AS37963 阿里云 · AS132203 腾讯云 · AS136987? 以 bgp.he.net 实查为准
# AS16509 Amazon · AS15169 Google · AS8075 Microsoft
```

**3. 响应特征 / 错误页**
_云 WAF 与网关的错误页有强指纹_
```
# 拦截页特征(触发一次明显攻击 payload 看拦截页)
curl -s "https://{TARGET}/?id=1' and '1'='1" | grep -oiE "aliyun|tencent|huawei|cloudfront|waf"
# 阿里云盾拦截页含 errors.aliyun.com / 405 blocked
# FOFA favicon 查询:icon_hash="{HASH}"(Phase 2 已算)
```

**4. 产出:云资产矩阵**
_喂给后续子文件的判定结果_
```
{SUB}.{TARGET} → 阿里云 OSS(30-object-storage.md)
{SUB}.{TARGET} → 腾讯云 CLB → 后端源站(回源 IP 探测归常规 recon)
{IP}           → K8s node(10250 开) → 40-k8s.md
```

---

### 云控制面暴露  `cloud-controlplane`

云产品的**公网管理面 / 数据面 endpoint** 暴露:函数计算默认域名、API 网关、云中间件公网访问、控制台相关子域。这类暴露不依赖 Web 漏洞,黑盒直接可达。
子类:**控制面暴露** · tags: `云安全` `函数计算` `API网关` `未授权`

**前置条件:** 子域清单 / IP 段;目标云厂商已知

**攻击链:**

**1. 函数计算 / Serverless 默认域名**
_FaaS 的 HTTP 触发器常被当"临时接口"挂公网,鉴权常缺失_
```
# 阿里云函数计算(新域名格式,以 FC 控制台实际返回为准)
{function}.{region}.fcapp.run
# 腾讯云云函数 / API 网关触发路径,以控制台为准
{func}-{account}.{region}.apigw.myqcloud.com
# AWS Lambda URL(2022+ 特性)
https://{url-id}.lambda-url.{region}.on.aws

# 处理:发现后按该函数业务逻辑测未授权 / 注入(参数直接进业务,归对应 playbook)
```

**2. 云中间件公网暴露**
_开了公网访问的托管中间件——枚举与弱口令归 unauth-access,这里只认云版指纹_
```
# 端口 + 产品对照(默认端口)
3306(RDS)  6379(云 Redis)  9200(云 ES)  27017(云 Mongo)  5672(云 MQ)
# 云 Redis 错误页: -ERR ... aliyun / tencent 特征行
# 测试纪律:默认凭据只试 1-3 次,见 dictionaries/default-credentials-cn.md
```

**3. 控制台 / 管理域发现**
_子域字典补云管理词_
```
# 子域爆破字典追加
console / ram / iam / oss / cos / k8s / kube / rancher / harbor
grafana / kibana / jenkins / gitlab / sso / login / admin-api
# 命中 console.* 先看登录口(弱口令归 unauth-access.md),再找它引用的 API 域名
```

**4. 云 WAF 绕过归属说明**
_控制面被云 WAF 拦时,绕过手法统一在 bypass 工具集,不在本文件重复_
```
→ methodology/02-bypass-toolkit.md 决策树
```

---

### 云凭据泄露面识别  `cloud-cred-leak`

黑盒收集环节识别"已暴露的云凭据":AK 前缀指纹、前端 / 小程序 / 抓包中的 STS、错误信息中的账号 ID。拿到凭据后的一切见 [`20-iam.md`](20-iam.md)。
子类:**凭据泄露** · tags: `云安全` `AK泄露` `STS` `信息收集`

**前置条件:** JS bundle / 抓包 / GitHub dorks(Phase 2)产出物

**攻击链:**

**1. AK 前缀指纹表**
_正则扫 JS / 仓库 / 日志,命中即视为凭据泄露_
```
LTAI[A-Za-z0-9]{12,}        # 阿里云 AccessKey(恒为 LTAI 开头)
AKID[A-Za-z0-9]{30,}        # 腾讯云 SecretId
AKIA[0-9A-Z]{16}            # AWS 长期 AK
ASIA[0-9A-Z]{16}            # AWS 临时 AK(STS)
AIza[0-9A-Za-z_-]{35}       # GCP API Key
# 伴生字段:accessKeyId / accessKeySecret / securityToken / stsToken / sessionToken
```

**2. 前端 STS 临时凭据**
_直传 OSS 的前端 SDK 常把 STS 三元组硬编码或经接口下发_
```
# SPA bundle 搜索
grep -rE "stsToken|SecurityToken|security_token|credentials" {DIST}/ | head
# 抓包:找 /sts /credential /getToken 类接口的响应体
# 响应含 AccessKeyId+AccessKeySecret+SecurityToken → 直接进 20-iam.md 验证
```

**3. GitHub / 网盘面(Phase 2 dorks 的云化)**
_组织名 + 云关键词_
```
# GitHub dorks(Phase 2 框架内)
org:{TARGET} "LTAI" | "AKID" | "accessKeySecret"
org:{TARGET} filename:.env OSS_ACCESS_KEY
# 命中后:验证仅用只读 API(get-caller-identity 级别),不触发写
```

**WAF/EDR 绕过变体:**

**1. 凭据验证的最小动作**
_验证 AK 是否有效只需一次只读调用,不枚举不触碰资源_
```
aliyun sts GetCallerIdentity            # 阿里云(无效 AK 报 InvalidAccessKeyId)
tccli sts GetCallerIdentity             # 腾讯云
aws sts get-caller-identity             # AWS
# 证明"凭据有效"到"证明能读敏感资源"之间全部动作见 20-iam.md 的权限枚举纪律
```

---

← 回 [00-index.md](00-index.md) · 相关:[`20-iam.md`](20-iam.md) · [`../ssrf-cache-host/11-cloud.md`](../ssrf-cache-host/11-cloud.md)(元数据链路)
