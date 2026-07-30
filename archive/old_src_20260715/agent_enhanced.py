#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Enhanced Agent system with multi-LLM support and agent harness
"""

import datetime as dt
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from .config import Config
from .io.pdf import PDFProcessor
from .io.vision import VisionProcessor
from .database import DatabaseManager
from .llm import LLMManager
from .harness import AgentHarness
from .routines import DownloadRoutine, IngestRoutine, ReportRoutine

class EnhancedAgent:
    """Enhanced Agent system with multi-LLM support and agent harness"""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize Enhanced Agent system"""
        self.config = config or Config()
        
        # Validate configuration
        if not self.config.validate():
            raise ValueError("Configuration validation failed")
        
        # Initialize components
        self.pdf_processor = PDFProcessor(self.config)
        self.vision_processor = VisionProcessor(self.config)
        self.db_manager = DatabaseManager(self.config)
        
        # Initialize LLM manager with multi-provider support
        self.llm_manager = LLMManager(self.config)
        
        # Initialize agent harness
        if self.config.harness_enabled:
            self.harness = AgentHarness(
                self.config,
                self.llm_manager,
                self.vision_processor
            )
        else:
            self.harness = None
        
        # Initialize routines
        self.downloader = DownloadRoutine(self.config)
        self.ingester = IngestRoutine(self.config, self.db_manager)
        
        # System state
        self.initialized = False
        
        print(f"🚀 {self.config.system_name} Enhanced System initialized")
        print(self.config)
        
        # Set GPU environment
        self.config.set_gpu_environment()
    
    def initialize(self) -> bool:
        """Initialize all system components"""
        try:
            print(f"🔧 Initializing {self.config.system_name} enhanced system...")
            
            # Initialize database
            if not self.db_manager.connect():
                print("❌ Failed to initialize database manager")
                return False
            
            # Initialize LLM manager
            if not self.llm_manager.is_available():
                print("⚠️ No LLM providers available")
                return False
            
            # Select best model
            model_selection = self.llm_manager.select_best_model()
            if model_selection:
                provider, model = model_selection
                print(f"✅ Selected LLM: {provider}/{model}")
            
            # Ensure database collection
            if not self.db_manager.ensure_collection():
                print("❌ Failed to ensure database collection")
                return False
            
            self.initialized = True
            print(f"✅ {self.config.system_name} enhanced system initialization complete")
            
            # Print status
            self._print_status()
            
            return True
            
        except Exception as e:
            print(f"❌ System initialization failed: {e}")
            return False
    
    def _print_status(self):
        """Print system status"""
        print("\n📊 System Status:")
        
        # LLM status
        llm_status = self.llm_manager.get_status()
        print(f"  LLM Providers:")
        for provider, info in llm_status['providers'].items():
            status = "✅" if info['available'] else "❌"
            print(f"    {status} {provider}: {len(info['models'])} models")
        
        # Vision status
        vision_status = "✅" if self.vision_processor.is_available() else "❌"
        print(f"  Vision Processing: {vision_status}")
        
        # Harness status
        if self.harness:
            harness_status = self.harness.get_status()
            stats = harness_status['coordinator_stats']
            print(f"  Agent Harness: ✅ ({stats['registered_agents']} agents registered)")
        else:
            print(f"  Agent Harness: ❌ Disabled")
        
        print()
    
    def analyze_paper_enhanced(
        self,
        paper: Dict[str, Any],
        pdf_path: Optional[str] = None,
        pdf_text: Optional[str] = None,
        use_vision: bool = True,
        use_harness: bool = True
    ) -> Dict[str, Any]:
        """Enhanced paper analysis using multiple agents and vision"""
        if not self.initialized:
            if not self.initialize():
                return {"success": False, "error": "System not initialized"}
        
        try:
            print(f"🔍 Enhanced analysis: {paper.get('title', 'Unknown')[:80]}")
            
            # Use agent harness if enabled and available
            if use_harness and self.harness:
                result = self.harness.analyze_paper_comprehensive(
                    paper=paper,
                    pdf_path=pdf_path,
                    pdf_text=pdf_text,
                    use_vision=use_vision and self.vision_processor.is_available()
                )
                result['success'] = True
                result['method'] = 'harness'
                return result
            
            # Fallback to direct analysis
            analysis_result = {
                "success": True,
                "method": "direct",
                "paper_title": paper.get("title", "Unknown"),
                "text_analysis": None,
                "visual_analysis": None
            }
            
            # Text analysis
            from .llm import Message
            messages = [Message(
                role="user",
                content=f"""Analyze this research paper:

Title: {paper.get('title', 'Unknown')}
Authors: {', '.join(paper.get('authors', []))}
Abstract: {paper.get('abstract', 'Not available')}

{f"Content: {pdf_text[:3000]}" if pdf_text else ""}

Provide a comprehensive analysis including objectives, methodology, findings, and significance."""
            )]
            
            text_analysis = self.llm_manager.chat(messages, max_tokens=3000)
            analysis_result['text_analysis'] = text_analysis
            
            # Vision analysis (if available and requested)
            if use_vision and pdf_path and self.vision_processor.is_available():
                # Select key pages
                pages = self.vision_processor.smart_page_selection(pdf_path, max_pages=3)
                images = self.vision_processor.pdf_to_images(pdf_path, pages)
                
                if images:
                    vision_prompt = "Analyze the visual content of these pages from a research paper. Describe figures, tables, and key visual elements."
                    vision_analysis = self.llm_manager.generate_with_vision(
                        text_prompt=vision_prompt,
                        image_data=images
                    )
                    analysis_result['visual_analysis'] = vision_analysis
            
            return analysis_result
            
        except Exception as e:
            print(f"❌ Enhanced analysis failed: {e}")
            return {"success": False, "error": str(e)}
    
    def batch_analyze_papers(
        self,
        papers: List[Dict[str, Any]],
        use_vision: bool = False
    ) -> List[Dict[str, Any]]:
        """Batch analyze multiple papers"""
        if not self.initialized:
            if not self.initialize():
                return []
        
        if self.harness:
            return self.harness.batch_analyze_papers(papers, use_vision)
        
        # Fallback to sequential processing
        results = []
        for paper in papers:
            result = self.analyze_paper_enhanced(
                paper=paper,
                use_vision=use_vision,
                use_harness=False
            )
            results.append(result)
        
        return results
    
    def compare_papers(
        self,
        papers: List[Dict[str, Any]],
        comparison_aspect: str = "methodology"
    ) -> Dict[str, Any]:
        """Compare multiple papers"""
        if not self.initialized:
            if not self.initialize():
                return {"success": False, "error": "System not initialized"}
        
        if self.harness:
            return self.harness.compare_papers(papers, comparison_aspect)
        
        return {"success": False, "error": "Harness not available for comparison"}
    
    def extract_figures_from_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """Extract and analyze figures from PDF"""
        if not self.initialized:
            if not self.initialize():
                return {"success": False, "error": "System not initialized"}
        
        try:
            figures = self.vision_processor.extract_figures(pdf_path)
            
            # Analyze figures if vision LLM is available
            figure_analyses = []
            if figures and self.llm_manager.is_available():
                for fig in figures[:5]:  # Limit to first 5
                    analysis = self.llm_manager.generate_with_vision(
                        text_prompt="Describe this figure from a research paper. What does it show?",
                        image_data=[fig]
                    )
                    figure_analyses.append({
                        "page": fig["page_number"],
                        "analysis": analysis
                    })
            
            return {
                "success": True,
                "total_figures": len(figures),
                "figure_analyses": figure_analyses
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        status = {
            "initialized": self.initialized,
            "pdf_processing": self.pdf_processor.is_available(),
            "vision_processing": self.vision_processor.is_available(),
            "database": self.db_manager.is_connected(),
            "llm": self.llm_manager.is_available(),
            "llm_status": self.llm_manager.get_status(),
            "database_stats": self.db_manager.get_collection_stats() if self.initialized else {},
            "email": self.config.email_enabled,
            "harness_enabled": self.config.harness_enabled
        }
        
        if self.harness:
            status['harness_status'] = self.harness.get_status()
        
        return status
    
    def shutdown(self):
        """Shutdown the system"""
        if self.harness:
            self.harness.shutdown()
        print(f"🛑 {self.config.system_name} Enhanced System shutdown complete")
