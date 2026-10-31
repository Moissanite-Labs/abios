"""Content-addressed store with deterministic ref labels."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

INLINE_REF_MIN_BYTES = 48


def _canonical_bytes(value: str | list | dict) -> bytes:
    if isinstance(value, str):
        return value.encode("utf-8")
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def serialized_byte_length(value: str | list | dict) -> int:
    return len(_canonical_bytes(value))


def content_digest(value: str | list | dict) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()[:16]


@dataclass
class ContentStore:
    by_digest: dict[str, str | list | dict] = field(default_factory=dict)
    digest_to_ref: dict[str, str] = field(default_factory=dict)
    ref_to_digest: dict[str, str] = field(default_factory=dict)
    published_on_wire: set[str] = field(default_factory=set)
    _seq: int = 0

    def intern(self, value: str | list | dict, *, min_bytes: int = INLINE_REF_MIN_BYTES) -> str | list | dict:
        raw = value
        if serialized_byte_length(value) < min_bytes:
            return value
        dg = content_digest(value)
        self.by_digest[dg] = raw
        if dg in self.digest_to_ref:
            ref = self.digest_to_ref[dg]
            if dg in self.published_on_wire:
                return ref
            return raw
        ref = self._alloc_ref()
        self.digest_to_ref[dg] = ref
        self.ref_to_digest[ref] = dg
        return raw

    def ref_if_published(self, value: str | list | dict) -> str | list | dict:
        """After first inline publish, emit ref token."""
        if serialized_byte_length(value) < INLINE_REF_MIN_BYTES:
            return value
        dg = content_digest(value)
        if dg not in self.by_digest:
            self.by_digest[dg] = value
        if dg not in self.digest_to_ref:
            ref = self._alloc_ref()
            self.digest_to_ref[dg] = ref
            self.ref_to_digest[ref] = dg
        if dg in self.published_on_wire:
            return self.digest_to_ref[dg]
        self.published_on_wire.add(dg)
        return value

    def mark_from_wire(self, token: str, value: str | list | dict) -> None:
        dg = content_digest(value)
        self.by_digest[dg] = value
        if token not in self.ref_to_digest:
            self.ref_to_digest[token] = dg
            self.digest_to_ref[dg] = token
        self.published_on_wire.add(dg)

    def resolve(self, token: str) -> str | list | dict:
        if token in self.ref_to_digest:
            dg = self.ref_to_digest[token]
            return self.by_digest[dg]
        raise KeyError(f"unknown content ref {token!r}")

    def observe_inline(self, value: str | list | dict) -> None:
        if serialized_byte_length(value) < INLINE_REF_MIN_BYTES:
            return
        dg = content_digest(value)
        self.by_digest[dg] = value
        if dg not in self.digest_to_ref:
            ref = self._alloc_ref()
            self.digest_to_ref[dg] = ref
            self.ref_to_digest[ref] = dg
        self.published_on_wire.add(dg)

    def _alloc_ref(self) -> str:
        for i in range(1, 65536):
            ref = f"#{i}"
            if ref not in self.ref_to_digest:
                return ref
        self._seq += 1
        return f"#h{self._seq:x}"
