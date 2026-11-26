"""Wire-list codec tests: 22 adversarial vectors, #39 bugs end to end, strict J: rejections.

Design (qalam, 2026-11-26): bare [a;b] string lists decoded by #39's decode_string_list
(unchanged); J: is a fallback forced by an encode-time round-trip check; no S[ form.
"""
from __future__ import annotations

import json
import os
import sys
import unittest
from typing import Any

_ABIOS_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts", "protean-abios")
)
if _ABIOS_DIR not in sys.path:
    sys.path.insert(0, _ABIOS_DIR)

from canonical import canonical_payload, coerce_wire_types, messages_equal  # noqa: E402
from encoders import (  # noqa: E402
    CombinedEncoder,
    DeltaEncoder,
    OmitEncoder,
    PositionalEncoder,
    RefsEncoder,
    _split_line,
    fresh_session,
)
import wire_lists as wl  # noqa: E402


def _exact_typed_equal(a: Any, b: Any) -> bool:
    if type(a) is not type(b):
        return False
    if type(a) is list:
        return len(a) == len(b) and all(_exact_typed_equal(x, y) for x, y in zip(a, b))
    if type(a) is dict:
        if set(a.keys()) != set(b.keys()):
            return False
        return all(_exact_typed_equal(a[k], b[k]) for k in a)
    return a == b


ADVERSARIAL_22_VECTORS: tuple[tuple[str, list[Any], str], ...] = (
    ("V01_empty", [], "[]"),
    ("V02_safe_paths", ["src/auth.py", "tests/test_auth.py"], "["),
    ("V03_single_safe", ["alpha"], "["),
    ("V04_pr39_bug1_single_space", [" "], "J:"),
    ("V05_pr39_bug1_spaces_and_tab", ["   ", "\t"], "["),
    ("V06_single_empty_str", [""], "["),
    ("V07_double_empty_str", ["", ""], "["),
    ("V08_pr39_bug2_int_list", [1, 2], "J:"),
    ("V09_pr39_bug2_bool_null_list", [True, False, None], "J:"),
    ("V10_mixed_scalar_types", [0, 1, False, True, "0", "1", -7], "J:"),
    ("V11_pr39_bug3_bracket_space", ["see [1] now"], "J:"),
    ("V12_pr39_bug3_multi_brackets", ["a] b", "c [d] e"], "J:"),
    ("V13_percent_escape_roundtrip", ["%20", "%25", "%2520", "%%20", "%25 0"], "["),
    ("V14_semicolon_and_backslash", ["a;b", "c\\d", "trail\\"], "J:"),
    ("V15_quotes_and_newlines", ['quote"here', "line1\nline2", "cr\rhere"], "J:"),
    ("V16_reserved_session_handles", ["-", "p", "t", "a", "h", "f", "v", "g"], "J:"),
    ("V17_reserved_prefixes_digits", ["http://example.com", "https://x.y/z", "42", "{k:v}"], "J:"),
    ("V18_wire_marker_self_quote", ["S[a;b]", "J:[1,2]", "[]", "\\e"], "J:"),
    ("V19_nested_lists_and_dicts", [["nested", [1, 2]], {"k": "v with space", "n": None}], "J:"),
    ("V20_unicode_arabic_cjk_spaces", ["العربية", "日本語 テスト", "é é é"], "["),
    ("V21_comma_braces_unicode_ws", ["a,b", "x{y}", "u\u00a0v", "line\u2028sep"], "["),
    ("V22_long_list_content_ref_size", ["item_alpha"] * 25, "["),
)


