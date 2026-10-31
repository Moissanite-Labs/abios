#!/usr/bin/env python3
"""ABIOS benchmark with honest decoder setup and break-even analysis."""
from __future__ import annotations

import json
import sys

from schemas.synbios.sym2p.codec import EncodeContext, encode_command

from decoder_context import cached_setup_cost, setup_sizes
from decode_rules import REFS_DECODE_RULES
from encoders import all_encoders, encode_transcript, fresh_session
from english import render_english_lossless, render_english_lossy
from schemas.synbios.fixtures import (
    lifecycle_11,
    lifecycle_11_random,
    lifecycle_40,
    lifecycle_40_random,
    lifecycle_200,
    lifecycle_200_random,
    lifecycle_hex_aliases,
    lifecycle_session_ids,
)
from lexicon import load_lexicon
from prior_art import (
    AGORA_ARXIV,
    agora_setup_prefix,
    encode_agora_line,
    encode_terse_english_line,
    encode_toon_line,
)
from tokens import load_tokenizers, token_count

V2_SESSION_STEADY_TOKENS_11 = 1202
V2_SESSION_HANDSHAKE_TOTAL_11 = 1415
V2_HANDSHAKE_TOKENS_11 = V2_SESSION_HANDSHAKE_TOTAL_11 - V2_SESSION_STEADY_TOKENS_11
# Measured negative results from synbios PR #6 dense pilot (o200k_base, lifecycle_11).
V2_RAW_MESSAGES_TOKENS_11 = 3386
V2_COMPACT_JSON_MESSAGES_11 = 683
SYM2P_V1_MESSAGES_11_PILOT = 2720
TERSE_ENGLISH_LABEL = "English (lossless, key=value one-line)"

CACHE_ASSUMPTION = "Assumes one-time decoder prefix billed at 10% of min setup tokens (not API-measured)."
PRIMARY_NOTE = (
    "**Primary accounting** (used in break-even and verdict): total = setup (min, decode-sufficient) + messages."
)


def _sym2p_v1_lines(messages: list[tuple[str, dict]]) -> list[str]:
    project_hex = "a1" * 16
    task_hex = "b2" * 16
    sender_hex = "d4" * 16
    agent_hex = "c3" * 16
    step = 1
    lines: list[str] = []
    for index, (action, payload) in enumerate(messages, start=1):
        ctx = EncodeContext(
            packet_id=f"c{index:03d}",
            project_hex=project_hex,
            task_hex=task_hex if action not in {"project.create"} else None,
            sender_hex=sender_hex
            if action not in {"task.claim", "task.transition", "artifact.add", "evidence.add"}
            else agent_hex,
            sender_human=action
            in {
                "project.create",
                "principal.create",
                "grant.create",
                "grant.revoke",
                "task.create",
                "review.create",
            },
            step=step,
        )
        step += 1
        lines.append(encode_command(action, payload, ctx))
    return lines


def _tok(specs, text: str) -> dict[str, int]:
    return {s.name: token_count(text, s) for s in specs}


def _primary(specs):
    return specs[0].name if specs else "n/a"


def _cumulative_crossover(
    setup_min: float,
    enc_lines: list[str],
    baseline_lines: list[str],
    spec,
) -> int | None:
    for i in range(1, len(enc_lines) + 1):
        enc_total = setup_min + token_count("\n".join(enc_lines[:i]), spec)
        base_total = token_count("\n".join(baseline_lines[:i]), spec)
        if enc_total < base_total:
            return i
    return None


def _row_from_lines(
    label: str,
    lines: list[str],
    specs,
    primary: str,
    *,
    setup_min: int = 0,
    setup_full: int = 0,
) -> dict:
    blob = "\n".join(lines)
    msg_counts = _tok(specs, blob)
    msgs = msg_counts.get(primary, 0)
    cached = cached_setup_cost(setup_min)
    return {
        "label": label,
        "setup_min": {primary: setup_min},
        "setup_full": {primary: setup_full},
        "setup_cached": {primary: cached},
        "messages": msg_counts,
        "total_primary": {primary: setup_min + msgs},
        "total_full": {primary: setup_full + msgs},
        "total_cached": {primary: cached + msgs},
        "msg_rate": msgs / len(lines) if lines else 0,
        "setup_min_n": setup_min,
    }


