#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Vision Analysis Agent for multimodal tasks
"""

import time
from typing import Dict, Any, List
from .base import BaseAgent, AgentTask, AgentResult, AgentCapability

class VisionAnalysisAgent(BaseAgent):
    """Agent specialized in vision-based analysis tasks"""
    
    def __init__(self, agent_id: str, config: Any, llm_manager: Any, vision_processor: Any):
        super().__init__(agent_id, config)
        self.llm_manager = llm_manager
        self.vision_processor = vision_processor
        self.capabilities = [
            AgentCapability.VISION_ANALYSIS,
            AgentCapability.SUMMARIZATION,
            AgentCapability.INFORMATION_EXTRACTION
        ]
    
    def can_handle(self, task: AgentTask) -> bool:
        """Check if this agent can handle the task"""
        # Check if vision is available and task requires vision
        if not self.vision_processor.is_available():
            return False
        
        required = set(task.required_capabilities)
        available = set(self.capabilities)
        
        # Must have vision capability requirement
        return AgentCapability.VISION_ANALYSIS in required and required.issubset(available)
    
    def execute(self, task: AgentTask) -> AgentResult:
        """Execute vision analysis task"""
        start_time = time.time()
        task.start()
        
        try:
            result_data = {}
            
            # Handle different task types
            if task.task_type == "analyze_pdf_visually":
                result_data = self._analyze_pdf_visually(task.input_data)
            
            elif task.task_type == "extract_figures":
                result_data = self._extract_and_analyze_figures(task.input_data)
            
            elif task.task_type == "compare_visual":
                result_data = self._compare_visual_content(task.input_data)
            
            else:
                raise ValueError(f"Unknown task type: {task.task_type}")
            
            task.complete()
            execution_time = time.time() - start_time
            self._record_task_result(True)
            
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                output_data=result_data,
                execution_time=execution_time,
                metadata={"task_type": task.task_type}
            )
            
        except Exception as e:
            task.fail()
            execution_time = time.time() - start_time
            self._record_task_result(False)
            
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=False,
                error_message=str(e),
                execution_time=execution_time
            )
    
    def _analyze_pdf_visually(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze PDF using vision (convert to images)"""
        pdf_path = input_data.get("pdf_path", "")
        analysis_focus = input_data.get("focus", "general")
        
        if not pdf_path:
            raise ValueError("No PDF path provided")
        
        # Smart page selection
        selected_pages = self.vision_processor.smart_page_selection(pdf_path)
        
        # Convert pages to images
        images = self.vision_processor.pdf_to_images(pdf_path, selected_pages)
        
        if not images:
            raise ValueError("Failed to convert PDF to images")
        
        # Build vision prompt
        prompts = {
            "general": "Analyze the content of these pages from a research paper. Describe what you see, including text, figures, tables, and any important visual elements.",
            "figures": "Focus on analyzing the figures, charts, and diagrams in these pages. Describe what each visualization shows.",
            "layout": "Analyze the layout and structure of these pages. Describe sections, formatting, and organization.",
            "tables": "Focus on analyzing any tables in these pages. Extract and describe the data presented."
        }
        
        prompt = prompts.get(analysis_focus, prompts["general"])
        
        # Generate vision analysis
        analysis = self.llm_manager.generate_with_vision(
            text_prompt=prompt,
            image_data=images,
            provider="openai_compatible"  # Prefer vision-capable provider
        )
        
        return {
            "visual_analysis": analysis,
            "pages_analyzed": len(images),
            "page_numbers": [img["page_number"] for img in images],
            "analysis_focus": analysis_focus
        }
    
    def _extract_and_analyze_figures(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and analyze figures from PDF"""
        pdf_path = input_data.get("pdf_path", "")
        
        if not pdf_path:
            raise ValueError("No PDF path provided")
        
        # Extract figures
        figures = self.vision_processor.extract_figures(pdf_path)
        
        if not figures:
            return {
                "figure_analyses": [],
                "total_figures": 0,
                "message": "No figures found in PDF"
            }
        
        # Analyze each figure
        figure_analyses = []
        for fig in figures[:5]:  # Limit to first 5 figures
            prompt = "Describe this figure from a research paper. What does it show? What are the key elements?"
            
            analysis = self.llm_manager.generate_with_vision(
                text_prompt=prompt,
                image_data=[fig],
                provider="openai_compatible"
            )
            
            figure_analyses.append({
                "page_number": fig["page_number"],
                "figure_index": fig["figure_index"],
                "analysis": analysis
            })
        
        return {
            "figure_analyses": figure_analyses,
            "total_figures": len(figures),
            "analyzed_count": len(figure_analyses)
        }
    
    def _compare_visual_content(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Compare visual content from multiple sources"""
        pdf_paths = input_data.get("pdf_paths", [])
        comparison_aspect = input_data.get("aspect", "methodology")
        
        if len(pdf_paths) < 2:
            raise ValueError("Need at least 2 PDFs for comparison")
        
        # Get images from each PDF
        all_images = []
        for pdf_path in pdf_paths[:3]:  # Limit to 3 PDFs
            pages = self.vision_processor.smart_page_selection(pdf_path, max_pages=2)
            images = self.vision_processor.pdf_to_images(pdf_path, pages)
            if images:
                all_images.append({
                    "pdf": pdf_path,
                    "images": images[:1]  # Take first page only
                })
        
        # Build comparison prompt
        prompt = f"Compare the {comparison_aspect} in these research paper pages. Identify similarities and differences."
        
        # Flatten images for analysis
        image_data = []
        for item in all_images:
            image_data.extend(item["images"])
        
        comparison = self.llm_manager.generate_with_vision(
            text_prompt=prompt,
            image_data=image_data,
            provider="openai_compatible"
        )
        
        return {
            "comparison_analysis": comparison,
            "papers_compared": len(all_images),
            "comparison_aspect": comparison_aspect
        }
