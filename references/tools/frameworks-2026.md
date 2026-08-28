# 2026 攻防框架调研 — 值得吸收的既有生态

> 调研日期 2026-08-28。问题:GitHub 上的 SRC/渗透框架里,有什么能让本 skill 变得更好?
> 结论:框架是**工具编排器**,本 skill 是**认知工作流**——不重复造轮子,吸收四样东西:命令流水线、验证模板、agentic 攻击循环、国内工具链。

## 1. 主流框架速览

| 框架 | Stars | 定位 | 对本 skill 的价值 |
|---|---|---|---|
| **PentAGI** (vxcontrol/pentagi) | ~21.5k | 全自主多 agent 渗透系统 | agent 分工架构(专职 agent:recon/exploit/verify)→ 对照本 skill 的 Phase 分工 |
| **Strix** (usestrix/strix) | 高速增长 | 自主 AI 攻击 agent,动态跑代码验证 | "找到即验证"的闭环思想 → Phase 4 强制流程已对齐 |
| **reNgine / reNgine-ng** | ~8.8k | web 侦察编排套件 | 子域→探活→截图→URL 收集→漏洞扫描的**流水线顺序** |
| **reconFTW** (six2dez) | ~8k | 一键自动化 recon | 最完整的**命令流水线字典**(passive→active→vulns 三段) |
| **Osmedeus** (j3ssie) | — | 声明式 YAML 安全工作流引擎 | "把流程写成可审计的定义"→本 skill 的 checkpoint 思路同源 |
| **CAI** (aliasrobotics) | ~3.6k | AI Security 框架(**已停更**) | 300+ 模型接入的抽象层设计;论文《CAI Fluency》的 benchmark 方法论 |
| **PentestGPT** | — | 交互→自主演进的 GPT 渗透助手 | 攻击树推理与任务分解提示词 |
| **OneForAll** | ~10k+ | 国产子域收集 | Phase 2 国内子域收集首选工具(替代纯 subfinder) |

## 2. 采纳清单(已/计划落进本 skill)

- [x] **recon 流水线顺序**(reconFTW/reNgine 三段式)→ 融合进 SKILL.md Phase 2→3 的既有 checkpoint(passive-only → active matrix),本 skill 的"Phase 2 禁主动发包"比框架默认更严,保留
- [x] **agentic 攻击循环**(PentAGI/CAI)→ Phase 4 的"每候选目标走一遍"即循环实现;LLM 分工见 `methodology/06` §5
- [x] **验证优先**(Strix 找到即验证)→ `methodology/07-js-recon.md` §6 后端验证矩阵
- [ ] **Nuclei 模板生态**:把高频 playbook 的 payload 转成 nuclei YAML 验证模板(下一个可做项,产出 `references/tools/nuclei-templates/`)
- [ ] **OneForAll 进 Phase 2 工具推荐**:国内目标子域收集首选,已在本文件记录,待写进 Phase 2 条件触发
- [ ] **Osmedeus 式流程导出**:把 5-Phase 工作流导出为 YAML 工作流定义,供 Osmedeus/reNgine 用户直接跑(社区互换价值)

## 3. 反向输出定位

本 skill 有而框架没有的:**真实案例库**(2951 H1 + 273 Google VRP + 8.8 万 WooYun)、反幻觉纪律、国内外云链路、AI 生态攻击面。框架用户按本 skill 方法论人工/agent 分诊,比框架的纯扫描噪声信噪比高一个量级——这是对外宣传的差异点。

## 4. 来源

- [PentAGI](https://github.com/vxcontrol/pentagi) · [Strix](https://github.com/usestrix/strix) · [reNgine](https://github.com/yogeshojha/rengine) · [reconFTW](https://github.com/six2dez/reconftw) · [Osmedeus](https://github.com/j3ssie/osmedeus) · [CAI](https://github.com/aliasrobotics/CAI) · [OneForAll](https://github.com/shmilylty/OneForAll)
- [AppSec Santa: AI Pentesting Agents 2026 (39+ tools)](https://appsecsanta.com/research/ai-pentesting-agents-2026)
