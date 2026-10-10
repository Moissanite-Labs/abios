# SYM-2P/2.0: draft specification

Status: DRAFT for review. Nothing here is normative. It becomes a proposal
for the reviewing team to reshape before any merge.

## 1. Why v2

SYM-2P v1 speaks JSON but thinks in English. The packet fields are English
prose inside string values: "scope: implement SYM-2P/1.0 sections 3-5 only".
A receiver that is a model must parse human language to understand a machine
message. That is the handicap. The full intention is laid out in
VISION.md.

v2 moves the language to symbols. Packet content is codes, numbers, and
structured expressions. English is a render target, not the source. A
translator script converts packets to human-readable English for operators.

What v2 keeps from v1: one packet per line in durable text artifacts, a
versioned wire format, and a validator with exit codes 0 (valid), 1
(invalid), 2 (usage or IO error).

## 2. Wire format

One packet is one line. Fields are positional, separated by `|` (U+007C).
There are no key names on the wire. Field order is fixed. A bare v2
line carries 13 fields. A v2-rcp line carries 14. The extra field is
the checksum defined in section 10. The edition shows in the field
count, not in a version bump: V stays `2`.

```
V|ID|TK|F|T|A|ST|CF|CV|BODY|RQ|BASE|EXP
```

| #   | Field   | Type          | Meaning                                    |
| --- | ------- | ------------- | ------------------------------------------ |
| 1   | V       | literal `2`   | wire version                               |
| 2   | ID      | token         | packet id, e.g. `b441`                     |
| 3   | TK      | token         | thread key                                 |
| 4   | F       | integer       | sender role code (section 3)               |
| 5   | T       | integer       | recipient role code (section 3)            |
| 6   | A       | integer       | act code (section 3)                       |
| 7   | ST      | integer       | state code (section 3)                     |
| 8   | CF      | 0-100         | confidence                                 |
| 9   | CV      | 0-100         | coverage                                   |
| 10  | BODY    | s-expressions | symbolic payload, may be empty (section 4) |
| 11  | RQ      | integer       | request code, 0 means none (section 3)     |
| 12  | BASE    | token         | base reference `id:ver`, empty means none  |
| 13  | EXP     | integer       | expiry in seconds, 0 means none            |
| 14  | SUM     | 16 hex, rcp only | checksum of the line (section 10)       |

A token matches `[A-Za-z0-9][A-Za-z0-9_.:/-]*`. The BODY field never
contains `|`.

Thread keys stay tokens. Threads are instance data, not shared
vocabulary: coding them would need per-thread allocation, which is a
separate protocol. TK is limited to 64 characters.

## 3. Code registries

Every categorical value is an integer. Code 0 is reserved in each registry
and means unset. Unknown codes are invalid.

Roles:

| Code   | Role             |
| ------ | ---------------- |
| 1      | coordinator      |
| 2      | builder          |
| 3      | verifier         |
| 4      | scout            |
| 5      | critic           |
| 6      | operator (human) |
| 7      | swarm (broadcast to all members) |

Acts:

| Code   | Act         |
| ------ | ----------- |
| 1      | assign      |
| 2      | acknowledge |
| 3      | assert      |
| 4      | update      |
| 5      | receipt     |
| 6      | challenge   |
| 7      | dispute     |
| 8      | authorize   |
| 9      | query       |
| 10     | inform      |
| 11     | delegate (recipient spawns a subordinate for the task) |
| 12     | report (a subordinate returns a result to its parent)  |

States:

| Code   | State      |
| ------ | ---------- |
| 1      | proposed   |
| 2      | accepted   |
| 3      | rejected   |
| 4      | verified   |
| 5      | open       |
| 6      | closed     |
| 7      | superseded |
| 8      | expired    |

Requests (RQ):

| Code   | Meaning                  |
| ------ | ------------------------ |
| 0      | none                     |
| 1      | acknowledgement required |
| 2      | verification required    |

## 4. Body language

The BODY field holds zero or more s-expressions. Each expression is an
operation applied to arguments:

```
expr := '(' op arg* ')'
arg  := number | symbol | reference | expr
```

A symbol matches `[A-Za-z][A-Za-z0-9_./-]*` or is `*` (meaning all).
Symbols are case-sensitive. Core vocabulary is lowercase by convention.
Numbers are unsigned integers. A reference is `$` followed by a symbol,
for example `$cov`. It refers to a name bound by `bind` (section 11).

