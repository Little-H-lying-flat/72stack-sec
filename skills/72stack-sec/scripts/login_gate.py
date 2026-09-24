#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""login_gate.py — 登录旁路：timeout / offer / ready / _auth_spawn_batch

不占目标席数 10。真源：资产/人工过盾续挖.md。
主控每回合先于 seat_watchdog 跑。执行腿禁止。

用法:
  python login_gate.py --task-root DIR [--dry-run|--apply] [--notify]
  python login_gate.py --task-root DIR --confirm-ready --host HOST
  python login_gate.py --task-root DIR --skip --host HOST
  python login_gate.py --task-root DIR --import-cookie --host HOST --file PATH
  python login_gate.py --task-root DIR --import-header --host HOST --header "a=1; b=2"

期2 UI: scripts/login_ui.py --once | --watch

退出码: 0=无待办  1=有要约/timeout/待spawn  2=参数错
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
SKILL_ROOT = HERE.parent

DEFAULTS: dict[str, Any] = {
    "enabled": 1,
    "wait_max": 1,
    "exec_max": 2,
    "deadline_min": 12,
    "family_deadline_min": 5,
    "cooldown_timeout_h": 6,
    "min_cookie_bytes": 20,
    "notify_on_offer": 0,  # 1=apply 新要约时调 login_ui --once
    "probe_required": 1,  # P0: cookie 后必须业务探活才 ready
    "probe_timeout_sec": 20,
    "manual_only_re": (
        r"飞书员工|员工飞书|要员工|门神|Tanna|tanna|供应商邀约|邀约票|"
        r"DoorGod|mpsso\.jiyunhudong|cli_a\w+.*员工"
    ),
}

PROBE_FAIL_RE = re.compile(
    r"没有用户登录|当前未登录|用户未登录|未登录|请先登录|请登录|"
    r"has_login\"?\s*:\s*false|not\s*login|unauthorized|"
    r"errno\"?\s*:\s*401|error_code\"?\s*:\s*(1002|1[19]\d{2})",
    re.I,
)
PROBE_PASS_RE = re.compile(
    r"has_login\"?\s*:\s*true|\"user_id\"\s*:\s*[1-9]|\"uid\"\s*:\s*[1-9]|"
    r"\"userId\"\s*:\s*[1-9]|\"nick\w*\"\s*:\s*\"[^\"]+\"|"
    r"\"errno\"\s*:\s*0|\"error_code\"\s*:\s*0",
    re.I,
)
IDENTITY_PATH_RE = re.compile(
    r"user/info|account/info|check_login|has_login|/me\b|whoami|"
    r"get_user|user_info|profile|currentUser|session/info",
    re.I,
)

API_URL_HINT = re.compile(
    r"send[_-]?code|sms_login|activation_code|/passport/|/api/|/oauth/|verify_code|"
    r"loginByCode|auth/code|token",
    re.I,
)

STATUSES = frozenset(
    {
        "waiting",
        "offered",
        "ready",
        "doing",
        "done",
        "skip",
        "no_account",
        "timeout",
        "fail_shield",
    }
)
PRIO_RANK = {"高": 0, "高优先": 0, "p0": 0, "中": 1, "中优先": 1, "p1": 1, "低": 2, "p2": 2}


def now_local() -> datetime:
    return datetime.now(timezone.utc).astimezone()


def now_iso() -> str:
    return now_local().isoformat(timespec="seconds")


def log(msg: str) -> None:
    print(msg, file=sys.stderr)


