#!/usr/bin/env python3
"""Measure encoding efficiency: v1 English vs v2 symbolic packets.

For each task in bench/tasks.jsonl, compares the v1 and v2 forms on
bytes, estimated tokens, and parse+validate latency. The token figure
is a chars/4 heuristic, labeled as such: it is a rough size proxy,
not a real tokenizer count. stdlib only.

Usage: sym2-bench.py [tasks.jsonl]
"""
import json
import os
import sys
import timeit

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts", "protean-sym2p"))
import sym2_parse  # noqa: E402
import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "sym2_validate",
    os.path.join(HERE, "..", "scripts", "protean-sym2p", "sym2-validate.py"))
_validate_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_validate_mod)

ITERS = 2000


def v1_text(task):
    return json.dumps(task["v1"], separators=(",", ":"))


def bench_v1(text):
    def run():
        json.loads(text)
    secs = timeit.timeit(run, number=ITERS) / ITERS
    return secs


def bench_v2(text):
    def run():
        errs = _validate_mod.check_line(text, 1)
        assert not errs
    secs = timeit.timeit(run, number=ITERS) / ITERS
    return secs


def row(task):
    t1, t2 = v1_text(task), task["v2"]
    return {
        "id": task["id"],
        "v1_bytes": len(t1.encode()),
        "v2_bytes": len(t2.encode()),
        "v1_ms": bench_v1(t1) * 1000,
        "v2_ms": bench_v2(t2) * 1000,
    }


def main(argv):
    path = argv[1] if len(argv) > 1 else os.path.join(HERE, "tasks.jsonl")
    with open(path) as fh:
        tasks = [json.loads(line) for line in fh if line.strip()]
    tasks = [t for t in tasks if "v1" in t]
    rows = [row(t) for t in tasks]
    print("%-6s %9s %9s %7s %10s %10s" %
          ("task", "v1 bytes", "v2 bytes", "ratio",
           "v1 ms", "v2 ms"))
    tb1 = tb2 = 0
    for r in rows:
        ratio = r["v1_bytes"] / r["v2_bytes"]
        print("%-6s %9d %9d %7.1fx %10.3f %10.3f" %
              (r["id"], r["v1_bytes"], r["v2_bytes"], ratio,
               r["v1_ms"], r["v2_ms"]))
        tb1 += r["v1_bytes"]
        tb2 += r["v2_bytes"]
    print("%-6s %9d %9d %7.1fx" % ("total", tb1, tb2, tb1 / tb2))
    print()
    print("bytes are exact. token estimate ~ chars/4 for either form.")
    print("ms is mean parse+validate latency over %d runs." % ITERS)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
