"""Assertion-free R5 unit & 22-vector adversarial round-trip suite for lossless wire_lists."""
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
    ("V02_safe_paths", ["src/auth.py", "tests/test_auth.py"], "S["),
    ("V03_single_safe", ["alpha"], "S["),
    ("V04_pr39_bug1_single_space", [" "], "J:"),
    ("V05_pr39_bug1_spaces_and_tab", ["   ", "\t"], "J:"),
    ("V06_single_empty_str", [""], "J:"),
    ("V07_double_empty_str", ["", ""], "J:"),
    ("V08_pr39_bug2_int_list", [1, 2], "J:"),
    ("V09_pr39_bug2_bool_null_list", [True, False, None], "J:"),
    ("V10_mixed_scalar_types", [0, 1, False, True, "0", "1", -7], "J:"),
    ("V11_pr39_bug3_bracket_space", ["see [1] now"], "J:"),
    ("V12_pr39_bug3_multi_brackets", ["a] b", "c [d] e"], "J:"),
    ("V13_percent_escape_roundtrip", ["%20", "%25", "%2520", "%%20", "%25 0"], "J:"),
    ("V14_semicolon_and_backslash", ["a;b", "c\\d", "trail\\"], "J:"),
    ("V15_quotes_and_newlines", ['quote"here', "line1\nline2", "cr\rhere"], "J:"),
    ("V16_reserved_session_handles", ["-", "p", "t", "a", "h", "f", "v", "g"], "J:"),
    ("V17_reserved_prefixes_digits", ["http://example.com", "https://x.y/z", "42", "{k:v}"], "J:"),
    ("V18_wire_marker_self_quote", ["S[a;b]", "J:[1,2]", "[]", "\\e"], "J:"),
    ("V19_nested_lists_and_dicts", [["nested", [1, 2]], {"k": "v with space", "n": None}], "J:"),
    ("V20_unicode_arabic_cjk_spaces", ["العربية", "日本語 テスト", "é é é"], "J:"),
    ("V21_comma_braces_unicode_ws", ["a,b", "x{y}", "u\u00a0v", "line\u2028sep"], "J:"),
    ("V22_long_list_content_ref_size", ["item_alpha"] * 25, "S["),
)


