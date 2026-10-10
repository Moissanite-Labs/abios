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


def frag(e):
    """Render an expression or atom as an inline fragment."""
    if isinstance(e, str):
        return e[1:] if e.startswith("$") else e
    if not e:
        return ""
    op = int(e[0])
    args = e[1:]
    if op == 20:
        unit = UNITS.get(args[0], str(args[0]))
        r = args[1]
        if isinstance(r, list):
            if r[0] == r[1]:
                return "implement section %s" % frag(r[0])
            return "implement sections %s-%s" % (frag(r[0]), frag(r[1]))
        return "implement section %s" % frag(r)
    if op == 21:
        if args[0] == "*":
            return "modify no existing paths"
        return "modify no paths matching %s" % frag(args[0])
    if op == 22:
        return "%s exits %s on valid input, %s on invalid" % (
            frag(args[0]), args[1], args[2])
    if op == 30:
        return "let %s = %s" % (args[0], frag(args[1]))
    if op == 31:
        s = "if %s then %s" % (frag(args[0]), frag(args[1]))
        if args[2]:
            s += ", otherwise %s" % frag(args[2])
        return s
    if op == 32:
        return "for each %s in %s: %s" % (
            args[0], frag(args[1]), frag(args[2]))
    if op == 33:
        return "[%s]" % ", ".join(frag(x) for x in args)
    if op == 34:
        return "%s < %s" % (frag(args[0]), frag(args[1]))
    if op == 35:
        return "%s = %s" % (frag(args[0]), frag(args[1]))
    if op == 40:
        role = ROLES.get(int(args[0]), str(args[0]))
        return "spawn %s on thread %s to %s" % (
            role, args[1], frag(args[2]))
    return None


def render_expr(expr):
    """Render a top-level body expression as one English sentence."""
    op = int(expr[0])
    args = expr[1:]
    if op == 10:
        return "Scope: %s of %s." % (frag(args[1]), args[0])
    if op == 11:
        return "Constraint: %s." % frag(args[0])
    if op == 12:
        return "Acceptance: %s." % frag(args[0])
    s = frag(expr)
    if s is None:
        return None
    return s[0].upper() + s[1:] + "."


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
            cerr = check_expr(e)
            if cerr:
                return None, "body: " + cerr
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
