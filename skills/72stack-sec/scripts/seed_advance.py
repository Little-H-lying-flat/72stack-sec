#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""seed_advance.py — 席空 + 业务 pending 空 → FOFA 续页入库 / 真空下种子

主控或 seat_watchdog --auto-fofa 调用。执行腿禁止。
FOFA 经 ~/.grok/mcp-servers/fofa_MCP/pi_bridge.py（不打印 key）。

用法:
  python seed_advance.py --task-root DIR --dry-run
  python seed_advance.py --task-root DIR --apply
  python seed_advance.py --task-root DIR --apply --force-page 6
  python seed_advance.py --task-root DIR --apply --chain-watchdog

退出码:
  0 = 无动作（条件不满足或真停候选）
  1 = 已翻页有 NEW / 或应下种子 / dry-run 有建议
  2 = 参数/FOFA 桥失败
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
FOFA_DIR = Path.home() / ".grok" / "mcp-servers" / "fofa_MCP"
FOFA_PY = FOFA_DIR / ".venv" / "Scripts" / "python.exe"
FOFA_BRIDGE = FOFA_DIR / "pi_bridge.py"

# 测试/噪音子域（入库 cold 或跳过，不填席）
NOISE_HOST = re.compile(
    r"(\.qa\.|\.tst\.|\.uat\.|\.io\.|\.sup\.io\.|localhost|catch-all|"
    r"\bdev\.|\.dev\.|staging|sandbox|mock|test\d*\.|ceshi|"
    r"flowable\.devops|office-cdn|:\d{4,5}$|"
    r"\bes\d*\.d\.|\.d\.xiaohongshu\.|ns-fe\.io|agar\d*\.io|slither\.io)",
    re.I,
)
CDN_HOST = re.compile(
    r"(cdn|xhscdn|71edge|static|pic\.|img\.|image|oss|cos)",
    re.I,
)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def find_dig(task: Path) -> Path | None:
    for p in sorted(task.iterdir()):
        if p.is_dir() and p.name.endswith("_dig"):
            return p
    return None


def load_json(path: Path, default):
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def save_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_seats_idle(task: Path) -> tuple[int, int]:
    """Return (doing_count, idle_or_empty_count)."""
    p = task / "编排" / "seats.md"
    if not p.is_file():
        return 0, 0
    doing = idle = 0
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip().startswith("|"):
            continue
        parts = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(parts) < 4 or not re.match(r"^\d+$", parts[0]):
            continue
        st = parts[3].lower()
        host = parts[1]
        if st == "doing" and host not in {"—", "-", ""}:
            doing += 1
        else:
            idle += 1
    return doing, idle


def count_biz_pending(task: Path) -> tuple[int, list[str]]:
    arr = task / "编排"
    hosts: list[str] = []
    for fp in sorted(arr.glob("leftover*.md")):
        for line in fp.read_text(encoding="utf-8", errors="replace").splitlines():
            if "pending" not in line.lower() or not line.strip().startswith("|"):
                continue
            parts = [c.strip() for c in line.strip().strip("|").split("|")]
            if not any(p.lower() == "pending" for p in parts):
                continue
            note = " ".join(parts)
            if re.search(r"cdn|只记不派|cold|禁止填席|低优测试", note, re.I):
                continue
            for cell in parts:
                m = re.search(r"([a-zA-Z0-9._-]+\.[a-zA-Z]{2,})", cell)
                if m and "." in m.group(1):
                    h = m.group(1).lower()
                    if h in {"host", "host.domain"}:
                        continue
                    if NOISE_HOST.search(h) or CDN_HOST.search(h):
                        continue
                    hosts.append(h)
                    break
    # unique
    seen = set()
    uniq = []
    for h in hosts:
        if h not in seen:
            seen.add(h)
            uniq.append(h)
    return len(uniq), uniq


def load_covered_known(task: Path) -> set[str]:
    out: set[str] = set()
    dig = find_dig(task)
    if dig:
        for p in dig.iterdir():
            if p.is_dir():
                out.add(p.name.lower())
    cov = task / "资产" / "covered_hosts.txt"
    if cov.is_file():
        for line in cov.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                out.add(re.split(r"\s+#", line)[0].strip().lower())
    # leftover all hosts
    for fp in (task / "编排").glob("leftover*.md"):
        for m in re.finditer(
            r"([a-zA-Z0-9._-]+\.[a-zA-Z]{2,})",
            fp.read_text(encoding="utf-8", errors="replace"),
        ):
            out.add(m.group(1).lower())
    return out


