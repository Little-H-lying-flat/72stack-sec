#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ticket_diff_check.py — 验票差分（omit Cookie vs 带 Cookie）一键检查

只做「票还活不活」：对用户声明的验票口打 omit/auth 两枪，比 result/HTTP。
不做换 id、不做矩阵、不拖会话仓、不打印 Cookie/手机号实值。

探针来源（按优先级）:
  1) --url / --method / --body（可重复 --url）
  2) {host}/ticket_probes.txt  （每行: METHOD URL [可选 JSON body]）
  3) DONE_auth.md / DONE.md 里的「验票口=METHOD URL」行

用法:
  python ticket_diff_check.py --host-dir DIR
  python ticket_diff_check.py --host-dir DIR --url https://h/x --method GET
  python ticket_diff_check.py --dig-root DIR --proxy http://127.0.0.1:7897
  python ticket_diff_check.py --host-dir DIR --dry-run

退出码: 0=跑完（含票死/无探针 SKIP）  1=有请求异常且 --strict  2=参数错误
红线: 主控可跑；禁止当扫描器；禁止改探针去打邻号 id。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import ssl
import sys
from pathlib import Path
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener, HTTPSHandler

PROBE_RE = re.compile(
    r"验票口\s*=\s*(?P<method>GET|POST|PUT|HEAD)\s+(?P<url>https?://\S+)",
    re.I,
)
PHONE_RE = re.compile(r"1\d{10}")
TOKENISH_RE = re.compile(
    r"(passToken|access_token|_st|_ph)=([^&\s\"']+)", re.I
)


def redact(s: str) -> str:
    s = PHONE_RE.sub("1**********", s)
    s = TOKENISH_RE.sub(lambda m: "%s=***" % m.group(1), s)
    s = re.sub(
        r'"(userId|shopId|accountId|merchantId|ksUserId|bUserId)"\s*:\s*\d+',
        lambda m: '"%s":***' % m.group(1),
        s,
        flags=re.I,
    )
    s = re.sub(
        r'"(userName|nickName|shopName)"\s*:\s*"[^"]*"',
        lambda m: '"%s":"***"' % m.group(1),
        s,
        flags=re.I,
    )
    s = re.sub(r"\s+", " ", s)
    return s[:160]

def load_cookie_header(path: Path) -> Optional[str]:
    if not path.is_file():
        return None
    parts: list[str] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "\t" in line:
            f = line.split("\t")
            if len(f) >= 7:
                parts.append("%s=%s" % (f[5], f[6]))
                continue
        if "=" in line and not line.lower().startswith("http"):
            parts.append(line)
    if not parts:
        return None
    return "; ".join(parts)


def load_probes(host_dir: Path, cli_urls: list[tuple[str, str, Optional[str]]]) -> list[tuple[str, str, Optional[str]]]:
    if cli_urls:
        return cli_urls
    probes: list[tuple[str, str, Optional[str]]] = []
    tf = host_dir / "ticket_probes.txt"
    if tf.is_file():
        for line in tf.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # METHOD URL [body...]
            m = re.match(r"^(GET|POST|PUT|HEAD)\s+(\S+)(?:\s+(.+))?$", line, re.I)
            if not m:
                continue
            body = m.group(3).strip() if m.group(3) else None
            probes.append((m.group(1).upper(), m.group(2), body))
        if probes:
            return probes
    for name in ("DONE_auth.md", "DONE.md"):
        fp = host_dir / name
        if not fp.is_file():
            continue
        text = fp.read_text(encoding="utf-8", errors="replace")
        for m in PROBE_RE.finditer(text):
            probes.append((m.group("method").upper(), m.group("url").rstrip(")。.,，"), None))
    # dedupe
    seen = set()
    out = []
    for p in probes:
        key = (p[0], p[1], p[2] or "")
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out


def hit(
    method: str,
    url: str,
    cookie: Optional[str],
    body: Optional[str],
    proxy: Optional[str],
    timeout: float,
) -> tuple[str, str, str]:
    """return (http_or_err, status_tag, hint)"""
    headers = {
        "User-Agent": "72stack-ticket-diff/1.0",
        "Accept": "application/json,text/plain,*/*",
    }
    if cookie:
        headers["Cookie"] = cookie
    data = None
    if body is not None and method in ("POST", "PUT"):
        data = body.encode("utf-8")
        headers["Content-Type"] = "application/json"
    handlers = [HTTPSHandler(context=ssl.create_default_context())]
    if proxy:
        handlers.insert(0, ProxyHandler({"http": proxy, "https": proxy}))
    opener = build_opener(*handlers)
    req = Request(url, data=data, headers=headers, method=method)
    try:
        with opener.open(req, timeout=timeout) as resp:
            raw = resp.read(800).decode("utf-8", errors="replace")
            code = str(getattr(resp, "status", None) or resp.getcode())
    except HTTPError as e:
        code = str(e.code)
        try:
            raw = e.read(800).decode("utf-8", errors="replace")
        except Exception:
            raw = str(e)
    except URLError as e:
        return "ERR", "NET", redact(str(e.reason if hasattr(e, "reason") else e))
    except Exception as e:
        return "ERR", "EXC", redact(str(e))

    tag = "BODY"
    m = re.search(r'"result"\s*:\s*(-?\d+)', raw)
    if m:
        tag = "result=%s" % m.group(1)
    elif re.search(r"loginUrl|unauthorized|G-803000|token过期|登录失效|100110000|-401", raw, re.I):
        tag = "NEED_LOGIN"
    elif re.search(r"userId|shopId|accountId|merchantId|nickName|shopName", raw):
        tag = "HAS_IDENTITY"
    return code, tag, redact(raw)


