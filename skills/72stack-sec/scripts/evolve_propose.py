#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""evolve_propose.py — 从 episodes.jsonl 生成待审 proposals（不改盲区库/rules）

用法:
  python evolve_propose.py --task-root DIR
  python evolve_propose.py --task-root DIR --since-ids-file 进化/.last_propose_ids

退出码: 0=ok  2=参数错误
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

CDN_HINT = re.compile(
    r"(file\.|dimg|webresource|static\.|tripcdn|cdn\.|images\d*\.|pic\.)",
    re.I,
)


def now_stamp() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y%m%d_%H%M%S")


def load_episodes(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    eps: list[dict] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            eps.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return eps


def write_proposal(
    prop_dir: Path,
    kind: str,
    title: str,
    body: str,
    episodes: list[str],
    merge_target: str,
) -> Path:
    pid = f"prop_{now_stamp()}_{kind[:6]}_{abs(hash(title)) % 10000:04d}"
    # stabilize hash across runs slightly by title+kind only already
    meta = {
        "id": pid,
        "kind": kind,
        "status": "pending",
        "from_episodes": episodes,
        "title": title,
        "merge_target": merge_target,
        "ts": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    }
    md = prop_dir / f"{pid}.md"
    js = prop_dir / f"{pid}.json"
    md.write_text(
        f"# {title}\n\n"
        f"- id: `{pid}`\n"
        f"- kind: `{kind}`\n"
        f"- status: pending（改 json 为 approved 后可 apply）\n"
        f"- merge_target: {merge_target}\n"
        f"- from_episodes: {', '.join(episodes) or '—'}\n\n"
        f"## 提案正文\n\n{body}\n\n"
        f"## 禁止\n\n"
        f"- 不写利用步骤 / PoC / Cookie / 真实 PII\n"
        f"- 不自动放宽红线；CORS 不单独成洞\n"
        f"- 执行腿禁止自行 merge\n",
        encoding="utf-8",
    )
    js.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return md


def propose_from_episode(ep: dict, prop_dir: Path) -> list[Path]:
    written: list[Path] = []
    eid = ep.get("id", "")
    host = ep.get("host", "")
    outcome = ep.get("outcome", "")
    wins = ep.get("win_patterns") or []
    fails = ep.get("fail_modes") or []
    stuck = ep.get("stuck")
    sev = ep.get("severity_hints") or []
    reports = ep.get("report_refs") or []
    carry = ep.get("carry_hosts") or []

    # mid+ / high → blindspot + checklist
    if outcome in {"high_report", "mid_report"} or sev:
        level = "高危+" if outcome == "high_report" or "高危" in sev or "严重" in sev else "中危+"
        q_bits = []
        if "hardcoded_token" in wins:
            q_bits.append("前端写死的上传/API 票是否全局有效、能否匿名写？")
        if "upload_html_exec" in wins:
            q_bits.append("上传回源是否按 text/html 执行？有无 nosniff/CSP/附件头？")
        if "samesite_api_read" in wins:
            q_bits.append("可执行页是否与业务 API 同站，CORS 是否允许恶意 Origin 带 Cookie 读回包？（升链证据，不交 CORS 专篇）")
        if "idor" in wins:
            q_bits.append("换 id 后是否读到他主体？列表 total 有无差分？")
        if "auth_bypass" in wins:
            q_bits.append("空会话写口/读口是否进 Controller 或落库？")
        if not q_bits:
            q_bits.append("本站命中的服务端信任边界是什么？哪道防线是假的？")

        body = (
            f"### 盲区库候选（{level} · `{host}`）\n\n"
            f"任务指针：`{ep.get('task')}` / `{host}`\n\n"
            f"报告：{', '.join(reports) or '（DONE 未挂路径）'}\n\n"
            f"建议语义疑问：\n"
            + "".join(f"- {q}\n" for q in q_bits)
            + "\n"
            f"win_patterns: `{', '.join(wins) or '—'}`\n\n"
            f"### 主控动作\n\n"
            f"1. 安全档由 `evolve_apply --auto-safe` 追加 `知识库/semantic-blindspots.auto.md`（去重、禁实值）\n"
            f"2. 本站 suspects 威胁模型头仍须引用相关问句（auto 行 ≠ 已引用）\n"
            f"3. covered 前过 P3 回灌门闩；短表/rules 不自动改\n"
        )
        written.append(
            write_proposal(
                prop_dir,
                "blindspot_candidate",
                f"{level}回灌候选 · {host}",
                body,
                [eid],
                "知识库/semantic-blindspots.md + 本站 suspects.md",
            )
        )

        if "upload_html_exec" in wins or "samesite_api_read" in wins:
            body2 = (
                f"### 报告升链检查清单 · `{host}`\n\n"
                f"- [ ] 未登录上传/落盘差分\n"
                f"- [ ] 回源 Content-Type / nosniff / CSP / 缓存\n"
                f"- [ ] 业务附件是否 target=_blank 直开\n"
                f"- [ ] 若做同站读 API：必须在 **恶意页 origin** 下复现（勿用 www 控制台冒充）\n"
                f"- [ ] 未登录 vs 登录对照；写「会话复用读接口」勿写 cticket 明文可读\n"
                f"- [ ] CORS 只作危害链，不交 CORS 专篇\n"
            )
            written.append(
                write_proposal(
                    prop_dir,
                    "report_checklist",
                    f"升链检查清单 · {host}",
                    body2,
                    [eid],
                    "任务 报告/ 修订或成包 checklist",
                )
            )

    # stuck → probe recipe
    if outcome == "stuck" or (stuck and "N/A瘦壳" not in (stuck or "")):
        if fails or (stuck and any(x in (stuck or "") for x in ("405", "空", "waf", "换路", "失败"))):
            body = (
                f"### 卡住换路配方 · `{host}`\n\n"
                f"卡住对照：`{stuck}`\n\n"
                f"fail_modes: `{', '.join(fails) or '—'}`\n\n"
                f"建议顺序（原子探针，禁扫描器全站喷）：\n"
                f"1. `anon_probe_alive.py` 探活\n"
                f"2. `anon_method_swap.py` 方法面\n"
                f"3. `anon_suffix_probe.py` 后缀/路径\n"
                f"4. 盲区库高频问句 + leftover 表行 sibling\n"
                f"5. DONE 写全 `卡住对照=问句已扫|…；sibling=…；换路=已试…`\n"
            )
            written.append(
                write_proposal(
                    prop_dir,
                    "probe_recipe",
                    f"卡住换路 · {host}",
                    body,
                    [eid],
                    "执行腿线程必读对照；不改红线",
                )
            )

    # carry hosts dispatch bias
    if carry:
        biz = [h for h in carry if not CDN_HINT.search(h)]
        cdn = [h for h in carry if CDN_HINT.search(h)]
        body = (
            f"### 带出host 处置 · `{host}`\n\n"
            f"业务候选（锁面内且 leftover 无 → 可进 leftover 派席）：\n"
            + ("".join(f"- `{h}`\n" for h in biz) or "- （无）\n")
            + "\nCDN/静态回源（**只记不派独立席**；危害在源站验证）：\n"
            + ("".join(f"- `{h}`\n" for h in cdn) or "- （无）\n")
            + "\n超大主站 m/www 默认不因带出整站开席。\n"
        )
        written.append(
            write_proposal(
                prop_dir,
                "dispatch_bias",
                f"带出host处置 · {host}",
                body,
                [eid],
                "主控 leftover / 种子队列（人审）",
            )
        )

    # done hygiene
    if not stuck and outcome != "unknown":
        pass
    elif not ep.get("carry_raw"):
        written.append(
            write_proposal(
                prop_dir,
                "done_fix",
                f"DONE 补字段 · {host}",
                f"`{host}` episode 缺带出host 原始行。补 `带出host=无|N/A瘦壳|list` 后再 covered。\n",
                [eid],
                "该站 DONE_*.md",
            )
        )

    return written


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate evolution proposals from episodes")
    ap.add_argument("--task-root", type=Path, required=True)
    ap.add_argument("--limit", type=int, default=50, help="max episodes to scan from end")
    args = ap.parse_args()
    task_root = args.task_root.resolve()
    evo = task_root / "进化"
    ep_path = evo / "episodes.jsonl"
    prop_dir = evo / "proposals"
    if not ep_path.is_file():
        print(f"ERROR: no episodes at {ep_path} — run episode_from_done.py first", file=sys.stderr)
        return 2

    eps = load_episodes(ep_path)
    if not eps:
        print("no episodes")
        return 0
    eps = eps[-args.limit :]

    # skip if proposal already references episode id
    existing_eids: set[str] = set()
    if prop_dir.is_dir():
        for jp in prop_dir.glob("prop_*.json"):
            try:
                meta = json.loads(jp.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            for e in meta.get("from_episodes") or []:
                existing_eids.add(e)

    prop_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    for ep in eps:
        eid = ep.get("id", "")
        if eid in existing_eids:
            print(f"SKIP proposals exist for {eid}")
            continue
        paths = propose_from_episode(ep, prop_dir)
        for p in paths:
            print(f"NEW  {p.name}")
            n += 1
        if paths:
            existing_eids.add(eid)

    # aggregate win pattern frequency → one dispatch/blindspot bias note
    freq: dict[str, int] = defaultdict(int)
    for ep in eps:
        for w in ep.get("win_patterns") or []:
            freq[w] += 1
    hot = [k for k, v in sorted(freq.items(), key=lambda x: -x[1]) if v >= 2]
    already_agg = False
    if prop_dir.is_dir():
        for jp in prop_dir.glob("prop_*.json"):
            try:
                if json.loads(jp.read_text(encoding="utf-8")).get("title") == "任务级重复根因":
                    already_agg = True
                    break
            except json.JSONDecodeError:
                continue
    if hot and not already_agg:
        body = (
            "### 本任务 win_pattern 频次 ≥2\n\n"
            + "".join(f"- `{k}` × {freq[k]}\n" for k in hot)
            + "\n若重复根因，开 hunt-iter 评估是否进打穿短表（**不直接改短表**）。\n"
        )
        p = write_proposal(
            prop_dir,
            "blindspot_candidate",
            "任务级重复根因",
            body,
            [],
            "hunt-iter.md 候选（人审）",
        )
        print(f"NEW  {p.name} (task aggregate)")
        n += 1
    elif hot and already_agg:
        print("SKIP 任务级重复根因 already proposed")

    print(f"wrote {n} proposal files under {prop_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
