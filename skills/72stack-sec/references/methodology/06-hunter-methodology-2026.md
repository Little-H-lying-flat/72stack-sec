# 2026 一线猎人方法论汇编(国内外大佬打法提炼)

> 来源:Jhaddix TBHM v4(GitHub jhaddix/tbhm)、kaneru《Bug Bounty 2025: The Unfiltered Roadmap》、Penligent《AI for Bug Bounty 2026》、Bugcrowd 2026 hacker survey、国内 Awesome-SRC-experience 体系、长亭百川云/JSRC/安全内参实战复盘。
> 定位:**认知层升级文件**——payload 不在这里,去 playbooks;这里是"怎么想、怎么选、怎么排、怎么用 AI"。

---

## 1. 选目标哲学(国外主流,kaneru/TBHM)

- **打"被遗忘的资产"**:孤儿域名、收购来的旧系统、组织缝隙("哪些系统落在职责边界之间?")——收购整合带是权限不一致/孤儿 API/跨租户故障高发区
- **避开饱和区**:公开主站的 auth bypass 现在是彩票;固件、CI/CD 完整性、ML 投毒这类冷面 dup 率低 ~70%
- **新兴面**:工业 IoT、API 聚合层、临时云基础设施(坏模板"修复后自动重建")
- **T 型知识**:先专一类再扩面;YouTube 教程普遍落后当前技术数年——学**披露报告的研究方法**(不是学洞本身),RealWorld CTF 类挑战

## 2. 国内上分现实(公众号/先知/长亭共识)

- **信息收集广度决定攻击广度**:子域名数量 ≈ 漏洞产出(多篇复盘反复验证)
- **敏感信息挖掘是性价比之王**:
  - Google: `site:target.com filetype:xls 登录` / `filetype:txt 密码` / `inurl:php?id=`
  - GitHub/Gitee 代码搜:数据账密、`access_key`、内网域名、第三方配置(edusrc 骚技巧)
  - fofa/shodan 资产面 + favicon hash 关联
- **越权 = 抓包改参数,别犹豫**:普通用户直接访问管理员接口成功即中;横向(改 ID)→ 纵向(改角色)→ 无鉴权(删 header 直接访)三层递进
- **公益 SRC 练手 → 企业 SRC 上分**是公认路径;漏洞盒子类平台对新厂收货快

## 3. 攻击面组织(三阶段,国内外一致)

| 阶段 | 动作 | 反模式 |
|---|---|---|
| Mapping | 测任何点之前,先画全入口点清单 | 上来就 fuzz |
| Categorize | 按**技术栈 + 业务功能**分组(不是扁平域名列表) | 一视同仁 |
| Priority | 高价值资产优先打 | 顺字典序扫 |

国内自动化三件套对应:资产发现流 / 漏扫引擎 / 带外探测(OOB)。Awesome-SRC-experience 的"背景→攻坚→自动化"三段式:每类洞先懂业务背景,再手工攻坚,最后沉淀自动化。

## 4. 2026 年的三个反转

1. **历史数据挖掘 > 主动扫描**(对旧教条的推翻):Wayback/CT/历史快照里翻消失的 endpoint,比盲扫活体收益高
2. **优势来自数据关联,不是更好的扫描器**:公开工具挖到的洞人人能挖——自定义字典/脚本是必选项不是加分项(自定义 wordlist 是公认 ROI 最高投入)
3. **链式打点 3-5 倍于单点**:SSRF→云提权、原型污染×serverless、GraphQL 深递归、XSS→客户端 IPC→接管(参考 xss/12 的 `xss-ai-client-escape`);国内对应"边界突破→云原生基础设施"
4. 附:手动 HTTP/3 测试是当前工具盲区,tooling 落后即是人肉窗口

## 5. AI 时代工作流(Penligent 2026 + Bugcrowd 调研)

**六步循环**:capture → compress → hypothesize → validate → preserve → report。

**分工表(AI 干活,人拍板):**

