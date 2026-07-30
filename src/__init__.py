"""
TORRI - Research Paper Management System
Refactored modular architecture for paper ingestion, analysis, and reporting
"""

__version__ = "2.0.0"
__author__ = "TORRI Development Team"

# Core modules
from .config import Config
from .database import DatabaseManager

# Only import modules that exist in refactored code
__all__ = [
    "Config",
    "DatabaseManager"
]
