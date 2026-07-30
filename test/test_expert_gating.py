#!/usr/bin/env python3
"""
Tests for domain-expert gating.

Running the kilonova expert on a pure GRB paper cost ~38s and fed a
confidence-0.00 review into the synthesis, diluting it.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.harness.expert_harness import ExpertHarness

select = ExpertHarness.select_experts


class TestGating(unittest.TestCase):
    def test_grb_paper_skips_kilonova_expert(self):
        # The real 2026-07-30 case: kilonova confidence was 0.00.
        paper = {"title": "The afterglow of gamma-ray burst - supernova connections",
                 "abstract": "We model X-ray afterglows of long GRBs with SN ejecta.",
                 "topic_tags": ["GRB", "afterglow", "SN"]}
        self.assertEqual(select(paper), (True, False))

    def test_kilonova_paper_skips_grb_expert(self):
        paper = {"title": "Beta-Particle Transport in Kilonova Ejecta",
                 "abstract": "We compute thermalization in r-process enriched ejecta.",
                 "topic_tags": ["kilonova", "r-process"]}
        self.assertEqual(select(paper), (False, True))

    def test_multi_messenger_paper_gets_both(self):
        paper = {"title": "Inferring Neutron Star Properties from GW and GRB Observations",
                 "abstract": "We combine GW170817 with short GRB afterglow constraints.",
                 "topic_tags": ["GRB", "kilonova", "multi-messenger"]}
        self.assertEqual(select(paper), (True, True))

    def test_unrecognised_paper_gets_both(self):
        """Never lose all specialist review just because cues were missed."""
        paper = {"title": "A study of something entirely different",
                 "abstract": "We measure unrelated quantities.", "topic_tags": []}
        self.assertEqual(select(paper), (True, True))

    def test_topic_tags_alone_can_trigger_an_expert(self):
        paper = {"title": "Opaque title", "abstract": "Opaque abstract.",
                 "topic_tags": ["kilonova"]}
        self.assertEqual(select(paper), (False, True))

    def test_case_insensitive(self):
        paper = {"title": "GAMMA-RAY BURST JET BREAK", "abstract": "", "topic_tags": []}
        self.assertEqual(select(paper), (True, False))

    def test_missing_fields_do_not_crash(self):
        self.assertEqual(select({}), (True, True))
        self.assertEqual(select({"title": None, "abstract": None}), (True, True))

    def test_agn_paper_still_gets_both(self):
        """
        An off-topic paper that slipped past relevance should not silently get
        zero expert review; relevance is the filter, not this gate.
        """
        paper = {"title": "Unification models of Active Galactic Nuclei",
                 "abstract": "We review the unified scheme.", "topic_tags": ["AGN"]}
        self.assertEqual(select(paper), (True, True))


if __name__ == "__main__":
    unittest.main(verbosity=2)
