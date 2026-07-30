#!/usr/bin/env python3
"""
Tests for paper_text: turning a PDF into the sections that carry the findings.

Both summaries are built from this output, so an empty or mis-split extraction
degrades every downstream stage.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils import paper_text

PAPER = {
    "title": "A Bright Kilonova",
    "abstract": "We report a kilonova following a short GRB.",
    "arxiv_id": "2607.25261",
    "pdf_url": "https://arxiv.org/pdf/2607.25261.pdf",
}

FULL_TEXT = """A Bright Kilonova Following GRB 240710A

ABSTRACT
We report observations of a kilonova.

1. Introduction
Short gamma-ray bursts are believed to originate from neutron star mergers.
This introduction motivates the observations that follow.

2. Observations and Data Reduction
We observed the field with Swift and ground-based telescopes.

3. Results
The light curve peaks at 0.5 days with an ejecta mass of 0.05 solar masses.
A blue component dominates the early emission.

4. Discussion
The blue component implies a lanthanide-poor ejecta.

5. Conclusions
We conclude that the event is consistent with a neutron star merger.

Acknowledgements
We thank the observatory staff.

References
[1] Some Author et al. 2017
"""


class TestSectionSplitting(unittest.TestCase):
    def setUp(self):
        self.sections = paper_text.split_sections(FULL_TEXT)

    def test_introduction_found(self):
        self.assertIn("neutron star mergers", self.sections["introduction"])

    def test_results_found(self):
        self.assertIn("0.05 solar masses", self.sections["results"])

    def test_conclusions_found(self):
        self.assertIn("consistent with a neutron star merger", self.sections["conclusions"])

    def test_references_excluded(self):
        joined = " ".join(self.sections.values())
        self.assertNotIn("Some Author et al. 2017", joined)

    def test_acknowledgements_excluded(self):
        joined = " ".join(self.sections.values())
        self.assertNotIn("observatory staff", joined)

    def test_methods_found(self):
        self.assertIn("Swift and ground-based", self.sections["methods"])

    def test_sections_do_not_bleed(self):
        # The introduction must stop where the observations begin.
        self.assertNotIn("Swift and ground-based", self.sections["introduction"])
        self.assertNotIn("0.05 solar masses", self.sections["introduction"])

    def test_compound_heading_classified_by_first_keyword(self):
        text = "Summary and Conclusions\nWe found a kilonova.\n"
        self.assertIn("We found a kilonova", paper_text.split_sections(text)["conclusions"])

    def test_prose_line_is_not_mistaken_for_heading(self):
        text = ("Introduction\n"
                "This introduction motivates the observations that follow.\n"
                "Results here are discussed at length in the text below.\n")
        sections = paper_text.split_sections(text)
        self.assertIn("motivates the observations", sections["introduction"])
        self.assertEqual(sections["results"], "")

    def test_unnumbered_headings(self):
        text = "INTRODUCTION\nMotivation here.\n\nRESULTS\nWe measure 42.\n\nCONCLUSIONS\nDone."
        sections = paper_text.split_sections(text)
        self.assertIn("Motivation here", sections["introduction"])
        self.assertIn("We measure 42", sections["results"])
        self.assertIn("Done", sections["conclusions"])


class TestTailTruncation(unittest.TestCase):
    def test_table_note_does_not_truncate_paper(self):
        """
        Regression: arXiv 2606.06213 has a table note beginning "References."
        early in the paper. Matching it discarded the results and conclusions.
        """
        text = ("Introduction\n" + "motivation text. " * 200 +
                "\nReferences. (1) This work; (2) Eyles-Ferris et al. 2025\n" +
                "Results\n" + "we measure an ejecta mass of 0.05 Msun. " * 100 +
                "\nConclusions\nA neutron star merger.\n"
                "References\n[1] Author 2017\n")
        sections = paper_text.split_sections(text)
        self.assertIn("ejecta mass", sections["results"])
        self.assertIn("neutron star merger", sections["conclusions"])
        self.assertNotIn("Author 2017", " ".join(sections.values()))

    def test_real_back_matter_still_dropped(self):
        text = ("Introduction\n" + "motivation. " * 300 +
                "\nConclusions\nWe conclude things.\n"
                "Acknowledgements\nWe thank the staff.\n")
        sections = paper_text.split_sections(text)
        self.assertIn("We conclude things", sections["conclusions"])
        self.assertNotIn("thank the staff", " ".join(sections.values()))

    def test_cross_reference_is_not_back_matter(self):
        text = ("Introduction\n" + "motivation. " * 300 +
                "\nResults\nSee Appendix A for details. We measure 42.\n")
        sections = paper_text.split_sections(text)
        self.assertIn("We measure 42", sections["results"])


class TestBudget(unittest.TestCase):
    def test_full_budget_used_when_sections_missing(self):
        """A review paper with only an introduction should still get the cap."""
        sections = {"introduction": "x" * 50000, "methods": "",
                    "results": "", "conclusions": ""}
        capped = paper_text._cap(sections, 12000)
        self.assertEqual(len(capped["introduction"]), 12000)

    def test_findings_weighted_above_methods(self):
        sections = {name: "x" * 50000 for name in
                    ("introduction", "methods", "results", "conclusions")}
        capped = paper_text._cap(sections, 12000)
        self.assertLessEqual(sum(len(v) for v in capped.values()), 12000)
        self.assertGreater(len(capped["conclusions"]), len(capped["methods"]))
        self.assertGreater(len(capped["results"]), len(capped["introduction"]))

    def test_short_sections_release_budget(self):
        sections = {"conclusions": "short.", "results": "y" * 40000,
                    "introduction": "z" * 40000, "methods": ""}
        capped = paper_text._cap(sections, 12000)
        self.assertEqual(capped["conclusions"], "short.")
        # The unused conclusions share must go to results, not be wasted.
        self.assertGreater(sum(len(v) for v in capped.values()), 11000)


class TestFallback(unittest.TestCase):
    def test_no_headings_uses_head_and_tail(self):
        text = "word " * 5000
        sections = paper_text.split_sections(text)
        self.assertTrue(sections["introduction"], "head slice should be populated")
        self.assertTrue(sections["conclusions"], "tail slice should be populated")

    def test_short_text_without_headings_survives(self):
        sections = paper_text.split_sections("A very short note about a burst.")
        self.assertIn("short note", " ".join(sections.values()))


class TestExtract(unittest.TestCase):
    def test_pdf_failure_degrades_to_abstract(self):
        with patch.object(paper_text, "_fetch_pdf", side_effect=OSError("network down")):
            result = paper_text.extract(PAPER)
        self.assertEqual(result["source"], "abstract")
        self.assertIn("kilonova following a short GRB", result["abstract"])

    def test_successful_extraction_marked_as_pdf(self):
        with patch.object(paper_text, "_fetch_pdf", return_value=b"%PDF-fake"), \
             patch.object(paper_text, "_pdf_to_text", return_value=FULL_TEXT):
            result = paper_text.extract(PAPER)
        self.assertEqual(result["source"], "pdf")
        self.assertIn("0.05 solar masses", result["results"])

    def test_empty_pdf_text_degrades_to_abstract(self):
        """A scanned or broken PDF must not yield an empty analysis input."""
        with patch.object(paper_text, "_fetch_pdf", return_value=b"%PDF-fake"), \
             patch.object(paper_text, "_pdf_to_text", return_value="   "):
            result = paper_text.extract(PAPER)
        self.assertEqual(result["source"], "abstract")

    def test_total_length_capped(self):
        huge = "Introduction\n" + ("padding words here " * 20000) + "\nConclusions\nEnd."
        with patch.object(paper_text, "_fetch_pdf", return_value=b"%PDF-fake"), \
             patch.object(paper_text, "_pdf_to_text", return_value=huge):
            result = paper_text.extract(PAPER, max_chars=4000)
        total = sum(len(result[k]) for k in
                    ("introduction", "methods", "results", "conclusions"))
        self.assertLessEqual(total, 4000)

    def test_as_prompt_context_includes_all_sections(self):
        extracted = {"abstract": "A.", "introduction": "B.", "methods": "M.",
                     "results": "C.", "conclusions": "D.", "source": "pdf"}
        context = paper_text.as_prompt_context(extracted)
        for piece in ("A.", "B.", "M.", "C.", "D."):
            self.assertIn(piece, context)

    def test_as_prompt_context_skips_empty_sections(self):
        extracted = {"abstract": "A.", "introduction": "", "methods": "",
                     "results": "", "conclusions": "", "source": "abstract"}
        context = paper_text.as_prompt_context(extracted)
        self.assertIn("A.", context)
        self.assertNotIn("Results:", context)


class TestRealPdf(unittest.TestCase):
    """Exercises fitz against a cached PDF if one is available."""

    def test_extraction_from_cached_pdf(self):
        cached = sorted(Path("data/pdfs").glob("*.pdf"))
        if not cached:
            self.skipTest("no cached PDFs available")
        text = paper_text._pdf_to_text(cached[0].read_bytes())
        self.assertGreater(len(text), 500, "expected substantial text from a real paper")


if __name__ == "__main__":
    unittest.main(verbosity=2)
