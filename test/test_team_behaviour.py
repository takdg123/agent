#!/usr/bin/env python3
"""
Tests for the team behaviours: revision loop, peer visibility, concurrency.

Regression context: the pipeline was a straight line. The critic scored once and
was never acted on, and a score BELOW 6.0 skipped the writer entirely, so the
weakest analyses got the least attention.
"""

import sys
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.harness.base import AgentCapability, AgentResult, AgentTask, BaseAgent
from src.harness.coordinator import AgentCoordinator
from src.harness.expert_harness import (
    MAX_REVISIONS, REVISION_THRESHOLD, ExpertHarness,
)

PAPER = {"title": "A GRB afterglow study", "abstract": "We model an afterglow.",
         "topic_tags": ["GRB"]}


# ---------------------------------------------------------------- coordinator

class FakeAgent(BaseAgent):
    """Records concurrency so we can prove tasks overlap (or do not)."""

    tracker_lock = threading.Lock()

    def __init__(self, agent_id, model, task_type, tracker, delay=0.05):
        super().__init__(agent_id, None)
        self.model = model
        self.task_type = task_type
        self.tracker = tracker
        self.delay = delay
        self.capabilities = [AgentCapability.TEXT_ANALYSIS]

    def can_handle(self, task):
        return task.task_type == self.task_type

    def execute(self, task):
        with self.tracker_lock:
            self.tracker["current"] += 1
            self.tracker["peak"] = max(self.tracker["peak"], self.tracker["current"])
            self.tracker.setdefault("per_model", {})
            self.tracker["per_model"][self.model] = \
                self.tracker["per_model"].get(self.model, 0) + 1
            self.tracker["peak_per_model"] = max(
                self.tracker.get("peak_per_model", 0),
                self.tracker["per_model"][self.model])
        time.sleep(self.delay)
        with self.tracker_lock:
            self.tracker["current"] -= 1
            self.tracker["per_model"][self.model] -= 1
        return AgentResult(task_id=task.task_id, agent_id=self.agent_id,
                           success=True, output_data={"ok": True})


def task_for(task_type, priority=5):
    return AgentTask(task_type=task_type, input_data={},
                     required_capabilities=[AgentCapability.TEXT_ANALYSIS],
                     priority=priority)


class TestCoordinatorConcurrency(unittest.TestCase):
    def test_different_models_run_concurrently(self):
        """Previously a sequential while-loop, so unrelated models waited."""
        tracker = {"current": 0, "peak": 0}
        coordinator = AgentCoordinator(None)
        coordinator.register_agent(FakeAgent("a", "model-a", "type_a", tracker))
        coordinator.register_agent(FakeAgent("b", "model-b", "type_b", tracker))

        coordinator.submit_task(task_for("type_a"))
        coordinator.submit_task(task_for("type_b"))
        results = coordinator.execute_all_tasks()

        self.assertEqual(len(results), 2)
        self.assertEqual(tracker["peak"], 2, "tasks on different models did not overlap")

    def test_same_model_is_serialised(self):
        """One 42GB model cannot serve two generations at once."""
        tracker = {"current": 0, "peak": 0}
        coordinator = AgentCoordinator(None)
        coordinator.register_agent(FakeAgent("a", "shared", "type_a", tracker))
        coordinator.register_agent(FakeAgent("b", "shared", "type_b", tracker))

        coordinator.submit_task(task_for("type_a"))
        coordinator.submit_task(task_for("type_b"))
        coordinator.execute_all_tasks()

        self.assertEqual(tracker["peak_per_model"], 1,
                         "two calls hit the same model simultaneously")

    def test_results_returned_for_every_task(self):
        tracker = {"current": 0, "peak": 0}
        coordinator = AgentCoordinator(None)
        coordinator.register_agent(FakeAgent("a", "m", "type_a", tracker, delay=0.01))
        for _ in range(5):
            coordinator.submit_task(task_for("type_a"))
        self.assertEqual(len(coordinator.execute_all_tasks()), 5)

    def test_queue_is_emptied(self):
        tracker = {"current": 0, "peak": 0}
        coordinator = AgentCoordinator(None)
        coordinator.register_agent(FakeAgent("a", "m", "type_a", tracker, delay=0.01))
        coordinator.submit_task(task_for("type_a"))
        coordinator.execute_all_tasks()
        self.assertTrue(coordinator.task_queue.empty())
        self.assertEqual(coordinator.execute_all_tasks(), [])

    def test_unhandled_task_reports_failure(self):
        coordinator = AgentCoordinator(None)
        coordinator.submit_task(task_for("nobody_handles_this"))
        results = coordinator.execute_all_tasks()
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].success)


# ------------------------------------------------------------- revision loop

class HarnessStub(ExpertHarness):
    """ExpertHarness with agent construction and task execution replaced."""

    def __init__(self, script):
        self.script = script          # task_type -> list of (output_data, success)
        self.calls = []
        self.config = None

    def _run_one(self, task):
        self.calls.append(task.task_type)
        queue = self.script.get(task.task_type, [])
        output, success = queue.pop(0) if queue else ({}, False)
        return AgentResult(task_id=task.task_id, agent_id="stub",
                           success=success, output_data=output)


