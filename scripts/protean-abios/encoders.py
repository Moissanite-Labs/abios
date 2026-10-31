"""ABIOS/3 wire encoders and decoders."""
from __future__ import annotations

import copy
import json
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from canonical import ForgeMessage, canonical_payload, normalize_message
from content_store import ContentStore
from lexicon import Lexicon, load_lexicon
from schema import POSITIONAL_ORDER
from state import Sym3Session
from wire_lists import can_encode_string_list, decode_string_list, encode_string_list

_QUOTED = re.compile(r'"((?:\\.|[^"\\])*)"')
_REF_LABEL = re.compile(r"^#\d+$|^#h[0-9a-f]+$")


def _unquote_content(s: str) -> str:
    out: list[str] = []
    i = 0
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s):
            nxt = s[i + 1]
            if nxt == "n":
                out.append("\n")
            elif nxt == "r":
                out.append("\r")
            elif nxt == '"':
                out.append('"')
            elif nxt == "\\":
                out.append("\\")
            else:
                out.append(nxt)
            i += 2
            continue
        out.append(s[i])
        i += 1
    return "".join(out)


def _is_ref_label(token: str) -> bool:
    return bool(_REF_LABEL.match(token))


def _register_inline(content: ContentStore, value: str | list | dict) -> None:
    content.observe_inline(value)


def _is_delta_short_form(parts: list[WireToken], lex: Lexicon) -> bool:
    if len(parts) != 3 or not parts[2].text.startswith("st="):
        return False
    try:
        action = _cmd_from_lex(lex, parts[0].text)
    except ValueError:
        return False
    return action == "task.transition"


def _lex_status(lex: Lexicon, status: str) -> str:
    try:
        return lex.word("status", status).strip()
    except KeyError as exc:
        raise ValueError(f"unknown status {status!r}") from exc


def _quote(s: str) -> str:
    esc = (
        s.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )
    return f'"{esc}"'


def _string_must_quote(value: str, session: Sym3Session) -> bool:
    if value == "":
        return True
    if value == "-":
        return True
    if value.isdigit():
        return True
    if value in {"p", "t", "a", "h", "f", "v", "g"}:
        return True
    if value.startswith("[") or value.startswith("{"):
        return True
    if _is_ref_label(value):
        return True
    if (
        " " in value
        or ";" in value
        or "," in value
        or '"' in value
        or "\n" in value
        or "\r" in value
        or value.startswith("http")
    ):
        return True
    return False


def _escape_token(value: Any, session: Sym3Session, content: ContentStore, use_refs: bool) -> str:
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(int(value)) if isinstance(value, int) or value == int(value) else str(value)
    if isinstance(value, list):
        list_sep = ";"
        if can_encode_string_list(value):
            blob = encode_string_list(value, list_sep)
        else:
            blob = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        if use_refs:
            published = session.content.ref_if_published(value)
            if isinstance(published, str) and published in session.content.ref_to_digest:
                return published
            return _escape_token(published, session, content, False)
        _register_inline(content, value)
        if "\n" in blob or "\r" in blob:
            return _quote(blob)
        if " " in blob and decode_string_list(blob) is None:
            return _quote(blob)
        return blob
    if isinstance(value, dict):
        blob = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        if use_refs:
            published = session.content.ref_if_published(value)
            if isinstance(published, str) and published in session.content.ref_to_digest:
                return published
            return _escape_token(published, session, content, False)
        _register_inline(content, value)
        if "\n" in blob or "\r" in blob:
            return _quote(blob)
        if " " in blob and decode_string_list(blob) is None:
            return _quote(blob)
        return blob
    if isinstance(value, str):
        if _is_ref_label(value):
            return _quote(value)
        alias = session.hex_alias_for(value)
        if alias is not None:
            return alias
        if use_refs:
            published = session.content.ref_if_published(value)
            if isinstance(published, str) and published in session.content.ref_to_digest and published != value:
                return published
            if published is value or (isinstance(published, str) and published == value):
                if not _string_must_quote(value, session):
                    if value == session.project_id:
                        return "p"
                    if value == session.task_id:
                        return "t"
                    if value == session.agent_id:
                        return "a"
                    if value == session.human_id:
                        return "h"
                    if value == session.artifact_id:
                        return "f"
                    _register_inline(session.content, value)
                    return value
            value = published if isinstance(published, str) else value
        if value == session.project_id:
            return "p"
        if value == session.task_id:
            return "t"
        if value == session.agent_id:
            return "a"
        if value == session.human_id:
            return "h"
        if value == session.artifact_id:
            return "f"
        if _string_must_quote(value, session):
            _register_inline(session.content, value)
            return _quote(value)
        _register_inline(session.content, value)
        return value
    return _quote(str(value))


