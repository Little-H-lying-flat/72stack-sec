#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""evolve_apply.py — 归档 proposal；安全档可自动追加盲区问句

人审（dispatch_bias / report_checklist / done_fix / hunt-iter）:
  python evolve_apply.py --task-root DIR --list
  python evolve_apply.py --task-root DIR --approve prop_xxx
  python evolve_apply.py --task-root DIR --apply --id prop_xxx

安全自动（evolve_hook 默认调用；不改 rules / SKILL / 短表 / 调度）:
  python evolve_apply.py --task-root DIR --auto-safe
  python evolve_apply.py --task-root DIR --auto-safe --dry-run
  python evolve_apply.py --task-root DIR --auto-safe --no-git

--auto-safe 只处理 pending 的 blindspot_candidate / probe_recipe:
  - 问句追加 知识库/semantic-blindspots.auto.md（去重、禁实值）
  - probe_recipe 另写入任务根 进化/auto_probe_recipes.md
  - 永不写 ~/.grok/rules、SKILL.md、主控调度、线程必读、打穿短表、semantic-blindspots.md 主表
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL_ROOT = HERE.parent
MAIN_MD = SKILL_ROOT / "知识库" / "semantic-blindspots.md"
AUTO_MD = SKILL_ROOT / "知识库" / "semantic-blindspots.auto.md"

SAFE_KINDS = frozenset({"blindspot_candidate", "probe_recipe"})
FORBIDDEN_TARGET = re.compile(
    r"hunt-iter|~/?\.grok/rules|主控调度|线程必读|SKILL\.md|打穿短表",
    re.I,
)
UNSAFE = re.compile(
    r"(set-cookie|authorization\s*:|bearer\s+[a-z0-9_\-\.]{16,}"
    r"|password\s*[:=]|cticket\s*[:=]|p00001"
    r"|eyj[a-z0-9_\-]{20,}|-----begin |"
    r"sk-[a-z0-9]{10,}|api[_-]?key\s*[:=])",
    re.I,
)
TOKENISH = re.compile(r"(?<![A-Za-z0-9])[A-Za-z0-9_\-]{28,}(?![A-Za-z0-9])")
Q_LINE = re.compile(r"^[-*]\s+(.+)$")

FAIL_MODE_Q = {
    "http_405": "GET 被 WAF 405 时，同 path POST 空包是否仍抠到 Controller？id 从会话取还是信客户端？",
    "empty_shell": "空壳/目录页是否只挡 SPA，正文 API 仍匿名可读？",
    "waf_family": "同皮 sibling 的 WAF 闸是否等于应用鉴权？`.json`/`.do` 后缀是否漏挂？",
}

AUTO_HEADER = """# 语义盲区 · 自动追加层

> 由 `evolve_apply --auto-safe` **只追加、不删、不改假点/算成门槛**。
> **禁止**本脚本改 `~/.grok/rules`、`SKILL.md`、`主控调度.md`、`线程必读.md`、`打穿短表.md`、主表 `semantic-blindspots.md`。
> 主控开 suspects：本文件 + `semantic-blindspots.md` 一起扫。
> 去重按规范化语义疑问。人可以把稳定问句提升进主表（人写主表，机器不删本层）。

## 高频问句（自动）

## 回灌日志（自动）

| 日期 | 类型 | 业务·栈 | 语义疑问（应问而未问清） | 对象形态 | 根因标签 | 回灌动作 | 任务指针 |
|------|------|---------|--------------------------|----------|----------|----------|----------|
"""


def now_local() -> datetime:
    return datetime.now(timezone.utc).astimezone()