def read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def write_text(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8", newline="\n")


def find_dig(task: Path) -> Path | None:
    for p in sorted(task.iterdir()):
        if p.is_dir() and p.name.endswith("_dig"):
            return p
    d = task / "dig"
    return d if d.is_dir() else None


def load_cfg(task: Path) -> dict[str, Any]:
    cfg = dict(DEFAULTS)
    p = task / "编排" / "login_lane.json"
    if p.is_file():
        try:
            data = json.loads(read_text(p))
            if isinstance(data, dict):
                cfg.update({k: data[k] for k in data if k in cfg or k in DEFAULTS})
        except json.JSONDecodeError as e:
            log(f"[W] login_lane.json 无效: {e}")
    return cfg


@dataclass
class ShieldRow:
    host: str
    shield: str = ""
    family: str = ""
    priority: str = "中"
    send_submit: str = ""
    cookie_path: str = ""
    main_job: str = ""
    status: str = "waiting"
    note: str = ""
    line_idx: int = -1
    status_col: int = -1
    note_col: int = -1
    n_cols: int = 0
    raw: str = ""


@dataclass
class Job:
    id: str
    host: str
    family: str = ""
    priority: int = 1
    priority_label: str = "中"
    login_url: str = ""
    cookie_path: str = ""
    main_job: str = ""
    state: str = "queued"
    offered_at: str = ""
    deadline_at: str = ""
    last_timeout_at: str = ""
    reason: str = ""
    note: str = ""
    manual_only: bool = False


@dataclass
class Report:
    messages: list[str] = field(default_factory=list)
    timeouts: list[str] = field(default_factory=list)
    offered: list[str] = field(default_factory=list)
    readied: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    auth_spawn: list[str] = field(default_factory=list)
    changed: bool = False


def parse_shield_table(path: Path) -> tuple[list[str], list[ShieldRow], int, int]:
    """Return (all_lines, rows, status_col, note_col). status_col may be -1."""
    text = read_text(path)
    lines = text.splitlines()
    if not lines:
        return [], [], -1, -1

    header_idx = -1
    status_col = -1
    note_col = -1
    for i, line in enumerate(lines):
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        low = [c.lower() for c in cells]
        if any("host" in c for c in low) and any("状态" in c or c == "status" for c in cells):
            header_idx = i
            for j, c in enumerate(cells):
                if c in ("状态", "status", "Status"):
                    status_col = j
                if c in ("备注", "note", "Note"):
                    note_col = j
            break

    rows: list[ShieldRow] = []
    if header_idx < 0:
        return lines, rows, -1, -1

    # skip header + separator
    start = header_idx + 1
    if start < len(lines) and re.match(r"^\|[\s\-:|]+\|$", lines[start].strip()):
        start += 1

    for i in range(start, len(lines)):
        line = lines[i]
        if not line.strip().startswith("|"):
            continue
        if re.match(r"^\|[\s\-:|]+\|$", line.strip()):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not cells:
            continue
        host = cells[0].strip().lower()
        if not host or host.startswith("（") or host.startswith("(") or "." not in host:
            continue
        # find status
        st = ""
        st_j = status_col
        if 0 <= status_col < len(cells) and cells[status_col].lower() in STATUSES:
            st = cells[status_col].lower()
        else:
            for j in range(len(cells) - 1, -1, -1):
                if cells[j].lower() in STATUSES:
                    st = cells[j].lower()
                    st_j = j
                    break
        note = ""
        if 0 <= note_col < len(cells):
            note = cells[note_col]
        elif cells and st_j >= 0 and st_j + 1 < len(cells):
            note = cells[st_j + 1]

        def col(j: int, default: str = "") -> str:
            return cells[j] if 0 <= j < len(cells) else default

        # fixed layout from template: 0 host 1 盾 2 同盾族 3 优先 4 发码 5 cookie 6 主业 7 状态 8 备注
        rows.append(
            ShieldRow(
                host=host,
                shield=col(1),
                family=col(2),
                priority=col(3) or "中",
                send_submit=col(4),
                cookie_path=col(5),
                main_job=col(6),
                status=st or "waiting",
                note=note,
                line_idx=i,
                status_col=st_j if st_j >= 0 else status_col,
                note_col=note_col if note_col >= 0 else (st_j + 1 if st_j >= 0 else -1),
                n_cols=len(cells),
                raw=line,
            )
        )
    return lines, rows, status_col, note_col


def set_row_status(lines: list[str], row: ShieldRow, new_status: str, note_append: str = "") -> None:
    if row.line_idx < 0 or row.line_idx >= len(lines):
        return
    line = lines[row.line_idx]
    if not line.strip().startswith("|"):
        return
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    sc = row.status_col
    if sc < 0 or sc >= len(cells):
        # append status before last
        if len(cells) >= 2:
            cells.insert(-1, new_status)
            sc = len(cells) - 2
        else:
            cells.append(new_status)
            sc = len(cells) - 1
    else:
        cells[sc] = new_status
    if note_append:
        nc = row.note_col
        if nc < 0 or nc >= len(cells):
            if sc + 1 < len(cells):
                nc = sc + 1
            else:
                cells.append("")
                nc = len(cells) - 1
        prev = cells[nc]
        tag = note_append.strip()
        if tag and tag not in prev:
            cells[nc] = (prev + " · " + tag).strip(" ·") if prev else tag
    lines[row.line_idx] = "| " + " | ".join(cells) + " |"
    row.status = new_status
    row.status_col = sc


def resolve_cookie_path(task: Path, dig: Path | None, row: ShieldRow) -> Path:
    raw = (row.cookie_path or "").strip()
    if raw and raw not in ("{dig}/…",):
        # {dig}/host/session.cookie
        m = re.search(r"\{dig\}/([^/\s]+)/session\.cookie", raw, re.I)
        if m and dig:
            return dig / m.group(1) / "session.cookie"
        m2 = re.search(r"([\w.-]+)/session\.cookie", raw)
        if m2 and dig:
            return dig / m2.group(1) / "session.cookie"
        p = Path(raw)
        if p.is_absolute():
            return p
        cand = task / raw
        if cand.exists() or raw.endswith("session.cookie"):
            return cand
    if dig:
        return dig / row.host / "session.cookie"
    return task / row.host / "session.cookie"


def cookie_ok(path: Path, min_bytes: int) -> bool:
    try:
        return path.is_file() and path.stat().st_size >= min_bytes
    except OSError:
        return False


def discover_probe_urls(
    task: Path,
    dig: Path | None,
    host: str,
    row: ShieldRow | None = None,
) -> list[str]:
    """Collect identity probe URLs: 探活= / endpoints / heuristics."""
    found: list[str] = []
    seen: set[str] = set()

    def add(u: str) -> None:
        u = (u or "").strip().rstrip(",.;")
        if not u:
            return
        if u.startswith("/"):
            u = f"https://{host}{u}"
        if not u.startswith("http"):
            return
        if u not in seen:
            seen.add(u)
            found.append(u)

    # explicit 探活= in note / main_job / family
    blob = " ".join(
        [
            (row.note if row else ""),
            (row.main_job if row else ""),
            (row.send_submit if row else ""),
            (row.family if row else ""),
        ]
    )
    for m in re.finditer(r"探活\s*[=:：]\s*(\S+)", blob):
        add(m.group(1))

    # dig endpoints / DONE
    host_dir = None
    if dig and (dig / host).is_dir():
        host_dir = dig / host
    if host_dir:
        for name in ("endpoints.md", "endpoints_auth.md", "DONE_anon.md", "matrix.md"):
            text = read_text(host_dir / name)
            for m in re.finditer(r"https?://[^\s|`\]）)]+", text):
                u = m.group(0).rstrip(".,;）)")
                if IDENTITY_PATH_RE.search(u):
                    add(u)
            for m in re.finditer(r"`?(GET|POST)\s+(/[^\s`|]+)`?", text, re.I):
                path = m.group(2)
                if IDENTITY_PATH_RE.search(path):
                    add(path)

    # heuristics
    for path in (
        "/platform/v1/user/info",
        "/api/v1/user/info",
        "/api/user/info",
        "/passport/web/account/info/",
        "/passport/account/info/",
        "/user/info",
        "/check_login/",
        "/check_login",
    ):
        add(f"https://{host}{path}")

    # common SSO hosts linked from family/note
    if re.search(r"open-miniprogram|microapp", blob + host, re.I):
        add("https://open-miniprogram.bytedance.com/check_login/")
        add("https://open.microapp.bytedance.com/platform/v1/user/info")

    return found[:12]


def _load_cookie_opener(cookie_path: Path):
    from http.cookiejar import MozillaCookieJar
    from urllib.request import HTTPCookieProcessor, Request, build_opener

    jar = MozillaCookieJar()
    try:
        # MozillaCookieJar needs # Netscape header ideally
        jar.load(str(cookie_path), ignore_discard=True, ignore_expires=True)
    except Exception:
        # fallback: parse name=value lines / tab netscape manually into header
        hdr_parts = []
        for line in read_text(cookie_path).splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "\t" in line:
                cols = line.split("\t")
                if len(cols) >= 7:
                    hdr_parts.append(f"{cols[5]}={cols[6]}")
            elif "=" in line and not line.lower().startswith("cookie:"):
                hdr_parts.append(line.split(";")[0].strip())
        opener = build_opener()

        def open_with_header(url: str, timeout: int):
            req = Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 login_gate_probe",
                    "Accept": "application/json,text/plain,*/*",
                    "Cookie": "; ".join(hdr_parts),
                },
            )
            return opener.open(req, timeout=timeout)

        return open_with_header

    opener = build_opener(HTTPCookieProcessor(jar))

    def open_jar(url: str, timeout: int):
        from urllib.request import Request

        req = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 login_gate_probe",
                "Accept": "application/json,text/plain,*/*",
            },
        )
        return opener.open(req, timeout=timeout)

    return open_jar


