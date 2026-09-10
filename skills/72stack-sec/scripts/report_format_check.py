#!/usr/bin/env python3
"""report_format_check.py — SRC 报告版式闸（不定级、不替代 format 正文）

对照 ~/.grok/rules/vuln-report-format.md 的「八块 + 排版」做静态检查。
不定级对不对、不验 curl 是否真打通过生产。

用法:
  python report_format_check.py <报告.md> [更多.md…]
  python report_format_check.py --dir "C:\\Users\\H\\Desktop\\某_SRC挖洞\\报告"
  python report_format_check.py --dir Desktop\\*_SRC挖洞\\报告   # 需 shell 展开；或传绝对路径

退出码: 0=全部通过  1=有失败  2=参数/读文件错误
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

FULLWIDTH_HASH = "＃"
HALFWIDTH_HASH = "#"

REQUIRED_LABELS = (
    "目标网站URL：",
    "漏洞等级：",
    "漏洞描述：",
    "漏洞危害：",
    "涉及接口清单",
    "复现步骤",
    "修复建议",
)

LEVEL_OK = frozenset({"中危", "高危", "严重"})


def log(msg: str) -> None:
    print(msg, file=sys.stderr)


def normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def check_one(path: Path) -> list[str]:
    errs: list[str] = []
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as e:
        return [f"读失败: {e}"]

    text = normalize_newlines(raw)
    lines = text.split("\n")
    if not lines or not lines[0].strip():
        errs.append("缺漏洞标题（第 1 行应非空）")
        return errs

    title = lines[0].strip()
    if title.startswith("#"):
        errs.append("标题行不要用 markdown # 标题；应是纯一行标题")

    # 前三行：标题 / 目标网站URL / 漏洞等级，中间不空行
    if len(lines) < 3:
        errs.append("正文过短：至少要有标题、目标网站URL、漏洞等级")
        return errs

    if lines[1].strip() == "" or lines[2].strip() == "":
        errs.append("标题 / 目标网站URL / 漏洞等级 之间不应空行")

    if not lines[1].startswith("目标网站URL："):
        errs.append("第 2 行应为「目标网站URL：https://…」")
    elif not re.search(r"https?://", lines[1]):
        errs.append("目标网站URL 缺少 http(s) 地址")

    level_line = lines[2].strip()
    if not level_line.startswith("漏洞等级："):
        errs.append("第 3 行应为「漏洞等级：中危|高危|严重」")
    else:
        level = level_line.split("：", 1)[-1].strip()
        # 允许「高危（…）」备注，但主等级须是三档之一
        base = re.split(r"[（(]", level, maxsplit=1)[0].strip()
        if base not in LEVEL_OK:
            errs.append(f"漏洞等级非法: {level!r}（只允许 中危/高危/严重）")

    for lab in REQUIRED_LABELS:
        if lab not in text:
            errs.append(f"缺块标签: {lab}")

    # 描述/危害：标签单独一行，正文不跟冒号同行
    for lab in ("漏洞描述：", "漏洞危害："):
        m = re.search(rf"(?m)^{re.escape(lab)}(.*)$", text)
        if not m:
            continue
        after = m.group(1).strip()
        if after:
            errs.append(f"{lab} 冒号后应换行再写正文，不要跟在同一行")

    # 半角 # 作大块分隔（允许 markdown 代码块内出现，粗检：单独一行的 #）
    for i, ln in enumerate(lines, 1):
        if ln.strip() == HALFWIDTH_HASH:
            errs.append(f"L{i}: 大块分隔应用全角＃，不要用半角 #")

    if FULLWIDTH_HASH not in text:
        errs.append("未见全角＃分隔（大块之间应有）")

    # 匿名闸粗检：标题含「匿名」时，复现整包区若出现 Cookie: 则告警
    if "匿名" in title:
        # 粗：标题有匿名 + 正文出现 Cookie: 头
        if re.search(r"(?mi)^Cookie\s*:", text):
            errs.append("匿名闸粗检: 标题含「匿名」但正文出现 Cookie:（有会话应改越权并写实值 Cookie）")
        if re.search(r"我拿自己的会话", text):
            errs.append("匿名闸粗检: 标题含「匿名」但描述用了「我拿自己的会话」")

    # 有会话描述却标匿名
    if "匿名" in title and re.search(r"我拿自己的会话", text):
        pass  # already flagged

    # 修复建议应在文末附近存在
    if "修复建议" in text:
        # 复现步骤后应有全角＃再接修复建议（软提醒）
        if not re.search(r"修复建议\s*[:：]", text) and "修复建议" not in text.split("复现步骤", 1)[-1]:
            errs.append("修复建议位置异常（应在复现步骤之后）")

    # 半角 # 标题样式误用（除代码块外很难完美，跳过）

    return errs


def iter_targets(args: argparse.Namespace) -> list[Path]:
    out: list[Path] = []
    for p in args.paths:
        path = Path(p)
        if path.is_file():
            out.append(path)
        else:
            log(f"[E] 不是文件: {path}")
            sys.exit(2)
    if args.dir:
        d = Path(args.dir)
        if not d.is_dir():
            log(f"[E] 不是目录: {d}")
            sys.exit(2)
        out.extend(sorted(d.glob("*.md")))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="SRC 报告版式闸（不定级）")
    ap.add_argument("paths", nargs="*", help="报告 .md 路径")
    ap.add_argument("--dir", help="扫描某任务 报告/ 目录下全部 .md")
    args = ap.parse_args()
    if not args.paths and not args.dir:
        ap.print_help()
        sys.exit(2)

    files = iter_targets(args)
    if not files:
        log("[E] 没有可检查的 .md")
        sys.exit(2)

    failed = 0
    for f in files:
        errs = check_one(f)
        if not errs:
            print(f"OK\t{f}")
        else:
            failed += 1
            print(f"FAIL\t{f}")
            for e in errs:
                print(f"  - {e}")

    if failed:
        log(f"[!] {failed}/{len(files)} 未过版式闸")
        sys.exit(1)
    log(f"[+] {len(files)} 全部过版式闸（不定级）")
    sys.exit(0)


if __name__ == "__main__":
    main()
