"""Sealed sessions (SPEC-ABIOS-3.md section 8.2): known answers, round trips, and every rejection."""
import hashlib
import hmac
import os
import struct
import sys
import unittest

ABIOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts", "protean-abios")
sys.path.insert(0, os.path.normpath(ABIOS))

from auth import (  # noqa: E402
    INITIATOR,
    RESPONDER,
    AuthError,
    SealParams,
    SidRegistry,
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
    "POST ok abios/3 70a7903f8829ad8a auth=hs256 kid=kat sid=12345678901234567890 tag=64 seal=2 mac=02111108734560368521\n"
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


class SealedKnownAnswerTests(unittest.TestCase):
    def test_render_matches_vector(self):
        post, session = render_sealed_post(KAT_CONTEXT, key=KEY, kid="kat", sid="12345678901234567890", seal_every=2)
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
        s = _spec_mac(KEY, b"abios/3 seal hs256", b"kat", b"12345678901234567890", post_hash)
        self.assertEqual(_dec(_spec_mac(s, b"post")[:8]), "02111108734560368521")
        k_i = _spec_mac(s, b"dir", b"i")
        c = _spec_mac(k_i, b"chain")
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


class SealedRoundTripTests(unittest.TestCase):
    def test_every_encoder_decodes_through_a_sealed_session(self):
        messages = lifecycle_40()
        for name in all_encoders():
            for seal_every in (1, 7):
                with self.subTest(encoder=name, seal_every=seal_every):
                    lines, minimal = _minimal(messages, name)
                    post, s_init = render_sealed_post(minimal, key=KEY, kid="k1", seal_every=seal_every)
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
                post, s_init = render_sealed_post(minimal, key=KEY, kid="k1", tag_bits=bits)
                self.assertIn(f" tag={bits} ", post.split("\n", 1)[0])
                _ctx, s_resp = open_sealed_post(post, keyring=KEYRING, seen=SidRegistry())
                wire = seal_transcript(s_init.sender(INITIATOR), lines)
                self.assertEqual(len(wire[1]), 1 + chars)
                self.assertEqual(unseal_transcript(s_resp.receiver(INITIATOR), wire), lines)

    def test_close_seal_covers_the_last_full_batch(self):
        _post, session = render_sealed_post(KAT_CONTEXT, key=KEY, kid="kat", sid="12345678901234567890", seal_every=1)
        wire = seal_transcript(session.sender(INITIATOR), KAT_LINES, close=True)
        self.assertEqual(len(wire), 2 * len(KAT_LINES))
        self.assertTrue(wire[-1].startswith("~!"))
        rx = session.receiver(INITIATOR)
        self.assertEqual(unseal_transcript(rx, wire, require_close=True), KAT_LINES)
        sender = session.sender(INITIATOR)
        sender.push("Est dn t", last=True)
        with self.assertRaises(AuthError):
            sender.push("Est wk t")

    def test_batch_lines_release_only_at_the_seal(self):
        _post, session = render_sealed_post(KAT_CONTEXT, key=KEY, kid="kat", sid="12345678901234567890", seal_every=2)
        rx = session.receiver(INITIATOR)
        self.assertEqual(rx.feed(KAT_WIRE_I[0]), [])
        self.assertEqual(rx.feed(KAT_WIRE_I[1]), [])
        self.assertEqual(rx.pending, 2)
        self.assertEqual(rx.feed(KAT_WIRE_I[2]), KAT_LINES[:2])
        self.assertEqual(rx.feed(KAT_WIRE_I[3]), [])
        self.assertEqual(rx.feed(KAT_WIRE_I[4]), KAT_LINES[2:])
        self.assertTrue(rx.closed)


class SealedRejectionTests(unittest.TestCase):
    def setUp(self):
        _ctx, self.session = open_sealed_post(KAT_POST, keyring=KEYRING, seen=SidRegistry())

    def _reject(self, wire, *, direction=INITIATOR, require_close=False):
        with self.assertRaises(AuthError):
            unseal_transcript(self.session.receiver(direction), wire, require_close=require_close)

    def test_altered_line(self):
        self._reject(["Est dn t", "Est dn t", KAT_WIRE_I[2]])

    def test_reordered_lines(self):
        self._reject([KAT_WIRE_I[1], KAT_WIRE_I[0]] + KAT_WIRE_I[2:])

    def test_dropped_line(self):
        self._reject(KAT_WIRE_I[:1] + KAT_WIRE_I[2:])

    def test_injected_line(self):
        self._reject(KAT_WIRE_I[:1] + ["Est wk t"] + KAT_WIRE_I[1:])

    def test_replayed_batch(self):
        self._reject(KAT_WIRE_I[:3] + KAT_WIRE_I[:3])

    def test_reflected_direction(self):
        self._reject(KAT_WIRE_R, direction=INITIATOR)
        self._reject(KAT_WIRE_I, direction=RESPONDER)

    def test_altered_tag(self):
        self._reject(KAT_WIRE_I[:2] + ["~11827668228127165078"])

    def test_seal_with_nothing_to_cover(self):
        self._reject([KAT_WIRE_I[2]])

    def test_overdue_seal(self):
        self._reject(KAT_WIRE_I[:2] + ["Est dn t"])

    def test_line_after_close(self):
        self._reject(KAT_WIRE_I + ["Est dn t", "~x"])

    def test_trailing_unsealed_line(self):
        self._reject(KAT_WIRE_I[:3] + ["Est dn t"])

    def test_truncation_caught_by_require_close(self):
        self._reject(KAT_WIRE_I[:3], require_close=True)

    def test_receiver_stays_failed(self):
        rx = self.session.receiver(INITIATOR)
        rx.feed("Est wk t")
        with self.assertRaises(AuthError):
            rx.feed(KAT_WIRE_I[2])
        with self.assertRaises(AuthError):
            rx.feed(KAT_WIRE_I[0])

    def test_other_session_tags_do_not_verify(self):
        _post, other = render_sealed_post(KAT_CONTEXT, key=KEY, kid="kat", sid="12345678901234567891", seal_every=2)
        sender = other.sender(INITIATOR)
        self._reject(seal_transcript(sender, KAT_LINES[:2]))


class SealedPostRejectionTests(unittest.TestCase):
    def _open(self, blob, keyring=KEYRING, seen=None):
        return open_sealed_post(blob, keyring=keyring, seen=seen or SidRegistry())

    def test_replayed_post(self):
        seen = SidRegistry()
        self._open(KAT_POST, seen=seen)
        with self.assertRaises(AuthError):
            self._open(KAT_POST, seen=seen)

    def test_failed_post_does_not_burn_the_sid(self):
        seen = SidRegistry()
        with self.assertRaisesRegex(AuthError, "mac mismatch"):
            self._open(KAT_POST.replace("mac=02111108734560368521", "mac=02111108734560368522"), seen=seen)
        self._open(KAT_POST, seen=seen)

    def test_wrong_key(self):
        with self.assertRaisesRegex(AuthError, "mac mismatch"):
            self._open(KAT_POST, keyring={"kat": bytes(32)})

    def test_unknown_kid(self):
        with self.assertRaises(AuthError):
            self._open(KAT_POST, keyring={"other": KEY})

    def test_tampered_context(self):
        # Re-digest the altered body so only the MAC can catch it.
        from post import context_digest

        body = KAT_CONTEXT.replace('"dn"', '"wk"')
        ack = KAT_POST.split("\n", 1)[0].replace("70a7903f8829ad8a", context_digest(body))
        with self.assertRaisesRegex(AuthError, "mac mismatch"):
            self._open(ack + "\n" + body)

    def test_tampered_parameters(self):
        for old, new in (("seal=2", "seal=3"), ("tag=64", "tag=96"), ("sid=12345678901234567890", "sid=12345678901234567891")):
            with self.subTest(change=new):
                # A wider tag also changes the expected mac length.
                with self.assertRaisesRegex(AuthError, "mac mismatch|decimal digits"):
                    self._open(KAT_POST.replace(old, new))

    def test_malformed_parameters(self):
        bad = (
            ("auth=hs256", "auth=ed25519"),
            ("seal=2", "seal=02"),
            ("seal=2", "seal=0"),
            ("tag=64", "tag=32"),
            (" kid=kat sid=12345678901234567890", " sid=12345678901234567890 kid=kat"),
            ("sid=12345678901234567890", "sid=99999999999999999999"),
            ("sid=12345678901234567890", "sid=1234567890123456789"),
            ("mac=02111108734560368521", "mac=021111087345603685210"),
            ("mac=02111108734560368521", "mac=0211110873456036852x"),
            ("mac=02111108734560368521", "mac=0211110873456036852\u0661"),
            ("kid=kat", "kid=k at"),
        )
        for old, new in bad:
            with self.subTest(change=new):
                with self.assertRaises(AuthError):
                    self._open(KAT_POST.replace(old, new))

    def test_plain_parser_refuses_sealed_post(self):
        with self.assertRaises(ValueError):
            parse_post_handshake(KAT_POST)

    def test_policy_refuses_plain_post(self):
        plain = render_post_handshake(KAT_CONTEXT)
        with self.assertRaises(AuthError):
            open_post(plain, require_seal=True, keyring=KEYRING, seen=SidRegistry())
        context, session = open_post(plain, require_seal=False)
        self.assertEqual(context, KAT_CONTEXT)
        self.assertIsNone(session)
        context, session = open_post(KAT_POST, require_seal=True, keyring=KEYRING, seen=SidRegistry())
        self.assertIsNotNone(session)

    def test_minimal_context_mismatch(self):
        _lines, minimal = _minimal(lifecycle_11())
        post, _session = render_sealed_post(minimal, key=KEY, kid="k1")
        with self.assertRaises(AuthError):
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
                    render_sealed_post(KAT_CONTEXT, **kwargs)

    def test_sender_refuses_seal_prefixed_or_multiline_lines(self):
        _post, session = render_sealed_post(KAT_CONTEXT, key=KEY, kid="k1")
        sender = session.sender(INITIATOR)
        for bad in ("~abc", "Est dn t\nEst wk t", ""):
            with self.subTest(line=bad):
                with self.assertRaises(AuthError):
                    sender.push(bad)

    def test_params_reject_bad_values(self):
        with self.assertRaises(AuthError):
            SealParams(kid="k1", sid="12345678901234567890", tag_bits=64, seal_every=-1)


if __name__ == "__main__":
    unittest.main()