Operation codes:

| Code   | Operation   | Shape              | Meaning                                             |
| ------ | ----------- | ------------------ | --------------------------------------------------- |
| 10     | scope       | `(10 target impl)` | what the packet covers                              |
| 11     | constraint  | `(11 constraint)`  | a hard limit                                        |
| 12     | accept      | `(12 accept)`      | acceptance criterion                                |
| 20     | impl        | `(20 unit range)`  | implement a unit over a range                       |
| 21     | nomod       | `(21 paths)`       | modify no paths                                     |
| 22     | exit        | `(22 prog ok bad)` | program exits `ok` on valid input, `bad` on invalid |
| 30     | bind        | `(30 name expr)`   | name the value of expr for later reference          |
| 31     | if          | `(31 test then else)` | branch on test (empty else allowed)         |
| 32     | each        | `(32 var items body)` | do body for each item in a list                  |
| 33     | list        | `(33 item*)`       | list literal                                        |
| 34     | lt          | `(34 a b)`         | a is less than b                                    |
| 35     | eq          | `(35 a b)`         | a equals b                                          |
| 40     | spawn       | `(40 role thread task)` | spawn a subagent of role on thread             |

Units such as `sec` are plain symbols, not opcodes. They appear as
arguments, for example `(20 sec (3 5))`, never as expression heads.

Example body:

```
(10 sym-2p/1.0 (20 sec (3 5)))(11 (21 *))(12 (22 validator 0 1))
```

Read as: scope is SYM-2P/1.0, implement sections 3 to 5. It modifies no
existing paths. The validator exits 0 on valid input and 1 on invalid.

## 5. Canonical form

- Exactly 13 `|`-separated fields for bare v2, 14 for v2-rcp.
- Integers carry no leading zeros.
- Inside BODY, exactly one space separates elements. No space follows `(`
  or precedes `)`.
- No leading or trailing whitespace on the line.
- SUM is 16 lowercase hex characters: the first 16 hex characters of
  the sha256 of the canonical 13-field line, encoded UTF-8.

## 6. Validation

A v2 validator MUST reject a line when any of these hold, with a typed
diagnostic:

- Field count is neither 13 (bare) nor 14 (rcp), or V is not `2`.
- ID, TK, or BASE fail the token pattern. BASE is neither empty nor
  `id:ver` shaped.
- F, T, A, ST, or RQ fall outside their registries.
- CF or CV fall outside 0-100; EXP is negative.
- BODY has unbalanced parentheses, an unknown opcode, or a malformed
  expression.
- On a 14-field line: SUM is not 16 lowercase hex characters, or it
  does not match the recomputed checksum of the first 13 fields.

Exit codes follow v1: 0 means every line valid, 1 means at least one
invalid with a typed diagnostic, 2 means usage, IO, or configuration
error.

## 7. The renderer

`sym2-render.py` converts v2 packets to human-readable English. It is the
script that turns the internal language into human syntax. Operators read
the rendered form. Agents read the wire form. The renderer is
informative, never normative: two renderers may word the same packet
differently, but they MUST NOT change its meaning. Wire parsing is shared
with the validator through `sym2_parse.py` so the grammar lives in one
place.

## 8. Density

The v1 brief packet template is 481 bytes. The same packet in v2:

```
2|b441|mr1|1|2|1|1|88|70|(10 sym-2p/1.0 (20 sec (3 5)))(11 (21 *))(12 (22 validator 0 1))|1|mr1:v1|40
```

That line is 101 bytes. The density gain comes from three removals: key
names, English prose, and JSON punctuation. The same packet is 4.8x
smaller than the 481-byte v1 template. The line above is the exact
output of `sym2-migrate.py` on the v1 template.

The same packet as v2-rcp is 118 bytes: the 101-byte bare line plus
the separator and the 16-character checksum.

## 9. Migration

- v1 (SYM-2P/1.0) stays normative and untouched. This draft does not
  change it.
- v2 is a new wire version, not an upgrade path. A line starting with
  `2|` is v2; v1 lines are JSON objects.