@dataclass(frozen=True)
class WireToken:
    text: str
    quoted: bool


def _scan_bracket_token(line: str, start: int, open_ch: str, close_ch: str) -> int:
    depth = 0
    i = start
    while i < len(line):
        ch = line[i]
        if ch == "\\" and i + 1 < len(line):
            i += 2
            continue
        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    raise ValueError(f"unclosed {open_ch} in wire line")


def _split_line(line: str) -> list[WireToken]:
    parts: list[WireToken] = []
    i = 0
    while i <= len(line):
        if i == len(line):
            break
        if line[i] == '"':
            m = _QUOTED.match(line, i)
            if not m:
                raise ValueError("bad quoted token")
            parts.append(WireToken(_unquote_content(m.group(1)), quoted=True))
            i = m.end()
            if i < len(line) and line[i] != " ":
                raise ValueError("bad quoted token spacing")
            if i < len(line) and line[i] == " ":
                i += 1
            continue
        if line[i] in "[{":
            close = "]" if line[i] == "[" else "}"
            end = _scan_bracket_token(line, i, line[i], close)
            parts.append(WireToken(line[i:end], quoted=False))
            i = end
            if i < len(line) and line[i] == " ":
                i += 1
            continue
        j = i
        while j < len(line) and line[j] != " ":
            j += 1
        if j == i:
            if j < len(line) and line[j] == " ":
                parts.append(WireToken("", quoted=False))
                i = j + 1
                continue
            break
        parts.append(WireToken(line[i:j], quoted=False))
        i = j + 1 if j < len(line) and line[j] == " " else j
    return parts


def _token_texts(tokens: list[WireToken]) -> list[str]:
    return [t.text for t in tokens]


def _unescape_token(token: WireToken, session: Sym3Session, content: ContentStore) -> Any:
    if token.quoted:
        _register_inline(content, token.text)
        return token.text
    raw = token.text
    if raw == "":
        raise ValueError("empty wire token")
    if raw == "-":
        return None
    if raw in content.ref_to_digest:
        return content.resolve(raw)
    if _is_ref_label(raw):
        raise ValueError(f"unknown content ref {raw!r}")
    hex_val = session.resolve_hex_alias(raw)
    if hex_val is not None:
        return hex_val
    if raw in {"p", "t", "a", "h", "f"}:
        _, rid = session.resolve_ref(raw)
        return rid
    if raw.startswith("[") or raw.startswith("{"):
        wire_list = decode_string_list(raw)
        if wire_list is not None:
            _register_inline(content, wire_list)
            return wire_list
        try:
            val = json.loads(raw)
            _register_inline(content, val)
            return val
        except json.JSONDecodeError as exc:
            raise ValueError(f"bad inline JSON token {raw!r}") from exc
    if raw.isdigit():
        return int(raw)
    if raw in {"0", "1"}:
        return raw == "1"
    _register_inline(content, raw)
    return raw


