#!/usr/bin/env python3
"""Validate SYM-2P v2 dense packet lines.

Checks field count, token shapes, registry codes, numeric ranges, and
body s-expression shape against SPEC-V2-DRAFT.md. stdlib only.

Usage: sym2-validate.py <packet-or-file>
Exit codes: 0 every line valid, 1 at least one invalid with a typed
diagnostic, 2 usage, IO, or configuration error.
"""
import re
import sys

TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/-]*$")
BASE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/-]*:[A-Za-z0-9][A-Za-z0-9_.:/-]*$")
ROLES = set(range(0, 7))
ACTS = set(range(0, 11))
STATES = set(range(0, 9))
RQS = set(range(0, 3))


def tokenize(text):
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
    return tokens


def parse_all(tokens):
    def parse(pos):
        pos += 1  # consume '('
        items = []
        while pos < len(tokens) and tokens[pos] != ")":
            if tokens[pos] == "(":
                sub, pos = parse(pos)
                items.append(sub)
            else:
                items.append(tokens[pos])
                pos += 1
        if pos >= len(tokens):
            raise ValueError("unbalanced parentheses")
        return items, pos + 1

    exprs, pos = [], 0
    while pos < len(tokens):
        if tokens[pos] != "(":
            raise ValueError("top-level atom outside expression")
        expr, pos = parse(pos)
        exprs.append(expr)
    return exprs


SYM = re.compile(r"^(?:\*|[A-Za-z][A-Za-z0-9_/.]*)$")


def is_num(t):
    return isinstance(t, str) and t.isdigit()


def is_sym(t):
    return isinstance(t, str) and bool(SYM.match(t))


def as_op(e, want):
    if not isinstance(e, list) or not e or e[0] != str(want):
        return "want (%d ...)" % want
    return check_expr(e)


def check_expr(e):
    if not isinstance(e, list) or not e:
        return "empty expression"
    if not (isinstance(e[0], str) and e[0].isdigit()):
        return "expression head is not an opcode"
    op, args = int(e[0]), e[1:]
    if op == 10:
        if len(args) != 2 or not is_sym(args[0]):
            return "scope wants (10 target impl)"
        return as_op(args[1], 20)
    if op == 11:
        if len(args) != 1:
            return "constraint wants (11 constraint)"
        return as_op(args[0], 21)
    if op == 12:
        if len(args) != 1:
            return "accept wants (12 accept)"
        return as_op(args[0], 22)
    if op == 20:
        if len(args) != 2 or not is_sym(args[0]):
            return "impl wants (20 unit range)"
        r = args[1]
        if not (isinstance(r, list) and len(r) == 2
                and is_num(r[0]) and is_num(r[1])):
            return "range wants (lo hi)"
        return None
    if op == 21:
        if len(args) != 1 or not is_sym(args[0]):
            return "nomod wants (21 paths)"
        return None
    if op == 22:
        if len(args) != 3 or not is_sym(args[0]) \
                or not is_num(args[1]) or not is_num(args[2]):
            return "exit wants (22 prog ok bad)"
        return None
    return "unknown opcode %d" % op


def check_sexpr(text):
    if not text.strip():
        return None
    try:
        exprs = parse_all(tokenize(text))
    except ValueError as ex:
        return str(ex)
    for e in exprs:
        err = check_expr(e)
        if err:
            return err
    return None


def check_line(line, lineno):
    errs = []

    def err(code, msg):
        errs.append("ERR:%s line %d: %s" % (code, lineno, msg))

    fields = line.split("|")
    if len(fields) != 13:
        err("SHAPE", "want 13 fields, have %d" % len(fields))
        return errs
    if fields[0] != "2":
        err("SHAPE", "want wire version 2")
    v, pid, tk, f, t, a, st, cf, cv, body, rq, base, exp = fields
    for name, tok in (("ID", pid), ("TK", tk)):
        if not TOKEN.match(tok):
            err("TOKEN", "%s fails token pattern" % name)
    if base and not BASE.match(base):
        err("TOKEN", "BASE is neither empty nor id:ver")
    nums = {}
    for name, raw in (("F", f), ("T", t), ("A", a), ("ST", st), ("CF", cf),
                      ("CV", cv), ("RQ", rq), ("EXP", exp)):
        if not re.fullmatch(r"\d+", raw):
            err("TYPE", "%s is not an unsigned integer" % name)
            continue
        nums[name] = int(raw)
    if "F" in nums and nums["F"] not in ROLES:
        err("CODE", "F=%d outside role registry" % nums["F"])
    if "T" in nums and nums["T"] not in ROLES:
        err("CODE", "T=%d outside role registry" % nums["T"])
    if "A" in nums and nums["A"] not in ACTS:
        err("CODE", "A=%d outside act registry" % nums["A"])
    if "ST" in nums and nums["ST"] not in STATES:
        err("CODE", "ST=%d outside state registry" % nums["ST"])
    if "RQ" in nums and nums["RQ"] not in RQS:
        err("CODE", "RQ=%d outside request registry" % nums["RQ"])
    for name in ("CF", "CV"):
        if name in nums and not 0 <= nums[name] <= 100:
            err("RANGE", "%s=%d outside 0-100" % (name, nums[name]))
    if "|" in body:
        err("SHAPE", "BODY contains the field separator")
    else:
        berr = check_sexpr(body)
        if berr:
            err("BODY", berr)
    if re.search(r"\( | \)|  ", body):
        err("CANON", "BODY spacing is not canonical")
    return errs


def main(argv):
    if len(argv) != 2:
        print("usage: sym2-validate.py <packet-or-file>", file=sys.stderr)
        return 2
    src = argv[1]
    try:
        with open(src) as fh:
            lines = fh.read().splitlines()
    except OSError:
        lines = [src]
    bad = 0
    for i, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue
        for e in check_line(line, i):
            print(e, file=sys.stderr)
            bad += 1
    if bad:
        print("%d invalid line(s)" % bad, file=sys.stderr)
        return 1
    print("all lines valid")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
