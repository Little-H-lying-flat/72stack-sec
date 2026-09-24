#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""write_surface_check.py — endpoints* 写面覆盖粗检（不定级、不探测）

规则：
  - 若存在 endpoints.md / endpoints_auth.md，统计 METHOD
  - 有 GET 但无写 METHOD 且未见「写面=N/A」→ WARN
  - 默认 WARN 不单独 FAIL；--strict 时 WARN→exit 1

用法:
  python write_surface_check.py --host-dir DIR
  python write_surface_check.py --dig-root DIR [--strict] [--only-fail]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SKIP = frozenset(
    {"js", "资产", "报告", "node_modules", ".git", "_trash", "tmp", "temp", "__pycache__"}
)
EP_NAMES = ("endpoints.md", "endpoints_auth.md")
WRITE_RE = re.compile(r"\b(POST|PUT|PATCH|DELETE)\b", re.I)
GET_RE = re.compile(r"\bGET\b", re.I)
NA_RE = re.compile(r"写面\s*=\s*N/A|写面探针\s*[：:].*N/A", re.I)


def check_host(host_dir: Path) -> tuple[str, list[str]]:
    notes: list[str] = []
    blobs: list[str] = []
    found_file = False
    for name in EP_NAMES:
        fp = host_dir / name
        if fp.is_file():
            found_file = True
            blobs.append(fp.read_text(encoding="utf-8", errors="replace"))
    for name in ("DONE_anon.md", "DONE_auth.md", "DONE.md", "suspects.md"):
        fp = host_dir / name
        if fp.is_file():
            blobs.append(fp.read_text(encoding="utf-8", errors="replace"))
    if not found_file:
        return "SKIP", ["无 endpoints*"]
    text = "\n".join(blobs)
    if NA_RE.search(text):
        return "PASS", ["写面=N/A 已声明"]
    has_write = bool(WRITE_RE.search(text))
    has_get = bool(GET_RE.search(text))
    if has_get and not has_write:
        notes.append("endpoints* 见 GET 但无写 METHOD，且无写面=N/A → 只扫读轨风险")
        return "WARN", notes
    if not has_get and not has_write:
        notes.append("endpoints* 未见 METHOD 枚举（建议补测方向）")
        return "WARN", notes
    return "PASS", ["ok"]


def iter_hosts(dig_root: Path) -> list[Path]:
    return sorted(
        [
            d
            for d in dig_root.iterdir()
            if d.is_dir() and d.name not in SKIP and not d.name.startswith(".")
        ],
        key=lambda d: d.name.lower(),
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="endpoints 写面覆盖粗检")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--host-dir", type=Path)
    g.add_argument("--dig-root", type=Path)
    ap.add_argument("--only-fail", action="store_true")
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()
    hosts = [args.host_dir] if args.host_dir else iter_hosts(args.dig_root)
    warn = fail = 0
    for h in hosts:
        if not h.is_dir():
            print("ERROR 非目录: %s" % h, file=sys.stderr)
            return 2
        status, notes = check_host(h)
        if status == "WARN":
            warn += 1
        elif status == "FAIL":
            fail += 1
        if args.only_fail and status == "PASS":
            continue
        if status == "SKIP":
            continue
        print("%s\t%s\t%s" % (status, h.name, "; ".join(notes)))
    print("# write_surface WARN=%d FAIL=%d hosts=%d" % (warn, fail, len(hosts)))
    if fail or (args.strict and warn):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())