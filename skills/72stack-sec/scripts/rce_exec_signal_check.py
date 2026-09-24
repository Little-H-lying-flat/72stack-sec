#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rce_exec_signal_check.py — RCE covered 必须带可复现执行信号（不定级、不探测）

验收句（证据包 19-RCE执行信号 / 20-RCE模板两步）：
  lab.ok:            RCE covered + 指回 D-xx 且该条含执行信号 → PASS
  lab.fake-sink:     有 D-xx 但只枚举 Sink/堆栈 → FAIL
  lab.fake-uid:      有 D-xx 但只沙箱 uid= → FAIL
  lab.fake-talk:     有 D-xx 但只口头「执行了」→ FAIL
  lab.fake-upload:   有 D-xx 但只「能上传/落盘」→ FAIL（upload-only）
  lab.fake-pollution:有 D-xx 但只「proto/配置污染成功」→ FAIL（pollution-only）
  lab.fake-parse:    有 D-xx 但只「进解析器/文档打开」→ FAIL（parse-only）
  20 lab.fake-half:  只有解释器差分却写 RCE covered → FAIL
  20 lab.fake-sinkonly: 只有 Sink/堆栈 → FAIL

触发：正向 RCE/命令执行/代码执行 + (covered|confirmed|收工)。
半条链/证伪/禁止 covered 不触发。
XSS-only 未写成 RCE 不触发。

用法:
  python rce_exec_signal_check.py --dig-root DIR
  python rce_exec_signal_check.py --host-dir DIR
  python rce_exec_signal_check.py --task-root DIR
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

# 正向 RCE 收工才触发
RCE_CLAIM_RE = re.compile(
    r"(?i)(?:\bRCE\b|命令执行|代码执行|远程代码|模板注入[^\n]{0,20}执行)"
    r".{0,40}(?:\bcovered\b|confirmed|收工)|"
    r"(?:本站|结论)[^\n]{0,40}(?:\bRCE\b|命令执行|代码执行)[^\n]{0,20}\bcovered\b|"
    r"(?:\bRCE\b|命令执行|代码执行)\s*covered"
)

NEG_RE = re.compile(
    r"(?i)(?:禁止|不要|不改|未改|勿|别|不得|未标|不标|禁)[^\n]{0,40}\bcovered\b|"
    r"半条链|已证伪|证伪|未\s*covered|假装[^\n]{0,12}covered|"
    r"不得按\s*RCE|不按\s*RCE\s*收"
)

REF_RE = re.compile(
    r"diff\.json#(D-[A-Za-z0-9]+)|证据/(?:diff\.json#)?(D-[A-Za-z0-9]+)|\b证据\s*=\s*[^\n]*(D-[A-Za-z0-9]+)|\b(D-[A-Za-z0-9]+)\b",
    re.I,
)

# 可复现执行信号（正向；避免「无约定标记文件」误命中）
EXEC_SIGNAL_RE = re.compile(
    r"执行信号\s*[=：:]\s*\S|"
    r"(?<![无没非未])约定标记文件(?:存在|已创建|已写出)|"
    r"标记文件[^\n]{0,12}(?:存在|已创建|已写出)|"
    r"(?<![无没非未])约定\s*stdout|"
    r"stdout\s*[=：:]\s*\S*LAB_|"
    r"\bLAB_RCE\b|\bLAB_STEP\d*_?OK\b|"
    r"无害执行信号|(?<![无没非未])约定副作用",
    re.I,
)

# 假证据：只有这些、没有执行信号 → FAIL
SINK_ONLY_RE = re.compile(
    r"Sink\s*[词枚舉枚举：:=]|Sink词|Sink/堆栈|堆栈[^\n]{0,8}(?:露|露类)|"
    r"Runtime\.exec|ProcessBuilder|ObjectInputStream|readObject|"
    r"仅枚举|只枚举",
    re.I,
)
UID_ONLY_RE = re.compile(r"\buid=\d+|沙箱\s*uid|沙箱回显", re.I)
TALK_ONLY_RE = re.compile(
    r"口头执行|口头[「\"']?执行|模型说|说执行了|判断[已]?执行|已执行系统命令",
    re.I,
)
UPLOAD_ONLY_RE = re.compile(
    r"上传成功|能上传|落盘\s*path|落盘成功|仅上传",
    re.I,
)
POLLUTION_ONLY_RE = re.compile(
    r"__proto__|proto\s*污染|污染成功|merge\s*配置|配置污染|"
    r"prototype\s*pollution",
    re.I,
)
PARSE_ONLY_RE = re.compile(
    r"解析栈|进解析器|仅解析|办公文档打开|文档[已]?被?解析|打开成功[；,]?无执行|"
    r"include\s*成功|模板渲染成功(?![^\n]{0,20}执行信号)",
    re.I,
)
SCHEMA_ONLY_RE = re.compile(
    r"schema\s*ok|规则生效|只改配置|无引擎差分|JSON\s*schema",
    re.I,
)
HALF_ONLY_RE = re.compile(
    r"解释器差分|进解释器|TemplateSyntaxError|语法错|类型错|"
    r"证入参进|OGNL|SpEL[^\n]{0,20}Error|仅半条|半条链",
    re.I,
)


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
    for name in (
        "DONE_auth.md",
        "DONE_anon.md",
        "DONE.md",
        "suspects.md",
    ):
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


