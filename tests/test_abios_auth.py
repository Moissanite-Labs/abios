"""Sealed sessions (SPEC-ABIOS-3.md section 8.2): known answers, round trips, and every rejection."""
import hashlib
import hmac
import os
import struct
import sys
import threading
import unittest

ABIOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts", "protean-abios")
sys.path.insert(0, os.path.normpath(ABIOS))

from auth import (  # noqa: E402
    INITIATOR,
    RESPONDER,
    AuthError,
    SealParams,
    SidRegistry,
    _check_dec,
    open_post,
    open_sealed_post,
    render_sealed_post,
    seal_transcript,
    unseal_transcript,
)
from canonical import messages_equal  # noqa: E402
from decoder_context import parse_decoder_context, setup_sizes  # noqa: E402
from encoders import all_encoders, decode_transcript, encode_transcript  # noqa: E402
from post import parse_post_handshake, render_post_handshake  # noqa: E402
from schemas.synbios.fixtures import lifecycle_11, lifecycle_40  # noqa: E402

KEY = bytes(range(32))
KEYRING = {"kat": KEY, "k1": KEY}

# Known-answer vector, also printed in SPEC-ABIOS-3.md section 8.2.
KAT_CONTEXT = (
    "abios/3\n\nlexicon:\n"
    '{"concepts":{"cmd":{"task.transition":"st"},"status":{"done":"dn"}},"format_tags":{"refs":"E"}}\n'
    "schema:\n"
    '{"task.transition":["status","task_id"]}\n'
)
KAT_POST = (
    "POST ok abios/3 70a7903f8829ad8a auth=hs256 kid=kat sid=12345678901234567890 tag=64 seal=2 "
    "mac=02111108734560368521\n"
    + KAT_CONTEXT
)
KAT_LINES = ["Est dn t", "Est wk t", "Est dn t"]
KAT_WIRE_I = ["Est dn t", "Est wk t", "~11827668228127165077", "Est dn t", "~!01027126885348767035"]
KAT_WIRE_R = ["Est dn t", "~01897601097019698901"]


def _spec_mac(key, *parts):
    """Section 8.2 key schedule, written from the spec text independently of auth.py."""
    data = b"".join(struct.pack(">I", len(p)) + p for p in parts)
    return hmac.new(key, data, hashlib.sha256).digest()


def _dec(raw):
    return str(int.from_bytes(raw, "big")).zfill(len(str((1 << (8 * len(raw))) - 1)))


def _minimal(messages, encoder="refs"):
    lines = encode_transcript(all_encoders()[encoder], messages)
    return lines, setup_sizes(messages, lines)["minimal_text"]


KAT_SID = "12345678901234567890"
# Key-schedule intermediates for the vector (hex), also in the spec.
KAT_POST_HASH = "c7b18a165500745cde20a3d413a9e03a89ef23c7c68fd3d82d85db56913f5ab4"
KAT_S = "ccee11daffb7977979ea45ae083442e71f1ed72335b2fede483ff81ee114e8fd"
KAT_K_I = "8a16a824037d2f2137c132799f3bd1e7b928308d67b411e9189fa5efe5d56638"
KAT_C0 = "a7a2f59f404b94ccae65b7e16e96d79f8299d8c6a37323dacbb365735676e4dd"


def _kat_session(seal_every=2, sid=KAT_SID):
    return render_sealed_post(KAT_CONTEXT, key=KEY, seen=SidRegistry(), kid="kat", sid=sid, seal_every=seal_every)


