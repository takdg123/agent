#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Optimized prompt loader"""

from pathlib import Path
from typing import Dict

class PromptLoader:
    """Load and cache prompts"""
    
    def __init__(self, prompt_dir: Path):
        self.prompt_dir = prompt_dir
        self._cache = {}
    
    def _load(self, filename: str) -> str:
        """Load and cache prompt"""
        if filename not in self._cache:
            path = self.prompt_dir / filename
            if path.exists():
                self._cache[filename] = path.read_text()
            else:
                self._cache[filename] = ""
        return self._cache[filename]
    
    def get_grb_expert_prompt(self, **kwargs) -> str:
        """Get GRB expert prompt"""
        return self._load("grb_expert.txt").format(**kwargs)
    
    def get_kilonova_expert_prompt(self, **kwargs) -> str:
        """Get kilonova expert prompt"""
        return self._load("kilonova_expert.txt").format(**kwargs)
    
    def get_astrophysicist_prompt(self, **kwargs) -> str:
        """Get astrophysicist synthesis prompt"""
        return self._load("astrophysicist_synthesis.txt").format(**kwargs)
    
    def get_language_expert_prompt(self, **kwargs) -> str:
        """Get language expert prompt"""
        return self._load("language_expert.txt").format(**kwargs)
    
    def get_critic_prompt(self, **kwargs) -> str:
        """Get critic prompt"""
        return self._load("critic.txt").format(**kwargs)
    
    def get_writer_prompt(self, **kwargs) -> str:
        """Get writer prompt"""
        return self._load("writer.txt").format(**kwargs)
    
    def get_report_fixer_en_prompt(self, **kwargs) -> str:
        """Get report fixer English prompt"""
        return self._load("report_fixer_en.txt").format(**kwargs)
    
    def get_report_fixer_ko_prompt(self, **kwargs) -> str:
        """Get report fixer Korean prompt"""
        return self._load("report_fixer_ko.txt").format(**kwargs)
    
    def get_report_validator_prompt(self, **kwargs) -> str:
        """Get report validator prompt"""
        return self._load("report_validator.txt").format(**kwargs)
