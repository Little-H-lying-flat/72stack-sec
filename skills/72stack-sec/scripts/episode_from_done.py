#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""episode_from_done.py — 从任务根 DONE* / 报告 抽进化 episode（只读业务文件，追加 jsonl）

不探测、不定级立法、不写盲区库。禁把 Cookie/Authorization 实值写入 episode。

用法:
  python episode_from_done.py --task-root DIR
  python episode_from_done.py --task-root DIR --host gmsrm.ctrip.com
  python episode_from_done.py --task-root DIR --dry-run

退出码: 0=ok  1=有错误  2=参数错误
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SKIP_DIR = frozenset(
    {
        "js",
        "资产",
        "报告",
        "编排",
        "进化",
        "node_modules",
        ".git",
        ".pi-web",
        "_trash",
        "tmp",
        "temp",
        "__pycache__",
    }
)

SENSITIVE_RE = re.compile(
    r"(?i)(cookie\s*[:=]|authorization\s*[:=]|ct-access-token\s*[:=]|cticket\s*[:=]|"
    r"password\s*[:=]|api[_-]?key\s*[:=]|secret\s*[:=])\s*\S+"
)

WIN_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("hardcoded_token", re.compile(r"写死.*(token|票|密钥)|hardcoded|ct-access-token", re.I)),
    ("upload_html_exec", re.compile(r"任意文件上传|html\s*可执行|text/html|存储型\s*XSS|上传票", re.I)),
    ("samesite_api_read", re.compile(r"同站|same-?site|credentials|操作成功|getInvoiceTitleList|cticket", re.I)),
    ("idor", re.compile(r"越权|IDOR|他主体|跨用户|跨租户", re.I)),
    ("auth_bypass", re.compile(r"未授权|无认证|匿名.*(读|写|登录)|任意登录", re.I)),
    ("info_leak", re.compile(r"信息泄漏|敏感信息|未授权.*读", re.I)),
    ("sqli", re.compile(r"SQL\s*注入|sqli", re.I)),
    ("ssrf", re.compile(r"SSRF", re.I)),
    ("ssti", re.compile(r"SSTI|模板注入", re.I)),
]

FAIL_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("http_405", re.compile(r"405")),
    ("empty_shell", re.compile(r"空壳|瘦壳|404\s*皮")),
    ("waf_family", re.compile(r"waf|盾|envoy\s*waf", re.I)),
    ("need_sms", re.compile(r"发码|短信|sms", re.I)),
    ("need_invite", re.compile(r"邀请码")),
    ("no_diff", re.compile(r"无差分|无新根")),
]


def redact(s: str, limit: int = 500) -> str:
    s = SENSITIVE_RE.sub(r"\1***", s)
    s = re.sub(r"[A-Za-z0-9_\-]{32,}", "***", s)
    s = s.replace("\r", " ").replace("\n", " ")
    return s[:limit].strip()


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def find_dig_roots(task_root: Path) -> list[Path]:
    roots: list[Path] = []
    for p in task_root.iterdir():
        if p.is_dir() and p.name.endswith("_dig"):
            roots.append(p)
    if (task_root / "dig").is_dir():
        roots.append(task_root / "dig")
    # flat host dirs under task_root
    return roots


def iter_host_dirs(task_root: Path, only_host: str | None) -> list[Path]:
    hosts: list[Path] = []
    for dig in find_dig_roots(task_root):
        for p in sorted(dig.iterdir()):
            if not p.is_dir() or p.name in SKIP_DIR:
                continue
            if only_host and p.name != only_host:
                continue
            if (p / "DONE_anon.md").is_file() or (p / "DONE_auth.md").is_file() or (p / "DONE.md").is_file():
                hosts.append(p)
    # also host dirs directly under task if any
    for p in sorted(task_root.iterdir()):
        if not p.is_dir() or p.name in SKIP_DIR or p.name.endswith("_dig"):
            continue
        if only_host and p.name != only_host:
            continue
        if (p / "DONE_anon.md").is_file() or (p / "DONE_auth.md").is_file():
            hosts.append(p)
    # dedupe
    seen: set[str] = set()
    out: list[Path] = []
    for h in hosts:
        key = str(h.resolve())
        if key not in seen:
            seen.add(key)
            out.append(h)
    return out


def parse_track(text: str) -> str:
    m = re.search(r"本轨\s*=\s*([^\s\|，,]+)", text)
    if not m:
        if re.search(r"本轨\s*=\s*有会话|DONE_auth", text):
            return "auth"
        return "anon"
    v = m.group(1).strip()
    # 未登录 contains 登录 — check 未登录 first
    if "一眼" in v:
        return "anon_glance"
    if "未登录" in v:
        return "anon"
    if "有会话" in v:
        return "auth"
    if v == "登录" or v.startswith("登录"):
        return "auth"
    return "unknown"