class SealedKnownAnswerTests(unittest.TestCase):
    def test_render_matches_vector(self):
        post, session = _kat_session()
        self.assertEqual(post, KAT_POST)
        sender = session.sender(INITIATOR)
        wire = []
        for line in KAT_LINES:
            wire += sender.push(line)
        wire += sender.close()
        self.assertEqual(wire, KAT_WIRE_I)
        self.assertEqual(seal_transcript(session.sender(RESPONDER), ["Est dn t"]), KAT_WIRE_R)

    def test_vector_matches_spec_formulas(self):
        signed = KAT_POST.split(" mac=")[0] + "\n" + KAT_CONTEXT
        post_hash = hashlib.sha256(signed.encode("utf-8")).digest()
        self.assertEqual(post_hash.hex(), KAT_POST_HASH)
        s = _spec_mac(KEY, b"abios/3 seal hs256", b"kat", KAT_SID.encode("ascii"), post_hash)
        self.assertEqual(s.hex(), KAT_S)
        self.assertEqual(_dec(_spec_mac(s, b"post")[:8]), "02111108734560368521")
        k_i = _spec_mac(s, b"dir", b"i")
        self.assertEqual(k_i.hex(), KAT_K_I)
        c = _spec_mac(k_i, b"chain")
        self.assertEqual(c.hex(), KAT_C0)
        for line in KAT_LINES[:2]:
            c = _spec_mac(k_i, c, line.encode("utf-8"))
        self.assertEqual("~" + _dec(_spec_mac(k_i, b"seal", c)[:8]), KAT_WIRE_I[2])
        c = _spec_mac(k_i, c, KAT_LINES[2].encode("utf-8"))
        self.assertEqual("~!" + _dec(_spec_mac(k_i, b"close", c)[:8]), KAT_WIRE_I[4])

    def test_responder_opens_vector(self):
        context, session = open_sealed_post(KAT_POST, keyring=KEYRING, seen=SidRegistry())
        self.assertEqual(context, KAT_CONTEXT)
        got = unseal_transcript(session.receiver(INITIATOR), KAT_WIRE_I, require_close=True)
        self.assertEqual(got, KAT_LINES)
        self.assertEqual(unseal_transcript(session.receiver(RESPONDER), KAT_WIRE_R), ["Est dn t"])

    def test_transport_normalization_is_ascii_only(self):
        # CRLF and SP/HT/CR/LF padding normalize away; the context returned is the one the MAC binds.
        padded = "\r\n " + KAT_POST.replace("\n", "\r\n") + "\t\r\n\r\n"
        context, _session = open_sealed_post(padded, keyring=KEYRING, seen=SidRegistry())
        self.assertEqual(context, KAT_CONTEXT)
        # Other Unicode whitespace is content, so it changes the digest.
        with self.assertRaisesRegex(AuthError, "digest mismatch"):
            open_sealed_post(KAT_POST.rstrip("\n") + "\u3000\n", keyring=KEYRING, seen=SidRegistry())


class SealedRoundTripTests(unittest.TestCase):
    def test_every_encoder_decodes_through_a_sealed_session(self):
        messages = lifecycle_40()
        for name in all_encoders():
            for seal_every in (1, 7):
                with self.subTest(encoder=name, seal_every=seal_every):
                    lines, minimal = _minimal(messages, name)
                    post, s_init = render_sealed_post(
                        minimal, key=KEY, seen=SidRegistry(), kid="k1", seal_every=seal_every
                    )
                    context, s_resp = open_sealed_post(
                        post, keyring=KEYRING, seen=SidRegistry(), minimal_context_text=minimal
                    )
                    wire = seal_transcript(s_init.sender(INITIATOR), lines, close=True)
                    got = unseal_transcript(s_resp.receiver(INITIATOR), wire, require_close=True)
                    lex, _schema = parse_decoder_context(context)
                    back = decode_transcript(all_encoders(lex)[name], got)
                    self.assertEqual(len(back), len(messages))
                    for exp, dec in zip(messages, back):
                        self.assertTrue(messages_equal(exp, dec))

    def test_tag_sizes(self):
        lines, minimal = _minimal(lifecycle_11())
        for bits, chars in ((64, 20), (96, 29), (128, 39)):
            with self.subTest(bits=bits):
                post, s_init = render_sealed_post(minimal, key=KEY, seen=SidRegistry(), kid="k1", tag_bits=bits)
                self.assertIn(f" tag={bits} ", post.split("\n", 1)[0])
                _ctx, s_resp = open_sealed_post(post, keyring=KEYRING, seen=SidRegistry(), min_tag_bits=bits)
                wire = seal_transcript(s_init.sender(INITIATOR), lines)
                self.assertEqual(len(wire[1]), 1 + chars)
                self.assertEqual(unseal_transcript(s_resp.receiver(INITIATOR), wire), lines)

    def test_close_seal_covers_the_last_full_batch(self):
        _post, session = _kat_session(seal_every=1)
        wire = seal_transcript(session.sender(INITIATOR), KAT_LINES, close=True)
        self.assertEqual(len(wire), 2 * len(KAT_LINES))
        self.assertTrue(wire[-1].startswith("~!"))
        rx = session.receiver(INITIATOR)
        self.assertEqual(unseal_transcript(rx, wire, require_close=True), KAT_LINES)
        sender = _kat_session(seal_every=1)[1].sender(INITIATOR)
        sender.push("Est dn t", last=True)
        with self.assertRaisesRegex(AuthError, "batch already full"):
            sender.push("Est wk t")

    def test_batch_lines_release_only_at_the_seal(self):
        _post, session = _kat_session()
        rx = session.receiver(INITIATOR)
        self.assertEqual(rx.feed(KAT_WIRE_I[0]), [])
        self.assertEqual(rx.feed(KAT_WIRE_I[1]), [])
        self.assertEqual(rx.pending, 2)
        self.assertEqual(rx.feed(KAT_WIRE_I[2]), KAT_LINES[:2])
        self.assertEqual(rx.feed(KAT_WIRE_I[3]), [])
        self.assertEqual(rx.feed(KAT_WIRE_I[4]), KAT_LINES[2:])
        self.assertTrue(rx.closed)