class WireListsLosslessR5Tests(unittest.TestCase):
    def test_22_adversarial_vectors_single_token_typed_bijection(self) -> None:
        self.assertEqual(len(ADVERSARIAL_22_VECTORS), 22)
        for label, payload, expected_prefix in ADVERSARIAL_22_VECTORS:
            with self.subTest(vector=label):
                tok = wl.encode_wire_list(payload)
                self.assertIs(type(tok), str)
                self.assertTrue(tok.startswith(expected_prefix), f"{label}: got {tok!r}")
                if tok.startswith("J:"):
                    self.assertFalse(any(ch.isspace() for ch in tok), f"{label}: whitespace in {tok!r}")
                    self.assertFalse(tok.startswith("[") and tok != "[]")
                parts = _split_line(f"X {tok} Y")
                self.assertEqual([p.text for p in parts], ["X", tok, "Y"], f"{label}: {tok!r} did not tokenize as one")
                decoded = wl.decode_wire_list(tok)
                self.assertTrue(
                    _exact_typed_equal(decoded, payload),
                    f"{label}: expected {payload!r}, got {decoded!r}",
                )

    def test_custom_separator_roundtrip(self) -> None:
        tok = wl.encode_wire_list(["alpha", "beta"], sep="|")
        self.assertEqual(tok, "[alpha|beta]")
        self.assertEqual(wl.decode_wire_list(tok, sep="|"), ["alpha", "beta"])
        # Item containing the custom sep falls back to J:
        tok_fb = wl.encode_wire_list(["alpha|beta", "gamma"], sep="|")
        self.assertTrue(tok_fb.startswith("J:"))
        self.assertEqual(wl.decode_wire_list(tok_fb, sep="|"), ["alpha|beta", "gamma"])

    def test_pr39_three_bugs_closed_e2e_all_encoders(self) -> None:
        encoders = (
            ("refs", RefsEncoder()),
            ("positional", PositionalEncoder()),
            ("omit", OmitEncoder()),
            ("delta", DeltaEncoder()),
            ("combined", CombinedEncoder()),
        )
        bug_cases = (
            ("bug1_single_space", [" "]),
            ("bug1_tab", ["\t"]),
            ("bug2_int_list", [1, 2]),
            ("bug2_bool_null", [True, False, None]),
            ("bug3_see_bracket_space", ["see [1] now"]),
            ("bug3_close_bracket_space", ["foo] bar"]),
        )
        for enc_name, enc in encoders:
            for bug_name, criteria in bug_cases:
                with self.subTest(encoder=enc_name, bug=bug_name):
                    s_enc = fresh_session()
                    s_dec = fresh_session()
                    payload = canonical_payload(
                        "task.create",
                        {
                            "project_id": "a1" * 16,
                            "title": "t",
                            "description": "d",
                            "criteria": criteria,
                            "scope": [],
                            "priority": "normal",
                            "dependencies": [],
                        },
                    )
                    line = enc.encode("task.create", payload, s_enc)
                    action, decoded = enc.decode(line, s_dec)
                    self.assertEqual(action, "task.create")
                    self.assertTrue(
                        _exact_typed_equal(decoded["criteria"], criteria),
                        f"{enc_name}/{bug_name}: expected {criteria!r}, got {decoded['criteria']!r}",
                    )

    def test_literal_string_fields_do_not_collide_with_bare_or_j_wire_lists(self) -> None:
        encoders = (
            ("refs", RefsEncoder()),
            ("positional", PositionalEncoder()),
            ("omit", OmitEncoder()),
            ("delta", DeltaEncoder()),
            ("combined", CombinedEncoder()),
        )
        for enc_name, enc in encoders:
            for tricky_str in ("S[a;b]", "J:[1,2]", "S[]", "J:", "[]"):
                with self.subTest(encoder=enc_name, value=tricky_str):
                    s_enc = fresh_session()
                    s_dec = fresh_session()
                    msg = (
                        "project.create",
                        canonical_payload(
                            "project.create",
                            {"name": tricky_str, "description": tricky_str, "repository": ""},
                        ),
                    )
                    line = enc.encode(msg[0], msg[1], s_enc)
                    got = enc.decode(line, s_dec)
                    self.assertTrue(messages_equal(msg, got))
                    self.assertIs(type(got[1]["name"]), str)
                    self.assertEqual(got[1]["name"], tricky_str)

    def test_content_ref_interning_with_j_carrier_and_dict_quoting(self) -> None:
        enc = RefsEncoder()
        s_enc = fresh_session()
        s_dec = fresh_session()
        long_list = ["see [1] now with unicode é " * 3]
        msg = (
            "task.create",
            canonical_payload(
                "task.create",
                {
                    "project_id": "a1" * 16,
                    "title": "ref test",
                    "description": "",
                    "criteria": long_list,
                    "scope": long_list,
                    "priority": "normal",
                    "dependencies": [],
                },
            ),
        )
        line1 = enc.encode(msg[0], msg[1], s_enc)
        s_enc.apply_message(msg[0], msg[1])
        line2 = enc.encode(msg[0], msg[1], s_enc)
        self.assertIn("#1", line2)
        got1 = enc.decode(line1, s_dec)
        s_dec.apply_message(got1[0], got1[1])
        got2 = enc.decode(line2, s_dec)
        self.assertTrue(messages_equal(msg, got1))
        self.assertTrue(messages_equal(msg, got2))

    def test_legacy_brackets_and_coerce_wire_types(self) -> None:
        # Legacy [a;b] and [1,2] tokens decode cleanly through RefsEncoder
        enc = RefsEncoder()
        s_dec = fresh_session()
        fused = enc._refs_prefix("task.create", s_dec)
        legacy_line = f'{fused} [alpha;beta] [] d normal p [1,2] "t"'
        action, decoded = enc.decode(legacy_line, s_dec)
        self.assertEqual(action, "task.create")
        self.assertEqual(decoded["criteria"], ["alpha", "beta"])
        # #39's decoder (unchanged) reads bare [1,2] as the one string "1,2"; int lists travel as J:[1,2].
        self.assertEqual(decoded["scope"], ["1,2"])

        # coerce_wire_types: [], J:..., legacy [...] (#39 path unchanged); S[ is no longer a form
        c1 = coerce_wire_types("task.create", {"criteria": "[]", "scope": "[x;y]", "dependencies": 'J:["%20"]'})
        self.assertEqual(c1["criteria"], [])
        self.assertEqual(c1["scope"], ["x", "y"])
        self.assertEqual(c1["dependencies"], [" "])
        c2 = coerce_wire_types("task.create", {"criteria": "J:[1,2]", "scope": "[1,2]", "dependencies": "S[x;y]"})
        self.assertTrue(_exact_typed_equal(c2["criteria"], [1, 2]))
        self.assertEqual(c2["scope"], ["1,2"])
        self.assertEqual(c2["dependencies"], "S[x;y]")
        # A malformed J: value in a list-typed field raises; it is never passed through as a string.
        for bad in ("J:bad", "J:[NaN]", 'J:["alpha"]', "J:", "J:[1,%202]"):
            with self.subTest(coerce_bad=bad):
                with self.assertRaises(ValueError):
                    coerce_wire_types("task.create", {"criteria": bad})

    def test_fail_closed_encode_and_decode_wire_list_guards(self) -> None:
        # Non-list inputs to encode_wire_list
        for bad_items in ("abc", ("a",), {"a": 1}, None, 42, True):
            with self.assertRaises(ValueError):
                wl.encode_wire_list(bad_items)  # type: ignore[arg-type]

        # Invalid separators
        for bad_sep in ("", 7, None):
            with self.assertRaises(ValueError):
                wl.encode_wire_list(["a"], sep=bad_sep)  # type: ignore[arg-type]

        # Invalid decode_wire_list tokens
        bad_tokens: tuple[Any, ...] = (
            None,
            123,
            [],
            "",
            "S[a b]",
            "S[a\tb]",
            "J: [1,2]",
            "J:[1,2]\n",
            "S[]",
            "S[a;;b]",
            "S[1;2]",
            "S[p]",
            "S[http://example.com]",
            "S[a,b]",
            'S[a"b]',
            "S[a[b]",
            "S[a]b]",
            "S[a\\b]",
            "S[a{b]",
            "S[a}b]",
            "J:",
            "S[a;b]",
            "S[alpha]",
            "J:%",
            "J:%2",
            "J:%2G",
            'J:["%2G"]',
            'J:["%00"]',
            'J:["\x7f"]',
            'J:["\u00e9"]',
            "J:\x01",
            "J:notjson",
            'J:{"a":1}',
            "J:42",
            'J:"hello"',
            "X[a;b]",
            "[unclosed",
            "S[a;b",
        )
        for bad_tok in bad_tokens:
            with self.subTest(bad_tok=bad_tok):
                with self.assertRaises(ValueError):
                    wl.decode_wire_list(bad_tok)

    def test_legacy_decode_string_list_is_pr39_unchanged(self) -> None:
        """(d) Bare [a;b] decoding is #39's decode_string_list at 3e251f0b, byte for byte."""
        import inspect
        import subprocess

        root = os.path.dirname(_ABIOS_DIR.rstrip(os.sep))
        root = os.path.dirname(root)
        try:
            src39 = subprocess.run(
                ["git", "show", "3e251f0b:scripts/protean-abios/wire_lists.py"],
                cwd=root, capture_output=True, text=True, check=True,
            ).stdout
        except (OSError, subprocess.CalledProcessError):
            self.skipTest("3e251f0b not available in this checkout")
        for name in ("_escape_item", "_unescape_item", "_split_items", "_item_needs_json_fallback",
                     "can_encode_string_list", "encode_string_list", "decode_string_list"):
            with self.subTest(function=name):
                self.assertIn(inspect.getsource(getattr(wl, name)), src39)

    def test_legacy_behaviour_pins(self) -> None:
        # #39 behaviour kept as is; the encoder routes the lossy cases to J: instead.
        self.assertEqual(wl.decode_string_list("[ ]"), [])
        self.assertEqual(wl.decode_string_list("[1,2]"), ["1,2"])
        self.assertEqual(wl.decode_string_list("[null]"), ["null"])
        self.assertEqual(wl.decode_string_list("[a\\;b;c\\\\d]"), ["a;b", "c\\d"])
        self.assertEqual(wl.decode_string_list("[\\e]"), [""])
        self.assertIsNone(wl.decode_string_list("S[a;b]"))
        self.assertIsNone(wl.decode_string_list('J:["%20"]'))
        self.assertEqual(wl.encode_wire_list([" "]), 'J:["%20"]')
        self.assertEqual(wl.encode_wire_list([1, 2]), "J:[1,2]")
        self.assertEqual(wl.encode_wire_list(["1,2"]), "[1,2]")
        self.assertEqual(wl.encode_wire_list(["null"]), "[null]")

    def test_unquoted_s_bracket_and_quoted_j_strings_stay_strings(self) -> None:
        """(d) With S[ dropped, unquoted S[... tokens are plain strings, as on #39."""
        enc = RefsEncoder()
        for value in ("S[x]", "S[", "S[x]y"):
            with self.subTest(value=value):
                s_enc, s_dec = fresh_session(), fresh_session()
                msg = ("project.create", canonical_payload(
                    "project.create", {"name": value, "description": "d", "repository": ""}))
                line = enc.encode(msg[0], msg[1], s_enc)
                self.assertIn(" " + value, line)  # emitted unquoted, exactly as #39 did
                got = enc.decode(line, s_dec)
                self.assertIs(type(got[1]["name"]), str)
                self.assertEqual(got[1]["name"], value)
        # Strings starting with J: are quoted on the wire and decode as strings.
        s_enc, s_dec = fresh_session(), fresh_session()
        msg = ("project.create", canonical_payload(
            "project.create", {"name": "J:[1]", "description": "d", "repository": ""}))
        line = enc.encode(msg[0], msg[1], s_enc)
        self.assertIn('"J:[1]"', line)
        self.assertEqual(enc.decode(line, s_dec)[1]["name"], "J:[1]")


