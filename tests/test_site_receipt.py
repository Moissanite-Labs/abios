#!/usr/bin/env python3
"""The site's ABIOS headline tables must match the committed bench receipt.

Every number in the headline tables of site/index(.template).html and
site/abios(.template).html is compared with total_primary/o200k_base in
bench/results/abios-bench.json. Also checks the 11-message TOON and Agora
figures quoted next to the index table.
"""
import json
import os
import unittest
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECEIPT = os.path.join(ROOT, "bench", "results", "abios-bench.json")
SITE = os.path.join(ROOT, "site")

# Columns per page, in table order, mapped to receipt row labels.
INDEX_COLS = ["compact JSON", "ABIOS refs", "ABIOS adaptive"]
ABIOS_COLS = ["compact JSON", "English (lossless)", "ABIOS refs", "ABIOS adaptive"]
PAGES = {
    "index.template.html": INDEX_COLS,
    "index.html": INDEX_COLS,
    "abios.template.html": ABIOS_COLS,
    "abios.html": ABIOS_COLS,
}
class _TableRows(HTMLParser):
    """Collect each <tr> as a list of its cell texts, with tags stripped."""

    def __init__(self):
        super().__init__()
        self.rows = []
        self._row = None
        self._cell = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._cell is not None:
            self._row.append("".join(self._cell).strip())
            self._cell = None
        elif tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)


def receipt_totals():
    with open(RECEIPT, encoding="utf-8") as fh:
        data = json.load(fh)
    out = {}
    for result in data["results"]:
        key = (result["count"], result["transcript"].endswith("_random"))
        out[key] = {
            row["label"]: row["total_primary"]["o200k_base"]
            for row in result["rows"]
        }
    return out


def site_rows(text):
    parser = _TableRows()
    parser.feed(text)
    out = {}
    for row in parser.rows:
        if not row:
            continue
        head = row[0].split()
        if len(head) >= 2 and head[0].isdigit() and head[1] in ("msgs", "messages"):
            # "11 msgs (fixture)", "11 messages (fixture hex)", "11 messages (random hex, seed 1)"
            key = (int(head[0]), "random" in row[0])
            out[key] = [int(c) for c in row[1:] if c.isdigit()]
    return out


class TestSiteMatchesReceipt(unittest.TestCase):
    def setUp(self):
        self.receipt = receipt_totals()

    def test_headline_tables_match_receipt(self):
        for page, cols in PAGES.items():
            with open(os.path.join(SITE, page), encoding="utf-8") as fh:
                rows = site_rows(fh.read())
            fixture_counts = sorted(c for c, rnd in rows if not rnd)
            self.assertEqual(fixture_counts, [11, 40, 200], page)
            for key, cells in rows.items():
                expected = [self.receipt[key][label] for label in cols]
                self.assertEqual(cells, expected,
                                 "%s %r disagrees with %s" % (page, key, RECEIPT))

    def test_index_eleven_message_baselines_match_receipt(self):
        r11 = self.receipt[(11, False)]
        for page in ("index.template.html", "index.html"):
            with open(os.path.join(SITE, page), encoding="utf-8") as fh:
                text = fh.read()
            self.assertIn("TOON approx fallback <strong>%d</strong>"
                          % r11["TOON (approx in-repo fallback)"], text, page)
            self.assertIn("Agora <strong>%d</strong>"
                          % r11["Agora envelope (arXiv:2410.11905)"], text, page)
            self.assertIn("ABIOS <strong>refs</strong> <strong>%d</strong> vs compact JSON <strong>%d</strong>"
                          % (r11["ABIOS refs"], r11["compact JSON"]), text, page)

    def test_check_fails_on_stale_total(self):
        with open(os.path.join(SITE, "abios.template.html"), encoding="utf-8") as fh:
            text = fh.read()
        good = self.receipt[(40, False)]["ABIOS refs"]
        stale = text.replace("<strong>%d</strong></td><td>%d" % (good, good),
                             "<strong>1990</strong></td><td>1990")
        self.assertNotEqual(stale, text)
        self.assertNotEqual(site_rows(stale)[(40, False)][2:], [good] * 2)


if __name__ == "__main__":
    unittest.main()
