#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""mp_extract_urls.py — 从小程序解包目录抽 URL/host（给主控进 leftover）

不改 leftover。锁面判定由主控做。
用法:
  python mp_extract_urls.py --dir "D:\SRC挖洞\某_SRC挖洞\js\wx123...\anon"
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

URL_RE = re.compile(r"https?://[^\s\"'`<>\\]+", re.I)
HOST_RE = re.compile(
    r"(?:https?://)?((?:[a-z0-9-]+\.)+[a-z]{2,})(?::\d+)?",
    re.I,
)
SKIP = frozenset({"node_modules", ".git", "__pycache__"})


def log(msg: str) -> None:
    print(msg, file=sys.stderr)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    args = ap.parse_args()
    root = Path(args.dir).expanduser().resolve()
    if not root.is_dir():
        log("[E] 不是目录")
        sys.exit(2)

    hosts: dict[str, str] = {}
    n_url = 0
    for p in root.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in {".js", ".json", ".html", ".wxml"}:
            continue
        if any(x in SKIP for x in p.parts):
            continue
        try:
            if p.stat().st_size > 6_000_000:
                continue
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for m in URL_RE.finditer(text):
            n_url += 1
            u = m.group(0).rstrip(").,;]'\"")
            try:
                host = (urlparse(u).hostname or "").lower()
            except Exception:
                continue
            if host and host not in hosts:
                hosts[host] = u[:180]
        if "wx.request" in text or "wx.request(" in text:
            for hm in HOST_RE.finditer(text):
                host = hm.group(1).lower()
                if host not in hosts and "." in host:
                    hosts[host] = "wx.request-context"

    for h in sorted(hosts):
        print(f"HOST\t{h}\t{hosts[h]}")
    log(f"[+] urls≈{n_url} hosts={len(hosts)} dir={root}")


if __name__ == "__main__":
    main()
