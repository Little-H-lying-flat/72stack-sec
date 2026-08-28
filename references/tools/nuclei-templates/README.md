# 72stack-sec Nuclei 验证模板

> payload **全部出自本仓库 playbook**(出处见各模板 description/reference)——反幻觉纪律同样适用于模板。
> 用法:`nuclei -t references/tools/nuclei-templates/ -l targets.txt -o result.txt`
> 定位:playbook 的"探测"是人工流程;模板是**规模化初筛**。命中后必须回到对应 playbook 做"参数频率表 → 证据链"的完整流程,模板命中 ≠ 报告。

## 模板与 playbook 映射

| 模板 | severity | 出处 playbook | 说明 |
|---|---|---|---|
| `spring-actuator-env-exposure.yaml` | high | `unauth-access.md`(5.3 heapdump 链) | 命中后走 heapdump→密码提取链 |
| `shiro-rememberme-detect.yaml` | info | `rce/10-framework.md` shiro-deserialize | 指纹;命中→反序列化利用链 |
| `thinkphp-invokefunction-detect.yaml` | critical | `rce/10-framework.md` thinkphp-rce | 用 phpinfo 变体,非破坏检测 |
| `log4j-jndi-oob-detect.yaml` | critical | `rce/10-framework.md` log4j-rce | interactsh OOB,多 header 注入点 |
| `aliyun-oss-anonymous-listing.yaml` | medium | `ssrf-cache-host/11-cloud.md` cn-object-storage | 目标直接给 bucket host |

## 纪律

1. **先指纹后利用**:shiro 模板只做指纹;利用链在读过 playbook 后人工/agent 决策
2. **非破坏变体优先**:thinkphp 用 phpinfo 不用 system;验证写权限只用时间戳命名 PoC 文件
3. 新模板的 payload 必须能在 playbook 里找到出处,新 payload 先进 playbook 再出模板
