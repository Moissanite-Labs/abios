"""Sealed sessions: sender authentication bound to POST (SPEC-ABIOS-3.md section 8.2).

A sealed POST names a pre-shared key by id (``kid``) and a fresh session id
(``sid``). Both peers derive a session key from the key, the ids, and the hash
of the POST text, so every later tag is bound to the decode context that POST
established. Each direction keeps a MAC chain over its wire lines; a seal line
(``~<tag>``) authenticates every line since the previous seal. The chain makes
the sequence number implicit: a replayed, reordered, dropped, or injected line
breaks every later seal at zero wire cost.

HMAC-SHA256 (stdlib only). This is authenticity between holders of one key,
not non-repudiation, and not confidentiality. A peer records the (kid, sid) of
every POST it sends or accepts in one registry, so its own POST reflected back
to it is a replay.
"""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import struct
import threading
from dataclasses import dataclass
from typing import Iterable, Mapping, MutableSet, Optional

from post import POST_ACK_PREFIX, PROFILE_LINE, parse_post_handshake, verify_post_or_raise

AUTH_ALG = "hs256"
KDF_LABEL = "abios/3 seal hs256"
TAG_BITS_ALLOWED = (64, 96, 128)
DEFAULT_TAG_BITS = 64
MIN_KEY_BYTES = 16
MAX_SEAL_EVERY = 1024
SEAL_PREFIX = "~"
CLOSE_PREFIX = "~!"
INITIATOR = "i"
RESPONDER = "r"
DIRECTIONS = (INITIATOR, RESPONDER)

_KID_RE = re.compile(r"[A-Za-z0-9._-]{1,32}\Z")
_PARAM_KEYS = ("auth", "kid", "sid", "tag", "seal", "mac")
_CANON_INT_RE = re.compile(r"[1-9][0-9]{0,3}\Z")
# Section 8.2 normalization trims exactly these, never other Unicode whitespace.
_ASCII_WS = " \t\r\n"


class AuthError(ValueError):
    """Sealed-session failure. Fail closed: the session is unusable (section 8.1 fallback)."""


def _lp(*parts: bytes) -> bytes:
    """Length-prefix each part (4-byte big-endian length) so concatenation is unambiguous."""
    return b"".join(struct.pack(">I", len(p)) + p for p in parts)


def _mac(key: bytes, *parts: bytes) -> bytes:
    return hmac.new(key, _lp(*parts), hashlib.sha256).digest()


def _width(bits: int) -> int:
    return len(str((1 << bits) - 1))


def _dec(raw: bytes) -> str:
    """Fixed-width decimal of a big-endian integer.

    Every lexicon tokenizer splits digit runs into chunks of at most three, so
    the token cost is fixed (seven digit tokens for 64 bits) and below base64's
    average for the same bits (docs/abios-auth-bench.md).
    """
    return str(int.from_bytes(raw, "big")).zfill(_width(8 * len(raw)))


def _check_dec(text: str, bits: int, what: str) -> None:
    if len(text) != _width(bits) or not (text.isascii() and text.isdigit()) or int(text) >> bits:
        raise AuthError(f"{what} must be {_width(bits)} decimal digits below 2^{bits}")


def new_sid() -> str:
    """Fresh 64-bit session id. Never reuse one with the same key."""
    return _dec(secrets.token_bytes(8))


@dataclass(frozen=True)
class SealParams:
    kid: str
    sid: str
    tag_bits: int = DEFAULT_TAG_BITS
    seal_every: int = 1

    def __post_init__(self) -> None:
        if not _KID_RE.match(self.kid):
            raise AuthError("kid must be 1-32 characters of [A-Za-z0-9._-]")
        _check_dec(self.sid, 64, "sid")
        if self.tag_bits not in TAG_BITS_ALLOWED:
            raise AuthError(f"tag bits must be one of {TAG_BITS_ALLOWED}")
        if not 1 <= self.seal_every <= MAX_SEAL_EVERY:
            raise AuthError(f"seal must be between 1 and {MAX_SEAL_EVERY}")

    @property
    def tag_bytes(self) -> int:
        return self.tag_bits // 8

    def ack_params(self) -> str:
        """Ack-line parameters without ``mac``, in the fixed wire order."""
        return f"auth={AUTH_ALG} kid={self.kid} sid={self.sid} tag={self.tag_bits} seal={self.seal_every}"


