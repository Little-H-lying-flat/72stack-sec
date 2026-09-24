#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""seat_watchdog.py — 假满席收尸 + 空席填 pending + 写出 spawn 批次

主控每回合 / cron 跑。执行腿禁止。
默认 --dry-run；--apply 才写 seats/leftover/prompts/NEXT。

登录旁路（有盾要约 / _auth_spawn_batch）由 login_gate.py 负责，本脚本不管。
主控顺序：先 login_gate --apply，再本脚本 --apply。

用法:
  python seat_watchdog.py --task-root DIR [--dry-run|--apply]
  python seat_watchdog.py --task-root DIR --apply --stall-minutes 45
  python seat_watchdog.py --task-root DIR --apply --set-sid 1=abc --set-sid 2=def
  python seat_watchdog.py --task-root DIR --apply --no-evolve --no-fill

退出码: 0=无待办  1=有收尸或待spawn（或 apply 后仍有待spawn）  2=参数错
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL_ROOT = HERE.parent

CDN_HINT = re.compile(
    r"(cdn|edge|static|pic|img|image|oss|cos|xhscdn|71edge|iqiyipic|qiyipic|tripcdn)",
    re.I,
)
LOGIN_WALL_HINT = re.compile(
    r"(登录墙|SSO|passport|login2|sso-gateway|cas\.|/login\b)",
    re.I,
)
SKIP_FILL_HINT = re.compile(
    r"(cdn|只记不派|cold|图床|第三方|IdP|登录墙填席|禁止.*填席)",
    re.I,
)


@dataclass
class Seat:
    n: int
    host: str
    track: str
    status: str
    sid: str
    note: str
    raw_line: str = ""


@dataclass
class Report:
    reaped: list[str] = field(default_factory=list)
    recycled: list[str] = field(default_factory=list)
    filled: list[str] = field(default_factory=list)
    kept_doing: list[str] = field(default_factory=list)
    prompts: list[dict] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def find_dig_dir(task: Path) -> Path | None:
    for p in sorted(task.iterdir()):
        if p.is_dir() and p.name.endswith("_dig"):
            return p
    return None


def load_covered(task: Path) -> set[str]:
    out: set[str] = set()
    for name in ("covered_hosts.txt", "covered_hosts"):
        p = task / "资产" / name
        if not p.is_file():
            continue
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            host = re.split(r"\s+#", line)[0].strip().lower()
            if host:
                out.add(host)
    return out


def parse_seats(text: str) -> tuple[list[str], list[Seat]]:
    """Return (preamble_lines including header sep, seats)."""
    lines = text.splitlines()
    seats: list[Seat] = []
    preamble: list[str] = []
    header_seen = False
    sep_seen = False
    for line in lines:
        if re.match(r"^\|\s*席\s*\|", line):
            header_seen = True
            preamble.append(line)
            continue
        if header_seen and not sep_seen and re.match(r"^\|\s*-+", line):
            sep_seen = True
            preamble.append(line)
            continue
        if not header_seen or not sep_seen:
            preamble.append(line)
            continue
        if not line.strip().startswith("|"):
            preamble.append(line)
            continue
        parts = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(parts) < 5:
            continue
        try:
            n = int(re.sub(r"\D", "", parts[0]) or "0")
        except ValueError:
            continue
        if n <= 0:
            continue
        host = parts[1].strip()
        track = parts[2].strip() if len(parts) > 2 else "未登录"
        status = parts[3].strip() if len(parts) > 3 else ""
        sid = parts[4].strip() if len(parts) > 4 else ""
        note = parts[5].strip() if len(parts) > 5 else ""
        seats.append(
            Seat(n=n, host=host, track=track, status=status, sid=sid, note=note, raw_line=line)
        )
    return preamble, seats


def render_seats(preamble: list[str], seats: list[Seat], max_seats: int) -> str:
    # ensure seats 1..max_seats
    by_n = {s.n: s for s in seats}
    rows: list[Seat] = []
    for i in range(1, max_seats + 1):
        if i in by_n:
            rows.append(by_n[i])
        else:
            rows.append(Seat(n=i, host="—", track="—", status="idle", sid="—", note=""))
    body = [
        f"| {s.n} | {s.host or '—'} | {s.track or '—'} | {s.status} | {s.sid or '—'} | {s.note} |"
        for s in rows
    ]
    # drop trailing empty preamble junk after table if any duplicated
    pre = "\n".join(preamble).rstrip() + "\n"
    if not any(re.match(r"^\|\s*席\s*\|", ln) for ln in preamble):
        pre = (
            "# 席位\n\n"
            "并行上限 %d。空席合法 != 收口。禁止空 cookie 登录轨。\n"
            "占席只认本表。leftover done != covered。由 seat_watchdog 维护。\n\n"
            "| 席 | host | 轨 | 状态 | sid | 备注 |\n"
            "|----|------|----|------|-----|------|\n"
        ) % max_seats
        return pre + "\n".join(body) + "\n"
    # preamble already has header
    return pre + "\n".join(body) + "\n"


