#!/usr/bin/env python3
"""Run the bench model-eval protocol against the OpenAI API.

Automates EVAL.md so the eval can be reproduced with one command.
stdlib only. Reads the API key from OPENAI_API_KEY in the environment;
it is never written to disk.

Usage:
  OPENAI_API_KEY=... python3 bench/run-api.py \
      --model gpt-6-astra --effort medium [--service-tier flex] \
      [--max-cost 5.0] [--out runs/] [--dry-run]

What it does, per EVAL.md:
  comprehension (t01-t06): one fresh call per form, v1 and v2, with the
    packet and the task's questions. Answers recorded verbatim, in order.
  render (t07-t08): one call per task, v2 line, ask for plain-English
    rendering. Scored later by sym2-score.py on key phrases.
  compile (t09-t10): one call per task, English description, ask for the
    v2 packet line. The prompt includes sections 3 and 4 of
    SPEC-V2-DRAFT.md verbatim, so the model is not tested on memorizing
    the spec.

Output: <out>/<date>-<model>-<effort>/answers.json (the scorer's input format,
plus a usage log with per-call token counts and estimated cost) and
usage.jsonl alongside it.

Cost control:
  --service-tier flex requests Flex processing (Batch rates, synchronous,
  best-effort capacity). If a Flex call fails with 4xx, that call is retried
  at the standard tier and the tier used is logged. --max-cost is a
  client-side circuit breaker: the run stops before starting the next call
  once cumulative estimated cost reaches it. Default 5.0 USD.

Prices below are ESTIMATES taken from third-party summaries, not a
verified rate card. Token counts are recorded per call so costs can be
recomputed exactly at any time; treat total_estimated_cost_usd as a
circuit-breaker heuristic, not an invoice.
"""
import argparse
import json
import os
import re
import ssl
import sys
import time
import urllib.request
import urllib.error
from datetime import date

try:
    import certifi
    _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:
    _SSL_CTX = ssl.create_default_context()

API_URL = os.environ.get("OPENAI_API_ENDPOINT", "https://api.openai.com/v1/responses")
HERE = os.path.dirname(os.path.abspath(__file__))

# ESTIMATED (input, output, cached-input) USD per million tokens.
ESTIMATED_PRICES = {
    "gpt-6-astra": {"standard": (10.0, 50.0, 1.00), "flex": (5.0, 25.0, 0.50)},
    "gpt-6.1-sol": {"standard": (2.0, 10.0, 0.20), "flex": (1.0, 5.0, 0.05)},
}

COMPREHENSION_ASK = (
    "Read this packet. Then answer each question below in order, "
    "one answer per line, just the answer, no extra words.\n\n"
)
RENDER_ASK = (
    "Render this packet as plain English, one sentence per body expression.\n\n"
)
COMPILE_ASK = (
    "Write this as a single SYM-2P v2 packet line.\n\n"
    "Field order: V|ID|TK|F|T|A|ST|CF|CV|BODY|RQ|BASE|EXP\n\n"
    "Spec excerpt (sections 3 and 4 of SPEC-V2-DRAFT.md):\n\n"
)


def est_cost(model, tier, usage):
    prices = ESTIMATED_PRICES.get(model, {}).get(tier) or \
             ESTIMATED_PRICES.get(model, {}).get("standard")
    if prices is None:
        return 0.0
    pin, pout, pcached = prices
    inp = usage.get("input_tokens", 0)
    cached = (usage.get("input_tokens_details") or {}).get("cached_tokens", 0)
    uncached = max(0, inp - cached)
    out = usage.get("output_tokens", 0)
    return (uncached * pin + cached * pcached + out * pout) / 1e6


