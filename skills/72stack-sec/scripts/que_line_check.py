#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""que_line_check.py — 缺号行格式校验（不定级、不探测）

检查 DONE_anon.md / DONE.md 里正式「缺号：」行：
  - 须能解析出 kind + 发码 + 提交（按「；键=」切，允许字段内注解分号）
  - kind∈干净|放弃|无HTTP口
  - 干净：发码/提交至少一侧像 HTTP API（METHOD URL 或含 /api/|/pass/ 等）
  - 同框「没号不开/放弃登录轨」+「缺号：干净」→ FAIL
  - 仅标题「缺号行」/勾选行忽略

用法:
  python que_line_check.py --host-dir DIR
  python que_line_check.py --dig-root DIR [--only-fail]

退出码: 0=无 FAIL；1=有 FAIL；2=参数错
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SKIP = frozenset(
    {"js", "资产", "报告", "node_modules", ".git", "_trash", "tmp", "temp", "__pycache__"}
)
DONE_NAMES = ("DONE_anon.md", "DONE.md")
KIND_RE = re.compile(r"缺号\s*[：:]\s*(?P<kind>干净|放弃|无HTTP口)")
FIELD_RE = re.compile(r"[；;]\s*(?P<key>发码|提交|通道|sid|盾|原因)\s*=\s*")
FN_TALK_RE = re.compile(
    r"没号不开|无测试号跳过登录|放弃登录轨|accounts\s*空\s*不开"
)
HTTP_API_RE = re.compile(
    r"(?i)^(?:GET|POST|PUT|PATCH|DELETE)\s+https?://|"
    r"https?://\S*(/api/|/pass/|/rest/|sms|send\w*code|verifycode|mobilecode)"
)


def parse_fields(line: str) -> dict[str, str] | None:
    km = KIND_RE.search(line)
    if not km:
        return None
    fields: dict[str, str] = {"kind": km.group("kind")}
    markers = list(FIELD_RE.finditer(line))
    if not markers:
        return fields  # kind only — incomplete
    for i, m in enumerate(markers):
        key = m.group("key")
        start = m.end()
        end = markers[i + 1].start() if i + 1 < len(markers) else len(line)
        fields[key] = line[start:end].strip().strip("*").strip()
    return fields


def looks_http(s: str) -> bool:
    t = (s or "").strip().strip("`")
    if not t or t in ("无", "N/A", "n/a", "-"):
        return False
    return bool(HTTP_API_RE.search(t))


def check_line(line: str, whole_doc: str) -> list[str]:
    errs: list[str] = []
    # skip non-formal
    if not KIND_RE.search(line):
        return errs
    fields = parse_fields(line)
    if not fields:
        return errs
    kind = fields.get("kind", "")
    if "发码" not in fields or "提交" not in fields:
        errs.append("缺号行缺「发码=」或「提交=」（须用；键= 分隔）")
        return errs
    for k in ("通道", "sid", "盾", "原因"):
        if k not in fields:
            errs.append("缺号行缺「%s=」" % k)
    send, sub = fields.get("发码", ""), fields.get("提交", "")
    if kind == "干净":
        if not (looks_http(send) or looks_http(sub)):
            errs.append("kind=干净 但发码/提交都不像 HTTP API（须 METHOD URL）")
        if FN_TALK_RE.search(whole_doc):
            errs.append("同框「缺号：干净」与「没号不开/放弃登录轨」自相矛盾")
    if kind == "无HTTP口" and (looks_http(send) or looks_http(sub)):
        errs.append("kind=无HTTP口 但发码/提交却像 HTTP API（自相矛盾）")
    return errs


def check_host(host_dir: Path) -> tuple[str, list[str]]:
    notes: list[str] = []
    found_formal = False
    for name in DONE_NAMES:
        fp = host_dir / name
        if not fp.is_file():
            continue
        text = fp.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            if "缺号" not in line:
                continue
            if not KIND_RE.search(line):
                continue
            found_formal = True
            for e in check_line(line, text):
                notes.append("%s: %s" % (name, e))
    if not found_formal:
        # no formal line — not this gate's job if anon missing entirely
        return "SKIP", ["无正式缺号：行"]
    if notes:
        return "FAIL", notes
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
    ap = argparse.ArgumentParser(description="缺号行格式校验")
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
        print("# FAIL hosts=%d/%d — 缺号行格式不达标" % (fail, len(hosts)))
        return 1
    print("# OK fail=0 hosts=%d" % len(hosts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
