"""Fused refs commands are used only when the POST's wire: block declares them."""
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/protean-abios"))

from canonical import SCHEMA_DEFAULTS, canonical_payload
from decoder_context import (fixture_session_ids, full_positional_schema,
                             parse_decoder_context, render_decoder_context)
from encoders import all_encoders, decode_transcript, fresh_session
from lexicon import LEXICON_PATH
from post import parse_post_handshake, render_post_handshake

MESSAGES = [
    ("project.create", {"name": "two", "description": "d"}),
    ("task.create", {"project_id": "p1", "title": "one", "criteria": ["a", "b"]}),
    ("task.claim", {"task_id": "t1"}),
]
NO_WIRE = object()


def setup_from_post(wire):
    lexicon_payload = json.loads(LEXICON_PATH.read_text())
    assert lexicon_payload.get("refs_cmd"), "lexicon must carry refs_cmd for these tests"
    context = render_decoder_context(
        lexicon_payload=lexicon_payload, schema=full_positional_schema(),
        session_ids=fixture_session_ids(), schema_defaults=SCHEMA_DEFAULTS,
        wire=None if wire is NO_WIRE else wire,
    )
    if wire is NO_WIRE:
        assert "\nwire:\n" not in context
    _, received = parse_post_handshake(render_post_handshake(context))
    return parse_decoder_context(received)


def encode(name, fused):
    encoder = all_encoders()[name]
    session = fresh_session(fixture_session_ids(), {}, fused_refs_cmd=fused)
    lines = []
    for action, payload in MESSAGES:
        lines.append(encoder.encode(action, payload, session))
        session.apply_message(action, payload)
    return lines


def decode(name, setup, lines):
    return decode_transcript(all_encoders(setup.lexicon, setup.schema)[name], lines, setup=setup)


EXPECTED = [(a, canonical_payload(a, p)) for a, p in MESSAGES]


class FusedMustBeDeclaredTests(unittest.TestCase):
    def test_missing_wire_block_with_refs_cmd_decodes_unfused(self):
        setup = setup_from_post(NO_WIRE)
        self.assertFalse(setup.fused_refs_cmd)
        unfused = encode("refs", False)
        self.assertTrue(all(line.startswith("E") for line in unfused))
        self.assertEqual(decode("refs", setup, unfused), EXPECTED)
        fused = encode("refs", True)
        self.assertNotEqual(fused, unfused)
        with self.assertRaises(ValueError):
            decode("refs", setup, fused)

    def test_wire_block_without_fused_key_decodes_unfused(self):
        setup = setup_from_post({"list_sep": ";"})
        self.assertFalse(setup.fused_refs_cmd)
        self.assertEqual(decode("refs", setup, encode("refs", False)), EXPECTED)

    def test_declared_unfused(self):
        setup = setup_from_post({"fused_refs_cmd": False, "list_sep": ";"})
        self.assertFalse(setup.fused_refs_cmd)
        self.assertEqual(decode("refs", setup, encode("refs", False)), EXPECTED)

    def test_declared_fused_still_works(self):
        setup = setup_from_post({"fused_refs_cmd": True, "list_sep": ";"})
        self.assertTrue(setup.fused_refs_cmd)
        for name in ("refs", "adaptive"):
            with self.subTest(encoder=name):
                self.assertEqual(decode(name, setup, encode(name, True)), EXPECTED)
        with self.assertRaises(ValueError):
            decode("refs", setup, encode("refs", False))


if __name__ == "__main__":
    unittest.main()
