#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Optimized Enhanced Agent - Streamlined version
"""

from pathlib import Path
from typing import List, Dict, Any, Optional

from .config import Config
from .io import PDFProcessor, VisionProcessor
from .database import DatabaseManager
from .llm import LLMManager
from .harness import AgentHarness

class Agent:
    """Optimized Agent with multi-LLM, vision, and harness support"""
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        if not self.config.validate():
            raise ValueError("Configuration validation failed")
        
        # Core components
        self.pdf = PDFProcessor(self.config)
        self.vision = VisionProcessor(self.config) if self.config.vision_enabled else None
        self.db = DatabaseManager(self.config)
        self.llm = LLMManager(self.config)
        self.harness = AgentHarness(self.config, self.llm, self.vision) if self.config.harness_enabled else None
        
        self.initialized = False
        self.config.set_gpu_environment()
    
    def initialize(self) -> bool:
        """Initialize system"""
        try:
            if not self.db.connect() or not self.db.ensure_collection():
                return False
            
            if not self.llm.is_available():
                print("⚠️ No LLM providers available")
                return False
            
            model_sel = self.llm.select_best_model()
            if model_sel:
                print(f"✅ Using {model_sel[0]}/{model_sel[1]}")
            
            self.initialized = True
            return True
        except Exception as e:
            print(f"❌ Initialization failed: {e}")
            return False
    
    def analyze_paper(
        self,
        paper: Dict[str, Any],
        pdf_path: Optional[str] = None,
        pdf_text: Optional[str] = None,
        use_vision: bool = True,
        use_harness: bool = True
    ) -> Dict[str, Any]:
        """Analyze paper with optional vision and harness"""
        if not self.initialized and not self.initialize():
            return {"success": False, "error": "Not initialized"}
        
        try:
            # Use harness if available
            if use_harness and self.harness:
                return {
                    **self.harness.analyze_paper_comprehensive(
                        paper, pdf_path, pdf_text, 
                        use_vision and self.vision is not None
                    ),
                    "success": True,
                    "method": "harness"
                }
            
            # Direct analysis
            from .llm import Message
            content = self._build_analysis_prompt(paper, pdf_text)
            messages = [Message(role="user", content=content)]
            
            result = {
                "success": True,
                "method": "direct",
                "paper_title": paper.get("title", "Unknown"),
                "analysis": self.llm.chat(messages, max_tokens=3000)
            }
            
            # Add vision if requested
            if use_vision and pdf_path and self.vision:
                pages = self.vision.smart_page_selection(pdf_path, max_pages=3)
                images = self.vision.pdf_to_images(pdf_path, pages)
                if images:
                    result["visual_analysis"] = self.llm.generate_with_vision(
                        "Analyze the visual content: figures, tables, and key elements.",
                        images
                    )
            
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def batch_analyze(self, papers: List[Dict[str, Any]], use_vision: bool = False) -> List[Dict[str, Any]]:
        """Batch analyze papers"""
        if not self.initialized and not self.initialize():
            return []
        
        if self.harness:
            return self.harness.batch_analyze_papers(papers, use_vision)
        
        return [self.analyze_paper(p, use_vision=use_vision, use_harness=False) for p in papers]
    
    def _build_analysis_prompt(self, paper: Dict[str, Any], pdf_text: Optional[str] = None) -> str:
        """Build analysis prompt from paper data"""
        from .utils.prompt_loader import PromptLoader
        loader = PromptLoader(self.config.root_dir / "prompts")
        
        return loader.get_paper_summary_prompt().format(
            title=paper.get('title', 'Unknown'),
            authors=', '.join(paper.get('authors', [])[:3]),
            abstract=paper.get('abstract', 'Not available'),
            categories=', '.join(paper.get('categories', [])),
            url=paper.get('url', 'Not available'),
            enhanced_pdf_context=pdf_text[:3000] if pdf_text else ''
        )
    
    def get_status(self) -> Dict[str, Any]:
        """Get system status"""
        return {
            "initialized": self.initialized,
            "llm": self.llm.get_status(),
            "vision": self.vision.is_available() if self.vision else False,
            "database": self.db.is_connected(),
            "harness": self.harness.get_status() if self.harness else None
        }
