#!/usr/bin/env python3
"""
Specialized Expert Agents for Research Paper Analysis
Includes: GRB Expert, Kilonova Expert, Astrophysicist, Language Expert, Critic, Writer

Refactored to use shared LLMClient (DRY principle)
"""

import time
from typing import Dict, Any
from pathlib import Path
from .base import BaseAgent, AgentTask, AgentResult, AgentCapability
from ..utils.llm_client import LLMClient, LLMError
from ..utils.paper_filter import PaperFilter
from ..utils.prompt_loader import PromptLoader
from ..utils.paper_text import as_prompt_context
import re

class BaseExpertAgent(BaseAgent):
    """Base class for all expert agents - DRY principle"""
    
    def __init__(self, agent_id: str, config: Any, llm_manager: Any, expertise: str, model: str = None):
        super().__init__(agent_id, config)
        # Use specified model or default from config
        default_model = getattr(config, 'ollama_model', 'qwen2.5:32b') if config else 'qwen2.5:32b'
        requested = model or default_model
        self.llm_client = LLMClient(model=requested)
        # Fail here, once, rather than turning into a 404 on every paper.
        self.model = self.llm_client.require_model(requested)
        self.llm_client.model = self.model
        self.expertise = expertise
        self.capabilities = [
            AgentCapability.TEXT_ANALYSIS,
            AgentCapability.INFORMATION_EXTRACTION
        ]
        # Initialize prompt loader
        prompt_dir = Path(config.root_dir) / "prompts" if config else Path(__file__).parent.parent.parent / "prompts"
        self.prompt_loader = PromptLoader(prompt_dir)
        print(f"   💡 {expertise} using model: {self.model}")
    
    def _query_llm(self, prompt: str, format: str = None,
                   options: dict = None) -> str:
        """Shared LLM query method - uses agent's designated model"""
        return self.llm_client.generate(prompt, model=self.model, format=format,
                                        options=options)
    
    def _assess_relevance(self, paper: Dict, keywords: list) -> float:
        """Shared relevance assessment"""
        text = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()
        matches = sum(1 for kw in keywords if kw.lower() in text)
        return min(1.0, matches / max(len(keywords) // 2, 1))

    @staticmethod
    def _paper_content(paper: Dict, limit: int = 12000) -> str:
        """
        The paper text an expert should reason over.

        Prefers the extracted full-text sections attached by paper_text.extract;
        falls back to the abstract so a failed PDF still yields an analysis.
        """
        contents = paper.get("contents")
        if contents:
            context = as_prompt_context(contents)
            if context.strip():
                return context[:limit]
        return (paper.get("abstract") or "No abstract")[:limit]

    @staticmethod
    def _format_context(previous_analysis: Any) -> str:
        """
        Render recalled context as prose.

        The harness passes a list of insight lines; interpolating it directly put
        a Python list repr into the prompt.
        """
        if not previous_analysis:
            return ""
        if isinstance(previous_analysis, (list, tuple)):
            body = "\n".join(str(item) for item in previous_analysis if item)
        else:
            body = str(previous_analysis)
        if not body.strip():
            return ""
        return f"Context you may use:\n{body}"


class GRBExpertAgent(BaseExpertAgent):
    """Expert specialized in Gamma-Ray Bursts - uses AstroSage-70B"""
    
    def __init__(self, agent_id: str, config: Any, llm_manager: Any):
        # Use AstroSage model for astronomy expertise
        astro_model = getattr(config, 'astro_expert_model', 'astrosage:70b-q4_K_M') if config else 'astrosage:70b-q4_K_M'
        super().__init__(agent_id, config, llm_manager, "Gamma-Ray Bursts (GRBs)", model=astro_model)
    
    def can_handle(self, task: AgentTask) -> bool:
        # Task types must be distinct per expert: the coordinator picks the first
        # matching agent, so a shared "expert_review" type routed the kilonova
        # review to this agent and the kilonova expert never ran.
        return (set(task.required_capabilities).issubset(set(self.capabilities)) and
                task.task_type == "grb_review")

    def execute(self, task: AgentTask) -> AgentResult:
        start_time = time.time()
        task.start()
        
        try:
            paper = task.input_data.get("paper", {})
            previous_analysis = task.input_data.get("previous_analysis", "")
            
            prompt = self.prompt_loader.get_grb_expert_prompt(
                title=paper.get('title', 'Unknown'),
                authors=', '.join(paper.get('authors', [])[:5]),
                contents=self._paper_content(paper),
                previous_analysis=self._format_context(previous_analysis)
            )

            result = self._query_llm(prompt)
            
            task.complete()
            self._record_task_result(True)
            
            grb_keywords = ["grb", "gamma-ray burst", "swift", "fermi"]
            confidence = self._assess_relevance(paper, grb_keywords)
            
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                output_data={
                    "expert_review": result,
                    "expertise": self.expertise,
                    "confidence": confidence
                },
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            task.fail()
            self._record_task_result(False)
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=False,
                error_message=str(e),
                execution_time=time.time() - start_time
            )


class KilonovaExpertAgent(BaseExpertAgent):
    """Expert specialized in Kilonovae and Neutron Star Mergers - uses AstroSage-70B"""
    
    def __init__(self, agent_id: str, config: Any, llm_manager: Any):
        # Use AstroSage model for astronomy expertise
        astro_model = getattr(config, 'astro_expert_model', 'astrosage:70b-q4_K_M') if config else 'astrosage:70b-q4_K_M'
        super().__init__(agent_id, config, llm_manager, "Kilonovae & Neutron Star Mergers", model=astro_model)
    
    def can_handle(self, task: AgentTask) -> bool:
        return (set(task.required_capabilities).issubset(set(self.capabilities)) and
                task.task_type == "kilonova_review")

    def execute(self, task: AgentTask) -> AgentResult:
        start_time = time.time()
        task.start()
        
        try:
            paper = task.input_data.get("paper", {})
            previous_analysis = task.input_data.get("previous_analysis", "")
            
            prompt = self.prompt_loader.get_kilonova_expert_prompt(
                title=paper.get('title', 'Unknown'),
                authors=', '.join(paper.get('authors', [])[:5]),
                contents=self._paper_content(paper),
                previous_analysis=self._format_context(previous_analysis)
            )

            result = self._query_llm(prompt)
            
            task.complete()
            self._record_task_result(True)
            
            kn_keywords = ["kilonova", "neutron star merger", "r-process", "gw170817"]
            confidence = self._assess_relevance(paper, kn_keywords)
            
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                output_data={
                    "expert_review": result,
                    "expertise": self.expertise,
                    "confidence": confidence
                },
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            task.fail()
            self._record_task_result(False)
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=False,
                error_message=str(e),
                execution_time=time.time() - start_time
            )


