#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""login_ui.py — 期2：本机通知 + 弹浏览器 + 自动/半自动取 cookie

人在环。不 OCR、不拖滑块、不替你登录。
默认 --watch 用 Playwright 开专用浏览器：你登录后自动导出 cookie → confirm-ready。
从 编排/login_offer.md / login_jobs 读当前要约。

用法:
  python login_ui.py --task-root DIR --once
  python login_ui.py --task-root DIR --watch
      # 通知 + Playwright 窗口 + 自动侦测 cookie（推荐）
  python login_ui.py --task-root DIR --watch --no-auto-cookie
      # 旧行为：只轮询 cookie 文件 / 手动 import-header
  python login_ui.py --task-root DIR --watch --import-header "a=1; b=2"

退出码: 0=ready/无要约  1=timeout/失败  2=参数  3=用户 skip
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

# Strong session cookies (ByteDance / generic). odin_tt alone is NOT enough (anon also has it).
# Note: open-miniprogram uses suffixes like sessionid_microapp / uid_tt_microapp / sid_tt_microapp.
STRONG_SESSION_NAME = re.compile(
    r"^(sessionid|sessionid_ss|sid_tt|sid_guard|uid_tt|uid_tt_ss|"
    r"passToken|passtoken|web_st|session|PHPSESSID|"
    r"access_token|refresh_token|user_session|account_session|"
    r"sessionid_\w+|sessionid_ss_\w+|sid_tt_\w+|sid_guard_\w+|"
    r"uid_tt_\w+|uid_tt_ss_\w+|sid_ucp_\w+|ssid_ucp_\w+|"
    r"toutiao_sso_user(_ss)?(_\w+)?|sso_uid_tt(_ss)?(_\w+)?)$",
    re.I,
)
# Weak: may appear for guests; only counts when paired with strong
WEAK_SESSION_NAME = re.compile(
    r"^(odin_tt|user_id|userid|uid|sid|ssid|auth_token|login_flag)$",
    re.I,
)
# Noise on login pages — must NOT trigger capture
NOISE_COOKIE_NAME = re.compile(
    r"(csrf|xsrf|monitor|trace|web_id|s_v_web|biz_trace|ttwid|msToken|"
    r"passport_csrf|bd_ticket_guard|_ga|_gid|n_mh|gfdat|SLARUA|"
    r"passport_auth_status|is_staff_user|store-region)",
    re.I,
)
LOGIN_PAGE_HINT = re.compile(r"登录|login|signin|sign-in|passport|auth", re.I)
# Passport / SSO sibling domains (ByteDance login often lands on toutiao.com)
PASSPORT_DOMAIN_EXTRA = (
    "toutiao.com",
    "snssdk.com",
    "ixigua.com",
    "douyin.com",
    "bytedance.com",
    "jinritoutiao.com",
    "iesdouyin.com",
    "oceanengine.com",
    "open-douyin.com",
)

HERE = Path(__file__).resolve().parent


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


def parse_iso(s: str) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def load_offer(task: Path) -> dict[str, Any] | None:
    """Parse current offer from login_offer.md table + jobs fallback."""
    offer_md = task / "编排" / "login_offer.md"
    text = read_text(offer_md)
    if not text or "当前无要约" in text:
        return None
    host = ""
    m = re.search(r"\|\s*host\s*\|\s*`([^`]+)`\s*\|", text, re.I)
    if m:
        host = m.group(1).strip().lower()
    if not host:
        return None

    def cell(key: str) -> str:
        mm = re.search(rf"\|\s*{re.escape(key)}\s*\|\s*(.*?)\s*\|", text, re.I)
        if not mm:
            return ""
        v = mm.group(1).strip()
        v = v.strip("`")
        return v

    login_url = cell("登录 URL")
    cookie_path = cell("cookie 路径")
    deadline = cell("deadline")
    offered_at = cell("offered_at")
    main_job = cell("进号后主业")
    family = cell("同盾族")

    # jobs jsonl enrich
    jobs_p = task / "编排" / "login_jobs.jsonl"
    for line in read_text(jobs_p).splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        if str(d.get("host") or "").lower() != host:
            continue
        if d.get("state") != "offered":
            # offer md may lag; still use if md says host
            pass
        login_url = login_url or str(d.get("login_url") or "")
        cookie_path = cookie_path or str(d.get("cookie_path") or "")
        deadline = deadline or str(d.get("deadline_at") or "")
        offered_at = offered_at or str(d.get("offered_at") or "")
        main_job = main_job or str(d.get("main_job") or "")
        family = family or str(d.get("family") or "")
        break

    if not login_url or login_url.startswith("（"):
        login_url = f"https://{host}/"
    # strip markdown bold leftovers
    deadline = re.sub(r"\*+", "", deadline).strip()

    return {
        "host": host,
        "login_url": login_url,
        "cookie_path": cookie_path,
        "deadline_at": deadline,
        "offered_at": offered_at,
        "main_job": main_job,
        "family": family,
    }


