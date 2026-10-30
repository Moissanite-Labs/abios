# Changelog

All notable changes to this repository are recorded here. The format is a short
entry per release: what changed, why, and how it was verified.

## Unreleased

- **What:** ABIOS/3 integration — `SPEC-ABIOS-3.md`, `scripts/protean-abios/` reference codec, `tests/test_abios.py`, golden bench (`make bench` / `bench/results/abios-bench.json`), paper source (`paper/abios.md`), GitHub Pages templates under `site/`. Leak gate scans `site/` again; ABIOS/3 is repo-only until the ingredient manifest lists it.
- **Why:** Token-aware shared-state command encoding with honest POST + minimal-setup accounting; record SYM-2P v2 dense supersession and external PR #6 negative constants.
- **Verified:** `python3 tests/run-tests.py`, `python3 -m unittest discover -s tests -v`, `make bench` (Python 3.11+ in CI via `bench/run-abios-bench.py`).

- **What:** `scripts/protean-abios/schemas/` has one import root,
  `scripts/protean-abios`. The unreferenced `schemas/synbios/sym2p/bench.py`
  (the only module importing `synbios.*` from a second root) and its sole
  helper, `codec.v1_size_breakdown`, are removed. `tests/test_abios.py` imports
  every `schemas` module in an isolated interpreter with only that root on
  `sys.path`.
- **Why:** No single `PYTHONPATH` imported every module (#32). The live
  SYM-2P v1 measurement is `scripts/protean-abios/bench.py`; the removed script
  printed byte sizes for a v2 draft that no table, test, or document cites.
- **Verified:** the new test fails with the removed module restored
  (`ModuleNotFoundError: No module named 'synbios'`) and passes without it.

- **What:** `scripts/protean-abios/comprehension.py` measures decode accuracy
  from the POST handshake plus the wire lines (it previously sent the lines
  with no decoder context), scores message-exact and field accuracy by
  position, and can score a saved reply offline (`--predictions`) or print the
  prompt (`--dry-run`). `paper/abios.md` narrows the comprehension section to
  that one metric, drops the uncommitted multilingual-lexicon "negative
  result", and states the sender-authentication gap (#24, #27).
- **Why:** The paper described a harness that could not measure what it
  claimed, and a result with no code or data behind it (#33).
- **Verified:** `tests/test_abios.py` checks that the reference decoder
  recovers every `lifecycle_11` message from the harness prompt alone for all
  six encoders, that an oracle reply scores 1.0, and that wrong, missing, and
  default-omitted predictions score as documented.

- **What:** `scripts/protean-sym2p/sym-publish.py`, the write-once object
  publisher (stdlib only): it assigns `v`, `sup`, `hash`, `by`, and `at`,
  resolves the next version from `<root>/objects/` (never from the input), writes
  canonical compact JSON, refuses to rewrite a published file, and can emit the
  canonical packet announcing the new ref. `tests/run-tests.py` gains a second
  section that exercises that write path end to end and re-validates every
  published file with `sym-validate.py --verify-hashes`, so the write path and
  the read path are proved to agree on the canonical content hash.
- **Why:** M-5 states that "the tooling refuses to rewrite a published file", and
  append-only versioning (L-14) was convention plus install docs: nothing
  enforced it on the write path, so `sym-validate.py` checked object shape only.
- **Fix:** `--dry-run` exited 1 on a fresh delegation root. It skipped creating
  `<root>/objects/` (correct) and then listed that directory anyway, so the
  documented first-use check failed with a spurious `ERR:SYN` while the same
  command without `--dry-run` succeeded. An absent store is now scanned as
  empty. A store that exists but cannot be listed is still a finding. The
  suite's `--dry-run` case reused a root an earlier case had already populated,
  so it never reached this path: `tests/run-tests.py` gains a first-use section
  that builds its own root with no `objects/` store.
- **Verification:** `python3 tests/run-tests.py`: 80/80 cases (34 validator, 46
  publisher) with every published file independently hash-verified under
  `--verify-hashes`. The five first-use cases fail against the pre-fix publisher
  with the defect's own `ERR:SYN` diagnostic. Also
  `python3 gates/protean-sym2p/check-internal-names.py .` clean;
  `python3 -m unittest discover -s tests` OK. Full output in the pull request.
- **Hash scope:** the publisher writes the documented body-scope hash (sha256
  over the canonical compact `body`, the rule in
  `AUDIT/protean-sym2p/provenance.md` that `--verify-hashes` enforces), so a
  published file verifies against the shipped validator. Because the hash covers
  the body, a caller-computed correct hash survives publication unchanged. Header
  fields stay outside the hash by design, which is why the publisher enforces
  `v`, `sup`, and `by` itself at write time. The suite pins that scope.
- **Contract:** unchanged. No wire bytes, no enum, no key order, no gate, no
  install target, and no manifest entry changed; `scripts/protean-sym2p/` was
  already a declared payload path, and adding an optional file to it is a
  compatible addition (CONTRIBUTING).
- **Not changed:** `SPEC.md`. The publisher emits `sup` as a legal REF and the
  section 4 rule 2 shorthand is left as filed for the owner (`<id>.v<N-1>` is not
  expressible under L-5's grammar).
- **Fix:** the internal-names gate reported a leak in every git worktree or
  submodule checkout. Such a checkout has a `.git` pointer file holding the
  absolute gitdir path, and the gate skipped `.git` only as a directory. It now
  skips a file named `.git` too: git cannot commit a path by that name, so no
  repository content is excluded. Both gate copies get the fix, and
  `tests/test_gates.py` gains a case that plants a `.git` pointer file holding a
  private path and expects a clean result.

## 1.0.0

- **What:** the first release of the `protean-sym2p` ingredient: the capability payload,
  the machine descriptor `protean-ingredient.json`, the standalone installer
  `install.sh`, the declared gates under `gates/protean-sym2p/`, and the test suite under
  `tests/`.
- **Why:** the capability was previously reachable only from inside a private
  working tree. This repository is its single public home, installable on its own.
- **Verification:** the declared gates and `python3 -m unittest discover -s tests`
  pass from a clean checkout of this commit. See the pull request body for the
  commands and their output.
- **Contract:** `SYM-2P: a compact versioned agentic message language - one canonical JSON packet per line over durable text artifacts - with validator, enums, and fixtures.`
- **License:** MIT. The committed `LICENSE` file is authoritative.
