#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ready_resume_check.py — 过盾 ready 必须插登录轨（不定级、不探测）

验收句：过盾表出现 ready → 同回合必须插登录轨 / NEXT: 有会话
  或 编排/_auth_spawn_batch.json 非空 seats（login_lane 旁路）；
已有 ready 却只继续未登录 / 纯文本无登录轨 NEXT → FAIL。

用法:
  python ready_resume_check.py --task-root DIR
  python ready_resume_check.py --dig-root DIR
  python ready_resume_check.py --host-dir DIR
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# 只认正向 NEXT 行，不认「无 NEXT: 插登录轨」里的词面
POS_AUTH_NEXT_RE = re.compile(
    r"(?im)^(?!.*无\s*NEXT)[^\n]*\bNEXT\s*[：:=]\s*(?:有会话|插登录轨)\b"
)
POS_SPAWN_RE = re.compile(
    r"(?im)^(?!.*无)[^\n]*(?:spawn\s*)?本轨\s*=\s*有会话|^(?!.*无)[^\n]*插登录轨\s*[→→-]"
)
NEG_AUTH_RE = re.compile(
    r"(?im)无\s*NEXT\s*[：:]\s*(?:插登录轨|有会话)|无登录轨\s*NEXT|"
    r"只(?:继续)?挖未登录|无有会话\s*spawn|纯文本终章"
)


def read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def resolve_task_root(dig_or_host: Path, is_host: bool) -> Path:
    dig = dig_or_host.parent if is_host else dig_or_host
    parent = dig.parent
    if (parent / "资产").is_dir() or (parent / "编排").is_dir():
        return parent
    if (dig / "资产").is_dir():
        return dig
    return parent


def find_shield_queue(task_root: Path) -> Path | None:
    cands = [
        task_root / "资产" / "人工过盾续挖.md",
        task_root / "人工过盾续挖.md",
    ]
    for fp in cands:
        if fp.is_file():
            return fp
    assets = task_root / "资产"
    if assets.is_dir():
        for fp in assets.glob("*过盾*.md"):
            if fp.is_file():
                return fp
    return None


def has_ready(queue_text: str) -> bool:
    for line in queue_text.splitlines():
        if not line.strip().startswith("|"):
            continue
        if re.search(r"(?i)host|状态|----", line):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if any(c.lower() == "ready" for c in cells):
            return True
    return False


def collect_orch(task_root: Path) -> str:
    orch = task_root / "编排"
    if not orch.is_dir():
        return ""
    return "\n".join(read_text(fp) for fp in sorted(orch.rglob("*.md")))


def has_auth_spawn_batch(task_root: Path) -> bool:
    p = task_root / "编排" / "_auth_spawn_batch.json"
    if not p.is_file():
        return False
    try:
        data = json.loads(p.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return False
    seats = data.get("seats") if isinstance(data, dict) else None
    return bool(seats)


def has_positive_auth_next(orch: str, task_root: Path | None = None) -> bool:
    if task_root is not None and has_auth_spawn_batch(task_root):
        return True
    if NEG_AUTH_RE.search(orch) and not POS_AUTH_NEXT_RE.search(orch):
        return False
    if POS_AUTH_NEXT_RE.search(orch):
        return True
    if POS_SPAWN_RE.search(orch) and not NEG_AUTH_RE.search(orch):
        return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description="过盾 ready 续挖闸")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--host-dir", type=Path)
    g.add_argument("--dig-root", type=Path)
    g.add_argument("--task-root", type=Path)
    ap.add_argument("--only-fail", action="store_true")
    args = ap.parse_args()

    if args.task_root:
        task_root = args.task_root.resolve()
    elif args.host_dir:
        task_root = resolve_task_root(args.host_dir.resolve(), True)
    else:
        task_root = resolve_task_root(args.dig_root.resolve(), False)

    qpath = find_shield_queue(task_root)
    if not qpath:
        if not args.only_fail:
            print(f"SKIP\t{task_root}\t无人工过盾续挖表")
        return 0

    qtext = read_text(qpath)
    if not has_ready(qtext):
        if not args.only_fail:
            print(f"SKIP\t{task_root}\t过盾表无 ready 行")
        return 0

    orch = collect_orch(task_root)
    if not has_positive_auth_next(orch, task_root):
        print(
            f"FAIL\t{task_root}\t"
            "过盾表已有 ready，却无 NEXT:有会话/插登录轨 且无 _auth_spawn_batch → 编排 bug；"
            "禁止只继续未登录或纯文本终章"
        )
        return 1

    if not args.only_fail:
        extra = " + auth_batch" if has_auth_spawn_batch(task_root) else ""
        print(f"PASS\t{task_root}\tready → 已有登录轨/有会话 NEXT{extra}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
