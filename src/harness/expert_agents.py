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
from ..utils.llm_client import LLMClient
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
    
    def _query_llm(self, prompt: str, format: str = None) -> str:
        """Shared LLM query method - uses agent's designated model"""
        return self.llm_client.generate(prompt, model=self.model, format=format)
    
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
        return f"Context from previously analysed papers:\n{body}"


class GRBExpertAgent(BaseExpertAgent):
    """Expert specialized in Gamma-Ray Bursts - uses AstroSage-70B"""
    
    def __init__(self, agent_id: str, config: Any, llm_manager: Any):
        # Use AstroSage model for astronomy expertise
        astro_model = getattr(config, 'astro_expert_model', 'astrosage:70b-q4_K_M') if config else 'astrosage:70b-q4_K_M'
        super().__init__(agent_id, config, llm_manager, "Gamma-Ray Bursts (GRBs)", model=astro_model)
    
    def can_handle(self, task: AgentTask) -> bool:
        return (set(task.required_capabilities).issubset(set(self.capabilities)) and 
                task.task_type in ["analyze_paper", "expert_review"])
    
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
                task.task_type in ["analyze_paper", "expert_review"])
    
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
                task.task_type in ["analyze_paper", "synthesize", "contextualize"])
    
    def execute(self, task: AgentTask) -> AgentResult:
        start_time = time.time()
        task.start()
        
        try:
            paper = task.input_data.get("paper", {})
            expert_reviews = task.input_data.get("expert_reviews", [])
            
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
    
    def can_handle(self, task: AgentTask) -> bool:
        return (set(task.required_capabilities).issubset(set(self.capabilities)) and 
                task.task_type in ["translate", "korean_summary"])
    
    def execute(self, task: AgentTask) -> AgentResult:
        start_time = time.time()
        task.start()
        
        try:
            paper = task.input_data.get("paper", {})
            english_analysis = task.input_data.get("english_analysis", "")
            
            prompt = self.prompt_loader.get_language_expert_prompt(
                title=paper.get('title', 'Unknown'),
                abstract=paper.get('abstract', 'No abstract')[:1000],
                english_analysis=english_analysis[:1500]
            )

            result = self._query_llm(prompt)
            
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
            korean_summary = task.input_data.get("korean_summary", "")
            
            prompt = self.prompt_loader.get_critic_prompt(
                title=paper.get('title', 'Unknown'),
                abstract=paper.get('abstract', 'No abstract')[:800],
                analysis=analysis[:2000],
                korean_summary=korean_summary
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
            korean_summary = task.input_data.get("korean_summary", "")
            critique = task.input_data.get("critique", "")
            
            prompt = self.prompt_loader.get_writer_prompt(
                title=paper.get('title', 'Unknown'),
                analysis=analysis,
                korean_summary=korean_summary,
                critique=critique[:500]
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