def parse_assign_line(text: str, key: str) -> str | None:
    m = re.search(rf"{re.escape(key)}\s*=\s*(.+)", text)
    if not m:
        return None
    line = m.group(1).strip()
    # cut at next markdown header-ish
    line = re.split(r"\n(?=#|\*\*)", line)[0]
    return redact(line.replace("\n", " "), 400)


def parse_carry_hosts(raw: str | None) -> list[str]:
    if not raw:
        return []
    # strip comments after fullwidth/half semicolon notes
    head = re.split(r"[；;]", raw)[0]
    parts = re.split(r"[,，\s]+", head)
    hosts: list[str] = []
    for p in parts:
        p = p.strip().strip("`")
        p = re.sub(r"^带出host\s*=\s*", "", p, flags=re.I)
        if not p or p in {"无", "N/A瘦壳", "N/A"}:
            continue
        if re.match(r"^[a-zA-Z0-9._-]+\.[a-zA-Z]{2,}$", p) or "c-ctrip" in p or p.endswith(".com"):
            hosts.append(p.lower())
    return hosts[:30]


def parse_next(text: str) -> str | None:
    m = re.search(r"NEXT\s*[=：:]\s*([^\n]+)", text, re.I)
    if not m:
        m = re.search(r"##\s*NEXT\s*\n+([^\n#]+)", text, re.I)
    if not m:
        return None
    v = m.group(1).strip()
    for k in ("补席", "下种子", "人工过盾", "有会话"):
        if k in v:
            return k
    return redact(v, 40)


def parse_fat_thin(text: str) -> str | None:
    m = re.search(r"肥\s*/\s*瘦\s*[=：:]\s*([^\n]+)", text)
    if m:
        return redact(m.group(1), 120)
    m = re.search(r"肥/瘦\s*[=：:]\s*([^\n]+)", text)
    if m:
        return redact(m.group(1), 120)
    return None


def find_reports(task_root: Path, host: str, done_text: str) -> list[Path]:
    report_dir = task_root / "报告"
    found: list[Path] = []
    # explicit paths in DONE
    for m in re.finditer(r"报告/[^\s\)\"']+\.md", done_text):
        rel = m.group(0).replace("\\", "/")
        p = task_root / rel
        if p.is_file():
            found.append(p)
    if not report_dir.is_dir():
        return found
    host_key = host.split(".")[0].lower()
    for p in report_dir.glob("*.md"):
        name = p.name.lower()
        try:
            head = p.read_text(encoding="utf-8", errors="replace")[:800]
        except OSError:
            continue
        if host.lower() in head.lower() or host_key in name or host.replace(".", "") in name.replace(".", ""):
            if p not in found:
                found.append(p)
    return found[:10]


def severity_from_text(text: str) -> list[str]:
    """Only structured grade lines — avoid DONE 正文里「无高危拟进」等假阳性。"""
    hints: list[str] = []
    # report header style
    if re.search(r"漏洞等级\s*[=：:]\s*严重", text):
        hints.append("严重")
    if re.search(r"漏洞等级\s*[=：:]\s*高危", text):
        hints.append("高危")
    if re.search(r"漏洞等级\s*[=：:]\s*中危", text):
        hints.append("中危")
    # DONE 明确落盘
    if re.search(r"(?<!无)高危已落盘|(?<!无)严重已落盘", text):
        if "高危" not in hints and "严重" not in hints:
            hints.append("高危")
    if re.search(r"(?<!无)中危已落盘|1\s*篇中危", text) and not re.search(
        r"无中危|不重复交|无高危拟进", text
    ):
        if "中危" not in hints and "高危" not in hints and "严重" not in hints:
            hints.append("中危")
    out: list[str] = []
    for h in hints:
        if h not in out:
            out.append(h)
    return out


def tags_from_text(text: str, rules: list[tuple[str, re.Pattern[str]]]) -> list[str]:
    hits: list[str] = []
    for name, rx in rules:
        if rx.search(text) and name not in hits:
            hits.append(name)
    return hits


def outcome_of(sev: list[str], stuck: str | None, text: str, has_report_file: bool) -> str:
    if "严重" in sev or "高危" in sev:
        return "high_report"
    if "中危" in sev:
        return "mid_report"
    # explicit report path + not 无洞
    if has_report_file and re.search(r"报告\s*[=：:].+\.md|`报告/", text):
        if re.search(r"无洞|无新篇|不重复交同根因|本轨不重复", text):
            return "no_report"
        return "report_other"
    if stuck and "N/A瘦壳" not in stuck and re.search(
        r"405|空壳|失败|waf|无差分|换路", stuck, re.I
    ):
        return "stuck"
    if re.search(r"无洞|无新篇|不重复交", text):
        return "no_report"
    return "unknown"


