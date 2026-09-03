#!/usr/bin/env python3
"""sms_code.py — 从 Android 手机读短信验证码(ADB 只读通道,永不增删改短信)

用法:
  python sms_code.py --wait 90                # 轮询 90s 等最新验证码,取到打到 stdout
  python sms_code.py --wait 90 --sender 106   # 只认发送方含 106 的短信
  python sms_code.py --peek                   # 通道自检:最近3条短信(内容脱敏)
  python sms_code.py --since 600 --keyword code

退出码: 0=取到验证码(stdout 只有码本身)  1=超时未取到  2=环境错误(adb缺失/无设备/未授权)
隐私: 完整短信内容不打印、不落盘;--peek 模式数字全打码。
"""
import argparse
import re
import subprocess
import sys
import time

CODE_RE = re.compile(r'(?<!\d)(\d{4,8})(?!\d)')
ROW_RE = re.compile(r'address=(?P<addr>.*?), date=(?P<date>\d{13}), body=(?P<body>.*)$')
KEYWORDS = ('验证码', '校验码', '动态码', '校验', 'code', 'Code', 'OTP', 'otp')
NEAR_RE = re.compile(r'(?:验证码|校验码|动态码|code|Code|OTP)[^\d]{0,6}(\d{4,8})')


def log(msg):
    print(msg, file=sys.stderr)


def adb(args, opt):
    cmd = [opt.adb]
    if opt.device:
        cmd += ['-s', opt.device]
    cmd += args
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, errors='replace', timeout=30)
    except FileNotFoundError:
        log('[E] adb 不存在:安装 platform-tools 或用 --adb 指定路径')
        sys.exit(2)
    except subprocess.TimeoutExpired:
        log('[E] adb 超时:检查手机连接')
        sys.exit(2)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


def pick_device(opt):
    rc, out = adb(['devices'], opt)
    if rc != 0:
        log('[E] adb devices 失败:' + out.strip()[:200])
        sys.exit(2)
    serials = [l.split('\t')[0] for l in out.splitlines() if l.endswith('\tdevice')]
    if not serials:
        log('[E] 无已授权设备:插手机、开USB调试、允许授权弹窗')
        sys.exit(2)
    if opt.device:
        if opt.device not in serials:
            log(f'[E] 设备 {opt.device} 不在线,当前在线: {serials}')
            sys.exit(2)
        return opt.device
    if len(serials) > 1:
        log(f'[E] 多台设备在线 {serials},用 --device 指定')
        sys.exit(2)
    return serials[0]


def query_sms(opt, device):
    rc, out = adb(['shell', 'content', 'query', '--uri', 'content://sms/inbox',
                   '--projection', 'address:date:body'], opt, )
    rows = []
    for line in out.splitlines():
        m = ROW_RE.search(line.strip())
        if m:
            rows.append({'addr': m.group('addr'), 'date': int(m.group('date')),
                         'body': m.group('body')})
    rows.sort(key=lambda r: r['date'], reverse=True)
    return rows


def extract_code(body):
    m = NEAR_RE.search(body)
    if m:
        return m.group(1)
    cands = CODE_RE.findall(body)
    if not cands:
        return None
    strong = [c for c in cands if not (len(c) == 8 and c.startswith('20'))]
    return (strong or cands)[-1]


def match(row, opt):
    if opt.sender and opt.sender not in row['addr']:
        return None
    if not any(k in row['body'] for k in ([opt.keyword] if opt.keyword else KEYWORDS)):
        return None
    return extract_code(row['body'])


def main():
    ap = argparse.ArgumentParser(description='ADB 只读短信验证码提取')
    ap.add_argument('--wait', type=int, default=0, help='轮询秒数,0=只查一次')
    ap.add_argument('--interval', type=int, default=3, help='轮询间隔秒')
    ap.add_argument('--since', type=int, default=300, help='短信时效窗(秒),默认300')
    ap.add_argument('--sender', default=None, help='发送方号码子串过滤')
    ap.add_argument('--keyword', default=None, help='自定义关键词(默认内置词表)')
    ap.add_argument('--adb', default='adb', help='adb 可执行路径')
    ap.add_argument('--device', default=None, help='设备序列号(多设备时必填)')
    ap.add_argument('--peek', action='store_true', help='自检:最近3条短信脱敏预览')
    opt = ap.parse_args()

    device = pick_device(opt)

    if opt.peek:
        rows = query_sms(opt, device)[:3]
        if not rows:
            log('[!] 短信库读到 0 条(部分 ROM 限制 shell 读短信;可改走 Tasker webhook 方案)')
            sys.exit(1)
        for r in rows:
            age = time.time() - r['date'] / 1000
            masked = re.sub(r'\d', '*', r['body'])[:50]
            log(f"[peek] 发送方={r['addr'][:14]} {age:.0f}s前 | {masked}")
        log('[OK] 通道正常')
        sys.exit(0)

    floor_ms = lambda: int((time.time() - opt.since) * 1000)
    deadline = time.time() + opt.wait
    while True:
        for r in query_sms(opt, device):
            if r['date'] < floor_ms():
                break  # 已按时间倒序,后面更旧
            code = match(r, opt)
            if code:
                if opt.sender is None and len(opt.keyword or '') == 0:
                    log(f"[i] 来自 {r['addr'][:14]}")
                print(code)
                sys.exit(0)
        if time.time() >= deadline:
            log(f'[!] {opt.wait}s 内未等到匹配验证码')
            sys.exit(1)
        time.sleep(opt.interval)


if __name__ == '__main__':
    main()
