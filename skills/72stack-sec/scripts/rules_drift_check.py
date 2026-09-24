#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""rules_drift_check.py — ~/.grok/rules 与 D:\dsh-72stack-sec\rules 必须同文

立法两份拷贝会各改各的。本脚本只报警，不覆盖。
exit 0=一致  1=漂移  2=缺目录
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

DSH = Path(r"D:\dsh-72stack-sec\rules")
GROK = Path.home() / ".grok" / "rules"


def md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def main() -> None:
    if not DSH.is_dir() or not GROK.is_dir():
        print(f"[E] 缺目录 dsh={DSH.is_dir()} grok={GROK.is_dir()}", file=sys.stderr)
        sys.exit(2)
    names = sorted({p.name for p in list(DSH.glob("*.md")) + list(GROK.glob("*.md"))})
    drift = 0
    for n in names:
        a, b = DSH / n, GROK / n
        if not a.is_file() or not b.is_file():
            print(f"MISS\t{n}\tdsh={a.is_file()}\tgrok={b.is_file()}")
            drift += 1
            continue
        if md5(a) != md5(b):
            print(f"DRIFT\t{n}\tdsh={a}\tgrok={b}")
            drift += 1
        else:
            print(f"OK\t{n}")
    print(f"[+] files={len(names)} drift={drift}", file=sys.stderr)
    sys.exit(1 if drift else 0)


if __name__ == "__main__":
    main()
