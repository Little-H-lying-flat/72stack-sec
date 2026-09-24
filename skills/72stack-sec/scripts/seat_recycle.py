#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""seat_recycle.py — leftover doing 僵尸超时回收

只认 leftover **表行** + seats.md，不信抬头。
进度信号：dig/{host} / js/{host} / 会话 jsonl(sid) 的最新 mtime。
无落盘则用 编排/doing_heartbeat.json 首次看见时间。
有 dig/js/jsonl 落盘后冻结：默认 45 分钟无新 mtime → 僵尸。
从未落盘（只有 heartbeat）：默认 25 分钟 → 僵尸。

默认只打印 STALL/LIVE。--recycle 才改 leftover doing→pending、seats 清成 idle。
不杀会话进程。占席只认 seats.md；回收后允许同 host 再派。

用法:
  python seat_recycle.py --root "D:\SRC挖洞\某_SRC挖洞"
  python seat_recycle.py --root "..." --minutes 45 --recycle
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

SKIP = frozenset(
    {"js", "资产", "报告", "node_modules", ".git", "_trash", "tmp", "temp", "__pycache__"}
)
DEFAULT_MIN = 45.0  # jsonl/dig/js 冻结
HEARTBEAT_MIN = 25.0  # 从未落盘


def log(msg: str) -> None:
    print(msg, file=sys.stderr)


def find_dig(root: Path) -> Path | None:
    for p in root.iterdir() if root.is_dir() else []:
        if p.is_dir() and (p.name.endswith("_dig") or p.name.endswith("dig")):
            return p
    return None


def leftover_doing(root: Path) -> list[tuple[Path, str, str]]:
    """[(leftover_file, host, raw_line)] status col == doing."""
    out: list[tuple[Path, str, str]] = []
    folder = root / "编排"
    if not folder.is_dir():
        return out
    for p in sorted(folder.glob("leftover*.md")):
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line in text.splitlines():
            if not line.startswith("|"):
                continue
            if re.match(r"\|[-: ]+\|", line) or re.search(r"\|\s*host", line, re.I):
                continue
            cols = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cols) < 2:
                continue
            if cols[1].strip().lower() != "doing":
                continue
            host = cols[0].split(":")[0].strip().lower()
            if host and "." in host:
                out.append((p, host, line))
    return out


def parse_seats(path: Path) -> list[dict]:
    rows: list[dict] = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("|"):
            continue
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cols) < 5 or cols[0] in ("席", "----"):
            continue
        if not re.match(r"^\d+$", cols[0]):
            continue
        rows.append(
            {
                "n": cols[0],
                "host": cols[1].strip().lower().strip("—-"),
                "track": cols[2],
                "status": cols[3].strip().lower(),
                "sid": cols[4].strip(),
                "note": cols[5] if len(cols) > 5 else "",
                "line": line,
            }
        )
    return rows


def newest_under(path: Path, max_files: int = 400) -> float:
    newest = 0.0
    if not path.exists():
        return 0.0
    n = 0
    stack = [path]
    while stack and n < max_files:
        cur = stack.pop()
        try:
            if cur.is_file():
                newest = max(newest, cur.stat().st_mtime)
                n += 1
                continue
            if not cur.is_dir() or cur.name in SKIP:
                continue
            for ent in cur.iterdir():
                stack.append(ent)
        except OSError:
            continue
    return newest


def find_jsonl(sid: str) -> Path | None:
    if not sid or len(sid) < 8:
        return None
    roots: list[Path] = []
    env = os.environ.get("PI_CODING_AGENT_DIR")
    if env:
        roots.append(Path(env) / "sessions")
    roots.append(Path(r"D:/SRC工作区/pi-dig/agent/sessions"))
    seen: set[Path] = set()
    for r in roots:
        r = r.resolve() if r.exists() else r
        if r in seen or not r.is_dir():
            continue
        seen.add(r)
        for p in r.rglob(f"*{sid}*.jsonl"):
            return p
    return None


def load_hb(path: Path) -> dict[str, float]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    out: dict[str, float] = {}
    if isinstance(data, dict):
        for k, v in data.items():
            try:
                out[str(k).lower()] = float(v)
            except (TypeError, ValueError):
                continue
    return out


