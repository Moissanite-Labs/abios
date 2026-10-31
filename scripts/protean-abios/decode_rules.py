"""REFS decode rules text counted in bench (informative model-facing overhead beyond POST setup body)."""
from __future__ import annotations

# Abbreviated summary (PR #36 first draft — too short for standalone decode; do not bill alone).
REFS_DECODE_RULES_ABBREV = """ABIOS/3 refs lines: one fused command lexeme then space-separated values.
Session ids p/t/a/h/f expand from setup ids block; setup hex block maps v/g to revision/digest.
Null is -; booleans 1/0; string lists use [a;b] with ; between items (not JSON).
Quoted strings are literal. Content refs #n resolve after first inline publish (>=48 bytes).
Positional field order follows setup schema; restore defaults from setup defaults block.
"""

# Normative decode rules for refs traffic (matches SPEC-ABIOS-3 §4–§5.3, §6–§7, setup ids/hex/defaults).
# A model needs this in addition to the POST decoder-context body (lexicon, schema, ids, optional hex, defaults).
REFS_DECODE_RULES = """ABIOS/3 refs wire decode (lossless):

Lines: one UTF-8 line per command, no trailing whitespace. Each refs line starts with either (a) one fused command lexeme from setup refs_cmd, or (b) format tag E immediately followed by the cmd lexeme from setup concepts when refs_cmd is omitted. Remaining tokens are positional field values in schema order for that command.

Tokenization: ASCII space separates tokens. No empty tokens. Quoted strings use "..." with \\, \", \\n, \\r escapes; quoted tokens are always literal strings. Null is -. Booleans are unquoted 1 or 0. Integers are unquoted digit runs.

Session handles: unquoted p/t/a/h/f expand to full ids from setup ids block. Optional setup hex block maps short tokens (e.g. v, g) to full hex strings; only tokens listed in hex expand.

Wire string lists: unquoted [ ... ] with items separated by ; (setup list_sep). Use \\; and \\\\ inside items. Bracket spans including internal spaces are one token. If [ ... ] is valid canonical JSON array of strings, JSON decode is also accepted.

Inline JSON objects/arrays: unquoted token starting with { or [ when wire-list form does not apply; canonical JSON.

Content refs: opaque #n labels resolve via session content store after the value was published inline (serialized length >= 48 bytes); unknown #n is an error.

Refs values use content addressing per S-9: first publish inline, later lines may emit #n. Decoders update session snapshots and content store after each line (same as canonical forge apply).

Default fields omitted on other encoders are present positionally on refs lines; merge setup defaults block for any default not on wire.

Fail closed: bad quoting, unknown fused command, arity mismatch, unknown content ref, or ambiguous token parse must error.
"""

# Backward-compatible alias used by bench/reporting.
REFS_RULES = REFS_DECODE_RULES
