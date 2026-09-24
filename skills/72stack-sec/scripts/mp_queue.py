#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""mp_queue.py — 小程序队（测绘，不占席，不挡翻页）

收单跑。层 0 抠 appid upsert 资产/miniprograms.md；扫本机微信缓存把 waiting_open→cached；
已解到 js/{appid}/anon → unpacked。不下载包、不改 leftover。

状态：skip | pending_triage | waiting_open | cached | unpacked | in_leftover

用法:
  python mp_queue.py --root "D:\SRC挖洞\某_SRC挖洞"
  python mp_queue.py --root "..." --cache-dir "C:\Users\H\Documents\WeChat Files"
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

APPID_RE = re.compile(r"wx[a-f0-9]{16}", re.I)
STATUSES = (
    "skip",
    "pending_triage",
    "waiting_open",
    "cached",
    "unpacked",
    "in_leftover",
)
SKIP_DIR = frozenset(
    {"node_modules", ".git", "_trash", "tmp", "temp", "__pycache__", "进化"}
)
TEXT_SUF = {".js", ".json", ".html", ".htm", ".md", ".txt", ".vue", ".ts", ".wxml"}
THIRD = re.compile(
    r"tenpay|weixin\.qq|wx\.qq\.com|servicewechat\.com/wx[a-f0-9]{16}/(htdocs)?login|"
    r"open\.weixin|res\.wx\.qq",
    re.I,
)
HEAD = "| appid | 名 | 源 | 锁面 | 状态 | 备注 |"
SEP = "|-------|----|----|------|------|------|"


def log(msg: str) -> None:
    print(msg, file=sys.stderr)


def cell(s: str) -> str:
    t = (s or "").replace("\r", " ").replace("\n", " ").replace("|", "／").strip()
    return re.sub(r"\s+", " ", t)


def read_table(path: Path) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("|") or line.startswith("| appid") or re.match(r"\|[-: ]+\|", line):
            continue
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cols) < 5:
            continue
        aid = cols[0].lower()
        if not APPID_RE.fullmatch(aid):
            continue
        st = cols[4] if len(cols) > 4 else "pending_triage"
        if st not in STATUSES:
            st = "pending_triage"
        rows[aid] = {
            "appid": aid,
            "name": cols[1] if len(cols) > 1 else "",
            "src": cols[2] if len(cols) > 2 else "",
            "scope": cols[3] if len(cols) > 3 else "待判",
            "status": st,
            "note": cols[5] if len(cols) > 5 else "",
        }
    return rows