class TestRevisionLoop(unittest.TestCase):
    def test_good_score_needs_no_revision(self):
        harness = HarnessStub({
            "quality_review": [({"critique": "solid", "quality_score": 8.5}, True)],
        })
        analysis, score, critique = harness._critique_and_revise(PAPER, "draft")
        self.assertEqual(analysis, "draft")
        self.assertEqual(score, 8.5)
        self.assertEqual(harness.calls.count("revise"), 0)

    def test_low_score_triggers_revision(self):
        harness = HarnessStub({
            "quality_review": [({"critique": "thin on methods", "quality_score": 5.0}, True),
                               ({"critique": "better", "quality_score": 8.0}, True)],
            "revise": [({"synthesis": "revised draft"}, True)],
        })
        analysis, score, _ = harness._critique_and_revise(PAPER, "draft")
        self.assertEqual(analysis, "revised draft")
        self.assertEqual(score, 8.0)
        self.assertEqual(harness.calls.count("revise"), 1)

    def test_revision_carries_the_critique(self):
        captured = {}

        class Capturing(HarnessStub):
            def _run_one(self, task):
                if task.task_type == "revise":
                    captured.update(task.input_data)
                return super()._run_one(task)

        harness = Capturing({
            "quality_review": [({"critique": "missing the jet break", "quality_score": 4.0}, True),
                               ({"critique": "ok", "quality_score": 9.0}, True)],
            "revise": [({"synthesis": "revised"}, True)],
        })
        harness._critique_and_revise(PAPER, "draft")
        self.assertEqual(captured["critique"], "missing the jet break")
        self.assertEqual(captured["analysis"], "draft")

    def test_revision_capped(self):
        harness = HarnessStub({
            "quality_review": [({"critique": "bad", "quality_score": 3.0}, True)] * 5,
            "revise": [({"synthesis": f"v{i}"}, True) for i in range(5)],
        })
        harness._critique_and_revise(PAPER, "draft")
        self.assertEqual(harness.calls.count("revise"), MAX_REVISIONS)

    def test_best_version_wins_when_revision_makes_it_worse(self):
        """A revision that scores lower must be discarded, not shipped."""
        harness = HarnessStub({
            "quality_review": [({"critique": "meh", "quality_score": 6.0}, True),
                               ({"critique": "worse", "quality_score": 4.0}, True),
                               ({"critique": "worse still", "quality_score": 3.0}, True)],
            "revise": [({"synthesis": "worse draft"}, True),
                       ({"synthesis": "worst draft"}, True)],
        })
        analysis, score, _ = harness._critique_and_revise(PAPER, "draft")
        self.assertEqual(analysis, "draft")
        self.assertEqual(score, 6.0)

    def test_failed_revision_keeps_current_version(self):
        harness = HarnessStub({
            "quality_review": [({"critique": "bad", "quality_score": 4.0}, True)],
            "revise": [({}, False)],
        })
        analysis, score, _ = harness._critique_and_revise(PAPER, "draft")
        self.assertEqual(analysis, "draft")
        self.assertEqual(score, 4.0)

    def test_failed_critic_does_not_block_the_paper(self):
        harness = HarnessStub({"quality_review": [({}, False)]})
        analysis, score, _ = harness._critique_and_revise(PAPER, "draft")
        self.assertEqual(analysis, "draft")
        self.assertIsNotNone(score)

    def test_threshold_boundary_accepts(self):
        harness = HarnessStub({
            "quality_review": [({"critique": "ok", "quality_score": REVISION_THRESHOLD}, True)],
        })
        harness._critique_and_revise(PAPER, "draft")
        self.assertEqual(harness.calls.count("revise"), 0)


# ------------------------------------------------------------- peer visibility

class TestPeerVisibility(unittest.TestCase):
    def test_stronger_specialist_writes_first(self):
        grb = {"title": "GRB afterglow jet break prompt emission", "abstract": "",
               "topic_tags": ["GRB"]}
        self.assertEqual(ExpertHarness.expert_order(grb, True, True)[0][0], "grb_review")

        kn = {"title": "Kilonova r-process AT2017gfo neutron star merger",
              "abstract": "", "topic_tags": ["kilonova"]}
        self.assertEqual(ExpertHarness.expert_order(kn, True, True)[0][0], "kilonova_review")

    def test_only_selected_experts_are_ordered(self):
        self.assertEqual(ExpertHarness.expert_order(PAPER, True, False),
                         [("grb_review", "GRB Expert")])
        self.assertEqual(ExpertHarness.expert_order(PAPER, False, False), [])

    def test_peer_lines_name_the_author_and_carry_content(self):
        lines = ExpertHarness._peer_lines([
            {"expertise": "Gamma-Ray Bursts (GRBs)",
             "expert_review": "The jet break constrains the opening angle."}
        ])
        self.assertEqual(len(lines), 1)
        self.assertIn("Gamma-Ray Bursts", lines[0])
        self.assertIn("opening angle", lines[0])

    def test_no_peer_lines_when_first_to_review(self):
        self.assertEqual(ExpertHarness._peer_lines([]), [])

    def test_peer_review_reaches_the_second_expert(self):
        from src.harness.expert_agents import KilonovaExpertAgent

        class StubConfig:
            root_dir = Path(__file__).parent.parent
            ollama_model = astro_expert_model = general_model = language_model = "stub"

        with patch("src.utils.llm_client.LLMClient.require_model", side_effect=lambda n: n):
            agent = KilonovaExpertAgent("kn", StubConfig(), None)

        captured = {}

        def fake(prompt, *a, **k):
            captured["prompt"] = prompt
            return "a review"

        peer = ExpertHarness._peer_lines([
            {"expertise": "Gamma-Ray Bursts (GRBs)", "expert_review": "Jet break at 2 days."}
        ])
        with patch.object(type(agent.llm_client), "generate", side_effect=fake):
            agent.execute(AgentTask(
                task_type="kilonova_review",
                input_data={"paper": PAPER, "previous_analysis": peer},
                required_capabilities=[AgentCapability.TEXT_ANALYSIS],
            ))
        self.assertIn("Jet break at 2 days", captured["prompt"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
