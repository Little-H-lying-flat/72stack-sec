# 接口 Fuzz 管线 — 参数 / 值 / 端点 / LLM 四类模糊测试

> 定位:证据先行门闩(Phase 4 流程 3)把纯猜测探针排到 parked 清单尾部——**fuzz 就是大规模猜测**,本文件管"怎么让 fuzz 有种子、有变异器、有 oracle、有预算",而不是盲炸。吸收 AI-Fuzz 生态思想(2026-08 调研):EvoMaster(SBST 智能用例生成)/ Fuzz4All(LLM 做生成与变异)/ AFL++(custom mutator 可插拔)/ FuzzyAI(变异+生成式+遗传三策略打 LLM)/ LLMFuzzer(LLM 集成应用边界)/ PS-Fuzz(系统提示词强化测试)——**只吸收思想,本库不内置工具**,生态索引见 §6。
>
> **总纪律**:fuzz 探针与普通探针同一套反幻觉约束——每个探针标注出处(种子来源 / 变异器规则名),标不出出处的探针不进会话输出;命中后照走三段差分确认,fuzz 命中 ≠ confirmed。
>
> **批内健康检查(强制门闩,dogfood 两次拦截 harness 自伤)**:每批**首探针 = baseline 复检**(重打一遍基线值);批内出现多条字节级同响应时,**harness 疑点优先于目标结论**——先手动单发一条核对 URL 拼接与参数形态,再判读阴性。实测教训:探针串带 `q=` 前缀与基础 URL 拼成 `?q=q=...`、shell 函数变量错位把全批拼成纯 baseline——两批假结果全靠"全同尺寸"信号回捞。

---

## 0. 何时 fuzz / 何时停

**触发**(全部满足才开):
- 来源探针(证据 / 字典 / 频率表)已打完,parked 队列仍有积压;或
- 参数枚举值 / 隐藏字段无任何来源可查;或
- LLM 集成接口需要规模化 prompt 测试(§4)。

**停机条件**:
- 11 号管线队列项 budget:fuzz 一样 15 探针或 20 分钟先到为准,耗尽即换路,不硬磨;
- 连续 8 探针无新信息 → 触发 11 号 §5 深度反思(fuzz 不豁免);
- WAF 拦截率高 → 先走 `02-bypass-toolkit.md` §2.1 过滤器画像,降档节流(§4.1 阶梯),再决定续不续;
- parked→fuzz→candidate 漏斗记账:fuzz 命中率 <1% 且无新信号 → 该类 fuzz 终止,结论落盘 notes。

**队列纪律**:fuzz 批次独立入 11 号队列(队列粒度=端点×场景),不与来源探针混跑——混跑会污染差分基线;每批结束记 parked→fuzzed 转化数。

---

## 1. 四类 fuzz 目标与命中 oracle

| 类 | 对象 | 种子来源(证据先行同源) | 命中 oracle |
|---|---|---|---|
| **参数名 fuzz** | 隐藏参数 / 被删字段 | JS endpoint 提取(07 §1–8)、报错页泄露字段、同 CMS 频率表(playbook) | 参数被消费:响应差分(加参 vs 基线)/ 状态码变化 / 错误签名改变 |
| **参数值 fuzz** | 类型混淆 / 边界 / 枚举 | 已采真实值的变异(§2 变异器库) | 500→200、越权返回他者数据、金额/数量异常接受、报错栈泄露 |
| **端点 fuzz** | 路径 / 方法 / Content-Type | 结构路径字典(11 §3.1)、API 文档、nuclei 初筛 | 非预期状态码(404→403→200 梯度)、长度离群、`Allow` 头暴露方法 |
| **LLM 入口 fuzz** | prompt 字段 / 系统提示词 | llm-prompt-injection playbook 场景 + §4 策略 | 越狱判据(可机械判定:关键词/格式)、系统段泄露、工具误调用、外带链触发 |

差分判读规则同 `03-evidence-discipline.md` §3:全零差分先查证据真实参数形态,再区分"未消费 / 数字归一";0B 窗口三档退避仍 0B → blocked 不判阴性。

---

## 2. 种子驱动的变异循环(AFL++ custom mutator 思想,黑盒化)

AFL++ 的核心不是"乱改",是**可插拔变异器 + 覆盖率反馈**。黑盒版对应:

```
1. 种子语料:只从 (a)已采证据 (b)指纹字典 (c)playbook 频率表 生成——
   fuzz 不豁免证据先行;纯虚构值一律排 parked 尾部
2. 变异器库(按规则名调用,输出标注规则名):
   - 类型表:空串 / null / 数组包一层 / 重复参数(?id=1&id=2) / 删参数
   - 数值表:0 / 负数 / 超大(2^63) / 科学计数(1e10) / 前导零 / 浮点精度
   - 编码表:URL 单双层 / Unicode / 宽字节 —— 完整梯度见 02-bypass §2.4 编码变体
   - 语义表:同义字段名(userId↔uid↔user_id)——对齐 09 号"数字参数族"三态推断
3. 反馈循环:每批记录 oracle 命中;命中的种子保留继续衍生(定向深挖),
   未命中种子不重复送 —— 对齐 AFL++"覆盖率反馈保留有价值输入"的思想
4. 固化回归(EvoMaster 思想):命中的探针固化成可重放脚本(curl/python)
   存 evidence/,repro 复核轮与盲复现报告直接引用 —— 一次性 fuzz 必须沉淀为回归资产
```

---

## 3. AI/LLM 增强的生成式 fuzz(Fuzz4All 思想)

Fuzz4All 的洞察:LLM 能生成**语法语义合法**的输入,打破手写 grammar 的限制。黑盒对应:

