"""Lossless single-token wire-list encoding for ABIOS/3 (PR #39 follow-up fix).

Provides:
  1. `encode_wire_list` / `decode_wire_list`: 100% lossless, space-free,
     single-token wire codec closing all three PR #39 wire_lists.py defects:
       - Whitespace-only strings (e.g. [' '], ['\\t']) no longer collapse to [].
       - Non-string scalar lists (e.g. [1, 2], [True, False], [None], [-1])
         preserve exact Python types and cardinality instead of corrupting into
         single-element string lists like ['1,2'].
       - Strings containing spaces and brackets (e.g. ['see [1] now']) emit a
         single space-free J:... carrier token instead of splitting across
         whitespace boundaries.
  2. Backward-compatible `can_encode_string_list` / `encode_string_list` /
     `decode_string_list` hardened against the whitespace-erasure and non-string
     JSON-array fallthrough defects.
"""
from __future__ import annotations

import json
from typing import Any

_EMPTY_ITEM = "\\e"
_RESERVED_ATOMS = frozenset({"-", "p", "t", "a", "h", "f", "v", "g", "0", "1"})
_FORBIDDEN_SEP_CHARS = frozenset({"[", "]", '"', "\\", "%", ",", "{", "}"})
_S_FORBIDDEN_CHARS = frozenset({'"', "[", "]", "\\", ",", "{", "}"})


def _validate_sep(sep: Any) -> str:
    if type(sep) is not str or len(sep) != 1 or sep.isspace() or sep in _FORBIDDEN_SEP_CHARS:
        raise ValueError("sep must be a single non-whitespace, non-delimiter ASCII char")
    return sep


def _is_safe_s_item(item: Any, sep: str) -> bool:
    if type(item) is not str:
        return False
    if item == "":
        return False
    if any(ch.isspace() for ch in item):
        return False
    if sep in item or any(ch in _S_FORBIDDEN_CHARS for ch in item):
        return False
    if item in _RESERVED_ATOMS or item.startswith("http") or item.isdigit():
        return False
    return True


def _percent_decode_j_body(body: str) -> str:
    """Strictly decode J: percent-escaped printable ASCII JSON body."""
    out: list[str] = []
    i = 0
    n = len(body)
    while i < n:
        ch = body[i]
        code = ord(ch)
        if code <= 0x20 or code > 0x7E:
            raise ValueError("J: wire-list body must contain printable non-space ASCII only")
        if ch == "%":
            esc = body[i + 1 : i + 3]
            if esc == "20":
                out.append(" ")
            elif esc == "25":
                out.append("%")
            else:
                raise ValueError(f"unsupported or truncated percent escape %{esc} in J: wire-list body")
            i += 3
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def encode_wire_list(items: list[Any], sep: str = ";") -> str:
    """Encode any JSON-serializable list as one space-free lossless wire token.

    Wire forms:
      - `[]` for empty lists.
      - `S[a;b;...]` when every element is a safe space/delimiter-free string.
      - `J:<escaped_json>` for all other lists (whitespace strings, brackets,
        non-string scalars, empty strings, nested lists/dicts, Unicode, etc.).
    """
    if type(items) is not list:
        raise ValueError("encode_wire_list requires an exact Python list")
    sep = _validate_sep(sep)
    if not items:
        return "[]"
    if all(_is_safe_s_item(x, sep) for x in items):
        return "S[" + sep.join(items) + "]"
    raw = json.dumps(items, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    escaped = raw.replace("%", "%25").replace(" ", "%20")
    return "J:" + escaped


def decode_wire_list(token: str, sep: str = ";") -> list[Any]:
    """Strictly invert `encode_wire_list`; fail closed with ValueError on invalid input."""
    if type(token) is not str or token == "":
        raise ValueError("wire-list token must be a non-empty str")
    sep = _validate_sep(sep)
    if token == "[]":
        return []
    if token.startswith("S[") and token.endswith("]"):
        parts = token[2:-1].split(sep)
        if any(not _is_safe_s_item(p, sep) for p in parts):
            raise ValueError("unsafe or empty item in S[...] wire-list token")
        return parts
    if token.startswith("J:"):
        raw = _percent_decode_j_body(token[2:])
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("malformed JSON payload in J: wire-list token") from exc
        if type(parsed) is not list:
            raise ValueError("J: wire-list payload must decode to a JSON list")
        return parsed
    raise ValueError(f"unrecognized wire-list token prefix: {token!r}")


# ---------------------------------------------------------------------------
# Hardened backward-compatible [a;b] string-list API
# ---------------------------------------------------------------------------

def _escape_item(item: str) -> str:
    if item == "":
        return _EMPTY_ITEM
    return item.replace("\\", "\\\\").replace(";", "\\;")


def _unescape_item(item: str) -> str:
    if item == _EMPTY_ITEM:
        return ""
    out: list[str] = []
    i = 0
    while i < len(item):
        if item[i] == "\\" and i + 1 < len(item):
            nxt = item[i + 1]
            if nxt in {"\\", ";"}:
                out.append(nxt)
                i += 2
                continue
        out.append(item[i])
        i += 1
    return "".join(out)


def _split_items(inner: str, sep: str) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    i = 0
    while i < len(inner):
        if inner[i] == "\\" and i + 1 < len(inner):
            buf.append(inner[i : i + 2])
            i += 2
            continue
        if inner[i : i + len(sep)] == sep:
            parts.append("".join(buf))
            buf = []
            i += len(sep)
            continue
        buf.append(inner[i])
        i += 1
    parts.append("".join(buf))
    return parts


def _item_needs_json_fallback(item: Any) -> bool:
    if type(item) is not str:
        return True
    if any(ch.isspace() for ch in item):
        return True
    if '"' in item or "[" in item or "]" in item:
        return True
    if item.endswith("\\"):
        return True
    if item.startswith("{") or item.startswith("http"):
        return True
    if item in _RESERVED_ATOMS:
        return True
    if item.isdigit():
        return True
    return False


def can_encode_string_list(items: list[Any]) -> bool:
    if type(items) is not list:
        return False
    if not items:
        return True
    return all(type(x) is str and not _item_needs_json_fallback(x) for x in items)


def encode_string_list(items: list[str], sep: str = ";") -> str:
    sep = _validate_sep(sep)
    if not can_encode_string_list(items):
        raise ValueError("list not eligible for wire-string encoding")
    if not items:
        return "[]"
    inner = sep.join(_escape_item(x) for x in items)
    return f"[{inner}]"


def decode_string_list(token: str, sep: str = ";") -> list[str] | None:
    if type(token) is not str:
        return None
    try:
        sep = _validate_sep(sep)
    except ValueError:
        return None
    if (token.startswith("S[") and token.endswith("]")) or token.startswith("J:"):
        try:
            decoded = decode_wire_list(token, sep)
        except ValueError:
            return None
        if all(type(x) is str for x in decoded):
            return decoded
        return None
    if not token.startswith("[") or not token.endswith("]"):
        return None
    inner = token[1:-1]
    if inner == "":
        return []
    if inner.strip() == "":
        return None
    try:
        parsed = json.loads(token)
        if type(parsed) is list:
            if all(type(x) is str for x in parsed):
                return parsed
            return None
    except json.JSONDecodeError:
        pass
    raw_parts = _split_items(inner, sep)
    unescaped = [_unescape_item(p) for p in raw_parts]
    if any(_item_needs_json_fallback(val) for val in unescaped):
        return None
    return unescaped
