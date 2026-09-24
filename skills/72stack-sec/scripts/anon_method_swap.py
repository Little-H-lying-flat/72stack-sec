#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""anon_method_swap.py — 未登录原子：同 path 换 METHOD（405 常见换路）

GET 若 405/501，再试 POST/PUT/PATCH（空 body）。输出 JSON。不定级。

用法:
  python anon_method_swap.py --url https://host/api/x
  python anon_method_swap.py --url https://host/api/x --noproxy

退出码: 0=至少一枪有响应  1=全失败  2=参数错误
"""
from __future__ import annotations

import argparse
import json
import ssl
import sys
import urllib.error
import urllib.request


def one(url: str, method: str, timeout: float, noproxy: bool) -> dict:
    handlers = []
    if noproxy:
        handlers.append(urllib.request.ProxyHandler({}))
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    handlers.append(urllib.request.HTTPSHandler(context=ctx))
    opener = urllib.request.build_opener(*handlers)
    data = b"{}" if method != "GET" else None
    headers = {"User-Agent": "72stack-anon-probe/1.0", "Accept": "*/*"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with opener.open(req, timeout=timeout) as resp:
            body = resp.read(2048)
            return {
                "method": method,
                "status": getattr(resp, "status", None) or resp.getcode(),
                "content_type": resp.headers.get("Content-Type"),
                "allow": resp.headers.get("Allow"),
                "body_prefix": body[:160].decode("utf-8", "replace"),
            }
    except urllib.error.HTTPError as e:
        body = e.read(2048) if hasattr(e, "read") else b""
        return {
            "method": method,
            "status": e.code,
            "content_type": e.headers.get("Content-Type") if e.headers else None,
            "allow": e.headers.get("Allow") if e.headers else None,
            "body_prefix": body[:160].decode("utf-8", "replace"),
        }
    except Exception as e:
        return {"method": method, "error": type(e).__name__, "message": str(e)[:200]}


def main() -> int:
    ap = argparse.ArgumentParser(description="同 path 换 METHOD")
    ap.add_argument("--url", required=True)
    ap.add_argument("--timeout", type=float, default=12.0)
    ap.add_argument("--noproxy", action="store_true")
    ap.add_argument("--methods", default="GET,POST,PUT,PATCH")
    args = ap.parse_args()
    if not args.url.startswith("http"):
        print(json.dumps({"ok": False, "error": "bad_url"}, ensure_ascii=False), file=sys.stderr)
        return 2
    methods = [m.strip().upper() for m in args.methods.split(",") if m.strip()]
    shots = [one(args.url, m, args.timeout, args.noproxy) for m in methods]
    ok = any("status" in x for x in shots)
    interesting = [
        x
        for x in shots
        if (x.get("status") and x.get("status") not in (404, 401, 403))
        or (x.get("method") != "GET" and x.get("status") not in (None, 404))
    ]
    out = {
        "ok": ok,
        "url": args.url,
        "shots": shots,
        "hint": "若 GET=405 且其它 METHOD 有业务 JSON/非 HTML，记入 endpoints 与 suspects，勿当噪音丢掉",
        "interesting": interesting,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