def _cmd_from_lex(lex: Lexicon, word: str) -> str:
    word_stripped = word.strip()
    matches = [cmd for cmd, w in lex.raw["cmd"].items() if w.strip() == word_stripped or w == word]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ValueError(f"ambiguous command lexeme {word!r}")
    raise ValueError(f"unknown command lexeme {word!r}")


def _lex_cmd(lex: Lexicon, action: str) -> str:
    return lex.word("cmd", action).strip()


def _status_from_lex(lex: Lexicon, word: str) -> str:
    matches = [st for st, w in lex.raw["status"].items() if w.strip() == word.strip() or w == word]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ValueError(f"ambiguous status lexeme {word!r}")
    raise ValueError(f"unknown status lexeme {word!r}")


def _require_tag(line: str, tag: str) -> str:
    if not line.startswith(tag):
        raise ValueError(f"expected format tag {tag!r}")
    return line[len(tag) :]


class Encoder(ABC):
    tag_name: str

    def __init__(self, lexicon: Lexicon | None = None, schema: dict[str, list[str]] | None = None) -> None:
        self.lex = lexicon or load_lexicon()
        self.schema = schema or POSITIONAL_ORDER

    @property
    def tag(self) -> str:
        return self.lex.tag(self.tag_name)

    @abstractmethod
    def encode(self, action: str, payload: dict[str, Any], session: Sym3Session) -> str: ...

    @abstractmethod
    def decode(self, line: str, session: Sym3Session) -> ForgeMessage: ...


class PositionalEncoder(Encoder):
    tag_name = "positional"

    def encode(self, action: str, payload: dict[str, Any], session: Sym3Session) -> str:
        full = canonical_payload(action, payload)
        order = self.schema[action]
        vals = [_escape_token(full[k], session, session.content, use_refs=False) for k in order]
        return f"{self.tag}{_lex_cmd(self.lex, action)} {' '.join(vals)}"

    def decode(self, line: str, session: Sym3Session) -> ForgeMessage:
        body = _require_tag(line, self.tag)
        parts = _split_line(body)
        if not parts:
            raise ValueError("empty positional line")
        action = _cmd_from_lex(self.lex, parts[0].text)
        order = self.schema[action]
        vals = parts[1:]
        if len(vals) != len(order):
            raise ValueError(f"positional arity mismatch for {action}: expected {len(order)}, got {len(vals)}")
        payload: dict[str, Any] = {}
        for key, tok in zip(order, vals):
            payload[key] = _unescape_token(tok, session, session.content)
        return normalize_message(action, payload)


class OmitEncoder(Encoder):
    tag_name = "omit"

    def encode(self, action: str, payload: dict[str, Any], session: Sym3Session) -> str:
        sparse = session.omit_defaults(action, payload)
        order = [k for k in self.schema[action] if k in sparse]
        vals = [_escape_token(sparse[k], session, session.content, use_refs=False) for k in order]
        keys_blob = "|".join(order) + "|"
        return f"{self.tag}{_lex_cmd(self.lex, action)} {keys_blob} {' '.join(vals)}"

    def _decode_sparse(self, parts: list[WireToken], session: Sym3Session) -> ForgeMessage:
        if not parts:
            raise ValueError("empty omit line")
        action = _cmd_from_lex(self.lex, parts[0].text)
        allowed = set(self.schema[action])
        if len(parts) < 3 or not parts[1].text.endswith("|"):
            raise ValueError("omit line missing key list")
        keys = parts[1].text[:-1].split("|") if parts[1].text[:-1] else []
        vals = parts[2:]
        if len(parts) > 2 + len(vals):
            raise ValueError("extra tokens on omit line")
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate omit keys")
        for k in keys:
            if k not in allowed:
                raise ValueError(f"unknown omit key {k!r} for {action}")
        if len(keys) != len(vals):
            raise ValueError(f"omit arity mismatch for {action}")
        payload: dict[str, Any] = {}
        for key, tok in zip(keys, vals):
            payload[key] = _unescape_token(tok, session, session.content)
        return normalize_message(action, session.restore_defaults(action, payload))

    def decode(self, line: str, session: Sym3Session) -> ForgeMessage:
        body = _require_tag(line, self.tag)
        return self._decode_sparse(_split_line(body), session)


