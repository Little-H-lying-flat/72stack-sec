#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Optional shape WARN for 72 dig file drops. Never blocks gates.

Default: always exit 0, print WARN\\tkind\\tpath\\treason lines.
--strict: exit 1 if any WARN (for human review only; do NOT wire into p2_gate).

Checks (required subsets only):
  queue-item: seed + coverage in {pending,doing,done,cold}  <- 资产/种子队列.md lines
  asset: host dir exists under dig when referenced
  finding: 报告/*.md has a title (filename/stem)
  baseline-diff: DONE* contains diff#D-xx style ids when claimed

Usage:
  python schema_warn.py --root "D:\\SRC挖洞\\某_SRC挖洞"
  python schema_warn.py --root ... --dig ks_dig
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

COVERAGE = {"pending", "doing", "done", "cold"}
DIFF_RE = re.compile(r"diff#D-[A-Za-z0-9]+|\bD-[A-Za-z0-9]+\b", re.I)
# seed queue line heuristics: pending|doing|done|cold as token
COV_RE = re.compile(r"\b(pending|doing|done|cold)\b", re.I)


def warn(kind: str, path: str, reason: str) -> None:
    print(f"WARN\t{kind}\t{path}\t{reason}")


def find_seed_queue(root: Path) -> Path | None:
    assets = root / "资产"
    if not assets.is_dir():
        return None
    for name in ("种子队列.md", "seed_queue.md", "队列.md"):
        p = assets / name
        if p.is_file():
            return p
    # first md mentioning pending/doing
    for p in assets.glob("*.md"):
        try:
            t = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if "pending" in t and ("doing" in t or "种子" in p.name):
            return p
    return None


def check_queue(root: Path, warnings: list) -> None:
    q = find_seed_queue(root)
    if not q:
        warnings.append(("queue-item", str(root / "资产"), "missing seed queue file"))
        return
    text = q.read_text(encoding="utf-8", errors="ignore")
    lines = [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    if not lines:
        warnings.append(("queue-item", str(q), "empty queue"))
        return
    for i, ln in enumerate(lines, 1):
        # skip pure table separators
        if set(ln) <= set("|-: "):
            continue
        cov = COV_RE.search(ln)
        if not cov:
            # not every line is a queue row
            continue
        c = cov.group(1).lower()
        if c not in COVERAGE:
            warnings.append(("queue-item", f"{q}:{i}", f"coverage not in enum: {c}"))
        # seed: require some non-status token
        body = COV_RE.sub("", ln)
        body = re.sub(r"[|`*\-]+", " ", body).strip()
        if len(body) < 2:
            warnings.append(("queue-item", f"{q}:{i}", "missing seed token"))


def find_dig(root: Path, dig_name: str | None) -> Path | None:
    if dig_name:
        p = root / dig_name
        return p if p.is_dir() else None
    cands = [p for p in root.iterdir() if p.is_dir() and p.name.endswith("_dig")]
    if len(cands) == 1:
        return cands[0]
    if cands:
        return sorted(cands, key=lambda x: x.name)[0]
    return None


def check_assets(dig: Path | None, warnings: list) -> None:
    if not dig:
        warnings.append(("asset", "(dig)", "dig root not found"))
        return
    hosts = [p for p in dig.iterdir() if p.is_dir() and not p.name.startswith(".")]
    if not hosts:
        # not necessarily wrong at open
        return
    for h in hosts:
        # host name is asset id
        if not h.name.strip():
            warnings.append(("asset", str(h), "empty host name"))


def check_findings(root: Path, warnings: list) -> None:
    rep = root / "报告"
    if not rep.is_dir():
        return
    for p in rep.glob("*.md"):
        title = p.stem.strip()
        if not title:
            warnings.append(("finding", str(p), "missing title"))
            continue
        # if file claims 越权/注入/凭证 and no diff ref anywhere, warn
        try:
            t = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        hot = any(k in t for k in ("越权", "注入", "SQLi", "凭证", "IDOR", "未授权"))
        if hot and not DIFF_RE.search(t):
            warnings.append(("finding", str(p), "sensitive claim without diff#D-xx / D-n ref"))


# 否定/证伪：有「差分」字样但无主张，不 WARN
NEG_DIFF_RE = re.compile(
    r"无差分|无业务差分|证伪|未形成差分|差分不成立|没有差分|无 D-xx|无diff",
    re.I,
)
# 正向主张：才要求 D-xx
POS_DIFF_CLAIM_RE = re.compile(
    r"差分证明|业务差分|有差分(?!面)|差分成立|指回\s*diff|diff#D-|越权成立|注入成立",
    re.I,
)


def check_diffs(dig: Path | None, warnings: list) -> None:
    if not dig:
        return
    for done in dig.rglob("DONE*.md"):
        try:
            text = done.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if NEG_DIFF_RE.search(text) and not POS_DIFF_CLAIM_RE.search(text):
            continue
        if POS_DIFF_CLAIM_RE.search(text) or re.search(r"主张.{0,12}差分", text):
            if not DIFF_RE.search(text):
                warnings.append(
                    ("baseline-diff", str(done), "claims diff without diff#D-xx / D-n")
                )


def main() -> int:
    ap = argparse.ArgumentParser(description="Optional schema shape WARN (exit 0 by default)")
    ap.add_argument("--root", required=True, help="task root e.g. D:\\SRC挖洞\\X_SRC挖洞")
    ap.add_argument("--dig", default=None, help="dig folder name under root")
    ap.add_argument("--strict", action="store_true", help="exit 1 on WARN (review only)")
    args = ap.parse_args()
    root = Path(args.root)
    warnings: list[tuple[str, str, str]] = []
    if not root.is_dir():
        warn("task", str(root), "root not a directory")
        return 1 if args.strict else 0

    check_queue(root, warnings)
    dig = find_dig(root, args.dig)
    check_assets(dig, warnings)
    check_findings(root, warnings)
    check_diffs(dig, warnings)

    for kind, path, reason in warnings:
        warn(kind, path, reason)
    if not warnings:
        print("OK\tschema_warn\t.\tno shape warnings")
    return 1 if (args.strict and warnings) else 0


if __name__ == "__main__":
    sys.exit(main())