def doing_seed(task: Path) -> str | None:
    q = task / "资产" / "种子队列.md"
    if not q.is_file():
        return None
    for line in q.read_text(encoding="utf-8", errors="replace").splitlines():
        if re.search(r"\|\s*doing\s*\|", line, re.I):
            m = re.search(r"([a-z0-9.-]+\.[a-z]{2,})", line, re.I)
            if m:
                return m.group(1).lower()
    return None


def next_pending_seed(task: Path) -> str | None:
    q = task / "资产" / "种子队列.md"
    if not q.is_file():
        return None
    for line in q.read_text(encoding="utf-8", errors="replace").splitlines():
        if re.search(r"\|\s*pending\s*\|", line, re.I) and not re.search(
            r"\|\s*cold\s*\|", line, re.I
        ):
            if re.search(r"cdn|cold|不深挖", line, re.I):
                continue
            m = re.search(r"([a-z0-9.-]+\.[a-z]{2,})", line, re.I)
            if m:
                return m.group(1).lower()
    return None


def run_fofa(domain: str, page: int) -> dict:
    if not FOFA_PY.is_file() or not FOFA_BRIDGE.is_file():
        return {"ok": False, "error": "fofa_bridge_missing", "path": str(FOFA_DIR)}
    cmd = [
        str(FOFA_PY),
        str(FOFA_BRIDGE),
        "search",
        "--domain",
        domain,
        "--page",
        str(page),
        "--status-code",
        "200",
    ]
    print("+", " ".join(cmd[:2]), "search", f"--domain {domain} --page {page}", flush=True)
    proc = subprocess.run(
        cmd,
        cwd=str(FOFA_DIR),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0 and not proc.stdout.strip():
        return {
            "ok": False,
            "error": "fofa_exit",
            "code": proc.returncode,
            "stderr": (proc.stderr or "")[:300],
        }
    try:
        return json.loads(proc.stdout.strip().splitlines()[-1])
    except json.JSONDecodeError:
        return {"ok": False, "error": "fofa_bad_json", "raw": proc.stdout[:200]}


def extract_hosts(data_field: str | list | None) -> list[str]:
    hosts: list[str] = []
    if data_field is None:
        return hosts
    if isinstance(data_field, list):
        for row in data_field:
            if isinstance(row, dict):
                h = row.get("host") or row.get("hostname") or row.get("name") or ""
            else:
                h = str(row)
            h = re.sub(r"^https?://", "", h).split("/")[0].split(":")[0].lower()
            if h and "." in h:
                hosts.append(h)
        return hosts
    text = str(data_field)
    for m in re.finditer(r"主机名:\s*(\S+)", text):
        h = m.group(1).strip()
        h = re.sub(r"^https?://", "", h).split("/")[0].split(":")[0].lower()
        if h and "." in h:
            hosts.append(h)
    # also bare host lines
    for m in re.finditer(r"\b([a-z0-9][a-z0-9.-]+\.[a-z]{2,})\b", text, re.I):
        h = m.group(1).lower()
        if h not in hosts:
            hosts.append(h)
    return hosts


def classify(host: str, domain: str) -> str:
    """biz | noise | cdn | other."""
    if CDN_HOST.search(host):
        return "cdn"
    if NOISE_HOST.search(host):
        return "noise"
    # must be under seed domain or parent
    if domain not in host and not host.endswith(domain):
        # allow subdomain of domain
        if not host.endswith("." + domain) and host != domain:
            return "other"
    return "biz"


def append_leftover(
    task: Path,
    domain: str,
    page: int,
    biz: list[str],
    noise: list[str],
) -> Path:
    arr = task / "编排"
    # prefer existing leftover for domain
    cands = list(arr.glob(f"leftover*{domain}*.md")) or list(arr.glob("leftover*.md"))
    path = cands[0] if cands else arr / f"leftover_seed1_{domain}.md"
    block = [
        "",
        f"## FOFA auto page={page} · {now_iso()}",
        "",
        f"- query: domain=\"{domain}\" && status_code=200",
        f"- biz_new={len(biz)} noise_skip={len(noise)}",
        "",
        "| host | 入口 | 备注 | 状态 |",
        "|------|------|------|------|",
    ]
    for h in biz:
        block.append(
            f"| {h} | https://{h}/ | FOFA p{page} NEW auto | pending |"
        )
    if noise:
        block.append("")
        block.append(f"<!-- noise skipped p{page}: {', '.join(noise[:30])}{'...' if len(noise)>30 else ''} -->")
    block.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write("\n".join(block))
    return path


def write_next(task: Path, kind: str, detail: str) -> None:
    body = (
        f"NEXT: {kind}\n"
        f"说明: seed_advance {now_iso()} · {detail}\n"
        f"主控: 跑 seat_watchdog --apply 填席；有 batch 则 spawn 4.5\n"
        f"禁止: 空席当收口；执行腿 FOFA\n"
    )
    (task / "编排" / "NEXT.md").write_text(body, encoding="utf-8")


def patch_seed_queue_vacuum(task: Path, domain: str, auto_next: bool) -> str | None:
    """Mark current seed done/vacuum; optionally promote next pending → doing."""
    q = task / "资产" / "种子队列.md"
    if not q.is_file():
        return None
    nxt = next_pending_seed(task)
    text = q.read_text(encoding="utf-8", errors="replace")
    lines = []
    promoted = None
    for line in text.splitlines():
        if domain in line and re.search(r"\bdoing\b", line, re.I):
            line = re.sub(r"\bdoing\b", "done", line, count=1, flags=re.I)
            if "FOFA真空" not in line:
                line = line.rstrip() + " · FOFA真空"
        elif (
            auto_next
            and nxt
            and nxt in line
            and re.search(r"\bpending\b", line, re.I)
            and not re.search(r"\bcold\b", line, re.I)
            and promoted is None
        ):
            line = re.sub(r"\bpending\b", "doing", line, count=1, flags=re.I)
            line = line.rstrip() + " · seed_advance 自动下种子"
            promoted = nxt
        lines.append(line)
    q.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return promoted


def main() -> int:
    ap = argparse.ArgumentParser(description="FOFA page advance when seats idle & pending empty")
    ap.add_argument("--task-root", type=Path, required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force-page", type=int, default=None)
    ap.add_argument("--min-pending", type=int, default=1, help="pending below this triggers advance")
    ap.add_argument("--zero-streak", type=int, default=3, help="consecutive 0-NEW pages → vacuum")
    ap.add_argument("--chain-watchdog", action="store_true", help="after NEW, run seat_watchdog --apply")
    ap.add_argument("--allow-busy", action="store_true", help="advance even if seats doing>0")
    ap.add_argument(
        "--auto-next-seed",
        action="store_true",
        default=True,
        help="vacuum 时种子队列 doing→done、下一 pending→doing（默认开）",
    )
    ap.add_argument("--no-auto-next-seed", action="store_true")
    args = ap.parse_args()
    if args.no_auto_next_seed:
        args.auto_next_seed = False
    if not args.apply:
        args.dry_run = True

    task = args.task_root.resolve()
    if not task.is_dir():
        print("ERROR: bad task-root", file=sys.stderr)
        return 2

    doing_n, idle_n = parse_seats_idle(task)
    pend_n, pend_hosts = count_biz_pending(task)
    domain = doing_seed(task)
    state_path = task / "编排" / "fofa_state.json"
    state = load_json(
        state_path,
        {
            "domain": domain or "",
            "page": 1,
            "zero_new_streak": 0,
            "size": None,
            "last_run": None,
            "vacuum": False,
        },
    )

    print("# SEED_ADVANCE", "APPLY" if args.apply else "DRY-RUN")
    print(f"# seats doing={doing_n} idle={idle_n} biz_pending={pend_n} seed={domain}")

    if domain is None:
        print("# skip: no doing seed in 种子队列")
        return 0

    if doing_n > 0 and not args.allow_busy:
        print("# skip: seats still doing (watchdog first); use --allow-busy to override")
        return 0

    if pend_n >= args.min_pending:
        print(f"# skip: biz pending={pend_n} >= {args.min_pending} (fill seats first)")
        return 0

    if state.get("vacuum") and state.get("domain") == domain and not args.force_page:
        nxt = next_pending_seed(task)
        detail = f"seed={domain} already vacuum; next_seed={nxt or '无'}"
        print("#", detail)
        if args.apply:
            promoted = patch_seed_queue_vacuum(task, domain, auto_next=args.auto_next_seed)
            if promoted:
                state["domain"] = promoted
                state["page"] = 0
                state["zero_new_streak"] = 0
                state["vacuum"] = False
                state["last_run"] = now_iso()
                save_json(state_path, state)
                write_next(task, "补席", detail + f"; 已切换→{promoted}; FOFA p1")
                print(f"# auto switch seed → {promoted}")
                if args.chain_watchdog:
                    subprocess.run(
                        [
                            sys.executable,
                            str(Path(__file__).resolve()),
                            "--task-root",
                            str(task),
                            "--apply",
                            "--force-page",
                            "1",
                            "--allow-busy",
                            "--chain-watchdog",
                        ],
                        cwd=str(HERE),
                        check=False,
                    )
            else:
                write_next(task, "下种子" if nxt else "补席", detail)
        return 1

    # 页码：优先 fofa_state.page + 1；勿被 STATE.md 里过期 page=1 打回
    if args.force_page is not None:
        page = args.force_page
    else:
        base = int(state.get("page") or 0)
        if base <= 0 and state.get("last_run") is None:
            st = task / "编排" / "STATE.md"
            if st.is_file():
                pages = [
                    int(x)
                    for x in re.findall(
                        r"page\s*=\s*(\d+)",
                        st.read_text(encoding="utf-8", errors="replace"),
                        flags=re.I,
                    )
                ]
                if pages:
                    base = max(pages)
        page = max(base, 0) + 1

    print(f"# FOFA domain={domain} page={page}")

    if args.dry_run and not args.apply:
        print(f"# dry-run would fofa_search page={page}")
        print("# pass --apply to call FOFA + write leftover")
        return 1

    result = run_fofa(domain, page)
    if result.get("ok") is False and result.get("error"):
        print("# FOFA fail", result, file=sys.stderr)
        return 2

    raw_hosts = extract_hosts(result.get("data"))
    # unique preserve order
    seen: set[str] = set()
    hosts = []
    for h in raw_hosts:
        if h not in seen:
            seen.add(h)
            hosts.append(h)

    known = load_covered_known(task)
    biz_new: list[str] = []
    noise: list[str] = []
    for h in hosts:
        kind = classify(h, domain)
        if kind != "biz":
            noise.append(h)
            continue
        if h in known or h == domain:
            continue
        # www/main often already dug
        if h in known:
            continue
        biz_new.append(h)

    size = result.get("size")
    count = result.get("count") or len(hosts)
    print(f"# fofa size={size} count={count} parsed={len(hosts)} biz_new={len(biz_new)} noise={len(noise)}")

    zero_streak = int(state.get("zero_new_streak") or 0)
    if len(biz_new) == 0:
        zero_streak += 1
    else:
        zero_streak = 0

    vacuum = zero_streak >= args.zero_streak
    state.update(
        {
            "domain": domain,
            "page": page,
            "zero_new_streak": zero_streak,
            "size": size,
            "last_run": now_iso(),
            "last_biz_new": len(biz_new),
            "vacuum": vacuum,
        }
    )

    if args.apply:
        save_json(state_path, state)
        if biz_new:
            path = append_leftover(task, domain, page, biz_new, noise)
            print(f"# wrote pending +{len(biz_new)} → {path}")
            write_next(
                task,
                "补席",
                f"FOFA p{page} biz_new={len(biz_new)} → leftover; seat_watchdog --apply",
            )
            if args.chain_watchdog:
                wd = HERE / "seat_watchdog.py"
                subprocess.run(
                    [sys.executable, str(wd), "--task-root", str(task), "--apply"],
                    cwd=str(HERE),
                    check=False,
                )
        else:
            detail = f"FOFA p{page} 0 biz NEW streak={zero_streak}/{args.zero_streak}"
            if vacuum:
                nxt = next_pending_seed(task)
                promoted = patch_seed_queue_vacuum(
                    task, domain, auto_next=args.auto_next_seed
                )
                # reset fofa_state for new seed
                if promoted:
                    state["domain"] = promoted
                    state["page"] = 0
                    state["zero_new_streak"] = 0
                    state["vacuum"] = False
                    save_json(state_path, state)
                    write_next(
                        task,
                        "补席",
                        detail
                        + f" vacuum; 已切换种子 {domain}→{promoted}; 再 seed_advance FOFA p1",
                    )
                    print(f"# vacuum → 自动下种子 {domain} → {promoted}")
                    if args.chain_watchdog:
                        # FOFA first page of new seed
                        subprocess.run(
                            [
                                sys.executable,
                                str(Path(__file__).resolve()),
                                "--task-root",
                                str(task),
                                "--apply",
                                "--force-page",
                                "1",
                                "--allow-busy",
                                "--chain-watchdog",
                            ],
                            cwd=str(HERE),
                            check=False,
                        )
                else:
                    write_next(
                        task,
                        "下种子" if nxt else "补席",
                        detail + f" vacuum; next_seed={nxt or '无'}（未自动切）",
                    )
                    print(f"# vacuum → NEXT 下种子 next={nxt}")
            else:
                write_next(task, "补席", detail + " → 再跑 seed_advance 续页")
                print("# 0 NEW → streak++, 继续续页")
        log = task / "编排" / "seed_advance.log"
        with log.open("a", encoding="utf-8") as f:
            f.write(
                f"{now_iso()} page={page} biz_new={len(biz_new)} noise={len(noise)} "
                f"streak={zero_streak} vacuum={vacuum}\n"
            )

    if biz_new or vacuum or zero_streak:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
