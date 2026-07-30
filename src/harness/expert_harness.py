#!/usr/bin/env python3
"""
Expert Harness - Multi-Expert Agent Orchestration
Coordinates GRB Expert, Kilonova Expert, Astrophysicist, Language Expert, Critic, and Writer
"""

from pathlib import Path
from typing import Dict, Any, List
from .base import AgentTask, AgentCapability
from .coordinator import AgentCoordinator
from .expert_agents import (
    GRBExpertAgent, KilonovaExpertAgent, AstrophysicistAgent,
    LanguageExpertAgent, CriticAgent, WriterAgent
)
from .knowledge_store import KnowledgeStore
from ..utils import key_numbers
from ..utils.llm_client import LLMClient

class ExpertHarness:
    """
    Multi-expert harness for comprehensive paper analysis
    
    Workflow:
    1. GRB Expert reviews → Specialized GRB analysis
    2. Kilonova Expert reviews → Specialized kilonova analysis
    3. Astrophysicist synthesizes → Broader context
    4. Language Expert translates → Korean summary
    5. Critic reviews → Quality check
    6. Writer polishes → Final version
    7. Memory Manager stores → Learning for future
    """
    
    def __init__(self, config: Any, llm_manager: Any):
        self.config = config
        self.llm_manager = llm_manager
        self.coordinator = AgentCoordinator(config)

        general_model = getattr(config, 'general_model', 'qwen2.5:32b') if config else 'qwen2.5:32b'
        self._number_llm = LLMClient(model=general_model)
        self.memory = KnowledgeStore(
            data_dir=getattr(config, 'data_dir', None) if config else None,
            llm=self._number_llm,
        )

        # Initialize all expert agents
        self._initialize_experts()
    
    def _initialize_experts(self):
        """Initialize and register all expert agents"""
        experts = [
            GRBExpertAgent("grb_expert", self.config, self.llm_manager),
            KilonovaExpertAgent("kilonova_expert", self.config, self.llm_manager),
            AstrophysicistAgent("astrophysicist", self.config, self.llm_manager),
            LanguageExpertAgent("language_expert", self.config, self.llm_manager),
            CriticAgent("critic", self.config, self.llm_manager),
            WriterAgent("writer", self.config, self.llm_manager)
        ]
        
        for expert in experts:
            self.coordinator.register_agent(expert)
        
        print(f"✅ Initialized {len(experts)} expert agents")
    
    # Cues that a paper is in a specialist's domain. Checked against title,
    # abstract, and the triage topic tags.
    GRB_CUES = ("grb", "gamma-ray burst", "gamma ray burst", "afterglow",
                "prompt emission", "swift", "fermi", "magnetar", "jet break",
                "central engine", "sgrb", "lgrb")
    # Deliberately excludes "ejecta" and "nucleosynthesis": both are common in
    # supernova papers, and "SN ejecta" wrongly pulled in the kilonova expert.
    KILONOVA_CUES = ("kilonova", "neutron star merger", "r-process", "gw170817",
                     "at2017gfo", "ns-ns", "ns merger", "nsbh", "bns",
                     "binary neutron star", "lanthanide", "neutron-rich ejecta")

    @classmethod
    def select_experts(cls, paper: Dict[str, Any]) -> tuple:
        """
        Decide which domain experts a paper warrants.

        Returns:
            (run_grb, run_kilonova)

        When neither domain is detected both experts run: an unrecognised paper
        must not silently lose all specialist review.
        """
        haystack = " ".join([
            paper.get("title") or "",
            paper.get("abstract") or "",
            " ".join(paper.get("topic_tags") or []),
        ]).lower()

        run_grb = any(cue in haystack for cue in cls.GRB_CUES)
        run_kilonova = any(cue in haystack for cue in cls.KILONOVA_CUES)
        if not (run_grb or run_kilonova):
            return True, True
        return run_grb, run_kilonova

    def analyze_paper_multi_expert(self, paper: Dict[str, Any], use_memory: bool = True) -> Dict[str, Any]:
        """
        Comprehensive multi-expert paper analysis
        
        Returns:
            {
                'english': str,
                'korean': str,
                'expert_reviews': list,
                'quality_score': float,
                'critique': str,
                'used_memory': bool,
                'execution_time': float
            }
        """
        import time
        start_time = time.time()
        
        print(f"\n{'='*70}")
        print(f"🔬 Multi-Expert Analysis: {paper.get('title', 'Unknown')[:60]}...")
        print(f"{'='*70}")
        
        # Step 0: Recall related past work
        context = {}
        recalled_lines = []
        if use_memory:
            context = self.memory.recall(paper)
            recalled_lines = self.memory.as_context_lines(context)
            if context.get('has_history'):
                print(f"📚 Recall: {len(context['similar'])} similar papers, "
                      f"{len(context['topic_notes'])} topic notes")
        
        # Steps 1-2: domain experts, only those whose domain the paper touches.
        # Running the kilonova expert on a pure GRB paper cost ~38s and fed an
        # empty review into the synthesis.
        run_grb, run_kn = self.select_experts(paper)

        grb_task_id = kn_task_id = None
        if run_grb:
            print("\n🌟 Step 1: GRB Expert Review...")
            grb_task_id = self.coordinator.submit_task(AgentTask(
                task_type="grb_review",
                description="GRB expert analysis",
                input_data={"paper": paper, "previous_analysis": recalled_lines},
                required_capabilities=[AgentCapability.TEXT_ANALYSIS],
                priority=10
            ))
        else:
            print("\n⏭️  Step 1: GRB Expert skipped (not a GRB paper)")

        if run_kn:
            print("💫 Step 2: Kilonova Expert Review...")
            kn_task_id = self.coordinator.submit_task(AgentTask(
                task_type="kilonova_review",
                description="Kilonova expert analysis",
                input_data={"paper": paper, "previous_analysis": recalled_lines},
                required_capabilities=[AgentCapability.TEXT_ANALYSIS],
                priority=10
            ))
        else:
            print("⏭️  Step 2: Kilonova Expert skipped (not a kilonova/merger paper)")

        # Executed sequentially: both experts share one 42GB model, so running
        # them concurrently would thrash VRAM.
        results = self.coordinator.execute_all_tasks()
        result_map = {r.task_id: r for r in results}

        # Collect expert reviews
        expert_reviews = []
        grb_result = result_map.get(grb_task_id) if grb_task_id else None
        kn_result = result_map.get(kn_task_id) if kn_task_id else None

        for label, task_id, result in (("GRB Expert", grb_task_id, grb_result),
                                       ("Kilonova Expert", kn_task_id, kn_result)):
            if task_id is None:
                continue
            if result and result.success:
                expert_reviews.append(result.output_data)
                print(f"   ✅ {label} (confidence: {result.output_data.get('confidence', 0):.2f})")
            else:
                # Never silent: a dead expert went unnoticed for weeks.
                reason = result.error_message if result else "no result returned"
                print(f"   ❌ {label} FAILED: {reason}")
        
        # Step 3: Astrophysicist Synthesis
        print("\n🔭 Step 3: Astrophysicist Synthesis...")
        synth_task = AgentTask(
            task_type="synthesize",
            description="Astrophysical synthesis",
            input_data={
                "paper": paper,
                "expert_reviews": expert_reviews
            },
            required_capabilities=[AgentCapability.SYNTHESIS],
            priority=9
        )
        synth_task_id = self.coordinator.submit_task(synth_task)
        
        results = self.coordinator.execute_all_tasks()
        result_map = {r.task_id: r for r in results}
        
        synth_result = result_map.get(synth_task_id)
        english_analysis = ""
        if synth_result and synth_result.success:
            english_analysis = synth_result.output_data.get('synthesis', '')
            print(f"   ✅ Synthesis complete ({len(english_analysis)} chars)")
        else:
            reason = synth_result.error_message if synth_result else "no result returned"
            # Without a synthesis there is nothing to report or translate.
            raise RuntimeError(f"synthesis failed: {reason}")
        
        # Step 4: Critic Review (English only; nothing is translated yet)
        print("\n🎯 Step 4: Critical Review...")
        critic_task = AgentTask(
            task_type="quality_review",
            description="Quality review and critique",
            input_data={
                "paper": paper,
                "analysis": english_analysis
            },
            required_capabilities=[AgentCapability.COMPARISON],
            priority=8
        )
        critic_task_id = self.coordinator.submit_task(critic_task)

        results = self.coordinator.execute_all_tasks()
        result_map = {r.task_id: r for r in results}

        critic_result = result_map.get(critic_task_id)
        critique = ""
        quality_score = 7.0
        if critic_result and critic_result.success:
            critique = critic_result.output_data.get('critique', '')
            quality_score = critic_result.output_data.get('quality_score', 7.0)
            print(f"   ✅ Quality Score: {quality_score}/10")
        else:
            reason = critic_result.error_message if critic_result else "no result returned"
            print(f"   ❌ Critic FAILED: {reason}")

        # Step 5: Writer polishes the English
        final_english = english_analysis

        if quality_score >= 6.0:
            print("\n✍️  Step 5: Final Polish (English)...")
            writer_task = AgentTask(
                task_type="polish",
                description="Final polishing",
                input_data={
                    "paper": paper,
                    "analysis": english_analysis,
                    "critique": critique
                },
                required_capabilities=[AgentCapability.SYNTHESIS],
                priority=7
            )
            writer_task_id = self.coordinator.submit_task(writer_task)

            results = self.coordinator.execute_all_tasks()
            result_map = {r.task_id: r for r in results}

            writer_result = result_map.get(writer_task_id)
            if writer_result and writer_result.success:
                polished = (writer_result.output_data.get('polished_content') or '').strip()
                if polished:
                    final_english = polished
                    print(f"   ✅ Polished ({len(final_english)} chars)")
            else:
                reason = writer_result.error_message if writer_result else "no result returned"
                print(f"   ⚠️  Polish failed ({reason}); keeping the synthesis")
        else:
            print(f"\n⚠️  Quality too low ({quality_score}/10), skipping final polish")

        # Step 6: Translate the FINAL English. Translating last is what keeps the
        # two languages saying the same thing - previously Korean was derived from
        # the pre-polish draft and then diverged when the writer rewrote English.
        print("\n🌐 Step 6: Korean Translation (of the final English)...")
        lang_task = AgentTask(
            task_type="korean_summary",
            description="Korean translation",
            input_data={
                "paper": paper,
                "english_analysis": final_english
            },
            required_capabilities=[AgentCapability.SUMMARIZATION],
            priority=6
        )
        lang_task_id = self.coordinator.submit_task(lang_task)

        results = self.coordinator.execute_all_tasks()
        result_map = {r.task_id: r for r in results}

        lang_result = result_map.get(lang_task_id)
        final_korean = ""
        if lang_result and lang_result.success:
            final_korean = lang_result.output_data.get('korean_summary', '')
            print(f"   ✅ Korean translation ({len(final_korean)} chars)")
        else:
            reason = lang_result.error_message if lang_result else "no result returned"
            print(f"   ❌ Translation FAILED: {reason}")

        # Step 7: Key numbers for the top of the report card
        print("\n🔢 Step 7: Key Numbers...")
        numbers = key_numbers.extract(
            self._number_llm, paper,
            model=getattr(self.config, 'general_model', None),
            prompt_dir=Path(self.config.root_dir) / "prompts" if self.config else None,
        )
        print(f"   ✅ {len(numbers)} key numbers extracted")

        analysis_data = {
            'english': final_english,
            'korean': final_korean,
            'expert_reviews': expert_reviews,
            'quality_score': quality_score,
            'key_numbers': numbers,
            'topic_tags': paper.get('topic_tags') or [],
            'relevance_score': paper.get('relevance_score'),
        }

        # Step 8: Remember it
        if use_memory and quality_score >= 6.0:
            print("\n📚 Storing in knowledge base...")
            self.memory.record(paper, analysis_data)

        execution_time = time.time() - start_time

        print(f"\n✅ Multi-expert analysis complete in {execution_time:.1f}s")
        print(f"{'='*70}\n")

        return {
            **analysis_data,
            'critique': critique,
            'used_memory': context.get('has_history', False),
            'text_source': (paper.get('contents') or {}).get('source', 'abstract'),
            'execution_time': execution_time,
            'grb_confidence': grb_result.output_data.get('confidence', 0) if grb_result and grb_result.success else 0,
            'kilonova_confidence': kn_result.output_data.get('confidence', 0) if kn_result and kn_result.success else 0
        }
    
    def batch_analyze_papers(
        self,
        papers: List[Dict[str, Any]],
        use_memory: bool = True
    ) -> List[Dict[str, Any]]:
        """Analyze multiple papers using multi-expert system"""
        results = []
        
        print(f"\n🚀 Starting batch analysis of {len(papers)} papers with multi-expert system\n")
        
        for i, paper in enumerate(papers, 1):
            print(f"\n📄 Paper {i}/{len(papers)}")
            try:
                analysis = self.analyze_paper_multi_expert(paper, use_memory=use_memory)
                results.append({
                    'paper': paper,
                    'analysis': analysis,
                    'success': True
                })
            except Exception as e:
                print(f"❌ Error analyzing paper: {e}")
                results.append({
                    'paper': paper,
                    'error': str(e),
                    'success': False
                })
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get harness statistics"""
        return {
            "coordinator": self.coordinator.get_statistics(),
            "memory": self.memory.get_statistics()
        }
    
    def shutdown(self):
        """Shutdown harness"""
        self.coordinator.clear_history()
        print("🛑 Expert harness shutdown")
