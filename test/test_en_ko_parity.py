#!/usr/bin/env python3
"""
Tests that English and Korean say the same thing.

Regression context: the pipeline ran synthesis -> translate -> critic -> writer,
so the writer rewrote the English *after* Korean had been derived from the
pre-polish draft. The Korean prompt also asked for an independent 150-200
character summary rather than a translation. Reports leaked "(194자)" into the
body and rendered "black hole" as 흑점 (sunspot).
"""

import re
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.harness.base import AgentCapability, AgentTask
from src.harness.expert_agents import CriticAgent, LanguageExpertAgent, WriterAgent
from src.utils.html_report_generator import HTMLReportGenerator as G

PROMPTS = Path("prompts")

PAPER = {
    "title": "A Bright Kilonova",
    "abstract": "An abstract that must not drive the Korean text.",
    "contents": {"abstract": "An abstract.", "introduction": "Intro.",
                 "methods": "Methods.", "results": "Results with 0.05 Msun.",
                 "conclusions": "Conclusions.", "source": "pdf"},
}


class StubConfig:
    root_dir = Path(__file__).parent.parent
    ollama_model = "stub"
    astro_expert_model = "stub"
    general_model = "stub"
    language_model = "stub"


def build(agent_cls):
    with patch("src.utils.llm_client.LLMClient.require_model", side_effect=lambda n: n):
        return agent_cls("test", StubConfig(), None)


def capture_prompt(agent, task):
    captured = {}

    def fake_generate(prompt, *args, **kwargs):
        captured.setdefault("prompt", prompt)
        # Must pass the Korean script check, or the translator retries and the
        # captured prompt would be a retry rather than the first call.
        return "이것은 한국어 번역입니다. 감마선 폭발과 킬로노바를 다룹니다."

    with patch.object(type(agent.llm_client), "generate", side_effect=fake_generate):
        agent.execute(task)
    return captured["prompt"]


class TestTranslationPromptIsATranslation(unittest.TestCase):
    def setUp(self):
        self.text = (PROMPTS / "language_expert.txt").read_text(encoding="utf-8")

    def test_no_character_count_target(self):
        """The 150-200자 target is what produced the '(194자)' artifacts."""
        self.assertNotIn("150-200", self.text)
        self.assertIsNone(re.search(r"\d+\s*-\s*\d+\s*자", self.text))

    def test_forbids_emitting_a_character_count(self):
        self.assertIn("(194자)", self.text)  # the explicit prohibition example
        self.assertIn("글자 수를 세지 마십시오", self.text)

    def test_does_not_ask_for_an_independent_summary(self):
        self.assertNotIn("맞춤형 요약", self.text)
        self.assertIn("요약이 아니라 번역", self.text)

    def test_prompt_is_scoped_to_one_paragraph(self):
        """
        Parity is enforced in code (one call per paragraph), not requested in the
        prompt — see TestKoreanScriptCheck.test_paragraph_count_is_preserved.
        """
        self.assertIn("문단 하나를 한국어 한 문단으로", self.text)
        self.assertIn("주어진 문단 전체를 번역", self.text)

    def test_instructions_are_korean_anchored(self):
        """
        English instructions on a long English source made Qwen answer in
        Chinese. Anchoring the whole prompt in Korean fixed it.
        """
        hangul = len(re.findall(r"[가-힣]", self.text))
        self.assertGreater(hangul, 200, "prompt must be written in Korean")
        self.assertIn("중국어", self.text)  # Chinese explicitly forbidden

    def test_glossary_fixes_the_observed_mistranslations(self):
        self.assertIn("블랙홀", self.text)
        self.assertIn("흑점", self.text)      # named as forbidden
        self.assertIn("흑홀", self.text)      # named as forbidden
        self.assertIn("강착원반", self.text)
        self.assertIn("콤프턴 산란", self.text)

    def test_takes_only_title_and_english(self):
        fields = set(re.findall(r"\{(\w+)\}", self.text))
        self.assertEqual(fields, {"title", "english_analysis"})
        self.assertNotIn("abstract", fields,
                         "the Korean must come from the English, not the abstract")


class TestWriterProducesEnglishOnly(unittest.TestCase):
    def setUp(self):
        self.text = (PROMPTS / "writer.txt").read_text(encoding="utf-8")

    def test_no_korean_requested(self):
        self.assertNotIn("한국어 요약", self.text)
        self.assertIn("English only", self.text)

    def test_no_bilingual_output_format(self):
        # The old format required a regex to recover each language.
        self.assertNotIn("**English Analysis:**", self.text)

    def test_takes_no_korean_input(self):
        fields = set(re.findall(r"\{(\w+)\}", self.text))
        self.assertEqual(fields, {"title", "analysis", "critique"})


