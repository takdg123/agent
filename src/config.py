#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Configuration management for TORRI system
Centralized configuration with environment variable support
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional

# Try to import python-dotenv for .env file support
try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

class Config:
    """Centralized configuration management for TORRI system"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.root_dir = Path(__file__).parent.parent
        self.config_file = config_file or self.root_dir / "config" / "sources.yml"
        
        # Load .env file if available
        self._load_env_file()
        
        # Database configuration
        self.qdrant_host = os.getenv("QDRANT_HOST", "127.0.0.1")
        self.qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
        self.collection_name = os.getenv("QDRANT_COLLECTION", "daily_knowledge")
        
        # Ollama configuration
        self.ollama_url = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
        
        # GPU configuration for Ollama
        self.gpu_device = os.getenv("GPU_DEVICE", "0")
        
        # LLM model preferences
        self.preferred_models = [
            "llama4:latest",
            "llama4:13b"
        ]
        
        # PDF processing configuration
        self.pdf_chunk_size = int(os.getenv("PDF_CHUNK_SIZE", "800"))
        self.pdf_overlap_size = int(os.getenv("PDF_OVERLAP_SIZE", "150"))
        self.max_pdf_content = int(os.getenv("MAX_PDF_CONTENT", "100000"))
        
        # Report configuration
        self.max_papers = int(os.getenv("MAX_PAPERS", "20"))
        self.report_time = os.getenv("REPORT_TIME", "10:00")
        
        # System configuration
        self.system_name = os.getenv("SYSTEM_NAME", "TORRI")
        
        # Email configuration
        self.sender_email = os.getenv("SENDER_EMAIL", "")
        self.sender_password = os.getenv("SENDER_PASSWORD", "")
        self.recipient_email = os.getenv("RECIPIENT_EMAIL", "")
        self.email_enabled = bool(self.sender_email and self.sender_password and self.recipient_email)
        
        # File paths
        self.data_dir = self.root_dir / "data"
        self.pdfs_dir = self.data_dir / "pdfs"
        self.reports_dir = self.data_dir / "reports"
        self.backups_dir = self.data_dir / "backups"
        self.state_file = self.data_dir / "state.json"
        
        # Create directories if they don't exist
        self._ensure_directories()
    
    def _load_env_file(self):
        """Load environment variables from .env file"""
        if not DOTENV_AVAILABLE:
            print("📁 python-dotenv not available, using system environment variables")
            return
        
        # Look for .env file in the root directory
        env_file = self.root_dir / ".env"
        if env_file.exists():
            load_dotenv(env_file)
            print(f"📁 Loaded environment from: {env_file}")
            self.env_source = str(env_file)
        else:
            # Also check for .env.local (for local overrides)
            env_local = self.root_dir / ".env.local"
            if env_local.exists():
                load_dotenv(env_local)
                print(f"📁 Loaded environment from: {env_local}")
                self.env_source = str(env_local)
            else:
                print("📁 No .env file found, using system environment variables")
                self.env_source = "system environment"
    
    def _ensure_directories(self):
        """Create necessary directories"""
        for directory in [self.data_dir, self.pdfs_dir, self.reports_dir, self.backups_dir]:
            directory.mkdir(parents=True, exist_ok=True)
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration"""
        return {
            "host": self.qdrant_host,
            "port": self.qdrant_port,
            "collection": self.collection_name
        }
    
    def get_llm_config(self) -> Dict[str, Any]:
        """Get LLM configuration"""
        return {
            "url": self.ollama_url,
            "preferred_models": self.preferred_models,
            "gpu_device": self.gpu_device
        }
    
    def set_gpu_environment(self):
        """Set GPU environment variables for Ollama"""
        os.environ["CUDA_VISIBLE_DEVICES"] = self.gpu_device
        print(f"🔧 Set CUDA_VISIBLE_DEVICES={self.gpu_device}")
    
    def get_pdf_config(self) -> Dict[str, Any]:
        """Get PDF processing configuration"""
        return {
            "chunk_size": self.pdf_chunk_size,
            "overlap_size": self.pdf_overlap_size,
            "max_content": self.max_pdf_content
        }
    
    def get_report_config(self) -> Dict[str, Any]:
        """Get report configuration"""
        return {
            "max_papers": self.max_papers,
            "report_time": self.report_time
        }
    
    def get_email_config(self) -> Dict[str, Any]:
        """Get email configuration"""
        return {
            "sender_email": self.sender_email,
            "sender_password": self.sender_password,
            "recipient_email": self.recipient_email,
            "enabled": self.email_enabled
        }
    
    def get_sources_config(self) -> Dict[str, Any]:
        """Get sources configuration from sources.yml"""
        try:
            import yaml
            with open(self.config_file, 'r', encoding='utf-8') as f:
                sources_config = yaml.safe_load(f)
            return sources_config
        except Exception as e:
            print(f"⚠️ Warning: Could not load sources config: {e}")
            # Return default configuration
            return {
                "feeds": [
                    {"url": "http://export.arxiv.org/api/query?search_query=cat:astro-ph.HE&start=0&max_results=50&sortBy=submittedDate&sortOrder=descending"}
                ],
                "keywords": ["kilonova", "GRB", "gamma-ray burst"],
                "lang": "en"
            }
    
    def validate(self) -> bool:
        """Validate configuration"""
        try:
            # Check if directories are accessible
            assert self.data_dir.exists() or self.data_dir.mkdir(parents=True)
            assert self.pdfs_dir.exists() or self.pdfs_dir.mkdir(parents=True)
            assert self.reports_dir.exists() or self.reports_dir.mkdir(parents=True)
            
            # Check if ports are valid
            assert 1 <= self.qdrant_port <= 65535
            assert self.max_papers > 0
            
            return True
        except Exception as e:
            print(f"❌ Configuration validation failed: {e}")
            return False
    
    def __str__(self) -> str:
        """String representation of configuration"""
        email_status = "✅ Enabled" if self.email_enabled else "❌ Disabled"
        env_source = getattr(self, 'env_source', 'unknown')
        return f"""{self.system_name} Configuration:
  Database: {self.qdrant_host}:{self.qdrant_port} (collection: {self.collection_name})
  Ollama: {self.ollama_url}
  GPU Device: {self.gpu_device}
  Max Papers: {self.max_papers}
  PDF Chunk Size: {self.pdf_chunk_size}
  Data Directory: {self.data_dir}
  Email: {email_status}
  Environment: {env_source}
"""