class AstrophysicistAgent(BaseExpertAgent):
    """General astrophysics expert for broader context - uses larger Qwen"""
    
    def __init__(self, agent_id: str, config: Any, llm_manager: Any):
        # Use larger Qwen for synthesis
        general_model = getattr(config, 'general_model', 'qwen2.5:32b') if config else 'qwen2.5:32b'
        super().__init__(agent_id, config, llm_manager, "General Astrophysics", model=general_model)
        self.capabilities.append(AgentCapability.SYNTHESIS)
    
    def can_handle(self, task: AgentTask) -> bool:
        return (set(task.required_capabilities).issubset(set(self.capabilities)) and
                task.task_type in ["analyze_paper", "synthesize", "contextualize",
                                   "revise"])
    
    def execute(self, task: AgentTask) -> AgentResult:
        start_time = time.time()
        task.start()
        
        try:
            paper = task.input_data.get("paper", {})
            expert_reviews = task.input_data.get("expert_reviews", [])

            if task.task_type == "revise":
                # Same agent, acting on the critic's findings rather than starting over.
                prompt = self.prompt_loader.get_revision_prompt(
                    title=paper.get('title', 'Unknown'),
                    contents=self._paper_content(paper, limit=8000),
                    analysis=task.input_data.get("analysis", ""),
                    critique=task.input_data.get("critique", "")
                )
            else:
                prompt = self.prompt_loader.get_astrophysicist_prompt(
                    title=paper.get('title', 'Unknown'),
                    authors=', '.join(paper.get('authors', [])[:5]),
                    contents=self._paper_content(paper),
                    expert_reviews=self._format_expert_reviews(expert_reviews)
                )

            result = self._query_llm(prompt)
            
            task.complete()
            self._record_task_result(True)
            
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                output_data={
                    "synthesis": result,
                    "expertise": self.expertise
                },
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            task.fail()
            self._record_task_result(False)
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=False,
                error_message=str(e),
                execution_time=time.time() - start_time
            )
    
    def _format_expert_reviews(self, reviews: list) -> str:
        if not reviews:
            return ""
        formatted = "\n\nExpert Reviews:\n"
        for review in reviews:
            formatted += f"- {review.get('expertise', 'Expert')}: {review.get('expert_review', 'N/A')[:200]}...\n"
        return formatted


