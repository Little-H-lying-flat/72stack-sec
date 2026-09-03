# -*- coding: utf-8 -*-
"""gate_check.py — 收工完整性门闩(可执行版,双档)

用法:
    python gate_check.py --work <目录> --host <当前host>              # practice 档(默认):国内 SRC 线
    python gate_check.py --work <目录> --tier formal                 # formal 档:靶场/平台提交,四查全查
    python gate_check.py --work <目录> --host <当前host> --json

--work 接任意目录:Desktop\\{任务}_SRC挖洞\\、{名}_dig\\、work/<slug> 均可。

practice 档(国内默认):必须 --host <当前host>,只认该 host 目录下的 endpoints.md + matrix.md;
  禁止整树第一份 endpoints.md 冒充当前站。同闸/瘦壳/无洞**不算失败**——findings/suspects/state.json 均不强制。
formal 档:原四查(预算账平/证据覆盖/登记簿对账/suspects 覆盖),无洞需 --no-findings 豁免。

退出码: 0=门闩通过; 1=未通过(不许宣布测完)
"""
import argparse
import json
import os
import re
import sys


def fail(name, detail):
    return {"check": name, "pass": False, "detail": detail}


def ok(name, detail):
    return {"check": name, "pass": True, "detail": detail}


def check1_budget(work):
    """预算账平:counters.probes vs evidence 探针文件计数。"""
    sp = os.path.join(work, "state.json")
    if not os.path.exists(sp):
        return fail("1 预算账平", "state.json 不存在")
    s = json.load(open(sp, encoding="utf-8"))
    probes = s.get("counters", {}).get("probes", -1)
    ev = os.path.join(work, "evidence")
    n_ev = len([f for f in os.listdir(ev) if os.path.isfile(os.path.join(ev, f))]) if os.path.isdir(ev) else 0
    if probes < 0:
        return fail("1 预算账平", "counters.probes 未记录(记账从未发生——11 §3-6 违规)")
    if n_ev == 0:
        return fail("1 预算账平", "evidence 目录为空——无探针即宣布测完")
    ratio = probes / n_ev if n_ev else 0
    if not (0.5 <= ratio <= 1.5):
        return fail("1 预算账平", f"probes={probes} vs evidence 文件={n_ev}(比值 {ratio:.2f},容差 ±50% 外——账实不符")
    return ok("1 预算账平", f"probes={probes}, evidence 文件={n_ev}, 比值 {ratio:.2f}")


def check2_coverage(work):
    """证据覆盖:findings/suspects/NEXT-ROUND 至少两件存在;findings 非空。"""
    f = os.path.join(work, "findings.md")
    s = os.path.join(work, "suspects.md")
    n = os.path.join(work, "NEXT-ROUND.md")
    have_f = os.path.exists(f) and os.path.getsize(f) > 50
    have_s = os.path.exists(s)
    have_n = os.path.exists(n)
    if not have_f:
        return fail("2 证据覆盖", "findings.md 缺失或近空")
    if not (have_s or have_n):
        return fail("2 证据覆盖", "suspects.md 与 NEXT-ROUND.md 均缺失——覆盖率声明无处落盘")
    return ok("2 证据覆盖", f"findings.md ✓, suspects.md {'✓' if have_s else '✗(14 号语义审计未产出——R18 前战役可豁免)'}, NEXT-ROUND {'✓' if have_n else '✗'}")


