# Reproducing SYM-3 benchmark numbers

The token counts in [sym3-bench.md](sym3-bench.md) and [paper/sym3.md](../paper/sym3.md) are produced by the in-repo harness. Primary accounting uses **o200k_base** via tiktoken: total = decode-sufficient setup (min) + message tokens.

## One command (verify only — CI)

From the repository root (Python 3.9+):

```bash
python3 -m pip install -r requirements-bench.txt
make bench
```

This **recomputes** tables in memory and compares them to the committed [docs/sym3-bench.md](sym3-bench.md) and [bench/results/sym3-bench.json](../bench/results/sym3-bench.json). It does **not** overwrite those files. Exit code is non-zero on any mismatch (git SHA fields in JSON are ignored).

## Refresh committed tables

After an intentional encoder, fixture, or dependency change:

```bash
python3 -m pip install -r requirements-bench.txt
make bench-write
git diff docs/sym3-bench.md bench/results/sym3-bench.json
```

`make bench-write` runs `scripts/protean-sym3/bench.py --write` and overwrites the markdown and JSON golden files.

## Pinned dependencies

[requirements-bench.txt](../requirements-bench.txt) pins `tiktoken` and `toon-format`. CI installs the same file before running `make bench`.

## Unit tests

```bash
PYTHONPATH=scripts/protean-sym3 python3 -m unittest tests.test_sym3 -v
python3 tests/run-tests.py
```

Round-trip tests cover every encoder on all lifecycle fixtures using decode-sufficient minimal context only.

## Optional checks

- LLM comprehension (requires `OPENAI_API_KEY`, not CI): `PYTHONPATH=scripts/protean-sym3 python3 scripts/protean-sym3/comprehension.py`

## GitHub Pages assets

Static site sources live under [site/](../site/). After changing CSS or HTML, run:

```bash
python3 site/inject_version.py
```

Asset query strings use `?v=<git short sha>` for cache busting. The `gh-pages` branch is updated from `site/` when publishing (deployment settings unchanged).
