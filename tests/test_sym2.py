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
validate_lines = _validate_mod.validate_lines
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

    def test_unknown_opcode_named(self):
        line = BRIEF_V2.replace("(10 sym2p/1.0", "(99 sym2p/1.0")
        text, err = render_packet(line)
        self.assertIsNone(text)
        self.assertIn("unknown opcode 99", err)


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
        line = BRIEF_V2.replace("(20 sec (3 5))", "(20 sec (3 5 7))")
        errs = check_line(line, 1)
        self.assertTrue(any("range wants" in e for e in errs))

    def test_single_atom_range_ok(self):
        line = BRIEF_V2.replace("(20 sec (3 5))", "(20 sec 5)")
        self.assertEqual(check_line(line, 1), [])

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

    def test_leading_zeros_rejected(self):
        line = BRIEF_V2.replace("|88|70|", "|088|70|", 1)
        errs = check_line(line, 1)
        self.assertTrue(any("ERR:CANON" in e and "leading zeros" in e
                            for e in errs))

    def test_trailing_whitespace_rejected(self):
        errs = validate_lines([BRIEF_V2 + "  "])
        self.assertTrue(any("ERR:CANON" in e and "whitespace" in e
                            for e in errs))

    def test_blank_lines_skipped(self):
        self.assertEqual(validate_lines(["", "   "]), [])


REASON_V2 = ("2|r202|mr1|1|2|1|1|90|75|"
             "(30 cov 62)(31 (34 $cov 70) (20 sec (6 6)) ())|1||0")
SWARM_V2 = ("2|r203|mr1|1|7|1|1|90|80|"
            "(32 s (33 3 4 5) (20 sec s))|0||0")
DELEGATE_V2 = ("2|r204|mr1|1|4|11|1|85|70|"
               "(40 2 b442 (20 sec (7 9)))|0|mr1:3|0")


class ReasoningTest(unittest.TestCase):
    def test_bind_if_validates(self):
        self.assertEqual(check_line(REASON_V2, 1), [])

    def test_bind_if_renders(self):
        text, err = render_packet(REASON_V2)
        self.assertIsNone(err)
        self.assertIn("Let cov = 62.", text)
        self.assertIn("If cov < 70 then implement section 6.", text)

    def test_each_swarm_validates(self):
        self.assertEqual(check_line(SWARM_V2, 1), [])

    def test_each_swarm_renders(self):
        text, err = render_packet(SWARM_V2)
        self.assertIsNone(err)
        self.assertIn("[coordinator -> swarm]", text)
        self.assertIn("For each s in [3, 4, 5]: implement section s.", text)

    def test_spawn_delegate_validates(self):
        self.assertEqual(check_line(DELEGATE_V2, 1), [])

    def test_spawn_delegate_renders(self):
        text, err = render_packet(DELEGATE_V2)
        self.assertIsNone(err)
        self.assertIn("delegate r204 [coordinator -> scout]", text)
        self.assertIn("Spawn builder on thread b442 to implement sections 7-9.",
                      text)

    def test_unbound_reference_fails(self):
        line = REASON_V2.replace("(30 cov 62)", "")
        errs = check_line(line, 1)
        self.assertTrue(any("ERR:SCOPE" in e and "unbound" in e
                            for e in errs))

    def test_reference_before_bind_fails(self):
        body = "(31 (34 $cov 70) (20 sec (6 6)) ())(30 cov 62)"
        line = REASON_V2.split("|")
        line[9] = body
        errs = check_line("|".join(line), 1)
        self.assertTrue(any("ERR:SCOPE" in e for e in errs))

    def test_each_over_atom_fails(self):
        line = SWARM_V2.replace("(33 3 4 5)", "5")
        errs = check_line(line, 1)
        self.assertTrue(any("each iterates" in e for e in errs))

    def test_bind_name_must_be_symbol(self):
        line = REASON_V2.replace("(30 cov 62)", "(30 $cov 62)")
        errs = check_line(line, 1)
        self.assertTrue(any("bind wants" in e for e in errs))

    def test_spawn_bad_role_fails(self):
        line = DELEGATE_V2.replace("(40 2 b442", "(40 9 b442")
        errs = check_line(line, 1)
        self.assertTrue(any("spawn wants" in e for e in errs))

    def test_swarm_role_renders(self):
        text, err = render_packet(SWARM_V2)
        self.assertIsNone(err)
        self.assertIn("swarm", text)

    def test_ref_in_range_ok(self):
        line = ("2|r203|mr1|1|7|1|1|90|80|"
                "(32 s (33 3 4 5) (20 sec ($s $s)))|0||0")
        self.assertEqual(check_line(line, 1), [])

    def test_unbound_ref_in_range_fails(self):
        line = ("2|r203|mr1|1|7|1|1|90|80|"
                "(20 sec ($s $s))|0||0")
        errs = check_line(line, 1)
        self.assertTrue(any("ERR:SCOPE" in e and "unbound" in e
                            for e in errs))


