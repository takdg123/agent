#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM Manager for coordinating multiple providers
"""

from typing import List, Dict, Any, Optional
from .base import BaseLLMProvider, ModelInfo, Message
from .ollama_provider import OllamaProvider
from .openai_compatible_provider import OpenAICompatibleProvider

class LLMManager:
    """Manages multiple LLM providers and handles fallback"""
    
    def __init__(self, config):
        self.config = config
        self.providers: Dict[str, BaseLLMProvider] = {}
        self._initialize_providers()
        self.current_provider = None
        self.current_model = None
    
    def _initialize_providers(self):
        """Initialize all configured providers"""
        # Initialize Ollama provider
        if self.config.ollama_enabled:
            try:
                ollama_config = {
                    "base_url": self.config.ollama_url,
                    "timeout": self.config.llm_timeout
                }
                self.providers["ollama"] = OllamaProvider(ollama_config)
                print("✅ Ollama provider initialized")
            except Exception as e:
                print(f"⚠️ Failed to initialize Ollama provider: {e}")
        
        # Initialize OpenAI-compatible provider (Qwen, vLLM, etc.)
        if self.config.openai_compatible_enabled:
            try:
                openai_config = {
                    "base_url": self.config.openai_compatible_url,
                    "api_key": self.config.openai_compatible_api_key,
                    "model_name": self.config.openai_compatible_model,
                    "timeout": self.config.llm_timeout
                }
                self.providers["openai_compatible"] = OpenAICompatibleProvider(openai_config)
                print("✅ OpenAI-compatible provider initialized")
            except Exception as e:
                print(f"⚠️ Failed to initialize OpenAI-compatible provider: {e}")
    
    def get_available_providers(self) -> List[str]:
        """Get list of available provider names"""
        return [name for name, provider in self.providers.items() if provider.is_available()]
    
    def get_all_models(self) -> Dict[str, List[ModelInfo]]:
        """Get all available models from all providers"""
        all_models = {}
        for name, provider in self.providers.items():
            if provider.is_available():
                models = provider.list_models()
                if models:
                    all_models[name] = models
        return all_models
    
    def select_best_model(self, prefer_vision: bool = False) -> Optional[tuple]:
        """Select the best available model
        
        Returns:
            tuple: (provider_name, model_name) or None
        """
        all_models = self.get_all_models()
        
        # Priority order for providers
        provider_priority = self.config.provider_priority or ["openai_compatible", "ollama"]
        
        for provider_name in provider_priority:
            if provider_name not in all_models:
                continue
            
            models = all_models[provider_name]
            
            if prefer_vision:
                # Find vision-capable model
                for model in models:
                    if provider_name == "openai_compatible":
                        # Prefer OpenAI-compatible for vision
                        self.current_provider = provider_name
                        self.current_model = model.name
                        self.providers[provider_name].set_model(model.name)
                        return (provider_name, model.name)
            else:
                # Just get first available model
                if models:
                    self.current_provider = provider_name
                    self.current_model = models[0].name
                    self.providers[provider_name].set_model(models[0].name)
                    return (provider_name, models[0].name)
        
        return None
    
    def generate(
        self,
        prompt: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> Optional[str]:
        """Generate text using specified or best available provider"""
        # Determine provider
        if provider and provider in self.providers:
            target_provider = self.providers[provider]
        elif self.current_provider:
            target_provider = self.providers[self.current_provider]
        else:
            # Auto-select best provider
            selection = self.select_best_model()
            if not selection:
                print("❌ No available LLM providers")
                return None
            target_provider = self.providers[selection[0]]
        
        return target_provider.generate(prompt, model, temperature, max_tokens, **kwargs)
    
    def chat(
        self,
        messages: List[Message],
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> Optional[str]:
        """Chat completion using specified or best available provider"""
        # Determine provider
        if provider and provider in self.providers:
            target_provider = self.providers[provider]
        elif self.current_provider:
            target_provider = self.providers[self.current_provider]
        else:
            # Auto-select best provider
            selection = self.select_best_model()
            if not selection:
                print("❌ No available LLM providers")
                return None
            target_provider = self.providers[selection[0]]
        
        return target_provider.chat(messages, model, temperature, max_tokens, **kwargs)
    
    def generate_with_vision(
        self,
        text_prompt: str,
        image_data: List[Dict[str, Any]],
        provider: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> Optional[str]:
        """Generate text with vision (multimodal input)"""
        # Select vision-capable provider
        if not provider:
            selection = self.select_best_model(prefer_vision=True)
            if not selection:
                print("❌ No vision-capable providers available")
                return None
            provider = selection[0]
        
        if provider not in self.providers:
            print(f"❌ Provider {provider} not available")
            return None
        
        target_provider = self.providers[provider]
        
        # Build multimodal message
        content = [{"type": "text", "text": text_prompt}]
        for img in image_data:
            content.append({
                "type": "image_url",
                "image_url": {"url": img["url"]}
            })
        
        messages = [Message(role="user", content=content)]
        return target_provider.chat(messages, model, **kwargs)
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of all providers"""
        status = {
            "providers": {},
            "current_provider": self.current_provider,
            "current_model": self.current_model
        }
        
        for name, provider in self.providers.items():
            status["providers"][name] = {
                "available": provider.is_available(),
                "models": [m.name for m in provider.list_models()],
                "current_model": provider.get_current_model()
            }
        
        return status
    
    def is_available(self) -> bool:
        """Check if any provider is available"""
        return len(self.get_available_providers()) > 0
    
    def get_current_model(self) -> Optional[str]:
        """Get current model name"""
        return self.current_model
