#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM module for multi-provider support
"""

from .base import BaseLLMProvider, ModelInfo, Message, ModelCapability
from .ollama_provider import OllamaProvider
from .openai_compatible_provider import OpenAICompatibleProvider
from .manager import LLMManager

# Backward compatibility alias
LLMAnalyzer = LLMManager

__all__ = [
    'BaseLLMProvider',
    'ModelInfo',
    'Message',
    'ModelCapability',
    'OllamaProvider',
    'OpenAICompatibleProvider',
    'LLMManager',
    'LLMAnalyzer'  # Backward compatibility
]
