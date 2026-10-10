#!/usr/bin/env python3
"""Score model eval answers against bench/tasks.jsonl.

Usage: sym2-score.py tasks.jsonl answers.json

answers.json shape:
{
  "model": "example-model", "date": "2026-10-10",
  "runs": {
    "t01": {"v1": ["a1", "a2", ...], "v2": ["a1", "a2", ...]},
    "t07": {"v2": "rendered English..."},
    "t09": {"v1": "2|...|"},
    ...
  }
}

Comprehension answers are lists in question order, one per form run.
Render answers are strings, scored on key-phrase containment.
Compile answers are v2 strings, scored on validity and exact match.

All string comparison is normalized (case, whitespace). stdlib only.
"""
import json
import os
import re
import sys
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "sym2_validate",
    os.path.join(HERE, "..", "scripts", "protean-sym2p", "sym2-validate.py"))
_validate_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_validate_mod)


def norm(s):
    return re.sub(r"\s+", " ", s.strip().lower())


def score_comprehension(task, answers):
    out = {}
    for form in ("v1", "v2"):
        given = answers.get(form, [])
        want = [q["a"] for q in task["questions"]]
        hits = sum(1 for g, w in zip(given, want) if norm(g) == norm(w))
        out[form] = (hits, len(want))
    return out


def score_render(task, answers):
    out = {}
    for form, text in answers.items():
        if not isinstance(text, str):
            continue
        ntext = norm(text)
        hits = sum(1 for p in task["key_phrases"] if norm(p) in ntext)
        out[form] = (hits, len(task["key_phrases"]))
    return out


def score_compile(task, answers):
    out = {}
    for form, text in answers.items():
        if not isinstance(text, str):
            continue
        valid = not _validate_mod.check_line(text.strip(), 1)
        exact = norm(text) == norm(task["v2"])
        out[form] = {"valid": valid, "exact": exact}
    return out


def main(argv):
    if len(argv) != 3:
        print("usage: sym2-score.py tasks.jsonl answers.json",
              file=sys.stderr)
        return 2
    with open(argv[1]) as fh:
        tasks = {json.loads(l)["id"]: json.loads(l)
                 for l in fh if l.strip()}
    with open(argv[2]) as fh:
        answers = json.load(fh)
    runs = answers.get("runs", {})
    print("model: %s  date: %s" %
          (answers.get("model", "?"), answers.get("date", "?")))
    print("%-6s %-14s %12s %12s" % ("task", "kind", "v1", "v2"))
    tot = {"v1": [0, 0], "v2": [0, 0]}
    for tid, task in tasks.items():
        kind = task["kind"]
        ans = runs.get(tid, {})
        if kind == "comprehension":
            s = score_comprehension(task, ans)
        elif kind == "render":
            s = score_render(task, ans)
        else:
            s = score_compile(task, ans)
            line = []
            for form in ("v1", "v2"):
                r = s.get(form, {})
                line.append("valid=%d exact=%d" %
                            (r.get("valid", 0), r.get("exact", 0)))
                if r.get("exact"):
                    tot[form][0] += 1
                tot[form][1] += 1
            print("%-6s %-14s %12s %12s" % (tid, kind, line[0], line[1]))
            continue
        cells = []
        for form in ("v1", "v2"):
            h, n = s.get(form, (0, 0))
            cells.append("%d/%d" % (h, n))
            tot[form][0] += h
            tot[form][1] += n
        print("%-6s %-14s %12s %12s" % (tid, kind, cells[0], cells[1]))
    print("%-6s %-14s %12s %12s" %
          ("total", "",
           "%d/%d" % tuple(tot["v1"]), "%d/%d" % tuple(tot["v2"])))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
