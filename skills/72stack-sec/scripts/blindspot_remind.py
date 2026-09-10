#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P3 helper: remind主控 to append semantic-blindspots after mid+ / miss.

Does NOT scrape reports for severity (no auto-classification).
Usage:
  python blindspot_remind.py --host-dir DIR
  python blindspot_remind.py --dig-root DIR

Exit 0 always for remind mode; prints checklist lines.
With --strict-suspects-header: exit 1 if suspects.md exists but 威胁模型 missing 盲区库问句/N/A.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def check_suspects_header(path: Path) -> list[str]:
    errs: list[str] = []
    if not path.is_file():
        return ["missing suspects.md"]
    text = path.read_text(encoding="utf-8", errors="replace")
    if "N/A 瘦壳" in text or text.strip().startswith("N/A"):
        return []
    if "盲区库" not in text and "semantic-blindspots" not in text:
        errs.append("suspects.md 威胁模型头未见盲区库引用（或写 N/A 无关+原因）")
    return errs


def main() -> int:
    ap = argparse.ArgumentParser(description="P3 blindspot remind / header check")
    ap.add_argument("--host-dir", type=Path)
    ap.add_argument("--dig-root", type=Path)
    ap.add_argument("--strict-suspects-header", action="store_true")
    args = ap.parse_args()

    hosts: list[Path] = []
    if args.host_dir:
        hosts = [args.host_dir]
    elif args.dig_root:
        hosts = sorted(p for p in args.dig_root.iterdir() if p.is_dir())
    else:
        ap.error("need --host-dir or --dig-root")

    print("P3 回灌提醒（人工确认后写 知识库/semantic-blindspots.md）：")
    print("  - 本站若有中危+ 报告 → 同回合追加「命中」行")
    print("  - 若明确漏问 → 追加「漏报」行 + suspects 补丁节")
    print("  - 无洞/瘦壳 → 回灌勾 N/A")
    print("操典: 知识库/回灌闭环.md")

    bad = 0
    for h in hosts:
        s = h / "suspects.md"
        if not s.is_file():
            continue
        errs = check_suspects_header(s)
        if errs:
            bad += 1
            print(f"FAIL {h.name}: " + "; ".join(errs))
        else:
            print(f"OK   {h.name}: suspects 头含盲区引用或瘦壳 N/A")

    if args.strict_suspects_header and bad:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
