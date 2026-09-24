#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""auth_false_negative_check.py — 干净登录口假阴性专闸（不定级、不探测）

规则：
  endpoints* 出现无盾干净登录/注册口（POST …/auth/login|register，path 不含 captcha）
  且 DONE_anon/DONE 出现「没号不开 / 无测试号跳过登录 / 放弃登录轨」一类收工话术
  → FAIL（假阴性：该走 auth_flow 却放弃）

  若已有「缺号：干净」且无「没号不开」话术 → PASS；两者同框 → FAIL（自相矛盾）
  若未见干净口 → SKIP

用法:
  python auth_false_negative_check.py --host-dir DIR
  python auth_false_negative_check.py --dig-root DIR [--only-fail]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SKIP = frozenset(
    {"js", "资产", "报告", "node_modules", ".git", "_trash", "tmp", "temp", "__pycache__"}
)
EP_NAMES = ("endpoints.md", "endpoints_auth.md")
DONE_NAMES = ("DONE_anon.md", "DONE.md")

FN_TALK_RE = re.compile(
    r"没号不开|无测试号跳过登录|放弃登录轨|accounts\s*空\s*不开|"
    r"无\s*ready\s*cookie.{0,16}不开登录|无测试号.{0,12}跳过"
)
CLEAN_QUE_RE = re.compile(r"缺号\s*[：:]\s*干净")


def has_clean_auth(text: str) -> bool:
    # table: | POST | /api/auth/login |
    for m in re.finditer(
        r"(?im)\|\s*POST\s*\|\s*`?(?:https?://[^/\s|]+)?(/api/auth/(?:register|login)(?:/[\w.-]+)?)`?\s*\|",
        text,
    ):
        if "captcha" not in m.group(1).lower():
            return True
    # free text POST ... /api/auth/login
    for m in re.finditer(r"(?im)\bPOST\b[^\n]{0,160}", text):
        frag = m.group(0)
        if re.search(r"/api/auth/(?:register|login)\b", frag) and "captcha" not in frag.lower():
            return True
    # path list without METHOD on same line but marked 干净口
    if re.search(r"(?im)/api/auth/(?:register|login)\b(?!/captcha)[^\n]{0,40}干净", text):
        return True
    if re.search(r"(?im)干净口[^\n]{0,80}/api/auth/(?:register|login)\b(?!/captcha)", text):
        return True
    # bare paths in table second column with 干净 in remark
    for m in re.finditer(
        r"(?im)\|\s*`?(/api/auth/(?:register|login)(?:/[\w.-]+)?)`?\s*\|([^\n]*)",
        text,
    ):
        path, rest = m.group(1), m.group(2)
        if "captcha" in path.lower():
            continue
        if re.search(r"POST|干净", rest, re.I) or True:
            # if this path appears and captcha sibling exists, still count clean path
            return True
    return False


def check_host(host_dir: Path) -> tuple[str, list[str]]:
    ep_blob = ""
    for name in EP_NAMES:
        fp = host_dir / name
        if fp.is_file():
            ep_blob += "\n" + fp.read_text(encoding="utf-8", errors="replace")
    if not ep_blob.strip():
        return "SKIP", ["无 endpoints*"]
    if not has_clean_auth(ep_blob):
        return "SKIP", ["未见无盾干净登录/注册口"]

    done_blob = ""
    for name in DONE_NAMES:
        fp = host_dir / name
        if fp.is_file():
            done_blob += "\n" + fp.read_text(encoding="utf-8", errors="replace")
    if not done_blob.strip():
        return "SKIP", ["无 DONE_anon/DONE"]

    has_clean_que = bool(CLEAN_QUE_RE.search(done_blob))
    has_fn_talk = bool(FN_TALK_RE.search(done_blob))
    # 同框自相矛盾：既写缺号：干净又写没号不开 → FAIL，禁止短路 PASS
    if has_clean_que and has_fn_talk:
        return "FAIL", [
            "同框「缺号：干净」与「没号不开/放弃登录轨」自相矛盾（禁止 covered）"
        ]
    if has_clean_que:
        return "PASS", ["已写缺号：干净"]
    if has_fn_talk:
        return "FAIL", [
            "干净登录/注册口存在，但 DONE 写「没号不开/跳过登录/放弃登录轨」= 假阴性（禁止 covered）"
        ]
    return "PASS", ["ok"]


def iter_hosts(dig_root: Path) -> list[Path]:
    return sorted(
        [
            d
            for d in dig_root.iterdir()
            if d.is_dir() and d.name not in SKIP and not d.name.startswith(".")
        ],
        key=lambda d: d.name.lower(),
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="干净口假阴性专闸")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--host-dir", type=Path)
    g.add_argument("--dig-root", type=Path)
    ap.add_argument("--only-fail", action="store_true")
    args = ap.parse_args()
    hosts = [args.host_dir] if args.host_dir else iter_hosts(args.dig_root)
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
        if status == "SKIP":
            continue
        print("%s\t%s\t%s" % (status, h.name, "; ".join(notes)))
    if fail:
        print("# FAIL hosts=%d/%d — 干净口假阴性，禁止 covered" % (fail, len(hosts)))
        return 1
    print("# OK fail=0 hosts=%d" % len(hosts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
