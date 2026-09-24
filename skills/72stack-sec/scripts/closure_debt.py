#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""closure_debt.py — leftover done ≠ 收口。生成 编排/收口债.md

登录轨 / 过盾 waiting·offered·timeout / 升链 / 无盾干净口。不挡本种子翻页。
主控收单或派席前跑。线程禁止跑。

用法:
  python closure_debt.py --root "D:\SRC挖洞\某_SRC挖洞"
  python closure_debt.py --root "..." --dry-run
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SKIP = frozenset(
    {"js", "资产", "报告", "node_modules", ".git", "_trash", "tmp", "temp", "__pycache__"}
)
STATUSES_SHIELD = frozenset(
    {"waiting", "offered", "ready", "doing", "done", "skip", "no_account", "timeout", "fail_shield"}
)
ESC_STATUSES = frozenset({"pending", "doing", "done", "证伪", "人在环停"})


def log(msg: str) -> None:
    print(msg, file=sys.stderr)


def find_dig(root: Path) -> Path | None:
    for p in root.iterdir() if root.is_dir() else []:
        if p.is_dir() and (p.name.endswith("_dig") or p.name.endswith("dig")):
            return p
    return None


def parse_md_table(path: Path) -> list[list[str]]:
    if not path.is_file():
        return []
    rows: list[list[str]] = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        if re.match(r"\|[-: ]+\|", line) or re.search(r"\|\s*host", line, re.I):
            continue
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        if cols:
            rows.append(cols)
    return rows


def covered_set(root: Path) -> set[str]:
    out: set[str] = set()
    for name in ("covered_hosts.txt", "covered_hosts.md"):
        p = root / "资产" / name
        if not p.is_file():
            continue
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            host = line.split("#")[0].split()[0].strip().lower()
            if host:
                out.add(host)
    return out


def leftover_hosts(root: Path) -> dict[str, str]:
    """host -> leftover 状态（取最后一次出现）。"""
    out: dict[str, str] = {}
    folder = root / "编排"
    if not folder.is_dir():
        return out
    for p in folder.glob("leftover*.md"):
        for cols in parse_md_table(p):
            if len(cols) < 2:
                continue
            hp = cols[0]
            st = cols[1].strip().lower()
            host = hp.split(":")[0].strip().lower()
            if host and "." in host:
                out[host] = st
    return out


