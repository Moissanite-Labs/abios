"""Wire-list encoding for ABIOS/3 refs traffic.

Two wire forms (SPEC-ABIOS-3 section 4):

1. Bare ``[a;b]`` string lists. Encoder and decoder are #39's
   ``encode_string_list`` / ``decode_string_list`` (3e251f0b), unchanged.
2. ``J:`` fallback: ``J:`` + canonical JSON (sorted keys, no spaces,
   ``ensure_ascii``, finite numbers) with ``%`` -> ``%25`` and space -> ``%20``,
   so the token never contains whitespace. Introduced by #53.

``encode_wire_list`` emits ``[]`` for the empty list, the bare form when it is
eligible *and* decodes back to exactly the same value, and ``J:`` otherwise.
``decode_wire_list`` is strict on ``J:``: non-finite numbers, duplicate object
keys, lone surrogates, malformed escapes and any token that is not exactly what
``encode_wire_list`` would emit for the decoded value are rejected.
"""
from __future__ import annotations

import json
import math
from typing import Any

_EMPTY_ITEM = "\\e"


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


def _item_needs_json_fallback(item: str) -> bool:
    if not isinstance(item, str):
        return True
    if item == "":
        return False
    if "\n" in item or "\r" in item or '"' in item:
        return True
    if "[" in item or "]" in item:
        return True
    if item.endswith("\\"):
        return True
    if item.startswith("[") or item.startswith("{") or item.startswith("http"):
        return True
    if item in {"-", "p", "t", "a", "h", "f", "v", "g", "0", "1"}:
        return True
    if item.isdigit():
        return True
    return False


def can_encode_string_list(items: list[Any]) -> bool:
    if not isinstance(items, list):
        return False
    if not items:
        return True
    return all(isinstance(x, str) and not _item_needs_json_fallback(x) for x in items)


def encode_string_list(items: list[str], sep: str = ";") -> str:
    if not can_encode_string_list(items):
        raise ValueError("list not eligible for wire-string encoding")
    if not items:
        return "[]"
    inner = sep.join(_escape_item(x) for x in items)
    return f"[{inner}]"


def decode_string_list(token: str, sep: str = ";") -> list[str] | None:
    if not token.startswith("[") or not token.endswith("]"):
        return None
    inner = token[1:-1]
    if inner == "":
        return []
    try:
        parsed = json.loads(token)
        if isinstance(parsed, list) and all(isinstance(x, str) for x in parsed):
            return parsed
    except json.JSONDecodeError:
        pass
    raw_parts = _split_items(inner, sep)
    if any(_item_needs_json_fallback(_unescape_item(p)) for p in raw_parts):
        return None
    return [_unescape_item(p) for p in raw_parts]


# ---------------------------------------------------------------------------
# Bare-or-J: codec (#53 superseded; qalam direction 2026-11-26)
# ---------------------------------------------------------------------------

J_PREFIX = "J:"


class _JRejected(ValueError):
    pass


def _reject_constant(name: str) -> Any:
    raise _JRejected(f"non-finite JSON constant {name} in J: wire list")


def _finite_float(text: str) -> float:
    val = float(text)
    if not math.isfinite(val):
        raise _JRejected(f"non-finite JSON number {text} in J: wire list")
    return val


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, val in pairs:
        if key in out:
            raise _JRejected(f"duplicate key {key!r} in J: wire list")
        out[key] = val
    return out


def _has_lone_surrogate(value: Any) -> bool:
    if isinstance(value, str):
        try:
            value.encode("utf-8")
        except UnicodeEncodeError:
            return True
        return False
    if isinstance(value, list):
        return any(_has_lone_surrogate(v) for v in value)
    if isinstance(value, dict):
        return any(_has_lone_surrogate(k) or _has_lone_surrogate(v) for k, v in value.items())
    return False


def _canonical_json(items: list[Any]) -> str:
    return json.dumps(items, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _percent_encode_j_body(raw: str) -> str:
    return raw.replace("%", "%25").replace(" ", "%20")


def _percent_decode_j_body(body: str) -> str:
    """Strictly decode a J: body: printable non-space ASCII, only %20 and %25 escapes."""
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


def _bare_round_trips(items: list[Any], sep: str) -> str | None:
    """Return #39's bare token for ``items`` iff #39's decoder gives back exactly ``items``."""
    if not can_encode_string_list(items):
        return None
    token = encode_string_list(items, sep)
    decoded = decode_string_list(token, sep)
    if decoded is None or len(decoded) != len(items):
        return None
    if any(type(a) is not str or a != b for a, b in zip(decoded, items)):
        return None
    return token


def encode_wire_list(items: list[Any], sep: str = ";") -> str:
    """Encode a JSON-native list as one wire token: ``[]``, bare ``[a;b]``, or ``J:``."""
    if type(items) is not list:
        raise ValueError("encode_wire_list requires an exact Python list")
    if type(sep) is not str or sep == "":
        raise ValueError("list separator must be a non-empty str")
    if _has_lone_surrogate(items):
        raise ValueError("lone surrogate in wire list (not encodable as UTF-8)")
    if not items:
        return "[]"
    bare = _bare_round_trips(items, sep)
    if bare is not None:
        return bare
    return J_PREFIX + _percent_encode_j_body(_canonical_json(items))


def decode_j_list(token: str, sep: str = ";") -> list[Any]:
    """Strictly decode a ``J:`` token; raise ValueError on anything the encoder cannot emit."""
    if type(token) is not str or not token.startswith(J_PREFIX):
        raise ValueError("not a J: wire-list token")
    raw = _percent_decode_j_body(token[len(J_PREFIX) :])
    try:
        parsed = json.loads(
            raw,
            parse_constant=_reject_constant,
            parse_float=_finite_float,
            object_pairs_hook=_no_duplicate_keys,
        )
    except _JRejected:
        raise
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("malformed JSON payload in J: wire-list token") from exc
    if type(parsed) is not list:
        raise ValueError("J: wire-list payload must decode to a JSON list")
    if _has_lone_surrogate(parsed):
        raise ValueError("lone surrogate in J: wire list")
    if encode_wire_list(parsed, sep) != token:
        raise ValueError("non-canonical J: wire-list token")
    return parsed


def decode_wire_list(token: str, sep: str = ";") -> list[Any]:
    """Decode ``[]``, a bare ``[a;b]`` list (via #39's decoder) or a strict ``J:`` token."""
    if type(token) is not str or token == "":
        raise ValueError("wire-list token must be a non-empty str")
    if token.startswith(J_PREFIX):
        return decode_j_list(token, sep)
    decoded = decode_string_list(token, sep)
    if decoded is None:
        raise ValueError(f"not a wire list: {token!r}")
    return decoded
