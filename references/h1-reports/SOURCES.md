# 报告来源清单（可持续收割）

> 现有库存:HackerOne High/Critical 2951 份唯一案例(raw 2887 + 2026-08 增量),分类索引 2836 条/144 类;WooYun 统计 88,636 条。
> 本文回答"还能从哪找已披露报告",按**可自动化程度**排序。

## 一、可自动化收割(结构化 API/导出)

已镜像:[Google VRP Writeups 273 篇](../writeups/google-vrp-writeups.md)(xdavidhu 清单 CSV,2026-08-28)

| 来源 | 内容 | 接入方式 |
|---|---|---|
| **HackerOne hacktivity** | 高质量 High/Critical,全程讨论 | 公开 GraphQL/REST,本库现有管道即此来源(`h1-harvest-*` 脚本),建议月度增量 |
| **Google VRP (bughunters.google.com)** | 全公开 tracker,含完整讨论与修复,质量顶级 | issue tracker 公开,可按组件抓取 |
| **Project Zero tracker** | 深度技术报告(浏览器/内核/沙箱) | issuetracker 公开,按 component 抓取 |
| **GHSA / GitHub Advisory** | 带 PoC/补丁 diff 的 CVE 级报告 | API 公开,可按 ecosystem+CWES 定向拉 |
| **Meta Whitehat** | Facebook/Meta 披露报告 | 公开页,反爬较强 |

## 二、半自动(公开页需解析)

| 来源 | 内容 | 备注 |
|---|---|---|
| **Intigriti** | 公开披露报告 + 月度 XSS challenge writeup 集 | 欧洲平台,报告叙述质量高,适合学"报告写法" |
| **YesWeHack** | 公开披露 + 博客复盘 | 同上 |
| **ZDI** | CVE 级 advisory(工控/企业软件为主) | 适配 `rce/` 供应链与框架类 |
| **MSRC** | 微软赏金官方博客 + researcher writeup | Windows/云方向 |

## 三、人工阅读(公众号/博客复盘,喂给 by-weakness 或方法论)

- 长亭百川云 rivers.chaitin.cn(越权/未授权系列实战复盘)
- 先知社区、FreeBuf、安全客
- 各大 SRC 公众号(JSRC 小课堂/阿里 SRC/美团 SRC)
- Intigriti monthly winner writeups(XSS 绕过技法密度最高)

## 四、入库规则

1. H1 增量走 `merge-h1.py` 管道:meta 过滤 High/Critical → 按 weakness 追加 → 重建 index → 校准 SKILL.md/README/marketplace 四处数字声明
2. 非结构化报告(公众号/博客)不进 by-weakness,提炼成 playbook 条目或方法论注脚(见 git 历史:vm2/云链/MCP 三笔即此模式)
3. 每次合并必须重算唯一 ID 总数(raw ∪ 增量),**不许沿用旧数字**
4. 入库前自动脱敏:披露报告正文里的历史密钥(AKIA/ASIA AK、SecretAccessKey、STS Token、私钥块)一律 `[REDACTED]` 处理——GitHub Push Protection 会拦,过期凭据也不该留在公开仓库
