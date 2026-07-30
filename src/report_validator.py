#!/usr/bin/env python3
"""
Report Quality Validator for TORRI
Reviews generated reports for quality and completeness
Uses both rule-based checks AND LLM-based intelligent review
"""

import re
from typing import Dict, List, Tuple
from datetime import datetime
from pathlib import Path
import requests
import json
from bs4 import BeautifulSoup
from .utils.prompt_loader import PromptLoader

class ReportValidator:
    """Validates report quality before sending using rules + LLM"""
    
    def __init__(self, ollama_url="http://localhost:11434", model="qwen2.5:7b", config=None):
        self.ollama_url = ollama_url
        self.model = model
        self.use_llm = True  # Enable LLM validation
        # Initialize prompt loader
        prompt_dir = Path(config.root_dir) / "prompts" if config else Path(__file__).parent.parent / "prompts"
        self.prompt_loader = PromptLoader(prompt_dir)
    
    def validate_report(self, html_content: str, papers_count: int) -> Dict:
        """
        Comprehensive validation of the generated report
        Uses both rule-based and LLM-based validation
        
        Returns: {
            'valid': bool,
            'issues': List[str],
            'warnings': List[str],
            'quality_score': int (0-100),
            'recommendations': List[str],
            'llm_feedback': Dict  # LLM's detailed assessment
        }
        """
        issues = []
        warnings = []
        recommendations = []
        
        print("   📏 Running rule-based checks...")
        
        # 1. Structure validation
        structure_ok = self._validate_structure(html_content, issues, warnings)
        
        # 2. Content validation
        content_ok = self._validate_content(html_content, papers_count, issues, warnings)
        
        # 3. Language validation
        language_ok = self._validate_languages(html_content, issues, warnings)
        
        # 4. Format validation
        format_ok = self._validate_format(html_content, issues, warnings)
        
        # 5. Link validation
        links_ok = self._validate_links(html_content, warnings)
        
        # Calculate rule-based score
        rule_score = self._calculate_quality_score(
            structure_ok, content_ok, language_ok, format_ok, links_ok,
            len(issues), len(warnings)
        )
        
        # 6. LLM-based intelligent validation
        llm_feedback = {}
        llm_score = rule_score  # Default to rule score
        
        if self.use_llm:
            print("   🤖 Running LLM-based quality review...")
            llm_feedback = self._llm_validate_report(html_content, papers_count)
            llm_score = llm_feedback.get('score', rule_score)
            
            # Add LLM findings to issues/warnings
            if llm_feedback.get('critical_issues'):
                for issue in llm_feedback['critical_issues']:
                    issues.append(f"LLM: {issue}")
            
            if llm_feedback.get('suggestions'):
                for suggestion in llm_feedback['suggestions'][:3]:  # Top 3
                    warnings.append(f"LLM: {suggestion}")
        
        # Final score: weighted average (60% rule-based, 40% LLM)
        final_score = int(rule_score * 0.6 + llm_score * 0.4)
        
        # Generate recommendations
        if final_score < 70:
            recommendations.append("Consider regenerating report - quality score below threshold")
        if len(issues) > 0:
            recommendations.append("Fix critical issues before sending")
        if papers_count == 0:
            recommendations.append("No papers analyzed - check filtering criteria")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'quality_score': final_score,
            'recommendations': recommendations,
            'paper_count': papers_count,
            'llm_feedback': llm_feedback,
            'rule_score': rule_score,
            'llm_score': llm_score
        }
    
    def _validate_structure(self, html: str, issues: List[str], warnings: List[str]) -> bool:
        """Validate HTML structure"""
        critical_elements = [
            ('<html', 'Missing <html> tag'),
            ('<head', 'Missing <head> tag'),
            ('<body', 'Missing <body> tag'),
            ('</html>', 'Missing closing </html> tag')
        ]
        
        # Check critical elements
        ok = True
        for element, error_msg in critical_elements:
            if element not in html:
                issues.append(f"Structure: {error_msg}")
                ok = False
        
        # Check optional but recommended elements (warnings only)
        if '<style' not in html and 'style=' not in html:
            warnings.append("Structure: No CSS styling found (recommended for formatting)")
        
        return ok
    
    def _validate_content(self, html: str, expected_papers: int, issues: List[str], warnings: List[str]) -> bool:
        """Validate content completeness"""
        ok = True
        
        # Check for paper entries (try multiple patterns).
        # 'card' is the current per-paper container; 'paper' is kept so older
        # reports on disk still validate.
        paper_patterns = [
            r'<div class="paper">',
            r'<div class=["\']paper["\']',
            r'<div[^>]*class=["\'][^"\']*\bcard\b[^"\']*["\']',
            r'<article[^>]*class=["\'][^"\']*paper[^"\']*["\']'
        ]
        
        actual_papers = 0
        for pattern in paper_patterns:
            count = len(re.findall(pattern, html, re.IGNORECASE))
            actual_papers = max(actual_papers, count)
        
        if actual_papers == 0:
            issues.append("Content: No papers found in report")
            ok = False
        elif abs(actual_papers - expected_papers) > 2:  # Allow small variance
            warnings.append(f"Content: Expected {expected_papers} papers, found {actual_papers}")
        
        # Check for analysis content (case-insensitive, more flexible)
        analysis_pattern = r'\b(analysis|analyze|summary|review|findings?)\b'
        analysis_matches = len(re.findall(analysis_pattern, html, re.IGNORECASE))
        
        if analysis_matches < 3:  # Expect at least a few analysis mentions
            issues.append("Content: Insufficient analysis content found")
            ok = False
        
        # Check for Korean content markers (more flexible)
        korean_markers = ['한국어', '요약', 'Korean', '🇰🇷']
        has_korean_marker = any(marker in html for marker in korean_markers)
        
        if not has_korean_marker:
            warnings.append("Content: Korean section markers may be missing")
        
        return ok
    
    def _validate_languages(self, html: str, issues: List[str], warnings: List[str]) -> bool:
        """Validate bilingual content"""
        ok = True
        
        # Check for English content (total count, not consecutive)
        english_chars = re.findall(r'[A-Za-z]+', html)
        total_english = sum(len(word) for word in english_chars)
        
        if total_english < 200:  # Need at least 200 English chars total (was 50 consecutive)
            issues.append(f"Language: Insufficient English content (found {total_english} chars, need 200+)")
            ok = False
        elif total_english < 500:
            warnings.append(f"Language: Limited English content (found {total_english} chars)")
        
        # Check for Korean content (total count, more flexible)
        korean_chars = re.findall(r'[\uAC00-\uD7A3]+', html)
        total_korean = sum(len(word) for word in korean_chars)
        
        if total_korean < 30:  # Need at least 30 Korean chars total (was 10 consecutive)
            warnings.append(f"Language: Limited Korean content (found {total_korean} chars, recommend 30+)")
        
        return ok
    
    def _validate_format(self, html: str, issues: List[str], warnings: List[str]) -> bool:
        """Validate formatting and styling"""
        ok = True
        
        # Check for broken tags (more lenient threshold)
        open_tags = len(re.findall(r'<(?!/)(?!!)(?!\?)[\w-]+', html))
        close_tags = len(re.findall(r'</[\w-]+>', html))
        tag_diff = abs(open_tags - close_tags)
        
        if tag_diff > 10:  # Increased from 5 to 10 for more tolerance
            warnings.append(f"Format: Possible tag mismatch (open: {open_tags}, close: {close_tags}, diff: {tag_diff})")
        
        # Check for obvious formatting errors
        if '<<' in html or '>>' in html:
            issues.append("Format: Malformed HTML tags detected (double brackets)")
            ok = False
        
        # Check for severely broken HTML
        if '<html<' in html or '>html>' in html:
            issues.append("Format: Severely malformed HTML structure")
            ok = False
        
        # CSS brace balance (warning only)
        brace_diff = abs(html.count('{') - html.count('}'))
        if brace_diff > 2:  # Allow small variance
            warnings.append(f"Format: Unbalanced braces in CSS (diff: {brace_diff})")
        
        return ok
    
    def _validate_links(self, html: str, warnings: List[str]) -> bool:
        """Validate arXiv links"""
        # Find all arXiv links
        arxiv_links = re.findall(r'https://arxiv\.org/(?:abs|pdf)/(\S+)', html)
        
        if len(arxiv_links) == 0:
            warnings.append("Links: No arXiv links found")
            return False
        
        # Check for malformed IDs
        for link in arxiv_links:
            if not re.match(r'\d{4}\.\d{4,5}', link.split('.')[0]):
                warnings.append(f"Links: Potentially malformed arXiv ID: {link}")
        
        return True
    
    def _calculate_quality_score(self, structure: bool, content: bool, language: bool, 
                                  format: bool, links: bool, issues_count: int, warnings_count: int) -> int:
        """Calculate overall quality score (0-100)"""
        score = 0
        
        # Component scores
        if structure: score += 25
        if content: score += 30
        if language: score += 20
        if format: score += 15
        if links: score += 10
        
        # Penalties
        score -= (issues_count * 10)
        score -= (warnings_count * 3)
        
        return max(0, min(100, score))
    
    def _llm_validate_report(self, html_content: str, papers_count: int) -> Dict:
        """
        Use LLM to intelligently validate report quality
        Checks: coherence, completeness, professionalism, bilingual quality
        """
        # Extract text content from HTML for LLM review
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            text_content = soup.get_text()[:8000]  # Limit for LLM context
        except:
            text_content = html_content[:8000]
        
        # Extract sample papers for detailed review
        paper_samples = self._extract_paper_samples(html_content, num_samples=3)
        
        prompt = self.prompt_loader.get_report_validator_prompt(
            papers_count=papers_count,
            report_length=len(html_content),
            content_length=len(text_content),
            text_content=text_content
        )

        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json"
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                llm_response = result.get('response', '{}')
                
                # Parse JSON response
                try:
                    feedback = json.loads(llm_response)
                    return feedback
                except json.JSONDecodeError:
                    # Try to extract JSON from response
                    import re
                    json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
                    if json_match:
                        feedback = json.loads(json_match.group())
                        return feedback
                    
                    return {
                        'score': 70,
                        'critical_issues': [],
                        'suggestions': ['LLM response parsing failed'],
                        'strengths': [],
                        'overall_assessment': 'Unable to parse LLM feedback'
                    }
            else:
                return {'score': 70, 'critical_issues': [], 'suggestions': []}
                
        except Exception as e:
            print(f"      ⚠️  LLM validation error: {e}")
            return {
                'score': 70,
                'critical_issues': [],
                'suggestions': [f'LLM validation failed: {str(e)}'],
                'strengths': [],
                'overall_assessment': 'LLM validation unavailable'
            }
    
    def _extract_paper_samples(self, html_content: str, num_samples: int = 3) -> List[str]:
        """Extract sample paper sections for detailed LLM review"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            papers = soup.find_all('div', class_='card') or soup.find_all('div', class_='paper')

            samples = []
            for i, paper in enumerate(papers[:num_samples]):
                samples.append(paper.get_text()[:500])  # First 500 chars of each
            
            return samples
        except:
            return []
    
    def print_validation_report(self, validation_result: Dict):
        """Pretty print validation results with LLM feedback"""
        print("\n" + "="*70)
        print("📋 REPORT QUALITY VALIDATION")
        print("="*70)
        
        # Quality scores
        final_score = validation_result['quality_score']
        rule_score = validation_result.get('rule_score', final_score)
        llm_score = validation_result.get('llm_score', final_score)
        
        if final_score >= 90:
            emoji = "🟢"
            status = "EXCELLENT"
        elif final_score >= 70:
            emoji = "🟡"
            status = "GOOD"
        else:
            emoji = "🔴"
            status = "NEEDS IMPROVEMENT"
        
        print(f"\n{emoji} Overall Score: {final_score}/100 ({status})")
        print(f"   📏 Rule-based: {rule_score}/100")
        print(f"   🤖 LLM-based: {llm_score}/100")
        print(f"📄 Papers: {validation_result['paper_count']}")
        print(f"✅ Valid: {validation_result['valid']}")
        
        # LLM Feedback
        llm_feedback = validation_result.get('llm_feedback', {})
        if llm_feedback:
            print(f"\n🤖 LLM Assessment:")
            if llm_feedback.get('overall_assessment'):
                print(f"   {llm_feedback['overall_assessment']}")
            
            if llm_feedback.get('strengths'):
                print(f"\n💪 Strengths:")
                for strength in llm_feedback['strengths'][:2]:
                    print(f"   ✓ {strength}")
            
            if llm_feedback.get('bilingual_quality'):
                print(f"\n🌐 Bilingual Quality: {llm_feedback['bilingual_quality']}")
        
        # Issues
        if validation_result['issues']:
            print(f"\n❌ Critical Issues ({len(validation_result['issues'])}):")
            for issue in validation_result['issues']:
                print(f"   • {issue}")
        else:
            print("\n✅ No critical issues found")
        
        # Warnings
        if validation_result['warnings']:
            print(f"\n⚠️  Warnings ({len(validation_result['warnings'])}):")
            for warning in validation_result['warnings']:
                print(f"   • {warning}")
        
        # Recommendations
        if validation_result['recommendations']:
            print(f"\n💡 Recommendations:")
            for rec in validation_result['recommendations']:
                print(f"   • {rec}")
        
        print("\n" + "="*70)
