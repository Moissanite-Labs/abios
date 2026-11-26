#!/usr/bin/env python3
"""Pin #39's refs wire features on a planner-chosen, POST-derived transcript.

abu-aska's M4 on #39: the earlier tests used one message, so the planner never
chose fused commands or hex aliases and mutations of those features survived.
These tests first assert that the planner *selected* fused refs commands and hex
aliases and that bare [a;b] wire lists were emitted, then check the round trip
through the POST handshake. Each of these mutations makes at least one test fail:
  - fused split: rest[1:] -> rest.lstrip() in RefsEncoder._split_refs_line
  - wire lists disabled (lists always sent as JSON)
  - hex aliasing disabled in the encoder (hex_alias_for -> None)
  - planner never fuses (plan_refs_wire fused loop -> (False,))
"""
import json
import os
import random
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "protean-abios"))

from canonical import canonical_payload, messages_equal  # noqa: E402
from decoder_context import (  # noqa: E402
    fixture_session_ids,
    infer_hex_candidates,
    parse_decoder_context,
    plan_refs_wire,
    setup_sizes,
)
from encoders import all_encoders, decode_transcript, encode_transcript  # noqa: E402
from post import parse_post_handshake, render_post_handshake  # noqa: E402
from schemas.synbios.fixtures import lifecycle_40, lifecycle_200  # noqa: E402

# Leading whitespace of several kinds in the first field of a fused line (B1).
ADVERSARIAL_TASK_IDS = ["\tx", " x", "\u00a0x", "\u2003x", "  x"]


def _transcript():
    msgs = list(lifecycle_200())
    for tid in ADVERSARIAL_TASK_IDS:
        msgs.append(("task.claim", canonical_payload("task.claim", {"task_id": tid})))
    return msgs


def _post_setup(messages, lines):
    sizes = setup_sizes(messages, lines)
    _, ctx = parse_post_handshake(render_post_handshake(sizes["minimal_text"]))
    return parse_decoder_context(ctx)


class RefsWireFeatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.messages = _transcript()
        enc = all_encoders()["refs"]
        cls.plan = plan_refs_wire(cls.messages, fixture_session_ids(),
                                  infer_hex_candidates(cls.messages), enc.lex)
        cls.lines = encode_transcript(enc, cls.messages)
        cls.setup = _post_setup(cls.messages, cls.lines)

    def test_planner_selects_fused_and_hex(self):
        self.assertTrue(self.plan.fused_refs_cmd, "planner did not choose fused refs commands")
        self.assertTrue(self.plan.hex_aliases, "planner did not choose hex aliases")
        self.assertTrue(self.setup.fused_refs_cmd)
        self.assertEqual(self.setup.hex_aliases, self.plan.hex_aliases)

    def test_lines_use_fused_lexemes_hex_aliases_and_wire_lists(self):
        enc = all_encoders(self.setup.lexicon, self.setup.schema)["refs"]
        fused = set(enc.lex.refs_cmd.values())
        self.assertTrue(all(any(l.startswith(f + " ") or l == f for f in fused) for l in self.lines))
        alias_tokens = set(self.plan.hex_aliases)
        tokens = {t for l in self.lines for t in l.split(" ")}
        self.assertTrue(alias_tokens & tokens, "no hex alias token on the wire")
        bare = re.compile(r'(?:^| )\[[^\]"]+;[^\]"]+\](?: |$)')
        self.assertTrue(any(bare.search(l) for l in self.lines), "no bare [a;b] wire list on the wire")

    def test_post_context_round_trip_with_leading_whitespace(self):
        enc = all_encoders(self.setup.lexicon, self.setup.schema)["refs"]
        back = decode_transcript(enc, self.lines, setup=self.setup)
        self.assertEqual(len(back), len(self.messages))
        for i, (m, b) in enumerate(zip(self.messages, back)):
            self.assertTrue(messages_equal(m, b), f"line {i}: {self.lines[i]!r}")
        for tid, b in zip(ADVERSARIAL_TASK_IDS, back[-len(ADVERSARIAL_TASK_IDS):]):
            self.assertEqual(b[1]["task_id"], tid)

    def test_adaptive_round_trip_through_post_context(self):
        enc = all_encoders()["adaptive"]
        lines = encode_transcript(enc, self.messages)
        setup = _post_setup(self.messages, lines)
        back = decode_transcript(all_encoders(setup.lexicon, setup.schema)["adaptive"], lines, setup=setup)
        self.assertTrue(all(messages_equal(m, b) for m, b in zip(self.messages, back)))

    def test_seeded_multi_message_fuzz_through_post_context(self):
        # String-only perturbations (no brackets, no blank items): the list-codec classes
        # are covered by the wire-list suite; this pins fused/hex/planner paths.
        rng = random.Random(0x39A4)
        alphabet = ["\t", " ", "\u00a0", "\u2003", ";", "\\", "#", "|", "é", "-", "_", ":", "/", ","]
        for trial in range(6):
            msgs = [(a, json.loads(json.dumps(p))) for a, p in lifecycle_40()]
            for _ in range(12):
                i = rng.randrange(len(msgs))
                action, payload = msgs[i]
                keys = [k for k, v in payload.items() if isinstance(v, str) and k != "status"]
                if not keys:
                    continue
                k = rng.choice(keys)
                pos = rng.choice(["pre", "post"])
                ch = rng.choice(alphabet)
                payload[k] = ch + payload[k] if pos == "pre" else payload[k] + ch
                msgs[i] = (action, canonical_payload(action, payload))
            for name in ("refs", "adaptive"):
                enc = all_encoders()[name]
                lines = encode_transcript(enc, msgs)
                setup = _post_setup(msgs, lines)
                back = decode_transcript(all_encoders(setup.lexicon, setup.schema)[name], lines, setup=setup)
                for j, (m, b) in enumerate(zip(msgs, back)):
                    self.assertTrue(messages_equal(m, b), f"trial {trial} {name} line {j}: {lines[j]!r}")


if __name__ == "__main__":
    unittest.main()