class SealedRejectionTests(unittest.TestCase):
    """One case per section 8.2 receiver check; each asserts the check that fires."""

    def _rx(self, direction=INITIATOR):
        # A session issues one receiver per direction, so each case opens its own.
        _ctx, session = open_sealed_post(KAT_POST, keyring=KEYRING, seen=SidRegistry())
        return session.receiver(direction)

    def _reject(self, wire, pattern, *, direction=INITIATOR, require_close=False):
        rx = self._rx(direction)
        with self.assertRaisesRegex(AuthError, pattern):
            unseal_transcript(rx, wire, require_close=require_close)
        return rx

    def test_altered_line(self):
        self._reject(["Est dn t", "Est dn t", KAT_WIRE_I[2]], "seal tag mismatch")

    def test_reordered_lines(self):
        self._reject([KAT_WIRE_I[1], KAT_WIRE_I[0]] + KAT_WIRE_I[2:], "seal tag mismatch")

    def test_dropped_line(self):
        self._reject(KAT_WIRE_I[:1] + KAT_WIRE_I[2:], "seal tag mismatch")

    def test_injected_line(self):
        self._reject(KAT_WIRE_I[:3] + ["Est wk t"] + KAT_WIRE_I[3:], "close seal tag mismatch")

    def test_replayed_batch(self):
        self._reject(KAT_WIRE_I[:3] + KAT_WIRE_I[:3], "seal tag mismatch")

    def test_reflected_direction(self):
        self._reject(KAT_WIRE_R, "seal tag mismatch", direction=INITIATOR)
        self._reject(KAT_WIRE_I, "seal tag mismatch", direction=RESPONDER)

    def test_altered_seal_tag(self):
        self._reject(KAT_WIRE_I[:2] + ["~11827668228127165078"], "seal tag mismatch")

    def test_altered_close_tag(self):
        self._reject(KAT_WIRE_I[:4] + ["~!01027126885348767036"], "close seal tag mismatch")

    def test_seal_with_nothing_to_cover(self):
        # The duplicate is a valid tag for the chain state, so only check 3 can refuse it.
        self._reject(KAT_WIRE_I[:3] + [KAT_WIRE_I[2]], "no lines to cover")

    def test_overdue_seal(self):
        rx = self._rx()
        rx.feed(KAT_WIRE_I[0])
        rx.feed(KAT_WIRE_I[1])
        with self.assertRaisesRegex(AuthError, "without a seal"):
            rx.feed("Est dn t")

    def test_line_after_close(self):
        self._reject(KAT_WIRE_I + [KAT_WIRE_I[4]], "after close")

    def test_trailing_unsealed_line(self):
        self._reject(KAT_WIRE_I[:3] + ["Est dn t"], "not covered by a seal")

    def test_truncation_caught_by_require_close(self):
        self._reject(KAT_WIRE_I[:3], "without a close seal", require_close=True)

    def test_malformed_wire_lines_fail_closed(self):
        # Wrong-width or non-ASCII tags, lone surrogates, and non-text all end the session.
        cases = (
            ("~\u00e9", "decimal digits"),
            ("~!\u0661", "decimal digits"),
            ("~1182766822812716507", "decimal digits"),
            ("Est \udcff t", "UTF-8"),
            (b"Est dn t", "malformed wire line"),
        )
        for bad, pattern in cases:
            with self.subTest(line=repr(bad)):
                rx = self._rx()
                rx.feed(KAT_WIRE_I[0])
                with self.assertRaisesRegex(AuthError, pattern):
                    rx.feed(bad)
                self.assertEqual(rx.pending, 0)
                with self.assertRaisesRegex(AuthError, "already failed"):
                    rx.feed(KAT_WIRE_I[1])

    def test_one_chain_per_role_and_direction(self):
        # A fresh receiver would restart the chain, which is resynchronization.
        _ctx, session = open_sealed_post(KAT_POST, keyring=KEYRING, seen=SidRegistry())
        session.receiver(INITIATOR)
        session.sender(RESPONDER)
        with self.assertRaisesRegex(AuthError, "already issued"):
            session.receiver(INITIATOR)
        with self.assertRaisesRegex(AuthError, "already issued"):
            session.sender(RESPONDER)

    def test_receiver_stays_failed(self):
        rx = self._rx()
        rx.feed("Est wk t")
        with self.assertRaises(AuthError):
            rx.feed(KAT_WIRE_I[2])
        with self.assertRaisesRegex(AuthError, "already failed"):
            rx.feed(KAT_WIRE_I[0])

    def test_other_session_tags_do_not_verify(self):
        _post, other = _kat_session(sid="12345678901234567891")
        self._reject(seal_transcript(other.sender(INITIATOR), KAT_LINES[:2]), "seal tag mismatch")


