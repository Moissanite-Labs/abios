# Reproducing ABIOS benchmark numbers

The token counts in [abios-bench.md](abios-bench.md) and [paper/abios.md](../paper/abios.md) are produced by the in-repo harness. Primary accounting uses **o200k_base** via tiktoken: total = **POST ack line** + decode-sufficient minimal setup + message tokens.

## Requirements

- Python **3.10+** recommended (`toon-format` baseline needs 3.10+; CI runs ABIOS bench on **3.11** only).
- Install [requirements-bench.txt](../requirements-bench.txt) before ABIOS unit tests that depend on tiktoken.

## One command (verify only — CI)

From the repository root:

```bash
python3 -m pip install -r requirements-bench.txt
make bench
```

This **recomputes** tables in memory and compares them to the committed [docs/abios-bench.md](abios-bench.md) and [bench/results/abios-bench.json](../bench/results/abios-bench.json). It does **not** overwrite those files. Exit code is non-zero on any mismatch (git SHA fields in JSON are ignored).

CI installs `requirements-bench.txt` before unit tests and runs `PYTHONPATH=scripts/protean-abios python3 bench/run-abios-bench.py` on Python 3.11 (not `make bench` on every matrix row).

## Refresh committed tables

After an intentional encoder, fixture, or dependency change:

```bash
python3 -m pip install -r requirements-bench.txt
make bench-write
git diff docs/abios-bench.md bench/results/abios-bench.json
```

`make bench-write` runs `scripts/protean-abios/bench.py --write` and overwrites the markdown and JSON golden files.

## Pinned dependencies

[requirements-bench.txt](../requirements-bench.txt) pins `tiktoken` and `toon-format`.

## Unit tests

```bash
python3 -m pip install -r requirements-bench.txt
PYTHONPATH=scripts/protean-abios python3 -m unittest tests.test_abios -v
python3 tests/run-tests.py
```

Round-trip tests cover every encoder on lifecycle fixtures; minimal-context and POST tests decode using explicit session ids from decoder setup only.
