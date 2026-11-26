#!/usr/bin/env python3
"""Seeded end-to-end fuzz for ABIOS/3 wire lists (bare [a;b] + strict J: fallback).

Each case builds a random JSON-native list, then checks three things:
  1. codec: decode_wire_list(encode_wire_list(x)) == x with exact types;
  2. tokenizer: the token survives encoders._split_line inside a line
     (``X <tok> Y`` splits into exactly three tokens, the middle one unchanged);
  3. line: a refs-encoded task.create carrying the list in ``criteria`` and
     ``scope`` decodes back to an equal message through RefsEncoder.decode
     (which runs _split_line and coerce_wire_types).

Usage: python3 scripts/protean-abios/fuzz_wire_lists.py [--n 200000] [--seed 1]
Exit status 0 means zero failures.
"""
from __future__ import annotations

import argparse
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from canonical import canonical_payload, messages_equal  # noqa: E402
from encoders import RefsEncoder, _split_line, fresh_session  # noqa: E402
import wire_lists as wl  # noqa: E402

ATOMS = [
    "", " ", "  ", "\t", "a", "b c", "a  b", " lead", "trail ", "1,2", "1", "0", "42", "-1",
    "1.5", "2e3", "true", "false", "null", "p", "t", "a", "h", "f", "v", "g", "-", "http://x",
    "https://y z", "see [1] now", "a]b", "[x", "a] b", "{k}", "x;y", ";", "a\\", "\\", "\\e",
    "a\\;b", 'q"', "line\nnext", "cr\rx", "u\u00a0v", "l\u2028s", "é ü", "日本語 テスト",
    "S[a;b]", "S[", "J:[1]", "J:", "[]", "%20", "%25", "%", "#1", "#h0a", "\x7f", "\x1f",
    "Round-trip lossless", "Reported by agent; not executed by forge.",
]


def rand_scalar(rng: random.Random):
    r = rng.random()
    if r < 0.70:
        if rng.random() < 0.8:
            return rng.choice(ATOMS)
        return "".join(rng.choice(ATOMS) for _ in range(rng.randint(1, 3)))
    if r < 0.80:
        return rng.choice([rng.randint(-5, 5), rng.randint(-(2**70), 2**70)])
    if r < 0.86:
        return rng.choice([1.5, -0.25, 0.0, -0.0, 1e300, 3.0])
    if r < 0.93:
        return rng.choice([True, False])
    return None


def rand_value(rng: random.Random, depth: int = 0):
    r = rng.random()
    if depth < 2 and r < 0.06:
        return [rand_value(rng, depth + 1) for _ in range(rng.randint(0, 3))]
    if depth < 2 and r < 0.10:
        return {rng.choice(["k", "a b", "", "J:"]): rand_value(rng, depth + 1) for _ in range(rng.randint(0, 2))}
    return rand_scalar(rng)


def rand_list(rng: random.Random):
    n = rng.choice([0, 1, 1, 2, 2, 3, 4, 6])
    if rng.random() < 0.6:
        return [rand_scalar_str(rng) for _ in range(n)]
    return [rand_value(rng) for _ in range(n)]


def rand_scalar_str(rng: random.Random) -> str:
    v = rng.choice(ATOMS)
    return v if rng.random() < 0.8 else v + rng.choice(ATOMS)


def exact(a, b) -> bool:
    if type(a) is not type(b):
        return False
    if type(a) is list:
        return len(a) == len(b) and all(exact(x, y) for x, y in zip(a, b))
    if type(a) is dict:
        return a.keys() == b.keys() and all(exact(a[k], b[k]) for k in a)
    if type(a) is float:
        return a == b and str(a) == str(b)
    return a == b


def run(n: int, seed: int) -> dict:
    rng = random.Random(seed)
    enc = RefsEncoder()
    stats = {"cases": 0, "bare": 0, "j": 0, "empty": 0, "codec_fail": 0, "split_fail": 0, "line_fail": 0, "second_lines": 0, "second_with_ref": 0}
    first = []
    for _ in range(n):
        items = rand_list(rng)
        stats["cases"] += 1
        tok = wl.encode_wire_list(items)
        kind = "empty" if tok == "[]" else ("j" if tok.startswith("J:") else "bare")
        stats[kind] += 1
        try:
            ok = exact(wl.decode_wire_list(tok), items)
        except ValueError:
            ok = False
        if not ok:
            stats["codec_fail"] += 1
            first.append(("codec", items, tok))
        parts = _split_line(f"X {tok} Y")
        if [p.text for p in parts] != ["X", tok, "Y"] or parts[1].quoted:
            stats["split_fail"] += 1
            first.append(("split", items, tok))
        crit = items
        scope = rand_list(rng)
        msg = ("task.create", canonical_payload("task.create", {
            "project_id": "a1" * 16, "title": "t", "description": "d", "criteria": crit,
            "scope": scope, "priority": "normal", "dependencies": [],
        }))
        try:
            s_enc, s_dec = fresh_session(), fresh_session()
            line = enc.encode(msg[0], msg[1], s_enc)
            got = enc.decode(line, s_dec)
            ok = messages_equal(msg, got) and exact(got[1]["criteria"], crit) and exact(got[1]["scope"], scope)
            if ok and stats["cases"] % 4 == 0:
                # Second identical message in the same session: long lists come back as #n content refs.
                s_enc.apply_message(msg[0], msg[1])
                s_dec.apply_message(got[0], got[1])
                line2 = enc.encode(msg[0], msg[1], s_enc)
                got2 = enc.decode(line2, s_dec)
                stats["second_lines"] += 1
                stats["second_with_ref"] += int("#" in line2)
                ok = messages_equal(msg, got2) and exact(got2[1]["criteria"], crit)
                line = line + " || " + line2
        except ValueError as exc:
            ok = False
            line = f"<{exc}>"
        if not ok:
            stats["line_fail"] += 1
            first.append(("line", items, line))
        if len(first) > 5:
            first = first[:5]
    stats["examples"] = first
    return stats


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--n", type=int, default=200000)
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()
    s = run(args.n, args.seed)
    fails = s["codec_fail"] + s["split_fail"] + s["line_fail"]
    print(f"seed={args.seed} cases={s['cases']} bare={s['bare']} j={s['j']} empty={s['empty']} "
          f"second_lines={s['second_lines']} second_with_ref={s['second_with_ref']} "
          f"codec_fail={s['codec_fail']} split_fail={s['split_fail']} line_fail={s['line_fail']}")
    for ex in s["examples"]:
        print("  example:", repr(ex)[:300])
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
