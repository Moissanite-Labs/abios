"""Short REFS decode rules text (informative token overhead for models reading the wire)."""
from __future__ import annotations

REFS_DECODE_RULES = """ABIOS/3 refs lines: one fused command lexeme then space-separated values.
Session ids p/t/a/h/f expand from setup ids block; setup hex block maps v/g to revision/digest.
Null is -; booleans 1/0; string lists use [a;b] with ; between items (not JSON).
Quoted strings are literal. Content refs #n resolve after first inline publish (>=48 bytes).
Positional field order follows setup schema; restore defaults from setup defaults block.
"""
