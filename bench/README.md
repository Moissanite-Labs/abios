# bench: the measurement harness

This directory turns the repo from a format into an instrument. It
measures what v2 buys over v1 English, in two parts: machine metrics
that run here, and a model eval protocol that runs wherever models
are available.

## Machine metrics

`sym2-bench.py` compares the v1 and v2 forms of each task in
`tasks.jsonl` on bytes and parse+validate latency. Token counts are
estimated at chars/4 and labeled as estimates.

```
python3 bench/sym2-bench.py
```

Current result on the 6 paired tasks: v2 is 3.1x smaller in bytes
than compact v1 JSON. Parse+validate latency is tens of microseconds
for both forms, so the win is bytes on the wire, not local parse
speed.

## Model eval

`tasks.jsonl` holds 10 tasks. Six are comprehension pairs: the same
packet in v1 English and v2, with structured questions and answers.
Two are render tasks (v2 to English). Two are compile tasks (English
to v2). `EVAL.md` gives the full protocol. `sym2-score.py` scores a
run:

```
python3 bench/sym2-score.py bench/tasks.jsonl answers.json
```

See `EVAL.md` for the answers file format.

## SYM-3 token bench

SYM-3 lifecycle measurements live in `docs/sym3-bench.md`. Regenerate with `make bench` from the repo root (see `docs/REPRODUCE.md`). CI runs `make bench-check`.

## What this does not claim

The harness measures encoding and comprehension. It does not run
models itself, and the corpus is 10 hand-written tasks, not a
benchmark suite. A real capability claim needs the eval run against
models, reported with the model name, date, and scores. The harness
makes that run cheap to do and honest to report.