class RcpTest(unittest.TestCase):
    def rcp(self, line=BRIEF_V2):
        return _sym2_parse.add_rcp(line)

    def test_rcp_line_validates(self):
        self.assertEqual(check_line(self.rcp(), 1), [])

    def test_bare_line_still_valid(self):
        self.assertEqual(check_line(BRIEF_V2, 1), [])

    def test_tampered_body_fails(self):
        line = self.rcp().replace("|88|70|", "|88|71|", 1)
        errs = check_line(line, 1)
        self.assertTrue(any("ERR:RCP" in e and "does not match" in e
                            for e in errs))

    def test_tampered_sum_fails(self):
        good = self.rcp()
        flip = "0" if good[-1] != "0" else "1"
        errs = check_line(good[:-1] + flip, 1)
        self.assertTrue(any("ERR:RCP" in e and "does not match" in e
                            for e in errs))

    def test_bad_sum_shape(self):
        errs = check_line(BRIEF_V2 + "|ZZZ", 1)
        self.assertTrue(any("ERR:RCP" in e and "16 lowercase hex" in e
                            for e in errs))

    def test_uppercase_sum_rejected(self):
        errs = check_line(BRIEF_V2 + "|0E003FAC2DF6829E", 1)
        self.assertTrue(any("ERR:RCP" in e for e in errs))

    def test_fifteen_fields_rejected(self):
        errs = check_line(self.rcp() + "|extra", 1)
        self.assertTrue(any("ERR:SHAPE" in e for e in errs))

    def test_rcp_renders(self):
        text, err = render_packet(self.rcp())
        self.assertIsNone(err)
        self.assertIn("Relay corruption protection: on.", text)

    def test_migrate_rcp_flag(self):
        out, err = _migrate_mod.migrate(BRIEF_V1, 1, rcp=True)
        self.assertIsNone(err)
        self.assertEqual(len(out.split("|")), 14)
        self.assertEqual(check_line(out, 1), [])

    def test_migrate_bare_default(self):
        out, err = _migrate_mod.migrate(BRIEF_V1, 1)
        self.assertIsNone(err)
        self.assertEqual(len(out.split("|")), 13)


class MigrateTest(unittest.TestCase):
    def test_brief_migrates(self):
        out, err = migrate(BRIEF_V1, 1)
        self.assertIsNone(err)
        self.assertTrue(out.startswith("2|b441|mr1|1|2|1|1|88|70|"))
        self.assertTrue(out.endswith("|1|mr1:v1|40"))
        self.assertIn("(11 (21 *))", out)

    def test_migrator_case_folds_symbols(self):
        out, err = migrate(BRIEF_V1, 1)
        self.assertIsNone(err)
        self.assertIn("(10 sym-2p/1.0", out)
        self.assertNotIn("SYM-2P", out)

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

    def test_pretty_printed_document(self):
        import json
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".json",
                                         delete=False) as fh:
            json.dump(BRIEF_V1, fh, indent=2)
            path = fh.name
        try:
            packets = _migrate_mod.read_packets(path)
        finally:
            os.unlink(path)
        self.assertEqual(len(packets), 1)
        out, err = migrate(packets[0][0], 1)
        self.assertIsNone(err)
        self.assertEqual(check_line(out, 1), [])


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
