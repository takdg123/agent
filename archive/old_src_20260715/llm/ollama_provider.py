#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Ollama LLM provider implementation
"""

import httpx
from typing import List, Dict, Any, Optional
from .base import BaseLLMProvider, ModelInfo, Message, ModelCapability

class OllamaProvider(BaseLLMProvider):
    """Ollama LLM provider"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get("base_url", "http://127.0.0.1:11434")
        self.timeout = config.get("timeout", 120)
        self._cached_models = None
    
    def list_models(self) -> List[ModelInfo]:
        """List available Ollama models"""
        if self._cached_models:
            return self._cached_models
        
        try:
            response = httpx.get(f"{self.base_url}/api/tags", timeout=10)
            response.raise_for_status()
            models_data = response.json().get("models", [])
            
            models = []
            for model in models_data:
                name = model.get("name", "")
                
                # Determine capabilities based on model name
                capabilities = [ModelCapability.TEXT_GENERATION, ModelCapability.STREAMING]
                if "vision" in name.lower() or "llava" in name.lower():
                    capabilities.append(ModelCapability.VISION)
                
                models.append(ModelInfo(
                    name=name,
                    provider="ollama",
                    capabilities=capabilities,
                    context_window=model.get("context_length", 4096)
                ))
            
            self._cached_models = models
            return models
            
        except Exception as e:
            print(f"❌ Error listing Ollama models: {e}")
            return []
    
    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> Optional[str]:
        """Generate text using Ollama"""
        target_model = model or self.current_model
        if not target_model:
            available = self.list_models()
            if available:
                target_model = available[0].name
                self.current_model = target_model
            else:
                print("❌ No Ollama models available")
                return None
        
        try:
            response = httpx.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": target_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens,
                        **kwargs
                    }
                },
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "").strip()
            else:
                print(f"❌ Ollama API error: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Error generating with Ollama: {e}")
            return None
    
    def chat(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> Optional[str]:
        """Chat completion using Ollama"""
        target_model = model or self.current_model
        if not target_model:
            available = self.list_models()
            if available:
                target_model = available[0].name
                self.current_model = target_model
            else:
                return None
        
        try:
            # Convert Message objects to dict format
            messages_dict = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]
            
            response = httpx.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": target_model,
                    "messages": messages_dict,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens,
                        **kwargs
                    }
                },
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("message", {}).get("content", "").strip()
            else:
                print(f"❌ Ollama chat API error: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Error in Ollama chat: {e}")
            return None
    
    def is_available(self) -> bool:
        """Check if Ollama is available"""
        try:
            response = httpx.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
