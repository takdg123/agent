#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Text Analysis Agent for text-based tasks
"""

import time
from typing import Dict, Any
from .base import BaseAgent, AgentTask, AgentResult, AgentCapability

class TextAnalysisAgent(BaseAgent):
    """Agent specialized in text analysis tasks"""
    
    def __init__(self, agent_id: str, config: Any, llm_manager: Any):
        super().__init__(agent_id, config)
        self.llm_manager = llm_manager
        self.capabilities = [
            AgentCapability.TEXT_ANALYSIS,
            AgentCapability.SUMMARIZATION,
            AgentCapability.QUESTION_ANSWERING,
            AgentCapability.INFORMATION_EXTRACTION
        ]
    
    def can_handle(self, task: AgentTask) -> bool:
        """Check if this agent can handle the task"""
        # Check if task requires only text capabilities
        required = set(task.required_capabilities)
        available = set(self.capabilities)
        return required.issubset(available)
    
    def execute(self, task: AgentTask) -> AgentResult:
        """Execute text analysis task"""
        start_time = time.time()
        task.start()
        
        try:
            result_data = {}
            
            # Handle different task types
            if task.task_type == "summarize":
                result_data = self._summarize(task.input_data)
            
            elif task.task_type == "extract_info":
                result_data = self._extract_information(task.input_data)
            
            elif task.task_type == "answer_question":
                result_data = self._answer_question(task.input_data)
            
            elif task.task_type == "analyze_paper":
                result_data = self._analyze_paper(task.input_data)
            
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
    
    def _summarize(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary of text"""
        text = input_data.get("text", "")
        prompt_template = input_data.get("prompt_template", "")
        
        if not text:
            raise ValueError("No text provided for summarization")
        
        # Build prompt
        if prompt_template:
            prompt = prompt_template.format(text=text)
        else:
            prompt = f"Please provide a concise summary of the following text:\n\n{text}"
        
        # Generate summary
        summary = self.llm_manager.generate(prompt)
        
        return {
            "summary": summary,
            "input_length": len(text),
            "summary_length": len(summary) if summary else 0
        }
    
    def _extract_information(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract specific information from text"""
        text = input_data.get("text", "")
        extraction_type = input_data.get("extraction_type", "key_points")
        
        if not text:
            raise ValueError("No text provided for extraction")
        
        # Build extraction prompt
        prompts = {
            "key_points": "Extract the key points from the following text:\n\n{text}",
            "methodology": "Extract and describe the methodology from the following research text:\n\n{text}",
            "findings": "Extract the main findings and results from the following text:\n\n{text}",
            "authors_info": "Extract author information and affiliations from the following text:\n\n{text}"
        }
        
        prompt = prompts.get(extraction_type, prompts["key_points"]).format(text=text)
        
        extracted = self.llm_manager.generate(prompt)
        
        return {
            "extracted_info": extracted,
            "extraction_type": extraction_type
        }
    
    def _answer_question(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Answer a question based on provided context"""
        question = input_data.get("question", "")
        context = input_data.get("context", "")
        
        if not question:
            raise ValueError("No question provided")
        
        if context:
            prompt = f"Based on the following context, please answer the question.\n\nContext:\n{context}\n\nQuestion: {question}\n\nAnswer:"
        else:
            prompt = f"Please answer the following question:\n\n{question}"
        
        answer = self.llm_manager.generate(prompt)
        
        return {
            "question": question,
            "answer": answer,
            "has_context": bool(context)
        }
    
    def _analyze_paper(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Comprehensive paper analysis"""
        paper = input_data.get("paper", {})
        pdf_text = input_data.get("pdf_text", "")
        
        if not paper and not pdf_text:
            raise ValueError("No paper data provided")
        
        # Build comprehensive analysis prompt
        prompt = f"""Please analyze the following research paper comprehensively:

Title: {paper.get('title', 'Unknown')}
Authors: {', '.join(paper.get('authors', []))}
Abstract: {paper.get('abstract', 'Not available')}

"""
        
        if pdf_text:
            prompt += f"\nFull text content:\n{pdf_text[:5000]}\n"  # Limit text length
        
        prompt += """
Please provide:
1. Main research question and objectives
2. Methodology overview
3. Key findings and contributions
4. Significance and potential impact
5. Limitations (if mentioned)
"""
        
        analysis = self.llm_manager.generate(prompt, max_tokens=3000)
        
        return {
            "analysis": analysis,
            "paper_title": paper.get('title', 'Unknown'),
            "has_full_text": bool(pdf_text)
        }