def _normalize_context(context_text: str) -> str:
    """CRLF to LF, trim SP/HT/CR/LF at both ends, end with exactly one LF (section 8.2)."""
    return context_text.replace("\r\n", "\n").strip(_ASCII_WS) + "\n"


def _body_digest(body: str) -> str:
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]


def _signed_post_text(context_text: str, params: SealParams) -> str:
    """P: the ack line without `` mac=...``, LF, the normalized body. What the session key binds."""
    body = _normalize_context(context_text)
    ack = f"{POST_ACK_PREFIX}{PROFILE_LINE} {_body_digest(body)} {params.ack_params()}"
    return f"{ack}\n{body}"


def _session_key(key: bytes, params: SealParams, signed_text: str) -> bytes:
    if len(key) < MIN_KEY_BYTES:
        raise AuthError(f"key must be at least {MIN_KEY_BYTES} bytes")
    post_hash = hashlib.sha256(signed_text.encode("utf-8")).digest()
    return _mac(
        key,
        KDF_LABEL.encode("ascii"),
        params.kid.encode("ascii"),
        params.sid.encode("ascii"),
        post_hash,
    )


class SealedSession:
    """Keys for one sealed session. Hand out one sender and one receiver per direction."""

    def __init__(self, session_key: bytes, params: SealParams) -> None:
        self.params = params
        self._key = session_key

    def post_mac(self) -> str:
        return _dec(_mac(self._key, b"post")[: self.params.tag_bytes])

    def _direction_key(self, direction: str) -> bytes:
        if direction not in DIRECTIONS:
            raise AuthError(f"direction must be one of {DIRECTIONS}")
        return _mac(self._key, b"dir", direction.encode("ascii"))

    def sender(self, direction: str) -> "SealSender":
        return SealSender(self._direction_key(direction), self.params)

    def receiver(self, direction: str) -> "SealReceiver":
        return SealReceiver(self._direction_key(direction), self.params)


class _Chain:
    def __init__(self, dir_key: bytes, params: SealParams) -> None:
        self._key = dir_key
        self._params = params
        self._state = _mac(dir_key, b"chain")

    def absorb(self, line: str) -> None:
        if not isinstance(line, str) or not line or "\n" in line or "\r" in line:
            raise AuthError("a sealed line must be one non-empty line")
        if line.startswith(SEAL_PREFIX):
            raise AuthError("a message line must not begin with the seal prefix")
        try:
            data = line.encode("utf-8")
        except UnicodeEncodeError:
            raise AuthError("a sealed line must be valid UTF-8 text") from None
        self._state = _mac(self._key, self._state, data)

    def tag(self, label: bytes) -> str:
        return _dec(_mac(self._key, label, self._state)[: self._params.tag_bytes])


class SealSender:
    """Sender side of one direction: append seal lines to outgoing ABIOS lines."""

    def __init__(self, dir_key: bytes, params: SealParams) -> None:
        self._chain = _Chain(dir_key, params)
        self._params = params
        self._pending = 0
        self._closed = False

    def push(self, line: str, *, last: bool = False) -> list[str]:
        """Wire lines for one message line: the line, then a seal when the batch is full.

        ``last=True`` leaves a full batch for the close seal that must follow, saving one seal line.
        """
        if self._closed:
            raise AuthError("direction already closed")
        if self._pending >= self._params.seal_every:
            raise AuthError("batch already full: close() must follow a last push")
        self._chain.absorb(line)
        self._pending += 1
        if self._pending >= self._params.seal_every and not last:
            return [line] + self.flush()
        return [line]

    def flush(self) -> list[str]:
        """Seal the pending lines now (for latency); nothing to emit if none are pending."""
        if self._closed:
            raise AuthError("direction already closed")
        if not self._pending:
            return []
        self._pending = 0
        return [SEAL_PREFIX + self._chain.tag(b"seal")]

    def close(self) -> list[str]:
        """Close seal: covers any pending lines and declares the end of this direction."""
        if self._closed:
            raise AuthError("direction already closed")
        self._closed = True
        self._pending = 0
        return [CLOSE_PREFIX + self._chain.tag(b"close")]


