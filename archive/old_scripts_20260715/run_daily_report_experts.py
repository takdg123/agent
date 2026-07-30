#!/usr/bin/env python3
"""
TORRI Daily Report - Multi-Expert Version
Uses 6-expert agent harness for comprehensive paper analysis
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import Config
from src.routines.rss_fetcher import RSSFetcher
from src.harness.expert_harness import ExpertHarness
from src.report_validator import ReportValidator
import requests
from datetime import datetime
import yagmail
import time

def check_ollama():
    """Check if Ollama is running"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        return response.status_code == 200
    except:
        return False

def generate_expert_html_report(papers_analysis):
    """Generate professional HTML report from expert analyses"""
    from datetime import datetime
    
    today = datetime.now()
    
    css = """* { margin: 0; padding: 0; box-sizing: border-box; } body { font-family: 'Segoe UI', 'Apple SD Gothic Neo', Arial, sans-serif; line-height: 1.6; color: #2c3e50; background: #f5f7fa; padding: 20px; } .container { max-width: 1000px; margin: 0 auto; background: white; box-shadow: 0 0 20px rgba(0,0,0,0.1); } .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px; text-align: center; } .header h1 { font-size: 2.2em; margin-bottom: 10px; font-weight: 300; } .header .subtitle { font-size: 1.1em; opacity: 0.9; } .meta-info { background: #f8f9fa; padding: 20px 40px; border-bottom: 2px solid #e9ecef; } .meta-info p { margin: 5px 0; color: #6c757d; } .expert-badge { display: inline-block; background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; padding: 4px 12px; border-radius: 12px; font-size: 0.75em; margin-left: 10px; font-weight: 600; } .content { padding: 40px; } .paper { background: white; border: 1px solid #e9ecef; border-radius: 8px; padding: 30px; margin-bottom: 30px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); transition: transform 0.2s, box-shadow 0.2s; } .paper:hover { transform: translateY(-2px); box-shadow: 0 4px 16px rgba(0,0,0,0.1); } .paper-title { color: #667eea; font-size: 1.3em; margin-bottom: 15px; font-weight: 600; border-left: 4px solid #667eea; padding-left: 15px; } .paper-meta { display: flex; flex-wrap: wrap; gap: 20px; margin: 15px 0; padding: 15px; background: #f8f9fa; border-radius: 6px; } .paper-meta-item { display: flex; align-items: center; gap: 8px; color: #6c757d; font-size: 0.9em; } .paper-meta-item strong { color: #495057; } .analysis-section { margin-top: 20px; } .section-label { font-weight: 600; color: #495057; margin: 20px 0 10px 0; font-size: 1.05em; border-bottom: 2px solid #e9ecef; padding-bottom: 5px; } .analysis-text { color: #2c3e50; line-height: 1.8; text-align: justify; } .korean-summary { background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 30%); padding: 20px; border-radius: 8px; margin-top: 20px; border-left: 4px solid #fc8b6f; } .korean-summary .label { font-weight: 600; color: #c0392b; margin-bottom: 10px; font-size: 1.05em; } .korean-summary .text { color: #2c3e50; line-height: 1.8; } .expert-reviews { background: #e3f2fd; padding: 20px; border-radius: 8px; margin-top: 20px; border-left: 4px solid #2196f3; } .expert-review-item { margin: 15px 0; padding: 15px; background: white; border-radius: 6px; } .expert-review-item .expert-name { font-weight: 600; color: #1976d2; margin-bottom: 8px; display: flex; align-items: center; gap: 10px; } .confidence-bar { display: inline-block; background: #e0e0e0; height: 6px; width: 100px; border-radius: 3px; overflow: hidden; } .confidence-fill { height: 100%; background: linear-gradient(90deg, #4caf50 0%, #8bc34a 100%); } .quality-badge { display: inline-block; padding: 6px 14px; border-radius: 16px; font-weight: 600; font-size: 0.85em; margin-left: 10px; } .quality-high { background: #d4edda; color: #155724; } .quality-medium { background: #fff3cd; color: #856404; } .quality-low { background: #f8d7da; color: #721c24; } .footer { background: #2c3e50; color: white; padding: 30px 40px; text-align: center; } .footer p { margin: 5px 0; opacity: 0.9; } .stats-summary { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 25px; border-radius: 8px; margin-bottom: 30px; } .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-top: 15px; } .stat-item { background: rgba(255,255,255,0.1); padding: 15px; border-radius: 6px; text-align: center; } .stat-value { font-size: 2em; font-weight: 600; margin-bottom: 5px; } .stat-label { font-size: 0.9em; opacity: 0.9; } @media (max-width: 768px) { .container { margin: 10px; } .content { padding: 20px; } .paper { padding: 20px; } }"""
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TORRI Daily Research Digest - {today.strftime('%Y-%m-%d')}</title>
    <style>{css}</style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔬 TORRI Research Digest</h1>
            <div class="subtitle">High-Energy Astrophysics • Multi-Expert Analysis<span class="expert-badge">6 EXPERTS</span></div>
            <div class="subtitle" style="margin-top: 10px;">{today.strftime('%A, %B %d, %Y')}</div>
        </div>
        
        <div class="meta-info">
            <p><strong>Focus Areas:</strong> Gamma-Ray Bursts (GRBs), Kilonovae, Neutron Star Mergers</p>
            <p><strong>Analysis Method:</strong> Multi-Expert AI System (GRB Expert, Kilonova Expert, Astrophysicist, Language Expert, Critic, Writer)</p>
            <p><strong>Papers Analyzed:</strong> {len(papers_analysis)} papers</p>
        </div>
        
        <div class="content">
            <div class="stats-summary">
                <h2 style="margin-bottom: 15px;">📊 Today's Analysis Summary</h2>
                <div class="stats-grid">
                    <div class="stat-item">
                        <div class="stat-value">{len(papers_analysis)}</div>
                        <div class="stat-label">Papers</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">{sum(1 for p in papers_analysis if p['analysis'].get('grb_confidence', 0) > 0.5)}</div>
                        <div class="stat-label">GRB Papers</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">{sum(1 for p in papers_analysis if p['analysis'].get('kilonova_confidence', 0) > 0.5)}</div>
                        <div class="stat-label">Kilonova Papers</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">{sum(1 for p in papers_analysis if p['analysis'].get('quality_score', 0) >= 8.0)}</div>
                        <div class="stat-label">High Quality</div>
                    </div>
                </div>
            </div>