def run_bench_for_transcript(
    name: str,
    messages: list[tuple[str, dict]],
    *,
    session_ids: dict[str, str] | None = None,
    hex_aliases: dict[str, str] | None = None,
) -> dict:
    specs = load_tokenizers()
    primary = _primary(specs)
    lex = load_lexicon()
    encoders = all_encoders(lex)
    n = len(messages)

    compact_json_lines = [
        json.dumps({"action": a, **p}, sort_keys=True, separators=(",", ":")) for a, p in messages
    ]
    pretty_json_lines = [
        json.dumps({"action": a, **p}, sort_keys=True, indent=2) for a, p in messages
    ]
    english_lossy_lines = [render_english_lossy(a, p) for a, p in messages]
    english_lossless_lines = [render_english_lossless(a, p) for a, p in messages]
    terse_lines = [encode_terse_english_line(a, p) for a, p in messages]
    toon_lines = [encode_toon_line(a, p) for a, p in messages]
    agora_lines = [encode_agora_line(a, p) for a, p in messages]
    agora_setup = agora_setup_prefix()
    agora_setup_tok = token_count(agora_setup, specs[0]) if specs else 0
    v1_lines = _sym2p_v1_lines(messages)

    rows: list[dict] = []
    rows.append(_row_from_lines("compact JSON", compact_json_lines, specs, primary))
    rows.append(_row_from_lines("pretty JSON", pretty_json_lines, specs, primary))
    rows.append(_row_from_lines("English (lossy summary)", english_lossy_lines, specs, primary))
    rows.append(_row_from_lines("English (lossless)", english_lossless_lines, specs, primary))
    rows.append(_row_from_lines(TERSE_ENGLISH_LABEL, terse_lines, specs, primary))
    rows.append(_row_from_lines("TOON (approx in-repo fallback)", toon_lines, specs, primary))
    rows.append(
        _row_from_lines(
            f"Agora envelope (arXiv:{AGORA_ARXIV})",
            agora_lines,
            specs,
            primary,
            setup_min=agora_setup_tok,
            setup_full=agora_setup_tok,
        )
    )
    rows.append(_row_from_lines("SYM-2P v1", v1_lines, specs, primary))

    if name == "lifecycle_11":
        rows.append(
            {
                "label": "SYM-2P v2 session + handshake (PR #6)",
                "setup_min": {primary: V2_HANDSHAKE_TOKENS_11},
                "setup_full": {primary: V2_HANDSHAKE_TOKENS_11},
                "setup_cached": {primary: cached_setup_cost(V2_HANDSHAKE_TOKENS_11)},
                "messages": {primary: V2_SESSION_STEADY_TOKENS_11},
                "total_primary": {primary: V2_SESSION_HANDSHAKE_TOTAL_11},
                "total_full": {primary: V2_SESSION_HANDSHAKE_TOTAL_11},
                "total_cached": {
                    primary: cached_setup_cost(V2_HANDSHAKE_TOKENS_11) + V2_SESSION_STEADY_TOKENS_11
                },
                "note": "External constants from synbios PR #6 dense pilot (not live-measured in this repo)",
            }
        )
        rows.append(
            {
                "label": "SYM-2P v2 dense raw (PR #6)",
                "setup_min": {primary: 0},
                "setup_full": {primary: 0},
                "setup_cached": {primary: 0.0},
                "messages": {primary: V2_RAW_MESSAGES_TOKENS_11},
                "total_primary": {primary: V2_RAW_MESSAGES_TOKENS_11},
                "total_full": {primary: V2_RAW_MESSAGES_TOKENS_11},
                "total_cached": {primary: float(V2_RAW_MESSAGES_TOKENS_11)},
                "note": f"vs compact JSON {V2_COMPACT_JSON_MESSAGES_11} messages-only (pilot)",
            }
        )
        rows.append(
            {
                "label": "SYM-2P v1 (PR #6 pilot reference)",
                "setup_min": {primary: 0},
                "setup_full": {primary: 0},
                "setup_cached": {primary: 0.0},
                "messages": {primary: SYM2P_V1_MESSAGES_11_PILOT},
                "total_primary": {primary: SYM2P_V1_MESSAGES_11_PILOT},
                "total_full": {primary: SYM2P_V1_MESSAGES_11_PILOT},
                "total_cached": {primary: float(SYM2P_V1_MESSAGES_11_PILOT)},
                "note": "pilot transcript; live bench row below uses this repo codec",
            }
        )

    sym3_rows: list[dict] = []
    for enc_name, enc in encoders.items():
        lines = encode_transcript(enc, messages, session=fresh_session(session_ids, hex_aliases))
        sizes = setup_sizes(
            messages,
            lines,
            lex,
            session_ids=session_ids,
            hex_aliases=hex_aliases,
        )
        post_setup = sizes["post_minimal"]
        row = _row_from_lines(
            f"ABIOS {enc_name}",
            lines,
            specs,
            primary,
            setup_min=post_setup,
            setup_full=sizes["post_full"],
        )
        if enc_name == "refs":
            row["note"] = f"closest prior art: Agora (arXiv:{AGORA_ARXIV})"
        rows.append(row)
        sym3_rows.append(row)

    break_even: dict[str, dict] = {}
    for row in sym3_rows:
        enc = row["label"].replace("ABIOS ", "")
        enc_lines = encode_transcript(
            encoders[enc],
            messages,
            session=fresh_session(session_ids, hex_aliases),
        )
        setup_used = row["setup_min_n"]
        break_even[enc] = {
            "vs_compact_json": _cumulative_crossover(
                setup_used, enc_lines, compact_json_lines, specs[0]
            ),
            "vs_english_lossless": _cumulative_crossover(
                setup_used, enc_lines, english_lossless_lines, specs[0]
            ),
        }

    return {
        "transcript": name,
        "count": n,
        "tokenizers": [s.name for s in specs],
        "rows": rows,
        "break_even": break_even,
    }


