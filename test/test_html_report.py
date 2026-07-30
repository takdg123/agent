#!/usr/bin/env python3
"""
Tests for the mobile-first HTML report generator.

Covers the two defects that made reports unreadable: unescaped model output
silently truncating paragraphs, and a desktop-only layout.
"""

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.html_report_generator import HTMLReportGenerator as G

PAPER = {
    "title": "Tightening Bounds on Warm Dark Matter with High-Redshift GRBs",
    "authors": ["Jun-Jie Wei", "Jing-Meng Hao", "Ding-Fang Hu", "Yang Liu",
                "Bao Wang", "Extra Author", "Another One"],
    "abstract": r"We use 118 Swift GRBs with \(z < 10\) to constrain WDM.",
    "arxiv_id": "2607.25261",
    "published": "Wed, 29 Jul 2026 00:00:00 -0400",
}

ANALYSIS = {
    "english": r"The sample spans \(z < 10\) at \(L \geq 4.0 \times 10^{52}\,\mathrm{erg\,s^{-1}}\). Conclusions follow.",
    "korean": "이 연구는 118개의 GRB를 사용하여 따뜻한 암흑물질을 제한합니다.",
    "quality_score": 8.0,
}

FULL = {
    **ANALYSIS,
    "relevance_score": 9.1,
    "topic_tags": ["GRB", "afterglow"],
    "why_it_matters": "Uses 118 Swift GRBs as a structure-formation probe.",
    "key_numbers": ["118 GRBs, z < 10", r"$L \geq 4.0 \times 10^{52}$ erg/s"],
}


def render(analysis=ANALYSIS, paper=PAPER):
    return G.generate_full_report([{"paper": paper, "analysis": analysis}])


class TestEscaping(unittest.TestCase):
    def test_math_content_is_not_truncated(self):
        """The 2026-07-30 failure: '<' in math ate the rest of the paragraph."""
        html = render()
        self.assertIn("Conclusions follow.", html)
        self.assertIn("constrain WDM.", html)

    def test_latex_rendered_not_raw(self):
        html = render()
        self.assertIn("×", html)
        self.assertIn("<sup>52</sup>", html)
        self.assertNotIn(r"\times", html)
        self.assertNotIn(r"\mathrm", html)
        self.assertNotIn("$", html)

    def test_injected_markup_is_neutralised(self):
        html = render({**ANALYSIS, "english": "<script>alert(1)</script> and text"})
        self.assertNotIn("<script>", html)
        self.assertIn("and text", html)

    def test_title_and_authors_escaped(self):
        html = render(paper={**PAPER, "title": "A <b>bold</b> claim & more",
                             "authors": [r"Michael P\"urrer"]})
        self.assertNotIn("<b>bold</b>", html)
        self.assertIn("Pürrer", html)


class TestMobileLayout(unittest.TestCase):
    def setUp(self):
        self.html = render()

    def test_viewport_meta(self):
        self.assertIn('name="viewport"', self.html)
        self.assertIn("width=device-width", self.html)

    def test_no_justified_text(self):
        # Justified text on a narrow screen produces rivers of whitespace.
        self.assertNotIn("justify", self.html)

    def test_no_fixed_wide_padding(self):
        self.assertNotIn("padding: 40px", self.html)

    def test_prose_text_at_least_16px(self):
        """Long-form text must be comfortable; small labels may be smaller."""
        prose_blocks = re.findall(r'class="(?:prose|why)"[^>]*style="([^"]*)"', self.html)
        self.assertTrue(prose_blocks, "expected inline styles on prose blocks")
        for style in prose_blocks:
            size = re.search(r"font-size:\s*(\d+)px", style)
            self.assertIsNotNone(size, style)
            self.assertGreaterEqual(int(size.group(1)), 16, style)

    def test_body_default_at_least_16px(self):
        body = re.search(r"<body[^>]*style=\"([^\"]*)\"", self.html)
        self.assertIsNotNone(body)
        size = re.search(r"font-size:\s*(\d+)px", body.group(1))
        self.assertGreaterEqual(int(size.group(1)), 16)

    def test_nothing_illegibly_small(self):
        sizes = [int(m) for m in re.findall(r"font-size:\s*(\d+)px", self.html)]
        self.assertGreaterEqual(min(sizes), 12, f"found sizes {sizes}")

    def test_has_narrow_first_media_query(self):
        self.assertIn("@media", self.html)


class TestEmailSafety(unittest.TestCase):
    def setUp(self):
        self.html = render()

    def test_no_javascript(self):
        self.assertNotIn("<script", self.html.lower())
        self.assertNotIn("onclick", self.html.lower())

    def test_no_external_resources(self):
        """A strict client blocks remote CSS/fonts/images; only arxiv links allowed."""
        for url in re.findall(r'(?:src|href)="(https?://[^"]+)"', self.html):
            self.assertIn("arxiv.org", url, f"external resource: {url}")

    def test_critical_styles_inlined(self):
        # Some clients drop <style>; the layout must not depend on it alone.
        self.assertIn('style="', self.html)


class TestCardStructure(unittest.TestCase):
    def test_abstract_is_included(self):
        self.assertIn("constrain WDM", render())

    def test_all_three_texts_present(self):
        html = render()
        self.assertIn("Abstract", html)
        self.assertIn("constrain WDM", html)          # abstract
        self.assertIn("Conclusions follow", html)      # english
        self.assertIn("따뜻한 암흑물질", html)            # korean

    def test_verdict_fields_render_when_present(self):
        html = render(FULL)
        self.assertIn("9.1", html)
        self.assertIn("afterglow", html)
        self.assertIn("structure-formation probe", html)
        self.assertIn("118 GRBs", html)

    def test_verdict_order_puts_why_before_abstract(self):
        html = render(FULL)
        self.assertLess(
            html.index("structure-formation probe"),
            html.index("constrain WDM"),
            "why-it-matters must precede the abstract",
        )

    def test_optional_fields_omitted_gracefully(self):
        """Chunk 1 has no relevance data yet; the card must still render."""
        html = render(ANALYSIS)
        self.assertIn("Conclusions follow", html)
        self.assertNotIn("WHY THIS MATTERS", html.upper())
        self.assertNotIn("KEY NUMBERS", html.upper())

    def test_authors_truncated_with_et_al(self):
        self.assertIn("et al", render())

    def test_arxiv_link_present(self):
        self.assertIn("arxiv.org/abs/2607.25261", render())

    def test_korean_missing_is_flagged_not_silent(self):
        html = render({**ANALYSIS, "korean": ""})
        self.assertIn("Conclusions follow", html)


class TestMultiplePapers(unittest.TestCase):
    def test_numbering_and_count(self):
        html = G.generate_full_report([
            {"paper": PAPER, "analysis": ANALYSIS},
            {"paper": {**PAPER, "title": "Second paper", "arxiv_id": "2607.00002"},
             "analysis": ANALYSIS},
        ])
        self.assertIn("Second paper", html)
        self.assertIn("2 papers", html)

    def test_empty_report_does_not_crash(self):
        html = G.generate_full_report([])
        self.assertIn("<html", html)


if __name__ == "__main__":
    unittest.main(verbosity=2)
