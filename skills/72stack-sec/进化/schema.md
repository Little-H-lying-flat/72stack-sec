# Episode / Proposal schema

## episode（`进化/episodes.jsonl` 每行一个 JSON 对象）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | 是 | 稳定 id：`{host}|{track}|{content_hash8}` |
| ts | string | 是 | ISO8601 写入时间 |
| task | string | 是 | 任务根目录名 |
| host | string | 是 | 如 `gmsrm.ctrip.com` |
| track | string | 是 | `anon` \| `anon_glance` \| `auth` \| `unknown` |
| fat_thin | string | 否 | 肥/瘦原文摘录（截断） |
| outcome | string | 是 | `high_report` \| `mid_report` \| `report_other` \| `no_report` \| `stuck` \| `gate_warn` \| `unknown` |
| win_patterns | string[] | 否 | 从 DONE/报告标题抽的根因标签（无 payload） |
| fail_modes | string[] | 否 | 卡住/失败模式标签 |
| stuck | string\|null | 否 | `卡住对照=` 原值截断 |
| carry_hosts | string[] | 否 | `带出host=` 解析出的 host 列表 |
| carry_raw | string | 否 | 带出host 原始行截断 |
| next | string\|null | 否 | NEXT 动作：补席\|下种子\|人工过盾\|有会话\|其它 |
| report_refs | string[] | 否 | 报告相对路径 |
| severity_hints | string[] | 否 | 从报告/DONE 看到的 高危/中危/严重 |
| source_files | string[] | 否 | 读过的 DONE/报告路径 |
| notes | string | 否 | 短备注，禁 Cookie/PII |

### win_patterns 建议枚举（可扩展，写入时小写蛇形）

`hardcoded_token` `upload_html_exec` `samesite_api_read` `idor` `auth_bypass` `info_leak` `ssti` `sqli` `ssrf` `other`

### fail_modes 建议枚举

`http_405` `empty_shell` `waf_family` `need_sms` `need_invite` `cors_only` `no_diff` `timeout` `other`

---

## proposal（`进化/proposals/{id}.md` + 同名 `.json` 元数据）

| 字段 | 说明 |
|------|------|
| id | `prop_{date}_{short}` |
| kind | `blindspot_candidate` \| `probe_recipe` \| `dispatch_bias` \| `report_checklist` \| `done_fix` |
| status | `pending` \| `approved` \| `rejected` \| `applied` \| `applied_auto` |
| from_episodes | episode id 列表 |
| title | 一行标题 |
| body_md | 人读提案（禁利用步骤、禁实值密钥） |
| merge_target | 建议合并到哪里（盲区 auto 层 / 短表指针须人审 / 仅任务内 checklist） |

`evolve_apply`：  
- `--auto-safe`（hook 默认）：`blindspot_candidate` / `probe_recipe` 且 merge_target 不含 hunt-iter/rules/短表/调度 → 追加 `知识库/semantic-blindspots.auto.md`，status=`applied_auto`。去重、拒实值。不改主表、不改 rules。  
- `pending` → 人改 json `status=approved` 或 CLI `--approve`（其余 kind）  
- `--apply` 仅处理 `approved`：拷到 `进化/applied/` 并写 `merge_hint.txt`。