class TestAgentsMatchTheirPrompts(unittest.TestCase):
    """Prompt placeholders and agent kwargs must not drift apart."""

    def test_language_agent_sends_full_english_untruncated(self):
        agent = build(LanguageExpertAgent)
        long_english = "Paragraph one. " * 200  # ~3000 chars, over the old 1500 cap
        prompt = capture_prompt(agent, AgentTask(
            task_type="korean_summary",
            input_data={"paper": PAPER, "english_analysis": long_english},
            required_capabilities=[AgentCapability.SUMMARIZATION],
        ))
        self.assertIn(long_english.strip()[-40:], prompt,
                      "the tail of the English was cut before translation")
        self.assertNotIn("must not drive the Korean", prompt,
                         "abstract leaked into the translation prompt")

    def test_critic_reads_paper_contents(self):
        agent = build(CriticAgent)
        prompt = capture_prompt(agent, AgentTask(
            task_type="quality_review",
            input_data={"paper": PAPER, "analysis": "An analysis."},
            required_capabilities=[AgentCapability.COMPARISON],
        ))
        self.assertIn("0.05 Msun", prompt)
        self.assertNotIn("{contents}", prompt)

    def test_writer_prompt_renders_without_korean(self):
        agent = build(WriterAgent)
        prompt = capture_prompt(agent, AgentTask(
            task_type="polish",
            input_data={"paper": PAPER, "analysis": "Draft.", "critique": "Fine."},
            required_capabilities=[AgentCapability.SYNTHESIS],
        ))
        self.assertIn("Draft.", prompt)
        self.assertIn("Fine.", prompt)
        self.assertIsNone(re.search(r"\{\w+\}", prompt),
                          "an unfilled placeholder is left in the prompt")


class TestRenderedParity(unittest.TestCase):
    """Both languages must reach the report with the same numbers."""

    def test_numbers_survive_into_both_languages(self):
        english = "The ejecta mass is 0.05 Msun at z = 0.16."
        korean = "분출물 질량은 z = 0.16에서 0.05 Msun입니다."
        html = G.generate_full_report([{
            "paper": PAPER,
            "analysis": {"english": english, "korean": korean, "quality_score": 8.0},
        }])
        for number in ("0.05", "0.16"):
            self.assertEqual(html.count(number), 2, f"{number} must appear in both")

    def test_character_count_artifact_would_be_visible(self):
        """Guards the test itself: a leaked count is not silently swallowed."""
        html = G.generate_full_report([{
            "paper": PAPER,
            "analysis": {"english": "Analysis.", "korean": "요약입니다. (194자)"},
        }])
        self.assertIn("(194자)", html)


