#!/usr/bin/env python3
"""Render SYM-2P v2 dense packets into human-readable English.

The wire form is the agents' language: codes, numbers, expressions.
This script converts it to human syntax for operators. The rendered
form is informative, never normative.

Usage: sym2-render.py <packet-or-file>
Exit codes: 0 ok, 2 usage or IO error.
"""
import sys

ROLES = {0: "reserved", 1: "coordinator", 2: "builder", 3: "verifier",
         4: "scout", 5: "critic", 6: "operator"}
ACTS = {0: "none", 1: "assign", 2: "acknowledge", 3: "assert", 4: "update",
        5: "receipt", 6: "challenge", 7: "dispute", 8: "authorize",
        9: "query", 10: "inform"}
STATES = {0: "none", 1: "proposed", 2: "accepted", 3: "rejected",
          4: "verified", 5: "open", 6: "closed", 7: "superseded",
          8: "expired"}
RQS = {0: "none", 1: "acknowledgement required", 2: "verification required"}
UNITS = {"sec": "sections"}


def parse_sexpr(text):
    """Parse concatenated s-expressions into nested lists. Returns (exprs, error)."""
    tokens, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c in "()":
            tokens.append(c)
            i += 1
        elif c.isspace():
            i += 1
        else:
            j = i
            while j < n and not text[j].isspace() and text[j] not in "()":
                j += 1
            tokens.append(text[i:j])
            i = j

    def parse(pos):
        if pos >= len(tokens) or tokens[pos] != "(":
            return None, pos, "expected '('"
        pos += 1
        items = []
        while pos < len(tokens) and tokens[pos] != ")":
            if tokens[pos] == "(":
                sub, pos, err = parse(pos)
                if err:
                    return None, pos, err
                items.append(sub)
            else:
                items.append(tokens[pos])
                pos += 1
        if pos >= len(tokens):
            return None, pos, "unbalanced parentheses"
        return items, pos + 1, None

    exprs, pos = [], 0
    while pos < len(tokens):
        expr, pos, err = parse(pos)
        if err:
            return None, err
        exprs.append(expr)
    return exprs, None


def num(tok):
    try:
        return int(tok)
    except (TypeError, ValueError):
        return None


def render_impl(expr):
    # (20 unit (lo hi))
    if len(expr) != 3:
        return None
    unit = UNITS.get(expr[1], str(expr[1]))
    rng = expr[2]
    if isinstance(rng, list) and len(rng) == 2:
        return "implement %s %s-%s" % (unit, rng[0], rng[1])
    return None


def render_expr(expr, target_hint=None):
    if not isinstance(expr, list) or not expr:
        return None
    op = num(expr[0])
    if op == 10 and len(expr) == 3:  # scope
        inner = render_expr(expr[2], target_hint=str(expr[1]))
        if inner is None:
            return None
        return "Scope: %s of %s." % (inner, expr[1])
    if op == 20:  # impl
        return render_impl(expr)
    if op == 11 and len(expr) == 2:  # constraint
        inner = expr[1]
        if isinstance(inner, list) and num(inner[0]) == 21 and len(inner) == 2:
            if inner[1] == "*":
                return "Constraint: modify no existing paths."
            return "Constraint: modify no paths matching %s." % inner[1]
        return None
    if op == 12 and len(expr) == 2:  # accept
        inner = expr[1]
        if isinstance(inner, list) and num(inner[0]) == 22 and len(inner) == 4:
            return ("Acceptance: %s exits %s on valid input, %s on invalid."
                    % (inner[1], inner[2], inner[3]))
        return None
    return None


def render_packet(line):
    fields = line.split("|")
    if len(fields) != 13 or fields[0] != "2":
        return None, "not a v2 packet line"
    _, pid, tk, f, t, a, st, cf, cv, body, rq, base, exp = fields
    try:
        f, t, a, st, rq = int(f), int(t), int(a), int(st), int(rq)
        cf, cv, exp = int(cf), int(cv), int(exp)
    except ValueError:
        return None, "non-integer in numeric field"
    if f not in ROLES or t not in ROLES or a not in ACTS or st not in STATES \
            or rq not in RQS:
        return None, "unknown registry code"
    out = ["%s %s [%s -> %s] (%s) confidence %d, coverage %d"
           % (ACTS[a], pid, ROLES[f], ROLES[t], STATES[st], cf, cv)]
    if body.strip():
        exprs, err = parse_sexpr(body)
        if err:
            return None, "body: " + err
        for e in exprs:
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
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
