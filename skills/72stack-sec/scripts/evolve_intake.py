#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""evolve_intake.py — evolve_hook 兼容入口（逻辑只认 evolve_hook.py）"""
from __future__ import annotations

import sys

from evolve_hook import main

if __name__ == "__main__":
    sys.exit(main())