def probe_session(
    task: Path,
    host: str,
    cookie_path: Path,
    row: ShieldRow | None = None,
    cfg: dict[str, Any] | None = None,
) -> tuple[bool, str]:
    """Business identity probe. PASS only if response looks logged-in."""
    cfg = cfg or DEFAULTS
    if not int(cfg.get("probe_required", 1)):
        return True, "probe_disabled"
    if not cookie_ok(cookie_path, int(cfg.get("min_cookie_bytes", 20))):
        return False, "cookie_missing"

    dig = find_dig(task)
    urls = discover_probe_urls(task, dig, host, row)
    if not urls:
        return False, "no_probe_url"

    timeout = int(cfg.get("probe_timeout_sec", 20))
    try:
        open_url = _load_cookie_opener(cookie_path)
    except Exception as e:
        return False, f"cookie_load:{e}"

    # optional csrf from jar for passport APIs
    csrf = ""
    try:
        for line in read_text(cookie_path).splitlines():
            if line.startswith("#") or "\t" not in line:
                continue
            cols = line.split("\t")
            if len(cols) >= 7 and cols[5] in (
                "passport_csrf_token",
                "passport_csrf_token_default",
                "csrftoken",
            ):
                csrf = cols[6]
                break
    except Exception:
        pass

    details: list[str] = []
    for url in urls:
        try:
            # open_url may be jar opener or header opener; inject csrf via wrapper
            from urllib.request import Request, build_opener, HTTPCookieProcessor
            from http.cookiejar import MozillaCookieJar

            jar = MozillaCookieJar()
            try:
                jar.load(str(cookie_path), ignore_discard=True, ignore_expires=True)
                opener = build_opener(HTTPCookieProcessor(jar))
            except Exception:
                opener = build_opener()
            headers = {
                "User-Agent": "Mozilla/5.0 login_gate_probe",
                "Accept": "application/json,text/plain,*/*",
                "Referer": f"https://{host}/",
            }
            if csrf:
                headers["x-csrf-token"] = csrf
                headers["X-Tt-Passport-Csrf-Token"] = csrf
            req = Request(url, headers=headers)
            with opener.open(req, timeout=timeout) as resp:
                code = getattr(resp, "status", None) or resp.getcode()
                raw = resp.read(8000)
                try:
                    body = raw.decode("utf-8", errors="replace")
                except Exception:
                    body = str(raw[:500])
        except Exception as e:
            details.append(f"FAIL {url} err={e}")
            continue

        snip = body.replace("\n", " ")[:180]
        if PROBE_FAIL_RE.search(body):
            details.append(f"FAIL {code} {url} :: {snip}")
            continue
        if code == 401:
            details.append(f"FAIL 401 {url}")
            continue
        if PROBE_PASS_RE.search(body):
            details.append(f"PASS {code} {url} :: {snip}")
            # write probe log without full secrets
            logp = task / "编排" / "login_probe_last.json"
            write_text(
                logp,
                json.dumps(
                    {
                        "host": host,
                        "ok": True,
                        "url": url,
                        "code": code,
                        "at": now_iso(),
                        "snip": snip[:240],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
            )
            return True, f"PASS {url} code={code}"
        # ambiguous 200
        details.append(f"AMBIG {code} {url} :: {snip}")

    write_text(
        task / "编排" / "login_probe_last.json",
        json.dumps(
            {"host": host, "ok": False, "at": now_iso(), "tries": details[:8]},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
    )
    return False, "; ".join(details[:4]) or "all_probes_failed"


def guess_login_url(row: ShieldRow) -> str:
    """Prefer human login page, not send_code/API URLs."""
    blob = " ".join([row.send_submit or "", row.note or "", row.family or "", row.shield or ""])
    urls = re.findall(r"https?://[^\s；;）)\]]+", blob)
    page_urls = []
    for u in urls:
        u = u.rstrip(".,，。")
        if API_URL_HINT.search(u):
            continue
        page_urls.append(u)
    if page_urls:
        return page_urls[0]
    # known product login hosts from notes
    if re.search(r"open-miniprogram", blob, re.I):
        return "https://open-miniprogram.bytedance.com/"
    if re.search(r"open\.microapp", blob, re.I) or "microapp" in (row.host or ""):
        return f"https://{row.host}/" if row.host else "https://open.microapp.bytedance.com/"
    if row.host:
        return f"https://{row.host}/"
    return ""


def is_manual_only(row: ShieldRow, cfg: dict[str, Any]) -> bool:
    blob = " ".join([row.shield, row.family, row.note, row.send_submit, row.main_job])
    return bool(re.search(cfg["manual_only_re"], blob, re.I))


def prio_rank(label: str) -> int:
    k = (label or "中").strip().lower()
    for key, val in PRIO_RANK.items():
        if key.lower() == k or key in (label or ""):
            return val
    if "高" in (label or ""):
        return 0
    if "低" in (label or ""):
        return 2
    return 1


def load_jobs(path: Path) -> dict[str, Job]:
    out: dict[str, Job] = {}
    if not path.is_file():
        return out
    for line in read_text(path).splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        host = str(d.get("host") or "").lower()
        if not host:
            continue
        out[host] = Job(
            id=str(d.get("id") or f"lg_{host}"),
            host=host,
            family=str(d.get("family") or ""),
            priority=int(d.get("priority") or 1),
            priority_label=str(d.get("priority_label") or "中"),
            login_url=str(d.get("login_url") or ""),
            cookie_path=str(d.get("cookie_path") or ""),
            main_job=str(d.get("main_job") or ""),
            state=str(d.get("state") or "queued"),
            offered_at=str(d.get("offered_at") or ""),
            deadline_at=str(d.get("deadline_at") or ""),
            last_timeout_at=str(d.get("last_timeout_at") or ""),
            reason=str(d.get("reason") or ""),
            note=str(d.get("note") or ""),
            manual_only=bool(d.get("manual_only") or False),
        )
    return out


def save_jobs(path: Path, jobs: dict[str, Job]) -> None:
    lines = []
    for host in sorted(jobs.keys()):
        lines.append(json.dumps(asdict(jobs[host]), ensure_ascii=False))
    write_text(path, "\n".join(lines) + ("\n" if lines else ""))


def parse_iso(s: str) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def in_cooldown(job: Job | None, cfg: dict[str, Any], now: datetime) -> bool:
    if not job or not job.last_timeout_at:
        return False
    ts = parse_iso(job.last_timeout_at)
    if not ts:
        return False
    return now < ts + timedelta(hours=float(cfg["cooldown_timeout_h"]))


def sync_job_from_row(job: Job | None, row: ShieldRow, cookie: Path, cfg: dict[str, Any]) -> Job:
    j = job or Job(id=f"lg_{row.host.replace('.', '_')}", host=row.host)
    j.family = row.family or j.family
    j.priority_label = row.priority or j.priority_label
    j.priority = prio_rank(row.priority)
    guessed = guess_login_url(row)
    if guessed:
        j.login_url = guessed  # always refresh; avoid sticky API send_code URL
    j.cookie_path = str(cookie)
    j.main_job = row.main_job or j.main_job
    j.manual_only = is_manual_only(row, cfg)
    j.note = row.note or j.note
    # state from table unless job is more advanced in runtime-only fields
    if row.status in STATUSES:
        j.state = row.status
    return j


def write_offer_md(path: Path, job: Job | None, cfg: dict[str, Any], now: datetime) -> None:
    if not job or job.state != "offered":
        write_text(
            path,
            "# login_offer\n\n> 当前无要约（wait_max 空闲或 login.enabled=0 或无可派 waiting）。\n"
            f"> generated {now_iso()}\n",
        )
        return
    remain = "?"
    dl = parse_iso(job.deadline_at)
    if dl:
        secs = int((dl - now).total_seconds())
        if secs < 0:
            remain = "已到期（下回合 timeout）"
        else:
            remain = f"{secs // 60} 分 {secs % 60} 秒"
    body = f"""# login_offer

> 登录旁路要约（**不占 10 席**）。同时最多 {cfg['wait_max']} 个。  
> generated {now_iso()}

## 当前要约

| 项 | 值 |
|----|-----|
| host | `{job.host}` |
| 同盾族 | {job.family or "—"} |
| 优先 | {job.priority_label} |
| 登录 URL | {job.login_url or "（请打开 https://" + job.host + "/）"} |
| cookie 路径 | `{job.cookie_path}` |
| 进号后主业 | {job.main_job or "—"} |
| offered_at | {job.offered_at} |
| deadline | {job.deadline_at} |
| 剩余 | **{remain}** |
| manual_only | {job.manual_only} |

## 你怎么做

1. 浏览器打开登录 URL，过盾登录（AI 不拖滑块）。
2. 把会话存到 cookie 路径（Netscape 或 `curl -b` 可用）。
3. 任选：对话说 `登录好了 {job.host}` / `过盾续挖 {job.host}`，或：
   `python login_gate.py --task-root <任务根> --confirm-ready --host {job.host}`
4. 没号/跳过：
   `python login_gate.py --task-root <任务根> --skip --host {job.host}`
5. **什么都不做** → 到期自动 `timeout`，冷却 {cfg['cooldown_timeout_h']}h，不空转。

## 导入 cookie 文件

`python login_gate.py --task-root <任务根> --import-cookie --host {job.host} --file <本地cookie文件>`
"""
    write_text(path, body)


def write_auth_seats(path: Path, seats: list[dict[str, str]]) -> None:
    lines = [
        "# auth_seats（登录旁路有会话 · 不计入目标席数 10）",
        "",
        f"> generated {now_iso()} · exec 并行见 login_lane.exec_max",
        "",
        "| 席 | host | 轨 | 状态 | sid | cookie | 备注 |",
        "|----|------|----|------|-----|--------|------|",
    ]
    if not seats:
        lines.append("| — | （空） | 有会话 | idle | — | — | 无 ready 待派 |")
    else:
        for s in seats:
            lines.append(
                f"| {s.get('n','')} | {s.get('host','')} | 有会话 | {s.get('status','pending')} | "
                f"{s.get('sid','—')} | `{s.get('cookie','')}` | {s.get('note','旁路=login_lane')} |"
            )
    write_text(path, "\n".join(lines) + "\n")


def write_auth_prompt(task: Path, dig: Path | None, job: Job, n: int) -> Path:
    prompts = task / "编排" / "auth_seat_prompts"
    prompts.mkdir(parents=True, exist_ok=True)
    fp = prompts / f"auth{n:02d}_{job.host}.txt"
    dig_name = dig.name if dig else "{dig}"
    ck = job.cookie_path or f"{dig_name}/{job.host}/session.cookie"
    text = f"""本轨=有会话
旁路=login_lane
host={job.host}
任务根={task}
cookie={ck}
身份=待确认
半径=未知
进号后主业={job.main_job or "对象图/换 id 或资质口"}

只做这一轨这一站。curl -b 使用上列 cookie。禁止发码、禁止改过盾表、禁止跑 login_gate/watchdog、禁止换站。
交 DONE_auth + 身份= + 半径= + 带出host= + NEXT。
"""
    write_text(fp, text)
    return fp


def count_auth_doing(task: Path, dig: Path | None) -> int:
    """Hosts with cookie + no DONE_auth but shield doing, or auth_seats doing."""
    n = 0
    seats_p = task / "编排" / "auth_seats.md"
    if seats_p.is_file():
        for line in read_text(seats_p).splitlines():
            if "doing" in line.lower() and "|" in line:
                n += 1
    # also dig dirs with cookie mid-flight marked doing in shield
    return n


def hosts_with_done_auth(dig: Path | None) -> set[str]:
    out: set[str] = set()
    if not dig or not dig.is_dir():
        return out
    for d in dig.iterdir():
        if d.is_dir() and (d / "DONE_auth.md").is_file():
            out.add(d.name.lower())
    return out


def patch_next_md(task: Path, rep: Report, offer_host: str | None) -> None:
    """Append login lane hint into NEXT.md without wiping 补席."""
    p = task / "编排" / "NEXT.md"
    existing = read_text(p)
    # Keep primary NEXT action if present
    primary = ""
    m = re.search(r"(?m)^NEXT\s*[：:]\s*(\S+)", existing)
    if m:
        primary = m.group(1)
    lines = []
    if primary in ("补席", "下种子", "人工过盾", "有会话"):
        lines.append(f"NEXT: {primary}")
    elif rep.auth_spawn:
        lines.append("NEXT: 有会话")
    elif offer_host:
        lines.append("NEXT: 人工过盾")
    else:
        lines.append(existing.splitlines()[0] if existing.strip() else "NEXT: 补席")

    lines.append(f"说明: login_gate {now_iso()}")
    if offer_host:
        lines.append(f"登录要约: {offer_host}（见 编排/login_offer.md；不占 10 席）")
    if rep.auth_spawn:
        lines.append("auth_spawn: " + ", ".join(rep.auth_spawn) + " → 读 编排/_auth_spawn_batch.json")
    if rep.timeouts:
        lines.append("login_timeout: " + ", ".join(rep.timeouts))
    if rep.readied:
        lines.append("login_ready: " + ", ".join(rep.readied))
    lines.append("主控: 先 spawn _auth_spawn_batch（有会话旁路），再 seat_watchdog 的 _spawn_batch（未登录）")
    lines.append("禁止: 空 cookie 有会话；执行腿跑 login_gate；auth_wait 填 seats 1–10")
    write_text(p, "\n".join(lines) + "\n")


def run_gate(task: Path, apply: bool, cfg: dict[str, Any]) -> tuple[Report, int]:
    rep = Report()
    orch = task / "编排"
    orch.mkdir(parents=True, exist_ok=True)
    shield_path = task / "资产" / "人工过盾续挖.md"
    if not shield_path.is_file():
        # try template copy hint
        rep.messages.append("无 资产/人工过盾续挖.md")
        log("[W] 无人工过盾续挖表，login_gate 空跑")
        write_offer_md(orch / "login_offer.md", None, cfg, now_local())
        write_text(orch / "_auth_spawn_batch.json", json.dumps({"generated_at": now_iso(), "seats": []}, ensure_ascii=False, indent=2) + "\n")
        write_auth_seats(orch / "auth_seats.md", [])
        return rep, 0

    dig = find_dig(task)
    lines, rows, _sc, _nc = parse_shield_table(shield_path)
    jobs_path = orch / "login_jobs.jsonl"
    jobs = load_jobs(jobs_path)
    now = now_local()
    done_auth = hosts_with_done_auth(dig)
    min_b = int(cfg["min_cookie_bytes"])

    if not int(cfg.get("enabled", 1)):
        rep.messages.append("login.enabled=0，旁路关闭")
        write_offer_md(orch / "login_offer.md", None, cfg, now)
        if apply:
            save_jobs(jobs_path, jobs)
        return rep, 0

    # --- pass 1: cookie → ready; offered expiry → timeout ---
    for row in rows:
        ck = resolve_cookie_path(task, dig, row)
        job = sync_job_from_row(jobs.get(row.host), row, ck, cfg)

        if row.status in ("skip", "no_account", "done"):
            job.state = row.status
            jobs[row.host] = job
            continue

        if row.host in done_auth:
            if row.status != "done":
                set_row_status(lines, row, "done", "DONE_auth 已存在")
                rep.changed = True
                rep.messages.append(f"done\t{row.host}")
            job.state = "done"
            jobs[row.host] = job
            continue

        if cookie_ok(ck, min_b) and row.status in (
            "waiting",
            "offered",
            "timeout",
            "fail_shield",
            "queued",
            "",
        ):
            pok, pdetail = probe_session(task, row.host, ck, row, cfg)
            if pok:
                set_row_status(lines, row, "ready", f"cookie+probe @ {now_iso()}")
                job.state = "ready"
                job.deadline_at = ""
                rep.readied.append(row.host)
                rep.changed = True
                rep.messages.append(f"ready\t{row.host}\t{ck}\t{pdetail}")
            else:
                # cookie 在但业务未登录：不 ready
                set_row_status(
                    lines,
                    row,
                    "fail_shield" if row.status != "offered" else "offered",
                    f"probe_fail @ {now_iso()} {pdetail[:60]}",
                )
                job.state = "fail_shield" if row.status != "offered" else "offered"
                rep.changed = True
                rep.messages.append(f"probe_fail\t{row.host}\t{pdetail}")

        elif row.status == "offered" or job.state == "offered":
            dl = parse_iso(job.deadline_at)
            if dl and now >= dl and not cookie_ok(ck, min_b):
                set_row_status(lines, row, "timeout", f"timeout @ {now_iso()}")
                job.state = "timeout"
                job.last_timeout_at = now_iso()
                job.offered_at = ""
                job.deadline_at = ""
                rep.timeouts.append(row.host)
                rep.changed = True
                rep.messages.append(f"timeout\t{row.host}")

        jobs[row.host] = job

    # refresh row status after mutations
    # re-parse status from rows objects (already updated)

    # --- pass 2: offer ---
    offered_now = [r for r in rows if r.status == "offered"]
    # also jobs still offered
    for r in rows:
        j = jobs.get(r.host)
        if j and j.state == "offered" and r.status != "timeout":
            if r not in offered_now and r.status == "offered":
                pass

    n_offered = sum(1 for r in rows if r.status == "offered")
    wait_max = int(cfg["wait_max"])

    if n_offered < wait_max:
        candidates: list[ShieldRow] = []
        for r in rows:
            if r.status != "waiting":
                continue
            j = jobs.get(r.host) or sync_job_from_row(None, r, resolve_cookie_path(task, dig, r), cfg)
            if j.manual_only:
                continue
            if in_cooldown(j, cfg, now):
                continue
            if r.host in done_auth:
                continue
            if cookie_ok(resolve_cookie_path(task, dig, r), min_b):
                continue
            candidates.append(r)
        candidates.sort(key=lambda r: (prio_rank(r.priority), r.host))
        slots = wait_max - n_offered
        for r in candidates[:slots]:
            ck = resolve_cookie_path(task, dig, r)
            j = sync_job_from_row(jobs.get(r.host), r, ck, cfg)
            j.state = "offered"
            j.offered_at = now_iso()
            j.deadline_at = (now + timedelta(minutes=float(cfg["deadline_min"]))).isoformat(timespec="seconds")
            j.reason = j.reason or "shield_waiting"
            j.login_url = j.login_url or guess_login_url(r)
            set_row_status(lines, r, "offered", f"offered deadline={j.deadline_at}")
            jobs[r.host] = j
            rep.offered.append(r.host)
            rep.changed = True
            rep.messages.append(f"offer\t{r.host}\tdeadline={j.deadline_at}")
            n_offered += 1

    # current offer job for md (first offered by prio)
    offer_job: Job | None = None
    offered_rows = [r for r in rows if r.status == "offered"]
    offered_rows.sort(key=lambda r: (prio_rank(r.priority), r.host))
    if offered_rows:
        offer_job = jobs.get(offered_rows[0].host)

    # --- pass 3: auth spawn batch from ready ---
    ready_rows = [r for r in rows if r.status == "ready"]
    ready_rows.sort(key=lambda r: (prio_rank(r.priority), r.host))
    exec_max = int(cfg["exec_max"])
    # count already doing
    doing_n = sum(1 for r in rows if r.status == "doing")
    auth_seats: list[dict[str, str]] = []
    batch_seats: list[dict[str, Any]] = []
    slot = 0
    for r in ready_rows:
        if doing_n + slot >= exec_max:
            break
        if r.host in done_auth:
            continue
        ck = resolve_cookie_path(task, dig, r)
        if not cookie_ok(ck, min_b):
            set_row_status(lines, r, "fail_shield", "ready 但 cookie 缺失/过短")
            j = jobs.get(r.host)
            if j:
                j.state = "fail_shield"
            rep.changed = True
            continue
        slot += 1
        j = jobs.get(r.host) or sync_job_from_row(None, r, ck, cfg)
        j.state = "ready"
        jobs[r.host] = j
        prompt = write_auth_prompt(task, dig, j, slot) if apply else orch / "auth_seat_prompts" / f"auth{slot:02d}_{r.host}.txt"
        if apply:
            write_auth_prompt(task, dig, j, slot)
        auth_seats.append(
            {
                "n": str(slot),
                "host": r.host,
                "status": "pending_spawn",
                "sid": "—",
                "cookie": str(ck),
                "note": "旁路=login_lane · " + (r.main_job or ""),
            }
        )
        batch_seats.append(
            {
                "n": slot,
                "host": r.host,
                "track": "有会话",
                "lane": "login_lane",
                "cookie": str(ck),
                "prompt_file": str(prompt),
                "main_job": r.main_job,
                "family": r.family,
            }
        )
        rep.auth_spawn.append(r.host)

    # persist
    if apply:
        write_text(shield_path, "\n".join(lines) + "\n")
        save_jobs(jobs_path, jobs)
        write_offer_md(orch / "login_offer.md", offer_job, cfg, now)
        write_auth_seats(orch / "auth_seats.md", auth_seats)
        batch = {
            "generated_at": now_iso(),
            "lane": "login_lane",
            "exec_max": exec_max,
            "seats": batch_seats,
        }
        write_text(
            orch / "_auth_spawn_batch.json",
            json.dumps(batch, ensure_ascii=False, indent=2) + "\n",
        )
        patch_next_md(task, rep, offer_job.host if offer_job else None)
    else:
        # dry-run still show offer snapshot in stdout path
        write_offer_md(orch / "login_offer.md", offer_job, cfg, now)
        log("[dry-run] 不写过盾表/jobs/batch；仍刷新 login_offer.md 供预览")

    for m in rep.messages:
        print(m)
    if offer_job:
        print(f"OFFER\thost={offer_job.host}\tdeadline={offer_job.deadline_at}")
    if rep.auth_spawn:
        print("AUTH_SPAWN\t" + ",".join(rep.auth_spawn))
    if rep.timeouts:
        print("TIMEOUT\t" + ",".join(rep.timeouts))

    pending = bool(rep.offered or rep.timeouts or rep.readied or rep.auth_spawn or offer_job)
    return rep, (1 if pending else 0)


def cmd_confirm_ready(task: Path, host: str, cfg: dict[str, Any]) -> int:
    host = host.lower().strip()
    dig = find_dig(task)
    shield_path = task / "资产" / "人工过盾续挖.md"
    if not shield_path.is_file():
        log("[E] 无过盾表")
        return 2
    lines, rows, _, _ = parse_shield_table(shield_path)
    row = next((r for r in rows if r.host == host), None)
    if not row:
        log(f"[E] 过盾表无 host={host}")
        return 2
    ck = resolve_cookie_path(task, dig, row)
    if not cookie_ok(ck, int(cfg["min_cookie_bytes"])):
        log(f"[E] cookie 不存在或过短: {ck}")
        return 1

    # P0: business probe before ready
    ok, detail = probe_session(task, host, ck, row, cfg)
    print(f"PROBE\t{'PASS' if ok else 'FAIL'}\t{host}\t{detail}")
    jobs_path = task / "编排" / "login_jobs.jsonl"
    jobs = load_jobs(jobs_path)
    j = sync_job_from_row(jobs.get(host), row, ck, cfg)
    if not ok:
        set_row_status(lines, row, "fail_shield", f"probe_fail @ {now_iso()} {detail[:80]}")
        write_text(shield_path, "\n".join(lines) + "\n")
        j.state = "fail_shield"
        j.note = (j.note or "") + f" · probe_fail"
        jobs[host] = j
        save_jobs(jobs_path, jobs)
        print(f"FAIL\tprobe\t{host}\t保持 offered/fail_shield，不 ready")
        return 1

    set_row_status(lines, row, "ready", f"confirm-ready+probe @ {now_iso()}")
    write_text(shield_path, "\n".join(lines) + "\n")
    j.state = "ready"
    jobs[host] = j
    save_jobs(jobs_path, jobs)
    print(f"OK\tready\t{host}\t{ck}")
    # chain apply to build batch
    _, code = run_gate(task, True, cfg)
    return 0 if code in (0, 1) else code


def cmd_skip(task: Path, host: str, cfg: dict[str, Any]) -> int:
    host = host.lower().strip()
    shield_path = task / "资产" / "人工过盾续挖.md"
    if not shield_path.is_file():
        log("[E] 无过盾表")
        return 2
    lines, rows, _, _ = parse_shield_table(shield_path)
    row = next((r for r in rows if r.host == host), None)
    if not row:
        log(f"[E] 过盾表无 host={host}")
        return 2
    set_row_status(lines, row, "skip", f"skip/no_account @ {now_iso()}")
    write_text(shield_path, "\n".join(lines) + "\n")
    jobs_path = task / "编排" / "login_jobs.jsonl"
    jobs = load_jobs(jobs_path)
    dig = find_dig(task)
    j = sync_job_from_row(jobs.get(host), row, resolve_cookie_path(task, dig, row), cfg)
    j.state = "skip"
    jobs[host] = j
    save_jobs(jobs_path, jobs)
    print(f"OK\tskip\t{host}")
    run_gate(task, True, cfg)
    return 0


def resolve_dest_cookie(task: Path, host: str) -> tuple[Path, ShieldRow | None]:
    dig = find_dig(task)
    shield_path = task / "资产" / "人工过盾续挖.md"
    rows: list[ShieldRow] = []
    if shield_path.is_file():
        _, rows, _, _ = parse_shield_table(shield_path)
    row = next((r for r in rows if r.host == host), None)
    if row:
        return resolve_cookie_path(task, dig, row), row
    if dig:
        return dig / host / "session.cookie", row
    return task / f"session.cookie.{host}", row


def header_to_netscape(host: str, header: str) -> str:
    h = header.strip()
    if h.lower().startswith("cookie:"):
        h = h.split(":", 1)[1].strip()
    lines = [
        "# Netscape HTTP Cookie File",
        f"# login_gate --import-header @ {now_iso()}",
        f"# host={host}",
    ]
    for part in re.split(r";\s*", h):
        part = part.strip()
        if not part or "=" not in part:
            continue
        name, val = part.split("=", 1)
        name, val = name.strip(), val.strip()
        if name:
            lines.append(f"{host}\tTRUE\t/\tFALSE\t0\t{name}\t{val}")
    lines.append("")
    return "\n".join(lines)


def cmd_import_cookie(task: Path, host: str, file: Path, cfg: dict[str, Any]) -> int:
    host = host.lower().strip()
    if not file.is_file():
        log(f"[E] 文件不存在: {file}")
        return 2
    dest, row = resolve_dest_cookie(task, host)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(file, dest)
    print(f"OK\timport\t{host}\t{dest}")
    if row is not None or (task / "资产" / "人工过盾续挖.md").is_file():
        return cmd_confirm_ready(task, host, cfg)
    return 0


def cmd_import_header(task: Path, host: str, header: str, cfg: dict[str, Any]) -> int:
    host = host.lower().strip()
    if not header.strip():
        log("[E] 空 Cookie 头")
        return 2
    dest, _row = resolve_dest_cookie(task, host)
    dest.parent.mkdir(parents=True, exist_ok=True)
    write_text(dest, header_to_netscape(host, header))
    print(f"OK\timport-header\t{host}\t{dest}")
    return cmd_confirm_ready(task, host, cfg)


def maybe_notify_ui(task: Path, rep: Report, force: bool = False) -> None:
    """期2: 新要约时调 login_ui --once（通知+弹浏览器）."""
    if not force and not rep.offered:
        # still notify if there is an active offer and force via --notify
        offer_md = read_text(task / "编排" / "login_offer.md")
        if "当前无要约" in offer_md or not offer_md.strip():
            return
    ui = HERE / "login_ui.py"
    if not ui.is_file():
        log("[W] login_ui.py 缺失，跳过 notify")
        return
    cmd = [sys.executable, str(ui), "--task-root", str(task), "--once", "--force-notify"]
    try:
        subprocess.run(cmd, cwd=str(HERE), check=False, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as e:
        log(f"[W] login_ui: {e}")


def main() -> int:
    ap = argparse.ArgumentParser(description="登录旁路 login_gate")
    ap.add_argument("--task-root", type=Path, required=True)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--apply", action="store_true")
    g.add_argument("--dry-run", action="store_true")
    ap.add_argument("--confirm-ready", action="store_true")
    ap.add_argument("--skip", action="store_true")
    ap.add_argument("--import-cookie", action="store_true")
    ap.add_argument("--import-header", action="store_true")
    ap.add_argument("--notify", action="store_true", help="apply 后对当前要约调 login_ui --once")
    ap.add_argument("--host", type=str, default="")
    ap.add_argument("--file", type=Path, default=None)
    ap.add_argument("--header", type=str, default="", help="Cookie 头: a=1; b=2")
    args = ap.parse_args()

    task = args.task_root.expanduser().resolve()
    if not task.is_dir():
        log(f"[E] 不是目录: {task}")
        return 2

    cfg = load_cfg(task)

    if args.confirm_ready:
        if not args.host:
            log("[E] --confirm-ready 需要 --host")
            return 2
        return cmd_confirm_ready(task, args.host, cfg)
    if args.skip:
        if not args.host:
            log("[E] --skip 需要 --host")
            return 2
        return cmd_skip(task, args.host, cfg)
    if args.import_cookie:
        if not args.host or not args.file:
            log("[E] --import-cookie 需要 --host 与 --file")
            return 2
        return cmd_import_cookie(task, args.host, args.file, cfg)
    if args.import_header:
        if not args.host or not args.header:
            log("[E] --import-header 需要 --host 与 --header")
            return 2
        return cmd_import_header(task, args.host, args.header, cfg)

    apply = bool(args.apply) and not args.dry_run
    # default dry-run if neither flag (safe)
    if not args.apply and not args.dry_run:
        apply = False
        log("[i] 默认 dry-run；写盘请加 --apply")

    rep, code = run_gate(task, apply, cfg)
    log(
        f"[+] login_gate apply={apply} offer={rep.offered} ready={rep.readied} "
        f"timeout={rep.timeouts} auth_spawn={rep.auth_spawn}"
    )
    if apply and (args.notify or int(cfg.get("notify_on_offer") or 0)):
        maybe_notify_ui(task, rep, force=bool(args.notify))
    return code


if __name__ == "__main__":
    sys.exit(main())
