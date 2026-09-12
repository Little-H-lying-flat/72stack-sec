#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""seat_stall_check.py — 空席/挂起告警（调度省心 · 只读）

主控回合自检：哪些 host 该派登录轨却没 DONE_auth、doing 挂太久、有 cookie 未验票探针等。
不派线程、不发 HTTP（可用 --with-mtime-hours 调阈值）。

用法:
  python seat_stall_check.py --dig-root DIR
  python seat_stall_check.py --root "D:\SRC挖洞\某_SRC挖洞"   # 自动找 *_dig 与 资产/种子队列.md
  python seat_stall_check.py --dig-root DIR --hours 24

退出码: 0=无告警  1=有 ALERT  2=参数错误
告警级别: ALERT（应立刻补席/收口） / WARN（建议处理）
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

SKIP = frozenset(
    {"js", "资产", "报告", "node_modules", ".git", "_trash", "tmp", "temp", "__pycache__", "_gate_batch"}
)


def age_hours(path: Path) -> float:
    try:
        return (time.time() - path.stat().st_mtime) / 3600.0
    except OSError:
        return 1e9


def find_dig_roots(root: Path) -> list[Path]:
    out: list[Path] = []
    for p in root.iterdir() if root.is_dir() else []:
        if p.is_dir() and (p.name.endswith("_dig") or p.name.endswith("dig")):
            out.append(p)
    # also direct dig-root
    if (root / "covered_hosts.txt").exists() or any(
        (d / "DONE_anon.md").exists() or (d / "session.cookie").exists()
        for d in root.iterdir() if d.is_dir()
    ):
        if root not in out and not root.name.endswith("_SRC挖洞"):
            out.append(root)
    return out


def parse_seed_doing(task_root: Path) -> list[str]:
    seeds = task_root / "资产" / "种子队列.md"
    if not seeds.is_file():
        return []
    doing: list[str] = []
    text = seeds.read_text(encoding="utf-8", errors="replace")
    # lines with doing
    for line in text.splitlines():
        if re.search(r"\bdoing\b|进行中", line, re.I):
            # grab host-like tokens
            for m in re.finditer(r"`?([a-z0-9.-]+\.[a-z]{2,})`?", line, re.I):
                doing.append(m.group(1).lower())
    return sorted(set(doing))


def check_host(host_dir: Path, hours: float) -> list[tuple[str, str]]:
    alerts: list[tuple[str, str]] = []
    cookie = host_dir / "session.cookie"
    auth = host_dir / "DONE_auth.md"
    anon = host_dir / "DONE_anon.md"
    legacy = host_dir / "DONE.md"
    suspects = host_dir / "suspects.md"
    probes = host_dir / "ticket_probes.txt"

    has_cookie = cookie.is_file() and cookie.stat().st_size > 20
    has_auth = auth.is_file()
    has_anon = anon.is_file() or legacy.is_file()

    if has_cookie and not has_auth:
        alerts.append(
            (
                "ALERT",
                "有 session.cookie 无 DONE_auth → 应立刻补登录轨席位（空席优先规则①）",
            )
        )
    if has_cookie and has_auth:
        # stale cookie vs auth doc
        if age_hours(cookie) > hours and age_hours(auth) > hours:
            alerts.append(
                (
                    "WARN",
                    "cookie 与 DONE_auth 均 >%.0fh 未更新 → 建议验票差分（ticket_diff --write-probes）"
                    % hours,
                )
            )
    if has_anon and not has_cookie:
        text = ""
        for n in ("DONE_anon.md", "DONE.md"):
            fp = host_dir / n
            if fp.is_file():
                text += fp.read_text(encoding="utf-8", errors="replace")
        if re.search(r"缺号\s*[：:]\s*干净", text) and not re.search(
            r"缺号\s*[：:]\s*(放弃|无HTTP口)", text
        ):
            alerts.append(
                (
                    "ALERT",
                    "DONE_anon 缺号=干净但无 cookie → 主控应跑 pending_from_done / auth_flow，禁止只派下一站",
                )
            )
    if has_auth:
        text = auth.read_text(encoding="utf-8", errors="replace")
        if not re.search(r"身份\s*=", text) or not re.search(r"半径\s*=", text):
            alerts.append(("ALERT", "DONE_auth 缺 身份= 或 半径= → 禁止 covered，补字段"))
        if has_cookie and not probes.is_file():
            # can auto extract?
            if re.search(r"(验票口|资质口)\s*=\s*(GET|POST)", text) or re.search(
                r"基线\s*(GET|POST)\s+`/", text
            ):
                alerts.append(
                    (
                        "WARN",
                        "有 DONE 验票线索但无 ticket_probes.txt → 跑 ticket_diff_check --write-probes",
                    )
                )
    if (has_anon or has_auth) and not suspects.is_file():
        # lean shell N/A in DONE?
        blob = ""
        for n in ("DONE_anon.md", "DONE_auth.md", "DONE.md"):
            fp = host_dir / n
            if fp.is_file():
                blob += fp.read_text(encoding="utf-8", errors="replace")
        if not re.search(r"N/A\s*瘦壳", blob):
            alerts.append(("WARN", "有 DONE 无 suspects.md → 覆盖闸会 FAIL"))
    return alerts


