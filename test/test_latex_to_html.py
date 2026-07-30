#!/usr/bin/env python3
"""
Tests for latex_to_html: HTML escaping and LaTeX -> readable HTML conversion.

The escaping cases are regressions from data/reports/expert_report_20260730.html,
where unescaped '<' inside LaTeX caused the browser to discard the rest of the
paragraph.
"""

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.latex_to_html import convert


class TestEscaping(unittest.TestCase):
    """Model output must never be able to open an HTML tag."""

    def test_less_than_inside_math_survives(self):
        # The exact string that broke the 2026-07-30 report: the raw '<' opened a
        # tag and the browser discarded everything up to the next '>'.
        source = r"118 GRBs with redshift \(z < 10\) and luminosity"
        result = convert(source)
        self.assertIn("&lt;", result)
        self.assertIn("luminosity", result)  # text after the '<' must survive
        self.assertNoUnsafeAngleBrackets(result)

    def assertNoUnsafeAngleBrackets(self, result: str):
        """No '<' may remain except the sup/sub tags we intentionally emit."""
        stripped = re.sub(r"</?su[pb]>", "", result)
        self.assertNotIn("<", stripped)
        self.assertNotIn(">", stripped)

    def test_bare_html_tag_is_neutralised(self):
        result = convert("before <script>alert(1)</script> after")
        self.assertNotIn("<script", result)
        self.assertIn("&lt;script&gt;", result)
        self.assertIn("after", result)

    def test_ampersand_escaped(self):
        self.assertIn("&amp;", convert("Swift & Fermi"))

    def test_greater_than_escaped(self):
        result = convert(r"$m_{\rm WDM} > 1.2$ keV")
        self.assertIn("&gt;", result)
        self.assertIn("keV", result)


class TestMathConversion(unittest.TestCase):
    def test_delimiters_stripped(self):
        self.assertNotIn("$", convert(r"a value of $42$ units"))
        result = convert(r"redshift \(z\) matters")
        self.assertNotIn(r"\(", result)
        self.assertNotIn(r"\)", result)

    def test_times_and_exponent(self):
        result = convert(r"$8.0 \times 10^{-5}$")
        self.assertIn("×", result)
        self.assertIn("<sup>-5</sup>", result)
        self.assertNotIn("^", result)

    def test_positive_exponent(self):
        self.assertIn("<sup>52</sup>", convert(r"$4.0 \times 10^{52}$"))

    def test_single_char_exponent_without_braces(self):
        self.assertIn("<sup>2</sup>", convert(r"$r^2$"))

    def test_subscript(self):
        self.assertIn("<sub>WDM</sub>", convert(r"$m_{\rm WDM}$"))

    def test_relations(self):
        self.assertIn("≲", convert(r"$z \lesssim 5$"))
        self.assertIn("≳", convert(r"$z \gtrsim 5$"))
        self.assertIn("≥", convert(r"$L \geq 4$"))
        self.assertIn("≤", convert(r"$L \leq 4$"))
        self.assertIn("≈", convert(r"$f \approx 0.6$"))
        self.assertIn("±", convert(r"$1.4 \pm 0.2$"))

    def test_greek(self):
        self.assertIn("α", convert(r"$\alpha$"))
        self.assertIn("Γ", convert(r"$\Gamma$"))
        self.assertIn("μ", convert(r"$\mu$"))

    def test_mathrm_unwrapped(self):
        result = convert(r"$L \geq 4.0 \times 10^{52}\,\mathrm{erg\,s^{-1}}$")
        self.assertIn("erg", result)
        self.assertNotIn("mathrm", result)
        self.assertNotIn("\\", result)

    def test_frac_becomes_slash(self):
        self.assertIn("1/2", convert(r"$\frac{1}{2}$"))

    def test_no_stray_braces(self):
        for source in [r"$m_{\rm WDM} > 1$", r"$10^{52}$", r"$\mathrm{erg}$"]:
            self.assertNotIn("{", convert(source), source)
            self.assertNotIn("}", convert(source), source)

    def test_unknown_command_left_readable(self):
        # Better to show the word than to silently drop content.
        result = convert(r"$\qqundefined x$")
        self.assertIn("qqundefined", result)
        self.assertNotIn("\\", result)


class TestAccents(unittest.TestCase):
    """Author names arrive with LaTeX accents from the arXiv RSS feed."""

    def test_umlaut(self):
        # 'Michael P\"urrer' appeared verbatim in the 2026-07-30 report.
        self.assertEqual(convert(r'Michael P\"urrer'), "Michael Pürrer")

    def test_acute(self):
        self.assertEqual(convert(r"Jos\'e"), "José")

    def test_tilde_n(self):
        self.assertEqual(convert(r"Mu\~noz"), "Muñoz")

    def test_braced_accent(self):
        self.assertEqual(convert(r'P\"{u}rrer'), "Pürrer")


class TestPlainText(unittest.TestCase):
    def test_plain_text_untouched(self):
        source = "This study investigates short-timescale optical variability."
        self.assertEqual(convert(source), source)

    def test_empty_and_none(self):
        self.assertEqual(convert(""), "")
        self.assertEqual(convert(None), "")

    def test_paragraph_breaks_preserved(self):
        result = convert("First para.\n\nSecond para.")
        self.assertIn("First para.", result)
        self.assertIn("Second para.", result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
