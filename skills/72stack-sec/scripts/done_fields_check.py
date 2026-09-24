#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""done_fields_check.py — DONE_anon / DONE_auth 必填字段闸（不定级、不探测）

对照线程必读「DONE 最低字段」+ P1 身份/半径硬字段。

用法:
  python done_fields_check.py --host-dir DIR
  python done_fields_check.py --dig-root DIR
  python done_fields_check.py --dig-root DIR --only-fail

退出码: 0=全过  1=有 FAIL  2=参数错误
线程可跑（只读检查）。主控写 covered 前建议跑。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

def has_field_assign(text: str, key: str) -> bool:
    """真赋值：身份=有店铺；排除「缺身份=」「未写身份=」「无 身份=」等否定句。"""
    for m in re.finditer(rf"{{0}}\s*=".format(re.escape(key)), text):
        start = m.start()
        prefix = text[max(0, start - 4):start]
        if re.search(r"(缺|未|无|非|禁)", prefix):
            continue
        # also deny if line says 缺/未写 before key
        line_start = text.rfind("\n", 0, start) + 1
        line = text[line_start:text.find("\n", start)]
        if re.search(rf"(缺|未写|未填|没有).{{0,6}}{re.escape(key)}", line):
            continue
        return True
    return False


SKIP_DIR = frozenset(
    {"js", "资产", "报告", "node_modules", ".git", "_trash", "tmp", "temp", "__pycache__"}
)


def check_anon(text: str) -> list[str]:
    notes: list[str] = []
    if not re.search(r"缺号\s*[：:]", text):
        notes.append("缺 缺号行")
    if not re.search(r"带出host\s*=", text, re.I):
        notes.append("缺 带出host=（禁止 covered）")
    if not re.search(r"suspects\s*=", text, re.I):
        notes.append("缺 suspects=（建议补）")
    if not re.search(r"卡住对照\s*=", text):
        notes.append("缺 卡住对照=（建议补；瘦壳写 N/A瘦壳）")
    # soft hints
    if not re.search(r"§?\s*4\.0|业务|对象", text):
        notes.append("建议补 §4.0/业务对象简述")
    return notes


def check_auth(text: str) -> list[str]:
    notes: list[str] = []
    if not has_field_assign(text, "身份"):
        notes.append("缺 身份=（禁止 covered）")
    if not has_field_assign(text, "半径"):
        notes.append("缺 半径=（禁止 covered）")
    if not re.search(r"带出host\s*=", text, re.I):
        notes.append("缺 带出host=（禁止 covered）")
    if not re.search(r"资质口\s*=", text):
        notes.append("缺 资质口=（建议补）")
    if not re.search(r"suspects\s*=", text, re.I):
        notes.append("缺 suspects=（建议补）")
    # radius unknown + empty house warning
    if re.search(r"半径\s*=\s*未知", text) and re.search(
        r"身份\s*=\s*(空户|待确认)", text
    ):
        if re.search(r"换\s*id|对象图", text) and not re.search(
            r"资质|开通", text
        ):
            notes.append("半径未知且空户时主业应是资质/开通，勿暗示已换 id")
    return notes


def check_host(host_dir: Path) -> tuple[str, list[str]]:
    notes: list[str] = []
    anon = host_dir / "DONE_anon.md"
    auth = host_dir / "DONE_auth.md"
    legacy = host_dir / "DONE.md"
    if not anon.is_file() and not auth.is_file() and not legacy.is_file():
        return "SKIP", ["无 DONE*"]
    if anon.is_file():
        notes.extend("anon:" + n for n in check_anon(anon.read_text(encoding="utf-8", errors="replace")))
    if auth.is_file():
        notes.extend("auth:" + n for n in check_auth(auth.read_text(encoding="utf-8", errors="replace")))
    if legacy.is_file() and not anon.is_file():
        text = legacy.read_text(encoding="utf-8", errors="replace")
        if re.search(r"缺号\s*[：:]", text):
            notes.extend("legacy:" + n for n in check_anon(text))
        if has_field_assign(text, "身份") or re.search(r"有会话|本轨\s*=\s*有会话", text):
            notes.extend("legacy:" + n for n in check_auth(text))
    hard = [n for n in notes if "禁止 covered" in n or n.endswith("缺 缺号行")]
    # treat missing 缺号 on anon as hard if DONE_anon exists
    soft_only = notes and not hard and not any(
        n.startswith("anon:缺 缺号行") or n.startswith("anon:缺 带出host") or n.startswith("auth:缺 身份") or n.startswith("auth:缺 半径") or n.startswith("auth:缺 带出host")
        for n in notes
    )
    if any(
        n.startswith("anon:缺 缺号行")
        or n.startswith("anon:缺 带出host")
        or n.startswith("auth:缺 身份")
        or n.startswith("auth:缺 半径")
        or n.startswith("auth:缺 带出host")
        for n in notes
    ):
        return "FAIL", notes
    if notes:
        return "WARN", notes
    return "PASS", ["ok"]


def iter_hosts(dig_root: Path) -> list[Path]:
    return sorted(
        [
            d
            for d in dig_root.iterdir()
            if d.is_dir() and d.name not in SKIP_DIR and not d.name.startswith(".")
        ],
        key=lambda d: d.name.lower(),
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="DONE 必填字段闸")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--host-dir", type=Path)
    g.add_argument("--dig-root", type=Path)
    ap.add_argument("--only-fail", action="store_true")
    args = ap.parse_args()
    hosts = [args.host_dir] if args.host_dir else iter_hosts(args.dig_root)
    fail = warn = 0
    for h in hosts:
        if not h.is_dir():
            print("ERROR 非目录: %s" % h, file=sys.stderr)
            return 2
        status, notes = check_host(h)
        if status == "FAIL":
            fail += 1
        elif status == "WARN":
            warn += 1
        if args.only_fail and status != "FAIL":
            continue
        if status == "SKIP":
            continue
        print("%s\t%s\t%s" % (status, h.name, "; ".join(notes)))
    if fail:
        print("# FAIL hosts=%d WARN=%d — 禁止写 covered，先补 DONE 字段" % (fail, warn))
        return 1
    print("# OK fail=0 warn=%d hosts=%d" % (warn, len(hosts)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
