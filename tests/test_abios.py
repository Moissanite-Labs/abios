import json
import os
import sys
import unittest

ABIOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts", "protean-abios")
sys.path.insert(0, os.path.normpath(ABIOS))

from canonical import canonical_payload, messages_equal, normalize_message  # noqa: E402
from decoder_context import FORMAT_HEADER, parse_decoder_context, render_decoder_context, setup_sizes  # noqa: E402
from encoders import all_encoders, decode_transcript, encode_transcript  # noqa: E402
from generate_lexicon import main as regen_lexicon  # noqa: E402
from lexicon import LEXICON_PATH, load_lexicon  # noqa: E402
from post import parse_post_handshake, render_post_handshake, verify_post_or_raise  # noqa: E402
from schemas.synbios.fixtures import lifecycle_11, lifecycle_40, lifecycle_200  # noqa: E402
from tokens import is_single_token, load_tokenizers  # noqa: E402


class AbiosLexiconTests(unittest.TestCase):
    def test_lexicon_file_exists(self):
        self.assertTrue(LEXICON_PATH.is_file())
        lex = load_lexicon()
        self.assertIn("cmd", lex.raw)
        self.assertIn("project.create", lex.raw["cmd"])

    def test_format_tags_single_token(self):
        specs = load_tokenizers()
        if not specs:
            self.skipTest("tiktoken not installed")
        primary = specs[0]
        lex = load_lexicon()
        for name, tag in lex.format_tags.items():
            self.assertTrue(is_single_token(tag, [primary]), f"tag {name}={tag!r}")


class AbiosRoundTripTests(unittest.TestCase):
    def _assert_round_trip(self, messages, encoder_name):
        enc = all_encoders()[encoder_name]
        lines = encode_transcript(enc, messages)
        back = decode_transcript(enc, lines)
        self.assertEqual(len(back), len(messages))
        for exp, got in zip(messages, back):
            self.assertTrue(messages_equal(exp, got), f"{encoder_name}: {exp} vs {got}")

    def test_all_encoders_round_trip_11(self):
        messages = lifecycle_11()
        for name in all_encoders():
            with self.subTest(encoder=name, transcript="lifecycle_11"):
                self._assert_round_trip(messages, name)

    def test_all_encoders_round_trip_40(self):
        messages = lifecycle_40()
        for name in all_encoders():
            with self.subTest(encoder=name, transcript="lifecycle_40"):
                self._assert_round_trip(messages, name)

    def test_all_encoders_round_trip_200(self):
        messages = lifecycle_200()
        for name in all_encoders():
            with self.subTest(encoder=name, transcript="lifecycle_200"):
                self._assert_round_trip(messages, name)


class AbiosMinimalContextTests(unittest.TestCase):
    LIFECYCLES = (
        ("lifecycle_11", lifecycle_11),
        ("lifecycle_40", lifecycle_40),
        ("lifecycle_200", lifecycle_200),
    )

    def test_minimal_context_decodes_every_encoder(self):
        full_lex = load_lexicon()
        for tname, fn in self.LIFECYCLES:
            messages = fn()
            for enc_name in all_encoders():
                with self.subTest(transcript=tname, encoder=enc_name):
                    enc_full = all_encoders(full_lex)[enc_name]
                    lines = encode_transcript(enc_full, messages)
                    sizes = setup_sizes(messages, lines, full_lex)
                    lex_min, _schema = parse_decoder_context(sizes["minimal_text"])
                    enc_min = all_encoders(lex_min)[enc_name]
                    back = decode_transcript(enc_min, lines)
                    self.assertEqual(len(back), len(messages))
                    for exp, got in zip(messages, back):
                        self.assertTrue(messages_equal(exp, got))


class AbiosBenchSmokeTests(unittest.TestCase):
    def test_minimal_setup_larger_than_header_only(self):
        specs = load_tokenizers()
        if not specs:
            self.skipTest("tiktoken not installed")
        messages = lifecycle_11()
        enc = all_encoders()["combined"]
        lines = encode_transcript(enc, messages)
        sizes = setup_sizes(messages, lines)
        self.assertGreater(sizes["minimal"], sizes["header_only"])
        self.assertGreater(sizes["full"], sizes["minimal"])

    def test_lifecycle_200_length(self):
        self.assertEqual(len(lifecycle_200()), 200)


class AbiosRegenLexiconTests(unittest.TestCase):
    def test_regenerate_lexicon(self):
        specs = load_tokenizers()
        if not specs:
            self.skipTest("tiktoken not installed")
        before = LEXICON_PATH.read_text(encoding="utf-8")
        self.assertEqual(regen_lexicon(), 0)
        after = LEXICON_PATH.read_text(encoding="utf-8")
        json.loads(after)
        self.assertEqual(before, after)


class AbiosPostTests(unittest.TestCase):
    def test_post_round_trip(self):
        messages = lifecycle_11()
        enc = all_encoders()["refs"]
        lines = encode_transcript(enc, messages)
        sizes = setup_sizes(messages, lines)
        minimal = sizes["minimal_text"]
        blob = render_post_handshake(minimal)
        ack, ctx = parse_post_handshake(blob)
        self.assertTrue(ack.startswith("POST ok abios/3 "))
        verify_post_or_raise(blob, minimal)
        lex, _schema = parse_decoder_context(ctx)
        back = decode_transcript(all_encoders(lex)["refs"], lines)
        self.assertEqual(len(back), len(messages))

    def test_legacy_sym3_header_still_parses(self):
        messages = lifecycle_11()
        enc = all_encoders()["refs"]
        lines = encode_transcript(enc, messages)
        sizes = setup_sizes(messages, lines)
        legacy = sizes["minimal_text"].replace("abios/3", "sym3/1", 1)
        lex, schema = parse_decoder_context(legacy)
        self.assertIn("project.create", schema)
        back = decode_transcript(all_encoders(lex)["refs"], lines)
        self.assertEqual(len(back), len(messages))

    def test_post_mismatch_raises(self):
        messages = lifecycle_11()
        enc = all_encoders()["refs"]
        lines = encode_transcript(enc, messages)
        sizes = setup_sizes(messages, lines)
        blob = render_post_handshake(sizes["minimal_text"])
        bad = blob.replace("abios/3", "abios/9", 1)
        with self.assertRaises(ValueError):
            parse_post_handshake(bad)


if __name__ == "__main__":
    unittest.main()
