#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mark_covered.py — covered 焊闸（薄）

跑同目录 p2_gate.py --host-dir；PASS 才 upsert 资产/covered_hosts.txt 一行。
FAIL → 原样打印闸 stdout/stderr，退出 1，不写盘。

用法:
  python mark_covered.py --host-dir "{dig}\\{host}" --reason "瘦壳；p2_gate OK"
  python mark_covered.py --dig-root "{dig}" --host example.com --reason "同闸一眼"

退出码: 0=已写/已更新  1=闸 FAIL 或写失败  2=参数错
"""
from __future__ import annotations

import argparse
import datetime as _dt
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
P2_GATE = HERE / "p2_gate.py"

HEADER = (
    "# covered_hosts · 已过 §4.3 收口才写（肥面须两轨收口或登录轨 N/A）\n"
    "# 格式：host  #  原因（瘦壳/同闸一眼/无干净口+未登录收口 / 两轨完成）\n"
)

HOST_LINE_RE = re.compile(r"^([^\s#]+)\s+#")


def resolve_task_root(host_dir: Path) -> Path:
    dig = host_dir.parent
    parent = dig.parent
    if (parent / "资产").is_dir() or (parent / "编排").is_dir():
        return parent
    if (dig / "资产").is_dir() or (dig / "编排").is_dir():
        return dig
    return parent if (parent / "资产").is_dir() else dig


def find_covered_path(task_root: Path) -> Path:
    assets = task_root / "资产"
    preferred = assets / "covered_hosts.txt"
    if preferred.is_file() or assets.is_dir():
        return preferred
    legacy = task_root / "covered_hosts.txt"
    if legacy.is_file():
        return legacy
    # last resort: create under 资产 if parent looks like a dig task
    if assets.is_dir() or (task_root / "编排").is_dir():
        assets.mkdir(parents=True, exist_ok=True)
        return preferred
    return preferred


def run_p2_gate(host_dir: Path) -> tuple[int, str]:
    if not P2_GATE.is_file():
        return 2, f"# MARK_COVERED ERR — missing {P2_GATE}\n"
    cmd = [sys.executable, str(P2_GATE), "--host-dir", str(host_dir)]
    print("+", " ".join(cmd), flush=True)
    proc = subprocess.run(
        cmd,
        cwd=str(HERE),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    out = ""
    if proc.stdout:
        out += proc.stdout
        if not proc.stdout.endswith("\n"):
            out += "\n"
    if proc.stderr:
        out += proc.stderr
        if not proc.stderr.endswith("\n"):
            out += "\n"
    return proc.returncode, out


def format_line(host: str, reason: str, day: str) -> str:
    reason = reason.strip().rstrip("。.")
    # keep trailing date like existing samples (YYYY-MM-DD)
    if not re.search(r"\d{4}-\d{2}-\d{2}\s*$", reason):
        reason = f"{reason}。{day}"
    else:
        # normalize: ensure Chinese period before date if missing
        if not reason.rstrip().endswith(day):
            reason = f"{reason.rstrip('。.')}。{day}"
    return f"{host}  # {reason}"


def upsert_line(path: Path, host: str, new_line: str, dry_run: bool) -> str:
    text = ""
    if path.is_file():
        text = path.read_text(encoding="utf-8", errors="replace")
    else:
        text = HEADER

    lines = text.splitlines(keepends=True)
    if not lines:
        lines = [HEADER]

    host_l = host.lower()
    replaced = False
    out_lines: list[str] = []
    for ln in lines:
        raw = ln.rstrip("\r\n")
        m = HOST_LINE_RE.match(raw)
        if m and m.group(1).lower() == host_l:
            out_lines.append(new_line + "\n")
            replaced = True
        else:
            # preserve original newline style loosely
            out_lines.append(ln if ln.endswith("\n") else ln + "\n")

    if not replaced:
        if out_lines and not out_lines[-1].endswith("\n"):
            out_lines[-1] += "\n"
        out_lines.append(new_line + "\n")

    new_text = "".join(out_lines)
    action = "UPDATE" if replaced else "APPEND"
    if dry_run:
        return f"# MARK_COVERED DRY-RUN {action} → {path}\n{new_line}\n"

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(new_text, encoding="utf-8", newline="\n")
    return f"# MARK_COVERED OK {action} → {path}\n{new_line}\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="covered 焊闸：p2_gate PASS 才写 covered_hosts")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--host-dir", type=Path)
    g.add_argument("--dig-root", type=Path)
    ap.add_argument("--host", default=None, help="with --dig-root: host folder name")
    ap.add_argument("--reason", required=True, help="covered 行原因（瘦壳/同闸一眼/两轨…）")
    ap.add_argument("--date", default=None, help="YYYY-MM-DD；默认今天（本地）")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.host_dir:
        host_dir = args.host_dir.resolve()
        host = args.host or host_dir.name
    else:
        if not args.host:
            ap.error("--dig-root requires --host")
        host_dir = (args.dig_root / args.host).resolve()
        host = args.host

    if not host_dir.is_dir():
        print(f"# MARK_COVERED DENY — 无 host 目录，禁 covered: {host_dir}", flush=True)
        return 1

    day = args.date or _dt.date.today().isoformat()
    rc, gate_out = run_p2_gate(host_dir)
    # always echo gate output so FAIL reason is visible
    if gate_out:
        sys.stdout.write(gate_out)
        if not gate_out.endswith("\n"):
            sys.stdout.write("\n")

    if rc != 0:
        # 蚂蚁口径：deny reason 优先塞带 FAIL\t 的行；末行兜底
        fail_tab = [ln for ln in (gate_out or "").splitlines() if "FAIL\t" in ln]
        if fail_tab:
            print("# MARK_COVERED DENY — FAIL 行摘录：", flush=True)
            for ln in fail_tab:
                print(ln, flush=True)
        print(
            "# MARK_COVERED DENY — p2_gate FAIL；禁本站 covered；未写入 covered_hosts.txt",
            flush=True,
        )
        return 1 if rc == 1 else rc

    task_root = resolve_task_root(host_dir)
    covered = find_covered_path(task_root)
    line = format_line(host, args.reason, day)
    msg = upsert_line(covered, host, line, dry_run=args.dry_run)
    sys.stdout.write(msg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