def host_done_path(dig: Path, host: str, track: str) -> Path | None:
    if not host or host in {"—", "-", "空", "idle"}:
        return None
    hd = dig / host
    if not hd.is_dir():
        # try without port
        host2 = host.split(":")[0]
        hd = dig / host2
    if not hd.is_dir():
        return None
    track_l = track or ""
    if "有会话" in track_l or "登录" in track_l and "未登录" not in track_l:
        for name in ("DONE_auth.md", "DONE.md"):
            p = hd / name
            if p.is_file():
                return p
    for name in ("DONE_anon.md", "DONE.md", "DONE_auth.md"):
        p = hd / name
        if p.is_file():
            return p
    return None


def dig_mtime(dig: Path, host: str) -> float | None:
    hd = dig / host.split(":")[0]
    if not hd.is_dir():
        return None
    latest = None
    try:
        for p in hd.rglob("*"):
            if p.is_file():
                m = p.stat().st_mtime
                latest = m if latest is None else max(latest, m)
    except OSError:
        return None
    return latest


def parse_leftover_pending(task: Path) -> list[tuple[str, str]]:
    """Return [(host, note), ...] from leftover*.md pending rows."""
    arr = task / "编排"
    files = sorted(arr.glob("leftover*.md")) if arr.is_dir() else []
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for fp in files:
        text = fp.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            if "pending" not in line.lower():
                continue
            if not line.strip().startswith("|"):
                continue
            parts = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(parts) < 2:
                continue
            # find host-like cell
            host = ""
            for cell in parts:
                m = re.search(r"([a-zA-Z0-9._-]+\.[a-zA-Z]{2,}(?::\d+)?)", cell)
                if m and "." in m.group(1):
                    host = m.group(1).split(":")[0].lower()
                    break
            if not host or host in seen:
                continue
            if host in {"host", "host.domain"}:
                continue
            note = " | ".join(parts[1:4])
            # status cell should be pending
            if not any(p.lower() == "pending" for p in parts):
                continue
            if CDN_HINT.search(host) or SKIP_FILL_HINT.search(note):
                continue
            seen.add(host)
            out.append((host, note[:120]))
    return out


def patch_leftover_status(task: Path, host: str, new_status: str) -> int:
    """Best-effort: change leftover table status cell for host."""
    arr = task / "编排"
    n = 0
    host_l = host.lower()
    for fp in sorted(arr.glob("leftover*.md")):
        text = fp.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        changed = False
        out_lines: list[str] = []
        for line in lines:
            if host_l in line.lower() and line.strip().startswith("|"):
                # replace trailing | doing | or | pending |
                nl = re.sub(
                    r"\|\s*(doing|pending)\s*\|",
                    f"| {new_status} |",
                    line,
                    count=1,
                    flags=re.I,
                )
                # also end cell
                nl = re.sub(
                    r"\|\s*(doing|pending)\s*$",
                    f"| {new_status}",
                    nl,
                    count=1,
                    flags=re.I,
                )
                if nl != line:
                    changed = True
                    n += 1
                out_lines.append(nl)
            else:
                out_lines.append(line)
        if changed:
            fp.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    return n


def seed_name(task: Path) -> str:
    q = task / "资产" / "种子队列.md"
    if q.is_file():
        for line in q.read_text(encoding="utf-8", errors="replace").splitlines():
            if re.search(r"\|\s*doing\s*\|", line, re.I) or "| doing |" in line:
                m = re.search(r"([a-z0-9.-]+\.[a-z]{2,})", line, re.I)
                if m:
                    return m.group(1)
    return "unknown"