class LanguageExpertAgent(BaseExpertAgent):
    """Expert for bilingual content (English-Korean translation) - uses larger Qwen"""
    
    def __init__(self, agent_id: str, config: Any, llm_manager: Any):
        # Use larger Qwen for better translation
        lang_model = getattr(config, 'language_model', 'qwen2.5:32b') if config else 'qwen2.5:32b'
        super().__init__(agent_id, config, llm_manager, "Bilingual Scientific Communication", model=lang_model)
        self.capabilities.append(AgentCapability.SUMMARIZATION)
    
    # Qwen is a Chinese-developed model and drifts into Chinese on a long English
    # source with English instructions - an early run returned an entire analysis
    # in Chinese, including Chinese commentary about the translation. The prompt is
    # anchored in Korean, and output is script-checked here as a backstop.
    HANGUL = re.compile(r"[가-힣]")
    HAN = re.compile(r"[一-鿿]")
    MIN_HANGUL = 20
    MAX_HAN = 2

    def can_handle(self, task: AgentTask) -> bool:
        return (set(task.required_capabilities).issubset(set(self.capabilities)) and
                task.task_type in ["translate", "korean_summary"])

    @classmethod
    def script_problem(cls, text: str, min_hangul: int = None) -> str:
        """Return a description of any script contamination, or '' if clean."""
        if not text or not text.strip():
            return "empty translation"
        han = len(cls.HAN.findall(text))
        if han > cls.MAX_HAN:
            return f"contains {han} Chinese characters"
        hangul = len(cls.HANGUL.findall(text))
        floor = cls.MIN_HANGUL if min_hangul is None else min_hangul
        if hangul < floor:
            return f"only {hangul} Hangul characters"
        return ""

    # A short source drifts far less than a long one, and translating one
    # paragraph per call makes paragraph parity structural rather than a request.
    MIN_HANGUL_PARAGRAPH = 5
    REINFORCEMENT = ("\n\n경고: 이전 시도는 한자를 포함했습니다. "
                     "반드시 한글만 사용하십시오. 한자를 절대 쓰지 마십시오.\n")
    # Ollama defaults to temperature 0.8. Translation needs fidelity, not
    # invention, and loose sampling is a direct cause of drifting into Chinese.
    TRANSLATION_OPTIONS = {"top_p": 0.9, "repeat_penalty": 1.05}
    TEMPERATURE_LADDER = (0.2, 0.1, 0.05)

    def _attempt(self, prompt: str, temperature: float):
        """One translation attempt. Returns (text, problem); text is None on error."""
        options = {**self.TRANSLATION_OPTIONS, "temperature": temperature}
        try:
            text = self._query_llm(prompt, options=options)
        except LLMError as exc:
            return None, str(exc)
        return text, self.script_problem(text, min_hangul=self.MIN_HANGUL_PARAGRAPH)

    def _translate_paragraph(self, build_prompt, paragraph: str) -> str:
        """
        Translate one paragraph, tightening sampling on each retry.

        Observed failure: Qwen drifts into Chinese mid-output, and one retry
        returned 3986 Chinese characters. Lower temperature reduces the drift, and
        a shorter source reduces it further, so the last resort is sentence by
        sentence.
        """
        base_prompt = build_prompt(paragraph)
        problem = ""
        for attempt, temperature in enumerate(self.TEMPERATURE_LADDER):
            prompt = base_prompt if attempt == 0 else base_prompt + self.REINFORCEMENT
            text, problem = self._attempt(prompt, temperature)
            if text is not None and not problem:
                return text.strip()
            print(f"      ⚠️  paragraph attempt {attempt + 1} "
                  f"(temp {temperature}) rejected: {problem}")

        return self._translate_sentences(build_prompt, paragraph)

    def _translate_sentences(self, build_prompt, paragraph: str) -> str:
        """Last resort: a sentence at a time, where drift is far less likely."""
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", paragraph) if s.strip()]
        if len(sentences) < 2:
            raise ValueError("paragraph not Korean and too short to split further")

        print(f"      ↪️  falling back to sentence-by-sentence ({len(sentences)} sentences)")
        rendered = []
        for sentence in sentences:
            text, problem = self._attempt(build_prompt(sentence),
                                          self.TEMPERATURE_LADDER[-1])
            if text is not None and not problem:
                rendered.append(text.strip())

        # Require most of the paragraph to have survived; a couple of dropped
        # sentences is a gap, half a paragraph is a wrong translation.
        if len(rendered) < max(1, len(sentences) // 2):
            raise ValueError(
                f"only {len(rendered)}/{len(sentences)} sentences translated")
        if len(rendered) < len(sentences):
            print(f"      ⚠️  {len(sentences) - len(rendered)} sentences dropped")
        return " ".join(rendered)

    def translate(self, build_prompt, english: str) -> str:
        """
        Translate English into Korean, one paragraph at a time.

        Raises:
            ValueError: if no paragraph could be translated
        """
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", english or "") if p.strip()]
        if not paragraphs:
            raise ValueError("no English text to translate")

        rendered, failures = [], 0
        for index, paragraph in enumerate(paragraphs, 1):
            try:
                rendered.append(self._translate_paragraph(build_prompt, paragraph))
            # LLMError included: one slow or failed call must not discard the
            # paragraphs that did translate.
            except (ValueError, LLMError) as exc:
                # Keep the paragraph slot so the two languages stay aligned, and
                # make the gap visible rather than quietly dropping content.
                print(f"      ❌ paragraph {index}/{len(paragraphs)} failed: {exc}")
                rendered.append("[번역 실패]")
                failures += 1

        if failures == len(paragraphs):
            raise ValueError(f"every paragraph failed to translate ({failures})")
        if failures:
            print(f"      ⚠️  {failures}/{len(paragraphs)} paragraphs untranslated")
        return "\n\n".join(rendered)

    def execute(self, task: AgentTask) -> AgentResult:
        start_time = time.time()
        task.start()

        try:
            paper = task.input_data.get("paper", {})
            english_analysis = task.input_data.get("english_analysis", "")
            
            # No abstract, and no truncation: the Korean must be a faithful
            # translation of the *whole* final English, not a fresh summary.
            title = paper.get('title', 'Unknown')
            result = self.translate(
                lambda paragraph: self.prompt_loader.get_language_expert_prompt(
                    title=title, english_analysis=paragraph
                ),
                english_analysis,
            )

            task.complete()
            self._record_task_result(True)
            
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                output_data={
                    "korean_summary": result,
                    "expertise": self.expertise
                },
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            task.fail()
            self._record_task_result(False)
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=False,
                error_message=str(e),
                execution_time=time.time() - start_time
            )