class RefsEncoder(Encoder):
    tag_name = "refs"

    def _refs_prefix(self, action: str) -> str:
        return self.lex.refs_cmd_lexeme(action)

    def _split_refs_line(self, line: str) -> tuple[str, str]:
        matches = [
            (action, fused)
            for action, fused in self.lex.refs_cmd.items()
            if line.startswith(fused)
        ]
        if not matches:
            raise ValueError("unknown refs command prefix")
        matches.sort(key=lambda item: len(item[1]), reverse=True)
        action, fused = matches[0]
        rest = line[len(fused) :]
        if rest and not rest.startswith(" "):
            raise ValueError("bad refs line spacing")
        return action, rest.lstrip()

    def encode(self, action: str, payload: dict[str, Any], session: Sym3Session) -> str:
        full = canonical_payload(action, payload)
        order = self.schema[action]
        vals = [_escape_token(full[k], session, session.content, use_refs=True) for k in order]
        return f"{self._refs_prefix(action)} {' '.join(vals)}"

    def _decode_positional(self, parts: list[WireToken], session: Sym3Session, action: str) -> ForgeMessage:
        if not parts:
            raise ValueError("empty refs line")
        order = self.schema[action]
        vals = parts
        if len(vals) != len(order):
            raise ValueError(f"refs arity mismatch for {action}")
        payload: dict[str, Any] = {}
        for key, tok in zip(order, vals):
            val = _unescape_token(tok, session, session.content)
            if (
                not tok.quoted
                and isinstance(val, str)
                and val in session.content.ref_to_digest
            ):
                val = session.content.resolve(val)
            payload[key] = val
        return normalize_message(action, payload)

    def decode(self, line: str, session: Sym3Session) -> ForgeMessage:
        action, rest = self._split_refs_line(line)
        parts = _split_line(rest) if rest else []
        return self._decode_positional(parts, session, action)


class DeltaEncoder(Encoder):
    tag_name = "delta"

    def encode(self, action: str, payload: dict[str, Any], session: Sym3Session) -> str:
        delta = session.delta_payload(action, payload)
        if delta and action == "task.transition" and session.task_id == canonical_payload(action, payload)["task_id"]:
            st_word = _lex_status(self.lex, delta["status"])
            return f"{self.tag}{_lex_cmd(self.lex, action)} t st={st_word}"
        omit = OmitEncoder(self.lex, self.schema)
        line = omit.encode(action, payload, session)
        return line.replace(omit.tag, self.tag, 1)

    def decode(self, line: str, session: Sym3Session) -> ForgeMessage:
        body = _require_tag(line, self.tag)
        parts = _split_line(body)
        if not parts:
            raise ValueError("empty delta line")
        action = _cmd_from_lex(self.lex, parts[0].text)
        if _is_delta_short_form(parts, self.lex):
            task_id = _unescape_token(parts[1], session, session.content)
            st_word = parts[2].text[3:]
            status = _status_from_lex(self.lex, st_word)
            return normalize_message(action, {"task_id": task_id, "status": status})
        omit = OmitEncoder(self.lex, self.schema)
        return omit._decode_sparse(parts, session)


