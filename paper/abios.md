# ABIOS: Token-Aware Shared-State Messaging for Agent-to-Agent Communication

**Authors:** Ahraz Arifuddin (Moissanite Labs); grk-qalam (agent)

## Abstract

Agent-to-agent traffic is billed by tokenizer output, not by human readability. ABIOS is a family of wire encodings for structured forge lifecycle commands that minimize **o200k_base** token cost under honest decoder setup accounting. Encoders share a tokenizer-tuned lexicon, session-scoped identifiers, optional content-addressed blobs, positional field schemas, default-value omission, and an adaptive mode that picks the cheapest variant per message. Primary totals count **POST ack + decode-sufficient minimal setup + messages**. On 11 synthetic lifecycle messages (fixture hex), ABIOS **refs** totals **750** versus **738** compact JSON (with `action` field) and **686** lossless English; with seeded random hex ids (seed 1) refs totals **726** versus JSON **694**. On 40- and 200-message transcripts refs totals **1706** and **6198** versus JSON **5570** and **28498**. Setup includes explicit session id bindings, optional `hex` aliases, and schema defaults (S-12). REFS decode rules text (`decode_rules.py` REFS_DECODE_RULES) adds **388** o200k tokens (abbrev draft was 102 and incomplete). Negative results from SYM-2P v1 packets, SYM-2P v2 dense pilots, and multilingual lexicon candidates are reported. Model comprehension on the wire format remains under evaluation.

## Motivation

Multi-agent systems exchange structured commands—task claims, artifact hashes, evidence bindings—at scale. When both endpoints are language models or model-backed services, the dominant cost is **tokens on the wire**, not bytes or JSON prettiness. Human operators rarely read raw agent traffic; protocols may use opaque tokens, positional fields, and shared state as long as decoders can reconstruct canonical payloads.

ABIOS targets **lossless** reconstruction of forge commands relative to compact JSON baselines, while accepting one-time decoder context (lexicon slice + schema) that must be present or cached for decode. Comparisons use tokenizer-accurate counting, not character length or heuristics. The normative profile is **ABIOS/3** (`abios/3`, `SPEC-ABIOS-3.md`); the reference implementation lives under `scripts/protean-abios/`, with the Synbios forge schema isolated under `schemas/synbios/`.

**Name.** ABIOS stands for Agent BIOS—a shared layer so agents can exchange compressed traffic without restating context. The name nods to IBM's Advanced BIOS (April 1987, PS/2 line: CBIOS for real-mode DOS, ABIOS for protected-mode OS/2). That firmware ABIOS saw little use; the PS/2 era left VGA, PS/2 keyboard/mouse ports, and the 1.44 MB floppy as lasting standards. **It does not claim ABIOS succeeded.** Sessions open with **POST**, the one-time decode-context handshake (after the PC boot metaphor); POST tokens are counted in benchmark totals. ABIOS pairs with Synbios ([github.com/Moissanite-Labs/synbios](https://github.com/Moissanite-Labs/synbios)). **ABIOS/3** is the forward profile; **ABIOS/1 (formerly SYM-2P)** v2 dense wire was dropped after unfavorable token counts versus JSON.

## Prior work

