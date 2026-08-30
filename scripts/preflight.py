# -*- coding: utf-8 -*-
"""preflight.py — 11-fullauto-pipeline §1.1 工具矩阵自检

只读本机工具,不向任何目标发包(--probe-target 仅做一次 HEAD 存活检查,可选)。
用法:
    python scripts/preflight.py                       # 工具矩阵(markdown 表,贴入 scope.md)
    python scripts/preflight.py --probe-target URL    # 追加一次目标存活检查
    python scripts/preflight.py --json                # 机器可读输出(供 state.json 引用)
"""
import argparse
import json
import shutil
import subprocess
import sys

# (显示名, 探测命令, 版本截取前 N 字符, 缺失时的回退链——与 11 §1.1 表一致)
CHECKS = [
    ("HTTP 客户端 curl", ["curl", "--version"], 24, "python urllib(基本必在)"),
    ("脚本运行时 python", [sys.executable, "--version"], 24, "管线硬停(11 §6-4)"),
    ("扫描器 nuclei", ["nuclei", "-version"], 30, "初筛 skipped-because: no-tool;命中后回 playbook 走完整流程"),
    ("资产探活 httpx", ["httpx", "-version"], 30, "curl 逐个探活"),
    ("端口扫描 nmap", ["nmap", "--version"], 30, "python socket connect 扫描(≤1-5 rps,顺序)"),
    ("子域收集 subfinder/OneForAll", ["subfinder", "-version"], 30, "CT 日志 / DNS 常见子域穷举(≤56 常见位)"),
    ("浏览器 browser-harness", ["browser-harness", "--version"], 30, "JS 动态路由类 skipped;录屏类证据 parked-转出(注明条件)"),
    ("报告生成 python-docx", [sys.executable, "-c", "import docx"], 0, "报告生成停,按 report-format.md 人工填模板"),
]


def probe(cmd, ver_len):
    exe = shutil.which(cmd[0])
    if exe is None:
        return "MISS", ""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        out = (r.stdout or r.stderr).strip().splitlines()
        ver = out[0][:ver_len] if out and ver_len else "OK"
        return "OK", ver
    except Exception as e:
        return "ERR", type(e).__name__


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe-target", default=None, help="可选:对目标做一次 HEAD 存活检查")
    ap.add_argument("--json", action="store_true", help="机器可读输出")
    args = ap.parse_args()

    rows = []
    for name, cmd, ver_len, fallback in CHECKS:
        status, ver = probe(cmd, ver_len)
        rows.append({"item": name, "status": status, "version": ver, "fallback": fallback if status != "OK" else ""})

    target = None
    if args.probe_target:
        import urllib.request
        try:
            req = urllib.request.Request(args.probe_target, method="HEAD")
            with urllib.request.urlopen(req, timeout=10) as resp:
                target = {"url": args.probe_target, "status": resp.status}
        except Exception as e:
            target = {"url": args.probe_target, "status": f"ERR {type(e).__name__}"}

    if args.json:
        print(json.dumps({"tools": rows, "target": target}, ensure_ascii=False, indent=2))
        return 0

    miss = [r for r in rows if r["status"] != "OK"]
    print("### 工具矩阵(preflight)")
    print("| 检查项 | 状态 | 版本/回退 |")
    print("|---|---|---|")
    for r in rows:
        cell = r["version"] if r["status"] == "OK" else f"**{r['status']}** → {r['fallback']}"
        print(f"| {r['item']} | {r['status']} | {cell} |")
    if target:
        print(f"\n目标存活: {target['url']} -> {target['status']}")
    print(f"\n== {len(rows) - len(miss)}/{len(rows)} OK ==")
    if miss:
        print("缺失项按上表回退链降级,全缺类直接 skipped-because: no-tool 进矩阵(11 §1.1)。")
    print("OOB 平台(interactsh/自建)请人工确认可达性——缺失则 SSRF/RCE 盲打类 skipped-because: no-oob。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
