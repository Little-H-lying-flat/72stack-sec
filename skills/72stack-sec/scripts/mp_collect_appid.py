#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mp_collect_appid.py — 兼容入口，收单请跑 mp_queue.py"""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

if __name__ == "__main__":
    sys.argv[0] = str(Path(__file__).with_name("mp_queue.py"))
    runpy.run_path(str(Path(__file__).with_name("mp_queue.py")), run_name="__main__")
