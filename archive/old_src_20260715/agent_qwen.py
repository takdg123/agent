#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Streamlined Agent - Qwen Only
Minimal, efficient implementation using only Qwen
"""

import httpx
from pathlib import Path
from typing import List, Dict, Any, Optional

from .config import Config
from .io import PDFProcessor, VisionProcessor
from .database import DatabaseManager

class Agent:
    """Streamlined Agent using only Qwen"""
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        
        # Qwen configuration
        self.qwen_url = self.config.openai_compatible_url
        self.qwen_model = self.config.openai_compatible_model
        self.api_key = self.config.openai_compatible_api_key
        
        # Core components only
        self.pdf = PDFProcessor(self.config)
        self.vision = VisionProcessor(self.config) if self.config.vision_enabled else None
        self.db = DatabaseManager(self.config)
        
        self.initialized = False
        self.config.set_gpu_environment()
    
    def initialize(self) -> bool:
        """Initialize system"""
        try:
            # Check Qwen availability
            if not self._check_qwen():
                print("❌ Qwen not available at", self.qwen_url)
                print("   Start with: ./start_qwen.sh")
                return False
            
            print(f"✅ Using Qwen: {self.qwen_model}")
            
            # Initialize database
            if not self.db.connect() or not self.db.ensure_collection():
                print("❌ Database initialization failed")
                return False
            
            self.initialized = True
            return True
            
        except Exception as e:
            print(f"❌ Initialization failed: {e}")
            return False
    
    def _check_qwen(self) -> bool:
        """Check if Qwen is available"""
        try:
            response = httpx.get(f"{self.qwen_url}/models", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def generate(self, prompt: str, max_tokens: int = 2000, **kwargs) -> Optional[str]:
        """Generate text with Qwen"""
        if not self.initialized and not self.initialize():
            return None
        
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = httpx.post(
                f"{self.qwen_url}/chat/completions",
                headers=headers,
                json={
                    "model": self.qwen_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens,
                    **kwargs
                },
                timeout=120
            )
            
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"].strip()
            else:
                print(f"❌ Qwen error: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Generation failed: {e}")
            return None
    
    def generate_with_vision(self, text: str, images: List[Dict], max_tokens: int = 2000) -> Optional[str]:
        """Generate with vision"""
        if not self.initialized and not self.initialize():
            return None
        
        try:
            content = [{"type": "text", "text": text}]
            for img in images:
                content.append({"type": "image_url", "image_url": {"url": img["url"]}})
            
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = httpx.post(
                f"{self.qwen_url}/chat/completions",
                headers=headers,
                json={
                    "model": self.qwen_model,
                    "messages": [{"role": "user", "content": content}],
                    "max_tokens": max_tokens
                },
                timeout=180
            )
            
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"].strip()
            return None
            
        except Exception as e:
            print(f"❌ Vision generation failed: {e}")
            return None
    
    def analyze_paper(self, paper: Dict[str, Any], pdf_path: Optional[str] = None,
                     use_vision: bool = True) -> Dict[str, Any]:
        """Analyze paper"""
        if not self.initialized and not self.initialize():
            return {"success": False, "error": "Not initialized"}
        
        try:
            # Load prompt
            from .utils.prompt_loader import PromptLoader
            loader = PromptLoader(self.config.root_dir / "prompts")
            
            # Build analysis prompt
            prompt = loader.get_paper_summary_prompt().format(
                title=paper.get('title', 'Unknown'),
                authors=', '.join(paper.get('authors', [])[:3]),
                abstract=paper.get('abstract', ''),
                categories=', '.join(paper.get('categories', [])),
                url=paper.get('url', ''),
                enhanced_pdf_context=''
            )
            
            # Text analysis
            print(f"🔍 Analyzing: {paper.get('title', 'Unknown')[:60]}...")
            analysis = self.generate(prompt, max_tokens=3000)
            
            result = {
                "success": True,
                "paper_title": paper.get("title"),
                "analysis": analysis
            }
            
            # Vision analysis if requested and PDF available
            if use_vision and pdf_path and self.vision:
                print("👁️ Performing vision analysis...")
                pages = self.vision.smart_page_selection(pdf_path, max_pages=3)
                images = self.vision.pdf_to_images(pdf_path, pages)
                
                if images:
                    vision_prompt = loader.get_vision_prompt(num_pages=len(images))
                    result["visual_analysis"] = self.generate_with_vision(vision_prompt, images)
            
            return result
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def batch_analyze(self, papers: List[Dict[str, Any]], use_vision: bool = False) -> List[Dict[str, Any]]:
        """Batch analyze papers"""
        if not self.initialized and not self.initialize():
            return []
        
        results = []
        for i, paper in enumerate(papers, 1):
            print(f"\n📄 {i}/{len(papers)}: {paper.get('title', 'Unknown')[:50]}")
            result = self.analyze_paper(paper, use_vision=use_vision)
            results.append(result)
        
        return results
    
    def get_status(self) -> Dict[str, Any]:
        """Get system status"""
        return {
            "initialized": self.initialized,
            "qwen_available": self._check_qwen(),
            "qwen_url": self.qwen_url,
            "qwen_model": self.qwen_model,
            "vision": self.vision.is_available() if self.vision else False,
            "database": self.db.is_connected()
        }
