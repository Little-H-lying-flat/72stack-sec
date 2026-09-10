#!/usr/bin/env python3
"""email_code.py — 从 IMAP 邮箱读验证码/激活链接(PEEK 只读,不标已读、不删信)

配置: register_profile.json 的 "email" 字段(由 _profile.py 定位,禁止 Read 进对话):
  { "enabled": true, "address": "x@qq.com", "imap_host": "imap.qq.com",
    "imap_port": 993, "user": "x@qq.com", "auth_code": "授权码",
    "proxy": "http://127.0.0.1:7897" }   # proxy 可选,Gmail 国内必须

用法:
  python email_code.py --wait 120                 # 轮询等最新验证邮件,提码打 stdout
  python email_code.py --wait 120 --mode link     # 提激活/验证链接而非数字码
  python email_code.py --from nooe --to dig+xx@   # 按发件人/收件人别名过滤
  python email_code.py --peek                     # 自检:最近3封(主题脱敏)

退出码: 0=取到  1=超时未取到  2=环境/配置错误
隐私: 正文不打印不落盘;--peek 主题脱敏;PEEK 取信不改邮箱状态。
"""
import argparse
import email
import email.header
import email.utils
import imaplib
import os
import re
import socket
import ssl
import sys
import time

from _profile import load_profile

CODE_RE = re.compile(r'(?<!\d)(\d{4,8})(?!\d)')
NEAR_RE = re.compile(r'(?:验证码|校验码|动态码|code|Code|OTP)[^\d]{0,6}(\d{4,8})')
LINK_RE = re.compile(r'https?://[^\s"\'<><>]+')
LINK_HINT = re.compile(r'verify|activat|confirm|reset|auth|token|register|invite|validate', re.I)
KEYWORDS = ('验证码', '校验码', '动态码', 'code', 'Code', 'OTP', 'verify', '验证')


def log(m):
    print(m, file=sys.stderr)


def load_conf():
    conf = load_profile().get('email') or {}
    if not conf.get('enabled') or not conf.get('auth_code'):
        log('[E] 邮箱未配置:在 register_profile.json 的 email 字段填 address/imap_host/user/auth_code 并 enabled=true')
        sys.exit(2)
    return conf


def connect(conf):
    """IMAP SSL 连接;配了 proxy 则经代理 CONNECT 隧道再 TLS。"""
    host, port = conf['imap_host'], int(conf.get('imap_port', 993))
    proxy = (conf.get('proxy') or '').strip()
    if not proxy:
        return imaplib.IMAP4_SSL(host, port), None
    m = re.match(r'^(?:socks5h?|http)://([^:/]+):(\d+)$', proxy)
    if not m:
        log(f'[E] proxy 格式不识别: {proxy}(示例 http://127.0.0.1:7897 / socks5://127.0.0.1:7897)')
        sys.exit(2)
    phost, pport = m.group(1), int(m.group(2))
    try:
        if proxy.lower().startswith('socks5'):
            import socks
            raw = socks.socksocket()
            raw.set_proxy(socks.SOCKS5, phost, pport)
            raw.settimeout(30)
            raw.connect((host, port))
        else:
            raw = socket.create_connection((phost, pport), timeout=30)
            raw.sendall(f'CONNECT {host}:{port} HTTP/1.1\r\nHost: {host}:{port}\r\n\r\n'.encode())
            buf = b''
            while b'\r\n\r\n' not in buf:
                chunk = raw.recv(4096)
                if not chunk:
                    break
                buf += chunk
            if b' 200' not in buf.split(b'\r\n', 1)[0]:
                log(f'[E] 代理 CONNECT 失败: {buf[:80]!r}(代理活着吗?)')
                sys.exit(2)
    except OSError as e:
        log(f'[E] 连不上代理 {phost}:{pport} — {e}')
        sys.exit(2)
    ctx = ssl.create_default_context()
    tls = ctx.wrap_socket(raw, server_hostname=host)
    return imaplib.IMAP4_stream.__new__(imaplib.IMAP4_stream), tls  # 占位,下一行真正构造


def _wrap_tls(tls_sock, host):
    """把已握手的 TLS socket 包装成 imaplib.IMAP4(跳过其自身 connect)。"""
    imap = imaplib.IMAP4.__new__(imaplib.IMAP4)
    imap.host = host
    imap.port = 993
    imap.debug = 0
    imap.sock = tls_sock
    imap.file = imap.sock.makefile('rb')
    imap.tagnum = 0
    imap.tagre = re.compile(r'(?P<tag>ADT\d+) (?P<type>[A-Z]+) ?(?P<data>.*)')
    imap.tagpre = 'ADT'
    imap.state = 'LOGOUT'
    imap.literal = None
    imap.continuation = None
    imap._tls_established = True
    typ, dat = imap._get_capabilities()
    if typ != 'OK':
        raise imaplib.IMAP4.error('CAPABILITY 失败: %r' % (dat,))
    imap.state = 'NONAUTH'
    typ, dat = imap._get_response()
    if typ != 'OK':
        raise imaplib.IMAP4.error('欢迎语异常: %r' % (dat,))
    return imap


