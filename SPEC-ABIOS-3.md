# ABIOS/3 — specification

Normative specification for **ABIOS**: a compact, tokenizer-aware wire encoding for
**forge command messages** (action plus JSON-shaped payload). ABIOS is a transport
and prompt-efficiency layer. It does not replace SYM-2P/1.0 inter-agent packets;
it encodes the same logical commands that may also be carried as SYM-2P `update`
packets, HTTP JSON bodies, or ledger rows. Evidence and bench numbers live under
`docs/` and `bench/`; they are informative, not normative.

**Naming.** ABIOS (Agent BIOS) is the forward-facing protocol name. Profile **ABIOS/3** (`abios/3`) supersedes the draft profile **SYM-3/1** (`sym3/1`, wire alias). ABIOS/3 was previously SYM-2P in product lineage; historical SYM-2P/1.0 and SYM-2P v2 draft packet layers keep their original names. This repository was `protean-sym2p` before transfer to [Moissanite-Labs/abios](https://github.com/Moissanite-Labs/abios).

## 1. Locked

Anything in this section is normative. A change to a locked item requires a
**ABIOS** revision increment (`abios/3` → `abios/4`), regenerated or migrated
lexicon where wire tokens change, round-trip and minimal-context decode tests,
and updated bench golden files when accounting rules change.

| # | Locked decision |
|---|---|
| S-1 | **Profile id is `abios/3`.** The first line of decoder setup is exactly `abios/3` followed by a newline (UTF-8). Receivers MUST also accept the legacy alias `sym3/1` (former profile id). Receivers reject setup missing a recognized profile header. |
| S-2 | **Logical message = `(action, payload)`.** `action` is a dotted forge command name (example schema: `task.create`). `payload` is a JSON object with a fixed field set per action. Canonical form fills schema defaults and sorts keys; encoders never emit fields outside the schema. |
| S-3 | **One command per line.** Each wire line is one UTF-8 text line with no trailing insignificant whitespace. Lines are independent; order in a transcript is application-defined. |
| S-4 | **Format tag prefixes every line.** The first token on the line is a **format tag** from the committed lexicon (`format_tags`). The tag names the encoding family: `delta`, `refs`, `positional`, `omit`, `combined`, or `adaptive`. The tag is concatenated with the command lexeme with no separator (e.g. `E` + `cta` → `Ecta`). |
| S-5 | **Six encoders, one decode contract.** Every encoder MUST round-trip canonical messages for the same session evolution. `adaptive` MUST decode by trying inner families in order: `delta`, `combined`, `refs`, `omit`, `positional`. |
| S-6 | **Positional field order is schema-defined.** For each action, field order is the sorted set of allowed keys (required-first convention: all keys sorted lexicographically in the example Synbios schema). Decoders bind tokens to keys by position or by explicit key list (omit/combined). |
| S-7 | **Default omission.** Fields equal to **schema defaults** MAY be omitted on the wire in `omit`, `combined`, and `delta` (fallback) encodings. Decoders MUST restore defaults before canonical validation. Defaults are normative per schema profile. |
| S-8 | **Session-scoped ref tokens.** When encoder and decoder share mirrored session state, stable ids MAY encode as single-letter tokens: `p` project, `t` task, `a` agent, `h` human, `f` artifact. Unknown tokens that match session ref tables resolve to full ids; otherwise tokens are literal strings or content refs. |
| S-9 | **Content-addressed refs.** Serialized values (UTF-8 string or canonical JSON) of **≥ 48 UTF-8 bytes** MAY be published once inline, then referenced by a **ref label** (`#1`, `#2`, … allocated in order on first use). Refs MUST resolve to the same bytes the publisher first sent on the wire. |
| S-10 | **State deltas.** When session snapshots prove only a bounded change, `delta` MAY emit a specialized short form. For `task.transition`, when only `status` changes and `task_id` matches the session task, the wire form is: `{tag}{cmd_lexeme} t st={status_lexeme}`. Other actions fall back to omit-shaped delta lines. |
| S-11 | **Tokenizer-cost lexicon.** Wire lexemes for commands, statuses, kinds, and format tags are chosen offline so each **format tag** is a **single token** under every tokenizer listed in `lexicon.json` `tokenizers`. Regeneration uses the algorithm in `scripts/protean-abios/generate_lexicon.py`. Committed `lexicon.json` is authoritative until the next ABIOS revision. |
| S-12 | **Decode-sufficient setup.** A receiver MUST accept either **full** setup (entire committed lexicon plus full positional schema) or **minimal** setup: only `concepts` entries for cmd/status/kind values appearing in the transcript, format tags used on the wire (if `adaptive` appears, **all** format tags), and positional key lists only for commands used. Minimal setup MUST decode the transcript; full setup is a convenience default. |
| S-13 | **Fail closed on decode.** Bad quoting, unknown command lexeme, ambiguous lexeme, short positional arity, or unknown content ref MUST error; no guessed fields or silent merge. |
| S-14 | **L-18 (SYM-2P) applies.** ABIOS adds no latent channel. Decoder setup is explicit durable text (header, lexicon block, schema block). Session state used for refs, deltas, and content addressing MUST be reconstructed only from prior lines in the transcript plus setup, or supplied explicitly in recovery (`rq:"full"` style recovery remains an application concern outside this wire profile). Prompt-prefix caching of setup is an optimization, never a correctness dependency (SPEC.md L-18, section 8). |

## 2. Relation to SYM-2P v1 and v2

| Layer | Role |
|---|---|
| **SYM-2P/1.0** (`SPEC.md`, wire `v:2`) | Inter-agent packets: acts, refs, bases, auth, routing. JSON object per line, canonical key order. Still the norm for delegation-tree traffic. |
| **SYM-2P/2.0 draft** (`SPEC-V2-DRAFT.md`) | Dense pipe-separated SYM-2P packet experiment. **Superseded for product direction:** bench showed unfavorable total cost (decode setup plus messages) versus compact JSON and ABIOS on Synbios forge lifecycles; PR #6 dense pilot numbers are retained only as **negative results** in `docs/abios-bench.md`. Not a migration target. |
| **ABIOS/3** (this document) | Compact encoding of **forge commands** (Synbios example: `schemas/synbios/command_fields.py`), comparable to JSON POST bodies and the Synbios SYM-2P v1 codec path (`schemas/synbios/sym2p/`). ABIOS lines may be embedded in artifacts, prompts, or sidecar logs; they do not alter SYM-2P packet grammar. |

Translation boundary: `schemas/synbios/sym2p/codec.py` maps forge commands ↔ SYM-2P v1 packets. ABIOS encoders map forge commands ↔ ABIOS lines. A deployment may use v1 packets on the blackboard and ABIOS only inside model context, as long as L-18 is preserved (everything needed to decode is written or sent). ABIOS MUST NOT replace SYM-2P JSON as the inter-agent surface without an explicit profile change (SPEC.md L-18, L-3, section 8.1).

## 3. Logical layer — canonical messages

Before encoding, implementations normalize:

1. Merge caller payload with **schema defaults** for the action.
2. Require every allowed field; reject unknown keys.
3. Emit **canonical payload**: sorted keys, deep-copied values.

Schema defaults for the Synbios example profile are fixed in `scripts/protean-abios/canonical.py` (`SCHEMA_DEFAULTS`). Other profiles MUST publish their own defaults table with the same semantics: omitted wire fields decode to these values.

**Equality:** two messages are equal iff actions match and canonical payloads are identical.

## 4. Wire token grammar

Tokens are space-separated except where noted. Parsing rules:

| Construct | Rule |
|---|---|
| Whitespace | ASCII space separates tokens; no empty tokens. |
| Quoted string | `"..."` with `\"`, `\\`, `\n`, and `\r` escapes; used when a string would otherwise parse as another token type, is empty, contains space, `;`, `,`, `"`, newline, carriage return, or starts with `http`. **Quoted tokens always decode as strings** (never re-parsed as JSON). |
| Null | `-` |
| Boolean | unquoted `1` / `0` |
| Integer | unquoted digit sequence |
| Inline JSON | unquoted token starting with `[` or `{`, canonical JSON (lists/objects in payloads) |
| Content ref | opaque `#n` label present in session `ref_to_digest` (e.g. `#1`) |
| List in payload | encoded as quoted canonical JSON unless refs encoder applies ref_if_published |

Command lexeme follows the format tag immediately. Remaining tokens are positional values or omit metadata.

## 5. Format families (message forms)

Let `T` = format tag lexeme, `C` = command lexeme, `K*` = ordered field keys, `V*` = escaped values.

### 5.1 `positional` (`T` = `I` in committed lexicon)

```
T+C K1 K2 ... Kn   →   values V1 V2 ... Vn in POSITIONAL_ORDER[action]
```

All schema fields appear. No content refs (`use_refs=false`). Baseline readable form.

### 5.2 `omit` (`M`)

```
T+C key1|key2|...|  V1 V2 ... Vk
```

Only non-default fields appear. Keys list ends with `|`; values align to keys. Decoder restores defaults (S-7).

### 5.3 `refs` (`E`)

Same shape as positional, but structured/string values ≥48 serialized bytes use **content refs** after first inline publication (S-9).

### 5.4 `delta` (`A`)

If S-10 specialized form applies:

```
T+C t st=<status_lexeme>
```

Else same as omit with tag replaced by delta tag.

### 5.5 `combined` (`Q`)

If S-10 applies, same as delta with combined tag. Else omit-shaped key list with **refs** escaping for values.

### 5.6 `adaptive` (`U`)

Encoder runs candidate families (`delta`, `refs`, `omit`, `positional`, `combined`), scores each line by **max tokenizer count** across lexicon tokenizers (tie-break shorter string), picks the winner, re-encodes once, and replaces the inner format tag with `U`. Decoder unwraps by substituting candidate tags (S-5).

Adaptive is normative for interoperability; it is not required for all senders. Fixed-family encoders are conformant if they satisfy S-5 round-trip.

## 6. Session state

Encoders and decoders maintain a mirrored **`AbiosSession`**:

| State | Use |
|---|---|
| `project_id`, `task_id`, `agent_id`, `human_id`, `artifact_id` | Ref token expansion (S-8) |
| `task_status`, `snapshots` | Delta detection (S-10), especially `task` snapshot after create/claim/transition |
| `content` (`ContentStore`) | Digest map, ref allocation, publish-on-first-seen |

**Transcript discipline:** for each line, decode (or encode) then **`apply_message`** updates session exactly as the canonical command would mutate the forge store. Cross-transcript refs are invalid unless setup re-seeds ids to match the fixture.

Delta rule (locked): for `task.transition`, if prior snapshot matches `task_id` and only `status` changes, delta emits status only; decoder supplies `task_id` from session.

## 7. Content store

Normative behavior:

1. **Digest:** SHA-256 over UTF-8 bytes (string) or canonical JSON (object/array), first 16 hex chars.
2. **Inline threshold:** serialized UTF-8 byte length &lt; 48 → always inline, no ref.
3. **First publish:** value sent literally; digest marked published on wire.
4. **Later mentions:** emit ref label if digest already published.
5. **Ref allocation:** assign `#1`, `#2`, … in order for each new digest; skip labels already bound. Fallback `#h{seq}` only if the numeric pool is exhausted.

Decoders observing inline large values register them for future ref resolution (`observe_inline`, `mark_from_wire`).

## 8. Lexicon and decoder setup

Committed file: `scripts/protean-abios/lexicon.json`.

Structure:

```json
{
  "version": 1,
  "tokenizers": ["o200k_base", "cl100k_base"],
  "concepts": { "cmd": {}, "field": {}, "status": {}, "kind": {}, "misc": {} },
  "format_tags": { "delta": "A", "refs": "E", ... }
}
```

**Concept categories:**

| Category | Maps |
|---|---|
| `cmd` | forge action → wire command lexeme |
| `field` | payload field name → optional hint lexeme (Synbios profile) |
| `status` | status enum → lexeme |
| `kind` | kind enum → lexeme |
| `misc` | `true`, `false`, `list_sep`, `ref_prefix` |

Field lexemes are informative for generators; positional encodings use values, not field names, except omit key lists.

**Decoder context text format:**

```
abios/3

lexicon:
{...json...}
schema:
{...json...}
ids:
{...json...}
defaults:
{...json...}
```

`schema` maps each command to ordered field name list. **Full schema** = all commands in profile. **Minimal schema** = only commands used in transcript (S-12).

`ids` binds session ref tokens (`p`, `t`, `a`, `h`, `f`) to full id strings. Decoders MUST NOT rely on hard-coded fixture ids outside this block (S-14).

`defaults` maps each command in the schema to its default payload fields (S-7). Minimal setup carries defaults only for commands present in the minimal schema.

Primary bench accounting (informative): **total cost = minimal setup tokens + message tokens**; cached setup MAY be reported at 10% of minimal setup for break-even analysis only, not as a wire requirement.

### 8.1 POST — session handshake

**POST** (power-on self-test) is the normative one-time exchange of **decode-sufficient minimal context** before either peer sends compressed ABIOS traffic. Each side verifies it shares the same lexicon slice, positional schema, and profile id as its partner—analogous to firmware POST before the OS loads drivers.

**Message form.** POST is UTF-8 text:

1. **Ack line:** `POST ok <profile> <digest>` where `<profile>` is `abios/3` or negotiated legacy `sym3/1`, and `<digest>` is the first 16 hex chars of SHA-256 over the decoder-context body after CRLF→LF normalization and ensuring a trailing newline (no Unicode whitespace trim).
2. **Body:** the minimal decoder context (profile header, `lexicon:`, `schema:`, `ids:`, and `defaults:` blocks) exactly as defined above.

The ack line profile MUST match the body profile header. Legacy `sym3/1` is accepted only when the body begins with `sym3/1` and the ack names `sym3/1`.

**Checks.** Receivers MUST verify: (a) ack prefix and profile, (b) digest matches the body, (c) `parse_decoder_context(body)` succeeds, (d) the body is decode-sufficient for the planned transcript (S-12). Reference: `scripts/protean-abios/post.py` (`render_post_handshake`, `parse_post_handshake`, `verify_post_or_raise`).

**Mismatch fallback.** If POST fails (digest, profile, or parse error), implementations MUST NOT assume shared context. They SHOULD fall back to plain compact JSON (or another agreed lossless carrier) for that session, or abort the session with an explicit error. They MUST NOT decode ABIOS lines with a guessed or partial lexicon.

## 9. Generic protocol vs Synbios example schema

| Generic (this spec) | Synbios example (`schemas/synbios/`) |
|---|---|
| Action namespace pattern `noun.verb` | `project.create`, `task.transition`, … in `command_fields.py` |
| `COMMAND_FIELDS` defines allowed keys | Same file, committed field sets |
| `POSITIONAL_ORDER` = sorted keys per command | `schema.py` |
| `SCHEMA_DEFAULTS` per action | `canonical.py` |
| Lifecycle fixtures for tests/bench | `fixtures.py` (`lifecycle_11`, `lifecycle_40`, `lifecycle_200`) |
| SYM-2P v1 packet adapter | `sym2p/codec.py`, `adapter.py` |

Implementations targeting another forge MUST ship their own `command_fields`, defaults, and lexicon regeneration inputs; format tags and encoder logic remain as defined here.

## 10. Versioning

| Artifact | Version |
|---|---|
| Wire profile | `abios/3` (header string) |
| Lexicon file | integer `version` inside `lexicon.json` (currently `1`) |
| SYM-2P packet envelope | unchanged (`v:2` per SPEC.md L-1) |

Increment ABIOS profile when: format tag set changes, token grammar changes, default omission rules change, or content-ref algorithm changes. Lexicon-only token reassignment with unchanged grammar MAY bump lexicon `version` under the same `abios/N` if decoders accept both lexicons via setup; otherwise bump profile.

## 11. Conformance tests

Normative reference suite: **`tests/test_abios.py`**, run via:

```bash
make abios-test
```

Requirements mirrored by tests:

| Test area | Requirement |
|---|---|
| Lexicon | File exists; every `format_tags` value is single-token under primary tokenizer |
| Round-trip | All six encoders × lifecycles 11, 40, 200 messages |
| Minimal context | Transcript decodes with **minimal** setup only (S-12) |
| Lexicon stability | `generate_lexicon.py` reproduces committed `lexicon.json` byte-identical |

Bench regression (informative): `make bench` / `bench/run-abios-bench.py` compares totals to golden `bench/results/abios-bench.json`.

## 12. Acceptance criteria (ABIOS implementation)

| # | Criterion |
|---|---|
| C-1 | Implements all six format families and adaptive selection per S-5–S-6. |
| C-2 | Canonical normalization matches schema defaults and field sets for the declared profile. |
| C-3 | Session ref tokens and content refs round-trip on ordered transcripts. |
| C-4 | `delta` specialized `task.transition` form matches S-10 when snapshot preconditions hold. |
| C-5 | Decoder setup parser accepts full and minimal lexicon/schema payloads with `abios/3` header. |
| C-6 | No dependency on hidden KV state, embeddings, or undeclared cross-process memory (L-18 / S-14). |
| C-7 | `tests/test_abios.py` passes with tiktoken available. |
| C-8 | POST handshake (`post.py`) verifies minimal context digest; mismatch is a hard error (fallback signal). |

## 13. Non-goals

ABIOS does not define: SYM-2P act enums, authorization envelopes, routing gates, dispute objects, or English rendering requirements (English renderers such as `english.py` are non-normative convenience). It does not mandate adaptive encoding on the wire. It does not revive SYM-2P/2.0 draft pipe packets as a standard.

---

*Profile name:* **ABIOS/3**  
*Reference implementation:* `scripts/protean-abios/`  
*Synbios example schema:* `scripts/protean-abios/schemas/synbios/`