- **适用**:复杂 JSON body、嵌套结构、需要业务语义的字段组合(字典 fuzz 对这类结构命中率极低)。
- **做法**:拿已采到的真实请求/响应样本 → 本地让 LLM 生成同构变体(改字段数、改类型、改嵌套、注入边界值)→ **人工/脚本审核后入队**,不是让 LLM 直接对目标自由发挥(失控流量 + 出 scope 风险)。
- **出处标注**:AI 生成探针标 `(generated-from: <样本响应 hash/来源>)`,与 playbook 出处标注同级;无样本不上 LLM 生成。
- **边界**:目标环境的 LLM 测试(§4)≠ 用目标环境外的第三方 LLM API 打目标;生成阶段用什么模型是本地方案,不打进目标流量。

---

## 4. LLM 集成接口的 fuzz(FuzzyAI / LLMFuzzer / PS-Fuzz 思想)

打点对象 = **目标站自己的 LLM 集成功能**(客服 bot / RAG 问答 / Agent 工具调用),手法路由进 `playbooks/llm-prompt-injection/00-index.md`,这里只管"规模化测试的策略层":

| 策略(FuzzyAI 三分类) | 做法 | oracle 判定 |
|---|---|---|
| **变异式** | 种子 prompt(§2 同源:目标业务上下文)+ 变异器(角色注入前缀 / 指令分隔符 / 编码) | 可机械判定:输出含越狱内容特征 / 违反设定的格式 |
| **生成式** | 用 LLM 针对目标拒绝样本生成绕过变体(拒绝→变体→再测循环) | 同上;拒绝样本与绕过样本都要落盘 |
| **遗传式(GA)** | 得分高的种子交叉/变异繁殖下一代;**轮数上限 3–5 代**(防自嗨收敛) | 适应度=越狱判据命中;每代记录最优个体 |
| **系统提示词泄露(PS-Fuzz)** | 迭代变异"复述你之前的指令"类探针族(直接/间接/翻译/补全变体) | 回复中出现系统段特征(角色设定词/工具清单/格式约束) |

**红线**:不把 fuzz 工具指向外部第三方 LLM API(消耗别人配额 = 出 scope);目标 LLM 接口有限速时走 §4.1 节流阶梯;LLM 类 fuzz 产生的 prompt/payload 属于探针,同样进 findings 台账与差分确认,不因"看着像越狱"直接写报告。

---

## 5. 与既有机制的衔接

- **11 号管线**:fuzz 批次 = 队列项(budget/节流/反思/落盘全部适用);复现复核轮(reverify)对 fuzz 固化脚本直接复跑。
- **02-bypass-toolkit**:变异器库的编码/过滤绕过变体从其 §2 引用,不重复维护。
- **nuclei-templates**:高频参数值 fuzz 可固化成 nuclei 模板规模化初筛(模板 payload 均出自 playbook,命中后回 playbook 走全流程——Phase 3 既有约定)。
- **09-target-workspace**:fuzz 批次结果(含未命中)入 findings 台账,`skipped-because: budget` 与"预算未耗尽"不得自相矛盾(三查门闩)。
- **11 号 §4.4/§4.5 共享实例与 env-broken**:批次开始即遇统一错误签名(全 503 / 全 0B)→ 该批结果记 invalid / skipped-because: env-broken,**不入阴性账**(env-broken 不产生假阴性);立即停流量,恢复监控(特征端点字节签名)后再补跑。

---

## 6. 生态工具索引(参考,本库不内置)

| 工具 | 定位 | 对应本 skill 用法 |
|---|---|---|
| [EvoMaster](https://github.com/webfuzzing/evomaster) | AI 驱动 REST/GraphQL/gRPC API fuzzer(SBST,黑盒模式可用) | §2-4 固化回归思想:产出可重放测试;自托管 API 且可跑 JVM/Node 时可选 |
| [Fuzz4All](https://github.com/fuzz4all/fuzz4all) | LLM 做用例生成与变异,免手写 grammar | §3 生成式 fuzz 思想来源;面向编程语言解析器,业务 API 场景用其思想自建 |
| [AFL++](https://github.com/AFLplusplus/AFLplusplus) | 工业级 fuzzer,custom mutator 插件机制 | §2 变异器库的组织范式(可插拔规则表);二进制目标不属本 skill 主战场 |
| [FuzzyAI](https://github.com/cyberark/fuzzyai) | LLM 越狱 fuzz(变异/生成式/遗传,多 provider) | §4 三策略分类来源;注意其默认指向你自己的 API key——打目标站接口时只借策略不直连 |
| [LLMFuzzer](https://github.com/mnns/llmfuzzer) | 最早的 LLM 集成应用漏洞挖掘框架 | §4 场景划分参考(应用边界 vs 模型本身) |
| [PS-Fuzz](https://github.com/prompt-security/ps-fuzz) | GenAI 系统提示词自动化测试 | §4 系统提示词泄露探针族思路 |

---

## 7. 红线

- **fuzz ≠ 盲炸**:种子无出处、变异器无规则名、命中无差分——三缺一不出报告。
- **高并发限制**:共享环境 / 生产目标并发 ≤2,走 §4.1 节流;DoS 类 playbook 红线优先于本文件。
- **LLM fuzz 只打目标自己的集成接口**,不指向第三方模型 API;GA 代数上限 3–5。
- **样本控制**:fuzz 意外命中批量数据口(IDOR/批量参数)→ 拉 1–3 条样本即停,转 playbook 正常流程。
- **固化脚本含凭据**:evidence/ 里的回归脚本带 session/token,遵守 09 号产物隔离(不入 git 远端)。