def main() -> int:
    ap = argparse.ArgumentParser(description="空席/挂起告警")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dig-root", type=Path)
    g.add_argument("--root", type=Path, help="任务根（含 资产/ 与 *_dig）")
    ap.add_argument("--hours", type=float, default=24.0)
    ap.add_argument("--alerts-only", action="store_true", help="只打印 ALERT（调度巡检安静模式）")
    args = ap.parse_args()

    digs: list[Path] = []
    task_root: Path | None = None
    if args.dig_root:
        digs = [args.dig_root]
        task_root = args.dig_root.parent if args.dig_root.parent else None
    else:
        task_root = args.root
        digs = find_dig_roots(args.root)
        if not digs:
            # treat root as dig-root
            digs = [args.root]

    doing = parse_seed_doing(task_root) if task_root else []
    n_alert = n_warn = 0

    if doing:
        print("# seed doing hosts: %s" % ", ".join(doing[:20]))

    for dig in digs:
        if not dig.is_dir():
            print("ERROR 非目录: %s" % dig, file=sys.stderr)
            return 2
        hosts = sorted(
            [
                d
                for d in dig.iterdir()
                if d.is_dir() and d.name not in SKIP and not d.name.startswith(".")
            ],
            key=lambda x: x.name.lower(),
        )
        for h in hosts:
            notes = check_host(h, args.hours)
            for level, msg in notes:
                if level == "ALERT":
                    n_alert += 1
                else:
                    n_warn += 1
                if args.alerts_only and level != "ALERT":
                    continue
                print("%s\t%s\t%s" % (level, h.name, msg))
            if doing and h.name.lower() in doing:
                # doing but no recent touch
                newest = 0.0
                for fn in ("DONE_auth.md", "DONE_anon.md", "DONE.md", "session.cookie", "endpoints.md"):
                    fp = h / fn
                    if fp.is_file():
                        newest = max(newest, fp.stat().st_mtime)
                if newest and (time.time() - newest) / 3600.0 > args.hours:
                    print(
                        "ALERT\t%s\t种子队列 doing 且文件 >%.0fh 未更新 → 挂起，应收口或补席"
                        % (h.name, args.hours)
                    )
                    n_alert += 1

    # summary seat hint
    print(
        "# summary ALERT=%d WARN=%d | 主控: ALERT 必须本回合 spawn/进号/收口，禁止纯文本停转"
        % (n_alert, n_warn)
    )
    return 1 if n_alert else 0


if __name__ == "__main__":
    sys.exit(main())
