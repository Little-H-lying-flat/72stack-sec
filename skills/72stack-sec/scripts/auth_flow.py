#!/usr/bin/env python3
"""auth_flow.py — 主控串行：发码 API → 取码 → 提交 API → 落 cookie（禁 Read 凭据文件）

占位符（body/URL 内，脚本自己替换，不打印真号）:
  {phone} {phone_masked} {email} {email_alias} {name_alias} {code}

用法:
  python auth_flow.py --channel sms --wait 90 \\
    --send-url https://host/api/send --send-data "mobile={phone}&type=1" \\
    --submit-url https://host/api/login --submit-data "mobile={phone}&code={code}" \\
    --save D:\\...\\host\\session.cookie \\
    --accounts D:\\...\\资产\\accounts.md --target host --sid web.api

  python auth_flow.py --channel email --wait 120 \\
    --send-json "{{\\"email\\":\\"{email}\\"}}" --submit-json "{{\\"email\\":\\"{email}\\",\\"code\\":\\"{code}\\"}}" ...

退出码: 0=进号并落盘  1=取码超时/提交失败  2=参数/环境  3=遇盾
stdout: OK 一行（路径+打码账号，无 cookie 实值、无验证码）
线程禁止跑本脚本。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import ssl
import subprocess
import sys
import time
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import HTTPCookieProcessor, HTTPSHandler, Request, build_opener

from _profile import load_profile
from accounts_book import append_row, full_account, login_password

HERE = Path(__file__).resolve().parent
CAPTCHA_RE = re.compile(r"滑块|图形验证|captcha|yoda|geetest|人机校验", re.I)
TOKEN_KEYS = (
    "passToken",
    "passtoken",
    "accessToken",
    "access_token",
    "token",
    "sid",
    "userId",
    "userid",
    "st",
    "web_st",
)


def log(msg: str) -> None:
    print(msg, file=sys.stderr)


def profile_sub(s: str, code: str = "") -> str:
    if not s:
        return s
    p = load_profile()
    email = (p.get("email") or {}) if isinstance(p.get("email"), dict) else {}
    repl = {
        "{phone}": str(p.get("phone") or ""),
        "{phone_masked}": str(p.get("phone_masked") or ""),
        "{email}": str(email.get("address") or ""),
        "{email_alias}": str(p.get("email_alias") or email.get("address") or ""),
        "{name_alias}": str(p.get("name_alias") or ""),
        "{password}": str(p.get("login_password") or ""),
        "{code}": code,
    }
    out = s
    for k, v in repl.items():
        out = out.replace(k, v)
    return out


def masked_account(channel: str) -> str:
    p = load_profile()
    if channel == "email":
        email = (p.get("email") or {}) if isinstance(p.get("email"), dict) else {}
        addr = str(p.get("email_alias") or email.get("address") or "")
        if "@" in addr:
            name, dom = addr.split("@", 1)
            return (name[:2] + "***@" + dom) if name else "***@" + dom
        return "(email)"
    return str(p.get("phone_masked") or "phone_masked")


def parse_body(raw: str | None, as_json: bool) -> tuple[bytes | None, str | None]:
    if not raw:
        return None, None
    if as_json:
        json.loads(raw)  # validate
        return raw.encode("utf-8"), "application/json"
    return urlencode(_split_form(raw)).encode("utf-8"), "application/x-www-form-urlencoded"


def _split_form(raw: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in raw.split("&"):
        if not part:
            continue
        if "=" in part:
            k, v = part.split("=", 1)
        else:
            k, v = part, ""
        out[k] = v
    return out


def is_captcha(body: str, status: int) -> bool:
    if CAPTCHA_RE.search(body or ""):
        return True
    try:
        j = json.loads(body)
    except Exception:
        return False
    if not isinstance(j, dict):
        return False
    code = j.get("result") or j.get("code") or j.get("error_code") or j.get("errorCode")
    try:
        c = int(code)
        if 400001 <= c <= 410999:
            return True
    except (TypeError, ValueError):
        pass
    blob = json.dumps(j, ensure_ascii=False)
    return bool(CAPTCHA_RE.search(blob))


def _token_pairs(data: dict) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    keys_l = {k.lower() for k in TOKEN_KEYS}
    for k, v in data.items():
        if isinstance(v, bool) or v is None:
            continue
        if isinstance(v, int) and v in (0, 1):
            continue
        sv = str(v).strip()
        if sv in ("", "0", "null") or (sv.isdigit() and len(sv) < 8):
            continue
        kl = str(k).lower()
        if kl in keys_l or kl.endswith("_st") or kl.endswith("_at") or "passtoken" in kl:
            out.append((str(k), sv))
    return out


def session_hit(set_cookie: list[str], body: str) -> bool:
    blob = " ".join(set_cookie or []).lower()
    if any(k.lower() in blob for k in ("passtoken", "userid", "session", "sid=", "st=", "token=")):
        if "delete" in blob and "passtoken" in blob:
            return False
        return True
    try:
        j = json.loads(body)
    except Exception:
        return False
    if not isinstance(j, dict):
        return False
    data = j.get("data") if isinstance(j.get("data"), dict) else j
    if not isinstance(data, dict):
        return False
    return bool(_token_pairs(data))


def wait_code(channel: str, wait: int, sender: str | None) -> str:
    if channel == "sms":
        cmd = [sys.executable, str(HERE / "sms_code.py"), "--wait", str(wait)]
        if sender:
            cmd += ["--sender", sender]
    elif channel in ("email", "email-link"):
        cmd = [sys.executable, str(HERE / "email_code.py"), "--wait", str(wait)]
        if channel == "email-link":
            cmd += ["--mode", "link"]
    else:
        log("[E] --channel 只支持 sms / email / email-link")
        sys.exit(2)
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    err = (p.stderr or "").strip()
    if err:
        log(err[-400:])
    if p.returncode != 0:
        sys.exit(p.returncode if p.returncode in (1, 2) else 1)
    code = (p.stdout or "").strip().splitlines()[-1] if p.stdout else ""
    if channel != "email-link" and not (code.isdigit() and 4 <= len(code) <= 8):
        log("[E] 取到的不像验证码")
        sys.exit(1)
    if channel == "email-link" and not code.startswith("http"):
        log("[E] 取到的不像链接")
        sys.exit(1)
    return code


def opener_of():
    ctx = ssl.create_default_context()
    jar = CookieJar()
    return build_opener(HTTPSHandler(context=ctx), HTTPCookieProcessor(jar)), jar


def request(opener, method: str, url: str, data: bytes | None, ctype: str | None, headers: list[str], origin: str | None, referer: str | None):
    h = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN",
        "Connection": "close",
    }
    if ctype:
        h["Content-Type"] = ctype
    if origin:
        h["Origin"] = origin
    if referer:
        h["Referer"] = referer
    for raw in headers or []:
        if ":" in raw:
            k, v = raw.split(":", 1)
            h[k.strip()] = v.strip()
    req = Request(url, data=data, headers=h, method=method.upper())
    try:
        resp = opener.open(req, timeout=25)
        raw = resp.read()
        sc = resp.headers.get_all("Set-Cookie") if hasattr(resp.headers, "get_all") else [resp.headers.get("Set-Cookie")]
        return getattr(resp, "status", 200) or 200, raw, [x for x in (sc or []) if x]
    except HTTPError as e:
        raw = e.read() if e.fp else b""
        sc = []
        if e.headers and hasattr(e.headers, "get_all"):
            sc = [x for x in (e.headers.get_all("Set-Cookie") or []) if x]
        return e.code, raw, sc
    except URLError as e:
        log("[E] 请求失败: " + str(e.reason)[:160])
        sys.exit(1)


def save_netscape(path: Path, jar: CookieJar, host: str, extra: list[tuple[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Netscape HTTP Cookie File", "# generated by auth_flow.py; do not Read into chat"]
    seen = set()
    for c in jar:
        key = (c.domain, c.path, c.name)
        if key in seen:
            continue
        seen.add(key)
        domain = c.domain or host
        flag = "TRUE" if domain.startswith(".") else "FALSE"
        secure = "TRUE" if c.secure else "FALSE"
        expires = str(int(c.expires or 0))
        lines.append(f"{domain}\t{flag}\t{c.path or '/'}\t{secure}\t{expires}\t{c.name}\t{c.value}")
    parsed = urlparse("https://" + host if "://" not in host else host)
    dom = parsed.hostname or host
    for name, val in extra:
        if (dom, "/", name) in seen:
            continue
        lines.append(f"{dom}\tFALSE\t/\tTRUE\t0\t{name}\t{val}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def extra_tokens(body: str) -> list[tuple[str, str]]:
    try:
        j = json.loads(body)
    except Exception:
        return []
    data = j.get("data") if isinstance(j.get("data"), dict) else j
    if not isinstance(data, dict):
        return []
    return _token_pairs(data)


def append_accounts(root: str, target: str, sid: str, cookie_path: str, channel: str, status: str, login_url: str) -> None:
    pwd = "验证码进号" if channel in ("sms", "email", "email-link") else (login_password() or "验证码进号")
    append_row(
        root=root or "",
        host=target,
        account=full_account(channel),
        password=pwd,
        login_url=login_url,
        cookie=cookie_path,
        sid=sid,
        status=status,
        note="auth_flow",
        channel=channel,
    )


def main() -> None:
    os.environ.setdefault("NO_PROXY", "*")
    os.environ.setdefault("no_proxy", "*")
    ap = argparse.ArgumentParser(description="主控串行发码+提交")
    ap.add_argument("--channel", required=True, choices=["sms", "email", "email-link"])
    ap.add_argument("--wait", type=int, default=0)
    ap.add_argument("--sender", default=None)
    ap.add_argument("--send-url", default=None)
    ap.add_argument("--send-data", default=None)
    ap.add_argument("--send-json", default=None)
    ap.add_argument("--submit-url", required=True)
    ap.add_argument("--submit-data", default=None)
    ap.add_argument("--submit-json", default=None)
    ap.add_argument("--method-send", default="POST")
    ap.add_argument("--method-submit", default="POST")
    ap.add_argument("--header", action="append", default=[])
    ap.add_argument("--origin", default=None)
    ap.add_argument("--referer", default=None)
    ap.add_argument("--save", required=True, help="session.cookie 路径")
    ap.add_argument("--accounts", default=None, help="资产/accounts.md（仍兼容；优先 --root）")
    ap.add_argument("--root", default="", help="任务根，用于写 资产/accounts.md + 全局账密本")
    ap.add_argument("--login-url", default="", help="人打开的登录页/进号网址")
    ap.add_argument("--target", default="")
    ap.add_argument("--sid", default="")
    args = ap.parse_args()

    wait = args.wait or (120 if args.channel.startswith("email") else 90)
    save = Path(args.save)
    host = args.target or (urlparse(args.submit_url).hostname or "")

    opener, jar = opener_of()

    if args.send_url:
        raw = args.send_json if args.send_json is not None else args.send_data
        if raw is None:
            log("[E] 有 --send-url 必须带 --send-data 或 --send-json")
            sys.exit(2)
        body, ctype = parse_body(profile_sub(raw), as_json=args.send_json is not None)
        st, raw_b, sc = request(
            opener, args.method_send, profile_sub(args.send_url), body, ctype, args.header, args.origin, args.referer
        )
        text = raw_b.decode("utf-8", "replace")
        if is_captcha(text, st):
            log("[!] 发码口遇盾，pending 标 abandon「需人工过盾」")
            sys.exit(3)
        if st >= 400:
            log(f"[E] 发码 HTTP {st} len={len(raw_b)}")
            sys.exit(1)
        log(f"[i] 发码 HTTP {st} len={len(raw_b)}")

    code = wait_code(args.channel, wait, args.sender)
    log("[i] 已取码（不打印）")

    raw = args.submit_json if args.submit_json is not None else args.submit_data
    if raw is None:
        log("[E] 必须带 --submit-data 或 --submit-json")
        sys.exit(2)
    body, ctype = parse_body(profile_sub(raw, code=code), as_json=args.submit_json is not None)
    st, raw_b, sc = request(
        opener, args.method_submit, profile_sub(args.submit_url, code=code), body, ctype, args.header, args.origin, args.referer
    )
    text = raw_b.decode("utf-8", "replace")
    if is_captcha(text, st):
        log("[!] 提交口遇盾")
        sys.exit(3)
    if not session_hit(sc, text):
        log(f"[E] 提交 HTTP {st} 未见会话字段 len={len(raw_b)}")
        sys.exit(1)

    extra = extra_tokens(text)
    save_netscape(save, jar, host, extra)
    root = args.root
    if not root and args.accounts:
        acc = Path(args.accounts)
        root = str(acc.parent.parent) if acc.parent.name == "资产" else str(acc.parent)
    login_url = args.login_url or (urlparse(args.submit_url).scheme + "://" + (urlparse(args.submit_url).hostname or host))
    append_accounts(root, host or args.target, args.sid, str(save), args.channel, "已进号", login_url)
    print(f"OK\thost={host}\taccount={masked_account(args.channel)}\tcookie={save}")


if __name__ == "__main__":
    main()