def build_prompt(
    task: Path,
    dig: Path,
    seat_n: int,
    host: str,
    track: str,
    note: str,
    seed: str,
) -> str:
    skill = SKILL_ROOT
    short = dig.name
    track_line = track if track and track != "—" else "未登录"
    lock = f"*.{seed}" if seed != "unknown" else "锁面内本种子"
    return f"""本轨={track_line}
host={host}
席={seat_n}
任务根={task}
dig={dig}
种子={seed}
备注={note}

只加载 72stack-sec + src-dig（禁止 relay-runner）。立法认 ~/.grok/rules。读 dig/线程必读.md。知识库/短表：{skill}/知识库/打穿短表.md 只扫开场认法层。一人一轨一站。推理按 high。模型 xai/grok-4.5 + high。

硬规则：
- 禁止 FOFA；禁止换站；禁止发码/注册/登录；禁止 auth_flow/pending_from_done/mark_covered/自跑进化/seat_watchdog；禁止手改 covered_hosts；禁止 logout
- 约束测试红线：真实数据/注入出数≤5 组；禁止写操作/WebShell/扫描器批量/DoS/内网横移/社工；AK/SK/kube 不自行进业务
- CORS 永久不挖、不交 CORS 专篇（可作 XSS/上传升链证据 only）
- 卡住先对照盲区+leftover sibling+短表；优先 anon_probe_alive/method_swap/suffix_probe；DONE 必写 卡住对照=
- JS → js/{host}/anon/；清单 endpoints.md + matrix.md + suspects.md；DONE → {short}/{host}/DONE_anon.md
- 缺号行、带出host=、NEXT∈{{补席|下种子|人工过盾}} 必写
- 做完写 DONE 并停。不要开第二站。

锁面本种子={lock}。对照 leftover 只读 sibling，禁止自己占第二席。

立刻开挖本 host。工作目录=任务根。
"""


