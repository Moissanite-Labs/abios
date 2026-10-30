#!/usr/bin/env python3
"""Optional LLM decode-accuracy check for ABIOS/3 wire lines (skipped in CI without API key).

Measures one thing: given the POST handshake (ack + decode-sufficient minimal
context) and the wire lines, how accurately does a model reconstruct each
message? The prompt carries the same context a reference decoder needs, so a
perfect decoder scores 100%. State-question and generation round-trip metrics
are not implemented.

Scores a live model call (OpenAI-compatible), or a saved model reply with
--predictions, so results can be reproduced without an API key.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

from canonical import ForgeMessage, canonical_payload
from decoder_context import setup_sizes
from encoders import all_encoders, encode_transcript
from post import render_post_handshake
from schemas.synbios.fixtures import lifecycle_11, lifecycle_40, lifecycle_200

FIXTURES = {"lifecycle_11": lifecycle_11, "lifecycle_40": lifecycle_40, "lifecycle_200": lifecycle_200}

PROMPT = """You decode ABIOS/3 wire lines. The first block is the POST handshake: an ack
line followed by the decoder context (lexicon, positional schema, session ids,
schema defaults). Then come the wire lines, one message per line, in order;
session state (ids, refs, prior task state) carries from line to line.
Decode each wire line to a JSON object with keys "cmd" (the forge command name)
and "payload" (the full payload, with schema defaults filled in).
Return a JSON array only, one object per wire line, same order."""


def build_prompt(encoder: str, messages: list[ForgeMessage]) -> tuple[str, list[dict[str, Any]]]:
    """Return (user prompt, expected decodes) for one encoder over one transcript."""
    lines = encode_transcript(all_encoders()[encoder], messages)
    post = render_post_handshake(setup_sizes(messages, lines)["minimal_text"])
    user = post + "\nWIRE LINES:\n" + "\n".join(lines) + "\n"
    expected = [{"cmd": a, "payload": canonical_payload(a, p)} for a, p in messages]
    return user, expected


def parse_predictions(raw: str) -> list[Any]:
    """Parse a model reply: a JSON array, optionally inside a fenced code block."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        text = text.rsplit("```", 1)[0]
    value = json.loads(text)
    if not isinstance(value, list):
        raise ValueError("model reply is not a JSON array")
    return value


def _normalized(pred: Any) -> tuple[Any, dict[str, Any]]:
    if not isinstance(pred, dict):
        return None, {}
    cmd, payload = pred.get("cmd"), pred.get("payload")
    if not isinstance(payload, dict):
        return cmd, {}
    try:
        return cmd, canonical_payload(cmd, payload)
    except (ValueError, TypeError):
        return cmd, payload


def score_predictions(expected: list[dict[str, Any]], predicted: list[Any]) -> dict[str, Any]:
    """Score by position. Missing predictions count as wrong; extra ones are reported.

    message_exact: share of messages whose cmd and full canonical payload match.
    field_accuracy: share of expected slots (cmd plus each payload field) that match.
    """
    exact = 0
    fields_ok = 0
    fields_total = 0
    for index, exp in enumerate(expected):
        cmd, payload = _normalized(predicted[index]) if index < len(predicted) else (None, {})
        fields_total += 1 + len(exp["payload"])
        fields_ok += cmd == exp["cmd"]
        fields_ok += sum(1 for k, v in exp["payload"].items() if k in payload and payload[k] == v)
        exact += cmd == exp["cmd"] and payload == exp["payload"]
    return {
        "messages": len(expected),
        "predicted": len(predicted),
        "message_exact": exact / len(expected) if expected else 0.0,
        "field_accuracy": fields_ok / fields_total if fields_total else 0.0,
    }


def _openai_chat(api_key: str, model: str, user: str) -> str:
    body = json.dumps(
        {
            "model": model,
            "messages": [
                {"role": "system", "content": PROMPT},
                {"role": "user", "content": user},
            ],
            "temperature": 0,
        }
    ).encode()
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode())
    return data["choices"][0]["message"]["content"]


def main() -> int:
    parser = argparse.ArgumentParser(description="ABIOS/3 decode-accuracy harness")
    parser.add_argument("--encoder", default="combined", choices=sorted(all_encoders()))
    parser.add_argument("--fixture", default="lifecycle_11", choices=sorted(FIXTURES))
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--dry-run", action="store_true", help="print the prompt and exit")
    parser.add_argument("--predictions", help="score a saved model reply instead of calling an API")
    parser.add_argument("--min-accuracy", type=float, default=0.8,
                        help="exit 1 if message_exact is below this (default 0.8)")
    args = parser.parse_args()
    user, expected = build_prompt(args.encoder, FIXTURES[args.fixture]())
    if args.dry_run:
        print(PROMPT + "\n\n" + user)
        return 0
    if args.predictions:
        with open(args.predictions, encoding="utf-8") as fh:
            raw = fh.read()
    else:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            print("OPENAI_API_KEY not set and no --predictions file; comprehension check skipped")
            return 0
        try:
            raw = _openai_chat(api_key, args.model, user)
        except urllib.error.URLError as exc:
            print(f"API call failed: {exc}")
            return 1
    try:
        predicted = parse_predictions(raw)
    except ValueError as exc:
        print(f"unparseable model reply: {exc}")
        return 1
    score = score_predictions(expected, predicted)
    score.update(encoder=args.encoder, fixture=args.fixture,
                 model=None if args.predictions else args.model)
    print(json.dumps(score, sort_keys=True))
    return 0 if score["message_exact"] >= args.min_accuracy else 1


if __name__ == "__main__":
    sys.exit(main())