class SealedPostRejectionTests(unittest.TestCase):
    def _open(self, blob, keyring=KEYRING, seen=None, **kwargs):
        return open_sealed_post(blob, keyring=keyring, seen=seen or SidRegistry(), **kwargs)

    def test_replayed_post(self):
        seen = SidRegistry()
        self._open(KAT_POST, seen=seen)
        with self.assertRaisesRegex(AuthError, "replay"):
            self._open(KAT_POST, seen=seen)

    def test_own_post_reflected_back_is_a_replay(self):
        # A peer that both starts and accepts sessions under one pair key shares one registry.
        seen = SidRegistry()
        post, _session = render_sealed_post(KAT_CONTEXT, key=KEY, seen=seen, kid="kat", sid=KAT_SID, seal_every=2)
        with self.assertRaisesRegex(AuthError, "replay"):
            self._open(post, seen=seen)

    def test_concurrent_claims_accept_one(self):
        seen, wins = SidRegistry(), []

        def worker():
            try:
                seen.claim("kat", KAT_SID)
                wins.append(1)
            except AuthError:
                pass

        threads = [threading.Thread(target=worker) for _ in range(16)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(wins), 1)

    def test_failed_post_does_not_burn_the_sid(self):
        seen = SidRegistry()
        with self.assertRaisesRegex(AuthError, "mac mismatch"):
            self._open(KAT_POST.replace("mac=02111108734560368521", "mac=02111108734560368522"), seen=seen)
        self._open(KAT_POST, seen=seen)

    def test_wrong_key(self):
        with self.assertRaisesRegex(AuthError, "mac mismatch"):
            self._open(KAT_POST, keyring={"kat": bytes(32)})

    def test_unknown_kid(self):
        with self.assertRaisesRegex(AuthError, "unknown key id"):
            self._open(KAT_POST, keyring={"other": KEY})

    def test_wrong_profile(self):
        with self.assertRaisesRegex(AuthError, "profile"):
            self._open(KAT_POST.replace("POST ok abios/3", "POST ok abios/4", 1))

    def test_digest_field_alone_altered(self):
        with self.assertRaisesRegex(AuthError, "digest mismatch"):
            self._open(KAT_POST.replace("70a7903f8829ad8a", "70a7903f8829ad8b"))

    def test_tampered_context(self):
        # Re-digest the altered body so only the MAC can catch it.
        from post import context_digest

        body = KAT_CONTEXT.replace('"dn"', '"wk"')
        ack = KAT_POST.split("\n", 1)[0].replace("70a7903f8829ad8a", context_digest(body))
        with self.assertRaisesRegex(AuthError, "mac mismatch"):
            self._open(ack + "\n" + body)

    def test_tampered_parameters(self):
        for old, new in (("seal=2", "seal=3"), ("sid=" + KAT_SID, "sid=12345678901234567891")):
            with self.subTest(change=new):
                with self.assertRaisesRegex(AuthError, "mac mismatch"):
                    self._open(KAT_POST.replace(old, new))
        # A wider tag also changes the expected mac width.
        with self.assertRaisesRegex(AuthError, "decimal digits"):
            self._open(KAT_POST.replace("tag=64", "tag=96"))

    def test_malformed_parameters(self):
        bad = (
            ("auth=hs256", "auth=ed25519"),
            ("seal=2", "seal=02"),
            ("seal=2", "seal=0"),
            ("seal=2", "seal=\u00b2"),
            ("seal=2", "seal=" + "9" * 5000),
            ("tag=64", "tag=32"),
            ("tag=64", "tag=6\u2074"),
            (" kid=kat sid=" + KAT_SID, " sid=" + KAT_SID + " kid=kat"),
            ("sid=" + KAT_SID, "sid=99999999999999999999"),
            ("sid=" + KAT_SID, "sid=1234567890123456789"),
            ("mac=02111108734560368521", "mac=021111087345603685210"),
            ("mac=02111108734560368521", "mac=0211110873456036852x"),
            ("mac=02111108734560368521", "mac=0211110873456036852\u0661"),
            ("kid=kat", "kid=k at"),
            (" auth=hs256", "  auth=hs256"),
            (" mac=02111108734560368521", ""),
            (" mac=02111108734560368521", " mac=02111108734560368521 x=1"),
        )
        for old, new in bad:
            with self.subTest(change=new[:40]):
                with self.assertRaises(AuthError):
                    self._open(KAT_POST.replace(old, new))

    def test_dec_range(self):
        with self.assertRaisesRegex(AuthError, "below 2\\^64"):
            _check_dec(str(1 << 64).zfill(20), 64, "sid")
        _check_dec(str((1 << 64) - 1), 64, "sid")

    def test_bare_cr_and_lone_surrogate_bodies(self):
        with self.assertRaisesRegex(AuthError, "bare CR"):
            render_sealed_post(KAT_CONTEXT.replace("schema:", "sch\r\rema:"), key=KEY, seen=SidRegistry(), kid="kat")
        with self.assertRaisesRegex(AuthError, "bare CR|digest mismatch"):
            self._open(KAT_POST.replace("schema:", "sch\r\r\nema:"))
        with self.assertRaisesRegex(AuthError, "UTF-8"):
            self._open(KAT_POST.replace("schema:", "sch\udcffema:"))

    def test_format_tag_must_not_begin_with_seal_prefix(self):
        post, _session = render_sealed_post(
            KAT_CONTEXT.replace('"refs":"E"', '"refs":"~E"'), key=KEY, seen=SidRegistry(), kid="kat"
        )
        with self.assertRaisesRegex(AuthError, "seal prefix"):
            self._open(post)

    def test_registry_with_atomic_external_store(self):
        store = set()

        def add_if_absent(kid, sid):
            if (kid, sid) in store:
                return False
            store.add((kid, sid))
            return True

        seen = SidRegistry(add_if_absent=add_if_absent)
        self._open(KAT_POST, seen=seen)
        with self.assertRaisesRegex(AuthError, "replay"):
            self._open(KAT_POST, seen=seen)
        with self.assertRaises(ValueError):
            SidRegistry(set(), add_if_absent=add_if_absent)

    def test_minimum_tag_policy(self):
        with self.assertRaisesRegex(AuthError, "minimum"):
            self._open(KAT_POST, min_tag_bits=128)

    def test_mac_valid_post_with_unparseable_body(self):
        post, _session = render_sealed_post(
            "abios/3\n\nlexicon:\n[1]\nschema:\n{}", key=KEY, seen=SidRegistry(), kid="kat"
        )
        with self.assertRaisesRegex(AuthError, "does not parse"):
            self._open(post)

    def test_plain_parser_refuses_sealed_post(self):
        with self.assertRaisesRegex(ValueError, "sealed-session parameters"):
            parse_post_handshake(KAT_POST)
        # 8.1(a): nothing may follow the digest, not even whitespace.
        plain = render_post_handshake(KAT_CONTEXT)
        ack, body = plain.split("\n", 1)
        for tail in (" ", "\t", "\u3000"):
            with self.subTest(tail=repr(tail)):
                with self.assertRaises(ValueError):
                    parse_post_handshake(ack + tail + "\n" + body)

    def test_policy_refuses_plain_post(self):
        plain = render_post_handshake(KAT_CONTEXT)
        with self.assertRaisesRegex(AuthError, "requires a sealed session"):
            open_post(plain, require_seal=True, keyring=KEYRING, seen=SidRegistry())
        context, session = open_post(plain, require_seal=False)
        self.assertEqual(context, KAT_CONTEXT)
        self.assertIsNone(session)
        context, session = open_post(KAT_POST, require_seal=True, keyring=KEYRING, seen=SidRegistry())
        self.assertIsNotNone(session)

    def test_policy_entry_point_runs_8_1_checks(self):
        _lines, minimal = _minimal(lifecycle_11())
        with self.assertRaisesRegex(AuthError, "minimal context"):
            open_post(KAT_POST, require_seal=True, keyring=KEYRING, seen=SidRegistry(), minimal_context_text=minimal)
        with self.assertRaisesRegex(AuthError, "plain POST rejected"):
            open_post(render_post_handshake(KAT_CONTEXT), require_seal=False, minimal_context_text=minimal)
        with self.assertRaisesRegex(AuthError, "plain POST rejected"):
            open_post(render_post_handshake("abios/3\n\nlexicon:\n[1]\nschema:\n{}"), require_seal=False)

    def test_minimal_context_mismatch(self):
        _lines, minimal = _minimal(lifecycle_11())
        post, _session = render_sealed_post(minimal, key=KEY, seen=SidRegistry(), kid="k1")
        with self.assertRaisesRegex(AuthError, "minimal context"):
            open_sealed_post(post, keyring=KEYRING, seen=SidRegistry(), minimal_context_text=KAT_CONTEXT)

    def test_parameter_validation(self):
        for kwargs in (
            {"key": bytes(15), "kid": "k1"},
            {"key": KEY, "kid": ""},
            {"key": KEY, "kid": "k" * 33},
            {"key": KEY, "kid": "k1", "sid": "short"},
            {"key": KEY, "kid": "k1", "tag_bits": 256},
            {"key": KEY, "kid": "k1", "seal_every": 0},
            {"key": KEY, "kid": "k1", "seal_every": 1025},
        ):
            with self.subTest(kwargs={k: v for k, v in kwargs.items() if k != "key"}):
                with self.assertRaises(AuthError):
                    render_sealed_post(KAT_CONTEXT, seen=SidRegistry(), **kwargs)

    def test_sender_refuses_seal_prefixed_or_multiline_lines(self):
        _post, session = render_sealed_post(KAT_CONTEXT, key=KEY, seen=SidRegistry(), kid="k1")
        sender = session.sender(INITIATOR)
        for bad in ("~abc", "Est dn t\nEst wk t", "", "Est \udcff t"):
            with self.subTest(line=repr(bad)):
                with self.assertRaises(AuthError):
                    sender.push(bad)

    def test_params_reject_bad_values(self):
        with self.assertRaises(AuthError):
            SealParams(kid="k1", sid=KAT_SID, tag_bits=64, seal_every=-1)


if __name__ == "__main__":
    unittest.main()
