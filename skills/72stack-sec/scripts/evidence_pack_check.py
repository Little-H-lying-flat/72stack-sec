#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""evidence_pack_check.py — 已授权差分证据包字段闸（复盘模式 · 不探口）"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SKIP = frozenset(
    {"js", "资产", "报告", "node_modules", ".git", "_trash", "tmp", "temp", "__pycache__"}
)
REQUIRED_DIFF_KEYS = (
    "method",
    "url_path",
    "auth_context",
    "status",
    "key_headers",
    "body_signal",
    "contrast",
)
SECRET_RE = re.compile(
    r"(?i)(access_key\s*[:=]|secret_key\s*[:=]|session_token\s*[:=]|"
    r"authorization:\s*bearer\s+[a-z0-9\-._~+/]+=*)"
)
POC_POS_RE = re.compile(r"(?m)^(?:#+\s*)?(?:复现步骤|利用步骤|PoC\s*[:：]|攻击步骤)")
POC_NEG_RE = re.compile(r"不写利用步骤|禁(?:止)?\s*PoC|无\s*PoC|不含利用")
SHALLOW_LOGIN_RE = re.compile(r"能登录(?:控制台)?|可登录控制台")
STS_NAME_RE = re.compile(r"STS|临时钥|临时密钥|GetFederationToken|assumeRole|平台方", re.I)
DIFF_REF_RE = re.compile(r"diff\.json#(D-\d+)|\b(D-\d+)\b", re.I)
COVERED_RE = re.compile(r"\bcovered\b|收工", re.I)


def evidence_roots(pack: Path) -> list[Path]:
    cands = [pack, pack / "证据", pack / "evidence"]
    return [c for c in cands if c.is_dir()]


def read_named(pack: Path, name: str) -> Path | None:
    for root in evidence_roots(pack):
        fp = root / name
        if fp.is_file():
            return fp
    return None


