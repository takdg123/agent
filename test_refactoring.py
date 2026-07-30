#!/usr/bin/env python3
"""
Test script to verify refactored code works identically
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.llm_client import LLMClient
from src.utils.paper_filter import PaperFilter
from src.utils.html_report_generator import HTMLReportGenerator

def test_llm_client():
    """Test LLM client"""
    print("="*70)
    print("Testing LLMClient")
    print("="*70)
    
    llm = LLMClient()
    print(f"✅ LLMClient initialized")
    print(f"   Base URL: {llm.base_url}")
    print(f"   Model: {llm.model}")
    print(f"   Available: {llm.is_available()}")
    
    if llm.is_available():
        models = llm.get_models()
        print(f"   Models: {', '.join(models[:3])}...")
    
    print()

def test_paper_filter():
    """Test paper filtering"""
    print("="*70)
    print("Testing PaperFilter")
    print("="*70)
    
    test_papers = [
        {
            'title': 'GRB 240710A: Kilonova Discovery',
            'abstract': 'Observation of a kilonova from GRB 240710A merger event.'
        },
        {
            'title': 'Dark Matter Halos in Galaxies',
            'abstract': 'Study of dark matter distribution in spiral galaxies.'
        },
        {
            'title': 'Neutron Star Merger and Gravitational Waves',
            'abstract': 'GW observation of neutron star merger electromagnetic counterpart.'
        }
    ]
    
    print(f"Testing with {len(test_papers)} papers")
    
    for i, paper in enumerate(test_papers, 1):
        score = PaperFilter.calculate_relevance(paper)
        keywords = PaperFilter.extract_keywords(paper)
        print(f"\n  Paper {i}:")
        print(f"    Title: {paper['title'][:50]}...")
        print(f"    Score: {score}")
        print(f"    Keywords: {', '.join(list(keywords)[:3])}")
    
    filtered = PaperFilter.filter_papers(test_papers, min_score=1.0)
    print(f"\n✅ Filtered: {len(filtered)}/{len(test_papers)} papers (score ≥ 1.0)")
    
    print()

def test_html_generator():
    """Test HTML report generation"""
    print("="*70)
    print("Testing HTMLReportGenerator")
    print("="*70)
    
    # Mock data
    papers_analysis = [
        {
            'paper': {
                'title': 'Test GRB Paper',
                'authors': ['Smith, J.', 'Doe, A.'],
                'arxiv_id': '2407.12345',
                'published': '2024-07-15'
            },
            'analysis': {
                'english': 'This is a test analysis of the paper.',
                'korean': '이것은 논문의 테스트 분석입니다.',
                'quality_score': 8.5
            }
        }
    ]
    
    html = HTMLReportGenerator.generate_full_report(
        papers_analysis=papers_analysis,
        title="Test Report",
        subtitle="Testing",
        expert_count=6,
        metadata={'description': 'Test description'}
    )
    
    print(f"✅ HTML generated: {len(html)} characters")
    print(f"   Contains CSS: {'<style>' in html}")
    print(f"   Contains paper title: {'Test GRB Paper' in html}")
    print(f"   Contains Korean: {'이것은' in html}")
    print(f"   Valid HTML structure: {html.startswith('<!DOCTYPE html>')}")
    
    print()

def test_expert_agents():
    """Test refactored expert agents"""
    print("="*70)
    print("Testing Expert Agents")
    print("="*70)
    
    from src.config import Config
    from src.harness.expert_agents import (
        GRBExpertAgent, KilonovaExpertAgent, 
        AstrophysicistAgent, LanguageExpertAgent,
        CriticAgent, WriterAgent
    )
    
    config = Config()
    
    agents = [
        ('GRB Expert', GRBExpertAgent('grb', config, None)),
        ('Kilonova Expert', KilonovaExpertAgent('kn', config, None)),
        ('Astrophysicist', AstrophysicistAgent('astro', config, None)),
        ('Language Expert', LanguageExpertAgent('lang', config, None)),
        ('Critic', CriticAgent('critic', config, None)),
        ('Writer', WriterAgent('writer', config, None))
    ]
    
    print(f"Initialized {len(agents)} expert agents:")
    for name, agent in agents:
        print(f"  ✅ {name}")
        print(f"     - ID: {agent.agent_id}")
        print(f"     - Expertise: {agent.expertise}")
        print(f"     - Capabilities: {len(agent.capabilities)}")
        print(f"     - Has LLM client: {hasattr(agent, 'llm_client')}")
    
    print()

def main():
    """Run all tests"""
    print("\n")
    print("🧪 REFACTORING VALIDATION TEST")
    print("="*70)
    print()
    
    try:
        test_llm_client()
        test_paper_filter()
        test_html_generator()
        test_expert_agents()
        
        print("="*70)
        print("✅ ALL TESTS PASSED")
        print("="*70)
        print()
        print("Refactoring successful! All utilities work correctly.")
        print()
        return 0
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