def format_markdown(results: list[dict], primary: str, *, rules_tokens: int = 0) -> str:
    lines = [
        "# ABIOS benchmark",
        "",
        PRIMARY_NOTE,
        "Secondary: setup (full, committed lexicon + full schema). "
        f"Tertiary: setup (cached†) = 10% × setup (min). {CACHE_ASSUMPTION}",
        "",
        "Minimal setup is **decode-sufficient**: all used cmd/status/kind wire mappings and format tags "
        "for the transcript (plus all format tags when `adaptive` appears). "
        "Primary setup (min) counts POST ack line plus minimal decoder context (section 8.1).",
        "",
        f"REFS decode rules overhead (informative, `decode_rules.py`): **{rules_tokens}** tokens ({primary}).",
        "",
    ]
    for block in results:
        lines.append(f"## {block['transcript']} ({block['count']} messages)")
        lines.append("")
        header = (
            "| Format | setup (min) | messages | total (primary) | "
            "setup (full) | total (full setup) | setup (cached†) | total (cached†) |"
        )
        sep = "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"
        lines.extend([header, sep])
        for row in block["rows"]:
            sm = row["setup_min"].get(primary, 0)
            sf = row["setup_full"].get(primary, 0)
            sc = row["setup_cached"].get(primary, 0.0)
            msgs = row["messages"].get(primary, 0)
            tp = row["total_primary"].get(primary, sm + msgs)
            tf = row["total_full"].get(primary, sf + msgs)
            tc = row["total_cached"].get(primary, sc + msgs)
            note = row.get("note", "")
            label = row["label"] if not note else f"{row['label']} — {note}"
            lines.append(
                f"| {label} | {sm} | {msgs} | {tp} | {sf} | {tf} | {sc:.1f} | {tc:.1f} |"
            )
        lines.append("")
        lines.append("### Cumulative crossover (primary accounting: POST + setup min + messages)")
        lines.append("")
        lines.append(
            "| Encoder | msgs before total beats compact JSON | msgs before total beats English (lossless) |"
        )
        lines.append("| --- | ---: | ---: |")
        for enc, be in sorted(block["break_even"].items()):
            c = be["vs_compact_json"]
            e = be["vs_english_lossless"]
            lines.append(
                f"| {enc} | {'never' if c is None else c} | {'never' if e is None else e} |"
            )
        lines.append("")

    lines.append("## Verdict (primary accounting, o200k_base)")
    lines.append("")
    l11 = next(b for b in results if b["transcript"] == "lifecycle_11")
    l11r = next(b for b in results if b["transcript"] == "lifecycle_11_random")
    refs = next(r for r in l11["rows"] if r["label"] == "ABIOS refs")
    adaptive = next(r for r in l11["rows"] if r["label"] == "ABIOS adaptive")
    compact = next(r for r in l11["rows"] if r["label"] == "compact JSON")
    english = next(r for r in l11["rows"] if r["label"] == "English (lossless)")
    toon = next(r for r in l11["rows"] if "TOON" in r["label"])
    primary = _primary(load_tokenizers())
    refs_total = refs["total_primary"][primary]
    refs_random = next(r for r in l11r["rows"] if r["label"] == "ABIOS refs")["total_primary"][primary]
    adaptive_total = adaptive["total_primary"][primary]
    compact_total = compact["total_primary"][primary]
    compact_random = next(r for r in l11r["rows"] if r["label"] == "compact JSON")["total_primary"][primary]
    english_total = english["total_primary"][primary]
    toon_total = toon["total_primary"][primary]
    lines.append(
        f"On lifecycle_11 (fixture hex), ABIOS **refs** total **{refs_total}** vs compact JSON **{compact_total}** "
        f"and lossless English **{english_total}** (primary = POST + minimal setup + messages). "
        f"Same task with **seeded random hex ids** (see `lifecycle_*_random`): refs **{refs_random}** vs JSON **{compact_random}**. "
        f"**Adaptive** total **{adaptive_total}**. TOON fallback row **{toon_total}** (approximation). "
        "lifecycle_40/200 repeat many messages verbatim, which inflates refs savings; see transcript notes. "
        "SYM-2P v2 rows are external PR #6 constants, not live bench output."
    )
    lines.append("")
    return "\n".join(lines) + "\n"