- The kit lock still pins v1.0.0 until this draft is accepted and merged.
- v1-to-v2 translation tooling ships as `sym2-migrate.py`: structured
  fields map through the registries, and English cond strings map
  through known patterns. A cond with no known pattern fails loudly
  rather than being guessed at. Emitted symbols are case-folded to
  lowercase, per the core-vocabulary convention in section 4.

## 10. Editions: bare and -rcp

Every wire version ships two editions. v2 ships bare v2 and v2-rcp.
A future v3 would ship bare v3 and v3-rcp. The `-rcp` suffix marks
relay corruption protection.

Bare v2 is the 13-field line in section 2. It is the default. Use it
where the medium is trusted: one machine, one operator, one local
relay.

v2-rcp adds the 14th field, SUM. Use it where a packet crosses
machines the sender does not fully trust: multi-hop relay, shared
queues, any path where a byte can change unnoticed.

The sender picks the edition per interaction, based on the medium.
There is no negotiation in this draft. A receiver accepts both
editions. An agent that mostly talks on trusted paths sends bare
lines and switches to -rcp for the relayed ones. It pays the
checksum cost only where corruption is possible.

SUM is the first 16 hex characters of the sha256 of the canonical
13-field line, encoded UTF-8. The checksum detects corruption in
transit. It does not prove who sent the packet. 16 characters keep
the overhead small: 17 bytes on the wire. Full transport signing,
which proves identity, stays a separate future protocol.

A validator written before this section rejects a 14-field line with
a shape error instead of misreading it. That is the intended
behavior: old readers fail loudly on the new edition.

## 11. Reasoning extension (v2.1)

The base language (sections 3 and 4) assigns tasks. This extension adds
the constructs for reasoning: naming values, branching on conditions,
iterating over collections, addressing a swarm, and dispatching
subagents. The wire version stays `2`. The extension is additive: every
v2.0 packet is still valid.

### 11.1 Binding and references

`(30 name expr)` binds `name` to the value of `expr`. Later, `$name`
refers to it. A `bind` name is visible to the top-level expressions
that follow it in the body. Inside `if` branches and `each` bodies,
bindings are local and do not leak outward. A `$name` with no visible
binding is invalid; the validator reports it as `ERR:SCOPE`.

```
(30 cov 62)(31 (34 $cov 70) (20 sec (6 6)) ())
```

Read as: let cov be 62. If cov is less than 70, implement section 6.

### 11.2 Iteration

`(32 var items body)` evaluates `body` once per item, with `var` bound
to the item. `items` is a `(33 ...)` list or a `$reference` to one.

```
(32 s (33 3 4 5) (20 sec s))
```

Read as: for each s in [3, 4, 5], implement section s.

An `impl` range may be a single atom as well as a `(lo hi)` pair, so the
loop variable can stand where a range bound stood. A pair `(x x)` means
just `x`.

### 11.3 Swarm broadcast

Role 7 is `swarm`. A packet with T=7 is addressed to every member of
the current thread. Combined with `each`, one packet can fan work out
across the swarm.

### 11.4 Subagent dispatch

Act 11 (`delegate`) tells the recipient to spawn a subordinate for the
body task. The body may name the spawn explicitly with `(40 role
thread task)`, where `role` is a role code and `thread` is the new
thread key. Act 12 (`report`) is the subordinate returning a result to
its parent on the parent thread.

```
(40 2 b442 (20 sec (7 9)))
```

Read as: spawn a builder on thread b442 to implement sections 7 to 9.

### 11.5 What this does not do

The extension adds expression, not execution. There is no defined
evaluation order beyond the reading order, no function definition, and
no recursion. Branches hold single expressions. These are deliberate
limits for a first reasoning dialect. They are open for the next
iteration.

## 12. Open items for reviewers

- Opcode registry governance. Proposed policy: codes 1-99 are core and
  owned by this spec. Codes 100-999 are domain extensions, allocated by
  pull request with reviewer approval. No code is ever reused once
  assigned. The registry lives in sections 3 and 4 of this draft, and
  the renderer MUST cover every assigned code.
- Thread keys stay tokens per section 2. The ambiguity is resolved:
  instance data is not coded.
- Transport signing (v1 open item O-1): the corruption-detection half
  is delivered as the v2-rcp edition in section 10. Signing itself,
  proof of identity across machines, stays open as a separate future
  protocol.
- The renderer vocabulary will grow with the opcode registry. The two
  MUST stay in sync.