class CombinedEncoder(Encoder):
    tag_name = "combined"

    def __init__(self, lexicon: Lexicon | None = None, schema: dict[str, list[str]] | None = None) -> None:
        super().__init__(lexicon, schema)
        self._delta = DeltaEncoder(self.lex, self.schema)
        self._refs = RefsEncoder(self.lex, self.schema)

    def encode(self, action: str, payload: dict[str, Any], session: Sym3Session) -> str:
        delta = session.delta_payload(action, payload)
        if (
            delta
            and action == "task.transition"
            and session.task_id == canonical_payload(action, payload)["task_id"]
        ):
            line = self._delta.encode(action, payload, session)
            return line.replace(self._delta.tag, self.tag, 1)
        sparse = session.omit_defaults(action, payload)
        order = [k for k in self.schema[action] if k in sparse]
        vals = [_escape_token(sparse[k], session, session.content, use_refs=True) for k in order]
        keys_blob = "|".join(order) + "|"
        return f"{self.tag}{_lex_cmd(self.lex, action)} {keys_blob} {' '.join(vals)}"

    def decode(self, line: str, session: Sym3Session) -> ForgeMessage:
        if not line.startswith(self.tag):
            raise ValueError(f"expected format tag {self.tag!r}")
        body = _require_tag(line, self.tag)
        parts = _split_line(body)
        if not parts:
            raise ValueError("empty combined line")
        if _is_delta_short_form(parts, self.lex):
            action = _cmd_from_lex(self.lex, parts[0].text)
            task_id = _unescape_token(parts[1], session, session.content)
            st_word = parts[2].text[3:]
            status = _status_from_lex(self.lex, st_word)
            return normalize_message(action, {"task_id": task_id, "status": status})
        action = _cmd_from_lex(self.lex, parts[0].text)
        if len(parts) > 2 and parts[1].text.endswith("|"):
            keys = parts[1].text[:-1].split("|") if parts[1].text[:-1] else []
            vals = parts[2:]
            allowed = set(self.schema[action])
            if len(keys) != len(set(keys)):
                raise ValueError("duplicate omit keys")
            for k in keys:
                if k not in allowed:
                    raise ValueError(f"unknown omit key {k!r} for {action}")
            if len(keys) != len(vals):
                raise ValueError(f"combined omit arity mismatch for {action}")
            payload: dict[str, Any] = {}
            for key, tok in zip(keys, vals):
                val = _unescape_token(tok, session, session.content)
                if (
                    not tok.quoted
                    and isinstance(val, str)
                    and val in session.content.ref_to_digest
                ):
                    val = session.content.resolve(val)
                payload[key] = val
            return normalize_message(action, session.restore_defaults(action, payload))
        return RefsEncoder(self.lex, self.schema)._decode_positional(parts[1:], session, action)


@dataclass
class AdaptiveResult:
    line: str
    encoder: str
    encode_cpu_ns: int


def _snapshot_content(session: Sym3Session) -> ContentStore:
    return copy.deepcopy(session.content)


def _restore_content(session: Sym3Session, snap: ContentStore) -> None:
    session.content = snap


class AdaptiveEncoder(Encoder):
    tag_name = "adaptive"

    def __init__(self, lexicon: Lexicon | None = None, schema: dict[str, list[str]] | None = None) -> None:
        super().__init__(lexicon, schema)
        self._choices = [
            DeltaEncoder(self.lex, self.schema),
            RefsEncoder(self.lex, self.schema),
            OmitEncoder(self.lex, self.schema),
            PositionalEncoder(self.lex, self.schema),
            CombinedEncoder(self.lex, self.schema),
        ]

    def encode(self, action: str, payload: dict[str, Any], session: Sym3Session) -> str:
        return self.encode_adaptive(action, payload, session).line

    def encode_adaptive(self, action: str, payload: dict[str, Any], session: Sym3Session) -> AdaptiveResult:
        from tokens import load_tokenizers, max_token_count

        specs = load_tokenizers()
        best_line = ""
        best_name = ""
        best_score = 10**9
        best_ns = 0
        best_enc: Encoder | None = None
        content_snap = _snapshot_content(session)
        for enc in self._choices:
            _restore_content(session, copy.deepcopy(content_snap))
            t0 = time.perf_counter_ns()
            line = enc.encode(action, payload, session)
            ns = time.perf_counter_ns() - t0
            score = max_token_count(line, specs) if specs else len(line)
            if score < best_score:
                best_score = score
                best_line = line
                best_name = enc.tag_name
                best_ns = ns
                best_enc = enc
        _restore_content(session, content_snap)
        assert best_enc is not None
        t0 = time.perf_counter_ns()
        final_line = best_enc.encode(action, payload, session)
        best_ns = time.perf_counter_ns() - t0
        return AdaptiveResult(final_line, best_name, best_ns)

    def decode(self, line: str, session: Sym3Session) -> ForgeMessage:
        snap = _snapshot_content(session)
        try:
            try:
                return RefsEncoder(self.lex, self.schema).decode(line, session)
            except ValueError:
                pass
            for name, tag in self.lex.format_tags.items():
                if name == "adaptive":
                    continue
                if line.startswith(tag):
                    return _encoder_by_name(name, self.lex, self.schema).decode(line, session)
            raise ValueError("cannot decode adaptive line: missing format tag")
        except Exception:
            _restore_content(session, snap)
            raise


