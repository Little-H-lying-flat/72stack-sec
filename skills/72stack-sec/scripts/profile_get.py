#!/usr/bin/env python3
"""Print one non-secret profile field to stdout (form fill / 台账). Never dumps auth_code."""
import sys

from _profile import load_profile

ALLOWED = {
    'phone',
    'phone_masked',
    'name_alias',
    'email_alias',
    'email.address',
    'email.imap_host',
    'email.imap_port',
    'email.enabled',
    'email.user',
}
DENIED_FRAG = ('auth_code', 'password', 'passwd', 'secret', 'token', 'api_key')


def log(m):
    print(m, file=sys.stderr)


def main():
    key = sys.argv[1].strip() if len(sys.argv) > 1 else ''
    if not key or any(d in key.lower() for d in DENIED_FRAG):
        log('[E] 用法: profile_get.py phone|phone_masked|name_alias|email_alias|email.address')
        log('[E] 禁止输出 auth_code / 密码类字段')
        sys.exit(2)
    if key not in ALLOWED:
        log('[E] 字段不在白名单: ' + ', '.join(sorted(ALLOWED)))
        sys.exit(2)
    cur = load_profile()
    for part in key.split('.'):
        if not isinstance(cur, dict) or part not in cur:
            log(f'[E] 资料里没有 {key}')
            sys.exit(2)
        cur = cur[part]
    if cur is None or cur == '':
        log(f'[E] {key} 为空')
        sys.exit(2)
    print(cur)


if __name__ == '__main__':
    main()
