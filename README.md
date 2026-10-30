SYM-2P: a compact versioned agentic message language - one canonical JSON packet per line over durable text artifacts - with validator, enums, and fixtures.

# protean-sym2p

The protocol ingredient of the Protean Kit distribution. It carries the
normative specification, the stdlib validator, the packet templates, the worked
example, and the fixture suite.

## Do you need this?

ROLE: The protocol ingredient of the Protean Kit distribution. It carries the normative SYM-2P specification, the stdlib validator, packet templates, a worked example, and the fixture suite.

USE WHEN:
- Two agents must pass messages as one canonical JSON packet per line inside durable text artifacts, per `SPEC.md` section 1.
- A receiver must validate a packet stream, optionally against receiver state or strict canonical form, and get typed diagnostics with exit codes 0 valid, 1 invalid, 2 usage or IO error.
- A run needs the routing-state rows checked. Install `protean-ops` alongside, which this manifest recommends.

SKIP WHEN:
- The run depends on open items O-1 to O-9. `SPEC.md` section 10 and this README state they remain open and undecided.
- Only record schemas and gates are needed. Those ship in `protean-ops`, not here.

## What it installs and where

| Path | Contents |
|---|---|
| `SPEC.md` | the normative specification |
| `skills/sym2p/` | the usage skill |
| `scripts/protean-sym2p/` | `sym-validate.py` and `sym-publish.py`, stdlib only |
| `templates/protean-sym2p/` | canonical brief and receipt packets |
| `examples/protean-sym2p/` | the worked review, fix, verify, merge loop |
| `AUDIT/protean-sym2p/` | evidence and provenance (never normative) |
| `gates/protean-sym2p/` | the leak gate and the blocklist |

## Install

```bash
bash install.sh --target <dir>
bash install.sh --target <dir> --dry-run
```

Bash and coreutils only, zero network calls, every written path printed, and no
`--target` means no run. A dry run writes nothing.

Installs alone with this command, resolving only its required dependencies listed
in its manifest entry. Optional relationships are reported, not fetched.

## Requirements and recommendations

Requires none. Recommends `protean-ops`: the protocol's routing-state rows are
records, and the ops ingredient carries the schemas and gates that check them.
The recommendation is documentary and never affects install order.

## Status: specified and built, with open items

`SPEC.md` defines the protocol. The validator, the write-once object publisher,
the templates, the worked example, and the fixture suite ship with this
repository and are exercised by its gates. The validator implements the
operational subset the specification names, and it rejects against the full
enums. The publisher writes the append-only object versions the validator then
checks.

Open items O-1 to O-9 remain open and are carried in `SPEC.md` section 10. No open
item is closed by this repository, and none is presented as decided.

## Use

```bash
python3 scripts/protean-sym2p/sym-validate.py --help
python3 scripts/protean-sym2p/sym-validate.py <packet-or-stream>
python3 scripts/protean-sym2p/sym-validate.py --state <receiver-state.json> <packets.jsonl>
python3 scripts/protean-sym2p/sym-validate.py --strict-canonical <packets.jsonl>
python3 scripts/protean-sym2p/sym-validate.py --verify-hashes --kind object <root>/objects/<id>.v2.md
python3 scripts/protean-sym2p/sym-publish.py --root <delegation-dir> --by <role-id> draft.json
python3 scripts/protean-sym2p/sym-publish.py --root <dir> --by <role-id> --announce --to <recipient> draft.json
python3 tests/run-tests.py
```

Exit codes: 0 every document valid, 1 at least one invalid with typed
diagnostics, 2 usage, IO, or configuration error. `.jsonl` is read one object per
line: that is the wire carrier.

## Gates

| Gate | Command (declared) |
|---|---|
| internal-name gate | `python3 gates/protean-sym2p/check-internal-names.py .` |
| protocol suite | `python3 tests/run-tests.py` |

The suite gives every valid fixture a pass and every malformed, stale, duplicate,
or protected-semantic fixture a typed rejection, and exercises the publisher's
append-only write path end to end.

## Offline and cache behaviour

Used through the composer, this ingredient is fetched once from its pinned tag
and reused from a content-addressed cache keyed by commit SHA. `--offline`
performs zero network calls and fails closed when the cache entry is absent.

## Limits and open items

- Transport signing is not implemented (O-1). Integrity is a canonical sha256
  computed in process, on a single-machine trust assumption.
- Reference resolution and expiry checks need the caller to supply receiver state
  and a reference clock. Without them, those fields are syntax-checked only, and
  the skill says so.
- Phase 3 routing predicates are named and not implemented (O-3).
- The protocol's routing semantics are described here. The record schemas that
  carry routing state belong to `protean-ops`.

## License

MIT. The committed `LICENSE` file is authoritative.

## SYM-3 (token-aware messaging)

SYM-3 is the third wire profile in this repository: one UTF-8 line per message, shared session state, content-addressed refs, and a decode-sufficient lexicon prefix. It respects **L-18** (no latent channels)—the same rule as SYM-2P/1.0 in `SPEC.md`.

| Transcript (primary total: setup min + msgs, o200k) | SYM-3 refs | Compact JSON | English (lossless) |
| --- | ---: | ---: | ---: |
| lifecycle_11 | **491** | 682 | 686 |
| lifecycle_40 | **1717** | 5343 | 5242 |
| lifecycle_200 | **7628** | 27363 | 26754 |

**Caveats:** savings come from repeated ids and large repeated fields; single-turn traffic benefits little. Full lexicon setup (~524 tokens) beats JSON only after several messages. English lossy summaries are smaller but not lossless. **DOI: pending.**

| Path | Contents |
| --- | --- |
| `SPEC-V3.md` | normative SYM-3 specification |
| `sym3/` | reference implementation, lexicon, encoders, fixtures |
| `docs/sym3-bench.md` | full benchmark tables |
| `docs/REPRODUCE.md` | `make bench` / `make bench-check` |
| `paper/sym3.md` | design paper (PDF in `paper/sym3.pdf`) |
| `site/` | static project overview |

```bash
make bench          # regenerate docs/sym3-bench.md + bench/sym3-results.json
PYTHONPATH=. python3 -m unittest tests.test_sym3 -v
```
