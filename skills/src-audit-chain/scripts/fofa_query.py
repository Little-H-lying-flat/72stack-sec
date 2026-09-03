# -*- coding: utf-8 -*-
"""FOFA query helper for src-audit-chain (stats only).

Key resolution order:
  1) --key
  2) env FOFA_KEY
  3) FofaViewer config.properties (common paths / --config)

Usage:
  python fofa_query.py --query 'title="Product"'
  python fofa_query.py --query 'title="X"' --query 'body="A" && body="B"' --out out.json
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import time
from pathlib import Path

import requests

DEFAULT_API = "https://fofa.info"
FIELDS = "host,ip,port,protocol,title,country"


def load_key(config_path: str = "", cli_key: str = "") -> tuple[str, str]:
    if cli_key:
        return cli_key, DEFAULT_API
    env = os.environ.get("FOFA_KEY", "").strip()
    if env:
        return env, os.environ.get("FOFA_API", DEFAULT_API)

    candidates = []
    if config_path:
        candidates.append(Path(config_path))
    candidates.extend(
        [
            Path(r"D:\toos\FofaViewer_1.1.16\config.properties"),
            Path.home() / "FofaViewer" / "config.properties",
        ]
    )
    # glob light
    for base in [Path(r"D:\toos"), Path.home()]:
        if base.exists():
            for p in base.glob("**/FofaViewer*/config.properties"):
                candidates.append(p)

    key, api = "", DEFAULT_API
    for p in candidates:
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        for line in text.splitlines():
            if line.startswith("key="):
                key = line.split("=", 1)[1].strip()
            if line.startswith("api="):
                api = line.split("=", 1)[1].strip().replace("\\:", ":")
        if key:
            return key, api or DEFAULT_API
    return "", DEFAULT_API


def search(api: str, key: str, query: str, size: int = 50, retries: int = 4) -> dict:
    qbase64 = base64.b64encode(query.encode("utf-8")).decode()
    url = api.rstrip("/") + "/api/v1/search/all"
    last = {"error": True, "errmsg": "unknown", "size": 0, "results": []}
    for i in range(retries):
        r = requests.get(
            url,
            params={
                "key": key,
                "qbase64": qbase64,
                "size": size,
                "page": 1,
                "fields": FIELDS,
            },
            timeout=60,
        )
        if r.status_code == 429:
            time.sleep(6 * (i + 1))
            continue
        if r.status_code >= 400:
            last = {"error": True, "errmsg": f"HTTP {r.status_code}", "size": 0, "results": []}
            time.sleep(2)
            continue
        return r.json()
    return last


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", action="append", default=[], help="FOFA query (repeatable)")
    ap.add_argument("--config", default="", help="FofaViewer config.properties path")
    ap.add_argument("--key", default="", help="FOFA API key (prefer env/config)")
    ap.add_argument("--size", type=int, default=50)
    ap.add_argument("--out", default="")
    ap.add_argument("--sleep", type=float, default=3.0)
    args = ap.parse_args()

    if not args.query:
        raise SystemExit("provide at least one --query")

    key, api = load_key(args.config, args.key)
    if not key:
        raise SystemExit("No FOFA key. Set FOFA_KEY or --config/--key")

    info = requests.get(api.rstrip("/") + "/api/v1/info/my", params={"key": key}, timeout=30).json()
    print(
        "Account:",
        {k: info.get(k) for k in ("error", "username", "isvip", "vip_level", "fofa_point")},
    )

    all_rows = []
    per_query = []
    for i, q in enumerate(args.query):
        if i:
            time.sleep(args.sleep)
        data = search(api, key, q, size=args.size)
        size = data.get("size", 0) or 0
        results = data.get("results") or []
        print("=" * 60)
        print("QUERY:", q)
        print("error:", data.get("error"), "size:", size, "returned:", len(results))
        if data.get("errmsg"):
            print("errmsg:", data.get("errmsg"))
        for row in results[:5]:
            print("  sample:", row)
        per_query.append({"query": q, "size": size, "returned": len(results), "error": data.get("error")})
        for row in results:
            if isinstance(row, list) and len(row) >= 3:
                all_rows.append(
                    {
                        "query": q,
                        "host": row[0],
                        "ip": row[1],
                        "port": str(row[2]),
                        "protocol": row[3] if len(row) > 3 else "",
                        "title": row[4] if len(row) > 4 else "",
                        "country": row[5] if len(row) > 5 else "",
                    }
                )

    by_ip_port = {f"{r['ip']}:{r['port']}": r for r in all_rows}
    print("\nDEDUP ip:port:", len(by_ip_port))
    print("THRESHOLD 20+:", "YES" if len(by_ip_port) >= 20 else "NO")
    print("NOTE: apply product fingerprint filter before counting as product cases.")

    out = {
        "api": api,
        "account": {k: info.get(k) for k in ("username", "isvip", "vip_level")},
        "per_query": per_query,
        "raw": len(all_rows),
        "dedup_ip_port": len(by_ip_port),
        "threshold_20": len(by_ip_port) >= 20,
        "items": list(by_ip_port.values()),
    }
    if args.out:
        Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print("Saved", args.out)


if __name__ == "__main__":
    main()
