"""Semicolon-bracket encoding for string lists (refs wire optimization)."""
from __future__ import annotations

import json
import re
from typing import Any

_ITEM_SPLIT = re.compile(r"(?<!\\);")


def _escape_item(item: str) -> str:
    return item.replace("\\", "\\\\").replace(";", "\\;")


def _unescape_item(item: str) -> str:
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


def _item_needs_json_fallback(item: str) -> bool:
    if not isinstance(item, str):
        return True
    if item == "":
        return False
    if "\n" in item or "\r" in item or '"' in item:
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
    parts = _ITEM_SPLIT.split(inner)
    if any(_item_needs_json_fallback(_unescape_item(p)) for p in parts):
        return None
    return [_unescape_item(p) for p in parts]
