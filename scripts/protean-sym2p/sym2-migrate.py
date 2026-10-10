#!/usr/bin/env python3
"""Migrate SYM-2P v1 JSON packets to v2 dense lines.

Structured fields map directly through the registries. The English
cond strings map through known patterns; a cond that matches no known
pattern fails loudly instead of being guessed at.

Accepts a JSONL file (one packet per line) or a single JSON document,
such as the repo's pretty-printed templates.

Usage: sym2-migrate.py <v1-packets>
Exit codes: 0 every packet migrated, 1 at least one packet
unmigratable, 2 usage, IO, or configuration error.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

V1_ROLES = {"cos": 1, "builder": 2, "verifier": 3, "scout": 4,
            "critic": 5, "operator": 6}
V1_ACTS = {"assign": 1, "ack": 2, "assert": 3, "update": 4, "receipt": 5,
           "challenge": 6, "dispute": 7, "authorize": 8, "query": 9,
           "inform": 10}
V1_STATES = {"proposed": 1, "accepted": 2, "rejected": 3, "verified": 4,
             "open": 5, "closed": 6, "superseded": 7, "expired": 8}
V1_RQS = {"ack": 1, "verify": 2}

SCOPE_RE = re.compile(r"^scope: implement (\S+) sections (\d+)-(\d+)", re.I)
NOMOD_RE = re.compile(r"^constraint: no existing paths? may be modified", re.I)
ACCEPT_RE = re.compile(r"^acceptance: (\S+) exits (\d+) on valid \S+, "
                       r"non-zero on invalid", re.I)


def migrate_cond(cond):
    m = SCOPE_RE.match(cond)
    if m:
        return "(10 %s (20 sec (%s %s)))" % (m.group(1), m.group(2), m.group(3))
    if NOMOD_RE.match(cond):
        return "(11 (21 *))"
    m = ACCEPT_RE.match(cond)
    if m:
        return "(12 (22 %s %s 1))" % (m.group(1), m.group(2))
    return None


def lookup(table, value, field):
    if value not in table:
        return None, "unknown v1 %s %r" % (field, value)
    return table[value], None


def migrate(obj, lineno):
    def fail(msg):
        return None, "line %d: %s" % (lineno, msg)

    if not isinstance(obj, dict):
        return fail("not a JSON object")
    f, err = lookup(V1_ROLES, obj.get("f"), "role")
    if err:
        return fail(err)
    t, err = lookup(V1_ROLES, obj.get("t"), "role")
    if err:
        return fail(err)
    a, err = lookup(V1_ACTS, obj.get("a"), "act")
    if err:
        return fail(err)
    st, err = lookup(V1_STATES, obj.get("st"), "state")
    if err:
        return fail(err)
    rq = V1_RQS.get(obj.get("rq"), 0)
    body = []
    for cond in obj.get("cond", []):
        expr = migrate_cond(cond)
        if expr is None:
            return fail("cond has no v2 pattern: %r" % cond)
        body.append(expr)
    for name in ("cf", "cov", "exp"):
        v = obj.get(name, 0)
        if not isinstance(v, int) or v < 0:
            return fail("%s is not a non-negative integer" % name)
    fields = ["2", str(obj.get("id", "")), str(obj.get("tk", "")),
              str(f), str(t), str(a), str(st),
              str(obj.get("cf", 0)), str(obj.get("cov", 0)),
              "".join(body), str(rq), str(obj.get("base", "")),
              str(obj.get("exp", 0))]
    return "|".join(fields), None


def read_packets(path):
    """Read v1 packets from a JSONL file or a single JSON document.

    Returns a list of (obj, lineno) or raises ValueError on bad input.
    """
    with open(path) as fh:
        raw = fh.read()
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            return [(obj, 1)]
    except json.JSONDecodeError:
        pass
    packets = []
    for i, line in enumerate(raw.splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            packets.append((json.loads(line), i))
        except json.JSONDecodeError as ex:
            raise ValueError("line %d: invalid JSON: %s" % (i, ex))
    return packets


def main(argv):
    if len(argv) != 2:
        print("usage: sym2-migrate.py <v1-packets>", file=sys.stderr)
        return 2
    try:
        packets = read_packets(argv[1])
    except OSError as ex:
        print("cannot read %s: %s" % (argv[1], ex), file=sys.stderr)
        return 2
    except ValueError as ex:
        print(ex, file=sys.stderr)
        return 2
    bad = 0
    for obj, i in packets:
        out, err = migrate(obj, i)
        if err:
            print(err, file=sys.stderr)
            bad += 1
        else:
            print(out)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