| 阶段 | AI 的活 | 你的活 |
|---|---|---|
| Scope 解析 | 提取约束/禁测项/披露条款 | 最终解释权在自己(scope 解读**不准交给 AI**) |
| Recon 分诊 | 资产聚类/技术栈摘要/异常标记 | 选打哪个 |
| API 鉴权测试 | 建"角色×对象"矩阵、diff 双账号响应、提出最小非破坏验证请求 | 证明越权与影响 |
| JS/SPA 分析 | 从 bundle 抽路由/endpoint/鉴权敏感流,聚类"admin 面/上传管道" | 后端验证(前端校验是 theater) |
| 源码辅助 | 汇总 sink/wrapper/patch diff,问"哪些兄弟站点共享同一不安全假设" | 确认可利用性 |
| 报告 | 把已确认笔记格式化,逐句标注 fact/inference/context | 对每句话真实性负责 |

**两个 prompt 模式:**
- **API diff**:scope 备注 + 双账号配对请求/响应 + 字段扁平 diff → 要"疑似对象级/属性级鉴权问题",分"弱线索/高优验证"两栏,禁止破坏性动作
- **纪律 prompt**:强制输出"已确认事实 / 强假设 / 弱假设 / 最小下一步 / 待保全证据"——防止模型从"有点怪"直接跳"高危"

**六个不要交给 AI**(滥用模式,来自实战复盘):
1. scope 解读(会测出界)
2. 可利用性判定("响应不同 ≠ 有影响;反射 ≠ 执行")
3. 早期 lead 泛滥(5 个想透的 > 500 个没评估的)
4. 贴扫描器输出直接产出(减少 slop,不是生产 slop)
5. 把聊天线程当笔记本(原始产物在模型外留存)
6. 营销腔影响描述(triager 要精确爆炸半径)

**数据**:Bugcrowd 2026 调研 82% 猎人已用 AI;HackerOne 有效 AI 漏洞报告 +210%(prompt injection 领跑)。**现实检查**:LLM 类洞仍 <5% 产出,经典 web/API 仍是吃饭家伙——AI 先当工具,再当目标。

## 6. 心态与时间(kaneru + TBHM)

- **一小时规则**:60 分钟无进展 → 记录,切换;2-3 小时整块时间 + "回访队列"
- **30% 时间写报告**:讲得好的 medium 常比讲不好的 critical 值钱
- **dup 冷静 24h** 再回复 triager;"被拒的是报告,不是你"
- 收入结构:稳定猎人赏金只占 40-60%(咨询/工具/内容补充);首赏现实预期 6-12 个月
- 连续三个月低于阈值 = 换策略的信号

## 7. 与本 skill 的接口

- 选点/排优先级 → 本文件 §1-§4,细化打点回 playbooks
- AI 分工在 Phase 2(recon 分诊)/Phase 4(API diff)直接套 §5 表格
- 证据纪律红线在 `03-evidence-discipline.md`,与本文件 §5"六不要"叠加生效
- 国内场景敏感信息语法在 Phase 2 直接用;深挖入口回对应 playbook

## 8. 来源

- [jhaddix/tbhm (TBHM v4)](https://github.com/jhaddix/tbhm)
- [kaneru: Bug Bounty 2025 The Unfiltered Roadmap](https://kaneru.netlify.app/blog/bugbounty-roadmap/)
- [Penligent: How to Use AI for Bug Bounty in 2026](https://www.penligent.ai/hackinglabs/how-to-use-ai-for-bug-bounty-in-2026/)
- [Bugcrowd: What I learned building AI agents for bug bounty](https://www.bugcrowd.com/blog/what-i-learned-building-ai-agents-for-bug-bounty-hunting/)
- [owl234/Awesome-SRC-experience](https://github.com/owl234/Awesome-SRC-experience)
- 安全内参/长亭百川云/JSRC 小课堂/edusrc 骚技巧等公众号复盘(要点已并入 §2/§4)
- 公众号"ai时代下衍生出的通杀"(XSS→接管链,见 xss/12 `xss-ai-client-escape`)