class CriticAgent(BaseExpertAgent):
    """Critical reviewer checking quality, accuracy, and completeness - uses larger Qwen"""
    
    def __init__(self, agent_id: str, config: Any, llm_manager: Any):
        # Use larger Qwen for critical analysis
        general_model = getattr(config, 'general_model', 'qwen2.5:32b') if config else 'qwen2.5:32b'
        super().__init__(agent_id, config, llm_manager, "Scientific Quality Review", model=general_model)
        self.capabilities = [AgentCapability.TEXT_ANALYSIS, AgentCapability.COMPARISON]
    
    def can_handle(self, task: AgentTask) -> bool:
        return (set(task.required_capabilities).issubset(set(self.capabilities)) and 
                task.task_type in ["critique", "quality_review"])
    
    def execute(self, task: AgentTask) -> AgentResult:
        start_time = time.time()
        task.start()
        
        try:
            paper = task.input_data.get("paper", {})
            analysis = task.input_data.get("analysis", "")

            prompt = self.prompt_loader.get_critic_prompt(
                title=paper.get('title', 'Unknown'),
                contents=self._paper_content(paper, limit=4000),
                analysis=analysis[:4000]
            )

            result = self._query_llm(prompt)
            score = self._extract_score(result)
            
            task.complete()
            self._record_task_result(True)
            
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                output_data={
                    "critique": result,
                    "quality_score": score,
                    "expertise": self.expertise
                },
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            task.fail()
            self._record_task_result(False)
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=False,
                error_message=str(e),
                execution_time=time.time() - start_time
            )
    
    def _extract_score(self, critique: str) -> float:
        """Extract quality score from critique"""
        match = re.search(r'(\d+(\.\d+)?)\s*/\s*10', critique)
        return float(match.group(1)) if match else 7.0


class WriterAgent(BaseExpertAgent):
    """Professional science writer for final polishing - uses larger Qwen"""
    
    def __init__(self, agent_id: str, config: Any, llm_manager: Any):
        # Use larger Qwen for polished writing
        general_model = getattr(config, 'general_model', 'qwen2.5:32b') if config else 'qwen2.5:32b'
        super().__init__(agent_id, config, llm_manager, "Scientific Writing & Communication", model=general_model)
        self.capabilities.append(AgentCapability.SYNTHESIS)
    
    def can_handle(self, task: AgentTask) -> bool:
        return (set(task.required_capabilities).issubset(set(self.capabilities)) and 
                task.task_type in ["polish", "finalize"])
    
    def execute(self, task: AgentTask) -> AgentResult:
        start_time = time.time()
        task.start()
        
        try:
            paper = task.input_data.get("paper", {})
            analysis = task.input_data.get("analysis", "")
            critique = task.input_data.get("critique", "")

            prompt = self.prompt_loader.get_writer_prompt(
                title=paper.get('title', 'Unknown'),
                analysis=analysis,
                critique=critique[:800]
            )

            result = self._query_llm(prompt)
            
            task.complete()
            self._record_task_result(True)
            
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                output_data={
                    "polished_content": result,
                    "expertise": self.expertise
                },
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            task.fail()
            self._record_task_result(False)
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=False,
                error_message=str(e),
                execution_time=time.time() - start_time
            )
