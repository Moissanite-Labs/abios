# EVAL: model eval protocol for v1 English vs v2

## Goal

Find out whether models work with v2 symbolic packets as well as
with v1 English packets, and where they do better or worse. The
corpus is `tasks.jsonl`: 10 tasks, three kinds.

## Task kinds

**Comprehension** (t01-t06): the same packet in v1 English and v2,
each with 3-5 structured questions and exact answers. Run each form
in a fresh session. Ask the questions, record the answers verbatim.

**Render** (t07-t08): give the model the v2 packet, ask for a
plain-English rendering. Score by key-phrase containment (see
`key_phrases` in the task).

**Compile** (t09-t10): give the model the English description, ask
for the v2 packet line. Score by validator acceptance first, then
exact match against the reference line.

## Procedure

1. Pick a model. Record its name, version, and the date.
2. For each comprehension task, open two fresh sessions. In one,
   paste the v1 packet (as JSON) and ask the questions. In the
   other, paste the v2 line and ask the same questions. Do not let
   the sessions see each other.
3. For render tasks, paste the v2 line and ask: "Render this packet
   as plain English, one sentence per body expression."
4. For compile tasks, paste the English description and ask: "Write
   this as a single SYM-2P v2 packet line." Include the field order
   `V|ID|TK|F|T|A|ST|CF|CV|BODY|RQ|BASE|EXP` and the opcode table
   from SPEC-V2-DRAFT.md sections 3 and 4 in the prompt, so the
   model is not tested on memorization of the spec.
5. Save answers as `answers.json`:

```json
{
  "model": "example-model-1",
  "date": "2026-10-10",
  "runs": {
    "t01": {"v1": ["coordinator", "builder", "assign", "3-5",
                    "existing paths"],
            "v2": ["coordinator", "builder", "assign", "3-5",
                    "existing paths"]},
    "t07": {"v2": "Scope: implement sections 3-5 of sym-2p/1.0. ..."},
    "t09": {"v1": "2|c901|mr1|1|2|1|1|80|60|...|1||0"}
  }
}
```

6. Score it: `python3 bench/sym2-score.py bench/tasks.jsonl answers.json`

## Reading the scores

- Comprehension: accuracy per form. If v2 matches or beats v1,
  models read symbols as well as prose. If v2 lags, the gap names
  what to fix: the opcode, the scope rule, or the rendering.
- Render: phrase hits. Measures whether the model recovered the
  meaning, not the exact words.
- Compile: `valid` means the validator accepted it; `exact` means
  byte-identical to the reference. Valid-but-not-exact is
  interesting: it shows the model grasped the grammar but not the
  canonical form.

## Limits

Ten hand-written tasks are a smoke test, not a benchmark. The
corpus covers the worked patterns, not the full language. Report
scores with the model name and date, and do not generalize from one
model to all models. The honest claim this protocol supports is
"on this task set, with this model, v2 scored X and v1 scored Y."
