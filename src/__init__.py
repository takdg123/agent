"""
Agent - Research Paper Management System
A class-based architecture for paper ingestion, analysis, and reporting
"""

__version__ = "2.0.0"
__author__ = "Agent Development Team"

from .config import Config
from .io.pdf import PDFProcessor
from .database import DatabaseManager
from .llm import LLMAnalyzer
from .agent import Agent

__all__ = [
    "Config",
    "PDFProcessor", 
    "DatabaseManager",
    "LLMAnalyzer",
    "Agent"
]
