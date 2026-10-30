# SYM-3/1.0 — specification

Normative specification for **SYM-3**: token-aware, shared-state agent messaging carried as one UTF-8 text line per message inside durable artifacts. This document is the norm for SYM-3. SYM-2P/1.0 (`SPEC.md`) and the SYM-2P v2 dense draft (`SPEC-V2-DRAFT.md`) remain the specifications for those profiles; SYM-3 is a distinct wire profile optimized for LLM token budgets while respecting the same **no latent channel** rule (**L-18** in `SPEC.md`).

## 1. Relation to prior profiles

| Profile | Carrier | Role |
| --- | --- | --- |
| SYM-2P/1.0 | One canonical JSON object per line | Normative agentic packets; English recovery ladder |
| SYM-2P v2 (draft) | Dense positional `|` lines | Symbol-first wire; measured **worse** than compact JSON on the SYM-3 lifecycle fixtures when session setup is included |
| SYM-3/1.0 | One space-separated text line per message | Shared session state + lexicon; optional content refs; decode-sufficient setup prefix |

SYM-3 does **not** replace SYM-2P routing semantics or dispute rules. It defines an alternative **message line** encoding for application commands (the reference implementation uses the Synbios forge command schema in `sym3/schemas/synbios_example.py`; other deployments supply their own schema).

## 2. Locked decisions (SYM-3)

| # | Decision |
| --- | --- |
| S3-1 | **Wire = one line per message**, UTF-8, no insignificant leading/trailing whitespace on the line. Lines are opaque text to transports; only durable text artifacts are normative (aligns with **L-18**: no hidden KV cache, embedding side channel, or cross-session memory—prompt prefix reuse is an optimization, not a channel). |
| S3-2 | **Decoder context is text**, shipped once per session (or transcript) as a prefix block beginning with `sym3/1` (see §6). Receivers MUST NOT depend on undeclared lexicon entries or schema fields. |
| S3-3 | **Lexicon** maps concepts (commands, statuses, kinds, format tags) to wire tokens chosen for single-token fertility on reference tokenizers (committed in `sym3/lexicon.json`). |
| S3-4 | **Positional schema** lists field order per command; encoders emit fields in that order. Decoders use the schema from decoder context, not inline key names. |
| S3-5 | **Session state** mirrors entity ids and snapshots so repeated ids and default field values need not be re-sent (default omission, delta transitions, content refs). |
| S3-6 | **Content-addressed refs**: repeated large strings or JSON values MAY be published inline once, then referenced by allocator-chosen ref tokens recorded in session content store (refs encoder). |
| S3-7 | **Format tag** prefixes each line: one committed single-token tag selects encoder (`delta`, `refs`, `positional`, `omit`, `combined`, `adaptive`). Adaptive lines wrap the tag of the encoder chosen for that message. |
| S3-8 | **Versioning**: profile name `sym3/1`; lexicon file carries integer `version`. Incompatible lexicon or schema changes require a new profile revision and migration tests. |
| S3-9 | **Fail closed**: unknown lexeme, unknown ref, or schema mismatch MUST error; no guessed decode. |

## 3. Message forms

Each message line has the shape:

```
<format-tag><command-lexeme> <payload tokens...>
```

- **Format tag**: from `format_tags` in lexicon (e.g. refs encoder).
- **Command lexeme**: maps to `cmd` concept (e.g. `project.create`).
- **Payload**: space-separated tokens; quoted strings use JSON string escaping; `-` means null; short entity aliases `p t a h f` map to session ids when documented in decoder context.

Encoders (normative set for 1.0):

| Encoder | Purpose |
| --- | --- |
| `positional` | Full positional payload |
| `omit` | Omit schema-default fields; optional `keys\|` prefix |
| `refs` | Like positional but content-ref repeated values |
| `delta` | Minimal task status transition when only status changes |
| `combined` | Delta OR omit+refs |
| `adaptive` | Per-message min-token choice among delta/refs/omit/positional/combined |

## 4. State deltas and default omission

Session state (`Sym3Session`) tracks project, task, agent, human, artifact ids, task status, entity snapshots, and a content store. Encoders MAY:

- Omit fields equal to schema defaults (`SCHEMA_DEFAULTS` in reference code).
- Emit `task.transition` as `t st=<status-lexeme>` when only status changes.
- Replace repeated content with ref tokens after first inline publish.

Decoders MUST apply the same rules in order so round-trip restores canonical command payloads.

## 5. Content-addressed references

Digest: first 16 hex chars of SHA-256 over canonical bytes (UTF-8 string or sorted JSON). Ref tokens are allocated from a single-token pool; first wire appearance is inline value, later appearances use ref. Decoders populate the content store from inline and ref tokens; refs unknown to store MUST fail.

## 6. Decoder context (decode-sufficient minimal)

Header:

```
sym3/1

lexicon:
{... minimal JSON: used cmd/status/kind + used format tags ...}
schema:
{... command -> ordered field list ...}
```

**Minimal** context includes every lexeme and format tag required to decode the transcript. When `adaptive` appears, minimal context includes **all** format tags. **Full** context includes the entire committed lexicon and full positional schema (used for secondary bench accounting only).

## 7. Canonical command payloads

Before encoding, implementations normalize payloads: known field set per command schema, defaults applied, sorted keys in canonical JSON used for equality. Reference function: `canonical_payload` in `sym3/canonical.py`.

## 8. Conformance

A conforming implementation MUST:

1. Round-trip every encoder on fixtures `lifecycle_11`, `lifecycle_40`, `lifecycle_200` (reference: `sym3/fixtures.py`).
2. Decode transcripts using **only** minimal decoder context (tests in `tests/test_sym3.py`).
3. Keep committed bench totals stable under `make bench-check` (token accounting).

## 9. Benchmark accounting (informative)

Primary total = decode-sufficient setup (min) + message tokens (o200k_base). See `docs/sym3-bench.md`. Cached setup assumes 10% of min setup (not API-measured). SYM-2P v1 and v2 dense numbers in the bench table are baselines on the same fixtures.

## 10. No latent channel (L-18)

SYM-3 state lives in explicit lines and explicit decoder context text. Implementations MUST NOT require undisclosed prior turns, provider prompt caches, or cross-agent shared memory beyond what is written to artifacts. Any optimization that reuses a prefix MUST remain byte-identical to resending the prefix text.
