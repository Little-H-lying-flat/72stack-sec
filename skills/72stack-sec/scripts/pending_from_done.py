#!/usr/bin/env python3
r"""pending_from_done.py — 扫 DONE_anon.md / 旧 DONE.md 缺号行，upsert 资产/pending_register.md（仅主控跑）

用法:
  python pending_from_done.py --root "D:\SRC挖洞\某_SRC挖洞"
  python pending_from_done.py --root "..." --dry-run

stdout: NEXT / REUSE / NOHTTP / ABANDON 行（无手机号、无 cookie 实值）
退出码: 0=跑完  2=参数错误
线程禁止跑本脚本。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SKIP_DIR = frozenset(
    {"js", "资产", "报告", "node_modules", ".git", "_trash", "tmp", "temp", "__pycache__"}
)
# 缺号只认未登录轨回单；不扫 DONE_auth（登录轨禁止写缺号催新号）
DONE_SCAN = frozenset({"DONE.md", "DONE_anon.md"})

QUE_HEAD = (
    "| host | 发码API(METHOD URL) | 提交API(METHOD URL) | 通道(sms/email) "
    "| sid/体系 | 盾 | 状态(pending/doing/done/abandon) | 备注 |"
)
QUE_SEP = "|------|---------------------|---------------------|------------------|--------|------|--------------------------------|------|"

# 新格式：按「；键=」切字段，允许发码/提交注解括号内再写中文分号
NEW_KIND_RE = re.compile(
    r"缺号\s*[：:]\s*(?P<kind>干净|放弃|无HTTP口)",
    re.I,
)
NEW_FIELD_RE = re.compile(
    r"[；;]\s*(?P<key>发码|提交|通道|sid|盾|原因)\s*=\s*",
    re.I,
)
# 兼容旧调用：无内部；注解时的严格版仍保留
NEW_RE = re.compile(
    r"缺号\s*[：:]\s*(?P<kind>干净|放弃|无HTTP口)"
    r"(?:；|;|,)?\s*发码\s*=\s*(?P<send>[^；;]+)"
    r"(?:；|;|,)?\s*提交\s*=\s*(?P<sub>[^；;]+)"
    r"(?:；|;|,)?\s*通道\s*=\s*(?P<ch>[^；;]+)"
    r"(?:；|;|,)?\s*sid\s*=\s*(?P<sid>[^；;]+)"
    r"(?:；|;|,)?\s*盾\s*=\s*(?P<shield>[^；;]+)"
    r"(?:；|;|,)?\s*原因\s*=\s*(?P<why>.*)",
    re.I,
)
# 旧格式：缺号、注册口=URL / 缺号：注册口=`url`
OLD_RE = re.compile(
    r"缺号[^。\n]{0,40}?(?:注册口|发码口)\s*[=＝]\s*`?(?P<url>https?://[^\s;`]+)`?",
    re.I,
)

STATUSES = ("pending", "doing", "done", "abandon")
N_COLS = 8


def log(msg: str) -> None:
    print(msg, file=sys.stderr)


def walk_done(base: Path, max_depth: int = 5) -> list[Path]:
    out: list[Path] = []
    stack: list[tuple[Path, int]] = [(base, 0)]
    while stack:
        cur, depth = stack.pop()
        try:
            entries = list(cur.iterdir())
        except OSError:
            continue
        for ent in entries:
            if ent.is_file() and ent.name in DONE_SCAN:
                out.append(ent)
                continue
            if not ent.is_dir():
                continue
            if ent.name in SKIP_DIR or ent.name.startswith("."):
                continue
            if depth >= max_depth:
                continue
            stack.append((ent, depth + 1))
    return out


def host_of(done: Path, root: Path) -> str:
    rel = done.relative_to(root)
    parts = rel.parts
    # {dig}/{host}/DONE_anon.md 或 {dig}/{host}/DONE.md
    if len(parts) >= 2:
        return parts[-2]
    return done.parent.name


def host_from_cookie(path: str) -> str:
    if not path:
        return ""
    p = Path(path)
    if p.suffix == ".cookie" or p.name.endswith(".cookie"):
        return p.parent.name
    return ""


def is_http_api(s: str) -> bool:
    """发码/提交必须是 HTTP API，登录/注册页不算干净口。"""
    t = (s or "").strip().strip("`")
    if t in ("", "无"):
        return False
    if re.match(r"(GET|POST|PUT|PATCH|DELETE)\s+https?://", t, re.I):
        return True
    if re.search(r"https?://", t, re.I) and re.search(
        r"(/rest/|/api/|/pass/|/infra/|send\w*code|sms|mobilecode|verifycode)",
        t,
        re.I,
    ):
        return True
    return False


def norm_cell(s: str) -> str:
    t = (s or "").strip().strip("`").strip()
    if t in ("无", "none", "-", "N/A", "n/a", ""):
        return "无"
    return re.sub(r"\s+", " ", t)


def shield_blocks_auto(shield: str) -> bool:
    """仅「挡 auth_flow 本身」的人机盾才禁自动进号。

    滑块/实名/人脸/SSO/IdP/人工过盾 → abandon（挂人工过盾续挖）。
    WSG/签名/图形验证码/schema 校验 → 不拦：自有测试号仍可走 sms/email auth_flow。
    """
    t = (shield or "").strip()
    if not t:
        return False
    if t in ("无", "none", "-", "N/A", "n/a"):
        return False
    if re.match(r"无", t):
        return False
    # 人机/身份墙才禁自动
    if re.search(r"滑块|实名|人脸|SSO|IdP|人工过盾", t, re.I):
        return True
    return False


def parse_new_format(text: str) -> dict | None:
    """解析缺号新格式；字段值可含括号内中文分号。"""
    km = NEW_KIND_RE.search(text)
    if not km:
        return None
    kind = km.group("kind")
    markers = list(NEW_FIELD_RE.finditer(text))
    if not markers:
        return None
    fields: dict[str, str] = {}
    for i, m in enumerate(markers):
        key = m.group("key")
        start = m.end()
        end = markers[i + 1].start() if i + 1 < len(markers) else len(text)
        fields[key] = text[start:end].strip().strip("*").strip()
    # 至少要有发码+提交，否则不算完整新格式（交给 OLD/fallback）
    if "发码" not in fields or "提交" not in fields:
        return None
    send = norm_cell(fields.get("发码", "无"))
    sub = norm_cell(fields.get("提交", "无"))
    ch = norm_cell(fields.get("通道", "无")).lower()
    if ch not in ("sms", "email", "无"):
        ch = "sms" if "sms" in ch else ("email" if "email" in ch else "无")
    sid = norm_cell(fields.get("sid", "无"))
    shield = norm_cell(fields.get("盾", "无"))
    why = (fields.get("原因") or "").strip()
    if kind == "干净" and send == "无" and sub == "无":
        kind = "无HTTP口"
    # 干净口但有盾：保留 kind 语义，队列不自动进号
    if kind == "干净" and shield_blocks_auto(shield):
        st = "abandon"
    elif kind == "干净":
        st = "pending"
    else:
        st = "abandon"
    note = why[:120] if why else ""
    if kind == "干净" and st == "abandon" and shield_blocks_auto(shield):
        note = (("人机盾禁自动进号（滑块/实名/SSO）；" + note) if note else "人机盾禁自动进号（滑块/实名/SSO）")[:120]
    return {
        "kind": kind,
        "send": send,
        "submit": sub,
        "channel": ch,
        "sid": sid,
        "shield": shield,
        "status": st,
        "note": note,
    }


def parse_line(text: str) -> dict | None:
    parsed = parse_new_format(text)
    if parsed:
        return parsed
    m = OLD_RE.search(text)
    if m:
        url = m.group("url").rstrip(")。,，")
        abandon = bool(re.search(r"放弃|滑块|实名|人脸|SSO", text))
        # 登录页当无 HTTP 口，带 /api/ 或 send/register/sms 当干净
        looks_api = bool(re.search(r"/api/|send|sms|register|login\.(do|json)|pass/", url, re.I))
        if abandon and re.search(r"滑块|实名|人脸|SSO", text):
            kind, st = "放弃", "abandon"
        elif not looks_api:
            kind, st = "无HTTP口", "abandon"
        else:
            kind, st = "干净", "pending"
        return {
            "kind": kind,
            "send": url if looks_api else "无",
            "submit": url if looks_api else "无",
            "channel": "sms" if "短信" in text or "sms" in text.lower() else ("email" if "邮" in text else "无"),
            "sid": "无",
            "shield": "滑块" if "滑块" in text else ("SSO" if "SSO" in text or "IdP" in text else "无"),
            "status": st,
            "note": "旧格式 " + text.strip()[:80],
        }
    # 只认「缺号：/缺号:」正式行；忽略「## 缺号行」「- [x] 缺号行」勾选标题
    if re.search(r"缺号\s*[：:]", text):
        return {
            "kind": "放弃",
            "send": "无",
            "submit": "无",
            "channel": "无",
            "sid": "无",
            "shield": "无",
            "status": "abandon",
            "note": text.strip()[:80],
        }
    return None


def cell(s: str) -> str:
    t = (s or "").replace("\r", " ").replace("\n", " ").replace("|", "／").strip()
    t = re.sub(r"\s+", " ", t)
    return t


def parse_register_row(line: str) -> dict | None:
    """8 列；盾/备注里的 | 会撑列。状态只认 STATUSES，找不到则列溢出按 abandon 回收。"""
    cols = [c.strip() for c in line.strip().strip("|").split("|")]
    if len(cols) < 7:
        return None
    host = cols[0]
    if not host or host == "host":
        return None
    idx = None
    for i, c in enumerate(cols):
        if c in STATUSES:
            idx = i
    if idx is None:
        status = "abandon" if len(cols) != N_COLS else "pending"
        shield = cell("／".join(cols[5:-1])) if len(cols) > 6 else cell(cols[5] if len(cols) > 5 else "无")
        note = cell(cols[-1] if len(cols) > 6 else "")
        if len(cols) != N_COLS:
            note = cell((note + " 列溢出已回收").strip())
        send, submit, channel, sid = (cols[1] if len(cols) > 1 else "无",
                                      cols[2] if len(cols) > 2 else "无",
                                      cols[3] if len(cols) > 3 else "无",
                                      cols[4] if len(cols) > 4 else "无")
    else:
        send = cols[1] if idx > 1 else "无"
        submit = cols[2] if idx > 2 else "无"
        channel = cols[3] if idx > 3 else "无"
        sid = cols[4] if idx > 4 else "无"
        shield = "／".join(cols[5:idx]) if idx > 5 else (cols[5] if idx == 6 else "无")
        status = cols[idx]
        note = "／".join(cols[idx + 1 :])
    st = status if status in STATUSES else "pending"
    return {
        "host": host,
        "send": cell(send) or "无",
        "submit": cell(submit) or "无",
        "channel": cell(channel) or "无",
        "sid": cell(sid) or "无",
        "shield": cell(shield) or "无",
        "status": st,
        "note": cell(note),
    }


def read_table(path: Path) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    if not path.is_file():
        return rows
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return rows
    for line in text.splitlines():
        if not line.startswith("|") or line.startswith("| host") or re.match(r"\|[-: ]+\|", line):
            continue
        rec = parse_register_row(line)
        if rec:
            rows[rec["host"]] = rec
    return rows


def write_table(path: Path, rows: dict[str, dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# pending_register（仅主控写；线程只写 DONE_anon 缺号行）",
        "",
        QUE_HEAD,
        QUE_SEP,
    ]
    for host in sorted(rows):
        r = rows[host]
        st = r.get("status") or "pending"
        if st not in STATUSES:
            st = "pending"
        lines.append(
            f"| {cell(host)} | {cell(r.get('send','无')) or '无'} | {cell(r.get('submit','无')) or '无'} | {cell(r.get('channel','无')) or '无'} "
            f"| {cell(r.get('sid','无')) or '无'} | {cell(r.get('shield','无')) or '无'} | {st} | {cell(r.get('note',''))} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_accounts(path: Path) -> list[dict]:
    out: list[dict] = []
    if not path.is_file():
        return out
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return out
    for line in text.splitlines():
        if not line.startswith("|") or "账号" in line or re.match(r"\|[-: ]+\|", line):
            continue
        cols = [c.strip() for c in line.strip("|").split("|")]
        if len(cols) < 5:
            continue
        rec = {
            "target": cols[0],
            "status": cols[4] if len(cols) > 4 else "",
            "sid": "",
            "cookie": "",
            "host": "",
        }
        blob = " | ".join(cols)
        sm = re.search(r"sid\s*=\s*([^\s|;，]+)", blob, re.I)
        if sm:
            rec["sid"] = sm.group(1)
        for c in cols:
            if c.endswith(".cookie") and (":\\" in c or c.startswith("/")):
                rec["cookie"] = c
                rec["host"] = host_from_cookie(c)
            elif (not rec["sid"]) and c and c not in ("无",) and "cookie" not in c.lower() and ":\\" not in c and c.count(".") >= 1 and "http" not in c.lower() and len(c) < 80:
                if re.search(r"(kuaishou|kwai|shop|ad\.|sid)", c, re.I) or c.startswith("kuaishou."):
                    rec["sid"] = c
        out.append(rec)
    return out


def cookie_for(accs: list[dict], host: str, sid: str) -> str:
    host_l = (host or "").strip()
    sid_l = (sid or "").strip()
    for a in accs:
        if a.get("status") in ("放弃", "abandon", "失败"):
            continue
        cookie = a.get("cookie") or ""
        if not cookie:
            continue
        ahost = a.get("host") or host_from_cookie(cookie)
        if host_l and host_l == ahost:
            return cookie
        if sid_l and sid_l not in ("无",) and sid_l == (a.get("sid") or ""):
            return cookie
    return ""


def merge(old: dict | None, new: dict, host: str) -> dict:
    if not old:
        return {"host": host, **new}
    st = old.get("status") or "pending"
    # 已 done/doing 不降级；abandon 遇到新的干净且无盾 API 可翻回 pending
    if (
        new.get("status") == "pending"
        and st == "abandon"
        and is_http_api(new.get("send") or "")
        and not shield_blocks_auto(new.get("shield") or "")
    ):
        st = "pending"
    if st in ("done", "doing") and new.get("status") == "pending":
        st = st
    out = dict(old)
    for k in ("send", "submit", "channel", "sid", "shield", "note"):
        nv = new.get(k)
        if nv and nv != "无":
            out[k] = nv
    out["status"] = st
    out["host"] = host
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="扫 DONE 缺号行 → pending_register")
    ap.add_argument("--root", required=True, help="任务根 D:\\SRC挖洞\\{任务}_SRC挖洞")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verbose", action="store_true", help="把历史 NOHTTP/ABANDON 也打到 stdout")
    args = ap.parse_args()
    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        log("[E] 不是目录: " + str(root))
        sys.exit(2)

    que_path = root / "资产" / "pending_register.md"
    acc_path = root / "资产" / "accounts.md"
    existing = read_table(que_path)
    accs = load_accounts(acc_path)

    n_line = 0
    done_files = walk_done(root)
    anon_parents = {p.parent for p in done_files if p.name == "DONE_anon.md"}
    for done in done_files:
        if done.name == "DONE.md" and done.parent in anon_parents:
            continue
        try:
            text = done.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        host = host_of(done, root)
        for line in text.splitlines():
            if "缺号" not in line:
                continue
            n_line += 1
            rec = parse_line(line)
            if not rec:
                continue
            existing[host] = merge(existing.get(host), rec, host)

    if not args.dry_run:
        write_table(que_path, existing)

    n_next = n_reuse = n_no = n_ab = 0
    seen_cookie: set[str] = set()
    for host, r in sorted(existing.items()):
        st = r.get("status") or "pending"
        sid = r.get("sid") or "无"
        cookie = cookie_for(accs, host, sid)
        if cookie and Path(cookie).parent.joinpath("DONE_auth.md").is_file():
            cookie = ""
        if cookie:
            print(f"REUSE\thost={host}\tsid={sid}\tcookie={cookie}")
            seen_cookie.add(cookie)
            n_reuse += 1
            continue
        if st == "pending" and (
            is_http_api(r.get("send") or "") or is_http_api(r.get("submit") or "")
        ):
            print(
                f"NEXT\thost={host}\tsend={r.get('send')}\tsubmit={r.get('submit')}"
                f"\tchannel={r.get('channel')}\tsid={sid}"
            )
            n_next += 1
            continue
        shield = r.get("shield") or "无"
        if st == "abandon" and r.get("send") in ("", "无") and shield in ("无",):
            n_no += 1
            if args.verbose:
                print(f"NOHTTP\thost={host}\tnote={r.get('note','')[:60]}")
            continue
        if st == "abandon":
            n_ab += 1
            if args.verbose:
                print(f"ABANDON\thost={host}\tshield={shield}\tnote={r.get('note','')[:60]}")

    for a in accs:
        cookie = a.get("cookie") or ""
        if not cookie or cookie in seen_cookie:
            continue
        if a.get("status") in ("放弃", "abandon", "失败"):
            continue
        if Path(cookie).parent.joinpath("DONE_auth.md").is_file():
            continue
        host = a.get("host") or host_from_cookie(cookie) or a.get("target") or ""
        print(f"REUSE\thost={host}\tsid={a.get('sid') or '无'}\tcookie={cookie}")
        seen_cookie.add(cookie)
        n_reuse += 1

    log(
        f"[+] DONE缺号行={n_line} NEXT={n_next} REUSE={n_reuse} NOHTTP={n_no} ABANDON={n_ab} "
        f"队={'dry-run' if args.dry_run else que_path}"
        + ("" if args.verbose else "（NOHTTP/ABANDON 默认不刷 stdout，要看加 --verbose）")
    )
    if n_next + n_reuse == 0:
        log("[i] 无待进号干净 API、无待派登录轨 cookie")


if __name__ == "__main__":
    main()
