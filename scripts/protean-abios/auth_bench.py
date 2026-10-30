#!/usr/bin/env python3
"""Token cost of sealed sessions (SPEC-ABIOS-3.md section 8.2).

Default: verify docs/abios-auth-bench.md and bench/results/abios-auth-bench.json
against a fresh run, printing the generated tables on mismatch. --write
refreshes them. Refuses to run without every lexicon tokenizer, so a missing
tokenizer can never be mistaken for a bench change.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import sys
from pathlib import Path

from auth import INITIATOR, TAG_BITS_ALLOWED, _dec, render_sealed_post, seal_transcript
from decoder_context import setup_sizes
from encoders import all_encoders, encode_transcript
from lexicon import LEXICON_PATH
from post import render_post_handshake
from schemas.synbios.fixtures import lifecycle_11, lifecycle_40, lifecycle_200
from tokens import load_tokenizers, token_count

ROOT = Path(__file__).resolve().parents[2]
MD_PATH = ROOT / "docs" / "abios-auth-bench.md"
JSON_PATH = ROOT / "bench" / "results" / "abios-auth-bench.json"

# Fixed, public bench inputs: tags are pseudorandom, so token counts depend on
# them. Never use this key for anything else.
BENCH_KEY = b"abios-auth-bench-public-key-0001"
BENCH_KID = "bench"
BENCH_SID = "11111111111111111111"
ENCODER = "refs"
VARIANTS = [(64, 1), (64, 10), (128, 1), (128, 10)]
TAG_SAMPLES = 1024
TRANSCRIPTS = (("lifecycle_11", lifecycle_11), ("lifecycle_40", lifecycle_40), ("lifecycle_200", lifecycle_200))


def _require_tokenizers():
    specs = load_tokenizers()
    want = json.loads(LEXICON_PATH.read_text(encoding="utf-8"))["tokenizers"]
    have = [s.name for s in specs]
    missing = [w for w in want if w not in have]
    if missing:
        print(
            f"abios auth bench: tokenizers unavailable: {', '.join(missing)}. "
            "Install requirements-bench.txt with network access; refusing to verify or write.",
            file=sys.stderr,
        )
        raise SystemExit(2)
    return [s for s in specs if s.name in want]


def _counts(specs, text: str) -> dict[str, int]:
    return {s.name: token_count(text, s) for s in specs}


def _sealed(lines: list[str], minimal: str, tag_bits: int, seal_every: int) -> tuple[str, list[str]]:
    post, session = render_sealed_post(
        minimal, key=BENCH_KEY, kid=BENCH_KID, sid=BENCH_SID, tag_bits=tag_bits, seal_every=seal_every
    )
    return post, seal_transcript(session.sender(INITIATOR), lines, close=True)


def _transcript_rows(specs, name: str, messages) -> dict:
    primary = specs[0].name
    lines = encode_transcript(all_encoders()[ENCODER], messages)
    minimal = setup_sizes(messages, lines)["minimal_text"]
    json_lines = [json.dumps(p, sort_keys=True, separators=(",", ":")) for _, p in messages]
    plain_post = _counts(specs, render_post_handshake(minimal))
    plain_msgs = _counts(specs, "\n".join(lines))
    json_msgs = _counts(specs, "\n".join(json_lines))
    plain_total = plain_post[primary] + plain_msgs[primary]
    rows = []
    for tag_bits, seal_every in VARIANTS:
        post, wire = _sealed(lines, minimal, tag_bits, seal_every)
        _post, json_wire = _sealed(json_lines, minimal, tag_bits, seal_every)
        sealed_post = _counts(specs, post)
        sealed_msgs = _counts(specs, "\n".join(wire))
        sealed_json = _counts(specs, "\n".join(json_wire))
        overhead = sealed_post[primary] - plain_post[primary] + sealed_msgs[primary] - plain_msgs[primary]
        rows.append(
            {
                "tag_bits": tag_bits,
                "seal_every": seal_every,
                "seals": len(wire) - len(lines),
                "post_sealed": sealed_post,
                "messages_sealed": sealed_msgs,
                "total_sealed": sealed_post[primary] + sealed_msgs[primary],
                "overhead": overhead,
                "overhead_pct": round(100.0 * overhead / plain_total, 1),
                "json_messages_sealed": sealed_json,
            }
        )
    return {
        "transcript": name,
        "count": len(messages),
        "encoder": ENCODER,
        "post_plain": plain_post,
        "messages_plain": plain_msgs,
        "total_plain": plain_total,
        "json_messages_plain": json_msgs,
        "variants": rows,
    }


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _tag_token_stats(specs) -> list[dict]:
    """Tokens of a lone seal line over deterministic pseudorandom tags, for the
    decimal encoding the spec uses and for base64url, the alternative it rejects."""
    primary = specs[0]
    out = []
    for encoding, render in (("decimal", _dec), ("base64url", _b64)):
        for bits in TAG_BITS_ALLOWED:
            counts = []
            for i in range(TAG_SAMPLES):
                raw = hmac.new(BENCH_KEY, f"tag-sample-{i}".encode("ascii"), hashlib.sha256).digest()[: bits // 8]
                counts.append(token_count("~" + render(raw), primary))
            out.append(
                {
                    "encoding": encoding,
                    "tag_bits": bits,
                    "samples": TAG_SAMPLES,
                    "min": min(counts),
                    "max": max(counts),
                    "mean": round(sum(counts) / len(counts), 2),
                }
            )
    return out


def compute() -> dict:
    specs = _require_tokenizers()
    return {
        "primary_tokenizer": specs[0].name,
        "tokenizers": [s.name for s in specs],
        "encoder": ENCODER,
        "bench_kid": BENCH_KID,
        "bench_sid": BENCH_SID,
        "results": [_transcript_rows(specs, name, fn()) for name, fn in TRANSCRIPTS],
        "seal_line_tokens": _tag_token_stats(specs),
    }


def format_markdown(payload: dict) -> str:
    p = payload["primary_tokenizer"]
    out = [
        "# ABIOS sealed-session benchmark",
        "",
        "Token cost of sender authentication (SPEC-ABIOS-3.md section 8.2) on the bench lifecycles, "
        f"encoder `{payload['encoder']}`, tokenizer `{p}`. Generated by "
        "`scripts/protean-abios/auth_bench.py`; `make bench` verifies it.",
        "",
        "Accounting: plain = POST (ack line plus minimal decoder context) + message lines. "
        "Sealed = sealed POST + message lines with seal lines interleaved and a close seal at the end. "
        "Overhead is sealed minus plain. The authenticated JSON column seals compact JSON lines with the "
        "same scheme and counts messages only (no POST), which favors JSON.",
        "",
        "Bench key, kid, and sid are fixed public values, so tags (and their token counts) are reproducible.",
        "",
    ]
    for r in payload["results"]:
        out += [
            f"## {r['transcript']} ({r['count']} messages)",
            "",
            f"Plain: POST {r['post_plain'][p]} + messages {r['messages_plain'][p]} = **{r['total_plain']}**. "
            f"Compact JSON messages, unauthenticated: {r['json_messages_plain'][p]}.",
            "",
            "| tag bits | seal every | seals | POST (sealed) | messages (sealed) | total (sealed) | overhead | overhead % | JSON messages (sealed) |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        for v in r["variants"]:
            out.append(
                f"| {v['tag_bits']} | {v['seal_every']} | {v['seals']} | {v['post_sealed'][p]} | "
                f"{v['messages_sealed'][p]} | **{v['total_sealed']}** | {v['overhead']} | {v['overhead_pct']} | "
                f"{v['json_messages_sealed'][p]} |"
            )
        out.append("")
    out += [
        "## Seal line cost",
        "",
        f"Tokens of a lone seal line (`~` plus tag) over {TAG_SAMPLES} deterministic pseudorandom tags. "
        "The spec uses fixed-width decimal; base64url is the measured alternative.",
        "",
        "| encoding | tag bits | min | mean | max |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for s in payload["seal_line_tokens"]:
        out.append(f"| {s['encoding']} | {s['tag_bits']} | {s['min']} | {s['mean']} | {s['max']} |")
    return "\n".join(out) + "\n"


def _dump(payload: dict) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def main(argv: list[str]) -> int:
    write = "--write" in argv
    payload = compute()
    md, js = format_markdown(payload), _dump(payload)
    if write:
        MD_PATH.write_text(md, encoding="utf-8")
        JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
        JSON_PATH.write_text(js, encoding="utf-8")
        print(f"Wrote {MD_PATH}\nWrote {JSON_PATH}")
        return 0
    committed_md = MD_PATH.read_text(encoding="utf-8") if MD_PATH.is_file() else ""
    committed_js = JSON_PATH.read_text(encoding="utf-8") if JSON_PATH.is_file() else ""
    if committed_md == md and committed_js == js:
        print("ABIOS sealed-session bench verification passed (docs/abios-auth-bench.md and bench/results/abios-auth-bench.json).")
        return 0
    print("ABIOS sealed-session bench mismatch. Generated tables follow; review them before --write.")
    print(f"----- BEGIN {MD_PATH.relative_to(ROOT)} -----\n{md}----- END -----")
    print(f"----- BEGIN {JSON_PATH.relative_to(ROOT)} -----\n{js}----- END -----")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
