#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sqli_diff_signal_check.py — SQL注入 covered 必须带业务差分信号（不定级、不探测）

验收句（证据包 21-SQLi差分信号 等）：
  lab.ok:            注入 covered + D-xx 含 total/条数/他主体差分 → PASS
  lab.fake-quote:    有 D-xx 但只喷 ' / syntax error → FAIL
  lab.fake-sqlmap:   有 D-xx 但只贴 sqlmap 日志 → FAIL
  lab.fake-waf:      有 D-xx 但只 WAF 405 → FAIL
  22 fake-whitelist / 23 fake-empty-array / 24 fake-log-only → FAIL

触发：正向 SQL注入/注入 + (covered|confirmed|收工)。
禁止 covered / 证伪 / 逻辑洞标明不触发。

用法:
  python sqli_diff_signal_check.py --dig-root DIR
  python sqli_diff_signal_check.py --host-dir DIR
  python sqli_diff_signal_check.py --task-root DIR
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SKIP = frozenset(
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
        "编排",
        "证据",
    }
)

CLAIM_RE = re.compile(
    r"(?i)(?:SQL\s*注入|SQLi|注入(?:点|漏洞)?)"
    r".{0,40}(?:\bcovered\b|confirmed|收工)|"
    r"(?:本站|结论)[^\n]{0,40}(?:SQL\s*注入|SQLi|注入)[^\n]{0,20}\bcovered\b|"
    r"(?:SQL\s*注入|SQLi)\s*covered|"
    # 教学合规包：标题「合规 · …注入 PASS」也当正向收工
    r"#\s*合规[^\n]{0,40}注入[^\n]{0,20}PASS|"
    r"(?:列名位|body|Header)\s*注入\s*PASS|"
    r"Header\s*进查询\s*PASS|"
    r"#\s*合规[^\n]{0,40}(?:列名|body|Header|注入)[^\n]{0,20}PASS"
)

NEG_RE = re.compile(
    r"(?i)(?:禁止|不要|不改|未改|勿|别|不得|未标|不标|禁)[^\n]{0,40}\bcovered\b|"
    r"已证伪|证伪|未\s*covered|假装[^\n]{0,12}covered|"
    r"不得按\s*(?:SQL)?注入|不按\s*SQLi\s*收|逻辑洞[^\n]{0,12}不[是算]?\s*SQLi"
)

REF_RE = re.compile(
    r"diff\.json#(D-\d+)|证据/(?:diff\.json#)?(D-\d+)|\b证据\s*=\s*[^\n]*(D-\d+)|\b(D-\d+)\b",
    re.I,
)

# 业务差分信号（只认 body_signal/signal）
BIZ_DIFF_RE = re.compile(
    r"total\s*[=：:]\s*\d+|"
    r"total\s*(?:从|变|涨|→|->)|"
    r"条数\s*(?:从|变|涨|[=：:]\s*\d+)|"
    r"他主体|他租户|跨租户|"
    r"首行[^\n]{0,20}他|"
    r"业务差分|标识符位差分|"
    r"对照\s*D-\d+",
    re.I,
)

QUOTE_ONLY_RE = re.compile(
    r"syntax\s*error|喷\s*['`']|全参喷|只喷\s*['`']|quote|"
    r"语法错|报错栈",
    re.I,
)
SQLMAP_ONLY_RE = re.compile(r"sqlmap|is vulnerable|injectable", re.I)
WAF_ONLY_RE = re.compile(r"\bWAF\b|\b405\b|blocked", re.I)
WHITELIST_ONLY_RE = re.compile(r"白名单|invalid field|非法列名被拒", re.I)
LOGIC_ONLY_RE = re.compile(r"空数组|不过滤|业务不过滤|逻辑洞", re.I)
LOG_ONLY_RE = re.compile(r"只进日志|写入日志|日志文件|SQL\s*total\s*未变|无库差分", re.I)


def read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def resolve_task_root(dig_or_host: Path, is_host: bool) -> Path:
    dig = dig_or_host.parent if is_host else dig_or_host
    parent = dig.parent
    if (parent / "证据").is_dir() or (parent / "编排").is_dir() or (parent / "资产").is_dir():
        return parent
    return dig if (dig / "证据").is_dir() else parent


def iter_hosts(dig_root: Path) -> list[Path]:
    if not dig_root.is_dir():
        return []
    return sorted(
        d
        for d in dig_root.iterdir()
        if d.is_dir() and d.name not in SKIP and not d.name.startswith(".")
    )


def host_blob(host: Path) -> str:
    parts: list[str] = []
    for name in ("DONE_auth.md", "DONE_anon.md", "DONE.md", "suspects.md"):
        fp = host / name
        if fp.is_file():
            parts.append(read_text(fp))
    return "\n".join(parts)


def load_diff_entries(task_root: Path, host: Path) -> dict[str, dict]:
    candidates = [
        task_root / "证据" / "diff.json",
        host / "diff.json",
        host / "证据" / "diff.json",
        task_root / "diff.json",
    ]
    out: dict[str, dict] = {}
    for fp in candidates:
        if not fp.is_file():
            continue
        try:
            data = json.loads(read_text(fp) or "[]")
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and "entries" in data:
            data = data["entries"]
        if not isinstance(data, list):
            continue
        for item in data:
            if isinstance(item, dict) and item.get("id"):
                out[str(item["id"])] = item
    return out


