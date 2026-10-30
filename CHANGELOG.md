# Changelog

All notable changes to this repository are recorded here. The format is a short
entry per release: what changed, why, and how it was verified.

## Unreleased

- **What:** ABIOS/3 sealed sessions (`SPEC-ABIOS-3.md` section 8.2): an optional
  sealed POST binds a pre-shared HMAC-SHA-256 key (`kid`) and a fresh session id
  (`sid`) to the decode context, and seal lines (`~<tag>`, close `~!<tag>`)
  authenticate message lines over a per-direction MAC chain.
  `scripts/protean-abios/auth.py` (stdlib only), `tests/test_abios_auth.py`, and
  `scripts/protean-abios/auth_bench.py` with goldens
  `bench/results/abios-auth-bench.json` and `docs/abios-auth-bench.md`.
  `post.parse_post_handshake` now names a sealed POST instead of reporting a
  digest mismatch.
- **Why:** ABIOS/3 had no sender authentication (#24). The chain makes the
  sequence number implicit, so in-session replay, reordering, loss, and injection
  fail closed at no wire cost. A `(kid, sid)` registry, which also records the
  POSTs a peer sends, rejects replay of a whole session and a peer's own POST
  reflected back to it.
- **Verified:** `python3 -m unittest discover -s tests` (a known-answer vector
  also checked against the spec formulas, round trips for all six encoders, and
  every receiver check), `make bench` in CI.
- **Not provided:** confidentiality, non-repudiation, key distribution.

- **What:** ABIOS/1 canonical integration — `SPEC-ABIOS-3.md`, `scripts/protean-abios/` reference implementation, `tests/test_abios.py`, reproducible bench (`make bench` / golden `bench/results/abios-bench.json`), paper and citation metadata, GitHub Pages sources under `site/`.
- **Why:** Make protean-sym2p the home for tokenizer-aware shared-state command encoding; record SYM-2P v2 dense supersession and measured negative results.
- **Verified:** `python3 tests/run-tests.py`, `python3 -m unittest discover -s tests -v`, `make bench`.

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