def _encoder_by_name(name: str, lex: Lexicon, schema: dict[str, list[str]] | None = None) -> Encoder:
    return {
        "delta": DeltaEncoder(lex, schema),
        "refs": RefsEncoder(lex, schema),
        "omit": OmitEncoder(lex, schema),
        "positional": PositionalEncoder(lex, schema),
        "combined": CombinedEncoder(lex, schema),
    }[name]


DELTA_TAG = "delta"
REFS_TAG = "refs"
POSITIONAL_TAG = "positional"
OMIT_TAG = "omit"
COMBINED_TAG = "combined"
ADAPTIVE_TAG = "adaptive"


def all_encoders(
    lex: Lexicon | None = None,
    schema: dict[str, list[str]] | None = None,
) -> dict[str, Encoder]:
    lex = lex or load_lexicon()
    schema = schema or POSITIONAL_ORDER
    return {
        DELTA_TAG: DeltaEncoder(lex, schema),
        REFS_TAG: RefsEncoder(lex, schema),
        POSITIONAL_TAG: PositionalEncoder(lex, schema),
        OMIT_TAG: OmitEncoder(lex, schema),
        COMBINED_TAG: CombinedEncoder(lex, schema),
        ADAPTIVE_TAG: AdaptiveEncoder(lex, schema),
    }


def fresh_session(session_ids: dict[str, str] | None = None, hex_aliases: dict[str, str] | None = None) -> Sym3Session:
    """Session ids aligned with synbios/sym2p bench lifecycle fixtures."""
    from decoder_context import fixture_hex_aliases, fixture_session_ids

    session = Sym3Session()
    ids = session_ids if session_ids is not None else fixture_session_ids()
    session.project_id = ids.get("project_id", "")
    session.task_id = ids.get("task_id", "")
    session.agent_id = ids.get("agent_id", "")
    session.human_id = ids.get("human_id", "")
    session.artifact_id = ids.get("artifact_id", "")
    session.hex_aliases = dict(hex_aliases if hex_aliases is not None else fixture_hex_aliases())
    return session


def encode_transcript(encoder: Encoder, messages: list[ForgeMessage], session: Sym3Session | None = None) -> list[str]:
    session = session or fresh_session()
    lines: list[str] = []
    for action, payload in messages:
        lines.append(encoder.encode(action, payload, session))
        session.apply_message(action, payload)
    return lines


def decode_transcript(
    encoder: Encoder,
    lines: list[str],
    setup: "DecoderSetup | None" = None,
) -> list[ForgeMessage]:
    from decoder_context import session_from_setup

    if setup is not None:
        session = session_from_setup(setup)
    else:
        session = fresh_session()
    out: list[ForgeMessage] = []
    for line in lines:
        msg = encoder.decode(line, session)
        out.append(msg)
        session.apply_message(msg[0], msg[1])
    return out


from decoder_context import FORMAT_HEADER


def setup_prefix(lex: Lexicon | None = None) -> str:
    return FORMAT_HEADER
