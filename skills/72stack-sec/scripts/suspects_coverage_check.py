#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""suspects_coverage_check.py — 硬闸覆盖率粗检（不定级、不探测）。"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

def has_field_assign(text: str, key: str) -> bool:
    pat = re.compile(re.escape(key) + r"\s*=")
    for m in pat.finditer(text):
        start = m.start()
        prefix = text[max(0, start - 4):start]
        if re.search(r"(缺|未|无|非|禁)", prefix):
            continue
        line_start = text.rfind("\n", 0, start) + 1
        line_end = text.find("\n", start)
        line = text[line_start: line_end if line_end != -1 else len(text)]
        if re.search(r"(缺|未写|未填|没有).{0,6}" + re.escape(key), line):
            continue
        return True
    return False


REQUIRED_HINTS = [
    (r"威胁模型", "缺威胁模型头"),
    (r"覆盖率自检|硬闸", "缺覆盖率自检表"),
    (r"凭证作用域|半径\s*[（(]|信任边界", "缺信任边界（凭证作用域/半径）"),
    (r"S-\d+|suspects:\s*N/A", "无 S-xx 行且未声明 N/A"),
]
DONE_NAMES = ("DONE_anon.md", "DONE.md", "DONE_auth.md")
AUTH_DONE = ("DONE_auth.md",)


def check_host(host_dir: Path) -> tuple[str, list[str]]:
    suspects = host_dir / "suspects.md"
    notes: list[str] = []
    if not suspects.is_file():
        return "FAIL", ["无 suspects.md"]
    text = suspects.read_text(encoding="utf-8", errors="replace")
    if re.search(r"suspects:\s*N/A\s*瘦壳|N/A\s*瘦壳", text, re.I):
        return "N/A_LEAN", ["显式瘦壳 N/A"]
    for pat, msg in REQUIRED_HINTS:
        if not re.search(pat, text, re.I):
            notes.append(msg)
    if re.search(r"覆盖率自检", text):
        unchecked = len(re.findall(r"\|\s*☐\s*\|", text))
        if unchecked >= 3:
            notes.append("覆盖率表未勾项偏多(☐×%d)" % unchecked)
        # 信任边界行若存在且仍 ☐，点名（P1）
        if re.search(r"信任边界[^\n]*☐", text):
            notes.append("信任边界未勾（禁止 covered）")
        if re.search(r"写面探针", text) and re.search(r"写面探针[^\n]*☐", text):
            notes.append("写面探针未勾（禁止只扫读轨 covered）")
        elif not re.search(r"写面探针|写面\s*=\s*N/A", text, re.I):
            notes.append("缺写面探针勾选或写面=N/A（建议补）")
    done_hit = False
    for name in DONE_NAMES:
        fp = host_dir / name
        if fp.is_file() and re.search(
            r"suspects\s*=", fp.read_text(encoding="utf-8", errors="replace"), re.I
        ):
            done_hit = True
            break
    if not done_hit:
        notes.append("DONE* 未写 suspects= 字段（建议补）")
    # P1: 有 DONE_auth 则强制 身份= 与 半径=
    for name in AUTH_DONE:
        fp = host_dir / name
        if not fp.is_file():
            continue
        auth = fp.read_text(encoding="utf-8", errors="replace")
        if not has_field_assign(auth, "身份"):
            notes.append("DONE_auth 缺 身份=（禁止 covered）")
        if not has_field_assign(auth, "半径"):
            notes.append("DONE_auth 缺 半径=（禁止 covered）")
        if re.search(r"身份\s*=\s*(空户|待确认)", auth) and re.search(
            r"(POST|PUT|PATCH|DELETE)\s+/", auth
        ):
            if not re.search(r"空身份禁写", auth):
                notes.append("空户/待确认却有写面结论且未标「空身份禁写」（禁止 covered）")
    if notes:
        return "FAIL", notes
    return "PASS", ["ok"]


def iter_hosts(dig_root: Path) -> list[Path]:
    return sorted(
        [
            d
            for d in dig_root.iterdir()
            if d.is_dir() and not d.name.startswith((".", "_"))
        ],
        key=lambda d: d.name.lower(),
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="suspects 硬闸覆盖率粗检")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--host-dir", type=Path)
    g.add_argument("--dig-root", type=Path)
    ap.add_argument("--only-fail", action="store_true")
    args = ap.parse_args()
    if args.host_dir:
        hosts = [args.host_dir]
    else:
        if not args.dig_root.is_dir():
            print("ERROR dig-root 不存在: %s" % args.dig_root, file=sys.stderr)
            return 2
        hosts = iter_hosts(args.dig_root)
    fail = 0
    for h in hosts:
        if not h.is_dir():
            print("ERROR 非目录: %s" % h, file=sys.stderr)
            return 2
        status, notes = check_host(h)
        if status == "FAIL":
            fail += 1
        if args.only_fail and status != "FAIL":
            continue
        print("%s\t%s\t%s" % (status, h.name, "; ".join(notes)))
    if fail:
        print("# FAIL hosts=%d/%d — 禁止写 covered，先补 suspects.md" % (fail, len(hosts)))
        return 1
    print("# OK hosts=%d" % len(hosts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
