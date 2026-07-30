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

# A critic score below this sends the analysis back to the astrophysicist.
REVISION_THRESHOLD = 7.0
MAX_REVISIONS = 2
DEFAULT_QUALITY = 7.0


class ExpertHarness:
    """
    Multi-expert harness for comprehensive paper analysis

    Workflow:
    0. Knowledge store recalls semantically similar past papers and topic notes
    1. Domain experts review, only those whose domain the paper touches, most
       relevant first, each seeing the reviews already written
    2. Astrophysicist synthesizes → broader context
    3. Critic scores; below threshold the astrophysicist revises and is
       re-reviewed, up to MAX_REVISIONS times, and the best version wins
    4. Writer polishes the English
    5. Language Expert translates the FINAL English → Korean
    6. Key numbers extracted for the top of the report card
    7. Knowledge store records the paper for future recall

    Translation is last on purpose: deriving Korean from the finished English is
    what stops the two languages disagreeing.
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

    @classmethod
    def expert_order(cls, paper: Dict[str, Any], run_grb: bool, run_kilonova: bool) -> List[tuple]:
        """
        The experts to run, most relevant first.

        The stronger specialist writes first so the second has something worth
        responding to, rather than a fixed GRB-then-kilonova order that puts a
        marginal review ahead of the central one.
        """
        haystack = " ".join([
            paper.get("title") or "",
            paper.get("abstract") or "",
            " ".join(paper.get("topic_tags") or []),
        ]).lower()

        planned = []
        if run_grb:
            planned.append((sum(cue in haystack for cue in cls.GRB_CUES),
                            "grb_review", "GRB Expert"))
        if run_kilonova:
            planned.append((sum(cue in haystack for cue in cls.KILONOVA_CUES),
                            "kilonova_review", "Kilonova Expert"))

        planned.sort(key=lambda entry: entry[0], reverse=True)
        return [(task_type, label) for _, task_type, label in planned]

    def _run_one(self, task: AgentTask):
        """Submit one task, run it, and return its result (or None)."""
        task_id = self.coordinator.submit_task(task)
        return {r.task_id: r for r in self.coordinator.execute_all_tasks()}.get(task_id)

    def _critique_and_revise(self, paper: Dict[str, Any], analysis: str) -> tuple:
        """
        Critique the analysis, and send it back for revision if it falls short.

        Returns:
            (best_analysis, best_score, critique_of_best)

        The best-scoring version wins, so a revision that makes things worse is
        discarded rather than shipped.
        """
        best = (analysis, DEFAULT_QUALITY, "")

        for attempt in range(MAX_REVISIONS + 1):
            label = "Critical Review" if attempt == 0 else f"Re-review (revision {attempt})"
            print(f"\n🎯 {label}...")
            result = self._run_one(AgentTask(
                task_type="quality_review",
                description="Quality review and critique",
                input_data={"paper": paper, "analysis": analysis},
                required_capabilities=[AgentCapability.COMPARISON],
                priority=8
            ))

            if not (result and result.success):
                reason = result.error_message if result else "no result returned"
                print(f"   ❌ Critic FAILED: {reason}")
                break

            critique = result.output_data.get('critique', '')
            score = result.output_data.get('quality_score', DEFAULT_QUALITY)
            print(f"   ✅ Quality Score: {score}/10")

            if score > best[1] or attempt == 0:
                best = (analysis, score, critique)

            if score >= REVISION_THRESHOLD:
                break
            if attempt == MAX_REVISIONS:
                print(f"   ⚠️  still {score}/10 after {MAX_REVISIONS} revisions; "
                      f"keeping the best version ({best[1]}/10)")
                break

            print(f"\n♻️  Revising (score {score} < {REVISION_THRESHOLD})...")
            revision = self._run_one(AgentTask(
                task_type="revise",
                description="Revise analysis after critique",
                input_data={"paper": paper, "analysis": analysis, "critique": critique},
                required_capabilities=[AgentCapability.SYNTHESIS],
                priority=8
            ))

            revised = (revision.output_data.get('synthesis') or '').strip() \
                if revision and revision.success else ''
            if not revised:
                reason = revision.error_message if revision else "no result returned"
                print(f"   ⚠️  Revision failed ({reason}); keeping the current version")
                break
            print(f"   ✅ Revised ({len(revised)} chars)")
            analysis = revised

        return best

    @staticmethod
    def _peer_lines(expert_reviews: List[Dict[str, Any]]) -> List[str]:
        """Reviews already written, for the next specialist to build on or dispute."""
        return [
            f"- Peer review already written by the {review.get('expertise', 'expert')}:\n"
            f"  {(review.get('expert_review') or '')[:900].strip()}"
            for review in expert_reviews
        ]

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
        planned = self.expert_order(paper, run_grb, run_kn)

        if not run_grb:
            print("\n⏭️  GRB Expert skipped (not a GRB paper)")
        if not run_kn:
            print("⏭️  Kilonova Expert skipped (not a kilonova/merger paper)")

        # Run specialists in relevance order, each seeing the reviews already
        # written. They share one 42GB model, so this costs no extra wall-clock
        # over running them blind - it just makes the second review better informed.
        expert_reviews = []
        confidences = {}
        for step, (task_type, label) in enumerate(planned, 1):
            print(f"\n🌟 Step {step}: {label} Review"
                  f"{' (sees prior review)' if expert_reviews else ''}...")
            task_id = self.coordinator.submit_task(AgentTask(
                task_type=task_type,
                description=f"{label} analysis",
                input_data={
                    "paper": paper,
                    "previous_analysis": recalled_lines + self._peer_lines(expert_reviews),
                },
                required_capabilities=[AgentCapability.TEXT_ANALYSIS],
                priority=10
            ))
            result_map = {r.task_id: r for r in self.coordinator.execute_all_tasks()}
            result = result_map.get(task_id)

            if result and result.success:
                expert_reviews.append(result.output_data)
                confidence = result.output_data.get('confidence', 0)
                confidences[task_type] = confidence
                print(f"   ✅ {label} (confidence: {confidence:.2f})")
            else:
                # Never silent: a dead expert went unnoticed for weeks.
                reason = result.error_message if result else "no result returned"
                print(f"   ❌ {label} FAILED: {reason}")

        grb_confidence = confidences.get("grb_review", 0)
        kn_confidence = confidences.get("kilonova_review", 0)

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
        synth_result = self._run_one(synth_task)
        english_analysis = ""
        if synth_result and synth_result.success:
            english_analysis = synth_result.output_data.get('synthesis', '')
            print(f"   ✅ Synthesis complete ({len(english_analysis)} chars)")
        else:
            reason = synth_result.error_message if synth_result else "no result returned"
            # Without a synthesis there is nothing to report or translate.
            raise RuntimeError(f"synthesis failed: {reason}")
        
        # Step 4: critique, and revise until the critic is satisfied.
        # Previously a single pass, and a LOW score *skipped* the polish - so the
        # weakest analyses got the least attention, which is backwards.
        english_analysis, quality_score, critique = self._critique_and_revise(
            paper, english_analysis
        )

        # Step 5: Writer polishes the English. Always - a weak analysis needs the
        # writer more, not less.
        final_english = english_analysis
        print("\n✍️  Step 5: Final Polish (English)...")
        writer_result = self._run_one(AgentTask(
            task_type="polish",
            description="Final polishing",
            input_data={
                "paper": paper,
                "analysis": english_analysis,
                "critique": critique
            },
            required_capabilities=[AgentCapability.SYNTHESIS],
            priority=7
        ))
        if writer_result and writer_result.success:
            polished = (writer_result.output_data.get('polished_content') or '').strip()
            if polished:
                final_english = polished
                print(f"   ✅ Polished ({len(final_english)} chars)")
        else:
            reason = writer_result.error_message if writer_result else "no result returned"
            print(f"   ⚠️  Polish failed ({reason}); keeping the synthesis")

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
        lang_result = self._run_one(lang_task)
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
            'grb_confidence': grb_confidence,
            'kilonova_confidence': kn_confidence
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
