#!/usr/bin/env python3
"""72stack-sec 仓库自检:相对链接 / nuclei YAML / 计数一致性。

用法: python scripts/validate.py   (在仓库根目录或任意位置均可)
任一检查失败 → 退出码 1。改完文档跑一遍,防悬空链接和计数漂移。
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
errors = []

# ---------- 1. markdown 相对链接存在性 ----------
LINK = re.compile(r"\[[^\]\n]*\]\(([^)#\n]+?)(?:#[^)\n]*)?\)")  # 禁止跨行配对,防 payload 文本幻影链接
FENCE = re.compile(r"```.*?```", re.DOTALL)
warnings = []
for md in ROOT.rglob("*.md"):
    text = FENCE.sub("", md.read_text(encoding="utf-8"))  # 代码块内的 () 不是链接
    rel = md.parent
    archived = "h1-reports" in md.parts  # 归档原文,图片未镜像属预期
    for target in LINK.findall(text):
        t = target.strip()
        if not t or t.startswith(("http://", "https://", "mailto:")):
            continue
        if not (rel / t).exists():
            msg = f"broken link: {md.relative_to(ROOT)} -> {t}"
            (warnings if archived else errors).append(msg)

# ---------- 2. nuclei 模板 ----------
try:
    import yaml
    for y in (ROOT / "references/tools/nuclei-templates").glob("*.yaml"):
        try:
            d = yaml.safe_load(y.read_text(encoding="utf-8"))
            for key in ("id", "info", "http"):
                if key not in d:
                    raise ValueError(f"missing key: {key}")
        except Exception as e:
            errors.append(f"bad nuclei template: {y.name}: {e}")
except ImportError:
    print("note: pyyaml not installed, skip yaml check")

# ---------- 3. 计数一致性 ----------
playbook_dir = ROOT / "references/playbooks"
n_playbooks = sum(1 for p in playbook_dir.iterdir() if p.is_dir()) + sum(
    1 for p in playbook_dir.glob("*.md") if p.name != "00-index.md"
)
for f, pattern in [
    ("SKILL.md", rf"{n_playbooks} 个攻击类 playbook"),
    ("README.md", rf"{n_playbooks} 类攻击 playbook"),
]:
    text = (ROOT / f).read_text(encoding="utf-8")
    if pattern not in text:
        errors.append(f"count mismatch in {f}: expected '{pattern}'")

# payloader/h1-reports 已移除(20260831 瘦身:零产出数据支撑);payload 出处=playbook 或自证构造逻辑

# ---------- 结果 ----------
if warnings:
    print(f"{len(warnings)} warning(s) (h1-reports 归档原文,忽略):")
if errors:
    print("FAIL:")
    for e in errors:
        print("  -", e)
    sys.exit(1)
print(f"OK: links valid, {n_playbooks} playbooks, nuclei templates pass")