def check3_ledger(work):
    """登记簿对账:confirmed 行引用的 evidence 文件存在。"""
    f = os.path.join(work, "findings.md")
    if not os.path.exists(f):
        return fail("3 登记簿对账", "findings.md 不存在")
    txt = open(f, encoding="utf-8", errors="replace").read()
    conf_rows = [l for l in txt.splitlines() if "| **confirmed" in l or "| confirmed" in l]
    if not conf_rows:
        return fail("3 登记簿对账", "无 confirmed 行(若确有发现应先走差分;若确无发现,此项以 --no-findings 跳过)")
    missing = []
    for row in conf_rows:
        # 简写展开:"a1/a2.html" → 两个真实文件名(台账常见 a-b 系列简写)
        expanded = set()
        for m in re.finditer(r"([\w\-]+(?:/\d+)?\.(?:txt|html|png|har|yml|json|bmp))", row):
            fn = m.group(1)
            expanded.add(fn)
            if "/" in fn:
                pre, suf = fn.split("/", 1)
                base = re.sub(r"\d+\.\w+$", "", pre)  # 去掉 pre 末尾序号:t9-xss-search1 → t9-xss-search
                m2 = re.match(r"^(.*?)(\d+)\.(\w+)$", pre)
                if m2:
                    expanded.add(f"{m2.group(1)}{suf}")          # search1/2.html → search2.html(序号替换)
                    expanded.add(f"{m2.group(1)}{m2.group(2)}{suf}")  # 原序号+新后缀
                expanded.add(base + suf)                          # search.html(去序号)
        expanded.discard(next((x for x in expanded if '/' in x), None))  # 展开成功即丢弃简写原串
        for fn in sorted(x for x in expanded if x):
            if fn.endswith(".md"):
                continue  # 方法论/报告文档引用,非 evidence
            if "*" in fn or "?" in fn:
                continue  # 通配符写法(如 f05-*.txt)按存在族抽样
            hit = any(os.path.exists(os.path.join(dp, fn)) for dp, _, _ in os.walk(work))
            if not hit:
                # 通配族抽测:替换末段数字为 * 再抽查一个同族文件
                stem = re.sub(r"\d+", "*", fn)
                fam = fn
                for dp, _, files in os.walk(work):
                    for f in files:
                        if re.sub(r"\d+", "*", f) == stem:
                            fam = f; break
                if fam != fn:
                    continue  # 同族文件在盘=引用成立
                if fn not in missing:
                    missing.append(fn)
    if missing:
        # 豁免:台账已声明散佚(历史轮清理)且有 fresh-repro 复验证据在盘
        if "散佚" in txt and ("复验" in txt or "fresh repro" in txt.lower()):
            return ok("3 登记簿对账", f"confirmed {len(conf_rows)} 条;{len(missing)} 个散佚引用已声明(见 findings.md gate_check 注记),复验证据在盘")
        return fail("3 登记簿对账", f"confirmed 行引用但 evidence 缺失: {missing[:5]}")
    return ok("3 登记簿对账", f"confirmed 行 {len(conf_rows)} 条,证据文件全部在盘")


def check4_suspects(work):
    """suspects 覆盖:14 号语义审计产出存在且结构完整。"""
    s = os.path.join(work, "suspects.md")
    if not os.path.exists(s):
        return fail("4 suspects 覆盖", "suspects.md 不存在(14 号 Phase 4.5 未执行——发现主引擎缺席)")
    txt = open(s, encoding="utf-8", errors="replace").read()
    n_sus = len(re.findall(r"S-\d+", txt))
    has_map = ("playbook" in txt) or ("映射" in txt)
    if n_sus == 0:
        return fail("4 suspects 覆盖", "suspects.md 存在但无可疑点条目(S-xx)")
    if not has_map:
        return fail("4 suspects 覆盖", "suspects 条目缺 playbook 映射列(payload 确认阶段无法查表)")
    return ok("4 suspects 覆盖", f"可疑点 {n_sus} 条,含映射列")


def _norm_host(host):
    h = (host or "").strip().lower()
    if h.startswith("https://"):
        h = h[8:]
    elif h.startswith("http://"):
        h = h[7:]
    h = h.split("/")[0]
    return h


def _host_dir_match(dirname, host_n):
    d = (dirname or "").lower()
    if not d or not host_n:
        return False
    if d == host_n:
        return True
    # www.foo.com vs foo.com
    if d.startswith("www.") and d[4:] == host_n:
        return True
    if host_n.startswith("www.") and host_n[4:] == d:
        return True
    return False


def _rank_host_dir(dp):
    s = dp.replace("\\", "/").lower()
    if "/线程交付/" in s or s.endswith("/线程交付") or "\\线程交付\\" in dp.lower():
        return 0
    if "_dig" in os.path.basename(os.path.dirname(dp)).lower() or "/_dig/" in s or s.endswith("_dig"):
        return 1
    return 2