class TestKoreanScriptCheck(unittest.TestCase):
    """
    A smoke run returned an entire analysis in Chinese, with Chinese commentary
    about the translation, because Qwen drifted on a long English source.
    """

    def test_clean_korean_accepted(self):
        text = ("이 논문은 감마선 폭발과 초신성의 연관성을 다룹니다. "
                "분출물 질량은 0.05 Msun이며 Swift 관측을 사용했습니다.")
        self.assertEqual(LanguageExpertAgent.script_problem(text), "")

    def test_chinese_output_rejected(self):
        text = ("这项研究解决了相对论性喷流和超新星抛射物之间相互作用的关键方面，"
                "提出了一种统一模型来解释非热和热成分。")
        self.assertIn("Chinese", LanguageExpertAgent.script_problem(text))

    def test_mixed_drift_rejected(self):
        """The real failure began in Korean and then switched to Chinese."""
        text = ("이 논문은 긴 감마선 폭발과 광대 " +
                "谱之外的内容被省略了因为翻译需要保持与原文的一致性并且不能包含任何未在英文中出现的信息" * 2)
        self.assertIn("Chinese", LanguageExpertAgent.script_problem(text))

    def test_english_passthrough_rejected(self):
        text = "This analysis reviews the connection between jets and supernova ejecta."
        self.assertIn("Hangul", LanguageExpertAgent.script_problem(text))

    def test_empty_rejected(self):
        self.assertIn("empty", LanguageExpertAgent.script_problem(""))

    def test_stray_han_tolerated(self):
        # One or two ideographs (e.g. a quoted term) must not fail the run.
        text = "이 논문은 감마선 폭발을 다룹니다. 분출물 질량은 0.05 Msun입니다. 光"
        self.assertEqual(LanguageExpertAgent.script_problem(text), "")

    def test_retry_then_success(self):
        agent = build(LanguageExpertAgent)
        good = "이 논문은 감마선 폭발과 초신성의 연관성을 다룹니다. 분출물 질량은 0.05 Msun입니다."
        replies = iter(["这是中文的翻译，完全不是韩语，应该被拒绝。" * 3, good])

        with patch.object(type(agent.llm_client), "generate",
                          side_effect=lambda *a, **k: next(replies)):
            self.assertEqual(agent.translate(lambda p: p, "one paragraph"), good)

    def test_paragraph_count_is_preserved(self):
        """Translating per paragraph makes parity structural, not a request."""
        agent = build(LanguageExpertAgent)
        english = "First para.\n\nSecond para.\n\nThird para."
        with patch.object(type(agent.llm_client), "generate",
                          side_effect=lambda *a, **k: "이것은 한국어 문단입니다. 감마선 폭발."):
            korean = agent.translate(lambda p: p, english)
        self.assertEqual(len(re.split(r"\n\s*\n", korean)), 3)

    def test_each_paragraph_sent_separately(self):
        agent = build(LanguageExpertAgent)
        seen = []

        def fake(prompt, *a, **k):
            seen.append(prompt)
            return "이것은 한국어 문단입니다. 감마선 폭발."

        with patch.object(type(agent.llm_client), "generate", side_effect=fake):
            agent.translate(lambda p: p, "Alpha para.\n\nBeta para.")
        self.assertEqual(len(seen), 2)
        self.assertIn("Alpha para.", seen[0])
        self.assertNotIn("Beta para.", seen[0])

    def test_one_bad_paragraph_keeps_the_others_and_the_slot(self):
        agent = build(LanguageExpertAgent)
        good = "이것은 한국어 문단입니다. 감마선 폭발."
        calls = {"n": 0}

        def fake(prompt, *a, **k):
            calls["n"] += 1
            # The second paragraph fails all three attempts (calls 2, 3, 4).
            return "这是中文" * 20 if 2 <= calls["n"] <= 4 else good

        with patch.object(type(agent.llm_client), "generate", side_effect=fake):
            korean = agent.translate(lambda p: p, "A.\n\nB.\n\nC.")
        parts = re.split(r"\n\s*\n", korean)
        self.assertEqual(len(parts), 3)
        self.assertIn("[번역 실패]", parts[1])
        self.assertIn("감마선", parts[0])
        self.assertIn("감마선", parts[2])

    def test_transport_failure_on_one_paragraph_keeps_the_rest(self):
        """A 180s timeout on paragraph 1 used to discard the whole translation."""
        from src.utils.llm_client import LLMError
        agent = build(LanguageExpertAgent)
        good = "이것은 한국어 문단입니다. 감마선 폭발."
        calls = {"n": 0}

        def fake(prompt, *a, **k):
            calls["n"] += 1
            if calls["n"] <= 3:          # paragraph 1 times out on every attempt
                raise LLMError("timeout after 420s for model 'qwen2.5:32b'")
            return good

        with patch.object(type(agent.llm_client), "generate", side_effect=fake):
            korean = agent.translate(lambda p: p, "A.\n\nB.")
        parts = re.split(r"\n\s*\n", korean)
        self.assertEqual(len(parts), 2)
        self.assertIn("[번역 실패]", parts[0])
        self.assertIn("감마선", parts[1])

    def test_prompt_does_not_contain_chinese_glyphs(self):
        """Naming the forbidden script in that script appeared to prime it."""
        text = (PROMPTS / "language_expert.txt").read_text(encoding="utf-8")
        self.assertEqual(re.findall(r"[一-鿿]", text), [])

    def test_persistent_chinese_fails_the_task(self):
        """All paragraphs failing must fail the task, not publish Chinese."""
        agent = build(LanguageExpertAgent)
        with patch.object(type(agent.llm_client), "generate",
                          side_effect=lambda *a, **k: "这是中文的翻译，完全不是韩语。" * 5):
            result = agent.execute(AgentTask(
                task_type="korean_summary",
                input_data={"paper": PAPER, "english_analysis": "Some analysis."},
                required_capabilities=[AgentCapability.SUMMARIZATION],
            ))
        self.assertFalse(result.success)
        self.assertNotIn("korean_summary", result.output_data)


