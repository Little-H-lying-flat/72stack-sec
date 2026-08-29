# 云身份与提权(IAM / RAM / CAM) — payload 库

> 父文档:[00-index.md](00-index.md)
> 涵盖:云凭据的有效性验证、权限枚举纪律、AWS 提权路径速查(完整 payload 见 [`../ssrf-cache-host/11-cloud.md`](../ssrf-cache-host/11-cloud.md))、**阿里云 RAM / 腾讯云 CAM 提权**。定位是"拿到凭据之后、出报告之前"的处置流程。

**WSTG / CWE 映射**(报告时填 `../../templates/report-submission.md` 对应字段;WSTG 标到类级):

| 场景 | WSTG | CWE |
|---|---|---|
| cloud-cred-validate / cloud-enum-readonly | —(处置流程,非漏洞本体) | — |
| cloud-privesc-paths | WSTG-ATHZ | CWE-269(过度授权→提权) |

---

### 凭据验证与账号定位  `cloud-cred-validate`

拿到任何云凭据(泄露 AK / 元数据三元组 / 甲方测试 AK)后的**第一步**:只读验证有效性,定位账号与身份,不做任何资源枚举。
子类:**凭据处置** · tags: `云安全` `AK` `STS` `验证`

**前置条件:** 持有 AK/SK(±STS token);来源在授权范围内

**攻击链:**

**1. 一次只读调用验证**
_有效 / 无效 / 过期,一步分清_
```
# 阿里云(含 STS 三元组:--sts-token)
aliyun sts GetCallerIdentity --access-key-id {AK} --access-key-secret {SK} [--sts-token {ST}]
# 返回:UserId / AccountId / Arn(arn:acs:ram::{ACCOUNT_ID}:user/{NAME} 或 role/...)

# 腾讯云
tccli sts GetCallerIdentity --secret-id {AK} --secret-key {SK} [--token {ST}]

# AWS
aws sts get-caller-identity
# InvalidAccessKeyId = 无效;ExpiredToken = 过期;正常返回 = 有效
```

**2. 账号归属核对**
_ Arn 里的账号 ID 必须 ∈ scope 清单,否则立即停_
```
# 核对 Arn → Phase 1 云 scope 清单(账号 ID / 资源 ARN 粒度)
# 出 scope → 停手回 Phase 1 重核(SKILL.md 反幻觉硬约束 4 同样适用)
```

---

### 权限枚举(只读纪律)  `cloud-enum-readonly`

有效性确认后枚举"这个身份能做什么"。**只发只读 Action**;被拒绝(AccessDenied)本身就是权限边界的证据。
子类:**权限枚举** · tags: `云安全` `枚举` `RAM` `CAM` `IAM`

**前置条件:** 凭据已验证有效;限速 ≤10 QPS

**攻击链:**

**1. 阿里云 RAM 枚举**
_身份绑定策略 → 策略内容,两步读_
```
aliyun ram ListUsers                       # 用户列表(有权限则看)
aliyun ram ListPolicies                    # 自定义策略
aliyun ram GetPolicy --policy-name {NAME} --policy-type Custom   # 策略文档(Statement 即权限)
aliyun ram ListRoles                       # 可假设角色(拿去 AssumeRole)
# OSS 侧
aliyun oss ls                              # 匿名/凭据可列 bucket 清单
```

**2. 腾讯云 CAM 枚举**
```
tccli cam ListUsers
tccli cam ListPolicies --page-size 20
tccli cam GetUserAppId                     # 归属 AppId
tccli cos ls                               # COS 桶清单
```

**3. AWS 枚举与自动化**
_AWS 侧完整工具链在 11-cloud.md §cloud-iam-escalation,此处只列入口_
```
aws iam list-attached-user-policies --user-name {NAME}
python3 enumerate-iam.py --access-key {AK} --secret-key {SK}   # 全 Action 探测(只读命中留痕)
cloudfox aws --profile target all-checks                       # 自动化全景
```

**4. 拒绝也是证据**
_枚举中每条 AccessDenied 记入证据表——它划出了影响上界_
```
| Action | 结果 | 说明 |
| oss:ListObjects | 允许 | 列出 {BUCKET} |
| ram:CreateAccessKey | 拒绝 | 无提权路径 A |
```

---

### 云提权路径速查  `cloud-privesc-paths`

持有低权限身份时,按本表逐条核对可提权路径。**评估 ≠ 利用**:除非 scope 明确允许,证明"路径存在"(策略文档里看到高危 Action)即写报告,不实际提权。
子类:**提权** · tags: `云安全` `RAM` `CAM` `提权`

**前置条件:** 权限枚举产出策略文档;scope 对提权动作的授权已确认

