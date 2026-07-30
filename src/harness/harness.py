#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Agent Harness - High-level orchestration system
"""

from typing import Dict, Any, List, Optional
from .base import AgentTask, AgentResult, AgentCapability
from .coordinator import AgentCoordinator
from .text_agent import TextAnalysisAgent
from .vision_agent import VisionAnalysisAgent

class AgentHarness:
    """High-level agent harness for orchestrating complex workflows"""
    
    def __init__(self, config: Any, llm_manager: Any, vision_processor: Any):
        self.config = config
        self.llm_manager = llm_manager
        self.vision_processor = vision_processor
        self.coordinator = AgentCoordinator(config)
        
        # Initialize agents
        self._initialize_agents()
    
    def _initialize_agents(self):
        """Initialize and register all agents"""
        # Text analysis agent
        text_agent = TextAnalysisAgent(
            agent_id="text_agent_01",
            config=self.config,
            llm_manager=self.llm_manager
        )
        self.coordinator.register_agent(text_agent)
        
        # Vision analysis agent (if vision is available)
        if self.vision_processor.is_available():
            vision_agent = VisionAnalysisAgent(
                agent_id="vision_agent_01",
                config=self.config,
                llm_manager=self.llm_manager,
                vision_processor=self.vision_processor
            )
            self.coordinator.register_agent(vision_agent)
        else:
            print("⚠️ Vision agent not initialized (PyMuPDF not available)")
    
    def analyze_paper_comprehensive(
        self,
        paper: Dict[str, Any],
        pdf_path: Optional[str] = None,
        pdf_text: Optional[str] = None,
        use_vision: bool = True
    ) -> Dict[str, Any]:
        """Comprehensive paper analysis using multiple agents"""
        results = {}
        
        # Task 1: Text-based analysis
        text_task = AgentTask(
            task_type="analyze_paper",
            description="Analyze paper content using text",
            input_data={
                "paper": paper,
                "pdf_text": pdf_text or ""
            },
            required_capabilities=[AgentCapability.TEXT_ANALYSIS, AgentCapability.SUMMARIZATION],
            priority=5
        )
        results['text_task_id'] = self.coordinator.submit_task(text_task)
        
        # Task 2: Vision-based analysis (if PDF available and vision enabled)
        if pdf_path and use_vision and self.vision_processor.is_available():
            vision_task = AgentTask(
                task_type="analyze_pdf_visually",
                description="Analyze paper using vision",
                input_data={
                    "pdf_path": pdf_path,
                    "focus": "general"
                },
                required_capabilities=[AgentCapability.VISION_ANALYSIS],
                priority=4
            )
            results['vision_task_id'] = self.coordinator.submit_task(vision_task)
            
            # Task 3: Figure extraction and analysis
            figure_task = AgentTask(
                task_type="extract_figures",
                description="Extract and analyze figures",
                input_data={
                    "pdf_path": pdf_path
                },
                required_capabilities=[AgentCapability.VISION_ANALYSIS],
                priority=3
            )
            results['figure_task_id'] = self.coordinator.submit_task(figure_task)
        
        # Execute all tasks
        task_results = self.coordinator.execute_all_tasks()
        
        # Compile results
        compiled_results = {
            "paper_title": paper.get("title", "Unknown"),
            "analysis_complete": True,
            "text_analysis": None,
            "visual_analysis": None,
            "figure_analysis": None
        }
        
        for result in task_results:
            if result.success:
                if result.task_id == results.get('text_task_id'):
                    compiled_results['text_analysis'] = result.output_data.get('analysis')
                elif result.task_id == results.get('vision_task_id'):
                    compiled_results['visual_analysis'] = result.output_data.get('visual_analysis')
                elif result.task_id == results.get('figure_task_id'):
                    compiled_results['figure_analysis'] = result.output_data.get('figure_analyses')
        
        return compiled_results
    
    def batch_analyze_papers(
        self,
        papers: List[Dict[str, Any]],
        use_vision: bool = True
    ) -> List[Dict[str, Any]]:
        """Batch analyze multiple papers"""
        results = []
        
        for paper in papers:
            # Create task for each paper
            task = AgentTask(
                task_type="analyze_paper",
                description=f"Analyze paper: {paper.get('title', 'Unknown')[:50]}",
                input_data={"paper": paper},
                required_capabilities=[AgentCapability.TEXT_ANALYSIS],
                priority=3
            )
            task_id = self.coordinator.submit_task(task)
            results.append({
                "paper_title": paper.get("title", "Unknown"),
                "task_id": task_id
            })
        
        # Execute all tasks
        task_results = self.coordinator.execute_all_tasks()
        
        # Match results with papers
        result_map = {r.task_id: r for r in task_results}
        
        for result_entry in results:
            task_id = result_entry['task_id']
            if task_id in result_map:
                agent_result = result_map[task_id]
                if agent_result.success:
                    result_entry['analysis'] = agent_result.output_data.get('analysis')
                    result_entry['success'] = True
                else:
                    result_entry['error'] = agent_result.error_message
                    result_entry['success'] = False
        
        return results
    
    def compare_papers(
        self,
        papers: List[Dict[str, Any]],
        comparison_aspect: str = "methodology"
    ) -> Dict[str, Any]:
        """Compare multiple papers"""
        if len(papers) < 2:
            return {
                "success": False,
                "error": "Need at least 2 papers for comparison"
            }
        
        # First, analyze each paper
        analyses = []
        for paper in papers:
            task = AgentTask(
                task_type="analyze_paper",
                description=f"Analyze for comparison: {paper.get('title', 'Unknown')[:50]}",
                input_data={"paper": paper},
                required_capabilities=[AgentCapability.TEXT_ANALYSIS],
                priority=5
            )
            task_id = self.coordinator.submit_task(task)
            analyses.append(task_id)
        
        # Execute analysis tasks
        task_results = self.coordinator.execute_all_tasks()
        result_map = {r.task_id: r for r in task_results}
        
        # Compile analyses
        paper_analyses = []
        for i, task_id in enumerate(analyses):
            if task_id in result_map and result_map[task_id].success:
                paper_analyses.append({
                    "title": papers[i].get("title", "Unknown"),
                    "analysis": result_map[task_id].output_data.get('analysis', '')
                })
        
        # Create comparison task
        comparison_text = "\n\n".join([
            f"Paper {i+1}: {pa['title']}\n{pa['analysis']}"
            for i, pa in enumerate(paper_analyses)
        ])
        
        comparison_task = AgentTask(
            task_type="answer_question",
            description="Compare papers",
            input_data={
                "question": f"Compare these papers focusing on {comparison_aspect}. Identify similarities and differences.",
                "context": comparison_text
            },
            required_capabilities=[AgentCapability.TEXT_ANALYSIS],
            priority=10
        )
        
        comp_task_id = self.coordinator.submit_task(comparison_task)
        comp_results = self.coordinator.execute_all_tasks()
        
        for result in comp_results:
            if result.task_id == comp_task_id and result.success:
                return {
                    "success": True,
                    "comparison": result.output_data.get('answer'),
                    "papers_compared": len(papers),
                    "comparison_aspect": comparison_aspect
                }
        
        return {
            "success": False,
            "error": "Comparison failed"
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get harness status"""
        return {
            "harness_status": "active",
            "coordinator_stats": self.coordinator.get_statistics(),
            "vision_available": self.vision_processor.is_available(),
            "llm_available": self.llm_manager.is_available()
        }
    
    def shutdown(self):
        """Shutdown the harness"""
        self.coordinator.clear_history()
        print("🛑 Agent harness shutdown complete")
