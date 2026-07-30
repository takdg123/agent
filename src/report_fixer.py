#!/usr/bin/env python3
"""
Report Auto-Fixer for TORRI
Automatically regenerates reports when validation fails
"""

from typing import Dict, List
from pathlib import Path
import requests
from .utils.prompt_loader import PromptLoader

class ReportFixer:
    """Fixes reports based on validation feedback"""
    
    def __init__(self, ollama_url="http://localhost:11434", model="qwen2.5:7b", config=None):
        self.ollama_url = ollama_url
        self.model = model
        # Initialize prompt loader
        prompt_dir = Path(config.root_dir) / "prompts" if config else Path(__file__).parent.parent / "prompts"
        self.prompt_loader = PromptLoader(prompt_dir)
    
    def analyze_issues(self, validation_result: Dict) -> str:
        """Analyze validation issues and create improvement plan"""
        issues = validation_result.get('issues', [])
        warnings = validation_result.get('warnings', [])
        
        problem_summary = []
        
        if issues:
            problem_summary.append("Critical Issues:")
            for issue in issues:
                problem_summary.append(f"  - {issue}")
        
        if warnings:
            problem_summary.append("Warnings:")
            for warning in warnings:
                problem_summary.append(f"  - {warning}")
        
        return "\n".join(problem_summary)
    
    def suggest_improvements(self, validation_result: Dict) -> List[str]:
        """Generate specific improvement suggestions"""
        improvements = []
        issues = validation_result.get('issues', [])
        warnings = validation_result.get('warnings', [])
        
        for issue in issues:
            if "Structure" in issue:
                improvements.append("Fix HTML structure: Ensure all tags are properly closed")
            elif "Content" in issue and "No papers" in issue:
                improvements.append("Regenerate with papers - check filtering criteria")
            elif "Language" in issue:
                improvements.append("Ensure both English and Korean content are generated")
            elif "Format" in issue:
                improvements.append("Fix HTML formatting errors")
        
        for warning in warnings:
            if "Korean" in warning:
                improvements.append("Generate more comprehensive Korean summaries")
            elif "Tag mismatch" in warning:
                improvements.append("Balance HTML tags properly")
            elif "Links" in warning:
                improvements.append("Verify all arXiv links are valid")
        
        return improvements
    
    def regenerate_paper_analysis(self, paper_data, model, attempt_num):
        """Regenerate analysis with focus on quality"""
        url = "http://localhost:11434/api/generate"
        
        # Use prompt loader
        prompt_en = self.prompt_loader.get_report_fixer_en_prompt(
            attempt_num=attempt_num,
            title=paper_data.get('title', 'Unknown'),
            authors=', '.join(paper_data.get('authors', [])[:5]),
            abstract=paper_data.get('abstract', 'No abstract')[:1000]
        )

        prompt_ko = self.prompt_loader.get_report_fixer_ko_prompt(
            attempt_num=attempt_num,
            title=paper_data.get('title', 'Unknown'),
            authors=', '.join(paper_data.get('authors', [])[:5]),
            abstract=paper_data.get('abstract', 'No abstract')[:1000]
        )

        try:
            # English
            payload_en = {"model": model, "prompt": prompt_en, "stream": False}
            response_en = requests.post(url, json=payload_en, timeout=150)
            analysis_en = response_en.json().get("response", "") if response_en.status_code == 200 else ""
            
            # Korean
            payload_ko = {"model": model, "prompt": prompt_ko, "stream": False}
            response_ko = requests.post(url, json=payload_ko, timeout=150)
            analysis_ko = response_ko.json().get("response", "") if response_ko.status_code == 200 else ""
            
            # Quality check
            if len(analysis_en) < 200:
                analysis_en += "\n\n[Note: Analysis regenerated for quality improvement]"
            
            if len(analysis_ko) < 100:
                analysis_ko += "\n\n[참고: 품질 개선을 위해 재생성됨]"
            
            return {
                "english": analysis_en,
                "korean": analysis_ko
            }
            
        except Exception as e:
            return {
                "english": f"Error in regeneration: {str(e)}",
                "korean": f"재생성 오류: {str(e)}"
            }