**攻击链:**

**1. 通用高危 Action 表(三家云对照)**
_命中任一 Action 即存在提权候选,验证手法见对应列_
```
| 能力              | AWS                        | 阿里云 RAM                | 腾讯云 CAM               |
| 改策略/建策略版本 | iam:CreatePolicyVersion    | ram:CreatePolicyVersion   | cam:CreatePolicyVersion  |
| 给自己/他人挂策略 | iam:AttachUserPolicy       | ram:AttachPolicyToUser    | cam:AttachUserPolicy     |
| 造新密钥          | iam:CreateAccessKey        | ram:CreateAccessKey       | 控制台操作(以文档为准)   |
| PassRole 执行     | iam:PassRole(+lambda/ec2)  | ram:PassRole(+fc/ecs)     | cam:PassRole(+scf/cvm)   |
| 角色扮演          | sts:AssumeRole             | sts:AssumeRole            | sts:AssumeRole           |
| 更新角色信任      | iam:UpdateAssumeRolePolicy | ram:CreateRole+信任策略   | cam:UpdateRolePolicy...  |
# 命名以各家官方 Action 列表为准;字段级差异查官方文档
```

**2. AWS 完整利用 payload**
_PassRole+Lambda / CreatePolicyVersion / UpdateAssumeRolePolicy 三条链的完整命令:_
```
→ ../ssrf-cache-host/11-cloud.md §cloud-iam-escalation(不在此重复)
```

**3. 阿里云 RAM 提权验证(最小动作)**
_以"策略文档里存在 ram:CreateAccessKey / ram:AttachPolicyToUser"为证据,利用演示仅限甲方明示允许_
```
# 路径核对(读策略文档即可证明,无需发写请求):
aliyun ram GetPolicy --policy-name {NAME} --policy-type Custom | jq '.Policy.Document'
# Statement 含 "ram:*" 或上表 Action → 写报告:低权限身份可自我提权至管理
# 如甲方允许实操演示,按 AWS 链路类比替换 Action 名,先在测试账号演练
```

**4. 国内云提权研究的稀缺性声明**
_RAM/CAM 提权公开研究远少于 AWS,上表为 API 能力映射而非已验证利用链_
```
# 纪律:引用时写"策略允许 X,该能力在 AWS 对应路径为已验证提权路径",
# 不写"已实现国内云提权"——除非实测完成(证据纪律,03-evidence-discipline.md)
```

**WAF/EDR 绕过变体:**

**1. 枚举限速与留痕**
_云 API 全程 CloudTrail / ActionTrail 留痕,慢一点对双方都好_
```
# 每次调用间 sleep 5-10s;工具侧限速
enumerate-iam 默认并发即偏高 → 手动分批跑
# 甲方项目:提前报备源 IP 与窗口(见 00-index.md §2 检测告知)
```

---

## 不要做的事(身份面红线)

- **禁**:验证凭据有效后继续"顺手"调写接口(哪怕 create-test)——除非 scope 明示
- **禁**:枚举出的用户列表 / 策略文档整包贴报告——贴关键 Statement 片段,用户名脱敏
- **禁**:对拒绝的 Action 反复重试(风控按异常行为封测试 AK)
- **禁**:把甲方测试 AK 写进报告正文 / 截图(报告里脱敏为 `LTAI****xxxx`)

---

## H1 真实案例

_3 份 HackerOne 已披露 High/Critical 报告命中云凭据面_

| Severity | $ | 程序 | 标题（点击看原报告） | 摘要 |
|---|--:|---|---|---|
| High | 8868 usd | Basecamp | [AWS keys and user cookie leakage via uninitialized memory leak in outdated librsvg version in Basecamp](https://hackerone.com/reports/2107680) | 过时 librsvg 未初始化内存泄露出 AWS keys + 用户 cookie——"Web 缺陷 → 云凭据"的桥接样本 |
| High | — | U.S. Dept Of Defense | [Secret Access Key of AWS Firehose Disclosure](https://hackerone.com/reports/2914739) | AWS Firehose Secret Access Key 直接泄露 |
| High | — | — | [two aws access key and secret key and database username and password exposed](https://hackerone.com/reports/2401648) | AK/SK + 数据库凭据成对暴露（AK 与业务凭据同点泄露的典型） |

**来源分组（h1-reports/by-weakness/）：**

- information-disclosure：3 条

---

← 回 [00-index.md](00-index.md) · 相关:[`10-recon-exposure.md`](10-recon-exposure.md) · [`30-object-storage.md`](30-object-storage.md) · [`../ssrf-cache-host/11-cloud.md`](../ssrf-cache-host/11-cloud.md)