class SealReceiver:
    """Receiver side of one direction. Releases lines only once a seal covers them."""

    def __init__(self, dir_key: bytes, params: SealParams) -> None:
        self._chain = _Chain(dir_key, params)
        self._params = params
        self._pending: list[str] = []
        self._closed = False
        self._failed = False

    @property
    def pending(self) -> int:
        return len(self._pending)

    @property
    def closed(self) -> bool:
        return self._closed

    def _check(self, got: str, label: bytes, what: str) -> list[str]:
        _check_dec(got, self._params.tag_bits, what)
        if not hmac.compare_digest(got, self._chain.tag(label)):
            raise AuthError(f"{what} tag mismatch")
        released, self._pending = self._pending, []
        return released

    def feed(self, wire_line: str) -> list[str]:
        """Consume one wire line; return the message lines this line releases (maybe none).

        Any failure, whatever raised it, ends the session: no resynchronization.
        """
        if self._failed:
            raise AuthError("sealed session already failed")
        try:
            return self._feed(wire_line)
        except Exception as exc:
            self._failed = True
            self._pending = []
            if isinstance(exc, AuthError):
                raise
            raise AuthError(f"malformed wire line: {exc}") from None

    def _feed(self, wire_line: str) -> list[str]:
        if self._closed:
            raise AuthError("line after close seal")
        if wire_line.startswith(CLOSE_PREFIX):
            released = self._check(wire_line[len(CLOSE_PREFIX) :], b"close", "close seal")
            self._closed = True
            return released
        if wire_line.startswith(SEAL_PREFIX):
            if not self._pending:
                raise AuthError("seal with no lines to cover")
            return self._check(wire_line[len(SEAL_PREFIX) :], b"seal", "seal")
        if len(self._pending) >= self._params.seal_every:
            raise AuthError(f"more than {self._params.seal_every} lines without a seal")
        self._chain.absorb(wire_line)
        self._pending.append(wire_line)
        return []


class SidRegistry:
    """Every (kid, sid) a peer sent or accepted. A POST reusing one is refused.

    Pass a persistent ``seen`` set to keep the record for the key's lifetime. The
    lock makes check-and-record atomic in one process; a store shared across
    processes must give the same insert-if-absent guarantee (section 8.2).
    """

    def __init__(self, seen: Optional[MutableSet[tuple[str, str]]] = None) -> None:
        self._seen = seen if seen is not None else set()
        self._lock = threading.Lock()

    def claim(self, kid: str, sid: str) -> None:
        with self._lock:
            if (kid, sid) in self._seen:
                raise AuthError("POST replay: session id already used with this key")
            self._seen.add((kid, sid))


def render_sealed_post(
    context_text: str,
    *,
    key: bytes,
    kid: str,
    seen: SidRegistry,
    sid: Optional[str] = None,
    tag_bits: int = DEFAULT_TAG_BITS,
    seal_every: int = 1,
) -> tuple[str, SealedSession]:
    """Render a sealed POST and return it with the initiator's session keys.

    Records (kid, sid) in ``seen`` first: the same registry this peer checks when
    it accepts POSTs, so its own POST reflected back to it is refused as a replay.
    """
    body = _normalize_context(context_text)
    if not body.startswith(PROFILE_LINE):
        raise ValueError("POST context must start with profile header")
    params = SealParams(kid=kid, sid=sid if sid is not None else new_sid(), tag_bits=tag_bits, seal_every=seal_every)
    signed = _signed_post_text(body, params)
    session = SealedSession(_session_key(key, params, signed), params)
    seen.claim(params.kid, params.sid)
    ack, rest = signed.split("\n", 1)
    return f"{ack} mac={session.post_mac()}\n{rest}", session


def is_sealed_post(blob: str) -> bool:
    first = blob.replace("\r\n", "\n").lstrip(_ASCII_WS).split("\n", 1)[0]
    return " auth=" in first