def do_login(conf):
    host = conf['imap_host']
    proxy = (conf.get('proxy') or '').strip()
    if not proxy:
        imap = imaplib.IMAP4_SSL(host, int(conf.get('imap_port', 993)))
    else:
        _, tls = connect(conf)
        imap = _wrap_tls(tls, host)
    try:
        imap.login(conf['user'], conf['auth_code'])
    except imaplib.IMAP4.error as e:
        log(f'[E] IMAP 登录失败:{e}\n    检查:auth_code 是应用专用密码/授权码(非登录密码)?两步验证已开?')
        sys.exit(2)
    try:  # 163 反爬:不发 ID 命令的客户端 SELECT 时被拒 "Unsafe Login"
        imap.xatom('ID', '("name" "dig-mail" "version" "1.0" "vendor" "myclient" "contact" "dig@local")')
    except Exception:
        pass
    return imap


def dec_header(s):
    if not s:
        return ''
    return ''.join(t.decode(c or 'utf-8', 'replace') if isinstance(t, bytes) else t
                   for t, c in email.header.decode_header(s))


def body_text(msg):
    parts = []
    for part in msg.walk():
        if part.get_content_type() in ('text/plain', 'text/html'):
            payload = part.get_payload(decode=True)
            if payload:
                cs = part.get_content_charset() or 'utf-8'
                parts.append(payload.decode(cs, 'replace'))
    return re.sub(r'<[^>]+>', ' ', '\n'.join(parts))


def extract(msg, mode):
    text = body_text(msg)
    if mode in ('code', 'auto'):
        m = NEAR_RE.search(text)
        if m:
            return m.group(1)
        cands = [c for c in CODE_RE.findall(text) if not (len(c) == 8 and c.startswith('20'))]
        if cands:
            return cands[-1]
        if mode == 'code':
            return None
    links = [l.rstrip('.,;)】」') for l in LINK_RE.findall(text)]
    hit = [l for l in links if LINK_HINT.search(l)]
    return (hit or links or [None])[0]


def fetch_new(imap, opt, since_ts):
    imap.select('INBOX', readonly=True)  # PEEK 式只读
    typ, data = imap.search(None, 'SINCE', time.strftime('%d-%b-%Y', time.gmtime(since_ts)))
    out = []
    if typ != 'OK':
        return out
    for num in reversed(data[0].split()):
        typ, d = imap.fetch(num, '(BODY.PEEK[])')
        if typ != 'OK' or not d or d[0] is None:
            continue
        msg = email.message_from_bytes(d[0][1])
        ts = email.utils.mktime_tz(email.utils.parsedate_tz(msg.get('Date', '')) or (0, '', 0, '', '', 0, '', '', 0))
        if ts < since_ts:
            continue
        out.append({'from': dec_header(msg.get('From', '')), 'to': (msg.get('To') or '').lower(),
                    'subject': dec_header(msg.get('Subject', '')), 'msg': msg})
    return out


def match(m, opt):
    if opt.from_ and opt.from_.lower() not in m['from'].lower():
        return None
    if opt.to and opt.to.lower() not in m['to']:
        return None
    kws = opt.keyword.split(',') if opt.keyword else list(KEYWORDS)  # 默认主题闸门,防发票/账单类误提
    if not any(k.lower() in m['subject'].lower() for k in kws):
        return None
    return extract(m['msg'], opt.mode)


def main():
    ap = argparse.ArgumentParser(description='IMAP 只读验证码/链接提取')
    ap.add_argument('--wait', type=int, default=0)
    ap.add_argument('--interval', type=int, default=5)
    ap.add_argument('--since', type=int, default=600, help='时效窗秒,默认600')
    ap.add_argument('--from', dest='from_', default=None, help='发件人子串过滤')
    ap.add_argument('--to', default=None, help='收件人(别名)子串过滤')
    ap.add_argument('--mode', choices=['auto', 'code', 'link'], default='auto')
    ap.add_argument('--keyword', default=None, help='主题关键词,逗号分隔')
    ap.add_argument('--peek', action='store_true', help='自检:最近3封主题脱敏')
    opt = ap.parse_args()

    conf = load_conf()
    imap = do_login(conf)
    log(f"[i] 已登录 {conf['address']}")

    if opt.peek:
        rows = fetch_new(imap, opt, time.time() - 7 * 86400)[:3]
        for r in rows:
            log(f"[peek] {r['from'][:26]} | {re.sub(r'\\d', '*', r['subject'])[:44]}")
        log('[OK] 通道正常' if rows else '[!] 7天内 0 封信(能登录=通道本身通)')
        sys.exit(0)

    deadline = time.time() + opt.wait
    floor = time.time() - opt.since
    while True:
        for m in fetch_new(imap, opt, floor):
            hit = match(m, opt)
            if hit:
                log(f"[i] 来自 {m['from'][:28]} | 主题 {m['subject'][:30]}")
                print(hit)
                sys.exit(0)
        if time.time() >= deadline:
            log(f'[!] {opt.wait}s 内未等到匹配验证邮件')
            sys.exit(1)
        time.sleep(opt.interval)


if __name__ == '__main__':
    main()
