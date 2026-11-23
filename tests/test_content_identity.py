"""Content refs preserve JSON types independently of tokenizer availability."""
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/protean-abios"))

from canonical import SCHEMA_DEFAULTS, canonical_payload
from content_store import ContentStore, content_digest, serialized_byte_length
from decoder_context import (fixture_session_ids, full_positional_schema,
                             parse_decoder_context, render_decoder_context)
from encoders import all_encoders, decode_transcript, encode_transcript
from lexicon import LEXICON_PATH
from post import parse_post_handshake, render_post_handshake


class ContentIdentityTests(unittest.TestCase):
    def test_json_text_and_values_have_distinct_refs(self):
        for value in (["x" * 60], {"value": "x" * 60}):
            text = json.dumps(value, sort_keys=True, separators=(",", ":"))
            self.assertNotEqual(content_digest(value), content_digest(text))
            for values in ((value, text), (text, value)):
                store = ContentStore()
                for item in values:
                    store.observe_inline(item)
                for index, item in enumerate(values, 1):
                    resolved = store.resolve(f"#{index}")
                    self.assertIs(type(resolved), type(item))
                    self.assertEqual(resolved, item)
                    self.assertEqual(store.ref_if_published(item), f"#{index}")

    def test_domain_prefix_does_not_change_threshold(self):
        store = ContentStore()
        for size in (47, 48):
            value = "x" * size
            self.assertEqual(serialized_byte_length(value), size)
            store.observe_inline(value)
            self.assertEqual(content_digest(value) in store.digest_to_ref, size == 48)

    def test_collision_transcripts_decode_from_post(self):
        context = render_decoder_context(
            lexicon_payload=json.loads(LEXICON_PATH.read_text()),
            schema=full_positional_schema(), session_ids=fixture_session_ids(),
            schema_defaults=SCHEMA_DEFAULTS,
        )
        _, received_context = parse_post_handshake(render_post_handshake(context))
        setup = parse_decoder_context(received_context)
        for value in (["x" * 60], ["é " * 30]):
            text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
            structured = ("task.create", {"project_id": "p1", "title": "one", "criteria": value})
            literal = ("project.create", {"name": "two", "description": text})
            for first in ((structured, literal), (literal, structured)):
                messages = list(first) * 3
                for name in ("refs", "combined", "delta", "omit", "positional"):
                    with self.subTest(value=value, first=first[0][0], encoder=name):
                        lines = encode_transcript(all_encoders()[name], messages)
                        decoded = decode_transcript(
                            all_encoders(setup.lexicon, setup.schema)[name], lines, setup=setup)
                        expected = [(a, canonical_payload(a, p)) for a, p in messages]
                        self.assertEqual(decoded, expected)
                        for (_, payload), (_, actual) in zip(expected, decoded):
                            for key in payload:
                                self.assertIs(type(actual[key]), type(payload[key]))
                        if name in ("refs", "combined"):
                            self.assertTrue(any("#1" in line for line in lines))
                            self.assertTrue(any("#2" in line for line in lines))


if __name__ == "__main__":
    unittest.main()