def load_ui_state(task: Path) -> dict[str, Any]:
    p = task / "编排" / "login_ui_state.json"
    if not p.is_file():
        return {}
    try:
        return json.loads(read_text(p))
    except json.JSONDecodeError:
        return {}


def save_ui_state(task: Path, st: dict[str, Any]) -> None:
    write_text(task / "编排" / "login_ui_state.json", json.dumps(st, ensure_ascii=False, indent=2) + "\n")


def windows_toast(title: str, body: str) -> bool:
    """Win10+ toast via PowerShell + WinRT. Soft-fail."""
    # Escape for PowerShell single-quoted strings
    def esc(s: str) -> str:
        return s.replace("'", "''")

    title_e, body_e = esc(title), esc(body)
    ps = f"""
$ErrorActionPreference = 'Stop'
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
$template = @"
<toast>
  <visual>
    <binding template="ToastGeneric">
      <text>{title_e}</text>
      <text>{body_e}</text>
    </binding>
  </visual>
</toast>
"@
$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml($template)
$toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
$notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('72stack-login-lane')
$notifier.Show($toast)
"""
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if r.returncode != 0:
            log(f"[W] toast fail: {(r.stderr or r.stdout or '')[:200]}")
            return False
        return True
    except (OSError, subprocess.TimeoutExpired) as e:
        log(f"[W] toast exception: {e}")
        return False


def open_browser(url: str) -> bool:
    url = (url or "").strip()
    if not url:
        return False
    try:
        # Windows: prefer os.startfile / cmd start for default browser
        if sys.platform.startswith("win"):
            os.startfile(url)  # type: ignore[attr-defined]
            return True
    except OSError:
        pass
    try:
        return bool(webbrowser.open(url, new=2))
    except Exception as e:
        log(f"[W] browser open fail: {e}")
        return False


def cookie_ok(path: Path, min_bytes: int = 20) -> bool:
    try:
        if not path.is_file():
            return False
        # ignore pure comment-only / tiny smoke if user wants — size gate
        data = path.read_text(encoding="utf-8", errors="replace")
        if "login_lane_smoke" in data and "pipeline_test" in data:
            # allow but log
            log("[i] cookie 文件含 smoke 桩标记")
        return path.stat().st_size >= min_bytes
    except OSError:
        return False


def header_to_netscape(host: str, header: str) -> str:
    """Convert 'a=b; c=d' or 'Cookie: a=b' to Netscape cookie file."""
    h = header.strip()
    if h.lower().startswith("cookie:"):
        h = h.split(":", 1)[1].strip()
    domain = host.lower()
    lines = [
        "# Netscape HTTP Cookie File",
        f"# written by login_ui import-header @ {now_iso()}",
        f"# host={domain}",
    ]
    for part in re.split(r";\s*", h):
        part = part.strip()
        if not part or "=" not in part:
            continue
        name, val = part.split("=", 1)
        name, val = name.strip(), val.strip()
        if not name:
            continue
        # domain_specified TRUE, path /, secure FALSE, expires 0 (session)
        lines.append(f"{domain}\tTRUE\t/\tFALSE\t0\t{name}\t{val}")
    lines.append("")
    return "\n".join(lines)