def call_model(model, effort, service_tier, instructions, user_input, timeout=900):
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        sys.exit("OPENAI_API_KEY is not set; refusing to make calls.")
    body = {
        "model": model,
        "instructions": instructions,
        "input": user_input,
        "service_tier": service_tier,
    }
    if effort != "none":
        body["reasoning"] = {"effort": effort}
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        API_URL, data=data, method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as resp:
            return json.loads(resp.read()), service_tier, None
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:500]
        if service_tier == "flex" and e.code in (400, 408, 429, 503):
            # Flex is best-effort; fall back to standard for this call only.
            return call_model(model, effort, "auto", instructions, user_input, timeout)
        return None, service_tier, f"HTTP {e.code}: {detail}"
    except Exception as e:  # network-level failure; retry once at same tier
        time.sleep(5)
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as resp:
                return json.loads(resp.read()), service_tier, None
        except Exception as e2:
            return None, service_tier, f"{e}; retry failed: {e2}"


def response_text(payload):
    for item in payload.get("output", []):
        if item.get("type") == "message":
            for part in item.get("content", []):
                if part.get("type") == "output_text":
                    return part.get("text", "")
    return ""


def spec_excerpt():
    try:
        text = open(os.path.join(HERE, "..", "SPEC-V2-DRAFT.md")).read()
        m = re.search(r"(?ms)^## 3\..*?(?=^## 5\.)", text)
        return m.group(0) if m else text[:8000]
    except OSError:
        return "(SPEC-V2-DRAFT.md sections 3 and 4 not readable)"


def extract_compile_line(text):
    for line in text.splitlines():
        s = line.strip().strip("`")
        if s.startswith("2|"):
            return s
    return text.strip()


def extract_answers(text, n):
    lines = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        s = re.sub(r"^\s*(?:[0-9]+[.)]|[-*])\s*", "", s).strip()
        if s:
            lines.append(s)
    return lines[:n]


