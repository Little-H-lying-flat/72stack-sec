# FOFA 操作说明（辅线）

## 凭证来源（优先顺序）

1. 环境变量 `FOFA_KEY`（可选 `FOFA_EMAIL`）
2. FofaViewer：`*/FofaViewer_*/config.properties` 中 `key=` / `api=`
3. 用户当次提供（用完不写进报告）

```properties
# 示例路径
D:\toos\FofaViewer_1.1.16\config.properties
api=https://fofa.info
key=***
```

## 查询步骤

```bash
# 账户探活
# GET https://fofa.info/api/v1/info/my?key=...

python scripts/fofa_query.py --query 'title="产品全称"'
python scripts/fofa_query.py --queries-file queries.txt --out results.json
```

注意：

- 控制 QPS，遇 429 退避重试
- `size` 为引擎统计总数；本地再按 `ip:port` 去重
- **报告禁止粘贴完整 key**

## 门槛判定话术

```markdown
精确指纹去重 ip:port = N
- N >= 20 → 门槛通过
- 0 < N < 20 → 低暴露
- N = 0 → 未入测绘/私有化；源码审计结论独立有效
- 查询失败 → Needs FOFA，不编造
```

## 与主线关系

FOFA 结果 **不改变** 已验证源码漏洞的 Confirmed 状态；只影响“批量案例价值”评级。