"""
    
    for i, paper_data in enumerate(papers_analysis, 1):
        paper = paper_data['paper']
        analysis = paper_data['analysis']
        
        quality_score = analysis.get('quality_score', 7.0)
        quality_class = 'quality-high' if quality_score >= 8 else ('quality-medium' if quality_score >= 6 else 'quality-low')
        quality_label = 'High' if quality_score >= 8 else ('Medium' if quality_score >= 6 else 'Low')
        
        grb_conf = analysis.get('grb_confidence', 0)
        kn_conf = analysis.get('kilonova_confidence', 0)
        
        html += f"""
            <div class="paper">
                <div class="paper-title">
                    {i}. {paper.get('title', 'Unknown Title')}
                    <span class="quality-badge {quality_class}">Quality: {quality_label} ({quality_score:.1f}/10)</span>
                </div>
                
                <div class="paper-meta">
                    <div class="paper-meta-item">
                        <strong>Authors:</strong> {', '.join(paper.get('authors', ['Unknown'])[:5])}
                        {f'<em>et al.</em>' if len(paper.get('authors', [])) > 5 else ''}
                    </div>
                    <div class="paper-meta-item">
                        <strong>arXiv:</strong> <a href="https://arxiv.org/abs/{paper.get('arxiv_id', '')}" target="_blank">{paper.get('arxiv_id', 'N/A')}</a>
                    </div>
                    <div class="paper-meta-item">
                        <strong>Published:</strong> {paper.get('published', 'N/A')}
                    </div>
                </div>
                
                <div class="paper-meta">
                    <div class="paper-meta-item">
                        <strong>GRB Relevance:</strong>
                        <div class="confidence-bar">
                            <div class="confidence-fill" style="width: {grb_conf*100}%"></div>
                        </div>
                        <span style="margin-left: 8px;">{grb_conf*100:.0f}%</span>
                    </div>
                    <div class="paper-meta-item">
                        <strong>Kilonova Relevance:</strong>
                        <div class="confidence-bar">
                            <div class="confidence-fill" style="width: {kn_conf*100}%"></div>
                        </div>
                        <span style="margin-left: 8px;">{kn_conf*100:.0f}%</span>
                    </div>
                </div>
                
                <div class="analysis-section">
                    <div class="section-label">📝 Expert Analysis (English)</div>
                    <div class="analysis-text">{analysis.get('english', 'No analysis available')}</div>
                </div>
                
                <div class="korean-summary">
                    <div class="label">🇰🇷 한국어 요약</div>
                    <div class="text">{analysis.get('korean', '요약 없음')}</div>
                </div>
