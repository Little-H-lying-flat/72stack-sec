#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""p2_gate.py — P2 一键闸：DONE 字段 + suspects 覆盖 +（可选）验票 / 空席巡检

用法:
  python p2_gate.py --dig-root DIR
  python p2_gate.py --host-dir DIR --with-ticket --proxy http://127.0.0.1:7897
  python p2_gate.py --dig-root DIR --with-seat --alerts-only
  python p2_gate.py --dig-root DIR --with-ticket --write-probes --dry-run-ticket

默认不发 HTTP（只做字段/覆盖闸）。加 --with-ticket 才验票；--with-seat 才空席巡检。
退出码: 任一子检查 FAIL / ALERT → 1；参数错 → 2
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def run(cmd: list[str]) -> int:
    print("+", " ".join(cmd))
    p = subprocess.run(cmd, cwd=str(HERE))
    return p.returncode


def main() -> int:
    ap = argparse.ArgumentParser(description="P2 一键闸")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--host-dir", type=Path)
    g.add_argument("--dig-root", type=Path)
    ap.add_argument("--with-ticket", action="store_true")
    ap.add_argument("--write-probes", action="store_true", help="验票前从 DONE 抽 ticket_probes.txt")
    ap.add_argument("--proxy", default=None)
    ap.add_argument("--dry-run-ticket", action="store_true")
    ap.add_argument("--with-seat", action="store_true", help="空席/挂起巡检（ALERT→FAIL）")
    ap.add_argument("--alerts-only", action="store_true", help="席位巡检只打 ALERT")
    ap.add_argument("--seat-hours", type=float, default=24.0)
    args = ap.parse_args()

    scope = ["--host-dir", str(args.host_dir)] if args.host_dir else ["--dig-root", str(args.dig_root)]
    rc = 0
    for script in ("done_fields_check.py", "suspects_coverage_check.py"):
        code = run([sys.executable, str(HERE / script), *scope, "--only-fail"])
        if code not in (0, 1):
            return code
        if code == 1:
            rc = 1
    if args.with_ticket:
        tcmd = [sys.executable, str(HERE / "ticket_diff_check.py"), *scope]
        if args.write_probes:
            tcmd.append("--write-probes")
        if args.proxy:
            tcmd += ["--proxy", args.proxy]
        if args.dry_run_ticket:
            tcmd.append("--dry-run")
        code = run(tcmd)
        if code not in (0, 1):
            return code
        if code == 1:
            rc = 1
    if args.with_seat:
        if args.host_dir:
            # seat needs dig-root or task root; use parent as dig-root if host-dir given
            dig = args.host_dir.parent
            scmd = [sys.executable, str(HERE / "seat_stall_check.py"), "--dig-root", str(dig), "--hours", str(args.seat_hours)]
        else:
            scmd = [sys.executable, str(HERE / "seat_stall_check.py"), "--dig-root", str(args.dig_root), "--hours", str(args.seat_hours)]
        if args.alerts_only:
            scmd.append("--alerts-only")
        code = run(scmd)
        if code not in (0, 1):
            return code
        if code == 1:
            rc = 1
    if rc:
        print("# P2_GATE FAIL — 禁止写 covered")
    else:
        print("# P2_GATE OK")
    return rc


if __name__ == "__main__":
    sys.exit(main())