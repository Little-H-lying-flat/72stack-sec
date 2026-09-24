#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""anon_probe_alive.py — 未登录原子：HTTPS 探活（结构化 JSON）

线程可用。只做探活/跳转摘要，不定级、不爆破。

用法:
  python anon_probe_alive.py --host example.com
  python anon_probe_alive.py --url https://example.com/path
  python anon_probe_alive.py --host example.com --noproxy

退出码: 0=有响应  1=失败  2=参数错误
"""
from __future__ import annotations

import argparse
import json
import ssl
import sys
import urllib.error
import urllib.request


def fetch(url: str, timeout: float, noproxy: bool) -> dict:
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
            body = resp.read(4096)
            return {
                "ok": True,
                "url": url,
                "final_url": resp.geturl(),
                "status": getattr(resp, "status", None) or resp.getcode(),
                "content_type": resp.headers.get("Content-Type"),
                "server": resp.headers.get("Server"),
                "location": resp.headers.get("Location"),
                "body_prefix": body[:200].decode("utf-8", "replace"),
                "body_len_prefix": len(body),
            }
    except urllib.error.HTTPError as e:
        body = e.read(4096) if hasattr(e, "read") else b""
        return {
            "ok": True,
            "url": url,
            "final_url": e.geturl() if hasattr(e, "geturl") else url,
            "status": e.code,
            "content_type": e.headers.get("Content-Type") if e.headers else None,
            "server": e.headers.get("Server") if e.headers else None,
            "location": e.headers.get("Location") if e.headers else None,
            "body_prefix": body[:200].decode("utf-8", "replace"),
            "body_len_prefix": len(body),
            "error": "HTTPError",
        }
    except Exception as e:
        return {"ok": False, "url": url, "error": type(e).__name__, "message": str(e)[:300]}


def main() -> int:
    ap = argparse.ArgumentParser(description="未登录 HTTPS 探活 JSON")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--host")
    g.add_argument("--url")
    ap.add_argument("--timeout", type=float, default=12.0)
    ap.add_argument("--noproxy", action="store_true")
    args = ap.parse_args()
    url = args.url or ("https://%s/" % args.host.strip().strip("/"))
    if not url.startswith("http"):
        print(json.dumps({"ok": False, "error": "bad_url"}, ensure_ascii=False), file=sys.stderr)
        return 2
    out = fetch(url, args.timeout, args.noproxy)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