def write_prompts(task: Path, prompts: list[dict]) -> None:
    d = task / "编排" / "seat_prompts"
    d.mkdir(parents=True, exist_ok=True)
    # clear old seat_*.txt optional — only overwrite batch
    batch = task / "编排" / "_spawn_batch.json"
    batch.write_text(json.dumps(prompts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for item in prompts:
        n = int(item["seat"])
        host = item["host"]
        safe = re.sub(r"[^\w.-]+", "_", host)[:80]
        (d / f"seat{n:02d}_{safe}.txt").write_text(item["prompt"], encoding="utf-8")


def append_log(task: Path, lines: list[str]) -> None:
    log = task / "编排" / "watchdog.log"
    stamp = now_iso()
    with log.open("a", encoding="utf-8") as f:
        f.write(f"## {stamp}\n")
        for ln in lines:
            f.write(ln + "\n")
        f.write("\n")


def update_next(task: Path, rep: Report) -> None:
    nxt = task / "编排" / "NEXT.md"
    # Preserve login_gate hints (runs before watchdog)
    prev = ""
    try:
        prev = nxt.read_text(encoding="utf-8", errors="replace")
    except OSError:
        prev = ""
    keep: list[str] = []
    for line in prev.splitlines():
        s = line.strip()
        if s.startswith("登录要约:") or s.startswith("auth_spawn:") or s.startswith("login_"):
            keep.append(s)
    offer = task / "编排" / "login_offer.md"
    if offer.is_file() and not any(x.startswith("登录要约:") for x in keep):
        try:
            ot = offer.read_text(encoding="utf-8", errors="replace")
            m = re.search(r"\| host \| `([^`]+)`", ot)
            if m and "当前无要约" not in ot:
                keep.append(f"登录要约: {m.group(1)}（见 编排/login_offer.md；不占 10 席）")
        except OSError:
            pass
    auth_batch = task / "编排" / "_auth_spawn_batch.json"
    if auth_batch.is_file() and not any(x.startswith("auth_spawn:") for x in keep):
        try:
            data = json.loads(auth_batch.read_text(encoding="utf-8", errors="replace"))
            seats = data.get("seats") or []
            if seats:
                hosts = ",".join(str(s.get("host") or "") for s in seats if s.get("host"))
                keep.append(f"auth_spawn: {hosts} → 读 编排/_auth_spawn_batch.json")
        except (OSError, json.JSONDecodeError):
            pass
    body = (
        f"NEXT: 补席\n"
        f"说明: seat_watchdog {now_iso()} reap={len(rep.reaped)} fill={len(rep.filled)} "
        f"recycle={len(rep.recycled)} keep={len(rep.kept_doing)} spawn_batch={len(rep.prompts)}\n"
    )
    if keep:
        body += "\n".join(keep) + "\n"
    body += (
        f"主控: 先 _auth_spawn_batch（有会话旁路）再 _spawn_batch.json；xai/grok-4.5+high spawn_subsession；"
        f"spawn 后 seat_watchdog --set-sid N=sessionId\n"
        f"禁止: 假满席当停机；空 cookie 登录轨；执行腿自跑 watchdog/login_gate；auth_wait 占 seats 1-10\n"
    )
    nxt.write_text(body, encoding="utf-8")


def run_evolve(task: Path) -> None:
    hook = HERE / "evolve_hook.py"
    if not hook.is_file():
        return
    subprocess.run(
        [sys.executable, str(hook), "--task-root", str(task)],
        cwd=str(HERE),
        check=False,
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Seat watchdog: reap DONE, fill pending, write spawn batch")
    ap.add_argument("--task-root", type=Path, required=True)
    ap.add_argument("--apply", action="store_true", help="write seats/leftover/prompts")
    ap.add_argument("--dry-run", action="store_true", help="default if no --apply")
    ap.add_argument("--max-seats", type=int, default=10)
    ap.add_argument("--stall-minutes", type=float, default=45.0)
    ap.add_argument("--no-fill", action="store_true", help="only reap, do not fill")
    ap.add_argument("--no-evolve", action="store_true")
    ap.add_argument(
        "--set-sid",
        action="append",
        default=[],
        help="N=sessionId (can repeat); apply to seats",
    )
    ap.add_argument("--prefer-biz", action="store_true", default=True)
    ap.add_argument(
        "--auto-fofa",
        action="store_true",
        default=True,
        help="apply 后若席空且无业务 pending，链式 seed_advance（默认开）",
    )
    ap.add_argument(
        "--no-auto-fofa",
        action="store_true",
        help="关闭 FOFA 续页链式",
    )
    args = ap.parse_args()
    if not args.apply:
        args.dry_run = True
    if args.no_auto_fofa:
        args.auto_fofa = False

    task = args.task_root.resolve()
    if not task.is_dir():
        print(f"ERROR: task-root missing {task}", file=sys.stderr)
        return 2
    seats_path = task / "编排" / "seats.md"
    if not seats_path.is_file():
        print(f"ERROR: no {seats_path}", file=sys.stderr)
        return 2
    dig = find_dig_dir(task)
    if dig is None:
        print("ERROR: no *_dig under task", file=sys.stderr)
        return 2

    covered = load_covered(task)
    seed = seed_name(task)
    text = seats_path.read_text(encoding="utf-8", errors="replace")
    preamble, seats = parse_seats(text)
    if not seats:
        # empty table — create max seats idle
        seats = [
            Seat(n=i, host="—", track="—", status="idle", sid="—", note="")
            for i in range(1, args.max_seats + 1)
        ]

    # apply set-sid first
    sid_map: dict[int, str] = {}
    for item in args.set_sid:
        if "=" not in item:
            continue
        a, b = item.split("=", 1)
        try:
            sid_map[int(a)] = b.strip()
        except ValueError:
            continue

    rep = Report()
    stall_sec = args.stall_minutes * 60.0
    now = time.time()

    # index by seat number
    by_n: dict[int, Seat] = {s.n: s for s in seats}
    for i in range(1, args.max_seats + 1):
        if i not in by_n:
            by_n[i] = Seat(n=i, host="—", track="—", status="idle", sid="—", note="")

    for n, s in list(by_n.items()):
        if n in sid_map:
            s.sid = sid_map[n]
            rep.messages.append(f"SET_SID seat={n} sid={sid_map[n]}")

        st = (s.status or "").lower()
        host = (s.host or "").strip()
        if host in {"—", "-", ""}:
            s.status = "idle"
            continue

        if st in {"done", "idle", "empty"}:
            if st == "done":
                # free for refill
                s.status = "idle"
                s.host = "—"
                s.track = "—"
                s.sid = "—"
                s.note = "watchdog freed"
            continue

        if st != "doing" and "doing" not in st:
            continue

        # doing
        done_p = host_done_path(dig, host, s.track)
        if done_p:
            rep.reaped.append(f"{n}:{host}")
            rep.messages.append(f"REAP seat={n} host={host} via {done_p.name}")
            s.status = "idle"
            s.host = "—"
            s.track = "—"
            s.sid = "—"
            s.note = f"reaped {done_p.name}"
            if args.apply:
                patch_leftover_status(task, host, "done")
            continue

        mt = dig_mtime(dig, host)
        if mt is not None and (now - mt) > stall_sec:
            rep.recycled.append(f"{n}:{host}")
            rep.messages.append(
                f"RECYCLE_CAND seat={n} host={host} age_min={(now - mt) / 60:.1f}"
            )
            # free seat for refill; leftover stays pending/doing for re-queue
            s.status = "idle"
            s.host = "—"
            s.track = "—"
            s.sid = "—"
            s.note = f"stall recycle >{args.stall_minutes:.0f}m"
            if args.apply:
                patch_leftover_status(task, host, "pending")
            continue

        rep.kept_doing.append(f"{n}:{host}")

    # fill idle seats
    pending = parse_leftover_pending(task)
    # filter covered / already doing
    active_hosts = {
        (s.host or "").lower()
        for s in by_n.values()
        if (s.status or "").lower() == "doing" and s.host not in {"—", ""}
    }
    fill_q: list[tuple[str, str]] = []
    for host, note in pending:
        if host in covered or host in active_hosts:
            continue
        if args.prefer_biz and LOGIN_WALL_HINT.search(host) and "不拿登录墙" in note:
            continue
        if SKIP_FILL_HINT.search(note):
            continue
        fill_q.append((host, note))

    if not args.no_fill:
        for n in range(1, args.max_seats + 1):
            s = by_n[n]
            if (s.status or "").lower() == "doing" and s.host not in {"—", ""}:
                continue
            if not fill_q:
                s.status = "idle"
                s.host = "—"
                s.track = "—"
                s.sid = "—"
                if not s.note:
                    s.note = "empty"
                continue
            host, note = fill_q.pop(0)
            s.host = host
            s.track = "未登录"
            s.status = "doing"
            s.sid = "—"
            s.note = f"watchdog fill · {note[:60]}"
            rep.filled.append(f"{n}:{host}")
            active_hosts.add(host)
            prompt = build_prompt(task, dig, n, host, "未登录", s.note, seed)
            rep.prompts.append({"seat": n, "host": host, "track": "未登录", "prompt": prompt})
            if args.apply:
                patch_leftover_status(task, host, "doing")
            rep.messages.append(f"FILL seat={n} host={host}")

    # prompts for kept doing with empty sid still need spawn? only new fills
    # also: idle after reap that got filled already in prompts

    new_seats = [by_n[i] for i in range(1, args.max_seats + 1)]
    new_text = render_seats(preamble, new_seats, args.max_seats)

    print("# SEAT_WATCHDOG", "APPLY" if args.apply else "DRY-RUN")
    print(f"# task={task}")
    print(f"# dig={dig} seed={seed}")
    print(f"# reaped={len(rep.reaped)} recycled={len(rep.recycled)} filled={len(rep.filled)} keep_doing={len(rep.kept_doing)}")
    for m in rep.messages:
        print(m)
    if rep.prompts:
        print(f"# spawn_batch={len(rep.prompts)} → 编排/_spawn_batch.json")
        for p in rep.prompts:
            print(f"  SPAWN seat={p['seat']} host={p['host']}")

    if args.apply:
        seats_path.write_text(new_text, encoding="utf-8")
        if rep.prompts:
            write_prompts(task, rep.prompts)
        else:
            # clear batch if nothing to spawn
            batch = task / "编排" / "_spawn_batch.json"
            batch.write_text("[]\n", encoding="utf-8")
        update_next(task, rep)
        append_log(task, rep.messages + [f"reaped={rep.reaped}", f"filled={rep.filled}"])
        if not args.no_evolve and (rep.reaped or rep.filled):
            run_evolve(task)
        print(f"# wrote {seats_path}")

        # 本轮填不满空席（pending 空）→ FOFA 续页 / 真空下种子
        # 不要求 10 席全 idle：有 1 腿在跑也要给其余空席补给
        if args.auto_fofa and not args.no_fill and not rep.filled and not rep.prompts:
            idle_n = sum(
                1
                for s in new_seats
                if (s.status or "").lower() != "doing" or s.host in {"—", "", "-"}
            )
            if idle_n > 0:
                adv = HERE / "seed_advance.py"
                if adv.is_file():
                    print("# chain seed_advance --apply --chain-watchdog --allow-busy")
                    code = subprocess.run(
                        [
                            sys.executable,
                            str(adv),
                            "--task-root",
                            str(task),
                            "--apply",
                            "--chain-watchdog",
                            "--allow-busy",
                        ],
                        cwd=str(HERE),
                    ).returncode
                    batch = task / "编排" / "_spawn_batch.json"
                    if batch.is_file():
                        try:
                            bj = json.loads(batch.read_text(encoding="utf-8"))
                            if bj:
                                rep.prompts = bj
                                print(f"# after advance spawn_batch={len(bj)}")
                        except json.JSONDecodeError:
                            pass
                    if code not in (0, 1):
                        print(f"# seed_advance exit {code}", file=sys.stderr)
    else:
        print("# dry-run: pass --apply to write seats/prompts/NEXT")

    # 1 = 主控应 spawn 或至少看过本回合动作；0 = 无事
    if rep.prompts:
        return 1
    if rep.reaped or rep.recycled or rep.filled:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
