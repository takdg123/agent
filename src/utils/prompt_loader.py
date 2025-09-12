#!/usr/bin/env python3
"""
Prompt Loader Utility
Loads prompt templates from text files using configuration
"""

from pathlib import Path
from typing import Dict, Optional
import yaml

class PromptLoader:
    """Loads and manages prompt templates using configuration"""
    
    def __init__(self, prompts_dir: Path):
        self.prompts_dir = prompts_dir
        self.prompts_dir.mkdir(parents=True, exist_ok=True)
        
        # Load prompt configuration
        self.config = self._load_prompt_config()
    
    def _load_prompt_config(self) -> Dict:
        """Load the prompt configuration file"""
        try:
            config_file = self.prompts_dir.parent / "config" / "prompts.yml"
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
            else:
                print(f"⚠️ Prompt config file not found: {config_file}")
                return {}
        except Exception as e:
            print(f"❌ Error loading prompt config: {e}")
            return {}
    
    def load_prompt(self, prompt_name: str) -> Optional[str]:
        """Load a prompt template by name using configuration"""
        try:
            # Check if prompt is configured and enabled
            if not self.config.get('prompts', {}).get(prompt_name, {}).get('enabled', True):
                print(f"⚠️ Prompt {prompt_name} is disabled in configuration")
                return None
            
            # Get filename from config
            prompt_config = self.config.get('prompts', {}).get(prompt_name, {})
            filename = prompt_config.get('file', f"{prompt_name}.txt")
            
            # Try to load the prompt file
            prompt_file = self.prompts_dir / filename
            if prompt_file.exists():
                encoding = self.config.get('settings', {}).get('default_encoding', 'utf-8')
                with open(prompt_file, 'r', encoding=encoding) as f:
                    return f.read().strip()
            else:
                print(f"⚠️ Prompt file not found: {prompt_file}")
                return None
            
        except Exception as e:
            print(f"❌ Error loading prompt {prompt_name}: {e}")
            return None
    
    def get_paper_summary_prompt(self) -> str:
        """Get the paper summary prompt template"""
        return self.load_prompt("paper_summary") or self._get_default_paper_summary_prompt()
    
    def list_available_prompts(self) -> Dict[str, Dict]:
        """List all available prompts and their configuration"""
        return self.config.get('prompts', {})
    
    def is_prompt_enabled(self, prompt_name: str) -> bool:
        """Check if a prompt is enabled"""
        return self.config.get('prompts', {}).get(prompt_name, {}).get('enabled', True)
    
    def _get_default_paper_summary_prompt(self) -> str:
        """Fallback default prompt if file not found"""
        return """Please provide a comprehensive summary of the following research paper:

Title: {title}
Authors: {authors}
Abstract: {abstract}
Categories: {categories}
URL: {url}

{enhanced_pdf_context}

Please provide a clear, structured summary highlighting the main objectives, methodology, findings, and significance of this research."""