class TestExpertRouting(unittest.TestCase):
    """
    Both experts declared can_handle for "expert_review", and the coordinator
    returns the first match — so grb_expert ran twice and the kilonova expert
    never ran at all.
    """

    def setUp(self):
        from src.harness.expert_agents import GRBExpertAgent, KilonovaExpertAgent
        self.grb = build(GRBExpertAgent)
        self.kn = build(KilonovaExpertAgent)

    def _task(self, task_type):
        return AgentTask(task_type=task_type, input_data={"paper": PAPER},
                         required_capabilities=[AgentCapability.TEXT_ANALYSIS])

    def test_grb_task_only_handled_by_grb_expert(self):
        self.assertTrue(self.grb.can_handle(self._task("grb_review")))
        self.assertFalse(self.kn.can_handle(self._task("grb_review")))

    def test_kilonova_task_only_handled_by_kilonova_expert(self):
        self.assertTrue(self.kn.can_handle(self._task("kilonova_review")))
        self.assertFalse(self.grb.can_handle(self._task("kilonova_review")))

    def test_shared_type_no_longer_matches_either(self):
        self.assertFalse(self.grb.can_handle(self._task("expert_review")))
        self.assertFalse(self.kn.can_handle(self._task("expert_review")))

    def test_harness_submits_distinct_types(self):
        source = Path("src/harness/expert_harness.py").read_text()
        self.assertIn('task_type="grb_review"', source)
        self.assertIn('task_type="kilonova_review"', source)


class TestTranslationEscalation(unittest.TestCase):
    """
    Qwen drifts into Chinese stochastically; one observed retry returned 3986
    Chinese characters. Retries tighten sampling, then fall back to sentences.
    """

    def test_temperature_tightens_on_each_retry(self):
        agent = build(LanguageExpertAgent)
        temps = []
        good = "이것은 한국어 문단입니다. 감마선 폭발."

        def fake(prompt, *a, **k):
            temps.append(k.get("options", {}).get("temperature"))
            return "这是中文" * 30 if len(temps) < 3 else good

        with patch.object(type(agent.llm_client), "generate", side_effect=fake):
            agent.translate(lambda p: p, "One paragraph.")
        self.assertEqual(temps, [0.2, 0.1, 0.05])

    def test_never_uses_ollama_default_temperature(self):
        """Default 0.8 is far too loose for translation."""
        agent = build(LanguageExpertAgent)
        seen = {}

        def fake(prompt, *a, **k):
            seen.update(k.get("options", {}))
            return "이것은 한국어 문단입니다. 감마선 폭발."

        with patch.object(type(agent.llm_client), "generate", side_effect=fake):
            agent.translate(lambda p: p, "One paragraph.")
        self.assertLessEqual(seen["temperature"], 0.2)

    def test_sentence_fallback_after_ladder_exhausted(self):
        agent = build(LanguageExpertAgent)
        calls = {"n": 0}
        good = "이것은 한국어 문장입니다."

        def fake(prompt, *a, **k):
            calls["n"] += 1
            # The three whole-paragraph attempts fail; sentences then succeed.
            return "这是中文" * 30 if calls["n"] <= 3 else good

        with patch.object(type(agent.llm_client), "generate", side_effect=fake):
            korean = agent.translate(lambda p: p, "First sentence. Second sentence.")
        self.assertEqual(korean, f"{good} {good}")
        self.assertEqual(calls["n"], 5)  # 3 paragraph attempts + 2 sentences

    def test_unsplittable_paragraph_fails_rather_than_publishing_chinese(self):
        agent = build(LanguageExpertAgent)
        with patch.object(type(agent.llm_client), "generate",
                          side_effect=lambda *a, **k: "这是中文" * 30):
            result = agent.execute(AgentTask(
                task_type="korean_summary",
                input_data={"paper": PAPER, "english_analysis": "Only one sentence."},
                required_capabilities=[AgentCapability.SUMMARIZATION],
            ))
        self.assertFalse(result.success)

    def test_mostly_failing_sentences_rejects_the_paragraph(self):
        agent = build(LanguageExpertAgent)
        calls = {"n": 0}

        def fake(prompt, *a, **k):
            calls["n"] += 1
            # Paragraph attempts fail, then only the last sentence of four works.
            return "이것은 한국어 문장입니다." if calls["n"] == 7 else "这是中文" * 30

        with patch.object(type(agent.llm_client), "generate", side_effect=fake):
            with self.assertRaises(ValueError):
                agent.translate(lambda p: p, "A one. B two. C three. D four.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