def load_meta(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_meta(path: Path, meta: dict) -> None:
    path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def list_props(prop_dir: Path) -> list[Path]:
    return sorted(prop_dir.glob("prop_*.json"))


def resolve_prop(prop_dir: Path, pid: str) -> Path | None:
    jp = prop_dir / f"{pid}.json"
    if jp.is_file():
        return jp
    cands = list(prop_dir.glob(f"{pid}*.json"))
    return cands[0] if cands else None


def cell(s: str, n: int = 180) -> str:
    s = re.sub(r"\s+", " ", (s or "").strip()).replace("|", "／")
    return s if len(s) <= n else s[: n - 1] + "…"


def norm_q(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"[，。？?、；;：:\-—_·`\"'“”‘’（）()【】\[\]<>]", "", s)
    return s


def looks_unsafe(s: str) -> bool:
    if not s or len(s) > 240:
        return True
    if UNSAFE.search(s):
        return True
    if TOKENISH.search(s):
        return True
    if "cookie" in s.lower() and re.search(r"(cookie\s*[:=]|cookie\s*是)", s, re.I):
        return True
    return False


def extract_questions(md: str) -> list[str]:
    qs: list[str] = []
    in_section = False
    for raw in (md or "").splitlines():
        line = raw.strip()
        if "建议语义疑问" in line:
            in_section = True
            continue
        if not in_section:
            continue
        if line.startswith("#") or line.startswith("win_patterns") or line.startswith("### "):
            break
        m = Q_LINE.match(line)
        if m:
            qs.append(m.group(1).strip())
            continue
        if not line:
            continue
        if qs:
            break
    return qs


def host_from_title(title: str) -> str:
    t = (title or "").strip()
    if "·" in t:
        t = t.split("·")[-1].strip()
    return cell(t, 40)


def existing_questions(*paths: Path) -> set[str]:
    found: set[str] = set()
    for p in paths:
        if not p.is_file():
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            s = line.strip()
            if s.startswith("- ") and ("？" in s or "?" in s):
                found.add(norm_q(s[2:]))
                continue
            if s.startswith("|") and s.count("|") >= 5:
                cols = [c.strip() for c in s.split("|")]
                if len(cols) > 4 and ("？" in cols[4] or "?" in cols[4]):
                    found.add(norm_q(cols[4]))
    found.discard("")
    return found


@contextmanager
def dir_lock(path: Path, timeout: float = 12.0):
    lock = path.with_name(path.name + ".lock")
    start = time.time()
    while True:
        try:
            lock.mkdir()
            break
        except FileExistsError:
            if time.time() - start > timeout:
                raise TimeoutError(f"lock timeout {lock}")
            time.sleep(0.15)
    try:
        yield
    finally:
        try:
            lock.rmdir()
        except OSError:
            pass


def ensure_auto_md() -> None:
    if not AUTO_MD.is_file():
        AUTO_MD.parent.mkdir(parents=True, exist_ok=True)
        AUTO_MD.write_text(AUTO_HEADER, encoding="utf-8")


def append_faq(question: str) -> bool:
    ensure_auto_md()
    text = AUTO_MD.read_text(encoding="utf-8")
    marker = "## 回灌日志（自动）"
    if marker not in text:
        text = text.rstrip() + f"\n\n- {question}\n\n{marker}\n"
        AUTO_MD.write_text(text, encoding="utf-8")
        return True
    faq, rest = text.split(marker, 1)
    if norm_q(question) in {norm_q(x[2:]) for x in faq.splitlines() if x.strip().startswith("- ")}:
        return False
    if not faq.endswith("\n"):
        faq += "\n"
    AUTO_MD.write_text(faq + f"- {question}\n\n" + marker + rest, encoding="utf-8")
    return True


def append_row(
    *,
    kind_type: str,
    biz: str,
    question: str,
    tag: str,
    task: str,
) -> None:
    ensure_auto_md()
    date = now_local().strftime("%Y-%m-%d")
    row = (
        f"| {date} | {cell(kind_type, 8)} | {cell(biz, 40)} | {cell(question, 180)} "
        f"| — | {cell(tag, 40)} | 自动追加（待主控引用 suspects） | {cell(task, 60)} |\n"
    )
    with AUTO_MD.open("a", encoding="utf-8") as f:
        f.write(row)


def git_commit_auto(msg: str) -> str:
    rel = "知识库/semantic-blindspots.auto.md"
    try:
        subprocess.run(
            ["git", "add", "--", rel],
            cwd=str(SKILL_ROOT),
            check=True,
            capture_output=True,
            text=True,
        )
        staged = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--", rel],
            cwd=str(SKILL_ROOT),
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if not staged:
            return "git: nothing to commit"
        r = subprocess.run(
            ["git", "commit", "-m", msg],
            cwd=str(SKILL_ROOT),
            capture_output=True,
            text=True,
        )
        if r.returncode != 0:
            subprocess.run(
                ["git", "reset", "-q", "HEAD", "--", rel],
                cwd=str(SKILL_ROOT),
                capture_output=True,
            )
            return f"git: commit skipped ({(r.stderr or r.stdout).strip()[:180]})"
        return "git: committed " + rel
    except Exception as e:
        return f"git: skipped ({e})"


def archive_auto(applied_dir: Path, jp: Path, md: Path, meta: dict, note: str) -> None:
    applied_dir.mkdir(parents=True, exist_ok=True)
    stamp = now_local().strftime("%Y%m%d_%H%M%S")
    pid = meta.get("id", jp.stem)
    if md.is_file():
        shutil.copy2(md, applied_dir / f"{stamp}_{md.name}")
    shutil.copy2(jp, applied_dir / f"{stamp}_{jp.name}")
    hint = applied_dir / f"{stamp}_{pid}_auto_hint.txt"
    hint.write_text(
        f"proposal: {pid}\n"
        f"title: {meta.get('title')}\n"
        f"kind: {meta.get('kind')}\n"
        f"status: {meta.get('status')}\n"
        f"note: {note}\n"
        f"auto_file: 知识库/semantic-blindspots.auto.md\n"
        "人工仍须: suspects 头引用问句；covered 过回灌门闩。"
        "禁止把本文件当改 rules/短表/调度的许可。\n",
        encoding="utf-8",
    )


def auto_safe(task_root: Path, *, dry_run: bool, do_git: bool) -> int:
    evo = task_root / "进化"
    prop_dir = evo / "proposals"
    applied_dir = evo / "applied"
    if not prop_dir.is_dir():
        print(f"ERROR: no proposals dir {prop_dir}", file=sys.stderr)
        return 2

    task_name = task_root.name
    n_appended = 0
    n_faq = 0
    n_dup = 0
    n_skip = 0
    n_recipe = 0
    wrote_auto = False

    pending = [p for p in list_props(prop_dir) if load_meta(p).get("status") == "pending"]
    if not pending:
        print("# AUTO_SAFE nothing pending")
        return 0

    with dir_lock(AUTO_MD):
        known = existing_questions(MAIN_MD, AUTO_MD)
        for jp in pending:
            meta = load_meta(jp)
            pid = meta.get("id", jp.stem)
            kind = meta.get("kind") or ""
            title = meta.get("title") or ""
            target = meta.get("merge_target") or ""
            md_path = prop_dir / f"{jp.stem}.md"
            if not md_path.is_file():
                md_path = prop_dir / f"{pid}.md"
            body = md_path.read_text(encoding="utf-8", errors="replace") if md_path.is_file() else ""

            def skip(reason: str) -> None:
                nonlocal n_skip
                n_skip += 1
                print(f"HUMAN {pid}  {kind}  {reason}")

            if kind not in SAFE_KINDS:
                skip("kind 须人审")
                continue
            if FORBIDDEN_TARGET.search(target) or "任务级重复根因" in title:
                skip("立法/短表/hunt-iter 须人审")
                continue

            qs = extract_questions(body)
            if kind == "probe_recipe":
                stuck = ""
                for line in body.splitlines():
                    if line.strip().startswith("卡住对照"):
                        stuck = line.split("：", 1)[-1].strip().strip("`")
                        break
                fails = re.findall(r"`([^`]+)`", body)
                for fm, q in FAIL_MODE_Q.items():
                    if fm in body or fm in fails:
                        qs.append(q)
                if dry_run:
                    print(f"DRY   {pid}  probe_recipe  qs={len(qs)}")
                    continue
                rec = evo / "auto_probe_recipes.md"
                rec.parent.mkdir(parents=True, exist_ok=True)
                block = (
                    f"## {now_local().strftime('%Y-%m-%d')} `{host_from_title(title)}` `{pid}`\n\n"
                    f"- 卡住对照: {cell(stuck, 200) or '—'}\n"
                    f"- 顺序: anon_probe_alive → method_swap → suffix_probe；盲区库问句 + leftover sibling\n"
                    f"- 禁扫描器全站喷；不改红线\n\n"
                )
                if not rec.is_file():
                    rec.write_text(
                        "# 卡住换路 · 任务内自动层\n\n"
                        "> evolve_apply --auto-safe 只追加。不进短表/rules。\n\n",
                        encoding="utf-8",
                    )
                rec.write_text(rec.read_text(encoding="utf-8") + block, encoding="utf-8")
                n_recipe += 1

            safe_qs = []
            for q in qs:
                if looks_unsafe(q):
                    print(f"UNSAFE {pid}  drop: {q[:80]}")
                    continue
                safe_qs.append(q)
            if kind == "blindspot_candidate" and not safe_qs:
                skip("无可用语义疑问")
                continue

            new_qs = []
            for q in safe_qs:
                k = norm_q(q)
                if not k or k in known:
                    n_dup += 1
                    continue
                known.add(k)
                new_qs.append(q)

            if dry_run:
                print(f"DRY   {pid}  {kind}  new={len(new_qs)} dup={len(safe_qs) - len(new_qs)}")
                continue

            host = host_from_title(title)
            row_type = "命中" if ("高危" in title or "中危" in title) else ("卡住" if kind == "probe_recipe" else "命中")
            tag = "自动/语义疑问" if kind == "blindspot_candidate" else "自动/换路"
            for q in new_qs:
                append_row(
                    kind_type=row_type,
                    biz=host,
                    question=q,
                    tag=tag,
                    task=task_name,
                )
                if append_faq(q):
                    n_faq += 1
                n_appended += 1
                wrote_auto = True

            meta["status"] = "applied_auto"
            meta["applied_ts"] = now_local().isoformat(timespec="seconds")
            meta["auto_note"] = f"new={len(new_qs)} dup_or_skip={len(safe_qs) - len(new_qs)}"
            save_meta(jp, meta)
            archive_auto(applied_dir, jp, md_path, meta, meta["auto_note"])
            print(f"AUTO  {pid}  {kind}  new={len(new_qs)}")

    print(
        f"# AUTO_SAFE appended={n_appended} faq={n_faq} dup={n_dup} "
        f"recipe={n_recipe} human_left={n_skip}  auto={AUTO_MD}"
    )
    print("# auto 行 ≠ suspects 头已引用；covered 门闩不免除")
    if dry_run:
        print("# dry-run: no files written")
        return 0
    if do_git and wrote_auto:
        msg = f"evolve: auto-append {n_appended} blindspot Q from {task_name}"
        print("# " + git_commit_auto(msg))
    return 0


def apply_approved(task_root: Path, args: argparse.Namespace) -> int:
    evo = task_root / "进化"
    prop_dir = evo / "proposals"
    applied_dir = evo / "applied"
    targets: list[Path] = []
    if args.all_approved:
        targets = [p for p in list_props(prop_dir) if load_meta(p).get("status") == "approved"]
    elif args.id:
        jp = resolve_prop(prop_dir, args.id)
        if not jp:
            print(f"ERROR: not found {args.id}", file=sys.stderr)
            return 2
        targets = [jp]
    else:
        args.dry_run = True
        targets = [p for p in list_props(prop_dir) if load_meta(p).get("status") == "approved"]
        if not targets:
            targets = list_props(prop_dir)
            print("no approved; showing all pending as dry-run candidates")

    if not args.apply and not args.dry_run:
        args.dry_run = True

    for jp in targets:
        meta = load_meta(jp)
        pid = meta.get("id", jp.stem)
        md = prop_dir / f"{jp.stem}.md"
        if not md.is_file():
            md = prop_dir / f"{pid}.md"
        status = meta.get("status")
        print(f"--- {pid} status={status} kind={meta.get('kind')} ---")
        print(f"title: {meta.get('title')}")
        print(f"merge_target: {meta.get('merge_target')}")
        if args.dry_run and not args.apply:
            print("dry-run: no copy")
            continue
        if args.apply:
            if status != "approved":
                print(f"SKIP not approved: {pid}")
                continue
            applied_dir.mkdir(parents=True, exist_ok=True)
            stamp = now_local().strftime("%Y%m%d_%H%M%S")
            dest_md = applied_dir / f"{stamp}_{md.name}"
            dest_js = applied_dir / f"{stamp}_{jp.name}"
            if md.is_file():
                shutil.copy2(md, dest_md)
            shutil.copy2(jp, dest_js)
            hint = applied_dir / f"{stamp}_{pid}_merge_hint.txt"
            hint.write_text(
                f"proposal: {pid}\n"
                f"title: {meta.get('title')}\n"
                f"merge_target: {meta.get('merge_target')}\n"
                f"from_episodes: {meta.get('from_episodes')}\n"
                f"copied: {dest_md.name if md.is_file() else 'no-md'}\n\n"
                f"人工下一步:\n"
                f"1. 打开 applied 内 md，润色语义疑问\n"
                f"2. 需要入主表时，手工追加 知识库/semantic-blindspots.md"
                f"（安全档已可能写入 .auto.md）\n"
                f"3. 本站 suspects 头引用问句；covered 前过回灌门闩\n"
                f"4. 禁止把本文件当自动改 rules 的许可\n",
                encoding="utf-8",
            )
            meta["status"] = "applied"
            meta["applied_ts"] = now_local().isoformat(timespec="seconds")
            save_meta(jp, meta)
            print(f"applied → {dest_md if md.is_file() else dest_js}")
            print(f"hint → {hint}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Apply evolution proposals (human archive + auto-safe append)"
    )
    ap.add_argument("--task-root", type=Path, required=True)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--approve", type=str, default=None, help="set status=approved for id")
    ap.add_argument("--reject", type=str, default=None, help="set status=rejected for id")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true", default=False)
    ap.add_argument("--id", type=str, default=None)
    ap.add_argument("--all-approved", action="store_true")
    ap.add_argument(
        "--auto-safe",
        action="store_true",
        help="append safe Q to semantic-blindspots.auto.md; never touch rules/短表",
    )
    ap.add_argument("--no-git", action="store_true", help="do not git-commit the auto layer")
    args = ap.parse_args()

    task_root = args.task_root.resolve()
    evo = task_root / "进化"
    prop_dir = evo / "proposals"
    if not prop_dir.is_dir():
        print(f"ERROR: no proposals dir {prop_dir}", file=sys.stderr)
        return 2

    if args.list:
        for jp in list_props(prop_dir):
            meta = load_meta(jp)
            print(
                f"{meta.get('status', '?'):12} {meta.get('id')}  {meta.get('kind')}  {meta.get('title')}"
            )
        return 0

    if args.approve:
        jp = resolve_prop(prop_dir, args.approve)
        if not jp:
            print(f"ERROR: not found {args.approve}", file=sys.stderr)
            return 2
        meta = load_meta(jp)
        meta["status"] = "approved"
        save_meta(jp, meta)
        print(f"approved {meta['id']}")
        return 0

    if args.reject:
        jp = resolve_prop(prop_dir, args.reject)
        if not jp:
            print(f"ERROR: not found {args.reject}", file=sys.stderr)
            return 2
        meta = load_meta(jp)
        meta["status"] = "rejected"
        save_meta(jp, meta)
        print(f"rejected {meta['id']}")
        return 0

    if args.auto_safe:
        return auto_safe(task_root, dry_run=args.dry_run, do_git=not args.no_git)

    return apply_approved(task_root, args)


if __name__ == "__main__":
    sys.exit(main())
