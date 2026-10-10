#!/usr/bin/env python3
"""Unit tests for the SYM-2P v2 tooling. stdlib only.

Run from the repo root: python3 tests/test_sym2.py
"""
import importlib.util
import os
import sys
import unittest

SCRIPTS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "scripts", "protean-sym2p")
sys.path.insert(0, SCRIPTS)


def load(modname, filename):
    spec = importlib.util.spec_from_file_location(
        modname, os.path.join(SCRIPTS, filename))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_sym2_parse = load("sym2_parse", "sym2_parse.py")
_render_mod = load("sym2_render", "sym2-render.py")
_validate_mod = load("sym2_validate", "sym2-validate.py")
_migrate_mod = load("sym2_migrate", "sym2-migrate.py")

check_expr = _sym2_parse.check_expr
parse_all = _sym2_parse.parse_all
render_packet = _render_mod.render_packet
check_line = _validate_mod.check_line
migrate = _migrate_mod.migrate

BRIEF_V2 = ("2|b441|mr1|1|2|1|1|88|70|"
            "(10 sym2p/1.0 (20 sec (3 5)))(11 (21 *))(12 (22 validator 0 1))|"
            "1|mr1:1|40")

BRIEF_V1 = {
    "v": 2, "id": "b441", "tk": "mr1", "prj": "sym2integration",
    "f": "cos", "t": "builder", "a": "assign", "s": "mr1",
    "st": "proposed", "cf": 88, "cov": 70,
    "cond": [
        "scope: implement SYM-2P/1.0 sections 3-5 only",
        "constraint: no existing path may be modified",
        "acceptance: validator exits 0 on valid fixtures, non-zero on invalid",
    ],
    "rq": "ack", "base": "mr1:v1", "exp": 40,
    "ext": {"sym2p": {"rev": "1.0"}},
}


class RenderTest(unittest.TestCase):
    def test_brief_renders(self):
        text, err = render_packet(BRIEF_V2)
        self.assertIsNone(err)
        self.assertIn("assign b441 [coordinator -> builder] (proposed)", text)
        self.assertIn("Scope: implement sections 3-5 of sym2p/1.0.", text)
        self.assertIn("Constraint: modify no existing paths.", text)
        self.assertIn("Acceptance: validator exits 0 on valid input, "
                      "1 on invalid.", text)

    def test_garbage_fails(self):
        text, err = render_packet("hello")
        self.assertIsNone(text)
        self.assertIsNotNone(err)

    def test_unknown_code_fails(self):
        line = BRIEF_V2.replace("|1|2|1|", "|1|2|99|", 1)
        text, err = render_packet(line)
        self.assertIsNone(text)
        self.assertIn("unknown act code", err)


class ValidateTest(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(check_line(BRIEF_V2, 1), [])

    def test_bad_act(self):
        line = BRIEF_V2.replace("|1|2|1|", "|1|2|99|", 1)
        errs = check_line(line, 1)
        self.assertTrue(any("ERR:CODE" in e for e in errs))

    def test_unbalanced(self):
        errs = check_line(BRIEF_V2.replace("(3 5))", "(3 5)"), 1)
        self.assertTrue(any("unbalanced" in e for e in errs))

    def test_unknown_opcode(self):
        line = BRIEF_V2.replace("(10 sym2p/1.0", "(99 sym2p/1.0")
        errs = check_line(line, 1)
        self.assertTrue(any("unknown opcode 99" in e for e in errs))

    def test_bad_range(self):
        line = BRIEF_V2.replace("(20 sec (3 5))", "(20 sec 5)")
        errs = check_line(line, 1)
        self.assertTrue(any("range wants" in e for e in errs))

    def test_cf_out_of_range(self):
        line = BRIEF_V2.replace("|88|70|", "|101|70|", 1)
        errs = check_line(line, 1)
        self.assertTrue(any("ERR:RANGE" in e for e in errs))

    def test_wrong_field_count(self):
        errs = check_line("2|b441|mr1", 1)
        self.assertTrue(any("ERR:SHAPE" in e for e in errs))

    def test_noncanonical_spacing(self):
        line = BRIEF_V2.replace("(10 sym2p/1.0", "(10  sym2p/1.0")
        errs = check_line(line, 1)
        self.assertTrue(any("ERR:CANON" in e for e in errs))

    def test_tk_too_long(self):
        line = BRIEF_V2.replace("|mr1|", "|" + "t" * 65 + "|", 1)
        errs = check_line(line, 1)
        self.assertTrue(any("TK longer than 64" in e for e in errs))


class MigrateTest(unittest.TestCase):
    def test_brief_migrates(self):
        out, err = migrate(BRIEF_V1, 1)
        self.assertIsNone(err)
        self.assertTrue(out.startswith("2|b441|mr1|1|2|1|1|88|70|"))
        self.assertTrue(out.endswith("|1|mr1:v1|40"))
        self.assertIn("(11 (21 *))", out)

    def test_migrated_validates(self):
        out, err = migrate(BRIEF_V1, 1)
        self.assertIsNone(err)
        self.assertEqual(check_line(out, 1), [])

    def test_unknown_cond_fails_loudly(self):
        obj = dict(BRIEF_V1, cond=["scope: do something ineffable"])
        out, err = migrate(obj, 1)
        self.assertIsNone(out)
        self.assertIn("no v2 pattern", err)

    def test_unknown_role_fails(self):
        obj = dict(BRIEF_V1, f="oracle")
        out, err = migrate(obj, 1)
        self.assertIsNone(out)
        self.assertIn("unknown v1 role", err)


class ParseTest(unittest.TestCase):
    def test_nested(self):
        exprs, err = parse_all("(10 a (20 sec (3 5)))")
        self.assertIsNone(err)
        self.assertEqual(exprs, [["10", "a", ["20", "sec", ["3", "5"]]]])

    def test_unbalanced(self):
        _, err = parse_all("(10 a")
        self.assertIsNotNone(err)

    def test_check_expr_ok(self):
        exprs, _ = parse_all("(10 sym2p/1.0 (20 sec (3 5)))")
        self.assertIsNone(check_expr(exprs[0]))


if __name__ == "__main__":
    unittest.main()
