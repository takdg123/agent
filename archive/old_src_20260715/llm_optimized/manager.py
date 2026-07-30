#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Optimized LLM Manager"""

import httpx
from typing import List, Dict, Any, Optional
from .base import Message, ModelInfo

class LLMManager:
    """Manages multiple LLM providers"""
    
    def __init__(self, config):
        self.config = config
        self.providers = {}
        self.current = None
        
        # Initialize providers
        if config.ollama_enabled:
            self.providers["ollama"] = {
                "url": config.ollama_url,
                "api_type": "ollama"
            }
        
        if config.openai_compatible_enabled:
            self.providers["openai"] = {
                "url": config.openai_compatible_url,
                "api_key": config.openai_compatible_api_key,
                "model": config.openai_compatible_model,
                "api_type": "openai"
            }
    
    def select_best_model(self, prefer_vision: bool = False) -> Optional[tuple]:
        """Select best available provider"""
        priority = ["openai", "ollama"] if prefer_vision else self.config.provider_priority
        
        for provider in priority:
            if provider in self.providers and self._check_available(provider):
                models = self._list_models(provider)
                if models:
                    self.current = (provider, models[0].name)
                    return self.current
        return None
    
    def generate(self, prompt: str, provider: Optional[str] = None, 
                max_tokens: int = 2000, **kwargs) -> Optional[str]:
        """Generate text"""
        if not provider:
            provider = self.current[0] if self.current else None
        if not provider and not self.select_best_model():
            return None
        
        prov = self.providers.get(provider or self.current[0])
        if not prov:
            return None
        
        try:
            if prov["api_type"] == "ollama":
                return self._ollama_generate(prov, prompt, max_tokens, **kwargs)
            else:
                return self._openai_generate(prov, prompt, max_tokens, **kwargs)
        except Exception as e:
            print(f"❌ Generation failed: {e}")
            return None
    
    def chat(self, messages: List[Message], provider: Optional[str] = None,
            max_tokens: int = 2000, **kwargs) -> Optional[str]:
        """Chat completion"""
        if not provider:
            provider = self.current[0] if self.current else None
        if not provider and not self.select_best_model():
            return None
        
        prov = self.providers.get(provider or self.current[0])
        if not prov:
            return None
        
        try:
            msgs = [{"role": m.role, "content": m.content} for m in messages]
            
            if prov["api_type"] == "ollama":
                response = httpx.post(
                    f"{prov['url']}/api/chat",
                    json={"model": self._get_model(provider), "messages": msgs, 
                          "stream": False, "options": {"num_predict": max_tokens}},
                    timeout=120
                )
                return response.json().get("message", {}).get("content", "").strip()
            else:
                headers = {"Authorization": f"Bearer {prov.get('api_key', 'EMPTY')}"}
                response = httpx.post(
                    f"{prov['url']}/chat/completions",
                    headers=headers,
                    json={"model": prov["model"], "messages": msgs, "max_tokens": max_tokens},
                    timeout=120
                )
                return response.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        except Exception as e:
            print(f"❌ Chat failed: {e}")
            return None
    
    def generate_with_vision(self, text_prompt: str, image_data: List[Dict[str, Any]], 
                            provider: Optional[str] = None, **kwargs) -> Optional[str]:
        """Generate with vision"""
        if not provider:
            self.select_best_model(prefer_vision=True)
            provider = self.current[0] if self.current else None
        
        if not provider or provider not in self.providers:
            return None
        
        content = [{"type": "text", "text": text_prompt}]
        for img in image_data:
            content.append({"type": "image_url", "image_url": {"url": img["url"]}})
        
        return self.chat([Message(role="user", content=content)], provider, **kwargs)
    
    def _ollama_generate(self, prov: Dict, prompt: str, max_tokens: int, **kwargs) -> str:
        """Ollama generation"""
        response = httpx.post(
            f"{prov['url']}/api/generate",
            json={"model": self._get_model("ollama"), "prompt": prompt, 
                  "stream": False, "options": {"num_predict": max_tokens}},
            timeout=120
        )
        return response.json().get("response", "").strip()
    
    def _openai_generate(self, prov: Dict, prompt: str, max_tokens: int, **kwargs) -> str:
        """OpenAI-compatible generation"""
        return self.chat([Message(role="user", content=prompt)], "openai", max_tokens, **kwargs)
    
    def _list_models(self, provider: str) -> List[ModelInfo]:
        """List models for provider"""
        try:
            prov = self.providers[provider]
            if prov["api_type"] == "ollama":
                response = httpx.get(f"{prov['url']}/api/tags", timeout=5)
                models = response.json().get("models", [])
                return [ModelInfo(m["name"], provider, "vision" in m["name"].lower()) 
                       for m in models]
            else:
                return [ModelInfo(prov["model"], provider, "vl" in prov["model"].lower())]
        except:
            return []
    
    def _get_model(self, provider: str) -> str:
        """Get model name for provider"""
        models = self._list_models(provider)
        return models[0].name if models else "llama4:latest"
    
    def _check_available(self, provider: str) -> bool:
        """Check if provider is available"""
        try:
            prov = self.providers[provider]
            url = f"{prov['url']}/api/tags" if prov["api_type"] == "ollama" else f"{prov['url']}/models"
            response = httpx.get(url, timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def is_available(self) -> bool:
        """Check if any provider available"""
        return any(self._check_available(p) for p in self.providers)
    
    def get_status(self) -> Dict[str, Any]:
        """Get status"""
        return {
            "providers": {
                name: {"available": self._check_available(name), 
                       "models": [m.name for m in self._list_models(name)]}
                for name in self.providers
            },
            "current": self.current
        }
