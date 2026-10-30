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

## SYM-3 (token-aware command wire)

SYM-3/1 is the canonical home for tokenizer-aware, shared-state command encoding alongside SYM-2P v1 packets. Normative spec: `SPEC-v3.md`. Reference code: `scripts/protean-sym3/` (generic protocol); Synbios forge example schema: `scripts/protean-sym3/schemas/synbios/`.

| Path | Contents |
|---|---|
| `SPEC-v3.md` | normative SYM-3/1 profile |
| `scripts/protean-sym3/` | encoders, lexicon, decoder context, bench harness |
| `docs/sym3-bench.md` | committed benchmark tables |
| `bench/results/sym3-bench.json` | golden JSON (`make bench` verifies) |
| `paper/sym3.md` | preprint source |
| `docs/REPRODUCE.md` | reproduction instructions |

### Headline results (primary: setup min + messages, o200k_base)

| Transcript | Compact JSON | Lossless English | SYM-3 refs | SYM-3 adaptive |
| --- | ---: | ---: | ---: | ---: |
| 11 messages | 682 | 686 | **491** | 512 |
| 40 messages | 5343 | 5242 | **1717** | 1738 |
| 200 messages | 27363 | 26754 | **7628** | 7649 |

Also on 11 messages: TOON **805**, Agora envelope **1027** (see bench doc). **DOI: pending** (Zenodo deposit planned).

**Caveats:** Savings scale with session length and repeated content; full lexicon setup exceeds JSON on very short transcripts. `SPEC-V2-DRAFT.md` is superseded for token efficiency (v2 dense pilot total **1415** vs JSON **682** on 11 msgs; raw v2 **3386**). The bench row **English (lossless, key=value one-line)** is honestly labeled—it is not Chain-of-Draft terse prose and costs **691** vs **686** lossless English on 11 msgs.

```bash
python3 -m pip install -r requirements-bench.txt
make bench          # verify committed tables (CI)
make bench-write    # refresh golden files after intentional changes
PYTHONPATH=scripts/protean-sym3 python3 -m unittest tests.test_sym3 -v
```

Site: https://aska-digital.github.io/protean-sym2p/ (sources in `site/`; published from `gh-pages` branch).
