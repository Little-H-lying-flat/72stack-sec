# 目标工作区与执行台账

> 视角:挖洞不是单会话行为。本文件定义"每个目标一份工作区"的四件套、findings 台账(去重登记簿的落地格式)、**Phase 4 出口检查**(覆盖率门闩)与跨会话续作。它是 08-multi-agent 三本账的单人版;约束(反幻觉 / scope / 证据纪律)在本层只增不减。

---

## 1. 建账时机与目录

**时机**:Phase 1 checkpoint 的 scope / rules 两项确认后立即建账(建账本身就是 checkpoint 第 5 项)。

**位置**:agent 工作区下 `work/<target-slug>/`,target-slug = 主域去 `www`(如 `work/example-com/`)。

```text
work/<target-slug>/
  scope.md      # in/out 逐条 + 公告来源 URL + payout tier + 时间盒 + next 节(§4)
  assets.md     # Phase 3 资产矩阵(域 → 端口 → 服务 → 指纹 → JS endpoint),增量追加
  findings.md   # findings 台账(§2 格式)——去重登记簿就在这张表里
  evidence/     # HTTP 包 / 截图 / 录屏,命名见 §1.1
```

### 1.1 evidence 命名

```text
YYYYMMDD-HHMMSS_<endpoint-slug>_<vuln-class>_<seq>.<txt|png|har|mp4>
例:20260830-142301_api-orders-id_idor_01.txt
```

同一 finding 的全部证据共享同一前缀(`日期-时间` 段固定)→ 报告附件一键归集。

---

## 2. findings 台账

`findings.md` 一行一 finding,**这张表同时就是去重登记簿**:

| id | 日期 | endpoint | vuln-class | variant | status | evidence | notes |
|---|---|---|---|---|---|---|---|
| F-01 | 20260830 | /api/orders/{id} | IDOR | 改 id 遍历 | confirmed | evidence/2026…01.txt | A 账号读 B 订单 |

**status 状态机**:`candidate → confirmed(差分通过) → submitted → (accepted / dup / rejected)`

**三条规则**:

1. **新命中先查登记簿**:同 `endpoint × vuln-class` 已有 entry → 记一行 status=`dup`,不重测(去重抑制的落地,SKILL.md Phase 4 步骤 7)
2. **candidate 不准进 Phase 5**:必须先走三段差分(03-evidence-discipline §3 原则 2)变 `confirmed`
3. **同根因合并**:多路径同一缺陷 → 一行,endpoint 列列多个;报告里作扩展面(与 enterprise-src-hunt 核心原则 9 同构)

---

## 3. Phase 4 出口检查(覆盖率门闩)

**进入条件**:打算从 Phase 4 收工——**无论有没有 finding**。

**MUST 输出**:覆盖率矩阵,写入 `scope.md` 或直接贴会话:

| 资产(assets.md 每行) | applicable playbook 类 | tested | result |
|---|---|---|---|
| api.example.com | IDOR / api-rest / info-disclosure | 是 | clean(差分阴性) |
| static.example.com(OSS) | 30-object-storage | 是 | hit(F-01) |
| vpn.example.com | unauth-access | 否 | **skipped-because: 需授权证书,超时间盒** |

**四条规则**:

1. `applicable` 依据指纹 / 端口 / 参数信号从 SKILL.md Phase 4 路由表得出——**不许凭感觉圈类**
2. `skipped` 必须写原因(时间盒 / 需授权 / 风控拦截),**留空 = 没做完**
3. `hit` 但未差分确认 → 回 candidate 流程;全 `clean` 才叫"测过干净",clean 也是产出
4. 与 01-attack-priority 的分工:**01 管"先打哪个",本节管"收工前打全了没"**

时间盒紧张时矩阵照常输出,允许大面积 `skipped-because: timebox`——**显式放弃优于假装测完**。

---

## 4. 跨会话续作

- **会话收尾**:`findings.md` status 更新 + `assets.md` 增量 + 在 `scope.md` 底部 `next:` 节写 ≤3 条下一步
- **会话开场**(同一目标):Read 四件套 → 从台账继续,**已 clean 的类不重测**(登记簿兜底)
- **交接**:四件套即交接物;08-multi-agent 的任务卡从这里派生(卡里的 scope / 目标清单直接引用,不复制)

---

## 5. 与既有文档的关系

| 文档 | 分工 |
|---|---|
| 03-evidence-discipline | 管证据"长什么样"(三段差分 / 复现率 / 截图规范) |
| 本文件 | 管证据和状态"放哪里、怎么编号、何时算完" |
| 08-multi-agent §5 三本账 | 本文件台账的**并发版**;单人挖洞用本文件,并行时升格 |
| enterprise-src-hunt 模块账本 | 同思想的模块粒度版;按主流程选账本,两 skill 不混用 |
