"""Offline scoring regressions; no tokenizer or model access required."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/protean-abios"))
from canonical import canonical_payload
from comprehension import score_predictions


class ComprehensionTypeTests(unittest.TestCase):
    def expected(self, value):
        return [{"cmd": "task.create", "payload": canonical_payload(
            "task.create", {"project_id": "p1", "title": "t", "criteria": value})}]

    def test_nested_type_errors_are_not_exact(self):
        for original, replacement in (([1], [True]), ([0], [False]),
                                      ([True], [1]), ([1], [1.0]),
                                      ([{"nested": [0]}], [{"nested": [False]}])):
            with self.subTest(original=original, replacement=replacement):
                expected = self.expected(original)
                predicted = copy.deepcopy(expected)
                predicted[0]["payload"]["criteria"] = replacement
                score = score_predictions(expected, predicted)
                self.assertEqual(score["message_exact"], 0.0)
                self.assertEqual(score["field_accuracy"], 7 / 8)

    def test_oracle_defaults_missing_and_extra_fields(self):
        expected = self.expected([{"a": 1, "b": True}])
        predicted = [{"cmd": "task.create", "payload": {
            "title": "t", "project_id": "p1", "criteria": [{"b": True, "a": 1}]}}]
        self.assertEqual(score_predictions(expected, predicted)["message_exact"], 1.0)
        self.assertEqual(score_predictions(expected, predicted)["field_accuracy"], 1.0)
        self.assertEqual(score_predictions(expected, [])["field_accuracy"], 0.0)
        predicted[0]["payload"]["unexpected"] = 0
        self.assertEqual(score_predictions(expected, predicted)["message_exact"], 0.0)


if __name__ == "__main__":
    unittest.main()
