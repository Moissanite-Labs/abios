#!/usr/bin/env python3
"""Verify the ABIOS and sealed-session benchmarks against committed tables (no file writes)."""
from __future__ import annotations

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ABIOS = os.path.join(ROOT, "scripts", "protean-abios")


def main() -> int:
    env = os.environ.copy()
    env["PYTHONPATH"] = ABIOS + os.pathsep + env.get("PYTHONPATH", "")
    status = 0
    for script in ("bench.py", "auth_bench.py"):
        proc = subprocess.run(
            [sys.executable, os.path.join(ABIOS, script)],
            cwd=ROOT,
            env=env,
            check=False,
        )
        if proc.returncode != 0 and status == 0:
            # A child killed by a signal reports a negative code; still a failure.
            status = proc.returncode if proc.returncode > 0 else 1
    return status


if __name__ == "__main__":
    sys.exit(main())
