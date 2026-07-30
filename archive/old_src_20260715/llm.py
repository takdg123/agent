#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM analyzer class for TORRI system
Handles all Ollama interactions and LLM model management
"""

import httpx
from typing import List, Dict, Any, Optional

class LLMAnalyzer:
    """Handles all LLM interactions for TORRI system"""
    
    def __init__(self, config):
        self.config = config
        self.ollama_url = config.ollama_url
        self.preferred_models = config.preferred_models
        self.current_model = None
        
    def get_available_model(self) -> Optional[str]:
        """Get available LLM model from Ollama, prioritizing preferred models"""
        try:
            response = httpx.get(f"{self.ollama_url}/api/tags", timeout=10)
            response.raise_for_status()
            models = response.json().get("models", [])
            
            # Check preferred models in order
            for preferred in self.preferred_models:
                if any(m["name"] == preferred for m in models):
                    self.current_model = preferred
                    print(f"✅ Using LLM model: {preferred}")
                    return preferred
            
            # If none of preferred models found, return first available
            if models:
                self.current_model = models[0]["name"]
                print(f"⚠️ Using fallback model: {self.current_model}")
                return self.current_model
            
            print("❌ No LLM models available")
            return None
            
        except Exception as e:
            print(f"❌ Error checking LLM models: {e}")
            return None
    
    def generate_summary(self, content: str, prompt: str, model: Optional[str] = None) -> Optional[str]:
        """Generate summary using LLM"""
        try:
            # Only get available model if we don't have one cached and none provided
            if not model and not self.current_model:
                model = self.get_available_model()
            elif not model:
                model = self.current_model
            
            if not model:
                print("❌ No available LLM model")
                return None
            
            # Prepare the full prompt
            full_prompt = f"{prompt}\n\nContent to analyze:\n{content}" if content else prompt
            
            response = httpx.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": model,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "max_tokens": 2000
                    }
                },
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "").strip()
            else:
                print(f"❌ LLM API error: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Error generating summary: {e}")
            return None
    
    def generate_paper_summary(self, paper: Dict[str, Any], 
                              enhanced_pdf_data: Dict[str, Any]) -> Optional[str]:
        """Generate individual paper summary"""
        try:
            # Load prompt template
            from .utils import PromptLoader
            
            prompt_loader = PromptLoader(self.config.root_dir / "prompts")
            
            prompt_template = prompt_loader.get_paper_summary_prompt()
            
            # Format the prompt with paper data
            prompt = prompt_template.format(
                title=paper.get('title', 'Unknown'),
                authors=', '.join(paper.get('authors', [])),
                abstract=paper.get('abstract', 'No abstract available'),
                categories=', '.join(paper.get('categories', [])),
                url=paper.get('url', 'No URL available'),
                enhanced_pdf_context=enhanced_pdf_data.get('content', '')
            )
            
            return self.generate_summary("", prompt)
            
        except Exception as e:
            print(f"⚠️ Error loading prompt template: {e}")
            # Fallback to simple prompt
            prompt = f"""Please provide a summary of this research paper:

Title: {paper.get('title', 'Unknown')}
Authors: {', '.join(paper.get('authors', []))}
Abstract: {paper.get('abstract', 'No abstract available')}

Please summarize the main objectives, methodology, findings, and significance."""
            
            return self.generate_summary("", prompt)
    
    def test_model_availability(self, model: str) -> bool:
        """Test if a specific model is available"""
        try:
            response = httpx.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": model,
                    "prompt": "test",
                    "stream": False
                },
                timeout=10
            )
            response.raise_for_status()
            return True
        except Exception:
            return False
    
    def get_model_info(self, model: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific model"""
        try:
            response = httpx.get(f"{self.ollama_url}/api/show", 
                               params={"name": model}, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Error getting model info for {model}: {e}")
            return None
    
    def get_current_model(self) -> Optional[str]:
        """Get the currently selected model"""
        return self.current_model
    
    def is_available(self) -> bool:
        """Check if LLM analysis is available"""
        return self.current_model is not None
    
    def ask_question(self, question: str, model: Optional[str] = None) -> Optional[str]:
        """Ask a direct question to the LLM model"""
        try:
            # Only get available model if we don't have one cached and none provided
            if not model and not self.current_model:
                model = self.get_available_model()
            elif not model:
                model = self.current_model
            
            if not model:
                print("❌ No available LLM model")
                return None
            
            # Simple prompt for direct questions
            prompt = f"Please answer the following question:\n\n{question}"
            
            response = httpx.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "max_tokens": 2000
                    }
                },
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "").strip()
            else:
                print(f"❌ LLM API error: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Error asking question: {e}")
            return None
