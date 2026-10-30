# SYM-3: Token-Aware Shared-State Messaging for Agent-to-Agent Communication

**Authors:** Ahraz Arifuddin (Moissanite Labs); grk-qalam (agent)

## Abstract

Large language models charge by the token. Agent-to-agent protocols that repeat JSON field names, UUIDs, and boilerplate on every turn pay that cost on every message. SYM-3 is a text-line messaging profile that keeps all semantics on the wire in durable UTF-8 artifacts: a decode-sufficient lexicon prefix, explicit session state updated only from prior lines, optional content-addressed references, and several encoders (positional, omit, refs, delta, combined, adaptive). On synthetic multi-step lifecycles measured with `o200k_base`, SYM-3 **refs** totals 491 tokens (setup min + messages) versus 682 for compact JSON and 686 for lossless English on an 11-message transcript—while respecting the no latent channel rule (SPEC-2P **L-18**). Savings grow with transcript length and repeated content; single-turn traffic and non-redundant payloads see little benefit.

## Motivation

Multi-agent stacks (coordinators, specialists, tool hosts) exchange structured commands at high frequency. Compact JSON is already smaller than pretty JSON or verbose English, but it still re-encodes schema keys and entity ids on every line. Prior agent protocols (MCP tool calls, A2A task envelopes) inherit similar redundancy. Token cost is not only bandwidth: it is inference budget and latency.

SYM-3 targets **tokenizer fertility**—fewer BPE tokens for the same information—without hiding state in provider caches or undisclosed memory. Everything a decoder needs must appear in the artifact stream.

## Prior work

- **Agora** (arXiv:2410.11905): deterministic envelopes with content addressing; SYM-3 **refs** encoder is closest in spirit. Measured Agora envelope total 1027 tokens on lifecycle_11 (48 setup + 979 messages) under the same accounting.
- **TOON** ([toon-format](https://github.com/toon-format/toon)): tabular/text encoding of structured data; 805 tokens messages-only on lifecycle_11 in our bench (pinned `toon-format==1.2.0`).
- **LLMLingua / LLMLingua-2**: prompt compression for inference; orthogonal to on-wire protocol design (SYM-3 does not drop information).
- **Chain of Draft**: terse lossless English; our CoD-style baseline is 691 tokens on lifecycle_11.
- **A2A, MCP**: interoperability layers; SYM-3 is a wire profile that could carry similar payloads with a declared schema.
- **Petrov et al. 2023**: tokenizer fertility varies by language and string shape; SYM-3 lexicon generation picks single-token wire words on reference encoders.

**In-repo baselines:** SYM-2P v1 JSON packets score 2719 tokens (11 msgs); SYM-2P v2 dense session pilot 1415 total (213 handshake + 1202 steady)—**worse than compact JSON** on the same fixture when setup is included.

## Method

1. **Canonical payloads** per command schema (reference: Synbios forge commands; generic protocol is schema-driven).
2. **Committed lexicon** (`sym3/lexicon.json`) mapping commands, statuses, kinds, and format tags to wire tokens.
3. **Session state** tracking entity ids and snapshots; encoders omit defaults and emit status deltas.
4. **Content store** publishing large repeated strings once, then cheap ref tokens.
5. **Decoder context** text block (`sym3/1` header + minimal lexicon JSON + positional schema) sized to the transcript (decode-sufficient).
6. **Encoders** selected by format tag; **adaptive** picks min-token encoder per message.

Conformance: round-trip tests for all encoders on 11/40/200 message fixtures; decode using only minimal context (`tests/test_sym3.py`).

## Negative results

- **SYM-2P v1** on lifecycle_11: 2719 message tokens—JSON field overhead dominates.
- **SYM-2P v2 dense** (pilot numbers): 1415 total vs 682 compact JSON—session + dense line format did not beat JSON on short transcripts.
- **Non-English lexicon tricks** (not shown in table): arbitrary non-English wire words are not automatically cheaper on `o200k_base`; lexicon search explicitly optimizes single-token mappings.

## Results

Primary accounting: **setup (min, decode-sufficient) + message tokens** (`o200k_base`). Secondary: full lexicon setup (524 tokens on lifecycles). Tertiary: cached setup = 10% × min (assumption labeled in bench).

| Transcript | SYM-3 refs (primary) | Compact JSON | English lossless |
| --- | ---: | ---: | ---: |
| lifecycle_11 | **491** | 682 | 686 |
| lifecycle_40 | **1717** | 5343 | 5242 |
| lifecycle_200 | **7628** | 27363 | 26754 |

Additional lifecycle_11 baselines: TOON 805; Agora envelope 1027; SYM-3 adaptive 512. Break-even vs compact JSON for refs/adaptive on lifecycle_11: **~7 messages** under primary accounting.

Full tables: `docs/sym3-bench.md`. Reproduce: `make bench` / `docs/REPRODUCE.md`.

## Limitations

- Savings depend on **shared state and repeated content**; they scale with conversation length and redundancy. Single-turn messages gain little.
- Fixtures are **synthetic lifecycles**, not production traffic mixes.
- Primary metrics use **`o200k_base`**; other models differ.
- **Full setup** (524 + messages) exceeds compact JSON at 11 messages for refs/adaptive—honest accounting must include decoder prefix.
- English lossy summaries are smaller but **not information-equivalent**; do not compare them to SYM-3 for lossless claims.

## Model comprehension

Structured decoding by frontier models (wire lines → JSON commands) is not yet reported in this repository.

| Model | Encoder | Transcript | Exact match | Notes |
| --- | --- | --- | --- | --- |
| TODO | TODO | lifecycle_11 | TODO | Results pending |

Optional harness: `sym3/comprehension.py` (requires API key; not run in CI).

## References

- Agora: arXiv:2410.11905
- SPEC-V3.md, SPEC.md (L-18), docs/sym3-bench.md
- Port reference: synbios @ 7978881
