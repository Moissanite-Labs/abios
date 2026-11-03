#!/usr/bin/env python3
"""Verify ABIOS benchmark against committed tables (no file writes)."""
from __future__ import annotations

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ABIOS = os.path.join(ROOT, "scripts", "protean-abios")


def main() -> int:
    env = os.environ.copy()
    env["PYTHONPATH"] = ABIOS + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(
        [sys.executable, os.path.join(ABIOS, "bench.py")],
        cwd=ROOT,
        env=env,
        check=False,
    )
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