def write_cookie_from_header(path: Path, host: str, header: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_text(path, header_to_netscape(host, header))


def run_confirm_ready(task: Path, host: str) -> int:
    gate = HERE / "login_gate.py"
    cmd = [
        sys.executable,
        str(gate),
        "--task-root",
        str(task),
        "--confirm-ready",
        "--host",
        host,
    ]
    r = subprocess.run(cmd, cwd=str(HERE))
    return int(r.returncode)


def run_skip(task: Path, host: str) -> int:
    gate = HERE / "login_gate.py"
    cmd = [sys.executable, str(gate), "--task-root", str(task), "--skip", "--host", host]
    return int(subprocess.run(cmd, cwd=str(HERE)).returncode)


def kbhit_char() -> str | None:
    """Non-blocking key (Windows)."""
    if not sys.platform.startswith("win"):
        return None
    try:
        import msvcrt

        if msvcrt.kbhit():
            return msvcrt.getwch()
    except Exception:
        return None
    return None


def kbhit_skip() -> bool:
    ch = kbhit_char()
    return ch in ("s", "S") if ch else False


def kbhit_enter_done() -> bool:
    ch = kbhit_char()
    return ch in ("\r", "\n", "d", "D") if ch else False


def playwright_available() -> bool:
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401

        return True
    except Exception:
        return False


def cookies_to_netscape(cookies: list[dict[str, Any]], host: str) -> str:
    """Export FULL cookie jar (all domains). P0: do not filter by host."""
    lines = [
        "# Netscape HTTP Cookie File",
        f"# login_ui full-jar @ {now_iso()}",
        f"# target_host={host}",
        f"# count={len(cookies)}",
    ]
    for c in cookies:
        dom = str(c.get("domain") or host)
        path = str(c.get("path") or "/")
        secure = "TRUE" if c.get("secure") else "FALSE"
        exp = c.get("expires")
        try:
            exp_i = int(exp) if exp and float(exp) > 0 else 0
        except (TypeError, ValueError):
            exp_i = 0
        name = str(c.get("name") or "")
        val = str(c.get("value") or "")
        if not name:
            continue
        include = "TRUE" if dom.startswith(".") else "FALSE"
        lines.append(f"{dom}\t{include}\t{path}\t{secure}\t{exp_i}\t{name}\t{val}")
    lines.append("")
    return "\n".join(lines)


def cookie_header_from_list(cookies: list[dict[str, Any]]) -> str:
    parts = []
    for c in cookies:
        n, v = c.get("name"), c.get("value")
        if n is not None and v is not None:
            parts.append(f"{n}={v}")
    return "; ".join(parts)


def _cookie_domain_related(dom: str, host: str) -> bool:
    """Match host, parent domain, or known passport SSO siblings."""
    dom = (dom or "").lstrip(".").lower()
    base = (host or "").split(":")[0].lower()
    if not dom:
        return True
    if base in dom or dom in base or base.endswith(dom) or dom.endswith(base):
        return True
    parts = base.split(".")
    if len(parts) >= 2 and ".".join(parts[-2:]) in dom:
        return True
    for extra in PASSPORT_DOMAIN_EXTRA:
        if dom == extra or dom.endswith("." + extra) or extra.endswith(dom):
            return True
    return False


def score_login_cookies(cookies: list[dict[str, Any]], host: str) -> tuple[int, str]:
    """Return (score, reason). score>=5 ≈ likely logged in.

    Hard rules (false-ready lessons):
    - csrf / monitor / web_id / ttwid alone → 0
    - odin_tt alone (guest) → 0
    - need ≥1 STRONG session cookie with value length ≥16
    - passport login may set sessionid on .toutiao.com while target is *.bytedance.com
    """
    if not cookies:
        return 0, "empty"
    related = []
    for c in cookies:
        dom = str(c.get("domain") or "")
        if _cookie_domain_related(dom, host):
            related.append(c)
    # Prefer related; if strong sess only on passport sibling, related must include them
    pool = related if related else cookies

    def cname(c: dict[str, Any]) -> str:
        return str(c.get("name") or "")

    def clen(c: dict[str, Any]) -> int:
        return len(str(c.get("value") or ""))

    noise = [c for c in pool if NOISE_COOKIE_NAME.search(cname(c))]
    signal = [c for c in pool if not NOISE_COOKIE_NAME.search(cname(c))]
    strong = [c for c in signal if STRONG_SESSION_NAME.search(cname(c)) and clen(c) >= 16]
    weak = [c for c in signal if WEAK_SESSION_NAME.search(cname(c))]

    if not strong:
        if noise and not signal:
            return 0, f"noise_only={len(noise)}"
        if weak and not strong:
            return 0, f"weak_only={','.join(cname(c) for c in weak[:3])}"
        if signal:
            return 0, f"no_strong_session signal={len(signal)} noise={len(noise)}"
        return 0, "empty_signal"

    score = 5
    reasons = [f"strong={','.join(cname(c) for c in strong[:4])}"]
    if len(strong) >= 2:
        score += 2
        reasons.append("strong_ge2")
    if weak:
        score += 1
        reasons.append(f"weak={','.join(cname(c) for c in weak[:3])}")
    extra = [c for c in signal if c not in strong and c not in weak]
    if len(extra) >= 2:
        score += 1
        reasons.append(f"extra={len(extra)}")
    return score, ",".join(reasons)


def auto_cookie_playwright(
    task: Path,
    offer: dict[str, Any],
    cookie_path: Path,
    deadline: datetime | None,
    poll: float,
    fresh_profile: bool = True,
) -> tuple[bool, str]:
    """Open headed browser; user logs in; auto-export cookies. Returns (ok, msg)."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False, "playwright_not_installed"

    host = offer["host"]
    url = offer["login_url"] or f"https://{host}/"
    profile = task / "编排" / "browser_profiles" / host.replace(":", "_")
    if fresh_profile and profile.exists():
        import shutil

        shutil.rmtree(profile, ignore_errors=True)
        print("AUTO_COOKIE\tfresh_profile\twiped sticky profile (防上次 csrf 残留)")
    profile.mkdir(parents=True, exist_ok=True)

    print(f"AUTO_COOKIE\tplaywright\turl={url}")
    print("AUTO_COOKIE\t请在弹出的 Chromium 窗口里登录/过盾（AI 不操作）")
    print("AUTO_COOKIE\t登录成功后：自动侦测 或 按 D/Enter 立即导出；按 S 跳过")
    windows_toast(
        f"请登录 {host}",
        "在弹出的浏览器窗口完成登录；成功后会自动抓 cookie",
    )

    baseline_score = 0
    stable_hits = 0

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(profile),
            headless=False,
            channel=None,
            viewport={"width": 1280, "height": 900},
            ignore_https_errors=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = context.pages[0] if context.pages else context.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            log(f"[W] goto: {e}")

        # initial cookies as baseline (often empty)
        try:
            baseline_score, _ = score_login_cookies(context.cookies(), host)
        except Exception:
            baseline_score = 0

        ok = False
        msg = "timeout"
        while True:
            ch = kbhit_char()
            if ch in ("s", "S"):
                msg = "user_skip"
                break
            force = ch in ("\r", "\n", "d", "D")

            if deadline and now_local() >= deadline:
                msg = "deadline"
                break

            try:
                cookies = context.cookies()
            except Exception as e:
                log(f"[W] cookies(): {e}")
                cookies = []

            score, reason = score_login_cookies(cookies, host)

            # optional: page still looks like login → refuse auto capture
            on_login_page = False
            try:
                title = page.title() or ""
                cur = page.url or ""
                if LOGIN_PAGE_HINT.search(title) or LOGIN_PAGE_HINT.search(cur):
                    on_login_page = True
            except Exception:
                pass

            if force:
                if score < 5:
                    print(
                        "AUTO_COOKIE\tforce_ignored\t"
                        f"仍无强会话 cookie（可能未登录） score={score} {reason}"
                    )
                    force = False
                    stable_hits = 0
                elif on_login_page:
                    print(
                        "AUTO_COOKIE\tforce_warn\t页面标题/URL 仍像登录页，但已有强会话 cookie，继续导出"
                    )

            # auto path: never capture while clearly on login page without strong cookie (score already 0)
            if on_login_page and score < 5 and not force:
                stable_hits = 0
            elif score >= 5 and score > baseline_score:
                stable_hits += 1
            else:
                stable_hits = 0

            need = 1 if force else 3
            if score >= 5 and stable_hits >= need and cookies:
                # SSO settle: bounce target host so product cookies can attach
                try:
                    settle = offer.get("login_url") or f"https://{host}/"
                    if "toutiao.com" in (page.url or "") or "snssdk.com" in (page.url or ""):
                        print(f"AUTO_COOKIE\tsettle\tgoto {settle}")
                        page.goto(settle, wait_until="domcontentloaded", timeout=30000)
                        time.sleep(1.5)
                        cookies = context.cookies()
                        score, reason = score_login_cookies(cookies, host)
                except Exception as e:
                    log(f"[W] settle goto: {e}")
                cookie_path.parent.mkdir(parents=True, exist_ok=True)
                write_text(cookie_path, cookies_to_netscape(cookies, host))
                # also write header sidecar for debug (no print of values)
                hdr = cookie_header_from_list(cookies)
                meta = {
                    "host": host,
                    "captured_at": now_iso(),
                    "cookie_count": len(cookies),
                    "score": score,
                    "reason": reason,
                    "header_len": len(hdr),
                }
                write_text(
                    cookie_path.with_suffix(".meta.json"),
                    json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
                )
                print(f"AUTO_COOKIE\tcaptured\tcount={len(cookies)}\tscore={score}\t{reason}")
                print(f"AUTO_COOKIE\twrote\t{cookie_path}")
                ok, msg = True, "captured"
                break

            time.sleep(max(0.8, float(poll)))

        try:
            context.close()
        except Exception:
            pass

    return ok, msg


def finish_success(task: Path, host: str, ck: Path) -> int:
    print(f"COOKIE_OK\t{ck}")
    print("PROBE\tconfirm-ready 将跑业务探活（失败不 ready）")
    rc = run_confirm_ready(task, host)
    print(f"CONFIRM\trc={rc}\thost={host}")
    if rc == 0:
        batch = task / "编排" / "_auth_spawn_batch.json"
        if batch.is_file():
            try:
                data = json.loads(read_text(batch))
                seats = data.get("seats") or []
                if seats:
                    print("AUTH_SPAWN\t" + ",".join(s.get("host", "") for s in seats))
            except json.JSONDecodeError:
                pass
        # ready only if shield says ready
        q = read_text(task / "资产" / "人工过盾续挖.md")
        if re.search(rf"\|\s*{re.escape(host)}\s*\|.*\|\s*ready\s*\|", q, re.I):
            print("SUCCESS\tlogin_lane P0：全量 cookie + 探活 PASS → ready → auth batch")
            return 0
        print("WAIT\tcookie 已落但探活未过，请继续登录或检查 编排/login_probe_last.json")
        return 1
    print("FAIL\tconfirm/probe 未通过 — 见 login_probe_last.json")
    return 1


def notify_and_open(
    task: Path,
    offer: dict[str, Any],
    do_notify: bool,
    do_browser: bool,
    auto_hint: bool = False,
) -> None:
    host = offer["host"]
    url = offer["login_url"]
    title = f"login_lane 要约 · {host}"
    body = f"请登录（不占10席）\n{url}\n主业: {offer.get('main_job') or '—'}\ndeadline: {offer.get('deadline_at') or '—'}"
    print(f"OFFER\thost={host}\turl={url}\tcookie={offer.get('cookie_path')}")
    if auto_hint:
        print("HINT\t将打开专用浏览器窗口；你登录后自动抓 cookie（无需手拷 DevTools）")
    else:
        print("HINT\t登录后 cookie 自动侦测，或 --import-header 粘贴 Cookie 头")
    if do_notify:
        ok = windows_toast(title, body[:200])
        print(f"NOTIFY\t{'ok' if ok else 'fail'}")
    if do_browser:
        ok = open_browser(url)
        print(f"BROWSER\t{'ok' if ok else 'fail'}\t{url}")
    st = load_ui_state(task)
    st["last_notified_host"] = host
    st["last_notified_at"] = now_iso()
    st["last_login_url"] = url
    st["last_deadline_at"] = offer.get("deadline_at") or ""
    save_ui_state(task, st)


def main() -> int:
    ap = argparse.ArgumentParser(description="login_lane 本机 UI：通知/弹窗/自动 cookie")
    ap.add_argument("--task-root", type=Path, required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--once", action="store_true", help="通知+开系统浏览器后退出")
    g.add_argument("--watch", action="store_true", help="通知+自动取 cookie 至 deadline")
    ap.add_argument("--no-notify", action="store_true")
    ap.add_argument("--no-browser", action="store_true", help="不开系统默认浏览器（auto-cookie 仍开 Playwright）")
    ap.add_argument(
        "--auto-cookie",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Playwright 专用窗登录并自动导出 cookie（默认开；--no-auto-cookie 关）",
    )
    ap.add_argument("--poll", type=float, default=2.0, help="轮询秒")
    ap.add_argument("--min-cookie-bytes", type=int, default=20)
    ap.add_argument("--import-header", type=str, default="", help="直接写入 Cookie 头并 confirm-ready")
    ap.add_argument("--force-notify", action="store_true", help="即使同 host 已通知过也再弹")
    ap.add_argument(
        "--keep-profile",
        action="store_true",
        help="保留 Playwright 用户目录（默认每次 fresh，避免未登录 csrf 残留）",
    )
    args = ap.parse_args()

    task = args.task_root.expanduser().resolve()
    if not task.is_dir():
        log(f"[E] 不是目录: {task}")
        return 2

    offer = load_offer(task)
    if not offer:
        print("NO_OFFER\t当前无 login_offer")
        return 0

    host = offer["host"]
    ck = Path(offer["cookie_path"]) if offer.get("cookie_path") else None
    if ck is None or str(ck).startswith("{") or not str(ck):
        dig = None
        for p in task.iterdir():
            if p.is_dir() and p.name.endswith("_dig"):
                dig = p
                break
        ck = (dig / host / "session.cookie") if dig else (task / f"{host}.session.cookie")
        offer["cookie_path"] = str(ck)

    # import-header path: write + confirm
    if args.import_header.strip():
        write_cookie_from_header(ck, host, args.import_header)
        print(f"OK\timport-header\t{host}\t{ck}")
        return finish_success(task, host, ck)

    use_auto = bool(args.auto_cookie) and args.watch and playwright_available()
    if args.auto_cookie and args.watch and not playwright_available():
        log("[W] playwright 不可用，回退文件轮询；可: pip install playwright && playwright install chromium")

    st = load_ui_state(task)
    already = (
        not args.force_notify
        and st.get("last_notified_host") == host
        and st.get("last_deadline_at") == (offer.get("deadline_at") or "")
        and st.get("last_notified_at")
    )

    # auto-cookie path: toast only here; Playwright opens its own window
    if not already:
        notify_and_open(
            task,
            offer,
            do_notify=not args.no_notify,
            do_browser=(not args.no_browser) and not use_auto,
            auto_hint=use_auto,
        )
    else:
        print(f"SKIP_NOTIFY\talready notified host={host} (use --force-notify)")
        if not use_auto and not args.no_browser and args.watch:
            open_browser(offer["login_url"])

    if args.once:
        print("ONCE_DONE\t真自动取 cookie 请: login_ui.py --watch（默认 --auto-cookie）")
        return 0

    deadline = parse_iso(offer.get("deadline_at") or "")
    print(f"WATCH\thost={host}\tcookie={ck}\tdeadline={offer.get('deadline_at') or 'none'}")

    if use_auto:
        ok, msg = auto_cookie_playwright(
            task,
            offer,
            ck,
            deadline,
            args.poll,
            fresh_profile=not getattr(args, "keep_profile", False),
        )
        if msg == "user_skip":
            print(f"USER_SKIP\t{host}")
            run_skip(task, host)
            return 3
        if ok and cookie_ok(ck, args.min_cookie_bytes):
            rc = finish_success(task, host, ck)
            if rc == 0:
                return 0
            print(
                "AUTO_COOKIE\tprobe_not_ready\t"
                "已导出全量 cookie 但业务探活未过；可继续在浏览器登录后按 D，或 --import-header 后再 watch"
            )
            # fall through to file poll so user can retry without restart
        else:
            print(f"AUTO_COOKIE\tfail\t{msg}\t回退文件轮询")

    # fallback: poll cookie file
    print("WATCH\t文件轮询模式：把 cookie 写入路径，或另开 --import-header；S=skip")
    while True:
        if kbhit_skip():
            print(f"USER_SKIP\t{host}")
            run_skip(task, host)
            return 3
        if cookie_ok(ck, args.min_cookie_bytes):
            return finish_success(task, host, ck)
        if deadline and now_local() >= deadline:
            print(f"TIMEOUT_LOCAL\t{host}\t超过 deadline，交 login_gate 收尸")
            subprocess.run(
                [sys.executable, str(HERE / "login_gate.py"), "--task-root", str(task), "--apply"],
                cwd=str(HERE),
            )
            return 1
        time.sleep(max(0.5, float(args.poll)))


if __name__ == "__main__":
    sys.exit(main())
