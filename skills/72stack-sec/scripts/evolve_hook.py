#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""evolve_hook.py — 工作流焊点：收单/p2/covered 后跑 episode + propose

主控必跑；执行腿禁止。
不探测、不改 rules/短表/调度；默认 --auto-safe 只追加 semantic-blindspots.auto.md。
失败默认不挡 p2/covered（除非 --strict）。

用法:
  python evolve_hook.py --task-root "D:\\SRC挖洞\\某某_SRC挖洞"
  python evolve_hook.py --host-dir "{dig}\\{host}"
  python evolve_hook.py --dig-root "{dig}"
  python evolve_hook.py --host-dir DIR --strict

退出码: 0=完成（或无任务根可跳过）  1=strict 且子失败  2=参数错
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def resolve_task_root(start: Path) -> Path | None:
    p = start.resolve()
    candidates: list[Path] = [p, p.parent, p.parent.parent]
    for c in candidates:
        if not c.is_dir():
            continue
        if any(c.glob("*_dig")) or (c / "报告").is_dir() or (c / "资产").is_dir() or (c / "编排").is_dir():
            return c
    if p.parent.name.endswith("_dig"):
        return p.parent.parent
    if p.name.endswith("_dig"):
        return p.parent
    return None


def run(cmd: list[str]) -> int:
    print("+", " ".join(cmd), flush=True)
    return subprocess.run(cmd, cwd=str(HERE)).returncode


def main() -> int:
    ap = argparse.ArgumentParser(description="Workflow hook: episode + propose")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--task-root", type=Path)
    g.add_argument("--host-dir", type=Path)
    g.add_argument("--dig-root", type=Path)
    ap.add_argument("--host", type=str, default=None)
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--skip-propose", action="store_true")
    ap.add_argument(
        "--no-auto-safe",
        action="store_true",
        help="跳过 evolve_apply --auto-safe（默认跑）",
    )
    args = ap.parse_args()

    host_filter = args.host
    if args.task_root:
        task = args.task_root.resolve()
    elif args.host_dir:
        hd = args.host_dir.resolve()
        task = resolve_task_root(hd)
        host_filter = host_filter or hd.name
    else:
        task = resolve_task_root(args.dig_root.resolve())

    if task is None or not task.is_dir():
        print("# EVOLVE_HOOK SKIP — cannot resolve task-root (no 资产/报告/*_dig)")
        return 0

    print(f"# EVOLVE_HOOK task-root={task}")
    evo = task / "进化"
    evo.mkdir(parents=True, exist_ok=True)

    cmd1 = [sys.executable, str(HERE / "episode_from_done.py"), "--task-root", str(task)]
    if host_filter:
        cmd1 += ["--host", host_filter]
    rc1 = run(cmd1)

    rc2 = 0
    if not args.skip_propose:
        rc2 = run(
            [sys.executable, str(HERE / "evolve_propose.py"), "--task-root", str(task)]
        )

    prop_dir = evo / "proposals"
    pending = 0
    if prop_dir.is_dir():
        for jp in prop_dir.glob("prop_*.json"):
            try:
                if json.loads(jp.read_text(encoding="utf-8")).get("status") == "pending":
                    pending += 1
            except Exception:
                continue

    rc3 = 0
    if not args.no_auto_safe:
        rc3 = run(
            [
                sys.executable,
                str(HERE / "evolve_apply.py"),
                "--task-root",
                str(task),
                "--auto-safe",
            ]
        )
        pending = 0
        if prop_dir.is_dir():
            for jp in prop_dir.glob("prop_*.json"):
                try:
                    if json.loads(jp.read_text(encoding="utf-8")).get("status") == "pending":
                        pending += 1
                except Exception:
                    continue

    print(f"# EVOLVE_HOOK OK — pending_human={pending}  dir={prop_dir}")
    print(f'# 人审剩余: python evolve_apply.py --task-root "{task}" --list')
    print("# auto-safe → 知识库/semantic-blindspots.auto.md；auto 行 ≠ suspects 头已引用")
    print("# 不改 rules / SKILL / 短表 / 调度；hunt-iter 与 dispatch_bias 仍人审")

    if args.strict and (rc1 != 0 or rc2 != 0 or rc3 != 0):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
