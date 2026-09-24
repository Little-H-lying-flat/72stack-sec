#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""js_inventory_check.py — JS 抽进清单闸（不定级、不探测）

验收句（证据包 16-JS进清单 + 17-JS清单全静态）：
  lab.ok-lean: DONE `JS=N/A瘦壳` → PASS
  lab.ok-fat:  `JS=已抽` + endpoints 标注来自 JS → PASS
  lab.fake:    anon 有 .js 但清单无 JS path 且未声明无业务 API → FAIL
  17 lab.ok:   `JS=已抽` + 来自 JS 的业务 METHOD path → PASS
  17 lab.fake: `JS=已抽` + 来自 JS 行全是静态壳且未写「JS 无业务 API」→ FAIL
  实场同义：`JS → js/...`、来源列含 `.js` 也算已抽（lab 仍教新字段）

验的是抽进清单，不是通读混淆。无 anon .js 且无 JS= 声明 → SKIP（不误杀历史瘦面）。

用法:
  python js_inventory_check.py --dig-root DIR
  python js_inventory_check.py --host-dir DIR
  python js_inventory_check.py --task-root DIR
"""
from __future__ import annotations

import argparse
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

LEAN_RE = re.compile(r"JS\s*=\s*N/A\s*瘦壳", re.I)
FAT_RE = re.compile(r"JS\s*=\s*已抽", re.I)
FROM_JS_RE = re.compile(
    r"来自\s*JS|从\s*JS|JS\s*抽出|JS抽出|JS\s*chunk|来自\s*JS\s*[：:]",
    re.I,
)
# 旧口径同义：JS → js/... / JS：js/... / 表行来源列含 .js 文件名
LEGACY_FROM_JS_RE = re.compile(
    r"JS\s*(?:→|->|⇒)\s*`?js/"
    r"|JS\s*[：:=]\s*`?js/"
    r"|JS\s*[→\-]+\s*`?js/"
    r"|(?:^|\n)\s*\|[^\n]*\.js[^\n]*\|",
    re.I,
)
NO_BIZ_RE = re.compile(
    r"JS\s*无业务\s*API|无业务\s*API.*JS|JS\s*[：:].{0,12}无业务",
    re.I,
)
LAZY_PULL_RE = re.compile(
    r"已拉\s*JS|拉过\s*JS|JS\s*已拉|本站测完",
    re.I,
)

STATIC_PATH_RE = re.compile(
    r"\.(?:js|css|map|woff2?|ttf|eot|svg|png|jpe?g|gif|webp|ico)(?:\?|$)"
    r"|/(?:static|assets|cdn)(?:/|$)"
    r"|chunk\.js|vendor\.js",
    re.I,
)
BIZ_METHOD_RE = re.compile(r"\b(?:GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\b", re.I)
APIISH_RE = re.compile(r"/api(?:/|$)|/graphql|/gql|/v\d+/|/rpc(?:/|$)", re.I)


def _table_rows(text: str) -> list[str]:
    return [ln for ln in text.splitlines() if ln.strip().startswith("|") and "---" not in ln]


def from_js_paths(text: str) -> list[str]:
    """Extract PATH cells from endpoints-style rows that look JS-sourced."""
    paths: list[str] = []
    for ln in _table_rows(text):
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        first = cells[0]
        # 只要 METHOD|PATH|备注 表，跳过 suspects 清单表
        if not (
            BIZ_METHOD_RE.search(first)
            or first.upper()
            in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "METHOD"}
        ):
            continue
        path = cells[1]
        note = cells[2] if len(cells) > 2 else ""
        js_cue = bool(
            re.search(
                r"来自\s*JS|从\s*JS|JS\s*抽出|JS抽出|JS\s*chunk",
                note + " " + ln,
                re.I,
            )
        )
        legacy_src = bool(re.search(r"\.js\b", note, re.I))
        if not js_cue and not legacy_src:
            continue
        if path.lower() in {"path", "路径", "url", "method"}:
            continue
        paths.append(path)
    return paths


def path_is_static(path: str) -> bool:
    p = path.strip().strip("`")
    if not p:
        return True
    if APIISH_RE.search(p):
        return False
    if STATIC_PATH_RE.search(p):
        return True
    if re.search(r"/(?:login|signin|static|assets)(?:/|$|\?)", p, re.I):
        return True
    # absolute path without static extension → treat as biz route
    if p.startswith("/") and not re.search(r"\.[a-z0-9]{1,5}(?:\?|$)", p, re.I):
        return False
    if p.startswith("http") and "/api" in p.lower():
        return False
    if p.startswith("http"):
        return True
    return False


def all_from_js_static(text: str) -> bool:
    paths = from_js_paths(text)
    if not paths:
        return False
    return all(path_is_static(x) for x in paths)




def read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def resolve_task_root(dig_or_host: Path, is_host: bool) -> Path:
    dig = dig_or_host.parent if is_host else dig_or_host
    parent = dig.parent
    if (parent / "js").is_dir() or (parent / "资产").is_dir() or (parent / "编排").is_dir():
        return parent
    if (dig / "js").is_dir():
        return dig
    return parent


def iter_hosts(dig_root: Path) -> list[Path]:
    if not dig_root.is_dir():
        return []
    return sorted(
        d
        for d in dig_root.iterdir()
        if d.is_dir() and d.name not in SKIP and not d.name.startswith(".")
    )


def anon_js_files(task_root: Path, host_name: str) -> list[Path]:
    root = task_root / "js" / host_name / "anon"
    if not root.is_dir():
        return []
    return sorted(p for p in root.rglob("*.js") if p.is_file())


def host_blob(host: Path) -> str:
    parts: list[str] = []
    for name in (
        "DONE_auth.md",
        "DONE_anon.md",
        "DONE.md",
        "endpoints.md",
        "endpoints_auth.md",
        "suspects.md",
    ):
        fp = host / name
        if fp.is_file():
            parts.append(read_text(fp))
    return "\n".join(parts)


def check_host(host: Path, task_root: Path) -> tuple[str, str]:
    text = host_blob(host)
    js_files = anon_js_files(task_root, host.name)
    lean = bool(LEAN_RE.search(text))
    fat = bool(FAT_RE.search(text))
    legacy = bool(LEGACY_FROM_JS_RE.search(text))
    from_js = bool(FROM_JS_RE.search(text)) or legacy
    no_biz = bool(NO_BIZ_RE.search(text))
    lazy = bool(LAZY_PULL_RE.search(text))

    if lean:
        if js_files:
            return "WARN", "JS=N/A瘦壳 但 anon 仍有 .js（声明与落盘矛盾）"
        return "PASS", "JS=N/A瘦壳"

    if js_files:
        if from_js or no_biz:
            # 17: 只看 endpoints* 表行，避免 suspects「JS chunk」污染
            ep_text = "\n".join(
                read_text(host / n)
                for n in ("endpoints.md", "endpoints_auth.md")
                if (host / n).is_file()
            )
            if from_js and not no_biz and all_from_js_static(ep_text or text):
                return (
                    "FAIL",
                    "JS=已抽/有来自JS行但全是静态壳，未声明 JS 无业务 API（禁止 covered）",
                )
            if fat and FROM_JS_RE.search(text):
                note = "JS=已抽 + endpoints 来自 JS（含业务 path）"
            elif fat and no_biz:
                note = "JS=已抽 + JS 无业务 API"
            elif FROM_JS_RE.search(text):
                note = "清单标注来自 JS"
            elif legacy:
                note = "旧同义句（JS→/来源列.js）"
            else:
                note = "已声明 JS 无业务 API"
            return "PASS", note
        return "FAIL", "anon 有 .js 但清单无 JS path 且未声明无业务 API"

    # 无 anon .js
    if fat:
        return "WARN", "JS=已抽 但 anon 无 .js 落盘"
    if lazy and not from_js and not no_biz:
        return "FAIL", "话术已拉 JS/本站测完 却无清单进路（假抽）"
    if not text.strip():
        return "SKIP", "无 DONE/endpoints"
    return "SKIP", "无 anon .js 且无 JS= 声明"


def main() -> int:
    ap = argparse.ArgumentParser(description="JS 抽进清单闸")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--host-dir", type=Path)
    g.add_argument("--dig-root", type=Path)
    g.add_argument("--task-root", type=Path)
    ap.add_argument("--only-fail", action="store_true")
    ap.add_argument("--strict", action="store_true", help="WARN 也当失败")
    args = ap.parse_args()

    if args.task_root:
        task_root = args.task_root.resolve()
        dig_root = task_root / "dig" if (task_root / "dig").is_dir() else task_root
        hosts = iter_hosts(dig_root) or [task_root]
    elif args.host_dir:
        hosts = [args.host_dir.resolve()]
        task_root = resolve_task_root(hosts[0], True)
    else:
        dig_root = args.dig_root.resolve()
        task_root = resolve_task_root(dig_root, False)
        hosts = iter_hosts(dig_root)

    fail = warn = saw = 0
    for h in hosts:
        if not h.is_dir():
            print("ERROR 非目录: %s" % h, file=sys.stderr)
            return 2
        st, note = check_host(h, task_root)
        if st == "SKIP":
            continue
        saw += 1
        if st == "FAIL":
            fail += 1
            print("FAIL\t%s\t%s" % (h.name, note))
        elif st == "WARN":
            warn += 1
            if not args.only_fail:
                print("WARN\t%s\t%s" % (h.name, note))
        elif not args.only_fail:
            print("PASS\t%s\t%s" % (h.name, note))

    print("# js_inventory FAIL=%d WARN=%d saw=%d" % (fail, warn, saw))
    if fail or (args.strict and warn):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