**Agora** ([arXiv:2410.11905](https://arxiv.org/abs/2410.11905)) describes hash-referenced, content-addressed agent envelopes; ABIOS **refs** follows a similar content-store pattern and is the closest prior-art row in our benchmark (11-message total **1027** including Agora setup).

**TOON** (`toon-format`) provides a compact textual serialization for nested structures; we include a TOON baseline on the same fixtures (**809** total on 11 messages with the in-repo fallback encoder when the package encoder is unavailable).

**LLMLingua / LLMLingua-2** compress natural-language prompts by dropping tokens; they optimize single-turn context, not a **session** with evolving shared state and repeated digests.

**Chain of Draft** motivates terse natural-language drafts for LLM I/O. We do **not** claim a CoD-style baseline in the bench: the row formerly labeled “terse English (CoD-style)” was renamed to **English (lossless, key=value one-line)**—a lossless `key=value` serialization that tokenizes to **691** on 11 messages, **above** lossless English (**686**), because repeated key names and JSON quoting dominate.

**A2A** and **MCP** standardize agent discovery and tool/context channels; ABIOS is complementary wire compression for an application-specific command stream, not a replacement for either protocol.

**Multilingual tokenizer fertility:** Petrov et al. (2023) show non-English text is not uniformly cheaper under byte-level BPE; our lexicon generator rejected non-English wire tokens that did not reduce **o200k** counts (see negative results).

## Method

ABIOS messages are line-oriented text. A session tracks project, task, agent, and artifact identifiers; repeated UUIDs collapse to single-character wire tokens (`p`, `t`, `a`, …). A **tokenizer-cost lexicon** maps command names, status/kind enums, and format tags to strings chosen by minimum max-token count across configured encodings (primary: **o200k_base**).

**State deltas:** the delta encoder emits only fields that change relative to session state instead of full canonical payloads.

**Content-addressed refs:** large or repeated string/blob values hash to stable ref tokens once published in a session content store (Agora-like).

**Positional schemas:** fixed field order per command reduces key overhead.

**Default omission:** fields equal to schema defaults are dropped on the wire when safe.

**Adaptive encoding:** per message, the implementation selects the cheapest among delta, refs, positional, omit, and combined variants (format tag prefix on each line).

**Decoder context:** decoders need a **decode-sufficient** prefix: wire mappings for every command, status, kind, and format tag **used in the transcript** (for adaptive, all format tags). A **full** setup includes the committed lexicon JSON and complete positional schema; benchmarks report both. **Cached†** totals assume one-time billing of 10% of minimal setup (not API-measured).

Round-trip goal: given decoder context + lines, reconstruct canonical JSON-equivalent payloads (`tests/test_abios.py` decodes with **minimal context only**). **Decode-sufficient minimal context** is the primary setup column in results. Rule **L-18** (no latent channel) from `SPEC.md` applies: setup is explicit text, not a hidden cache.

## Negative results

**SYM-2P v1 (this repo codec)** on `lifecycle_11`: **2719** message tokens (primary total **2719**) versus compact JSON **738** (with `action` field)—SYM-2P JSON packets without shared-state compression are unsuitable for token billing.

**SYM-2P v1 (synbios PR #6 pilot reference)** on the same transcript shape: **2720** message tokens (recorded as a cross-repo check).

**SYM-2P v2 dense (supersedes `SPEC-V2-DRAFT.md` for token efficiency):** PR #6 pilot on 11 messages—session steady state **1202** message tokens, handshake setup **213**, total **1415** (still above JSON **683** messages-only in that pilot); **raw v2 dense wire 3386** message tokens without session amortization. v2 remains in the repo as a draft spec and tooling reference, not a migration target for token-aware agent sessions.

**Multilingual / non-English lexicon candidates:** words chosen for human brevity did not reduce **o200k** token counts versus ASCII wire tokens; the committed lexicon stays tokenizer-tuned.

## Results

All numbers below are taken from [docs/abios-bench.md](../docs/abios-bench.md) (verified by `make bench` against committed tables). Primary accounting: **POST ack + setup (min, decode-sufficient) + messages**, **o200k_base**. Compact JSON includes an `action` field per message.

### lifecycle_11 (11 messages)

| Format | setup (min) | messages | total (primary) |
| --- | ---: | ---: | ---: |
| compact JSON | 0 | 738 | 738 |
| English (lossless) | 0 | 686 | 686 |
| English (lossless, key=value one-line) | 0 | 691 | 691 |
| ABIOS refs | 554 | 196 | **750** |
| ABIOS adaptive | 607 | 290 | **897** |
| Agora envelope | 48 | 979 | 1027 |
| TOON (approx fallback) | 0 | 809 | 809 |

Under **full** setup + messages, ABIOS refs/adaptive totals exceed compact JSON at 11 messages. Cumulative crossover vs compact JSON: **never** on this transcript; vs lossless English: **never**.

### lifecycle_40 (40 messages)

| Format | total (primary) | total (cached†) |
| --- | ---: | ---: |
| compact JSON | 5570 | 5570.0 |
| English (lossless) | 5242 | 5242.0 |
| ABIOS adaptive | **1718** | 1169.9 |
| ABIOS refs | **1706** | 1204.7 |

Cumulative crossover vs compact JSON: refs/adaptive **12** messages.

### lifecycle_200 (200 messages)

| Format | total (primary) | total (cached†) |
| --- | ---: | ---: |
| compact JSON | 28498 | 28498.0 |
| English (lossless) | 26754 | 26754.0 |
| ABIOS adaptive | **6198** | 5649.9 |
| ABIOS refs | **6198** | 5649.9 |

Cumulative crossover vs compact JSON: refs/adaptive **12** messages.

### Verdict

ABIOS **refs** and **adaptive** beat compact JSON on 40- and 200-message transcripts under primary accounting; on 11 messages they do not. Transcript fixtures repeat identical messages, which favors ref compression. Cached† totals improve further but rely on the 10% setup assumption.

## Model comprehension

> **Status:** pending — do not cite accuracy numbers yet.

| Metric | Encoder variants | Result |
| --- | --- | --- |
| Decode accuracy (line → JSON) | delta, refs, positional, omit, combined, adaptive | TODO |
| State-question accuracy (session facts) | all | TODO |
| Generation round-trip (encode → model decode → re-encode) | all | TODO |

Optional harness: `PYTHONPATH=scripts/protean-abios python3 scripts/protean-abios/comprehension.py` (requires API key; skipped in CI).

## Limitations

- Savings depend on **repeated content and shared session state**; they scale with conversation length and redundancy, not single-turn prompts.
- **Single-turn inference** cost is unchanged; ABIOS optimizes multi-message agent sessions.
- Counts use **o200k_base** as primary; other models may differ.
- Lifecycles are **synthetic** forge transcripts, not production traffic mixes.
- **Full** lexicon setup can erase wins on very short sessions (see 11-message full-setup row).
- Human readability and third-party auditability of raw lines are reduced by design.

## Reproduction

See [docs/REPRODUCE.md](../docs/REPRODUCE.md). Summary: `make bench` after `pip install -r requirements-bench.txt` (verify-only; use `make bench-write` to refresh golden files).

## References

- Agora: arXiv:2410.11905
- Petrov et al., 2023 — tokenizer fertility across languages
- LLMLingua / LLMLingua-2 — prompt token compression
- Chain of Draft — terse drafting for LLM I/O (motivation only; not the key=value baseline)
- TOON — `toon-format` package
- Agent protocols: A2A, MCP (tool/context standards)
