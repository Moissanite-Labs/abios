# abios

**ABIOS** (Agent BIOS) is token-aware shared-state command wire for agents: profile **ABIOS/3** (`abios/3`), **POST** session handshake, reproducible benchmarks, and a reference implementation under `scripts/protean-abios/`.

This repository also ships **ABIOS/1 (formerly SYM-2P)**: canonical JSON v1 packets, v2 dense wire experiments, stdlib validator, templates, and fixtures under `scripts/protean-sym2p/` (Protean Kit ingredient paths unchanged).

## Do you need this?

ROLE: Agent command wire (ABIOS/3) plus legacy inter-agent packets (ABIOS/1 / SYM-2P v1). Use ABIOS/3 when multi-turn forge or command streams are billed by tokenizer output and peers can share explicit decoder setup. Use v1 packets when you need `SPEC.md` JSON lines and `sym-validate.py`.

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

## ABIOS (Agent BIOS — token-aware command wire)

**ABIOS/3** (`abios/3`, `SPEC-ABIOS-3.md`) is the canonical home for tokenizer-aware, shared-state command encoding alongside SYM-2P/1.0 packets. Reference code: `scripts/protean-abios/` (generic protocol); Synbios forge example schema: `scripts/protean-abios/schemas/synbios/`. Legacy wire profile id `sym3/1` remains a decode alias for `abios/3`.

### Why ABIOS?

ABIOS stands for Agent BIOS. A BIOS is the layer that lets an operating system talk to hardware without knowing the details of each device. ABIOS plays that role for agents: a small, shared layer that lets one agent talk to another without either paying to restate everything they already share.

The name nods to IBM's Advanced BIOS ([IBM PS/2](https://en.wikipedia.org/wiki/IBM_PS/2), [Advanced BIOS](https://en.wikipedia.org/wiki/Advanced_BIOS)). In April 1987, IBM shipped the Personal System/2 with its ROM BIOS split in two: CBIOS, which kept real-mode DOS working, and ABIOS, a new interface for multitasking, protected-mode operating systems like OS/2. ABIOS itself saw little use. Operating systems mostly brought their own drivers, and the Micro Channel machines it shipped on lost to the open ISA/EISA ecosystem.

The PS/2 line around it lasted much longer. It introduced VGA, whose 640×480 mode remains a common lowest-common-denominator display mode. Its 6-pin mini-DIN keyboard and mouse connectors became the "PS/2 ports" found on PCs for decades. And it made the 1.44 MB 3.5-inch floppy the standard, the disk still drawn as the "save" icon. The name is for a forward-looking interface designed for multitasking systems before they were common. **It does not claim ABIOS succeeded.**

**POST.** Every PC runs POST (power-on self-test) at boot, before loading an operating system: it checks the hardware and sets up what the system needs. In ABIOS, POST is the one-time session handshake. Before any references or deltas, the two agents exchange the minimal context the receiver needs to decode messages. POST's tokens are included in every benchmark total.

**Synbios.** ABIOS pairs with [Synbios](https://github.com/Moissanite-Labs/synbios), Moissanite Labs' agent-first collaboration hub, which integrates ABIOS natively.

**Lineage.** ABIOS/3 was previously SYM-2P. Version 3 is the token-aware, shared-state redesign; the dense symbolic codes of SYM-2P v2 tokenized worse than JSON (1,415 vs 682 o200k tokens) and were dropped. Historical SYM-2P/1.0 and the v2 draft packet layers keep their original names in this repository.

| Path | Contents |
|---|---|
| `SPEC-ABIOS-3.md` | normative ABIOS/3 profile (POST handshake, decoder setup) |
| `scripts/protean-abios/` | encoders, lexicon, POST, decoder context, bench harness |
| `docs/abios-bench.md` | committed benchmark tables |
| `bench/results/abios-bench.json` | golden JSON (`make bench` verifies) |
| `paper/abios.md` | preprint source |
| `docs/REPRODUCE.md` | reproduction instructions |

### Headline results (primary: POST ack + minimal setup + messages, o200k_base)

| Transcript | Compact JSON | Lossless English | ABIOS refs | ABIOS adaptive |
| --- | ---: | ---: | ---: | ---: |
| 11 messages | 738 | 686 | **766** | **766** |
| 40 messages | 5570 | 5242 | **1990** | **1990** |
| 200 messages | 28498 | 26754 | **7901** | **7901** |

Also on 11 messages: TOON approx fallback **809**, Agora envelope **1027** (see `docs/abios-bench.md`). Compact JSON rows include an `action` field like ABIOS command names. **DOI: pending** (Zenodo deposit planned).

**Caveats:** On 11 messages, ABIOS totals exceed compact JSON under this accounting; savings appear from longer transcripts (40/200 repeat many identical messages). Full lexicon setup exceeds JSON on very short sessions. `SPEC-V2-DRAFT.md` is superseded for token efficiency (v2 dense pilot total **1415** vs JSON **738** on 11 msgs with current baselines; raw v2 **3386**). SYM-2P v2 bench rows are external PR #6 constants.

```bash
python3 -m pip install -r requirements-bench.txt
make bench          # verify committed tables (CI)
make bench-write    # refresh golden files after intentional changes
PYTHONPATH=scripts/protean-abios python3 -m unittest tests.test_abios -v
```

Site: https://moissanite-labs.github.io/abios/ (sources in `site/`; published from `gh-pages` branch).
