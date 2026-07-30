#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Base LLM interface for multi-provider support
Provides abstraction layer for different LLM backends
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum

class ModelCapability(Enum):
    """Capabilities that an LLM model can have"""
    TEXT_GENERATION = "text_generation"
    VISION = "vision"
    FUNCTION_CALLING = "function_calling"
    STREAMING = "streaming"
    EMBEDDING = "embedding"

@dataclass
class Message:
    """Represents a message in a conversation"""
    role: str  # system, user, assistant
    content: Union[str, List[Dict[str, Any]]]  # text or multimodal content
    
@dataclass
class ModelInfo:
    """Information about an LLM model"""
    name: str
    provider: str
    capabilities: List[ModelCapability]
    context_window: int = 4096
    max_output_tokens: int = 2048

class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.current_model = None
    
    @abstractmethod
    def list_models(self) -> List[ModelInfo]:
        """List available models from this provider"""
        pass
    
    @abstractmethod
    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> Optional[str]:
        """Generate text completion"""
        pass
    
    @abstractmethod
    def chat(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> Optional[str]:
        """Chat completion with message history"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available"""
        pass
    
    def supports_vision(self, model: Optional[str] = None) -> bool:
        """Check if model supports vision"""
        models = self.list_models()
        target = model or self.current_model
        for m in models:
            if m.name == target:
                return ModelCapability.VISION in m.capabilities
        return False
    
    def get_current_model(self) -> Optional[str]:
        """Get currently selected model"""
        return self.current_model
    
    def set_model(self, model_name: str) -> bool:
        """Set the current model"""
        models = self.list_models()
        if any(m.name == model_name for m in models):
            self.current_model = model_name
            return True
        return False