def open_sealed_post(
    blob: str,
    *,
    keyring: Mapping[str, bytes],
    seen: SidRegistry,
    minimal_context_text: Optional[str] = None,
    min_tag_bits: int = DEFAULT_TAG_BITS,
) -> tuple[str, SealedSession]:
    """Verify a sealed POST; return (normalized decoder context, responder's session keys).

    Checks, in order: ack prefix and profile, parameter syntax, order, and
    canonical values, the receiver's minimum tag size, the context digest, a
    known ``kid``, the POST MAC, then (only after the MAC verifies) the session
    id against ``seen``, then section 8.1 checks (c) and (d).
    """
    lines = blob.replace("\r\n", "\n").strip(_ASCII_WS).split("\n")
    head = f"{POST_ACK_PREFIX}{PROFILE_LINE} "
    if not lines or not lines[0].startswith(head):
        raise AuthError("missing POST ack line or profile mismatch")
    fields = lines[0][len(head) :].split(" ")
    if len(fields) != 1 + len(_PARAM_KEYS):
        raise AuthError("sealed POST ack must carry digest, auth, kid, sid, tag, seal, mac")
    digest, raw = fields[0], fields[1:]
    values: dict[str, str] = {}
    for want, item in zip(_PARAM_KEYS, raw):
        name, sep, value = item.partition("=")
        if name != want or not sep or not value:
            raise AuthError(f"sealed POST parameter {want}= missing or out of order")
        values[name] = value
    if values["auth"] != AUTH_ALG:
        raise AuthError(f"unsupported auth algorithm: {values['auth']}")
    if not _CANON_INT_RE.match(values["tag"]) or not _CANON_INT_RE.match(values["seal"]):
        raise AuthError("tag and seal must be canonical ASCII decimal")
    params = SealParams(
        kid=values["kid"], sid=values["sid"], tag_bits=int(values["tag"]), seal_every=int(values["seal"])
    )
    if params.tag_bits < min_tag_bits:
        raise AuthError(f"tag={params.tag_bits} is below this receiver's minimum of {min_tag_bits}")
    _check_dec(values["mac"], params.tag_bits, "mac")
    context = _normalize_context("\n".join(lines[1:]))
    if digest != _body_digest(context):
        raise AuthError("POST context digest mismatch")
    key = keyring.get(params.kid)
    if key is None:
        raise AuthError(f"unknown key id: {params.kid}")
    signed = _signed_post_text(context, params)
    session = SealedSession(_session_key(key, params, signed), params)
    if not hmac.compare_digest(values["mac"], session.post_mac()):
        raise AuthError("POST mac mismatch")
    seen.claim(params.kid, params.sid)
    if minimal_context_text is not None and context != _normalize_context(minimal_context_text):
        raise AuthError("POST context does not match decode-sufficient minimal context")
    from decoder_context import parse_decoder_context

    try:
        parse_decoder_context(context)
    except Exception as exc:
        raise AuthError(f"POST context does not parse: {exc}") from None
    return context, session


def open_post(
    blob: str,
    *,
    require_seal: bool,
    keyring: Optional[Mapping[str, bytes]] = None,
    seen: Optional[SidRegistry] = None,
    minimal_context_text: Optional[str] = None,
    min_tag_bits: int = DEFAULT_TAG_BITS,
) -> tuple[str, Optional[SealedSession]]:
    """Receiver policy entry point for one channel. Every failure raises AuthError.

    ``require_seal`` is per channel: a plain POST names no kid, so it cannot be
    matched to a per-key policy. A channel that requires sealing refuses a plain
    POST; one that accepts plain POSTs gets no protection from sealing.
    """
    if is_sealed_post(blob):
        if keyring is None or seen is None:
            raise AuthError("sealed POST needs a keyring and a session-id registry")
        return open_sealed_post(
            blob, keyring=keyring, seen=seen, minimal_context_text=minimal_context_text, min_tag_bits=min_tag_bits
        )
    if require_seal:
        raise AuthError("plain POST refused: this receiver requires a sealed session")
    try:
        _, context = parse_post_handshake(blob)
        if minimal_context_text is not None:
            verify_post_or_raise(blob, minimal_context_text)
        else:
            from decoder_context import parse_decoder_context

            parse_decoder_context(context)
    except Exception as exc:
        raise AuthError(f"plain POST rejected: {exc}") from None
    return context, None


def seal_transcript(sender: SealSender, lines: Iterable[str], *, close: bool = False) -> list[str]:
    """Interleave seal lines into a transcript; seal any remainder, or close the direction."""
    items = list(lines)
    out: list[str] = []
    for i, line in enumerate(items):
        out.extend(sender.push(line, last=close and i == len(items) - 1))
    out.extend(sender.close() if close else sender.flush())
    return out


def unseal_transcript(receiver: SealReceiver, wire_lines: Iterable[str], *, require_close: bool = False) -> list[str]:
    """Verify a complete sealed transcript and return its message lines in order."""
    out: list[str] = []
    for wire_line in wire_lines:
        out.extend(receiver.feed(wire_line))
    if receiver.pending:
        raise AuthError(f"{receiver.pending} trailing line(s) not covered by a seal")
    if require_close and not receiver.closed:
        raise AuthError("transcript ends without a close seal")
    return out
