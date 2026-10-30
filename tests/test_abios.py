import json
import os
import subprocess
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
        try:
            specs = load_tokenizers()
        except RuntimeError:
            self.skipTest("lexicon tokenizers unavailable")
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

    def _assert_round_trip_payload(self, action, payload, encoder_name="refs"):
        enc = all_encoders()[encoder_name]
        msg = (action, canonical_payload(action, payload))
        lines = encode_transcript(enc, [msg])
        back = decode_transcript(enc, lines)
        self.assertTrue(messages_equal(msg, back[0]), f"{encoder_name}: {msg} vs {back[0]}")

    def test_adversarial_round_trip_all_encoders(self):
        long_desc = "x" * 60
        cases = [
            ("project.create", {"name": "demo", "description": "", "repository": ""}),
            ("project.create", {"name": "#1", "description": long_desc, "repository": ""}),
            ("project.create", {"name": "20", "description": "digit name", "repository": ""}),
            ("project.create", {"name": "-", "description": "dash name", "repository": ""}),
            ("project.create", {"name": "p", "description": "letter name", "repository": ""}),
            ("task.create", {
                "project_id": "a1" * 16,
                "title": "brace",
                "description": "[not json",
                "criteria": [],
                "scope": [],
                "priority": "normal",
                "dependencies": [],
            }),
            ("task.create", {
                "project_id": "a1" * 16,
                "title": "pipe|suffix",
                "description": "ok",
                "criteria": [],
                "scope": [],
                "priority": "normal",
                "dependencies": [],
            }),
            ("task.create", {
                "project_id": "a1" * 16,
                "title": "newline",
                "description": "line1\nline2",
                "criteria": [],
                "scope": [],
                "priority": "normal",
                "dependencies": [],
            }),
        ]
        for encoder_name in all_encoders():
            for action, payload in cases:
                with self.subTest(encoder=encoder_name, action=action):
                    self._assert_round_trip_payload(action, payload, encoder_name)

    def test_unknown_content_ref_fails_closed(self):
        from encoders import fresh_session

        enc = all_encoders()["refs"]
        session = fresh_session()
        cmd = enc.lex.word("cmd", "project.create").strip()
        line = f"{enc.tag}{cmd} demo \"\" \"\" #9"
        with self.assertRaises(ValueError):
            enc.decode(line, session)

    def test_delta_other_task_not_short_form(self):
        from encoders import DeltaEncoder, encode_transcript, fresh_session

        messages = lifecycle_11()
        enc = DeltaEncoder()
        other_task = "f" * 32
        session = fresh_session()
        for action, payload in messages:
            session.apply_message(action, payload)
        line = enc.encode("task.transition", {"task_id": other_task, "status": "running"}, session)
        self.assertNotIn(" t st=", line)
        self.assertIn(other_task, line)
        back = decode_transcript(enc, encode_transcript(enc, messages + [("task.transition", {"task_id": other_task, "status": "running"})]))
        self.assertEqual(back[-1][1]["task_id"], other_task)

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
                    setup = parse_decoder_context(sizes["minimal_text"])
                    enc_min = all_encoders(setup.lexicon, setup.schema)[enc_name]
                    back = decode_transcript(enc_min, lines, setup=setup)
                    self.assertEqual(len(back), len(messages))
                    for exp, got in zip(messages, back):
                        self.assertTrue(messages_equal(exp, got))

    def test_s12_decode_from_post_context_bare_session(self):
        messages = lifecycle_11()
        enc = all_encoders()["combined"]
        lines = encode_transcript(enc, messages)
        sizes = setup_sizes(messages, lines)
        blob = render_post_handshake(sizes["minimal_text"])
        _, ctx = parse_post_handshake(blob)
        setup = parse_decoder_context(ctx)
        back = decode_transcript(all_encoders(setup.lexicon, setup.schema)["combined"], lines, setup=setup)
        self.assertEqual(len(back), len(messages))


class AbiosBenchSmokeTests(unittest.TestCase):
    def test_minimal_setup_larger_than_header_only(self):
        try:
            specs = load_tokenizers()
        except RuntimeError:
            self.skipTest("lexicon tokenizers unavailable")
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
        import tempfile
        from pathlib import Path

        try:
            load_tokenizers()
        except RuntimeError:
            self.skipTest("lexicon tokenizers unavailable")
        before = LEXICON_PATH.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "lexicon.json"
            self.assertEqual(regen_lexicon(out), 0)
            generated = out.read_text(encoding="utf-8")
        json.loads(generated)
        self.assertEqual(before, generated)


class AbiosImportRootTests(unittest.TestCase):
    def test_every_schemas_module_imports_from_one_root(self):
        # -I drops PYTHONPATH and the cwd, so scripts/protean-abios is the only root.
        code = (
            "import importlib, pathlib, sys\n"
            "root = pathlib.Path(sys.argv[1])\n"
            "sys.path.insert(0, str(root))\n"
            "for path in sorted((root / 'schemas').rglob('*.py')):\n"
            "    parts = path.relative_to(root).with_suffix('').parts\n"
            "    if parts[-1] == '__init__':\n"
            "        parts = parts[:-1]\n"
            "    importlib.import_module('.'.join(parts))\n"
            "    print('.'.join(parts))\n"
        )
        result = subprocess.run([sys.executable, "-I", "-c", code, os.path.normpath(ABIOS)],
                                capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("schemas.synbios.sym2p.adapter", result.stdout.split())


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
        setup = parse_decoder_context(ctx)
        back = decode_transcript(all_encoders(setup.lexicon, setup.schema)["refs"], lines, setup=setup)
        self.assertEqual(len(back), len(messages))

    def test_post_header_only_rejected(self):
        with self.assertRaises(ValueError):
            parse_post_handshake("POST ok abios/3 deadbeef\nabios/3\n")

    def test_post_sym3_profile_requires_matching_ack(self):
        messages = lifecycle_11()
        enc = all_encoders()["refs"]
        lines = encode_transcript(enc, messages)
        sizes = setup_sizes(messages, lines)
        legacy = sizes["minimal_text"].replace("abios/3", "sym3/1", 1)
        blob = render_post_handshake(legacy)
        setup = parse_decoder_context(legacy)
        back = decode_transcript(all_encoders(setup.lexicon, setup.schema)["refs"], lines, setup=setup)
        self.assertEqual(len(back), len(messages))
        self.assertTrue(blob.startswith("POST ok sym3/1 "))

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
