#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""diff_ref_check.py — 有号/越权/凭证面收工必须指回差分 id（不定级、不探测）

验收句：正向 covered / 凭证面 / 越权收工 → 必须指回 diff.json#D-xx 或 证据/D-xx；
只写「能登录/像越权」不挂 id → FAIL。
「禁止 covered / 不标 covered」是否定句，不触发。

无正向触发话术 → SKIP。若任务根有完整 证据/ 包，可另跑 evidence_pack_check。

用法:
  python diff_ref_check.py --dig-root DIR
  python diff_ref_check.py --host-dir DIR
  python diff_ref_check.py --task-root DIR
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SKIP = frozenset(
    {"js", "资产", "报告", "node_modules", ".git", "_trash", "tmp", "temp", "__pycache__", "编排"}
)

# 正向收工/浅层宣称才触发；STS/临时钥/信任边界不作裸触发（易误杀钥匙段/主机名）
TRIGGER_RE = re.compile(
    r"(?i)\bcovered\b|本站\s*covered|收工|"
    r"能登录(?:控制台)?|可登录控制台|像越权|越权读|越权写|凭证面"
)
# 否定/路径提及：抹掉后再判触发
NEG_COVERED_RE = re.compile(
    r"(?i)(?:禁止|不要|不改|未改|勿|别|不得|未标|不标|禁)[^\n]{0,40}\bcovered\b|"
    r"标\s*covered|"  # 死路/禁止清单里的「标 covered」；正向用「已 covered / 本站 covered」
    r"covered_hosts|"
    r"未\s*covered|"
    r"假装[^\n]{0,12}covered"
)
REF_RE = re.compile(
    r"diff\.json#(D-\d+)|证据/(?:diff\.json#)?(D-\d+)|\b证据\s*=\s*[^\n]*(D-\d+)|\b(D-\d+)\b",
    re.I,
)
SHALLOW_ONLY_RE = re.compile(r"能登录(?:控制台)?|可登录控制台|像越权")


def read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def resolve_task_root(dig_or_host: Path, is_host: bool) -> Path:
    dig = dig_or_host.parent if is_host else dig_or_host
    parent = dig.parent
    if (parent / "证据").is_dir() or (parent / "编排").is_dir() or (parent / "资产").is_dir():
        return parent
    return dig if (dig / "证据").is_dir() else parent


def iter_hosts(dig_root: Path) -> list[Path]:
    if not dig_root.is_dir():
        return []
    return sorted(
        d
        for d in dig_root.iterdir()
        if d.is_dir() and d.name not in SKIP and not d.name.startswith(".")
    )


def host_done_blob(host: Path) -> str:
    parts = []
    for name in ("DONE_auth.md", "DONE_anon.md", "DONE.md"):
        fp = host / name
        if fp.is_file():
            parts.append(read_text(fp))
    return "\n".join(parts)


def check_text(label: str, text: str) -> tuple[str, str]:
    masked = NEG_COVERED_RE.sub(" ", text)
    if not TRIGGER_RE.search(masked):
        return "SKIP", "无正向 covered/凭证/越权收工话术"
    if REF_RE.search(text):
        return "PASS", "已指回差分 id"
    return "FAIL", "covered/凭证面/越权收工未指回差分 id（如 diff.json#D-xx）"


def main() -> int:
    ap = argparse.ArgumentParser(description="差分指回习惯闸")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--host-dir", type=Path)
    g.add_argument("--dig-root", type=Path)
    g.add_argument("--task-root", type=Path)
    ap.add_argument("--only-fail", action="store_true")
    args = ap.parse_args()

    if args.task_root:
        task_root = args.task_root.resolve()
        dig_root = task_root / "dig" if (task_root / "dig").is_dir() else task_root
        hosts = iter_hosts(dig_root) or [task_root]
    elif args.host_dir:
        hosts = [args.host_dir.resolve()]
        task_root = resolve_task_root(hosts[0], True)
    else:
        dig_root = args.dig_root.resolve()
        task_root = resolve_task_root(dig_root, False)
        hosts = iter_hosts(dig_root)

    fail = 0
    saw = 0
    for h in hosts:
        text = host_done_blob(h)
        # also merge conclusion if under task 证据/
        conc = task_root / "证据" / "conclusion.md"
        if conc.is_file():
            text = text + "\n" + read_text(conc)
        st, note = check_text(h.name, text)
        if st == "SKIP":
            continue
        saw += 1
        if st == "FAIL":
            fail += 1
            print(f"FAIL\t{h.name}\t{note}")
        elif not args.only_fail:
            print(f"PASS\t{h.name}\t{note}")

    if saw == 0:
        if not args.only_fail:
            print(f"SKIP\t{task_root}\t无触发收工话术")
        return 0
    if fail:
        print(f"# FAIL hosts={fail}/{saw} — 差分指回缺失")
        return 1
    if not args.only_fail:
        print(f"# OK fail=0 hosts={saw}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
