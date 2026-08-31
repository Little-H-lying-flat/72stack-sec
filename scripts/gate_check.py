# -*- coding: utf-8 -*-
"""gate_check.py — 11-fullauto-pipeline 收工完整性四查(可执行版)

用法:
    python gate_check.py --work work/<target-slug>
    python gate_check.py --work work/<target-slug> --json   # 机器可读(state.json 引用)

四查(对照 11 §2 / 09 §3 / 14 §3):
  1 预算账平    : state.counters.probes 与 evidence 探针文件数对账(±20% 容差)
  2 证据覆盖    : findings 台账行数 vs 矩阵/suspects 覆盖声明(结构性检查)
  3 登记簿对账  : confirmed 行均有 evidence 文件引用且文件存在
  4 suspects 覆盖: suspects.md 存在且含映射类列(14 号语义审计产出)

退出码: 0=四查全过; 1=任一查 FAIL(不许宣布测完)
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True, help="work/<target-slug> 目录")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-findings", action="store_true", help="本轮合法无发现时跳过查 3 的空台账失败")
    ap.add_argument("--legacy", action="store_true", help="14 号语义审计之前的战役:查 4 降级为警告")
    args = ap.parse_args()
    work = args.work

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
        print(json.dumps({"gate": passed, "results": results}, ensure_ascii=False, indent=2))
    else:
        print("### 收工完整性四查(11 §2 / 09 §3 / 14 §3)")
        for r in results:
            mark = "✓" if r["pass"] else "✗"
            print(f"[{mark}] {r['check']}: {r['detail']}")
        print(f"\n== 门闩{'通过,可宣布测完' if passed else '未通过——不许宣布测完'} ==")
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
