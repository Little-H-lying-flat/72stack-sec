#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""deny_covered_hosts_write.py — Grok PreToolUse 焊闸

stdin: hook event JSON (toolName + toolInput)
stdout: {"decision":"deny","reason":"..."} or allow via exit 0 + empty/allow

规则:
  - Write/Edit/Delete 目标 path 含 covered_hosts.txt → DENY（必须走 mark_covered.py）
  - Bash/Shell 命令触碰 covered_hosts.txt → DENY，除非整条是 mark_covered.py 调用
  - 读（Read）不拦
"""
from __future__ import annotations

import json
import re
import sys

COVERED_RE = re.compile(
    r"(?i)(?:^|[/\\\\])(?:资产[/\\\\])?covered_hosts\.txt\b"
)
# allow only a mark_covered.py invocation (no chained writers to covered)
MARK_COVERED_CMD_RE = re.compile(
    r"(?is)^\s*(?:[\w.-]*python\d*(?:\.\d+)?\s+)?(?:"
    r'["\'][^"\']*mark_covered\.py["\']|'
    r"\S*mark_covered\.py"
    r")\b"
)
# compound write operators targeting covered
SHELL_WRITE_RE = re.compile(
    r"(?i)(?:>>|>|Out-File|Set-Content|Add-Content|Tee-Object|"
    r"Clear-Content|ni\b|New-Item|echo\s|printf\s|cat\s*>)"
)


def _paths_from_input(tool_input: dict) -> list[str]:
    out: list[str] = []
    if not isinstance(tool_input, dict):
        return out
    for key in (
        "path",
        "file_path",
        "filePath",
        "target_file",
        "targetFile",
        "file",
        "filename",
    ):
        v = tool_input.get(key)
        if isinstance(v, str):
            out.append(v)
    # Write sometimes nests
    for nest in ("args", "input", "parameters"):
        n = tool_input.get(nest)
        if isinstance(n, dict):
            out.extend(_paths_from_input(n))
    return out


def _command_from_input(tool_input: dict) -> str:
    if not isinstance(tool_input, dict):
        return ""
    for key in ("command", "cmd", "shell_command", "shellCommand"):
        v = tool_input.get(key)
        if isinstance(v, str):
            return v
    return ""


def decide(event: dict) -> dict | None:
    tool = str(event.get("toolName") or event.get("tool_name") or "")
    tin = event.get("toolInput") or event.get("tool_input") or {}
    tool_l = tool.lower()

    # file tools
    if any(x in tool_l for x in ("write", "edit", "delete", "strreplace", "applypatch")):
        for p in _paths_from_input(tin if isinstance(tin, dict) else {}):
            if COVERED_RE.search(p.replace("\\", "/")) or COVERED_RE.search(p):
                return {
                    "decision": "deny",
                    "reason": (
                        "焊闸：禁止直接 Write/Edit covered_hosts.txt；"
                        "请用 scripts/mark_covered.py（先跑 p2_gate）"
                    ),
                }
        return None

    # shell tools
    if any(x in tool_l for x in ("bash", "shell", "powershell", "cmd")):
        cmd = _command_from_input(tin if isinstance(tin, dict) else {})
        if not cmd:
            return None
        if not COVERED_RE.search(cmd) and "covered_hosts" not in cmd.lower():
            return None
        # covered mentioned
        if MARK_COVERED_CMD_RE.search(cmd) and not re.search(
            r"(?i)covered_hosts\.txt\s*[`'\"].*(?:>>|>|Out-File|Set-Content|Add-Content)",
            cmd,
        ):
            # pure mark_covered call (may mention path only as dig/host args — ok)
            # still deny if also shell-writing covered
            if SHELL_WRITE_RE.search(cmd) and COVERED_RE.search(cmd):
                # mark_covered itself doesn't need shell redirects to covered
                if "mark_covered.py" in cmd and not re.search(
                    r"(?i)(>>|>)\s*.*covered_hosts", cmd
                ):
                    return None
                return {
                    "decision": "deny",
                    "reason": (
                        "焊闸：Shell 不得顺带写入 covered_hosts.txt；"
                        "仅允许调用 mark_covered.py"
                    ),
                }
            return None
        return {
            "decision": "deny",
            "reason": (
                "焊闸：禁止 Shell/Bash 直接改 covered_hosts.txt；"
                "请: python <skill>/scripts/mark_covered.py --host-dir … --reason …"
            ),
        }

    return None


def main() -> int:
    raw = sys.stdin.buffer.read()
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    try:
        event = json.loads(raw.decode("utf-8", errors="replace") or "{}")
    except json.JSONDecodeError:
        # fail-open per Grok contract
        return 0

    denial = decide(event if isinstance(event, dict) else {})
    if denial:
        sys.stdout.write(json.dumps(denial, ensure_ascii=False))
        sys.stdout.write("\n")
        # exit 2 also denies; JSON decision is enough — use 0 + decision
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
