#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Main Agent system class
Orchestrates all components for paper ingestion, analysis, and reporting
"""

import datetime as dt
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from .config import Config
from .io.pdf import PDFProcessor
from .database import DatabaseManager
from .llm import LLMAnalyzer
from .routines import DownloadRoutine, IngestRoutine, ReportRoutine

class Agent:
    """Main system class that orchestrates all Agent components"""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize Agent system with configuration"""
        self.config = config or Config()
        
        # Validate configuration
        if not self.config.validate():
            raise ValueError("Configuration validation failed")
        
        # Initialize components
        self.pdf_processor = PDFProcessor(self.config)
        self.db_manager = DatabaseManager(self.config)
        self.llm_analyzer = LLMAnalyzer(self.config)
        
        # Initialize routines
        self.downloader = DownloadRoutine(self.config)
        self.ingester = IngestRoutine(self.config, self.db_manager)
        self.reporter = ReportRoutine(self.config, self.db_manager, self.llm_analyzer, self.pdf_processor)
        
        # System state
        self.initialized = False
        
        print(f"🚀 {self.config.system_name} System initialized")
        print(self.config)
        
        # Set GPU environment for Ollama
        self.config.set_gpu_environment()
    
    def initialize(self) -> bool:
        """Initialize all system components"""
        try:
            print(f"🔧 Initializing {self.config.system_name} system components...")
            
            # Initialize database connection
            if not self.db_manager.connect():
                print("❌ Failed to initialize database manager")
                return False
            
            # Initialize LLM analyzer
            if not self.llm_analyzer.get_available_model():
                print("⚠️ LLM analyzer not available, but system can continue")
            
            # Ensure database collection exists
            if not self.db_manager.ensure_collection():
                print("❌ Failed to ensure database collection")
                return False
            
            self.initialized = True
            print(f"✅ {self.config.system_name} system initialization complete")
            return True
            
        except Exception as e:
            print(f"❌ System initialization failed: {e}")
            return False
    
    def ingest_papers(self) -> Dict[str, Any]:
        """Run paper ingestion process"""
        if not self.initialized:
            if not self.initialize():
                return {"success": False, "error": "System not initialized"}
        
        return self.ingester.ingest_papers()
    
    def generate_daily_report(self, hours_back: int = 168) -> Dict[str, Any]:
        """Generate comprehensive daily report"""
        if not self.initialized:
            if not self.initialize():
                return {"success": False, "error": "System not initialized"}
        
        return self.reporter.generate_daily_report(hours_back)
    
    def analyze_pdf(self, pdf_path: str, analysis_type: str = "summary") -> Dict[str, Any]:
        """Analyze a specific PDF file"""
        if not self.initialized:
            if not self.initialize():
                return {"success": False, "error": "System not initialized"}
        
        try:
            print(f"🔍 Analyzing PDF: {Path(pdf_path).name}")
            
            # Process PDF for analysis
            enhanced_data = self.pdf_processor.process_pdf_for_analysis(pdf_path)
            
            if not enhanced_data.get("content"):
                return {"success": False, "error": "No content extracted from PDF"}
            
            # Generate analysis based on type
            if analysis_type == "summary":
                analysis = self.llm_analyzer.generate_paper_summary(
                    {"title": Path(pdf_path).stem}, enhanced_data
                )
            else:
                analysis = "Analysis type not supported"
            
            return {
                "success": True,
                "pdf_path": pdf_path,
                "analysis_type": analysis_type,
                "analysis": analysis,
                "metadata": enhanced_data.get("metadata", {}),
                "content_preview": enhanced_data.get("content", "")[:200] + "..."
            }
            
        except Exception as e:
            print(f"❌ PDF analysis failed: {e}")
            return {"success": False, "error": str(e)}
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        return {
            "initialized": self.initialized,
            "pdf_processing": self.pdf_processor.is_available(),
            "database": self.db_manager.is_connected(),
            "llm": self.llm_analyzer.is_available(),
            "current_model": self.llm_analyzer.get_current_model(),
            "database_stats": self.db_manager.get_collection_stats(),
            "email": self.config.email_enabled,
            "configuration": {
                "max_papers": self.config.max_papers,
                "pdf_chunk_size": self.config.pdf_chunk_size,
                "data_directory": str(self.config.data_dir),
                "email_enabled": self.config.email_enabled
            }
        }
