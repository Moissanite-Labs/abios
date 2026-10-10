#!/usr/bin/env python3
"""Render SYM-2P v2 dense packets into human-readable English.

The wire form is the agents' language: codes, numbers, expressions.
This script converts it to human syntax for operators. The rendered
form is informative, never normative.

Parsing lives in sym2_parse.py; this file only renders.

Usage: sym2-render.py <packet-or-file>
Exit codes: 0 ok, 1 at least one line failed, 2 usage or IO error.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sym2_parse import (  # noqa: E402
    ACTS, RQS, ROLES, STATES, UNITS, check_expr, parse_all, split_fields,
)


def render_impl(expr):
    # (20 unit (lo hi))
    unit = UNITS.get(expr[1], str(expr[1]))
    rng = expr[2]
    return "implement %s %s-%s" % (unit, rng[0], rng[1])


def render_expr(expr):
    op = int(expr[0])
    if op == 10:
        return "Scope: %s of %s." % (render_expr(expr[2]), expr[1])
    if op == 20:
        return render_impl(expr)
    if op == 11:
        inner = expr[1]
        if inner[1] == "*":
            return "Constraint: modify no existing paths."
        return "Constraint: modify no paths matching %s." % inner[1]
    if op == 12:
        inner = expr[1]
        return ("Acceptance: %s exits %s on valid input, %s on invalid."
                % (inner[1], inner[2], inner[3]))
    return None


def render_packet(line):
    fields, err = split_fields(line)
    if err:
        return None, "not a v2 packet line (%s)" % err
    _, pid, _tk, f, t, a, st, cf, cv, body, rq, base, exp = fields
    try:
        f, t, a, st, rq = int(f), int(t), int(a), int(st), int(rq)
        cf, cv, exp = int(cf), int(cv), int(exp)
    except ValueError:
        return None, "non-integer in numeric field"
    for code, reg, name in ((f, ROLES, "role"), (t, ROLES, "role"),
                            (a, ACTS, "act"), (st, STATES, "state"),
                            (rq, RQS, "request")):
        if code not in reg:
            return None, "unknown %s code %d" % (name, code)
    out = ["%s %s [%s -> %s] (%s) confidence %d, coverage %d"
           % (ACTS[a], pid, ROLES[f], ROLES[t], STATES[st], cf, cv)]
    if body.strip():
        exprs, perr = parse_all(body)
        if perr:
            return None, "body: " + perr
        for e in exprs:
            if check_expr(e):
                return None, "body: malformed expression"
            r = render_expr(e)
            if r is None:
                return None, "body: cannot render expression"
            out.append(r)
    if rq:
        out.append("Requires: %s." % RQS[rq])
    if base:
        out.append("Base: %s." % base)
    if exp:
        out.append("Expires in %ds." % exp)
    return "\n".join(out), None


def main(argv):
    if len(argv) != 2:
        print("usage: sym2-render.py <packet-or-file>", file=sys.stderr)
        return 2
    src = argv[1]
    try:
        with open(src) as fh:
            lines = fh.read().splitlines()
    except OSError:
        lines = [src]
    failed = False
    for i, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue
        text, err = render_packet(line)
        if err:
            print("line %d: %s" % (i, err), file=sys.stderr)
            failed = True
        else:
            print(text)
            print()
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
