# -*- coding: utf-8 -*-
"""Generic CWE-oriented static scan for src-audit-chain.

Emits a markdown-friendly table of candidate generic findings.
Does NOT claim Confirmed — human/agent must run multi-perspective verify.

Usage:
  python audit_generic_scan.py --root /path/to/src
  python audit_generic_scan.py --root /path/to/src --out report_candidates.md
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass


@dataclass
class Hit:
    gid: str
    cwe: str
    title: str
    path: str
    line: int
    snippet: str


RULES = [
    # gid, cwe, title, regex, exts
    ("G03", "668", "Dangerous bind 0.0.0.0", re.compile(r"0\.0\.0\.0"), (".py", ".js", ".go", ".java", ".yml", ".yaml")),
    ("G04", "942", "CORS allow all origins", re.compile(r"cors_allowed_origins\s*=\s*[\"']\*[\"']|Access-Control-Allow-Origin['\"].*\*"), (".py", ".js", ".ts", ".go")),
    ("G05", "798", "Hardcoded secret-like assignment", re.compile(r"SECRET_KEY\s*=\s*['\"][^'\"]+['\"]|API_KEY\s*=\s*['\"][^'\"]{8,}['\"]"), (".py", ".js", ".ts", ".env", ".json")),
    ("G10", "918", "Outbound HTTP client (SSRF candidate)", re.compile(r"requests\.(get|post|request|put|delete)\(|httpx\.|urllib\.request\.urlopen|urlopen\("), (".py",)),
    ("G20", "78", "OS command / subprocess", re.compile(r"os\.system\(|subprocess\.|Popen\(|shell\s*=\s*True"), (".py",)),
    ("G22", "94", "SSTI-like template string", re.compile(r"render_template_string\("), (".py",)),
    ("G23", "502", "Unsafe deserialize", re.compile(r"pickle\.loads\(|yaml\.load\((?!.*Loader)"), (".py",)),
    ("G26", "1333", "User-driven regex query", re.compile(r"\$regex|re\.compile\([^\n]*request"), (".py", ".js")),
    ("G31", "79", "Frontend HTML sink", re.compile(r"\.html\(|innerHTML\s*=|dangerouslySetInnerHTML|data-\w+=\"\$\{"), (".js", ".jsx", ".tsx", ".vue")),
    ("G40", "200", "Config endpoint pattern", re.compile(r"/api/.*/config|system/config|actuator/env"), (".py", ".js", ".ts", ".java", ".go")),
    ("G41", "732", "Config save/write pattern", re.compile(r"save_config\(|write.*config|json\.dump\([^\n]*config"), (".py",)),
]


def walk_files(root: str, exts: tuple[str, ...]):
    skip = {".git", "node_modules", "venv", "__pycache__", ".venv", "dist", "build", "static"}
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in skip and not d.startswith(".")]
        # still scan non-vendor static js under project js folders
        for f in files:
            if f.endswith(exts) and "jquery" not in f.lower() and "min.js" not in f.lower():
                yield os.path.join(base, f)


def scan(root: str) -> list[Hit]:
    hits: list[Hit] = []
    seen = set()
    for gid, cwe, title, cre, exts in RULES:
        for path in walk_files(root, exts):
            try:
                lines = open(path, encoding="utf-8", errors="ignore").read().splitlines()
            except OSError:
                continue
            for i, line in enumerate(lines, 1):
                if cre.search(line):
                    key = (gid, os.path.relpath(path, root), i)
                    if key in seen:
                        continue
                    seen.add(key)
                    hits.append(
                        Hit(
                            gid=gid,
                            cwe=cwe,
                            title=title,
                            path=os.path.relpath(path, root),
                            line=i,
                            snippet=line.strip()[:160],
                        )
                    )
    # Auth absence as synthetic finding if no markers
    auth_re = re.compile(r"login_required|before_request|check_auth|verify_token", re.I)
    auth_found = False
    for path in walk_files(root, (".py", ".js", ".ts", ".go", ".java")):
        if auth_re.search(open(path, encoding="utf-8", errors="ignore").read()):
            auth_found = True
            break
    if not auth_found:
        hits.insert(
            0,
            Hit(
                gid="G01",
                cwe="306",
                title="No auth markers detected in codebase (candidate missing authentication)",
                path="(project-wide)",
                line=0,
                snippet="grep login_required|before_request|check_auth|verify_token → empty",
            ),
        )
    return hits


def to_markdown(hits: list[Hit], root: str) -> str:
    lines = [
        f"# Generic scan candidates — `{root}`",
        "",
        "> Auto candidates only. Run multi-perspective verification before Confirmed.",
        "",
        "| ID | CWE | Title | Location | Snippet |",
        "|----|-----|-------|----------|---------|",
    ]
    for h in hits:
        loc = h.path if h.line == 0 else f"{h.path}:{h.line}"
        snip = h.snippet.replace("|", "\\|")
        lines.append(f"| {h.gid} | {h.cwe} | {h.title} | `{loc}` | `{snip}` |")
    lines.append("")
    lines.append(f"Total candidates: **{len(hits)}**")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print(f"root not found: {root}", file=sys.stderr)
        return 1
    hits = scan(root)
    md = to_markdown(hits, root)
    print(md)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"\nWrote {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
