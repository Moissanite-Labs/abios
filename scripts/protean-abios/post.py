"""POST — session handshake (decode-sufficient context exchange before ABIOS traffic)."""
from __future__ import annotations

import hashlib
import re

from decoder_context import FORMAT_HEADER, LEGACY_FORMAT_HEADERS, parse_decoder_context

PROFILE_LINE = FORMAT_HEADER.rstrip()
POST_ACK_PREFIX = "POST ok "
_DIGEST_RE = re.compile(r"^[0-9a-f]{16}$")


def context_digest(context_text: str) -> str:
    """16-hex digest of normalized decoder context (LF newlines, trailing newline on body)."""
    normalized = context_text.replace("\r\n", "\n")
    if not normalized.endswith("\n"):
        normalized += "\n"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def _body_profile(context_text: str) -> str:
    line = context_text.replace("\r\n", "\n").split("\n", 1)[0]
    return line


def post_ack_line(minimal_context_text: str) -> str:
    profile = _body_profile(minimal_context_text)
    digest = context_digest(minimal_context_text)
    return f"{POST_ACK_PREFIX}{profile} {digest}\n"


def render_post_handshake(minimal_context_text: str) -> str:
    """Render POST exchange: ack line + decode-sufficient context body."""
    text = minimal_context_text.replace("\r\n", "\n")
    if not text.endswith("\n"):
        text += "\n"
    profile = _body_profile(text)
    if profile != "abios/3" and profile not in LEGACY_FORMAT_HEADERS:
        raise ValueError("POST context must start with profile header")
    digest = context_digest(text)
    return f"{POST_ACK_PREFIX}{profile} {digest}\n{text}"


def _require_post_blocks(context: str) -> None:
    if not all(marker in context for marker in ("lexicon:", "schema:", "ids:")):
        raise ValueError("POST body missing required decoder blocks")


def parse_post_handshake(blob: str) -> tuple[str, str]:
    """Return (ack_line, decoder_context_text)."""
    normalized = blob.replace("\r\n", "\n")
    if not normalized.endswith("\n"):
        normalized += "\n"
    lines = normalized.split("\n")
    if not lines or not lines[0].startswith(POST_ACK_PREFIX):
        raise ValueError("missing POST ack line")
    ack = lines[0]
    context = "\n".join(lines[1:])
    if not context.strip():
        raise ValueError("POST body missing decoder context")
    body_lines = context.split("\n")
    if len(body_lines) < 2 or not any(line.strip() for line in body_lines[1:]):
        raise ValueError("POST body is header-only")
    profile = body_lines[0]
    if profile != "abios/3" and profile not in LEGACY_FORMAT_HEADERS:
        raise ValueError("POST context profile missing or unknown")
    expected_prefix = f"{POST_ACK_PREFIX}{profile} "
    if not ack.startswith(expected_prefix):
        raise ValueError("POST profile mismatch between ack and body")
    digest = ack[len(expected_prefix) :]
    if not _DIGEST_RE.match(digest):
        raise ValueError("POST digest malformed")
    _require_post_blocks(context)
    if digest != context_digest(context):
        raise ValueError("POST context digest mismatch")
    return ack, context


def verify_post_or_raise(post_blob: str, minimal_context_text: str) -> None:
    """Verify POST matches expected minimal context; raise on mismatch (fallback signal)."""
    _, parsed = parse_post_handshake(post_blob)
    expected = minimal_context_text.replace("\r\n", "\n")
    if not expected.endswith("\n"):
        expected += "\n"
    got = parsed.replace("\r\n", "\n")
    if not got.endswith("\n"):
        got += "\n"
    if got != expected:
        raise ValueError("POST context does not match decode-sufficient minimal context")
    parse_decoder_context(parsed)


def post_fingerprint(minimal_context_text: str) -> str:
    """Short fingerprint for logs and tests."""
    return context_digest(minimal_context_text)