def main(argv):
    p = argparse.ArgumentParser()
    p.add_argument("--tasks", default=os.path.join(HERE, "tasks.jsonl"))
    p.add_argument("--model", required=True)
    p.add_argument("--effort", default="medium",
                   choices=["none", "low", "medium", "high"])
    p.add_argument("--service-tier", default="flex",
                   choices=["flex", "auto", "default"])
    p.add_argument("--max-cost", type=float, default=5.0)
    p.add_argument("--out", default=os.path.join(HERE, "..", "runs"))
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--spec-in-context", action="store_true",
                   help="Carry the full SPEC-V2-DRAFT.md verbatim in the instructions for v2-form calls "
                        "(comprehension v2, render, compile). v1 calls run cold. Used for the "
                        "spec-in-context arm preregistered in Moissanite-Labs/abios#50.")
    args = p.parse_args(argv)

    spec_text = ""
    if args.spec_in_context:
        spec_path = os.path.join(HERE, "..", "SPEC-V2-DRAFT.md")
        with open(spec_path) as fh:
            spec_text = fh.read()

    def with_spec(base_instructions):
        return spec_text + "\n\n" + base_instructions if spec_text else base_instructions

    tasks = [json.loads(l) for l in open(args.tasks) if l.strip()]
    safe_model = args.model.replace("/", "-")
    outdir = os.path.join(args.out,
                          f"{date.today().isoformat()}-{safe_model}-{args.effort}")
    if args.dry_run:
        calls = sum(2 if t["kind"] == "comprehension" else 1 for t in tasks)
        print(f"would make {calls} calls: model={args.model} effort={args.effort} "
              f"tier={args.service_tier} out={outdir}")
        return 0

    os.makedirs(outdir, exist_ok=True)
    usage_log_path = os.path.join(outdir, "usage.jsonl")
    raw_log_path = os.path.join(outdir, "raw-responses.jsonl")
    answers = {"model": args.model, "date": date.today().isoformat(),
               "effort": args.effort, "service_tier": args.service_tier,
               "spec_in_context": bool(args.spec_in_context),
               "runs": {}}
    total_cost = 0.0
    usage_fh = open(usage_log_path, "a")
    raw_fh = open(raw_log_path, "a")

    def emit(task_id, form, tier, usage, cost, ok, error=None):
        usage_fh.write(json.dumps({
            "task": task_id, "form": form, "tier": tier,
            "usage": usage, "est_cost_usd": round(cost, 6),
            "ok": ok, "error": error}) + "\n")
        usage_fh.flush()

    def emit_raw(task_id, form, text, ok, error=None):
        raw_fh.write(json.dumps({
            "task": task_id, "form": form, "text": text,
            "ok": ok, "error": error}) + "\n")
        raw_fh.flush()

    for t in tasks:
        tid = t["id"]
        kind = t["kind"]
        if kind == "comprehension":
            nq = len(t["questions"])
            qtext = "\n".join(f"{i+1}. {q['q']}" for i, q in enumerate(t["questions"]))
            forms = {"v1": json.dumps(t["v1"], separators=(",", ":")),
                     "v2": t["v2"]}
            answers["runs"][tid] = {}
            for form, packet in forms.items():
                if total_cost >= args.max_cost:
                    sys.exit(f"circuit breaker: est cost ${total_cost:.2f} >= ${args.max_cost}; stop.")
                user_in = f"{COMPREHENSION_ASK}Packet ({form} form):\n{packet}\n\n{qtext}"
                instructions = "You answer precise questions about agent message packets."
                if form == "v2":
                    instructions = with_spec(instructions)
                payload, tier, err = call_model(args.model, args.effort,
                                                args.service_tier,
                                                instructions,
                                                user_in)
                usage = (payload or {}).get("usage", {})
                cost = est_cost(args.model, tier, usage)
                total_cost += cost
                if payload is None:
                    emit(tid, form, tier, {}, cost, False, err)
                    emit_raw(tid, form, "", False, err)
                    answers["runs"][tid][form] = []
                    print(f"FAIL {tid}/{form}: {err}", file=sys.stderr)
                    continue
                emit(tid, form, tier, usage, cost, True)
                text = response_text(payload)
                emit_raw(tid, form, text, True)
                answers["runs"][tid][form] = extract_answers(text, nq)
        elif kind == "render":
            if total_cost >= args.max_cost:
                sys.exit(f"circuit breaker: est cost ${total_cost:.2f} >= ${args.max_cost}; stop.")
            user_in = f"{RENDER_ASK}Packet:\n{t['v2']}"
            instructions = with_spec("You render dense agent packets as plain English.")
            payload, tier, err = call_model(args.model, args.effort,
                                            args.service_tier,
                                            instructions,
                                            user_in)
            usage = (payload or {}).get("usage", {})
            cost = est_cost(args.model, tier, usage)
            total_cost += cost
            if payload is None:
                emit(tid, "v2", tier, {}, cost, False, err)
                emit_raw(tid, "v2", "", False, err)
                answers["runs"][tid] = {"v2": ""}
                print(f"FAIL {tid}/v2: {err}", file=sys.stderr)
                continue
            emit(tid, "v2", tier, usage, cost, True)
            text = response_text(payload)
            emit_raw(tid, "v2", text, True)
            answers["runs"][tid] = {"v2": text}
        elif kind == "compile":
            if total_cost >= args.max_cost:
                sys.exit(f"circuit breaker: est cost ${total_cost:.2f} >= ${args.max_cost}; stop.")
            user_in = f"{COMPILE_ASK}{spec_excerpt()}\n\nDescription:\n{t['english']}"
            instructions = with_spec("You write canonical SYM-2P v2 packet lines.")
            payload, tier, err = call_model(args.model, args.effort,
                                            args.service_tier,
                                            instructions,
                                            user_in)
            usage = (payload or {}).get("usage", {})
            cost = est_cost(args.model, tier, usage)
            total_cost += cost
            if payload is None:
                emit(tid, "v1", tier, {}, cost, False, err)
                emit_raw(tid, "v1", "", False, err)
                answers["runs"][tid] = {"v1": ""}
                print(f"FAIL {tid}/v1: {err}", file=sys.stderr)
                continue
            emit(tid, "v1", tier, usage, cost, True)
            text = response_text(payload)
            emit_raw(tid, "v1", text, True)
            answers["runs"][tid] = {"v1": extract_compile_line(text)}

    usage_fh.close()
    raw_fh.close()
    answers["total_estimated_cost_usd"] = round(total_cost, 4)
    with open(os.path.join(outdir, "answers.json"), "w") as fh:
        json.dump(answers, fh, indent=2)
    print(f"wrote {outdir}/answers.json  est. cost ${total_cost:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
