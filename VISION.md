# The SYM-2P vision

## The thesis

Models are handicapped by being forced to reason and communicate in
English. The thought structure used to process human language is
antithetical to the one used for math, science, and code. This is the
wordcel versus shape-rotator gap: fluency in prose is not the same as
precision in reasoning, and training for the first taxes the second.

## The bet

Skip language-based processing where it is not needed. Let models
reason and communicate in code, numbers, formulas, and symbols. Put a
translator at the boundary that converts the internal language to
human syntax for operators. At minimum, models get their own internal
language for reasoning and for talking to collaborators, subagents,
and swarms.

## What this repo is

This repo is the home of that machine language. v1 built the packet
machinery: one canonical packet per line in durable text artifacts, a
validator with typed diagnostics, exit codes a script can read. v2 is
the language itself going symbolic: dense positional fields,
integer-coded registries, and an s-expression body language. English
moves from the source to a render target.

## The plan

1. **v2 wire format.** Dense, symbolic, validatable. Proposed in
   SPEC-V2-DRAFT.md. Delivered as a draft in PR #14.
2. **The translator.** `sym2-render.py` turns packets into
   human-readable English. Operators read the rendered form. Agents
   read the wire form. Delivered in PR #14.
3. **Reasoning-trace packets.** The language grows from task
   assignment to thinking: agents reasoning with each other,
   dispatching subagents, and coordinating swarms in symbols.
   Delivered as v2.1 in the reasoning-extension PR: `bind`/`if`/
   `each`/`list`/`lt`/`eq` for naming values, branching, and
   iteration, with `$name` references checked by the validator;
   role 7 `swarm` for broadcast; acts 11 `delegate` and 12
   `report` plus op 40 `spawn` for subagent dispatch. Deliberate
   limits for a first dialect: no function definition, no
   recursion, single-expression branches (SPEC-V2-DRAFT.md §11).
4. **Migration.** `sym2-migrate.py` converts v1 packets to v2,
   failing loudly where English has no symbolic pattern yet.
   Delivered as a scaffold in PR #14. It covers the worked
   examples, not the full corpus, so the kit lock cannot move on
   it yet.
5. **Kit adoption.** The Protean Kit pins v1 until v2 is accepted.
   Then the lock moves. Correctly deferred.
6. **Measurement.** The empirical question underneath all of this:
   does symbolic communication actually buy capability and
   efficiency. Delivered as a harness in the measurement PR, not as
   an answer.
   `bench/` holds a 10-task paired corpus (v1 English and v2 per
   task), `sym2-bench.py` for machine metrics (3.1x fewer bytes than
   compact v1 JSON, with parse latency negligible for both forms),
   `EVAL.md` for the model A/B protocol, and `sym2-score.py` to score
   runs. The harness does not run models itself. A real capability
   claim still needs the eval run against models, reported with model
   name, date, and scores.

## What stays

- English remains the render target for operators. Nothing here
  hides machine behavior from humans.
- stdlib only, offline-friendly, zero-network install. The language
  MUST NOT need a service to be read or checked.
- v1 stays normative until v2 is accepted and merged.

## Open questions

- How far the symbolic layer goes: message content only, or further
  into training. This repo covers the messages.
- Registry governance: who mints codes and how collisions are
  prevented. Proposed in the v2 draft, decided by reviewers.
- Transport signing (O-1): the corruption-detection half is delivered
  as the v2-rcp edition. Signing itself, proof of identity across
  machines, stays open as a future protocol.
- Whether the capability gain is real. That is what the instrument
  is for.
