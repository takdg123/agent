#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OpenAI-compatible API provider (works with Qwen, vLLM, etc.)
"""

import httpx
from typing import List, Dict, Any, Optional
from .base import BaseLLMProvider, ModelInfo, Message, ModelCapability

class OpenAICompatibleProvider(BaseLLMProvider):
    """OpenAI-compatible API provider for Qwen and other models"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get("base_url", "http://localhost:8000/v1")
        self.api_key = config.get("api_key", "EMPTY")
        self.timeout = config.get("timeout", 120)
        self.model_name = config.get("model_name", "Qwen2.5-VL-7B-Instruct")
        self._cached_models = None
    
    def list_models(self) -> List[ModelInfo]:
        """List available models from the API"""
        if self._cached_models:
            return self._cached_models
        
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = httpx.get(
                f"{self.base_url}/models",
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            models_data = response.json().get("data", [])
            
            models = []
            for model in models_data:
                model_id = model.get("id", "")
                
                # Determine capabilities
                capabilities = [ModelCapability.TEXT_GENERATION]
                if "vision" in model_id.lower() or "vl" in model_id.lower():
                    capabilities.append(ModelCapability.VISION)
                if model.get("streaming", True):
                    capabilities.append(ModelCapability.STREAMING)
                
                models.append(ModelInfo(
                    name=model_id,
                    provider="openai_compatible",
                    capabilities=capabilities,
                    context_window=model.get("context_length", 32768)
                ))
            
            self._cached_models = models
            
            # If no models from API, use configured default
            if not models and self.model_name:
                models = [ModelInfo(
                    name=self.model_name,
                    provider="openai_compatible",
                    capabilities=[ModelCapability.TEXT_GENERATION, ModelCapability.VISION],
                    context_window=32768
                )]
                self._cached_models = models
            
            return models
            
        except Exception as e:
            print(f"⚠️ Error listing models (using default {self.model_name}): {e}")
            # Return default model
            default_model = ModelInfo(
                name=self.model_name,
                provider="openai_compatible",
                capabilities=[ModelCapability.TEXT_GENERATION, ModelCapability.VISION],
                context_window=32768
            )
            return [default_model]
    
    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> Optional[str]:
        """Generate text using OpenAI-compatible API"""
        # Convert to chat format
        messages = [Message(role="user", content=prompt)]
        return self.chat(messages, model, temperature, max_tokens, **kwargs)
    
    def chat(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> Optional[str]:
        """Chat completion using OpenAI-compatible API"""
        target_model = model or self.current_model or self.model_name
        
        try:
            # Convert Message objects to OpenAI format
            messages_dict = []
            for msg in messages:
                if isinstance(msg.content, str):
                    messages_dict.append({"role": msg.role, "content": msg.content})
                else:
                    # Multimodal content (text + images)
                    messages_dict.append({"role": msg.role, "content": msg.content})
            
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = httpx.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json={
                    "model": target_model,
                    "messages": messages_dict,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    **kwargs
                },
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            else:
                print(f"❌ API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error in chat completion: {e}")
            return None
    
    def is_available(self) -> bool:
        """Check if the API is available"""
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = httpx.get(f"{self.base_url}/models", headers=headers, timeout=5)
            return response.status_code == 200
        except Exception:
            return False