"""
        
        # Add expert reviews if available
        expert_reviews = analysis.get('expert_reviews', [])
        if expert_reviews:
            html += """
                <div class="expert-reviews">
                    <div class="section-label" style="color: #1976d2; border-bottom-color: #2196f3;">🎓 Expert Reviews</div>
"""
            for review in expert_reviews:
                expertise = review.get('expertise', 'Expert')
                review_text = review.get('expert_review', 'N/A')[:400]  # Truncate for brevity
                confidence = review.get('confidence', 0)
                
                html += f"""
                    <div class="expert-review-item">
                        <div class="expert-name">
                            {expertise}
                            <div class="confidence-bar">
                                <div class="confidence-fill" style="width: {confidence*100}%"></div>
                            </div>
                            <span style="font-size: 0.85em; color: #666;">{confidence*100:.0f}% relevant</span>
                        </div>
                        <div style="color: #37474f; font-size: 0.9em; line-height: 1.6;">{review_text}...</div>
                    </div>
"""
            
            html += """
                </div>
"""
        
        html += """
            </div>
"""
    
    # Footer
    total_time = sum(p['analysis'].get('execution_time', 0) for p in papers_analysis)
    used_memory = sum(1 for p in papers_analysis if p['analysis'].get('used_memory', False))
    
    html += f"""
        </div>
        
        <div class="footer">
            <p><strong>TORRI</strong> - Transient Observation Research & Realtime Intelligence</p>
            <p>Multi-Expert AI Analysis System | 6 Specialized Agents</p>
            <p>Analysis Time: {total_time:.1f}s | Papers with Historical Context: {used_memory}</p>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC+9</p>
        </div>
    </div>
