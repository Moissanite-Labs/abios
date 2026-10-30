"""POST — session handshake (decode-sufficient context exchange before ABIOS traffic)."""
from __future__ import annotations

import hashlib

from decoder_context import FORMAT_HEADER, parse_decoder_context, render_decoder_context

PROFILE_LINE = FORMAT_HEADER.rstrip()
POST_ACK_PREFIX = "POST ok "


def context_digest(context_text: str) -> str:
    """16-hex digest of normalized decoder context (for POST verification)."""
    normalized = context_text.replace("\r\n", "\n").strip() + "\n"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def render_post_handshake(minimal_context_text: str) -> str:
    """Render POST exchange: ack line + decode-sufficient context body."""
    text = minimal_context_text.replace("\r\n", "\n").strip() + "\n"
    if not text.startswith(PROFILE_LINE):
        raise ValueError("POST context must start with profile header")
    digest = context_digest(text)
    return f"{POST_ACK_PREFIX}{PROFILE_LINE} {digest}\n{text}"


def parse_post_handshake(blob: str) -> tuple[str, str]:
    """Return (ack_line, decoder_context_text)."""
    lines = blob.replace("\r\n", "\n").strip().split("\n")
    if not lines or not lines[0].startswith(POST_ACK_PREFIX):
        raise ValueError("missing POST ack line")
    ack = lines[0]
    context = "\n".join(lines[1:]) + "\n"
    expected_prefix = f"{POST_ACK_PREFIX}{PROFILE_LINE} "
    if not ack.startswith(expected_prefix):
        raise ValueError("POST profile mismatch")
    digest, sep, _params = ack[len(expected_prefix) :].partition(" ")
    if sep:
        # A sealed POST (section 8.2) must never be accepted as a plain one.
        raise ValueError("POST carries sealed-session parameters; open it with auth.open_sealed_post")
    if digest != context_digest(context):
        raise ValueError("POST context digest mismatch")
    return ack, context


def verify_post_or_raise(post_blob: str, minimal_context_text: str) -> None:
    """Verify POST matches expected minimal context; raise on mismatch (fallback signal)."""
    _, parsed = parse_post_handshake(post_blob)
    if parsed.replace("\r\n", "\n").strip() + "\n" != minimal_context_text.replace("\r\n", "\n").strip() + "\n":
        raise ValueError("POST context does not match decode-sufficient minimal context")
    parse_decoder_context(parsed)


def post_fingerprint(minimal_context_text: str) -> str:
    """Short fingerprint for logs and tests."""
    return context_digest(minimal_context_text)
