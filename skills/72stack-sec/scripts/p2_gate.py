#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""p2_gate.py — P2 一键闸

默认不发 HTTP：DONE 字段 + suspects 覆盖 + 盲区头严格闸 + 写面粗检
+ 假阴性专闸 + 缺号行校验 + 凭证面话术闸 + 闸红续转(NEXT)闸 + 过盾 ready 续挖 + 差分指回 + JS进清单 + RCE执行信号 + SQLi业务差分。
加 --with-ticket 才验票；--with-seat 才空席巡检。

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
    return subprocess.run(cmd, cwd=str(HERE)).returncode


def main() -> int:
    ap = argparse.ArgumentParser(description="P2 一键闸")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--host-dir", type=Path)
    g.add_argument("--dig-root", type=Path)
    ap.add_argument("--with-ticket", action="store_true")
    ap.add_argument("--write-probes", action="store_true")
    ap.add_argument("--proxy", default=None)
    ap.add_argument("--dry-run-ticket", action="store_true")
    ap.add_argument("--with-seat", action="store_true")
    ap.add_argument("--alerts-only", action="store_true")
    ap.add_argument("--seat-hours", type=float, default=24.0)
    ap.add_argument("--strict-write", action="store_true")
    ap.add_argument(
        "--no-evolve",
        action="store_true",
        help="跳过收单进化环（默认跑 evolve_hook，不挡闸）",
    )
    ap.add_argument(
        "--evolve-strict",
        action="store_true",
        help="进化子脚本非0时本闸也 FAIL（默认进化失败不挡 covered）",
    )
    args = ap.parse_args()

    scope = (
        ["--host-dir", str(args.host_dir)]
        if args.host_dir
        else ["--dig-root", str(args.dig_root)]
    )
    rc = 0

    checks = [
        ("done_fields_check.py", ["--only-fail"]),
        ("suspects_coverage_check.py", ["--only-fail"]),
        ("blindspot_remind.py", ["--strict-suspects-header"]),
        ("write_surface_check.py", ["--only-fail"] + (["--strict"] if args.strict_write else [])),
        ("auth_false_negative_check.py", ["--only-fail"]),
        ("que_line_check.py", ["--only-fail"]),
        ("cred_surface_check.py", ["--only-fail"]),
        ("next_after_fail_check.py", ["--only-fail"]),
        ("diff_ref_check.py", ["--only-fail"]),
        ("ready_resume_check.py", ["--only-fail"]),
        ("js_inventory_check.py", ["--only-fail"]),
        ("rce_exec_signal_check.py", ["--only-fail"]),
        ("sqli_diff_signal_check.py", ["--only-fail"]),
    ]
    for script, extra in checks:
        code = run([sys.executable, str(HERE / script), *scope, *extra])
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
        dig = args.host_dir.parent if args.host_dir else args.dig_root
        scmd = [
            sys.executable,
            str(HERE / "seat_stall_check.py"),
            "--dig-root",
            str(dig),
            "--hours",
            str(args.seat_hours),
        ]
        if args.alerts_only:
            scmd.append("--alerts-only")
        code = run(scmd)
        if code not in (0, 1):
            return code
        if code == 1:
            rc = 1

    # 发现进化环：默认挂上，不挡闸（除非 --evolve-strict）
    if not args.no_evolve:
        ecmd = [sys.executable, str(HERE / "evolve_hook.py"), *scope]
        if args.evolve_strict:
            ecmd.append("--strict")
        code = run(ecmd)
        if args.evolve_strict and code not in (0,):
            rc = 1 if code == 1 else code
            if code not in (0, 1):
                return code

    print(
        "# P2_GATE FAIL — 禁本站 covered；必须给出 NEXT（补席|下种子|人工过盾），不是整场停"
        if rc
        else "# P2_GATE OK"
    )
    return rc


if __name__ == "__main__":
    sys.exit(main())