def compute_bench_payload() -> tuple[list[dict], str, str, dict]:
    specs = load_tokenizers()
    primary = _primary(specs)
    rules_tokens = token_count(REFS_DECODE_RULES, specs[0]) if specs else 0
    assert len(lifecycle_11()) == 11 and len(lifecycle_40()) == 40 and len(lifecycle_200()) == 200
    fixture_results = [
        run_bench_for_transcript("lifecycle_11", lifecycle_11()),
        run_bench_for_transcript("lifecycle_40", lifecycle_40()),
        run_bench_for_transcript("lifecycle_200", lifecycle_200()),
    ]
    random_seed = 1
    random_results = [
        run_bench_for_transcript(
            "lifecycle_11_random",
            lifecycle_11_random(random_seed),
            session_ids=lifecycle_session_ids(random_seed),
            hex_aliases=lifecycle_hex_aliases(random_seed),
        ),
        run_bench_for_transcript(
            "lifecycle_40_random",
            lifecycle_40_random(random_seed),
            session_ids=lifecycle_session_ids(random_seed),
            hex_aliases=lifecycle_hex_aliases(random_seed),
        ),
        run_bench_for_transcript(
            "lifecycle_200_random",
            lifecycle_200_random(random_seed),
            session_ids=lifecycle_session_ids(random_seed),
            hex_aliases=lifecycle_hex_aliases(random_seed),
        ),
    ]
    results = fixture_results + random_results
    md = format_markdown(results, primary, rules_tokens=rules_tokens)
    meta = {"refs_decode_rules_tokens": rules_tokens, "random_id_seed": random_seed}
    return results, md, primary, meta


def _normalize_md(text: str) -> str:
    return text.replace("\r\n", "\n").strip() + "\n"


def _strip_git(payload: dict) -> dict:
    out = dict(payload)
    out.pop("git_sha", None)
    out.pop("git_short", None)
    return out


def _git_identifiers(root) -> tuple[str, str]:
    import subprocess

    try:
        git_sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True
        ).strip()
        git_short = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=root, text=True
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        git_sha = "unknown"
        git_short = "unknown"
    return git_sha, git_short


def verify_against_committed(results: list[dict], md: str, primary: str, root, meta: dict) -> None:
    from pathlib import Path

    md_path = Path(root) / "docs" / "abios-bench.md"
    json_path = Path(root) / "bench" / "results" / "abios-bench.json"
    if not md_path.is_file():
        raise SystemExit(f"Missing committed benchmark tables: {md_path}")
    if not json_path.is_file():
        raise SystemExit(f"Missing committed benchmark JSON: {json_path}")

    committed_md = _normalize_md(md_path.read_text(encoding="utf-8"))
    generated_md = _normalize_md(md)
    if committed_md != generated_md:
        raise SystemExit(
            f"ABIOS benchmark mismatch: generated markdown differs from {md_path}. "
            "Re-run with --write after intentional bench changes."
        )

    with json_path.open(encoding="utf-8") as f:
        expected = _strip_git(json.load(f))
    generated = _strip_git(
        {
            "primary_tokenizer": primary,
            "tokenizers": [s.name for s in load_tokenizers()],
            "meta": meta,
            "results": results,
        }
    )
    if expected != generated:
        raise SystemExit(
            f"ABIOS benchmark mismatch: generated JSON differs from {json_path} "
            "(ignoring git sha fields). Re-run with --write after intentional bench changes."
        )


def write_committed(results: list[dict], md: str, primary: str, root, meta: dict) -> None:
    from pathlib import Path

    root = Path(root)
    md_path = root / "docs" / "abios-bench.md"
    json_path = root / "bench" / "results" / "abios-bench.json"
    git_sha, git_short = _git_identifiers(root)
    md_path.write_text(_normalize_md(md), encoding="utf-8")
    payload = {
        "git_sha": git_sha,
        "git_short": git_short,
        "primary_tokenizer": primary,
        "tokenizers": [s.name for s in load_tokenizers()],
        "meta": meta,
        "results": results,
    }
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {md_path}")
    print(f"Wrote {json_path}")


def main() -> int:
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(
        description="ABIOS benchmark: default verifies committed tables; --write refreshes them."
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Overwrite docs/abios-bench.md and bench/results/abios-bench.json (not for CI).",
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    results, md, primary, meta = compute_bench_payload()
    if args.write:
        write_committed(results, md, primary, root, meta)
        print(md)
        return 0
    verify_against_committed(results, md, primary, root, meta)
    print("ABIOS benchmark verification passed (docs/abios-bench.md and bench/results/abios-bench.json).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
