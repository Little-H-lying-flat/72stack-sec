#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""next_after_fail_check.py — 闸红后续转话术闸（不定级、不探测）

验收句：
  1) p2 FAIL / 终章话术 → 禁本站 covered + 必须 NEXT（补席|下种子|人工过盾）
  2) 种子队列有 pending 却完全无 NEXT → FAIL
  3) #4 收紧：leftover **真空** 且队列有 pending，却无「NEXT: 下种子」
     （只写 NEXT: 补席 / 干等出面 → FAIL；有活面时只写补席仍 PASS）

规则：
  - 终章话术且无正向 NEXT → FAIL
  - leftover 真空 + 队列 pending + 无「NEXT: 下种子」→ FAIL（证据包 28）
  - 队列 pending + 完全无 NEXT → FAIL
  - leftover 仍有活面时，仅「NEXT: 补席」可 PASS（不逼下种子）
  - 无终章、无 pending、无 编排/ → SKIP

用法:
  python next_after_fail_check.py --dig-root DIR
  python next_after_fail_check.py --host-dir DIR
  python next_after_fail_check.py --task-root DIR
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SKIP_DIRS = frozenset(
    {"js", "资产", "报告", "node_modules", ".git", "_trash", "tmp", "temp", "__pycache__", "编排"}
)

STOP_RE = re.compile(
    r"整场停|整场停止|本波收口|终章|本种子收口|不再\s*spawn|本轮完成.{0,24}收口|"
    r"纯文本终章|本波产出已收口"
)
# L743 挂起话术： alone OK if NEXT:下种子 exists when queue pending
HANG_RE = re.compile(r"过盾\s*waiting|禁止\s*covered|禁\s*covered|肥面禁止 covered")

POS_NEXT_ANY_RE = re.compile(
    r"(?im)(?:^|\n)\s*(?:[-*]\s*)?NEXT\s*[：:=]\s*(?:补席|下种子|人工过盾)"
)
POS_NEXT_SEED_RE = re.compile(
    r"(?im)(?:^|\n)\s*(?:[-*]\s*)?NEXT\s*[：:=]\s*下种子"
)
NEG_NEXT_RE = re.compile(
    r"(?im)无\s*NEXT|无补席|无下种子|无人工过盾|（无\s*NEXT）|\(无\s*NEXT\)|"
    r"（无\s*NEXT\s*[：:]\s*下种子）"
)

# table row: | name | pending |  or  | pending |
PENDING_ROW_RE = re.compile(
    r"(?im)^\s*\|[^\n]*\|\s*pending\s*\|"
)


def read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def resolve_task_root(dig_or_host: Path, is_host: bool) -> Path:
    dig = dig_or_host.parent if is_host else dig_or_host
    parent = dig.parent
    if (parent / "编排").is_dir():
        return parent
    if (dig / "编排").is_dir():
        return dig
    return parent if (parent / "资产").is_dir() else dig


def collect_orch(task_root: Path) -> tuple[str, bool]:
    orch_parts: list[str] = []
    has_next_file = False
    orch = task_root / "编排"
    if orch.is_dir():
        for fp in sorted(orch.rglob("*.md")):
            text = read_text(fp)
            orch_parts.append(text)
            if fp.name.upper().startswith("NEXT") and text.strip():
                has_next_file = True
    return "\n".join(orch_parts), has_next_file


def collect_dig(dig_root: Path) -> str:
    parts: list[str] = []
    if not dig_root.is_dir():
        return ""
    for name in ("DONE_anon.md", "DONE_auth.md", "DONE.md", "conclusion.md"):
        for fp in dig_root.rglob(name):
            if any(part in SKIP_DIRS for part in fp.parts):
                continue
            parts.append(read_text(fp))
    return "\n".join(parts)


def collect_seed_queue(task_root: Path) -> str:
    assets = task_root / "资产"
    blobs: list[str] = []
    candidates = [
        assets / "种子队列.md",
        task_root / "种子队列.md",
    ]
    if assets.is_dir():
        for fp in assets.glob("*种子*.md"):
            candidates.append(fp)
    seen: set[Path] = set()
    for fp in candidates:
        rp = fp.resolve() if fp.exists() else None
        if not fp.is_file() or rp in seen:
            continue
        seen.add(rp)
        blobs.append(read_text(fp))
    return "\n".join(blobs)


def has_pending_seeds(queue_text: str) -> bool:
    return bool(PENDING_ROW_RE.search(queue_text))


def collect_leftover(task_root: Path) -> str:
    assets = task_root / "资产"
    candidates = [
        assets / "leftover.md",
        task_root / "leftover.md",
    ]
    if assets.is_dir():
        for fp in assets.glob("*leftover*.md"):
            candidates.append(fp)
    blobs: list[str] = []
    seen: set[Path] = set()
    for fp in candidates:
        if not fp.is_file():
            continue
        rp = fp.resolve()
        if rp in seen:
            continue
        seen.add(rp)
        blobs.append(read_text(fp))
    return "\n".join(blobs)


