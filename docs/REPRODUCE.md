# Reproducing SYM-3 measurements

## Prerequisites

- Python 3.9+ (3.11 used in CI)
- Network access to `pip install` pinned packages in `requirements-bench.txt`

## One command

From the repository root:

```bash
make bench
```

This installs pinned `tiktoken` and `toon-format`, runs `sym3/bench.py`, and writes:

- `docs/sym3-bench.md` — human-readable tables
- `bench/sym3-results.json` — machine-readable results (git SHA, tokenizer list, full row data)

## Drift check (CI)

```bash
make bench-check
```

Exits non-zero if regenerated tables differ from committed files (ignores JSON metadata fields `generated_at` and `git_sha`).

## Tests

```bash
PYTHONPATH=. python3 -m unittest tests.test_sym3 -v
```

Round-trip all encoders on all lifecycle fixtures; decode with minimal context only.

## Regenerate lexicon (optional)

```bash
PYTHONPATH=. python3 -m sym3.generate_lexicon
```

Requires tiktoken; committed `sym3/lexicon.json` should remain stable unless candidate search changes.

## Reference source

Ported from [synbios](https://github.com/Moissanite-Labs/synbios) at commit `7978881565fa473d0afaef7e66cffdc26c306a26` (`synbios/sym3/`). Primary totals match `docs/sym3-bench.md` in that tree when using the pinned dependencies in `requirements-bench.txt`.