def write_table(path: Path, rows: dict[str, dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# miniprograms（测绘队 · 不占席 · 不挡翻页）",
        "",
        "> 有 appid ≠ 有包。锁面=是 且 waiting_open → 人在微信打开。禁止 CDN 拉包。",
        "",
        HEAD,
        SEP,
    ]
    order = {"waiting_open": 0, "cached": 1, "unpacked": 2, "in_leftover": 3, "pending_triage": 4, "skip": 5}
    for aid in sorted(rows, key=lambda a: (order.get(rows[a]["status"], 9), a)):
        r = rows[aid]
        lines.append(
            f"| {r['appid']} | {cell(r.get('name',''))} | {cell(r.get('src',''))} | "
            f"{cell(r.get('scope','待判'))} | {r.get('status','pending_triage')} | {cell(r.get('note',''))} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def brand_tokens(root: Path) -> list[str]:
    out: list[str] = []
    name = root.name.replace("_SRC挖洞", "").replace("_SRC打洞", "")
    if name:
        out.append(name.lower())
    q = root / "资产" / "种子队列.md"
    if q.is_file():
        for line in q.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.startswith("|"):
                continue
            cols = [c.strip() for c in line.strip("|").split("|")]
            if cols and "." in cols[0] and "种子" not in cols[0]:
                out.append(cols[0].split()[0].lower())
                out.append(cols[0].split(".")[0].lower())
    # uniq
    seen: set[str] = set()
    toks: list[str] = []
    for t in out:
        if t and t not in seen and t not in ("com", "cn", "www", "种子"):
            seen.add(t)
            toks.append(t)
    return toks


def classify(src: str, brands: list[str]) -> tuple[str, str]:
    s = (src or "").lower()
    if THIRD.search(s):
        return "否", "skip"
    if any(b in s for b in brands if len(b) >= 2):
        return "是", "waiting_open"
    return "待判", "pending_triage"


def iter_files(root: Path) -> list[Path]:
    out: list[Path] = []
    for folder in (root / "js", root / "报告", root / "编排"):
        if folder.is_dir():
            out.extend([p for p in folder.rglob("*") if p.is_file()])
    for p in root.rglob("*"):
        if p.is_file() and ("dig" in p.parts or (p.parent.name.endswith("_dig"))):
            out.append(p)
    seen: set[Path] = set()
    uniq: list[Path] = []
    for p in out:
        if p.suffix.lower() not in TEXT_SUF:
            continue
        if any(x in SKIP_DIR for x in p.parts):
            continue
        rp = p.resolve()
        if rp in seen:
            continue
        seen.add(rp)
        uniq.append(p)
    return uniq


def collect(root: Path, rows: dict[str, dict], brands: list[str]) -> int:
    n_new = 0
    for fp in iter_files(root):
        try:
            if fp.stat().st_size > 8_000_000:
                continue
            text = fp.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        try:
            rel = str(fp.relative_to(root))
        except ValueError:
            rel = str(fp)
        for m in APPID_RE.finditer(text):
            aid = m.group(0).lower()
            if aid in rows:
                continue
            scope, st = classify(rel, brands)
            rows[aid] = {
                "appid": aid,
                "name": "",
                "src": rel,
                "scope": scope,
                "status": st,
                "note": "层0",
            }
            n_new += 1
    return n_new


def wechat_cache_roots(extra: Path | None) -> list[Path]:
    roots: list[Path] = []
    if extra and extra.exists():
        roots.append(extra)
    home = Path.home()
    for p in (
        home / "Documents" / "WeChat Files",
        home / "Documents" / "xwechat_files",
        Path(os.environ.get("USERPROFILE", "")) / "Documents" / "WeChat Files",
    ):
        if p.exists():
            roots.append(p)
    seen: set[Path] = set()
    out: list[Path] = []
    for r in roots:
        rp = r.resolve()
        if rp in seen:
            continue
        seen.add(rp)
        out.append(rp)
    return out


def find_cached_appids(cache_roots: list[Path]) -> set[str]:
    found: set[str] = set()
    for root in cache_roots:
        try:
            applets = list(root.rglob("Applet"))
        except OSError:
            applets = []
        dirs = applets or [root]
        for ad in dirs:
            if not ad.is_dir():
                continue
            try:
                kids = list(ad.iterdir())
            except OSError:
                continue
            for child in kids:
                name = child.name.lower()
                if APPID_RE.fullmatch(name):
                    found.add(name)
                elif child.is_file():
                    m = APPID_RE.search(name)
                    if m:
                        found.add(m.group(0))
    return found


def sync_cache(root: Path, rows: dict[str, dict], cache_roots: list[Path]) -> tuple[int, int]:
    cached_ids = find_cached_appids(cache_roots) if cache_roots else set()
    n_cached = n_unpacked = 0
    js = root / "js"
    for aid, r in rows.items():
        if r["status"] in ("skip", "in_leftover"):
            continue
        unpacked_dir = js / aid / "anon"
        if unpacked_dir.is_dir() and any(unpacked_dir.iterdir()):
            if r["status"] not in ("unpacked", "in_leftover"):
                r["status"] = "unpacked"
                r["note"] = (r.get("note") or "") + " 已解包"
                n_unpacked += 1
            continue
        if aid in cached_ids and r["status"] in ("waiting_open", "pending_triage", "cached"):
            if r["status"] != "cached":
                r["status"] = "cached"
                r["scope"] = r["scope"] if r["scope"] == "是" else r["scope"]
                r["note"] = (r.get("note") or "") + " 缓存已见"
                n_cached += 1
    return n_cached, n_unpacked


def main() -> None:
    ap = argparse.ArgumentParser(description="小程序队 收单")
    ap.add_argument("--root", required=True)
    ap.add_argument("--cache-dir", type=Path, default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        log("[E] 不是目录")
        sys.exit(2)

    path = root / "资产" / "miniprograms.md"
    rows = read_table(path)
    brands = brand_tokens(root)
    n_new = collect(root, rows, brands)
    n_cached, n_unpacked = sync_cache(root, rows, wechat_cache_roots(args.cache_dir))
    if not args.dry_run:
        write_table(path, rows)

    n_wait = n_skip = n_triage = 0
    for r in rows.values():
        st = r["status"]
        if st == "waiting_open":
            n_wait += 1
            print(f"WAITING_OPEN\t{r['appid']}\t{r.get('name') or ''}\t{r.get('src','')}")
        elif st == "cached":
            print(f"CACHED\t{r['appid']}\t解包到 js/{r['appid']}/anon 后抽 URL")
        elif st == "unpacked":
            print(f"UNPACKED\t{r['appid']}\tmp_extract_urls.py --dir js/{r['appid']}/anon")
        elif st == "skip":
            n_skip += 1
        elif st == "pending_triage":
            n_triage += 1
    log(
        f"[+] new={n_new} waiting_open={n_wait} cached+={n_cached} unpacked+={n_unpacked} "
        f"triage={n_triage} skip={n_skip} brands={brands[:6]} -> {'dry-run' if args.dry_run else path}"
    )


if __name__ == "__main__":
    main()