class StrictJRejectionTests(unittest.TestCase):
    """(c) J: decoding is a strict inverse of encode_wire_list."""

    def _rejects(self, token: str) -> None:
        with self.assertRaises(ValueError):
            wl.decode_wire_list(token)
        with self.assertRaises(ValueError):
            wl.decode_j_list(token)

    def test_each_guard_fires_before_the_canonical_check(self) -> None:
        # Each rejection has its own guard; the canonical re-encode check is a second line of defence.
        cases = (
            ("J:[NaN]", "non-finite"),
            ("J:[Infinity]", "non-finite"),
            ("J:[1e999]", "non-finite"),
            ('J:[{"a":1,"a":2}]', "duplicate key"),
            ('J:["\\ud800"]', "lone surrogate in J:"),
            ('J:["alpha"]', "non-canonical"),
        )
        for tok, msg in cases:
            with self.subTest(token=tok):
                with self.assertRaisesRegex(ValueError, msg):
                    wl.decode_j_list(tok)

    def test_rejects_nan(self) -> None:
        self._rejects("J:[NaN]")

    def test_rejects_infinity(self) -> None:
        self._rejects("J:[Infinity]")
        self._rejects("J:[-Infinity]")

    def test_rejects_overflowing_number_1e999(self) -> None:
        self._rejects("J:[1e999]")
        self._rejects("J:[-1e999]")
        self._rejects("J:[[1e999]]")

    def test_rejects_duplicate_keys(self) -> None:
        self._rejects('J:[{"a":1,"a":2}]')
        self._rejects('J:[{"k":{"a":1,"a":1}}]')

    def test_rejects_lone_surrogates(self) -> None:
        self._rejects('J:["\\ud800"]')
        self._rejects('J:["\\udc00x"]')
        self._rejects('J:[{"\\ud800":1}]')
        with self.assertRaises(ValueError):
            wl.encode_wire_list(["\ud800"])

    def test_rejects_non_canonical_forms(self) -> None:
        for tok in (
            'J:["alpha"]',        # bare [alpha] is the canonical form
            'J:[""]',             # bare [\e]
            "J:[]",               # empty list is []
            "J:[1.0e0]",          # canonical is 1.0
            "J:[1.50]",           # canonical is 1.5
            "J:[1,%202]",         # a space between items
            'J:[{"b":1,"a":2}]',  # keys not sorted
            'J:["\\u0041",1]',  # ASCII written as an escape
            "J:[-0]",             # canonical int is 0
        ):
            with self.subTest(token=tok):
                self._rejects(tok)

    def test_rejects_malformed_j_values(self) -> None:
        for tok in ("J:", "J:bad", "J:[1", "J:%", "J:%2G", "J:42", 'J:{"a":1}', 'J:"x"', "J:[1]x"):
            with self.subTest(token=tok):
                self._rejects(tok)

    def test_malformed_j_on_the_wire_raises(self) -> None:
        enc = RefsEncoder()
        s_dec = fresh_session()
        fused = enc._refs_prefix("task.create", s_dec)
        for bad in ("J:[NaN]", "J:[1e999]", 'J:["alpha"]', "J:bad"):
            with self.subTest(token=bad):
                with self.assertRaises(ValueError):
                    enc.decode(f'{fused} {bad} [] d normal p [] "t"', fresh_session())

    def test_canonical_j_tokens_accepted(self) -> None:
        for items in ([1, 2], [" "], [None], [1.5], [{"a": [1, "x y"]}], ["see [1] now"], [-0.0]):
            with self.subTest(items=items):
                tok = wl.encode_wire_list(items)
                self.assertTrue(tok.startswith("J:"))
                self.assertTrue(_exact_typed_equal(wl.decode_wire_list(tok), items))


class SeededEndToEndFuzzTests(unittest.TestCase):
    def test_seeded_fuzz_through_split_line_and_refs_decode(self) -> None:
        sys.path.insert(0, _ABIOS_DIR)
        import fuzz_wire_lists

        stats = fuzz_wire_lists.run(3000, seed=20261126)
        self.assertGreater(stats["bare"], 300)
        self.assertGreater(stats["j"], 300)
        self.assertGreater(stats["second_with_ref"], 50)
        self.assertEqual((stats["codec_fail"], stats["split_fail"], stats["line_fail"]), (0, 0, 0),
                         stats["examples"])

if __name__ == "__main__":
    unittest.main()
