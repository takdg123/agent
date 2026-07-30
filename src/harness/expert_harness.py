#!/usr/bin/env python3
"""
Expert Harness - Multi-Expert Agent Orchestration
Coordinates GRB Expert, Kilonova Expert, Astrophysicist, Language Expert, Critic, and Writer
"""

from typing import Dict, Any, List
from .base import AgentTask, AgentCapability
from .coordinator import AgentCoordinator
from .expert_agents import (
    GRBExpertAgent, KilonovaExpertAgent, AstrophysicistAgent,
    LanguageExpertAgent, CriticAgent, WriterAgent
)
from .memory_manager import MemoryManager
import re

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
        self.memory = MemoryManager()
        
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
        
        # Step 0: Check memory for context
        context = {}
        if use_memory:
            context = self.memory.get_context_for_paper(paper)
            if context.get('has_history'):
                print(f"📚 Memory: {context.get('summary')}")
        
        # Step 1: GRB Expert Review
        print("\n🌟 Step 1: GRB Expert Review...")
        grb_task = AgentTask(
            task_type="expert_review",
            description="GRB expert analysis",
            input_data={"paper": paper, "previous_analysis": context.get('previous_insights', [])},
            required_capabilities=[AgentCapability.TEXT_ANALYSIS],
            priority=10
        )
        grb_task_id = self.coordinator.submit_task(grb_task)
        
        # Step 2: Kilonova Expert Review
        print("💫 Step 2: Kilonova Expert Review...")
        kn_task = AgentTask(
            task_type="expert_review",
            description="Kilonova expert analysis",
            input_data={"paper": paper, "previous_analysis": context.get('previous_insights', [])},
            required_capabilities=[AgentCapability.TEXT_ANALYSIS],
            priority=10
        )
        kn_task_id = self.coordinator.submit_task(kn_task)
        
        # Execute expert reviews in parallel
        results = self.coordinator.execute_all_tasks()
        result_map = {r.task_id: r for r in results}
        
        # Collect expert reviews
        expert_reviews = []
        grb_result = result_map.get(grb_task_id)
        kn_result = result_map.get(kn_task_id)
        
        for label, result in (("GRB Expert", grb_result), ("Kilonova Expert", kn_result)):
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
        
        # Step 4: Language Expert - Korean Translation
        print("\n🌐 Step 4: Korean Translation...")
        lang_task = AgentTask(
            task_type="korean_summary",
            description="Korean summary generation",
            input_data={
                "paper": paper,
                "english_analysis": english_analysis
            },
            required_capabilities=[AgentCapability.SUMMARIZATION],
            priority=8
        )
        lang_task_id = self.coordinator.submit_task(lang_task)
        
        results = self.coordinator.execute_all_tasks()
        result_map = {r.task_id: r for r in results}
        
        lang_result = result_map.get(lang_task_id)
        korean_summary = ""
        if lang_result and lang_result.success:
            korean_summary = lang_result.output_data.get('korean_summary', '')
            print(f"   ✅ Korean summary ({len(korean_summary)} chars)")
        
        # Step 5: Critic Review
        print("\n🎯 Step 5: Critical Review...")
        critic_task = AgentTask(
            task_type="quality_review",
            description="Quality review and critique",
            input_data={
                "paper": paper,
                "analysis": english_analysis,
                "korean_summary": korean_summary
            },
            required_capabilities=[AgentCapability.COMPARISON],
            priority=7
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
        
        # Step 6: Writer Polish (if quality is acceptable)
        final_english = english_analysis
        final_korean = korean_summary
        
        if quality_score >= 6.0:
            print("\n✍️  Step 6: Final Polish...")
            writer_task = AgentTask(
                task_type="polish",
                description="Final polishing",
                input_data={
                    "paper": paper,
                    "analysis": english_analysis,
                    "korean_summary": korean_summary,
                    "critique": critique
                },
                required_capabilities=[AgentCapability.SYNTHESIS],
                priority=6
            )
            writer_task_id = self.coordinator.submit_task(writer_task)
            
            results = self.coordinator.execute_all_tasks()
            result_map = {r.task_id: r for r in results}
            
            writer_result = result_map.get(writer_task_id)
            if writer_result and writer_result.success:
                polished = writer_result.output_data.get('polished_content', '')
                
                # Extract English and Korean from polished content
                eng_match = re.search(r'\*\*English Analysis:\*\*\s*(.+?)(?=\*\*한국어 요약:\*\*|$)', polished, re.DOTALL)
                kor_match = re.search(r'\*\*한국어 요약:\*\*\s*(.+?)$', polished, re.DOTALL)
                
                if eng_match:
                    final_english = eng_match.group(1).strip()
                if kor_match:
                    final_korean = kor_match.group(1).strip()
                
                print(f"   ✅ Polished and finalized")
        else:
            print(f"\n⚠️  Quality too low ({quality_score}/10), skipping final polish")
        
        # Step 7: Store in memory
        if use_memory and quality_score >= 6.0:
            print("\n📚 Storing in memory...")
            analysis_data = {
                'english': final_english,
                'korean': final_korean,
                'expert_reviews': expert_reviews,
                'quality_score': quality_score
            }
            self.memory.store_paper_analysis(paper, analysis_data)
        
        execution_time = time.time() - start_time
        
        print(f"\n✅ Multi-expert analysis complete in {execution_time:.1f}s")
        print(f"{'='*70}\n")
        
        return {
            'english': final_english,
            'korean': final_korean,
            'expert_reviews': expert_reviews,
            'quality_score': quality_score,
            'critique': critique,
            'used_memory': context.get('has_history', False),
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