class WireListsLosslessR5Tests(unittest.TestCase):
    def test_22_adversarial_vectors_single_token_typed_bijection(self) -> None:
        self.assertEqual(len(ADVERSARIAL_22_VECTORS), 22)
        for label, payload, expected_prefix in ADVERSARIAL_22_VECTORS:
            with self.subTest(vector=label):
                tok = wl.encode_wire_list(payload)
                self.assertIs(type(tok), str)
                self.assertTrue(tok.startswith(expected_prefix), f"{label}: got {tok!r}")
                self.assertFalse(any(ch.isspace() for ch in tok), f"{label}: whitespace in {tok!r}")
                self.assertEqual(len(tok.split()), 1, f"{label}: split into multiple tokens: {tok!r}")
                decoded = wl.decode_wire_list(tok)
                self.assertTrue(
                    _exact_typed_equal(decoded, payload),
                    f"{label}: expected {payload!r}, got {decoded!r}",
                )

    def test_custom_separator_roundtrip(self) -> None:
        tok = wl.encode_wire_list(["alpha", "beta"], sep="|")
        self.assertEqual(tok, "S[alpha|beta]")
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

    def test_literal_string_fields_do_not_collide_with_s_or_j_wire_lists(self) -> None:
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
        self.assertTrue(_exact_typed_equal(decoded["scope"], [1, 2]))

        # coerce_wire_types supports [], S[...], J:..., legacy [...], and ignores malformed J:
        c1 = coerce_wire_types("task.create", {"criteria": "[]", "scope": "S[x;y]", "dependencies": 'J:["%20"]'})
        self.assertEqual(c1["criteria"], [])
        self.assertEqual(c1["scope"], ["x", "y"])
        self.assertEqual(c1["dependencies"], [" "])
        c2 = coerce_wire_types("task.create", {"criteria": "J:[1,2]", "scope": "[1,2]", "dependencies": "J:bad"})
        self.assertTrue(_exact_typed_equal(c2["criteria"], [1, 2]))
        self.assertTrue(_exact_typed_equal(c2["scope"], [1, 2]))
        self.assertEqual(c2["dependencies"], "J:bad")

    def test_fail_closed_encode_and_decode_wire_list_guards(self) -> None:
        # Non-list inputs to encode_wire_list
        for bad_items in ("abc", ("a",), {"a": 1}, None, 42, True):
            with self.assertRaises(ValueError):
                wl.encode_wire_list(bad_items)  # type: ignore[arg-type]

        # Invalid separators
        for bad_sep in ("", ";;", " ", "\t", "[", "]", '"', "\\", "%", ",", "{", "}", 7, None):
            with self.assertRaises(ValueError):
                wl.encode_wire_list(["a"], sep=bad_sep)  # type: ignore[arg-type]
            with self.assertRaises(ValueError):
                wl.decode_wire_list("[]", sep=bad_sep)  # type: ignore[arg-type]

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
            "[a;b]",
            "X[a;b]",
            "S[a;b",
        )
        for bad_tok in bad_tokens:
            with self.subTest(bad_tok=bad_tok):
                with self.assertRaises(ValueError):
                    wl.decode_wire_list(bad_tok)

    def test_hardened_legacy_string_list_api_and_boundaries(self) -> None:
        self.assertTrue(wl.can_encode_string_list([]))
        self.assertTrue(wl.can_encode_string_list(["alpha", "beta", ""]))
        self.assertTrue(wl.can_encode_string_list(["a;b", "c\\d"]))
        self.assertEqual(wl.encode_string_list([]), "[]")
        self.assertEqual(wl.encode_string_list([""]), "[\\e]")
        self.assertEqual(wl.encode_string_list(["a;b", "c\\d"]), "[a\\;b;c\\\\d]")
        self.assertEqual(wl.decode_string_list("[a\\;b;c\\\\d]"), ["a;b", "c\\d"])
        self.assertEqual(wl.decode_string_list("[\\e]"), [""])
        self.assertEqual(wl.decode_string_list("[]"), [])
        self.assertEqual(wl.decode_string_list('["see [1] now"]'), ["see [1] now"])
        self.assertEqual(wl.decode_string_list("S[alpha;beta]"), ["alpha", "beta"])
        self.assertEqual(wl.decode_string_list('J:["%20"]'), [" "])
        # Unrecognized escape in legacy _unescape_item preserves literal backslash
        self.assertEqual(wl._unescape_item("a\\xb"), "a\\xb")

        # Ineligible lists rejected by can_encode_string_list & encode_string_list
        ineligible: tuple[Any, ...] = (
            "notalist",
            ("alpha", "beta"),
            [" "],
            ["\t"],
            ["a b"],
            ["a\nb"],
            ["a\rb"],
            ['a"b'],
            ["a[b"],
            ["a]b"],
            ["trail\\"],
            ["{obj}"],
            ["http://x"],
            ["-"],
            ["p"],
            ["42"],
            [1, 2],
            [True],
            [None],
        )
        for bad_list in ineligible:
            with self.subTest(ineligible=bad_list):
                self.assertFalse(wl.can_encode_string_list(bad_list))
                with self.assertRaises(ValueError):
                    wl.encode_string_list(bad_list)

        # Bad sep on legacy encode_string_list & decode_string_list
        with self.assertRaises(ValueError):
            wl.encode_string_list(["a"], sep=" ")
        self.assertIsNone(wl.decode_string_list("[a;b]", sep=" "))
        self.assertIsNone(wl.decode_string_list(123))  # type: ignore[arg-type]

        # Legacy decode_string_list rejects Bug 1, Bug 2, and invalid forms cleanly with None
        none_cases = (
            "[ ]",
            "[\t]",
            "[   ]",
            "[1,2]",
            "[true,false]",
            "[-1]",
            "[null]",
            "notbracketed",
            "[unclosed",
            "unopened]",
            "[a b]",
            "[p]",
            "[123]",
            "[http://x]",
            "[{a}]",
            "[a\\]",
            "J:[1,2]",
            "J:notjson",
            "S[]",
        )
        for tok in none_cases:
            with self.subTest(none_tok=tok):
                self.assertIsNone(wl.decode_string_list(tok))


if __name__ == "__main__":
    unittest.main()