def save_hb(path: Path, data: dict[str, float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def recycle_leftover_line(path: Path, host: str) -> bool:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    changed = False
    out: list[str] = []
    host_l = host.lower()
    for line in lines:
        if not line.startswith("|"):
            out.append(line)
            continue
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cols) >= 2 and cols[0].split(":")[0].strip().lower() == host_l and cols[1].lower() == "doing":
            cols[1] = "pending"
            note = cols[2] if len(cols) > 2 else ""
            if "stall-recycle" not in note:
                cols[2] = (note + " stall-recycle").strip() if note else "stall-recycle"
            while len(cols) < 3:
                cols.append("")
            line = "| " + " | ".join(cols) + " |"
            changed = True
        out.append(line)
    if changed:
        path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return changed


def recycle_seats(path: Path, host: str) -> bool:
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    changed = False
    out: list[str] = []
    host_l = host.lower()
    for line in lines:
        if not line.startswith("|"):
            out.append(line)
            continue
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        if (
            len(cols) >= 5
            and re.match(r"^\d+$", cols[0])
            and cols[1].strip().lower() == host_l
            and cols[3].strip().lower() == "doing"
        ):
            n = cols[0]
            line = f"| {n} | (空) | 未登录 | idle |  | stall-recycle {host_l} |"
            changed = True
        out.append(line)
    if changed:
        path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return changed


def main() -> int:
    ap = argparse.ArgumentParser(description="leftover doing 僵尸超时回收")
    ap.add_argument("--root", required=True)
    ap.add_argument("--minutes", type=float, default=DEFAULT_MIN, help="有 jsonl/dig/js 之后冻结多久算僵尸（默认 45）")
    ap.add_argument("--heartbeat-minutes", type=float, default=HEARTBEAT_MIN, help="从未落盘（仅 heartbeat）多久算僵尸（默认 25）")
    ap.add_argument("--recycle", action="store_true", help="写 leftover/seats；默认只打印")
    args = ap.parse_args()
    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        log("[E] 不是目录: " + str(root))
        return 2

    doing_rows = leftover_doing(root)
    seats_path = root / "编排" / "seats.md"
    seats = parse_seats(seats_path)
    sid_by_host = {
        r["host"]: r["sid"]
        for r in seats
        if r["status"] == "doing" and r["host"] and r["host"] not in ("(空)", "空")
    }
    dig = find_dig(root)
    hb_path = root / "编排" / "doing_heartbeat.json"
    hb = load_hb(hb_path)
    now = time.time()
    thresh_progress = args.minutes * 60.0
    thresh_hb = args.heartbeat_minutes * 60.0

    live_hosts = {h for _, h, _ in doing_rows}
    hb = {k: v for k, v in hb.items() if k in live_hosts}
    stalls: list[tuple[str, float, str]] = []

    for _fp, host, _line in doing_rows:
        if host not in hb:
            hb[host] = now
        newest = 0.0
        src = "heartbeat"
        if dig:
            newest = max(newest, newest_under(dig / host))
            if newest:
                src = "dig"
        newest = max(newest, newest_under(root / "js" / host))
        if newest and src == "heartbeat":
            src = "js"
        sid = sid_by_host.get(host, "")
        jsonl = find_jsonl(sid) if sid else None
        if jsonl and jsonl.is_file():
            mt = jsonl.stat().st_mtime
            if mt >= newest:
                newest = mt
                src = "jsonl"
        first = hb[host]
        if newest:
            progress_from = newest
            stalled = (now - progress_from) >= thresh_progress
        else:
            progress_from = first
            src = "heartbeat"
            stalled = (now - progress_from) >= thresh_hb
        age_min = (now - progress_from) / 60.0
        if stalled:
            stalls.append((host, age_min, src))
            print(f"STALL\thost={host}\tage_min={age_min:.1f}\tsignal={src}\tsid={sid or '无'}")
        else:
            print(f"LIVE\thost={host}\tage_min={age_min:.1f}\tsignal={src or 'none'}\tsid={sid or '无'}")

    if args.recycle:
        save_hb(hb_path, hb)
        n = 0
        for host, age_min, src in stalls:
            touched = False
            for fp, h, _ in doing_rows:
                if h == host:
                    touched = recycle_leftover_line(fp, host) or touched
            touched = recycle_seats(seats_path, host) or touched
            if touched:
                n += 1
                print(f"RECYCLE\thost={host}\tage_min={age_min:.1f}\tsignal={src}")
        logp = root / "编排" / "stall_recycle.log"
        if n:
            with logp.open("a", encoding="utf-8") as f:
                f.write(time.strftime("%Y-%m-%dT%H:%M:%S") + f" recycled={n} minutes={args.minutes}\n")
                for host, age_min, src in stalls:
                    f.write(f"  {host} age_min={age_min:.1f} {src}\n")
        log(f"[+] STALL={len(stalls)} recycled={n} minutes={args.minutes}")
    else:
        save_hb(hb_path, hb)
        log(f"[+] STALL={len(stalls)} LIVE={len(doing_rows)-len(stalls)} minutes={args.minutes}（加 --recycle 才改表）")

    return 1 if stalls else 0


if __name__ == "__main__":
    sys.exit(main())