def classify(omit_tag: str, auth_tag: str) -> str:
    if auth_tag.startswith("result=1") or auth_tag == "HAS_IDENTITY":
        if omit_tag in ("NEED_LOGIN",) or omit_tag.startswith("result=109") or omit_tag.startswith("result=-401"):
            return "ALIVE"
        if omit_tag == auth_tag:
            return "SAME_OMIT_AUTH"
        return "ALIVE_WEAK"
    if auth_tag in ("NEED_LOGIN",) or auth_tag.startswith("result=109") or auth_tag.startswith("result=-401"):
        return "DEAD"
    if omit_tag == auth_tag:
        return "NO_DIFF"
    return "CHECK"


def check_host(
    host_dir: Path,
    cli_urls: list[tuple[str, str, Optional[str]]],
    proxy: Optional[str],
    timeout: float,
    dry_run: bool,
) -> tuple[str, list[str]]:
    ck = load_cookie_header(host_dir / "session.cookie")
    probes = load_probes(host_dir, cli_urls)
    lines: list[str] = []
    if not ck:
        return "SKIP", ["无 session.cookie"]
    if not probes:
        return "SKIP", ["无探针（写 ticket_probes.txt 或 DONE_auth 验票口=METHOD URL）"]
    if dry_run:
        for method, url, body in probes:
            lines.append("DRY %s %s body=%s" % (method, url, "Y" if body else "N"))
        return "DRY", lines

    worst = "ALIVE"
    for method, url, body in probes:
        oc, ot, oh = hit(method, url, None, body, proxy, timeout)
        ac, at, ah = hit(method, url, ck, body, proxy, timeout)
        verdict = classify(ot, at)
        lines.append(
            "%s | omit %s/%s | auth %s/%s | %s | auth_hint=%s"
            % (verdict, oc, ot, ac, at, method + " " + url, ah)
        )
        if verdict == "DEAD":
            worst = "DEAD"
        elif verdict in ("NO_DIFF", "SAME_OMIT_AUTH", "CHECK") and worst == "ALIVE":
            worst = verdict
    return worst, lines


def iter_hosts(dig_root: Path) -> list[Path]:
    skip = {"js", "资产", "报告", "node_modules", ".git", "_trash", "tmp", "temp", "__pycache__"}
    return sorted(
        [d for d in dig_root.iterdir() if d.is_dir() and d.name not in skip and not d.name.startswith(".")],
        key=lambda d: d.name.lower(),
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="验票差分 omit vs auth")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--host-dir", type=Path)
    g.add_argument("--dig-root", type=Path)
    ap.add_argument("--url", action="append", default=[], help="可重复；配合 --method/--body")
    ap.add_argument("--method", default="GET")
    ap.add_argument("--body", default=None, help="POST JSON 字符串")
    ap.add_argument("--proxy", default=os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY"))
    ap.add_argument("--timeout", type=float, default=25.0)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--strict", action="store_true", help="网络 ERR 时退出 1")
    args = ap.parse_args()

    cli_urls: list[tuple[str, str, Optional[str]]] = [
        (args.method.upper(), u, args.body) for u in args.url
    ]
    hosts = [args.host_dir] if args.host_dir else iter_hosts(args.dig_root)
    err_net = 0
    for h in hosts:
        if not h.is_dir():
            print("ERROR 非目录: %s" % h, file=sys.stderr)
            return 2
        status, lines = check_host(h, cli_urls if args.host_dir else [], args.proxy, args.timeout, args.dry_run)
        # dig-root mode: per-host probes only (ignore cli unless single host)
        if args.dig_root:
            status, lines = check_host(h, [], args.proxy, args.timeout, args.dry_run)
        print("==== %s [%s] ====" % (h.name, status))
        for ln in lines:
            print(ln)
            if " | ERR/" in ln or ln.startswith("ERR"):
                err_net += 1
    if args.strict and err_net:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