</body>
</html>
"""
    
    return html

def main():
    print("="*70)
    print("🚀 TORRI Daily Report - Multi-Expert Version")
    print("="*70)
    
    # Check Ollama
    print("\n🔍 Checking Ollama...")
    if not check_ollama():
        print("❌ Ollama is not running!")
        print("\nPlease start Ollama:")
        print("   ollama serve")
        return 1
    print("✅ Ollama is running")
    
    # Initialize config
    config = Config()
    
    # Initialize Expert Harness
    print("\n🧠 Initializing Multi-Expert Harness...")
    harness = ExpertHarness(config=config, llm_manager=None)
    
    # Fetch papers
    print("\n📥 Fetching papers from arXiv RSS feeds...")
    rss_fetcher = RSSFetcher()
    
    categories = ["astro-ph.HE"]  # High Energy Astrophysics
    all_papers = []
    
    for category in categories:
        feed_url = f"http://export.arxiv.org/rss/{category}"
        print(f"   🔍 Fetching from {category}...")
        papers = rss_fetcher.fetch_from_rss(feed_url)
        all_papers.extend(papers)
        print(f"   📄 Found {len(papers)} papers")
    
    # Filter papers for GRB/kilonova relevance
    print(f"\n🔍 Filtering {len(all_papers)} papers for relevance...")
    
    primary_keywords = ["kilonova", "kilonovae", "at2017gfo", "grb", "gamma-ray burst"]
    secondary_keywords = ["neutron star merger", "gravitational wave", "r-process", 
                         "electromagnetic counterpart", "afterglow", "jet"]
    
    filtered_papers = []
    for paper in all_papers:
        title = paper.get('title', '').lower()
        abstract = paper.get('abstract', '').lower()
        full_text = f"{title} {abstract}"
        
        has_primary = any(kw.lower() in full_text for kw in primary_keywords)
        has_secondary = any(kw.lower() in full_text for kw in secondary_keywords)
        
        if has_primary or (has_secondary and ("merger" in full_text or "transient" in full_text)):
            paper['relevance_score'] = 2 if has_primary else 1
            filtered_papers.append(paper)
    
    filtered_papers.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
    
    print(f"✅ {len(filtered_papers)} relevant papers selected")
    
    if not filtered_papers:
        print("❌ No relevant papers found today")
        return 0
    
    # Limit to top papers (for testing, can be removed)
    papers_to_analyze = filtered_papers[:10]  # Top 10
    
    # Analyze papers with multi-expert system
    print(f"\n🔬 Analyzing {len(papers_to_analyze)} papers with 6-expert system...")
    print("   Experts: GRB Expert, Kilonova Expert, Astrophysicist, Language Expert, Critic, Writer")
    
    papers_analysis = harness.batch_analyze_papers(papers_to_analyze, use_memory=True)
    
    successful = [p for p in papers_analysis if p.get('success', False)]
    print(f"\n✅ Successfully analyzed {len(successful)}/{len(papers_to_analyze)} papers")
    
    # Generate HTML report
    print("\n📄 Generating HTML report...")
    html_report = generate_expert_html_report(successful)
    
    # Validate report
    print("\n🔍 Validating report quality...")
    validator = ReportValidator()
    validation = validator.validate_report(html_report, len(successful))
    validator.print_validation_report(validation)
    
    # Save report
    today_str = datetime.now().strftime('%Y%m%d')
    report_path = Path(config.data_dir) / f"reports/expert_report_{today_str}.html"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(html_report)
    
    print(f"\n💾 Report saved: {report_path}")
    
    # Store in memory
    harness.memory.store_report(str(report_path), filtered_papers, metadata={
        'quality_score': validation['quality_score'],
        'expert_count': 6,
        'llm_validated': True
    })
    
    # Send email if quality is good
    if validation['valid'] and validation['quality_score'] >= 70:
        print("\n📧 Sending email...")
        try:
            yag = yagmail.SMTP(config.email_from, config.email_password)
            yag.send(
                to=config.email_to,
                subject=f"🔬 TORRI Multi-Expert Digest - {datetime.now().strftime('%Y-%m-%d')} ({len(successful)} papers)",
                contents=html_report
            )
            print("✅ Email sent successfully!")
        except Exception as e:
            print(f"❌ Email failed: {e}")
    else:
        print(f"\n⚠️  Quality score ({validation['quality_score']}) too low, not sending email")
        print(f"   Draft saved: {report_path}")
    
    # Print statistics
    print("\n" + "="*70)
    print("📊 STATISTICS")
    print("="*70)
    stats = harness.get_stats()
    print(f"Agents: {stats['coordinator']['registered_agents']}")
    print(f"Tasks Executed: {stats['coordinator']['completed_tasks']}")
    print(f"Memory Papers: {stats['memory']['total_papers']}")
    print(f"Memory Reports: {stats['memory']['total_reports']}")
    print("="*70)
    
    harness.shutdown()
    return 0

if __name__ == "__main__":
    sys.exit(main())