def shield_queue(root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    p = root / "资产" / "人工过盾续挖.md"
    for cols in parse_md_table(p):
        if len(cols) < 2:
            continue
        host = cols[0].strip().lower()
        # last col-ish: 状态 often col 8 (0-index 7)
        st = ""
        for c in reversed(cols):
            if c in STATUSES_SHIELD:
                st = c
                break
        if host and "." in host:
            out[host] = st or cols[-1]
    return out


def escalate_queue(root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    p = root / "编排" / "升链队列.md"
    for cols in parse_md_table(p):
        if len(cols) < 2:
            continue
        host = ""
        st = ""
        for c in cols:
            if not host and "." in c and " " not in c:
                host = c.strip().lower()
            if c in ESC_STATUSES or c in ("pending", "doing", "done"):
                st = c
        if host:
            out[host] = st or "pending"
    return out


def cookies_without_auth(dig: Path) -> list[str]:
    out: list[str] = []
    if not dig.is_dir():
        return out
    for d in dig.iterdir():
        if not d.is_dir() or d.name in SKIP:
            continue
        ck = d / "session.cookie"
        if ck.is_file() and ck.stat().st_size > 20 and not (d / "DONE_auth.md").is_file():
            out.append(d.name.lower())
    return sorted(out)


def main() -> None:
    ap = argparse.ArgumentParser(description="leftover done ≠ 收口 → 收口债.md")
    ap.add_argument("--root", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        log("[E] 不是目录: " + str(root))
        sys.exit(2)

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from pending_from_done import is_http_api, read_table, shield_blocks_auto  # type: ignore

    covered = covered_set(root)
    leftover = leftover_hosts(root)
    shield = shield_queue(root)
    esc = escalate_queue(root)
    dig = find_dig(root) or root
    login_debt = cookies_without_auth(dig)
    preg = read_table(root / "资产" / "pending_register.md")

    rows: list[tuple[str, str, str, str]] = []
    seen: set[str] = set()

    def add(host: str, kind: str, auto: str, note: str) -> None:
        h = host.lower()
        key = h + "|" + kind
        if key in seen:
            return
        seen.add(key)
        rows.append((h, kind, auto, note))

    for h in login_debt:
        add(h, "登录轨", "是", "有 cookie 无 DONE_auth")
    for h, st in shield.items():
        if st == "waiting":
            add(h, "过盾", "否", "人工过盾 waiting（login_gate 可要约）")
        elif st == "offered":
            add(h, "过盾要约", "否", "login_offer 进行中 · 不占 10 席")
        elif st == "timeout":
            add(h, "过盾超时", "否", "login timeout 冷却中")
        elif st == "ready":
            add(h, "登录轨", "是", "过盾 ready → auth_exec / _auth_spawn_batch")
        elif st == "fail_shield":
            add(h, "过盾", "否", "cookie 探活失败 fail_shield")
    for h, st in esc.items():
        if st in ("pending", "doing", ""):
            add(h, "升链", "是", f"升链队列 {st or 'pending'}")
        elif st == "人在环停":
            add(h, "升链", "否", "升链人在环停")
    waiting = {h for h, st in shield.items() if st in ("waiting", "offered", "timeout")}
    for host, rec in preg.items():
        st = rec.get("status") or ""
        if st != "pending":
            continue
        hl = host.lower()
        if hl in covered or hl in waiting or hl in login_debt:
            continue
        if is_http_api(rec.get("send") or "") or is_http_api(rec.get("submit") or ""):
            if shield_blocks_auto(rec.get("shield") or ""):
                continue
            add(host, "可进号", "是", "pending_register 无盾干净口")

    mp = root / "资产" / "miniprograms.md"
    if mp.is_file():
        for cols in parse_md_table(mp):
            if len(cols) < 5:
                continue
            aid = cols[0].strip().lower()
            st = cols[4].strip() if len(cols) > 4 else ""
            scope = cols[3].strip() if len(cols) > 3 else ""
            if st == "waiting_open" and scope == "是":
                add(aid, "小程序待打开", "否", "人在微信打开")
            elif st == "cached":
                add(aid, "小程序待解包", "是", "缓存已见，收单 CLI 解包")

    auto_n = sum(1 for r in rows if r[2] == "是")
    hang_n = len(rows) - auto_n
    leftover_done = sum(1 for st in leftover.values() if st == "done")

    lines = [
        "# 收口债",
        "",
        "> leftover `done` = 本轨交单，不是 covered。本表不挡翻页。",
        f"> leftover_done={leftover_done} covered={len(covered)} 可自动={auto_n} 人在环/挂起={hang_n}",
        "",
        "| host | 债 | 可自动 | 备注 |",
        "|------|----|--------|------|",
    ]
    for h, kind, auto, note in sorted(rows, key=lambda x: (0 if x[2] == "是" else 1, x[1], x[0])):
        lines.append(f"| {h} | {kind} | {auto} | {note} |")
    if not rows:
        lines.append("| （无） | 无 | | leftover done 无登录/过盾/升链挂账 |")

    text = "\n".join(lines) + "\n"
    outp = root / "编排" / "收口债.md"
    if args.dry_run:
        sys.stdout.write(text)
    else:
        outp.parent.mkdir(parents=True, exist_ok=True)
        outp.write_text(text, encoding="utf-8")
    log(f"[+] 收口债 可自动={auto_n} 挂起={hang_n} leftover_done={leftover_done} covered={len(covered)} -> {'dry-run' if args.dry_run else outp}")
    for h, kind, auto, note in rows:
        if auto == "是":
            print(f"AUTO\thost={h}\tkind={kind}\t{note}")


if __name__ == "__main__":
    main()
