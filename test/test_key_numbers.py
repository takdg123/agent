#!/usr/bin/env python3
"""
Tests for key-number extraction.

These sit at the top of the report card, so a fabricated number is far worse than
a missing one. Every failure path must return an empty list.
"""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils import key_numbers
from src.utils.llm_client import LLMError

PAPER = {
    "title": "A Bright Kilonova",
    "contents": {"abstract": "We report a kilonova.", "introduction": "Intro.",
                 "methods": "Swift observations.",
                 "results": "The ejecta mass is 0.05 Msun and z = 0.16.",
                 "conclusions": "A merger.", "source": "pdf"},
}


class Responder:
    def __init__(self, payload):
        self.payload = payload
        self.prompt = None

    def generate(self, prompt, model=None, format=None, timeout=None):
        self.prompt = prompt
        return self.payload


class TestExtraction(unittest.TestCase):
    def test_values_extracted(self):
        llm = Responder(json.dumps({"key_numbers": ["ejecta mass 0.05 Msun", "z = 0.16"]}))
        self.assertEqual(key_numbers.extract(llm, PAPER),
                         ["ejecta mass 0.05 Msun", "z = 0.16"])

    def test_paper_contents_reach_the_prompt(self):
        llm = Responder(json.dumps({"key_numbers": []}))
        key_numbers.extract(llm, PAPER)
        self.assertIn("0.05 Msun", llm.prompt)

    def test_entries_without_digits_are_dropped(self):
        llm = Responder(json.dumps({"key_numbers": [
            "a significant improvement", "ejecta mass 0.05 Msun"]}))
        self.assertEqual(key_numbers.extract(llm, PAPER), ["ejecta mass 0.05 Msun"])

    def test_capped_at_five(self):
        llm = Responder(json.dumps({"key_numbers": [f"value {i}" for i in range(20)]}))
        self.assertEqual(len(key_numbers.extract(llm, PAPER)), 5)

    def test_long_entry_truncated(self):
        llm = Responder(json.dumps({"key_numbers": ["9 " + "x" * 500]}))
        self.assertLessEqual(len(key_numbers.extract(llm, PAPER)[0]), 80)

    def test_json_in_prose_recovered(self):
        llm = Responder('Sure:\n{"key_numbers": ["118 GRBs"]}\nDone.')
        self.assertEqual(key_numbers.extract(llm, PAPER), ["118 GRBs"])


class TestFailurePaths(unittest.TestCase):
    def test_llm_error_returns_empty(self):
        class Dead:
            def generate(self, *a, **k):
                raise LLMError("model down")

        self.assertEqual(key_numbers.extract(Dead(), PAPER), [])

    def test_unparseable_returns_empty(self):
        self.assertEqual(key_numbers.extract(Responder("no json at all"), PAPER), [])

    def test_wrong_shape_returns_empty(self):
        self.assertEqual(key_numbers.extract(Responder('{"other": [1]}'), PAPER), [])

    def test_no_content_returns_empty_without_calling_model(self):
        class Exploding:
            def generate(self, *a, **k):
                raise AssertionError("must not be called")

        self.assertEqual(key_numbers.extract(Exploding(), {"title": "x"}), [])

    def test_falls_back_to_abstract_when_no_contents(self):
        llm = Responder(json.dumps({"key_numbers": ["118 GRBs"]}))
        paper = {"title": "x", "abstract": "We analyse 118 GRBs."}
        self.assertEqual(key_numbers.extract(llm, paper), ["118 GRBs"])
        self.assertIn("118 GRBs", llm.prompt)


if __name__ == "__main__":
    unittest.main(verbosity=2)
