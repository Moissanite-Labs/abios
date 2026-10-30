#!/usr/bin/env python3
"""Verify SYM-3 benchmark against committed tables (no file writes)."""
from __future__ import annotations

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYM3 = os.path.join(ROOT, "scripts", "protean-sym3")


def main() -> int:
    env = os.environ.copy()
    env["PYTHONPATH"] = SYM3 + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(
        [sys.executable, os.path.join(SYM3, "bench.py")],
        cwd=ROOT,
        env=env,
        check=False,
    )
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
