#!/usr/bin/env python3
"""
Tests for relevance scoring.

Regression context: PaperFilter returned only 2.0/1.0/0.0, so any paper
containing "grb" scored maximal. Recent reports included AGN unification models,
a blazar QPO, a BBH waveform surrogate, and warm dark matter cosmology.
"""

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.llm_client import LLMError
from src.utils.relevance import RelevanceScorer, load_profile

ON_TOPIC = {"title": "Revealing the Structure and Magnetization of GRB Jets with ALMA Polarization",
            "abstract": "We present polarization observations constraining jet magnetization.",
            "arxiv_id": "1"}
OFF_TOPIC = {"title": "Unification models of Active Galactic Nuclei",
             "abstract": "We review the unified scheme for AGN.",
             "arxiv_id": "2"}
BORDERLINE = {"title": "Tightening Bounds on Warm Dark Matter with High-Redshift GRBs",
              "abstract": "We use 118 Swift GRBs to constrain the WDM particle mass.",
              "arxiv_id": "3"}

PROFILE = {
    "profile": "GRB and kilonova physics.",
    "core": ["GRB jets", "kilonovae"],
    "exclude": ["AGN", "dark matter constraints"],
    "threshold": 6.0,
    "max_triage": 15,
}

# Deliberate: the off-topic and borderline papers are scored below threshold,
# matching what we want the real triage model to do.
TRIAGE = {
    "1": {"score": 9.2, "topic_tags": ["GRB", "jets"], "why_it_matters": "Constrains jet magnetization directly."},
    "2": {"score": 0.5, "topic_tags": ["AGN"], "why_it_matters": "AGN unification is an excluded topic."},
    "3": {"score": 3.5, "topic_tags": ["cosmology"], "why_it_matters": "Uses GRBs as a tool to constrain dark matter."},
}


class StubLLM:
    """Embeddings keyed on crude keyword presence; triage from the table above."""

    def __init__(self):
        self.embed_calls = 0
        self.generate_calls = 0

    def embed(self, text, model="nomic-embed-text", timeout=None, **kwargs):
        self.embed_calls += 1
        low = text.lower()
        return [
            1.0 if "grb" in low or "kilonova" in low else 0.0,
            1.0 if "agn" in low or "nuclei" in low else 0.0,
            1.0 if "dark matter" in low else 0.0,
        ]

    def generate(self, prompt, model=None, format=None, timeout=None, **kwargs):
        self.generate_calls += 1
        # Identify the paper by its title appearing in the prompt.
        for paper, arxiv_id in ((ON_TOPIC, "1"), (OFF_TOPIC, "2"), (BORDERLINE, "3")):
            if paper["title"][:30] in prompt:
                return json.dumps(TRIAGE[arxiv_id])
        return json.dumps({"score": 5.0, "topic_tags": [], "why_it_matters": "unknown"})


def scorer(tmp: Path, llm=None):
    return RelevanceScorer(llm or StubLLM(), PROFILE, cache_dir=tmp)


class TestProfileLoading(unittest.TestCase):
    def test_real_config_loads(self):
        profile = load_profile(Path("config/interests.yml"))
        self.assertIn("gamma-ray burst", profile["profile"].lower())
        self.assertTrue(profile["core"])
        self.assertTrue(profile["exclude"])
        self.assertIsInstance(profile["threshold"], float)

    def test_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            load_profile(Path("config/does_not_exist.yml"))