def leftover_is_vacuum(leftover_text: str) -> bool:
    """True when leftover declares empty / 真空 / pending=0 with no live hosts."""
    if not leftover_text.strip():
        return False
    # explicit vacuum markers
    if re.search(r"leftover\s*=\s*0|真空|无\s*pending\s*host|无活\s*host|无\s*doing", leftover_text, re.I):
        # if also has live pending/doing host rows, not vacuum
        if re.search(r"(?im)^\s*\|[^\n]*\|\s*(?:pending|doing)\s*\|", leftover_text):
            # host table still has work
            return False
        if re.search(r"(?im)^\s*[-*]\s*\S[^\n]*\b(?:pending|doing)\b", leftover_text):
            return False
        return True
    if re.search(r"(?im)pending\s*=\s*0.*doing\s*=\s*0|doing\s*=\s*0.*pending\s*=\s*0", leftover_text):
        return True
    return False



def positive_next_any(orch: str, has_next_file: bool) -> bool:
    if NEG_NEXT_RE.search(orch) and not POS_NEXT_ANY_RE.search(orch):
        return False
    if POS_NEXT_ANY_RE.search(orch):
        return True
    if has_next_file and re.search(r"补席|下种子|人工过盾", orch):
        if NEG_NEXT_RE.search(orch) and not POS_NEXT_ANY_RE.search(orch):
            return False
        return True
    return False


def positive_next_seed(orch: str) -> bool:
    if NEG_NEXT_RE.search(orch) and not POS_NEXT_SEED_RE.search(orch):
        # explicit 无 NEXT: 下种子
        if re.search(r"(?im)无\s*NEXT\s*[：:]\s*下种子|（无\s*NEXT\s*[：:]\s*下种子）", orch):
            return False
    return bool(POS_NEXT_SEED_RE.search(orch))


def main() -> int:
    ap = argparse.ArgumentParser(description="闸红后续转 / NEXT 话术闸")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--host-dir", type=Path)
    g.add_argument("--dig-root", type=Path)
    g.add_argument("--task-root", type=Path)
    ap.add_argument("--only-fail", action="store_true")
    args = ap.parse_args()

    if args.task_root:
        task_root = args.task_root.resolve()
        dig_root = task_root / "dig" if (task_root / "dig").is_dir() else task_root
    elif args.host_dir:
        host = args.host_dir.resolve()
        dig_root = host.parent
        task_root = resolve_task_root(host, is_host=True)
    else:
        dig_root = args.dig_root.resolve()
        task_root = resolve_task_root(dig_root, is_host=False)

    orch, has_next_file = collect_orch(task_root)
    dig = collect_dig(dig_root)
    queue = collect_seed_queue(task_root)
    leftover = collect_leftover(task_root)
    combined = orch + "\n" + dig
    has_orch = (task_root / "编排").is_dir()
    stop = bool(STOP_RE.search(combined))
    hang = bool(HANG_RE.search(combined))
    pending = has_pending_seeds(queue)
    vacuum = leftover_is_vacuum(leftover)
    nxt_any = positive_next_any(orch, has_next_file)
    nxt_seed = positive_next_seed(orch)

    # #4：leftover 真空 + 队列 pending → 必须 NEXT: 下种子（禁只写补席干等）
    if vacuum and pending and not nxt_seed:
        print(
            f"FAIL\t{task_root}\t"
            "leftover 真空且种子队列有 pending，却无 NEXT: 下种子"
            "（只写补席/干等出面 = 编排 bug）"
        )
        return 1

    # 队列有 pending 却完全无任何 NEXT → FAIL（有活面时写补席即可）
    if pending and not nxt_any and not nxt_seed:
        print(
            f"FAIL\t{task_root}\t"
            "种子队列有 pending 却无 NEXT（补席|下种子|人工过盾）→ 编排 bug；"
            "过盾 waiting / 禁 covered 只能挂起本种子，不能当整场终章"
        )
        return 1

    if stop and not nxt_any:
        print(
            f"FAIL\t{task_root}\t"
            "闸红/终章话术后无 NEXT（补席|下种子|人工过盾）→ 编排 bug；"
            "p2 FAIL 只禁本站 covered，不是整场停"
        )
        return 1

    if not stop and not pending and not has_orch and not hang and not vacuum:
        if not args.only_fail:
            print(f"SKIP\t{task_root}\t无终章/pending/编排")
        return 0

    if nxt_any or nxt_seed:
        if not args.only_fail:
            if vacuum and nxt_seed:
                kind = "下种子（真空翻种）"
            elif nxt_seed:
                kind = "下种子"
            else:
                kind = "补席|下种子|人工过盾"
            print(f"PASS\t{task_root}\t已有 NEXT（{kind}）")
        return 0

    if not args.only_fail:
        print(f"PASS\t{task_root}\t无触发终章/pending 硬条件")
    return 0


if __name__ == "__main__":
    sys.exit(main())
