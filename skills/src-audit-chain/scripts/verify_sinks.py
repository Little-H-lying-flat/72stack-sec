# -*- coding: utf-8 -*-
"""Multi-perspective sink inventory for src-audit-chain.

Usage:
  python verify_sinks.py --root /path/to/src
"""
from __future__ import annotations

import argparse
import os
import re
import sys


def check(name: str, cond: bool, detail: str = "") -> bool:
    status = "PASS" if cond else "FAIL"
    line = f"[{status}] {name}"
    if detail:
        line += f" | {detail}"
    print(line)
    return cond


def read(path: str) -> str:
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            return f.read()
    except OSError:
        return ""


def walk_files(root: str, exts: tuple[str, ...]):
    skip = {".git", "node_modules", "venv", "__pycache__", ".venv", "dist", "build"}
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in skip]
        for f in files:
            if f.endswith(exts):
                if "jquery" in f.lower():
                    continue
                yield os.path.join(base, f)


def main() -> int:
    ap = argparse.ArgumentParser(description="src-audit-chain sink verification")
    ap.add_argument("--root", required=True, help="source root")
    args = ap.parse_args()
    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print(f"[FAIL] root not found: {root}")
        return 1

    results = []

    # Auth markers
    auth_re = re.compile(
        r"login_required|check_auth|verify_token|before_request|HTTPBasicAuth|@jwt|api_key",
        re.I,
    )
    auth_hit = []
    for p in walk_files(root, (".py", ".js", ".ts", ".go", ".java", ".php")):
        if auth_re.search(read(p)):
            auth_hit.append(os.path.relpath(p, root))
    # FAIL here often means vulnerability (no auth) — printed as inventory
    results.append(
        check(
            "Auth-related markers found (absence may mean CWE-306)",
            len(auth_hit) > 0,
            f"files={len(auth_hit)}",
        )
    )
    if not auth_hit:
        print("  note: no auth markers — treat as high-priority G01 review")

    # Dangerous sinks
    sink_re = re.compile(
        r"subprocess\.|os\.system|Popen\(|shell=True|eval\(|exec\(|"
        r"requests\.(get|post|request|put|delete)|httpx\.|urlopen\(|"
        r"pickle\.loads|yaml\.load\(|render_template_string",
        re.I,
    )
    sinks = []
    for p in walk_files(root, (".py", ".js", ".ts", ".go", ".java", ".php")):
        if sink_re.search(read(p)):
            sinks.append(os.path.relpath(p, root))
    results.append(check("Dangerous sink files discovered", len(sinks) > 0, f"count={len(sinks)}"))
    for s in sinks[:40]:
        print(f"  sink-file: {s}")

    # Frontend XSS candidates
    xss_files = []
    xss_re = re.compile(
        r"\.html\(|innerHTML|dangerouslySetInnerHTML|document\.write|data-\w+=\"\$\{"
    )
    for p in walk_files(root, (".js", ".jsx", ".tsx", ".vue", ".html")):
        if xss_re.search(read(p)):
            xss_files.append(os.path.relpath(p, root))
    results.append(
        check("Frontend HTML/attr sink candidates", len(xss_files) > 0, f"count={len(xss_files)}")
    )

    # Bind all interfaces
    bind_all = any(re.search(r"0\.0\.0\.0|::\b", read(p)) for p in walk_files(root, (".py", ".js", ".go", ".java", ".yml", ".yaml", ".json", ".toml")))
    results.append(check("Binds 0.0.0.0 / :: somewhere", bind_all))

    # Title fingerprint
    titles = set()
    for p in walk_files(root, (".html", ".htm", ".vue")):
        for m in re.finditer(r"<title>([^<]+)</title>", read(p), re.I):
            titles.add(m.group(1).strip())
    results.append(
        check("HTML title fingerprint candidates", len(titles) > 0, f"titles={list(titles)[:5]}")
    )

    passed = sum(1 for x in results if x)
    print(f"\n==== verify_sinks PASS_checks={passed}/{len(results)} ====")
    print("Interpret auth ABSENCE + public bind + SSRF/XSS sinks in the audit report.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
