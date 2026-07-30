#!/usr/bin/env python3
"""
Tests for KnowledgeStore: semantic recall and running topic notes.

Regression context: MemoryManager scored similarity by overlap of a flat keyword
list, so nearly every GRB paper matched every other, and it stored the string
"Error: HTTP 404" as the expert reviews for all 53 papers.
"""

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.harness.knowledge_store import KnowledgeStore
from src.utils.llm_client import LLMError


class StubLLM:
    """Embeds on a crude topic axis so similarity is predictable."""

    AXES = ("kilonova", "jet", "agn")

    def __init__(self):
        self.generate_calls = 0

    def embed(self, text, model=None, timeout=None, **kwargs):
        low = text.lower()
        return [1.0 if axis in low else 0.0 for axis in self.AXES] or [0.0]

    def generate(self, prompt, model=None, format=None, timeout=None, **kwargs):
        self.generate_calls += 1
        return "Condensed note about the field."


KILONOVA = {"arxiv_id": "1", "title": "Kilonova ejecta modelling",
            "abstract": "kilonova ejecta mass", "topic_tags": ["kilonova"]}
JET = {"arxiv_id": "2", "title": "GRB jet magnetization",
       "abstract": "jet polarization", "topic_tags": ["jet"]}
AGN = {"arxiv_id": "3", "title": "AGN unification",
       "abstract": "agn torus", "topic_tags": ["agn"]}


def analysis(text="Findings here.", tags=None, score=8.0):
    return {"english": text, "korean": "결과", "topic_tags": tags or [],
            "relevance_score": score, "key_numbers": ["0.05 Msun"]}


class StoreCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.llm = StubLLM()
        self.store = KnowledgeStore(data_dir=self.tmp, llm=self.llm)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


class TestRecording(StoreCase):
    def test_record_writes_a_line(self):
        self.assertTrue(self.store.record(KILONOVA, analysis()))
        self.assertEqual(self.store.get_statistics()["total_papers"], 1)

    def test_duplicate_is_not_stored_twice(self):
        self.store.record(KILONOVA, analysis())
        self.assertFalse(self.store.record(KILONOVA, analysis()))
        self.assertEqual(self.store.get_statistics()["total_papers"], 1)

    def test_vector_is_persisted(self):
        self.store.record(KILONOVA, analysis())
        record = json.loads(self.store.papers_file.read_text().splitlines()[0])
        self.assertTrue(record["vector"])
        self.assertEqual(record["key_numbers"], ["0.05 Msun"])

    def test_record_survives_a_dead_embedder(self):
        class Dead(StubLLM):
            def embed(self, *a, **k):
                raise LLMError("no embeddings")

        store = KnowledgeStore(data_dir=self.tmp, llm=Dead())
        self.assertTrue(store.record(KILONOVA, analysis()))
        self.assertEqual(store.get_statistics()["embedded_papers"], 0)

    def test_corrupt_line_does_not_lose_the_store(self):
        self.store.record(KILONOVA, analysis())
        with self.store.papers_file.open("a") as handle:
            handle.write("{not json\n")
        self.store.record(JET, analysis())
        self.assertEqual(self.store.get_statistics()["total_papers"], 2)


