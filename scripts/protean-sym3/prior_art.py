"""Prior-art and alternative wire baselines for SYM-3 bench."""
from __future__ import annotations

import hashlib
import json

from canonical import canonical_payload

# Agora (multi-agent messaging); arXiv:2410.11905 — cited as prior art for SYM-3 refs.
AGORA_ARXIV = "2410.11905"
AGORA_SPEC = (
    "Agora-style deterministic envelope: one line per message, "
    "SHA-256 of this spec document, space, compact JSON object with cmd and payload."
)
AGORA_SPEC_SHA256 = hashlib.sha256(AGORA_SPEC.encode()).hexdigest()
AGORA_PREFIX = f"agora/{AGORA_ARXIV}/{AGORA_SPEC_SHA256[:16]}"


def _canonical_message(action: str, payload: dict) -> dict:
    return {"cmd": action, "payload": canonical_payload(action, payload)}


def encode_toon_line(action: str, payload: dict) -> str:
    try:
        import toon_format as toon

        msg = _canonical_message(action, payload)
        if hasattr(toon, "dumps"):
            return toon.dumps(msg).strip()
        if hasattr(toon, "encode"):
            return toon.encode(msg).strip()
    except (ImportError, NotImplementedError):
        pass
    return _toon_fallback(action, payload)


def _toon_fallback(action: str, payload: dict) -> str:
    """Minimal TOON-like encoding when toon-format is not installed (see github.com/toon-format/toon)."""
    msg = _canonical_message(action, payload)
    lines = [f"cmd: {msg['cmd']}", "payload:"]
    for key, value in sorted(msg["payload"].items()):
        if isinstance(value, list):
            lines.append(f"  {key}[{len(value)}]: {','.join(json.dumps(v) for v in value)}")
        else:
            lines.append(f"  {key}: {json.dumps(value) if isinstance(value, (dict, list)) else value}")
    return "\n".join(lines)


def encode_keyvalue_english_line(action: str, payload: dict) -> str:
    """Lossless one-line key=value serialization (not Chain-of-Draft terse prose)."""
    p = canonical_payload(action, payload)
    parts = [action.replace(".", " ")]
    for key in sorted(p.keys()):
        val = p[key]
        if isinstance(val, list):
            parts.append(f"{key}={';'.join(json.dumps(v, separators=(',', ':')) for v in val)}")
        else:
            parts.append(f"{key}={json.dumps(val, separators=(',', ':')) if isinstance(val, str) else val}")
    return " ".join(parts)


encode_terse_english_line = encode_keyvalue_english_line


def encode_agora_line(action: str, payload: dict) -> str:
    body = json.dumps(_canonical_message(action, payload), sort_keys=True, separators=(",", ":"))
    return f"{AGORA_PREFIX} {body}"


def agora_setup_prefix() -> str:
    return f"{AGORA_SPEC}\n{AGORA_PREFIX}\n"