def entry_signal(entry: dict) -> str:
    parts = []
    for k in ("body_signal", "signal"):
        v = entry.get(k)
        if v:
            parts.append(str(v))
    return "\n".join(parts)


def entry_blob(entry: dict) -> str:
    parts = []
    for k in ("body_signal", "contrast", "note", "desc", "signal", "evidence"):
        v = entry.get(k)
        if v:
            parts.append(str(v))
    return "\n".join(parts)


def check_host(host: Path, task_root: Path) -> tuple[str, str]:
    text = host_blob(host)
    if not text.strip():
        return "SKIP", "无 DONE/suspects"
    masked = NEG_RE.sub(" ", text)
    if not CLAIM_RE.search(masked):
        return "SKIP", "无正向 SQL注入 covered/confirmed 话术"

    refs = []
    for m in REF_RE.finditer(text):
        rid = next(g for g in m.groups() if g)
        refs.append(rid)
    refs = list(dict.fromkeys(refs))
    if not refs:
        return "FAIL", "注入 covered 未指回差分 id（如 diff.json#D-xx）"

    entries = load_diff_entries(task_root, host)
    if not entries:
        return "FAIL", "注入 covered 指回了 id 但找不到 diff.json"

    missing = [r for r in refs if r not in entries]
    if missing:
        return "FAIL", "指回的差分 id 不存在: %s" % ",".join(missing)

    sig_blobs = [(rid, entry_signal(entries[rid])) for rid in refs]
    # 需要业务差分，且不能只是假因
    if any(BIZ_DIFF_RE.search(b) for _, b in sig_blobs):
        # 若唯一命中的「total=」其实写明未变/全量业务不过滤，仍 FAIL
        joined_sig = "\n".join(b for _, b in sig_blobs)
        if LOG_ONLY_RE.search(joined_sig) and not re.search(
            r"他主体|他租户|跨租户", joined_sig
        ):
            return "FAIL", "注入 covered 证据写明无库差分/只进日志"
        if LOGIC_ONLY_RE.search(joined_sig) and not re.search(
            r"他主体|他租户|探[针针]|注入", joined_sig
        ):
            # empty array logic: total=全量 + 业务不过滤
            if re.search(r"不过滤|空数组", joined_sig):
                return "FAIL", "注入 covered 实为业务不过滤逻辑洞，无注入差分"
        return "PASS", "注入 covered 已指回含业务差分信号的差分"

    joined = "\n".join(entry_blob(entries[rid]) for rid in refs) + "\n" + text
    if SQLMAP_ONLY_RE.search(joined):
        return "FAIL", "注入 covered 证据只有 sqlmap 日志，无业务差分"
    if WAF_ONLY_RE.search(joined) and not BIZ_DIFF_RE.search(joined):
        return "FAIL", "注入 covered 证据只有 WAF/405，无业务差分"
    if WHITELIST_ONLY_RE.search(joined):
        return "FAIL", "注入 covered 证据只有列名白名单拒绝，无业务差分"
    if LOGIC_ONLY_RE.search(joined):
        return "FAIL", "注入 covered 实为业务不过滤逻辑洞，无注入差分"
    if LOG_ONLY_RE.search(joined):
        return "FAIL", "注入 covered 证据头只进日志/无库差分"
    if QUOTE_ONLY_RE.search(joined):
        return "FAIL", "注入 covered 证据只有喷引号/syntax error，无业务差分"
    return "FAIL", "注入 covered 指回的差分缺少业务差分信号（total/条数/他主体）"


def main() -> int:
    ap = argparse.ArgumentParser(description="SQLi 业务差分信号闸")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--host-dir", type=Path)
    g.add_argument("--dig-root", type=Path)
    g.add_argument("--task-root", type=Path)
    ap.add_argument("--only-fail", action="store_true")
    args = ap.parse_args()

    if args.task_root:
        task_root = args.task_root.resolve()
        dig_root = task_root / "dig" if (task_root / "dig").is_dir() else task_root
        hosts = iter_hosts(dig_root) or ([dig_root] if dig_root.is_dir() else [])
    elif args.host_dir:
        hosts = [args.host_dir.resolve()]
        task_root = resolve_task_root(hosts[0], True)
    else:
        dig_root = args.dig_root.resolve()
        task_root = resolve_task_root(dig_root, False)
        hosts = iter_hosts(dig_root)

    fail = saw = 0
    for h in hosts:
        if not h.is_dir():
            print("ERROR 非目录: %s" % h, file=sys.stderr)
            return 2
        tr = resolve_task_root(h, True)
        st, note = check_host(h, tr)
        if st == "SKIP":
            continue
        saw += 1
        if st == "FAIL":
            fail += 1
            print("FAIL\t%s\t%s" % (h.name, note))
        elif not args.only_fail:
            print("PASS\t%s\t%s" % (h.name, note))

    print("# sqli_diff_signal FAIL=%d saw=%d" % (fail, saw))
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
