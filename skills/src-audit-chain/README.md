# src-audit-chain

源码安全审计主流程 Skill（**代码审计优先**，FOFA 为辅）。

## 安装

任选其一：

```bash
# 项目内（已在）
D:\SRC\Ai\skills\src-audit-chain

# 复制到 Claude / 用户 skills
# Windows 示例：
xcopy /E /I D:\SRC\Ai\skills\src-audit-chain %USERPROFILE%\.claude\skills\src-audit-chain
xcopy /E /I D:\SRC\Ai\skills\src-audit-chain %USERPROFILE%\.grok\skills\src-audit-chain
```

## 调用

```text
按 src-audit-chain 审计 <源码路径>
```

```text
只做通用洞：按 src-audit-chain P3–P5 审计 <路径>
```

## 脚本

```bash
python scripts/verify_sinks.py --root <SRC>
python scripts/audit_generic_scan.py --root <SRC> --out candidates.md
python scripts/fofa_query.py --query 'title="..."' --out fofa.json
```

## 流程摘要

P0 定位 → P1 指纹 → P2 FOFA 门槛（不阻断）→ **P3 鉴权** → **P4 通用洞+链路** → **P5 验证** → P6 报告 → P7 反馈
