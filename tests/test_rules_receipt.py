#!/usr/bin/env python3
"""Published refs-with-rules totals must match the committed bench receipt.

The README, paper, docs/abios-bench.md and site/abios(.template).html quote
the informative REFS_DECODE_RULES size and the 11-message refs totals with
those rules added (fixture and random hex ids). Each figure is derived from
bench/results/abios-bench.json: rules = refs_decode_rules_tokens, with-rules
= the 11-message ABIOS refs total_primary/o200k_base + rules.
"""
import json
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECEIPT = os.path.join(ROOT, "bench", "results", "abios-bench.json")
sys.path.insert(0, os.path.join(ROOT, "scripts", "protean-abios"))

# Published figures at this head (qalam, supersede-53): rules 374 -> 425.
PUBLISHED = {"rules": 425, "refs_fixture": 765, "refs_random": 743,
             "with_rules_fixture": 1190, "with_rules_random": 1168}
# Earlier refs-with-rules figures: #39 (374 rules), 0e91a57 (421), #39 at 378.
OLD_FIGURES = ("1139", "1117", "1186", "1164", "1143", "1121")


def receipt_figures():
    with open(RECEIPT, encoding="utf-8") as fh:
        data = json.load(fh)
    rules = data["meta"]["refs_decode_rules_tokens"]
    refs = {}
    for result in data["results"]:
        if result["count"] != 11:
            continue
        row = next(r for r in result["rows"] if r["label"] == "ABIOS refs")
        refs[result["transcript"].endswith("_random")] = row["total_primary"]["o200k_base"]
    return {"rules": rules, "refs_fixture": refs[False], "refs_random": refs[True],
            "with_rules_fixture": refs[False] + rules, "with_rules_random": refs[True] + rules}


def expected_quotes(f):
    r, wf, wr = f["rules"], f["with_rules_fixture"], f["with_rules_random"]
    site = [f"informative {r}-token REFS decode rules (fixture refs with rules: {wf})"]
    return {
        "README.md": [
            f"**{f['refs_fixture']}** (+{r} REFS decode rules → **{wf}** billed with rules)",
            f"**{f['refs_random']}** (+{r} rules → **{wr}**)",
            f"informative **{r}**-token `REFS_DECODE_RULES` text (refs with rules: **{wf}** "
            f"on the 11-message fixture, **{wr}** on random-id seed 1)",
        ],
        "paper/abios.md": [f"REFS_DECODE_RULES) adds **{r}** o200k tokens"],
        "docs/abios-bench.md": [f"REFS_DECODE_RULES): **{r}** tokens (o200k_base)"],
        "site/abios.template.html": site,
        "site/abios.html": site,
    }


def copy_problems(texts, figures):
    problems = []
    for path, quotes in expected_quotes(figures).items():
        text = texts[path]
        problems += [f"{path}: missing {q!r}" for q in quotes if q not in text]
        problems += [f"{path}: stale {old}" for old in OLD_FIGURES
                     if re.search(rf"(?<![\d.]){old}(?![\d.])", text)]
    return problems


def read_texts():
    out = {}
    for path in expected_quotes(PUBLISHED):
        with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
            out[path] = fh.read()
    return out


class RulesReceiptTests(unittest.TestCase):
    def setUp(self):
        self.figures = receipt_figures()
        self.texts = read_texts()

    def test_receipt_matches_published_figures(self):
        self.assertEqual(self.figures, PUBLISHED)

    def test_copy_matches_receipt(self):
        self.assertEqual(copy_problems(self.texts, self.figures), [])

    def test_check_fails_on_stale_copy(self):
        texts = dict(self.texts)
        wf = self.figures["with_rules_fixture"]
        texts["README.md"] = texts["README.md"].replace(f"**{wf}**", "**1139**")
        self.assertNotEqual(texts["README.md"], self.texts["README.md"])
        problems = copy_problems(texts, self.figures)
        self.assertTrue(any("README.md" in p for p in problems), problems)
        texts = dict(self.texts)
        texts["site/abios.html"] = texts["site/abios.html"].replace(f"rules: {wf}", "rules: 1139")
        self.assertTrue(copy_problems(texts, self.figures))

    def test_rules_text_token_count_matches_receipt(self):
        try:
            import tiktoken
        except ImportError:
            self.skipTest("tiktoken not installed")
        from decode_rules import REFS_DECODE_RULES
        enc = tiktoken.get_encoding("o200k_base")
        self.assertEqual(len(enc.encode(REFS_DECODE_RULES)), self.figures["rules"])


if __name__ == "__main__":
    unittest.main()
