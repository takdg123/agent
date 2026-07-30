#!/usr/bin/env python3
"""
Tests that the validator recognises the current report markup.

The email is gated on quality_score >= 70. When the per-paper container was
renamed from 'paper' to 'card', the content check found zero papers and the score
fell from 82 to 42 — silently stopping the daily email.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.report_validator import ReportValidator
from src.utils.html_report_generator import HTMLReportGenerator as G

PAPER = {"title": "A Bright Kilonova Following GRB 240710A",
         "authors": ["A. Author"], "arxiv_id": "2607.25261",
         "abstract": "We report a kilonova with an ejecta mass of 0.05 Msun."}
ANALYSIS = {"english": "This analysis reviews the findings and their significance "
                       "for merger physics, summarising the key results.",
            "korean": "이 분석은 병합 물리학에 대한 발견과 그 의의를 검토합니다. 주요 결과를 요약합니다.",
            "quality_score": 8.0}


def validator():
    v = ReportValidator()
    v.use_llm = False  # rule-based only; no model needed
    return v


class TestCurrentMarkupValidates(unittest.TestCase):
    def setUp(self):
        self.html = G.generate_full_report([{"paper": PAPER, "analysis": ANALYSIS}])
        self.result = validator().validate_report(self.html, 1)

    def test_papers_are_detected(self):
        self.assertNotIn("Content: No papers found in report", self.result["issues"])

    def test_no_critical_issues(self):
        self.assertEqual(self.result["issues"], [])

    def test_score_clears_the_email_threshold(self):
        self.assertGreaterEqual(self.result["rule_score"], 70,
                                "below 70 the daily email is not sent")

    def test_paper_samples_extractable(self):
        self.assertTrue(validator()._extract_paper_samples(self.html))


class TestLegacyMarkupStillValidates(unittest.TestCase):
    """Reports already on disk must not become invalid."""

    def test_old_paper_class_detected(self):
        html = ('<html><head><style>a{color:red}</style></head><body>'
                '<div class="paper"><h2>A Kilonova Following GRB 240710A</h2>'
                '<p>Analysis of the findings and review of the summary results.</p>'
                '<p>한국어 요약: 이 논문은 킬로노바를 보고합니다.</p>'
                '<a href="https://arxiv.org/abs/2607.25261">arXiv</a>'
                '</div></body></html>')
        result = validator().validate_report(html, 1)
        self.assertNotIn("Content: No papers found in report", result["issues"])


class TestEmptyReportIsFlagged(unittest.TestCase):
    def test_report_with_no_papers_reports_an_issue(self):
        html = G.generate_full_report([])
        result = validator().validate_report(html, 0)
        self.assertIn("Content: No papers found in report", result["issues"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
