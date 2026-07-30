#!/usr/bin/env python3
"""
Tests that an LLM failure inside an expert agent is reported as a failure.

Regression context: the GRB and kilonova experts reported success=True in 0.00s
while their "review" was the string "Error: HTTP 404". The harness appended that
string to expert_reviews and stored it in memory for 53 papers.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.harness.base import AgentCapability, AgentTask
from src.harness.expert_agents import (
    AstrophysicistAgent,
    GRBExpertAgent,
    KilonovaExpertAgent,
)
from src.utils.llm_client import LLMError

PAPER = {
    "title": "A Bright Kilonova Following GRB 240710A",
    "authors": ["A. Author", "B. Author"],
    "abstract": "We report observations of a kilonova.",
}


class StubConfig:
    root_dir = Path(__file__).parent.parent
    ollama_model = "stub-model"
    astro_expert_model = "stub-astro"
    general_model = "stub-general"
    language_model = "stub-language"


def _task(task_type, capability, **input_data):
    return AgentTask(
        task_type=task_type,
        description="test",
        input_data={"paper": PAPER, **input_data},
        required_capabilities=[capability],
    )


class TestExpertFailurePropagation(unittest.TestCase):
    """A dead model must produce success=False, not a prose-shaped error."""

    def setUp(self):
        # require_model is patched so agents construct without a live Ollama.
        patcher = patch("src.utils.llm_client.LLMClient.require_model", side_effect=lambda n: n)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _assert_failure(self, agent_cls, task):
        agent = agent_cls("test_agent", StubConfig(), None)
        with patch.object(
            type(agent.llm_client), "generate",
            side_effect=LLMError("HTTP 404 for model 'stub-astro': model not found"),
        ):
            result = agent.execute(task)

        self.assertFalse(result.success, "a 404 from the model must not count as success")
        self.assertIn("404", result.error_message or "")
        # The failure must not masquerade as content anywhere in the output.
        self.assertNotIn("expert_review", result.output_data)
        self.assertNotIn("synthesis", result.output_data)

    def test_grb_expert_reports_failure(self):
        self._assert_failure(
            GRBExpertAgent,
            _task("expert_review", AgentCapability.TEXT_ANALYSIS, previous_analysis=""),
        )

    def test_kilonova_expert_reports_failure(self):
        self._assert_failure(
            KilonovaExpertAgent,
            _task("expert_review", AgentCapability.TEXT_ANALYSIS, previous_analysis=""),
        )

    def test_astrophysicist_reports_failure(self):
        self._assert_failure(
            AstrophysicistAgent,
            _task("synthesize", AgentCapability.SYNTHESIS, expert_reviews=[]),
        )

    def test_failure_counted_in_stats(self):
        agent = GRBExpertAgent("test_agent", StubConfig(), None)
        with patch.object(
            type(agent.llm_client), "generate", side_effect=LLMError("boom")
        ):
            agent.execute(_task("expert_review", AgentCapability.TEXT_ANALYSIS, previous_analysis=""))
        self.assertEqual(agent.get_stats()["failure_count"], 1)
        self.assertEqual(agent.get_stats()["success_count"], 0)


class TestStartupModelValidation(unittest.TestCase):
    def test_missing_model_fails_at_construction(self):
        """Fail once at startup, not silently on every paper."""
        with patch(
            "src.utils.llm_client.LLMClient.require_model",
            side_effect=LLMError("configured model 'astrosage:70b-q4_K_M' is not installed"),
        ):
            with self.assertRaises(LLMError):
                GRBExpertAgent("test_agent", StubConfig(), None)


class TestPreviousAnalysisFormatting(unittest.TestCase):
    def test_list_context_is_rendered_as_text(self):
        """
        The harness passes context['previous_insights'], which is a list. It used
        to be f-string interpolated into the prompt as "['- foo...', '- bar...']".
        """
        with patch("src.utils.llm_client.LLMClient.require_model", side_effect=lambda n: n):
            agent = GRBExpertAgent("test_agent", StubConfig(), None)
            captured = {}

            def fake_generate(prompt, *args, **kwargs):
                captured["prompt"] = prompt
                return "a review"

            with patch.object(type(agent.llm_client), "generate", side_effect=fake_generate):
                agent.execute(
                    _task(
                        "expert_review",
                        AgentCapability.TEXT_ANALYSIS,
                        previous_analysis=["- Paper A: finding one", "- Paper B: finding two"],
                    )
                )

        prompt = captured["prompt"]
        self.assertIn("Paper A: finding one", prompt)
        self.assertNotIn("['", prompt, "list repr leaked into the prompt")


if __name__ == "__main__":
    unittest.main(verbosity=2)
