#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""anon_suffix_probe.py — 未登录原子：同 path 试常见后缀

默认试 .json / .json/ / .do / .action（可改）。输出 JSON。不定级、不爆破目录。

用法:
  python anon_suffix_probe.py --url https://host/api/foo
  python anon_suffix_probe.py --url https://host/api/foo --suffixes .json,.do

退出码: 0=至少一枪有响应  1=全失败  2=参数错误
"""
from __future__ import annotations

import argparse
import json
import ssl
import sys
import urllib.error
import urllib.request
from urllib.parse import urlsplit, urlunsplit


DEFAULT_SUFFIXES = (".json", ".json/", ".do", ".action")


def with_suffix(url: str, suf: str) -> str:
    parts = urlsplit(url)
    path = parts.path or "/"
    if path.endswith("/"):
        base = path.rstrip("/") + suf if suf.startswith(".") else path + suf
    else:
        base = path + suf
    return urlunsplit((parts.scheme, parts.netloc, base, parts.query, parts.fragment))


def one(url: str, timeout: float, noproxy: bool) -> dict:
    handlers = []
    if noproxy:
        handlers.append(urllib.request.ProxyHandler({}))
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    handlers.append(urllib.request.HTTPSHandler(context=ctx))
    opener = urllib.request.build_opener(*handlers)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "72stack-anon-probe/1.0", "Accept": "*/*"},
        method="GET",
    )
    try:
        with opener.open(req, timeout=timeout) as resp:
            body = resp.read(2048)
            return {
                "url": url,
                "status": getattr(resp, "status", None) or resp.getcode(),
                "content_type": resp.headers.get("Content-Type"),
                "body_prefix": body[:160].decode("utf-8", "replace"),
            }
    except urllib.error.HTTPError as e:
        body = e.read(2048) if hasattr(e, "read") else b""
        return {
            "url": url,
            "status": e.code,
            "content_type": e.headers.get("Content-Type") if e.headers else None,
            "body_prefix": body[:160].decode("utf-8", "replace"),
        }
    except Exception as e:
        return {"url": url, "error": type(e).__name__, "message": str(e)[:200]}


def main() -> int:
    ap = argparse.ArgumentParser(description="常见 path 后缀探针")
    ap.add_argument("--url", required=True)
    ap.add_argument("--timeout", type=float, default=12.0)
    ap.add_argument("--noproxy", action="store_true")
    ap.add_argument("--suffixes", default=",".join(DEFAULT_SUFFIXES))
    ap.add_argument("--include-base", action="store_true", help="同时打原始 URL")
    args = ap.parse_args()
    if not args.url.startswith("http"):
        print(json.dumps({"ok": False, "error": "bad_url"}, ensure_ascii=False), file=sys.stderr)
        return 2
    sufs = [x.strip() for x in args.suffixes.split(",") if x.strip()]
    targets = []
    if args.include_base:
        targets.append(args.url)
    for sfx in sufs:
        targets.append(with_suffix(args.url, sfx))
    shots = [one(u, args.timeout, args.noproxy) for u in targets]
    ok = any("status" in x for x in shots)
    delta = [
        x
        for x in shots
        if x.get("status") in (200, 500)
        or "json" in (x.get("content_type") or "").lower()
    ]
    out = {
        "ok": ok,
        "base": args.url,
        "shots": shots,
        "delta_candidates": delta,
        "hint": "相对基线多出 JSON/200/业务 500 时写入 endpoints+suspects；禁止目录爆破式加后缀",
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