class TestRanking(unittest.TestCase):
    def setUp(self):
        self.tmp = Path("data/knowledge_test")
        self.llm = StubLLM()
        self.scorer = scorer(self.tmp, self.llm)

    def tearDown(self):
        for f in self.tmp.glob("*"):
            f.unlink()
        if self.tmp.exists():
            self.tmp.rmdir()

    def test_on_topic_ranks_above_off_topic(self):
        ranked = self.scorer.rank([OFF_TOPIC, ON_TOPIC])
        self.assertEqual(ranked[0]["arxiv_id"], "1")

    def test_rank_limits_to_max_triage(self):
        papers = [dict(ON_TOPIC, arxiv_id=str(i)) for i in range(30)]
        self.assertEqual(len(self.scorer.rank(papers)), PROFILE["max_triage"])

    def test_profile_embedding_is_cached_across_instances(self):
        self.scorer.rank([ON_TOPIC])
        first = self.llm.embed_calls
        scorer(self.tmp, self.llm).rank([ON_TOPIC])
        # One embed per paper on the second pass, none for the profile.
        self.assertEqual(self.llm.embed_calls, first + 1)

    def test_embedding_failure_falls_back_to_all_papers(self):
        class DeadEmbedder(StubLLM):
            def embed(self, *a, **k):
                raise LLMError("embeddings unavailable")

        ranked = scorer(self.tmp, DeadEmbedder()).rank([OFF_TOPIC, ON_TOPIC])
        self.assertEqual(len(ranked), 2, "must not silently drop papers")


class TestTriage(unittest.TestCase):
    def setUp(self):
        self.tmp = Path("data/knowledge_test2")
        self.scorer = scorer(self.tmp)

    def tearDown(self):
        for f in self.tmp.glob("*"):
            f.unlink()
        if self.tmp.exists():
            self.tmp.rmdir()

    def test_excluded_topic_scored_below_threshold(self):
        result = self.scorer.triage(OFF_TOPIC)
        self.assertLess(result["score"], PROFILE["threshold"])
        self.assertIn("excluded", result["why_it_matters"].lower())

    def test_tool_use_paper_scored_below_threshold(self):
        self.assertLess(self.scorer.triage(BORDERLINE)["score"], PROFILE["threshold"])

    def test_on_topic_scored_above_threshold(self):
        result = self.scorer.triage(ON_TOPIC)
        self.assertGreaterEqual(result["score"], PROFILE["threshold"])
        self.assertIn("GRB", result["topic_tags"])

    def test_malformed_json_does_not_crash(self):
        class Babbler(StubLLM):
            def generate(self, *a, **k):
                return "Sure! Here is my assessment: the paper is quite good."

        result = scorer(self.tmp, Babbler()).triage(ON_TOPIC)
        self.assertIsNone(result["score"], "an unparseable verdict must not fake a score")

    def test_json_embedded_in_prose_is_recovered(self):
        class Chatty(StubLLM):
            def generate(self, *a, **k):
                return ('Here you go:\n{"score": 8.5, "topic_tags": ["GRB"], '
                        '"why_it_matters": "Direct jet physics."}\nHope that helps!')

        self.assertEqual(scorer(self.tmp, Chatty()).triage(ON_TOPIC)["score"], 8.5)

    def test_score_clamped_to_range(self):
        class Overshooter(StubLLM):
            def generate(self, *a, **k):
                return json.dumps({"score": 42, "topic_tags": [], "why_it_matters": "x"})

        self.assertLessEqual(scorer(self.tmp, Overshooter()).triage(ON_TOPIC)["score"], 10)


class TestSelectPapers(unittest.TestCase):
    def setUp(self):
        self.tmp = Path("data/knowledge_test3")
        self.scorer = scorer(self.tmp)

    def tearDown(self):
        for f in self.tmp.glob("*"):
            f.unlink()
        if self.tmp.exists():
            self.tmp.rmdir()

    def test_only_relevant_papers_kept_and_sorted(self):
        kept = self.scorer.select([OFF_TOPIC, BORDERLINE, ON_TOPIC])
        self.assertEqual([p["arxiv_id"] for p in kept], ["1"])

    def test_kept_papers_carry_score_and_reason(self):
        kept = self.scorer.select([ON_TOPIC])
        self.assertAlmostEqual(kept[0]["relevance_score"], 9.2)
        self.assertIn("magnetization", kept[0]["why_it_matters"])
        self.assertIn("GRB", kept[0]["topic_tags"])

    def test_unscoreable_paper_is_kept_for_review(self):
        """A triage failure must not silently hide a paper."""
        class Babbler(StubLLM):
            def generate(self, *a, **k):
                return "no json here"

        kept = scorer(self.tmp, Babbler()).select([ON_TOPIC])
        self.assertEqual(len(kept), 1)
        self.assertIsNone(kept[0]["relevance_score"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