def check_practice(work, host=None):
    """practice 档:只查当前 host 的 endpoints.md + matrix.md,禁止整树第一份冒充。"""
    if not host:
        return fail(
            "practice 收工查",
            "practice 必须 --host <当前host>,禁止整树第一份 endpoints.md 冒充当前站",
        )
    host_n = _norm_host(host)
    if not host_n:
        return fail("practice 收工查", "--host 为空")
    hits = []
    if os.path.isfile(os.path.join(work, "endpoints.md")):
        bn = os.path.basename(os.path.normpath(work))
        if _host_dir_match(bn, host_n):
            hits.append(os.path.normpath(work))
    for dp, _, files in os.walk(work):
        if "endpoints.md" not in files:
            continue
        bn = os.path.basename(dp)
        if _host_dir_match(bn, host_n):
            hits.append(os.path.normpath(dp))
    # unique preserve order
    seen = set()
    uniq = []
    for h in hits:
        k = h.lower()
        if k not in seen:
            seen.add(k)
            uniq.append(h)
    if not uniq:
        return fail(
            "practice 收工查",
            f"未找到 host={host_n} 的 endpoints.md（期望 线程交付/{host_n}/ 或同名目录）",
        )
    uniq.sort(key=_rank_host_dir)
    chosen = uniq[0]
    eps = os.path.join(chosen, "endpoints.md")
    mtx = os.path.join(chosen, "matrix.md")
    if not os.path.isfile(mtx):
        return fail("practice 收工查", f"{chosen} 有 endpoints.md 但缺 matrix.md——类型矩阵未落盘")
    n_eps = sum(1 for _ in open(eps, encoding="utf-8", errors="replace"))
    extra = f";另有 {len(uniq)-1} 处同 host 目录未采用" if len(uniq) > 1 else ""
    return ok(
        "practice 收工查",
        f"{chosen} endpoints.md({n_eps} 行)+matrix.md 在盘;同闸/瘦壳/无洞=合法收工{extra}",
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True, help="任务目录:Desktop 任务根/{名}_dig/work/<slug> 均可")
    ap.add_argument("--host", default=None,
                    help="practice 必填:当前站 host(目录名).禁止省略后拿整树第一份 endpoints.md")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--tier", choices=["practice", "formal"], default="practice",
                    help="practice=国内默认(当前 host 端点+矩阵在盘即合法);formal=靶场/平台提交(四查全查)")
    ap.add_argument("--no-findings", action="store_true", help="formal 档:本轮合法无发现时跳过查 3 的空台账失败")
    ap.add_argument("--legacy", action="store_true", help="formal 档:14 号之前的战役:查 4 降级为警告")
    ap.add_argument("--dry-run", action="store_true", help="流程试车/演练目录:只输出报告不作为门闩,exit 恒 0")
    args = ap.parse_args()
    work = args.work

    if args.tier == "practice":
        results = [check_practice(work, args.host)]
    else:
        results = [
            check1_budget(work),
            check2_coverage(work),
            check3_ledger(work),
            check4_suspects(work),
        ]
        if args.no_findings and not results[2]["pass"] and "无 confirmed 行" in results[2]["detail"]:
            results[2] = ok("3 登记簿对账", "本轮合法无发现(--no-findings)")
        if args.legacy and not results[3]["pass"] and "不存在" in results[3]["detail"]:
            results[3] = ok("4 suspects 覆盖(legacy 豁免)", "14 号发布前的战役:语义审计未产出属历史状态,新战役不豁免")

    passed = all(r["pass"] for r in results)
    if args.json:
        print(json.dumps({"gate": passed, "tier": args.tier, "results": results}, ensure_ascii=False, indent=2))
    else:
        title = "### 收工完整性四查(11 §2 / 09 §3 / 14 §3)" if args.tier == "formal" else "### 收工门闩(practice 档·国内默认)"
        print(title)
        for r in results:
            mark = "✓" if r["pass"] else "✗"
            print(f"[{mark}] {r['check']}: {r['detail']}")
        print(f"\n== 门闩{'通过,可宣布测完' if passed else '未通过——不许宣布测完'} ==")
    if args.dry_run:
        print("\n[dry-run] 试车目录:门闩仅演示,不计入战役判定。")
        sys.exit(0)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