def entry_blob(entry: dict, *, signal_only: bool = False) -> str:
    keys = ("body_signal", "signal") if signal_only else (
        "body_signal",
        "contrast",
        "note",
        "desc",
        "signal",
        "evidence",
    )
    parts = []
    for k in keys:
        v = entry.get(k)
        if v:
            parts.append(str(v))
    return "\n".join(parts)


def check_host(host: Path, task_root: Path) -> tuple[str, str]:
    text = host_blob(host)
    if not text.strip():
        return "SKIP", "无 DONE/suspects"
    masked = NEG_RE.sub(" ", text)
    if not RCE_CLAIM_RE.search(masked):
        return "SKIP", "无正向 RCE covered/confirmed 话术"

    refs = []
    for m in REF_RE.finditer(text):
        rid = next(g for g in m.groups() if g)
        refs.append(rid)
    refs = list(dict.fromkeys(refs))
    if not refs:
        return "FAIL", "RCE covered 未指回差分 id（如 diff.json#D-xx）"

    entries = load_diff_entries(task_root, host)
    if not entries:
        return "FAIL", "RCE covered 指回了 id 但找不到 diff.json"

    missing = [r for r in refs if r not in entries]
    if missing:
        return "FAIL", "指回的差分 id 不存在: %s" % ",".join(missing)

    # 执行信号只认 body_signal/signal，避免 contrast「无约定…」误命中
    sig_blobs = [(rid, entry_blob(entries[rid], signal_only=True)) for rid in refs]
    if any(EXEC_SIGNAL_RE.search(b) for _, b in sig_blobs):
        return "PASS", "RCE covered 已指回含执行信号的差分"

    # 无执行信号 → 按假因分类（可用 contrast + DONE）
    blobs = [(rid, entry_blob(entries[rid])) for rid in refs]
    joined = "\n".join(b for _, b in blobs) + "\n" + text
    if UID_ONLY_RE.search(joined) and not EXEC_SIGNAL_RE.search(joined):
        return "FAIL", "RCE covered 证据只有沙箱 uid=，无约定执行信号"
    if TALK_ONLY_RE.search(joined) and not EXEC_SIGNAL_RE.search(joined):
        return "FAIL", "RCE covered 证据只有口头执行，无约定执行信号"
    if SINK_ONLY_RE.search(joined) and not EXEC_SIGNAL_RE.search(joined):
        return "FAIL", "RCE covered 证据只有 Sink/堆栈枚举，无约定执行信号"
    if POLLUTION_ONLY_RE.search(joined) and not EXEC_SIGNAL_RE.search(joined):
        return "FAIL", "RCE covered 证据只有污染成功（pollution-only），无约定执行信号"
    if PARSE_ONLY_RE.search(joined) and not EXEC_SIGNAL_RE.search(joined):
        return "FAIL", "RCE covered 证据只有进解析器/文档打开（parse-only），无约定执行信号"
    if UPLOAD_ONLY_RE.search(joined) and not EXEC_SIGNAL_RE.search(joined):
        return "FAIL", "RCE covered 证据只有能上传/落盘（upload-only），无约定执行信号"
    if SCHEMA_ONLY_RE.search(joined) and not EXEC_SIGNAL_RE.search(joined):
        return "FAIL", "RCE covered 证据只有规则/schema 生效（schema-only），无约定执行信号"
    if HALF_ONLY_RE.search(joined) and not EXEC_SIGNAL_RE.search(joined):
        return "FAIL", "RCE covered 只有解释器/半条链差分，无约定执行信号"
    return "FAIL", "RCE covered 指回的差分缺少可复现执行信号（约定标记/stdout）"


def main() -> int:
    ap = argparse.ArgumentParser(description="RCE 执行信号闸")
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
        # per-host task root: lab.ok style keeps 证据 beside dig
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

    print("# rce_exec_signal FAIL=%d saw=%d" % (fail, saw))
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
