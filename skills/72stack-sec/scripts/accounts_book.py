#!/usr/bin/env python3
"""accounts_book.py — 主控落账密（任务 accounts.md + 全局账密本）

人打开 D:/dsh-72stack-sec/accounts/账密本.md 看网址/账号/密码。
禁止 Read 本文件、账密本、register_profile.json 进对话。
线程禁止跑。

用法:
  python accounts_book.py --append ^
    --root "D:\SRC挖洞\某_SRC挖洞" --host host.example.com ^
    --login-url "https://host.example.com/login" ^
    --account "13800000000" --password "验证码进号" ^
    --channel sms --sid web --cookie "D:\\...\\session.cookie" --note auth_flow
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

TASK_HEAD = (
    "# 账号台账（人可看明文；禁止 Read 进对话）\n\n"
    "| 目标 | 账号 | 密码 | 注册时间 | 状态 | sid/体系 | cookie路径 | 登录网址 | 备注 |\n"
    "|------|------|------|----------|------|----------|------------|----------|------|\n"
)
GLOBAL_HEAD = (
    "# SRC 账密本\n\n"
    "> 人看的。禁止把本文件 Read 进对话 / 贴进报告。\n"
    "> 验证码进号没有独立密码，密码列写「验证码进号」。\n"
    "> 要设登录密码时统一用 `register_profile.json` 的 `login_password`（`{password}` 占位）。\n\n"
    "| 任务根 | 目标 | 账号 | 密码 | 登录网址 | 注册时间 | 状态 | sid/体系 | cookie路径 | 备注 |\n"
    "|--------|------|------|------|----------|----------|------|----------|------------|------|\n"
)


def log(msg: str) -> None:
    print(msg, file=sys.stderr)


def global_book_path() -> Path:
    env = (os.environ.get("DSH_ACCOUNTS_BOOK") or os.environ.get("GROK_ACCOUNTS_BOOK") or "").strip()
    if env:
        return Path(env)
    dsh = Path(r"D:\dsh-72stack-sec\accounts") / "账密本.md"
    if dsh.parent.is_dir():
        return dsh
    return Path.home() / ".grok" / "accounts" / "账密本.md"
def ensure_md(path: Path, header: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.is_file() or path.stat().st_size == 0:
        path.write_text(header.replace("\n", "\r\n"), encoding="utf-8")
        return
    text = path.read_text(encoding="utf-8", errors="replace")
    if "| 登录网址 |" not in text and "| 目标 |" in text:
        # old accounts.md header: inject 登录网址 before 备注
        old = "| 目标 | 账号 | 密码 | 注册时间 | 状态 | sid/体系 | cookie路径 | 备注 |"
        new = "| 目标 | 账号 | 密码 | 注册时间 | 状态 | sid/体系 | cookie路径 | 登录网址 | 备注 |"
        if old in text:
            text = text.replace(old, new, 1)
            text = text.replace(
                "|------|------|------|----------|------|----------|------------|------|",
                "|------|------|------|----------|------|----------|------------|----------|------|",
                1,
            )
            path.write_text(text, encoding="utf-8")


def _pipe_cell(s: str) -> str:
    return (s or "").replace("|", "/").replace("\r", " ").replace("\n", " ").strip()


def append_row(
    *,
    root: str,
    host: str,
    account: str,
    password: str,
    login_url: str,
    cookie: str,
    sid: str = "",
    status: str = "已进号",
    note: str = "",
    channel: str = "",
) -> None:
    now = time.strftime("%Y-%m-%d %H:%M")
    host = _pipe_cell(host)
    account = _pipe_cell(account)
    password = _pipe_cell(password) or "验证码进号"
    login_url = _pipe_cell(login_url)
    cookie = _pipe_cell(cookie)
    sid_cell = f"sid={_pipe_cell(sid)}" if sid else "sid=无"
    note = _pipe_cell(note or channel)
    status = _pipe_cell(status) or "已进号"

    if root:
        acc = Path(root) / "资产" / "accounts.md"
        ensure_md(acc, TASK_HEAD)
        task_row = (
            f"| {host} | {account} | {password} | {now} | {status} | {sid_cell} | {cookie} | {login_url} | {note} |"
        )
        _append_unique(acc, task_row, keys=(host, cookie or account))

    book = global_book_path()
    ensure_md(book, GLOBAL_HEAD)
    root_cell = _pipe_cell(root)
    glob_row = (
        f"| {root_cell} | {host} | {account} | {password} | {login_url} | {now} | {status} | {sid_cell} | {cookie} | {note} |"
    )
    _append_unique(book, glob_row, keys=(host, cookie or account, root_cell))


def _append_unique(path: Path, row: str, keys: tuple[str, ...]) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    host = keys[0] if keys else ""
    extra = keys[1] if len(keys) > 1 else ""
    for line in text.splitlines():
        if host and host in line and extra and extra in line:
            return
    nl = "\r\n" if "\r\n" in text else "\n"
    if not text.endswith("\n"):
        text += nl
    path.write_text(text + row + nl, encoding="utf-8")


def full_account(channel: str) -> str:
    # local import: keep auth_flow able to call us without circular stdin
    from _profile import load_profile

    p = load_profile()
    if channel in ("email", "email-link"):
        email = (p.get("email") or {}) if isinstance(p.get("email"), dict) else {}
        return str(p.get("email_alias") or email.get("address") or "")
    return str(p.get("phone") or p.get("phone_masked") or "")


def login_password() -> str:
    from _profile import load_profile

    p = load_profile()
    return str(p.get("login_password") or "")


def main() -> None:
    ap = argparse.ArgumentParser(description="落账密本（禁进对话）")
    ap.add_argument("--append", action="store_true")
    ap.add_argument("--root", default="")
    ap.add_argument("--host", required=True)
    ap.add_argument("--login-url", default="")
    ap.add_argument("--account", default="")
    ap.add_argument("--password", default="")
    ap.add_argument("--channel", default="")
    ap.add_argument("--sid", default="")
    ap.add_argument("--cookie", default="")
    ap.add_argument("--status", default="已进号")
    ap.add_argument("--note", default="")
    args = ap.parse_args()
    if not args.append:
        log("[E] 只要 --append")
        sys.exit(2)
    account = args.account or (full_account(args.channel) if args.channel else "")
    password = args.password or ("验证码进号" if args.channel in ("sms", "email", "email-link") else login_password() or "验证码进号")
    append_row(
        root=args.root,
        host=args.host,
        account=account,
        password=password,
        login_url=args.login_url,
        cookie=args.cookie,
        sid=args.sid,
        status=args.status,
        note=args.note,
        channel=args.channel,
    )
    print(f"OK\tbook={global_book_path()}\thost={args.host}")


if __name__ == "__main__":
    main()
