#!/usr/bin/env python3
"""Locate register_profile.json. Script-load only — never Read the file into chat.

Search order:
  1) env GROK_REGISTER_PROFILE
  2) this directory register_profile.json
"""
import json
import os
import sys


def profile_path():
    env = (os.environ.get('GROK_REGISTER_PROFILE') or '').strip()
    if env and os.path.isfile(env):
        return env
    here = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'register_profile.json')
    if os.path.isfile(here):
        return here
    return None


def load_profile():
    p = profile_path()
    if not p:
        print(
            '[E] 找不到 register_profile.json。'
            '复制本目录 register_profile.json.example 为 register_profile.json 后填写，'
            '或设置 GROK_REGISTER_PROFILE 指向已有资料。',
            file=sys.stderr,
        )
        sys.exit(2)
    with open(p, encoding='utf-8') as f:
        return json.load(f)