class TestRecall(StoreCase):
    def setUp(self):
        super().setUp()
        for paper in (KILONOVA, JET, AGN):
            self.store.record(paper, analysis(f"Findings for {paper['title']}."))

    def test_recalls_the_semantically_similar_paper(self):
        query = {"arxiv_id": "9", "title": "New kilonova light curves",
                 "abstract": "kilonova ejecta"}
        similar = self.store.recall(query)["similar"]
        self.assertTrue(similar)
        self.assertEqual(similar[0]["arxiv_id"], "1")

    def test_does_not_recall_unrelated_papers(self):
        query = {"arxiv_id": "9", "title": "New kilonova light curves",
                 "abstract": "kilonova ejecta"}
        recalled_ids = {s["arxiv_id"] for s in self.store.recall(query)["similar"]}
        self.assertNotIn("3", recalled_ids, "AGN paper must not be recalled")

    def test_does_not_recall_itself(self):
        similar = self.store.recall(KILONOVA)["similar"]
        self.assertNotIn("1", {s["arxiv_id"] for s in similar})

    def test_recall_limit_respected(self):
        for i in range(10):
            self.store.record({"arxiv_id": f"k{i}", "title": "kilonova study",
                               "abstract": "kilonova"}, analysis())
        similar = self.store.recall({"arxiv_id": "z", "title": "kilonova",
                                     "abstract": "kilonova"})["similar"]
        self.assertLessEqual(len(similar), 3)

    def test_empty_store_returns_no_history(self):
        empty = KnowledgeStore(data_dir=Path(tempfile.mkdtemp()), llm=self.llm)
        self.assertFalse(empty.recall(KILONOVA)["has_history"])

    def test_context_lines_carry_arxiv_id_for_checking(self):
        query = {"arxiv_id": "9", "title": "kilonova follow-up",
                 "abstract": "kilonova"}
        lines = self.store.as_context_lines(self.store.recall(query))
        self.assertTrue(lines)
        self.assertIn("(1,", lines[0])


class TestTopicNotes(StoreCase):
    def _entries(self, tags):
        return [{"paper": KILONOVA, "analysis": analysis(tags=tags)}]

    def test_note_created_per_topic(self):
        self.store.update_topic_notes(self._entries(["kilonova", "r-process"]))
        slugs = {p.stem for p in self.store.topics_dir.glob("*.md")}
        self.assertEqual(slugs, {"kilonova", "r-process"})

    def test_note_accumulates_across_runs(self):
        self.store.update_topic_notes(self._entries(["kilonova"]))
        first = (self.store.topics_dir / "kilonova.md").read_text()
        self.store.update_topic_notes(
            [{"paper": JET, "analysis": analysis("Second finding.", ["kilonova"])}]
        )
        second = (self.store.topics_dir / "kilonova.md").read_text()
        self.assertIn("Second finding", second)
        self.assertGreater(len(second), len(first) - 10)

    def test_note_is_bounded(self):
        for i in range(40):
            self.store.update_topic_notes(
                [{"paper": {"arxiv_id": str(i), "title": "T" * 200},
                  "analysis": analysis("F" * 500, ["kilonova"])}]
            )
        note = (self.store.topics_dir / "kilonova.md").read_text()
        self.assertLessEqual(len(note), 4000)

    def test_notes_are_recalled_for_matching_tags(self):
        self.store.update_topic_notes(self._entries(["kilonova"]))
        recalled = self.store.recall({"arxiv_id": "9", "title": "x",
                                      "abstract": "x", "topic_tags": ["kilonova"]})
        self.assertTrue(recalled["topic_notes"])
        self.assertEqual(recalled["topic_notes"][0]["topic"], "kilonova")

    def test_slug_is_filesystem_safe(self):
        self.store.update_topic_notes(self._entries(["GRB / afterglow physics!"]))
        names = [p.name for p in self.store.topics_dir.glob("*.md")]
        self.assertEqual(names, ["grb-afterglow-physics.md"])

    def test_note_survives_a_dead_condenser(self):
        class DeadGen(StubLLM):
            def generate(self, *a, **k):
                raise LLMError("model down")

        store = KnowledgeStore(data_dir=self.tmp, llm=DeadGen())
        for i in range(30):
            store.update_topic_notes(
                [{"paper": {"arxiv_id": str(i), "title": "T" * 200},
                  "analysis": analysis("F" * 400, ["kilonova"])}]
            )
        self.assertTrue((store.topics_dir / "kilonova.md").read_text())


class TestPruning(StoreCase):
    def test_old_records_pruned(self):
        self.store.record(KILONOVA, analysis())
        records = [json.loads(l) for l in self.store.papers_file.read_text().splitlines()]
        records[0]["date"] = "2020-01-01T00:00:00"
        self.store.papers_file.write_text(json.dumps(records[0]) + "\n")
        self.assertEqual(self.store.prune(days=365), 1)
        self.assertEqual(self.store.get_statistics()["total_papers"], 0)

    def test_recent_records_kept(self):
        self.store.record(KILONOVA, analysis())
        self.assertEqual(self.store.prune(days=365), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