def collect_done_text(pack: Path) -> str:
    parts: list[str] = []
    for fp in pack.rglob("DONE*.md"):
        parts.append(fp.read_text(encoding="utf-8", errors="replace"))
    for fp in pack.rglob("suspects.md"):
        parts.append(fp.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(parts)


def load_diff(root: Path) -> tuple[list[dict], list[str]]:
    errs: list[str] = []
    jp = root / "diff.json"
    mp = root / "diff.md"
    rows: list[dict] = []
    if jp.is_file():
        try:
            data = json.loads(jp.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            return [], ["diff.json 不是合法 JSON: %s" % e]
        if isinstance(data, dict) and "items" in data:
            data = data["items"]
        if not isinstance(data, list):
            return [], ["diff.json 须为数组或 {items:[...]}"]
        for i, row in enumerate(data):
            if not isinstance(row, dict):
                errs.append("diff[%d] 不是对象" % i)
                continue
            rows.append(row)
        return rows, errs
    if mp.is_file():
        lines = mp.read_text(encoding="utf-8", errors="replace").splitlines()
        header = None
        for line in lines:
            if line.strip().startswith("|") and "method" in line.lower():
                header = [c.strip().lower() for c in line.strip("|").split("|")]
                continue
            if header and line.strip().startswith("|") and not re.match(r"^\|[\s:-]+\|", line):
                cols = [c.strip() for c in line.strip("|").split("|")]
                row = {k: v for k, v in zip(header, cols)}
                for a, b in (("url", "url_path"), ("path", "url_path"), ("auth", "auth_context"), ("headers", "key_headers"), ("signal", "body_signal")):
                    if a in row and b not in row:
                        row[b] = row[a]
                row.setdefault("id", "D-%d" % (len(rows) + 1))
                rows.append(row)
        return rows, errs
    return [], ["缺 diff.json / diff.md"]


def contrast_ok(v: object) -> bool:
    s = str(v or "").strip()
    return bool(s) and s.lower() not in ("无", "none", "n/a", "-", "null")


def check_pack(pack: Path) -> tuple[str, list[str]]:
    notes: list[str] = []
    scope = read_named(pack, "scope.md")
    conclusion = read_named(pack, "conclusion.md")
    if scope is None:
        notes.append("缺 scope.md")
    if conclusion is None:
        notes.append("缺 conclusion.md")

    rows: list[dict] = []
    derr = ["缺 diff.json / diff.md"]
    for root in evidence_roots(pack):
        if (root / "diff.json").is_file() or (root / "diff.md").is_file():
            rows, derr = load_diff(root)
            break
    notes.extend(derr)

    any_contrast = False
    ids: list[str] = []
    for i, row in enumerate(rows):
        rid = str(row.get("id") or "D-%d" % (i + 1))
        ids.append(rid)
        for k in REQUIRED_DIFF_KEYS:
            if k not in row or str(row.get(k, "")).strip() == "":
                notes.append("%s 缺字段 %s" % (rid, k))
        if contrast_ok(row.get("contrast")):
            any_contrast = True
    if rows and not any_contrast:
        notes.append("所有 diff 条目均无有效 contrast 对照")

    text_blobs: list[str] = []
    for name in ("scope.md", "conclusion.md", "diff.md", "diff.json"):
        fp = read_named(pack, name)
        if fp is not None:
            text_blobs.append(fp.read_text(encoding="utf-8", errors="replace"))
    done_blob = collect_done_text(pack)
    text_blobs.append(done_blob)
    blob = "\n".join(text_blobs)

    if SECRET_RE.search(blob):
        notes.append("疑似含原始密钥/长 token 正文（须脱敏）")
    if POC_POS_RE.search(blob) and not POC_NEG_RE.search(blob):
        notes.append("含利用/复现步骤表述（证据包禁 PoC；否定句「不写利用步骤」除外）")

    conc = conclusion.read_text(encoding="utf-8", errors="replace") if conclusion else ""
    if SHALLOW_LOGIN_RE.search(conc) and not STS_NAME_RE.search(blob):
        notes.append("conclusion 浅「能登录」但 diff/正文无凭证字段名")

    if COVERED_RE.search(done_blob) or COVERED_RE.search(conc):
        refs = DIFF_REF_RE.findall(done_blob + "\n" + conc)
        flat: list[str] = []
        for r in refs:
            if isinstance(r, tuple):
                flat.extend([x for x in r if x])
            else:
                flat.append(r)
        if not flat:
            notes.append("covered/收工未指回任何 diff id（如 D-01）")
        elif ids:
            unknown = [x for x in flat if x not in ids]
            if unknown:
                notes.append("指回的 diff id 不存在: %s" % ",".join(sorted(set(unknown))))

    if notes:
        return "FAIL", notes
    return "PASS", ["ok"]


def resolve_targets(args) -> list[Path]:
    if args.host_dir:
        return [args.host_dir]
    if args.pack_dir:
        root = args.pack_dir
        labs = [p for p in root.iterdir() if p.is_dir() and p.name.startswith("lab.")]
        return sorted(labs, key=lambda p: p.name) if labs else [root]
    return sorted(
        [d for d in args.dig_root.iterdir() if d.is_dir() and d.name not in SKIP and not d.name.startswith(".")],
        key=lambda d: d.name.lower(),
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="差分证据包字段闸")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--host-dir", type=Path)
    g.add_argument("--dig-root", type=Path)
    g.add_argument("--pack-dir", type=Path)
    ap.add_argument("--only-fail", action="store_true")
    args = ap.parse_args()
    targets = resolve_targets(args)
    fail = 0
    for h in targets:
        if not h.is_dir():
            print("ERROR 非目录: %s" % h, file=sys.stderr)
            return 2
        status, notes = check_pack(h)
        if status == "FAIL":
            fail += 1
        if args.only_fail and status != "FAIL":
            continue
        print("%s\t%s\t%s" % (status, h.name, "; ".join(notes)))
    if fail:
        print("# FAIL packs=%d/%d — 差分证据字段不达标" % (fail, len(targets)))
        return 1
    print("# OK fail=0 packs=%d" % len(targets))
    return 0


if __name__ == "__main__":
    sys.exit(main())