def build_episode(task_root: Path, host_dir: Path, done_path: Path) -> dict:
    text = done_path.read_text(encoding="utf-8", errors="replace")
    host = host_dir.name
    track = parse_track(text)
    if done_path.name.startswith("DONE_auth"):
        track = "auth"
    elif done_path.name.startswith("DONE_anon") and track == "unknown":
        track = "anon"

    stuck = parse_assign_line(text, "卡住对照")
    carry_raw = parse_assign_line(text, "带出host")
    carry = parse_carry_hosts(carry_raw)
    nxt = parse_next(text)
    fat = parse_fat_thin(text)

    reports = find_reports(task_root, host, text)
    report_texts = []
    report_refs: list[str] = []
    for rp in reports:
        try:
            rel = str(rp.relative_to(task_root)).replace("\\", "/")
        except ValueError:
            rel = rp.name
        report_refs.append(rel)
        report_texts.append(rp.read_text(encoding="utf-8", errors="replace")[:4000])

    blob = text + "\n" + "\n".join(report_texts)
    # severity: prefer report bodies; DONE alone only structured lines
    sev = severity_from_text("\n".join(report_texts) if report_texts else text)
    if not sev:
        sev = severity_from_text(text)
    wins = tags_from_text(blob, WIN_RULES)
    fails = tags_from_text((stuck or "") + "\n" + text, FAIL_RULES)
    outcome = outcome_of(sev, stuck, text, bool(report_refs))

    raw_id = f"{host}|{track}|{done_path.name}|{hashlib.sha1(text.encode('utf-8', errors='replace')).hexdigest()[:8]}"
    ep = {
        "id": raw_id,
        "ts": now_iso(),
        "task": task_root.name,
        "host": host,
        "track": track,
        "fat_thin": fat,
        "outcome": outcome,
        "win_patterns": wins,
        "fail_modes": fails,
        "stuck": stuck,
        "carry_hosts": carry,
        "carry_raw": carry_raw,
        "next": nxt,
        "report_refs": report_refs,
        "severity_hints": sev,
        "source_files": [str(done_path.relative_to(task_root)).replace("\\", "/") if done_path.is_relative_to(task_root) else done_path.name],
        "notes": "",
    }
    # stable id without ts
    ep["id"] = f"{host}|{track}|{hashlib.sha1(json.dumps({k: ep[k] for k in ('host','track','outcome','report_refs','stuck','carry_raw')}, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:8]}"
    return ep


def load_existing_ids(path: Path) -> set[str]:
    ids: set[str] = set()
    if not path.is_file():
        return ids
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ids.add(json.loads(line).get("id", ""))
        except json.JSONDecodeError:
            continue
    return ids


def main() -> int:
    ap = argparse.ArgumentParser(description="Extract evolution episodes from DONE*")
    ap.add_argument("--task-root", type=Path, required=True)
    ap.add_argument("--host", type=str, default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    task_root = args.task_root.resolve()
    if not task_root.is_dir():
        print(f"ERROR: task-root not dir: {task_root}", file=sys.stderr)
        return 2

    evo = task_root / "进化"
    out_path = evo / "episodes.jsonl"
    hosts = iter_host_dirs(task_root, args.host)
    if not hosts:
        print("WARN: no host dirs with DONE*")
        return 0

    existing = load_existing_ids(out_path) if out_path.is_file() else set()
    new_eps: list[dict] = []
    for hd in hosts:
        for name in ("DONE_anon.md", "DONE_auth.md", "DONE.md"):
            p = hd / name
            if not p.is_file():
                continue
            # skip DONE.md if split files exist
            if name == "DONE.md" and ((hd / "DONE_anon.md").is_file() or (hd / "DONE_auth.md").is_file()):
                continue
            try:
                ep = build_episode(task_root, hd, p)
            except Exception as ex:  # noqa: BLE001 — surface per-host
                print(f"ERROR {hd.name}/{name}: {ex}", file=sys.stderr)
                continue
            if ep["id"] in existing:
                print(f"SKIP exists {ep['id']}")
                continue
            new_eps.append(ep)
            existing.add(ep["id"])
            print(f"NEW  {ep['id']} outcome={ep['outcome']} wins={ep['win_patterns']} next={ep['next']}")

    if args.dry_run:
        print(f"dry-run: would append {len(new_eps)} episodes → {out_path}")
        return 0

    if new_eps:
        evo.mkdir(parents=True, exist_ok=True)
        with out_path.open("a", encoding="utf-8") as f:
            for ep in new_eps:
                f.write(json.dumps(ep, ensure_ascii=False) + "\n")
        print(f"appended {len(new_eps)} → {out_path}")
    else:
        print("no new episodes")
    return 0


if __name__ == "__main__":
    # Path.is_relative_to is 3.9+; shim for older
    if not hasattr(Path, "is_relative_to"):
        def _is_relative_to(self: Path, other: Path) -> bool:  # type: ignore[misc]
            try:
                self.relative_to(other)
                return True
            except ValueError:
                return False

        Path.is_relative_to = _is_relative_to  # type: ignore[attr-defined]
    sys.exit(main())
