#!/usr/bin/env python3
"""done_iter_scan.py — 扫桌面任务 DONE.md / DONE_anon.md / DONE_auth.md 里的拟进/拟补（只列清单，不改短表）

用法:
  python done_iter_scan.py
  python done_iter_scan.py --root "C:\\Users\\H\\Desktop"
  python done_iter_scan.py --only-real

退出码: 0=跑完  2=参数错误
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REAL_RE = re.compile(r"(拟进\s*[：:].*认|拟补\s*[：:].+)", re.IGNORECASE)
SKIP_RE = re.compile(
    r"无拟进|拟进\s*[：:]\s*无|拟进/拟补\s*[：:]\s*无|不进\s*[：:]|拟补\s*[：:]\s*无\s*$|拟进\s*[：:].*无报告|拟进\s*[：:].*无高危",
)

SKIP_DIR_NAMES = frozenset(
    {
        "js",
        "资产",
        "报告",
        "node_modules",
        ".git",
        "_trash",
        "tmp",
        "temp",
        "__pycache__",
    }
)
DONE_SCAN = frozenset({"DONE.md", "DONE_anon.md", "DONE_auth.md"})


def log(msg: str) -> None:
    print(msg, file=sys.stderr)


def is_real(line: str) -> bool:
    t = line.strip()
    if SKIP_RE.search(t):
        return False
    return bool(REAL_RE.search(t))


def walk_done(base: Path, max_depth: int = 4) -> list[Path]:
    """浅层走目录找 DONE.md / DONE_anon.md / DONE_auth.md，跳过 js/资产/报告 等重目录。"""
    out: list[Path] = []
    stack: list[tuple[Path, int]] = [(base, 0)]
    while stack:
        cur, depth = stack.pop()
        try:
            entries = list(cur.iterdir())
        except OSError:
            continue
        for ent in entries:
            name = ent.name
            if ent.is_file():
                if name in DONE_SCAN:
                    out.append(ent)
                continue
            if not ent.is_dir():
                continue
            if name in SKIP_DIR_NAMES or name.startswith("."):
                continue
            if depth >= max_depth:
                continue
            stack.append((ent, depth + 1))
    return out


def iter_done_files(root: Path, src_only: bool) -> list[Path]:
    if src_only:
        bases = sorted(root.glob("*_SRC挖洞"))
        if not bases:
            bases = [root]
    else:
        bases = [root]
    out: list[Path] = []
    seen: set[Path] = set()
    for base in bases:
        for done in walk_done(base):
            try:
                rp = done.resolve()
            except OSError:
                rp = done
            if rp in seen:
                continue
            seen.add(rp)
            out.append(done)
    return out


def scan(root: Path, only_real: bool, src_only: bool) -> list[tuple[Path, int, str]]:
    hits: list[tuple[Path, int, str]] = []
    for done in iter_done_files(root, src_only=src_only):
        try:
            text = done.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if "拟进" not in line and "拟补" not in line:
                continue
            if only_real and not is_real(line):
                continue
            if not only_real:
                if SKIP_RE.search(line.strip()) and "认" not in line:
                    continue
            hits.append((done, i, line.strip()))
    return hits


def main() -> None:
    ap = argparse.ArgumentParser(description="扫 DONE / DONE_anon / DONE_auth 拟进/拟补（不改短表）")
    ap.add_argument("--root", default=str(Path.home() / "Desktop"), help="扫描根目录")
    ap.add_argument("--only-real", action="store_true", help="只列含「认…」的拟进或非空拟补")
    ap.add_argument("--all", action="store_true", help="连「无拟进/不进」也列出")
    ap.add_argument("--whole-root", action="store_true", help="扫整个 --root（默认只扫 *_SRC挖洞）")
    args = ap.parse_args()
    root = Path(args.root)
    if not root.is_dir():
        log(f"[E] 不是目录: {root}")
        sys.exit(2)

    only_real = args.only_real or not args.all
    hits = scan(root, only_real=only_real, src_only=not args.whole_root)

    if not hits:
        print("0 条拟进/拟补候选")
        log("[+] 无待主控复核项（或已被过滤）")
        sys.exit(0)

    print(f"共 {len(hits)} 条（只列清单，不改短表；进不进认 hunt-iter）")
    print("---")
    for path, ln, text in hits:
        try:
            rel = path.relative_to(root)
        except ValueError:
            rel = path
        print(f"{rel}:{ln}")
        print(f"  {text}")
    sys.exit(0)


if __name__ == "__main__":
    main()
