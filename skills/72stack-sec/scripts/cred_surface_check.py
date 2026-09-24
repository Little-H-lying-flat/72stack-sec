#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cred_surface_check.py — 云临时钥/凭证面话术闸（不定级、不探测）

手法 A：
  PASS：未实名/空户登录态领到平台方 STS/临时钥 → 记严重凭证面
  FAIL：只写「能登录控制台」或未区分「平台方密钥 vs 本人密钥」就 covered/收工

触发条件（弱触发，避免误杀无关站）：
  DONE/suspects/endpoints 出现凭证相关语境（STS/临时钥/IAM/控制台/凭证/AK/SK/assumeRole 等）
  或明确写了 covered/收工

规则：
  若出现浅收工话术（能登录控制台/能进控制台/登录成功即收 等）
  且全文未见平台方凭证关键字段（STS/临时钥/平台方/assumeRole/GetFederationToken 等）
  → FAIL

用法:
  python cred_surface_check.py --host-dir DIR
  python cred_surface_check.py --dig-root DIR [--only-fail]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SKIP = frozenset(
    {"js", "资产", "报告", "node_modules", ".git", "_trash", "tmp", "temp", "__pycache__"}
)
BLOBS = (
    "DONE_anon.md",
    "DONE_auth.md",
    "DONE.md",
    "suspects.md",
    "endpoints.md",
    "endpoints_auth.md",
)

CTX_RE = re.compile(
    r"STS|临时钥|临时密钥|控制台|凭证|IAM|AK/?SK|AccessKey|assumeRole|"
    r"GetFederationToken|云账号|未实名|空户.?领",
    re.I,
)
SHALLOW_RE = re.compile(
    r"能登录控制台|可登录控制台|登录控制台成功|能进控制台|进入控制台即可|"
    r"只写.?能登录|登录成功即(?:可)?(?:收工|covered)|能登录即收",
    re.I,
)
DEEP_RE = re.compile(
    r"STS|临时钥|临时密钥|平台方(?:密钥|凭证|STS)?|本人密钥|assumeRole|"
    r"GetFederationToken|联邦令牌|严重凭证面|凭证作用域",
    re.I,
)
COVERED_RE = re.compile(r"\bcovered\b|写入\s*covered|标\s*covered|收工", re.I)


def check_host(host_dir: Path) -> tuple[str, list[str]]:
    done_parts: list[str] = []
    ctx_parts: list[str] = []
    for name in BLOBS:
        fp = host_dir / name
        if not fp.is_file():
            continue
        blob = fp.read_text(encoding="utf-8", errors="replace")
        ctx_parts.append(blob)
        # 浅/深话术只认 DONE*；suspects 模板常带「凭证作用域」不能当已证明 STS
        if name.startswith("DONE"):
            done_parts.append(blob)
    if not ctx_parts:
        return "SKIP", ["无 DONE/suspects/endpoints"]
    ctx = "\n".join(ctx_parts)
    speech = "\n".join(done_parts) if done_parts else ""
    if not CTX_RE.search(ctx) and not CTX_RE.search(speech):
        return "SKIP", ["无凭证面语境"]
    if not speech.strip():
        return "SKIP", ["无 DONE 话术"]
    shallow = bool(SHALLOW_RE.search(speech))
    deep = bool(DEEP_RE.search(speech))
    if shallow and not deep:
        return "FAIL", [
            "凭证面浅收工：只写「能登录控制台」类话术，未区分平台方 STS/临时钥 vs 本人密钥（禁止 covered）"
        ]
    if COVERED_RE.search(speech) and re.search(r"能登录", speech) and not deep:
        if re.search(r"控制台", speech):
            return "FAIL", [
                "covered/收工伴随「能登录控制台」但无平台方临时钥/STS 关键字段（禁止 covered）"
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
    ap = argparse.ArgumentParser(description="凭证面话术闸")
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
        print("# FAIL hosts=%d/%d — 凭证面话术不达标" % (fail, len(hosts)))
        return 1
    print("# OK fail=0 hosts=%d" % len(hosts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
