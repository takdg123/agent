#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Base LLM interfaces"""

from dataclasses import dataclass
from typing import Union, List, Dict, Any

@dataclass
class Message:
    """LLM message"""
    role: str
    content: Union[str, List[Dict[str, Any]]]

@dataclass
class ModelInfo:
    """Model information"""
    name: str
    provider: str
    supports_vision: bool = False
