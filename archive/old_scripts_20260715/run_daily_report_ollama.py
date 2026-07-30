#!/usr/bin/env python3
"""
TORRI Daily Report - Ollama Version
Simplified daily paper analysis using Ollama
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import Config
from src.routines.ingester import IngestRoutine
from src.routines.rss_fetcher import RSSFetcher
from src.database import DatabaseManager
from src.report_validator import ReportValidator
from src.report_fixer import ReportFixer
import requests
import json
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

def analyze_paper_with_ollama(paper_data, model="qwen2.5:7b"):
    """Analyze a paper using Ollama - bilingual output"""
    url = "http://localhost:11434/api/generate"
    
    # English analysis prompt
    prompt_en = f"""Analyze this astrophysics research paper professionally:

Title: {paper_data.get('title', 'Unknown')}
Authors: {', '.join(paper_data.get('authors', [])[:5])}
Abstract: {paper_data.get('abstract', 'No abstract')[:1000]}

Provide a professional analysis with:
1. **Main Contribution**: What is the key scientific contribution? (2-3 sentences)
2. **Key Results**: What are the main observational or theoretical findings?
3. **Significance**: Why is this important for GRB/kilonova/multi-messenger astronomy?
4. **Methodology**: What observational or computational methods were used?

Keep professional and focused on scientific content. Maximum 250 words."""

    # Korean summary prompt
    prompt_ko = f"""다음 천체물리학 논문을 한국어로 요약해주세요:

제목: {paper_data.get('title', 'Unknown')}
저자: {', '.join(paper_data.get('authors', [])[:5])}
초록: {paper_data.get('abstract', 'No abstract')[:1000]}

전문적인 한국어 요약을 제공해주세요 (150자 이내):
- 핵심 연구 내용
- 주요 발견
- 중력파 천문학/감마선 폭발/킬로노바 연구에 대한 의의

간결하고 전문적으로 작성해주세요."""

    try:
        # Get English analysis
        payload_en = {"model": model, "prompt": prompt_en, "stream": False}
        response_en = requests.post(url, json=payload_en, timeout=120)
        analysis_en = response_en.json().get("response", "Analysis failed") if response_en.status_code == 200 else "Error"
        
        # Get Korean summary
        payload_ko = {"model": model, "prompt": prompt_ko, "stream": False}
        response_ko = requests.post(url, json=payload_ko, timeout=120)
        analysis_ko = response_ko.json().get("response", "요약 실패") if response_ko.status_code == 200 else "오류"
        
        return {
            "english": analysis_en,
            "korean": analysis_ko
        }
    except Exception as e:
        return {
            "english": f"Error analyzing paper: {str(e)}",
            "korean": f"분석 오류: {str(e)}"
        }

def generate_daily_report(papers_analysis):
    """Generate professional bilingual HTML report"""
    from datetime import datetime
    
    today = datetime.now()
    
    # Generate CSS separately to avoid parsing issues
    css = """
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', 'Apple SD Gothic Neo', Arial, sans-serif; line-height: 1.6; color: #2c3e50; background: #f5f7fa; padding: 20px; }
        .container { max-width: 1000px; margin: 0 auto; background: white; box-shadow: 0 0 20px rgba(0,0,0,0.1); }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px; text-align: center; }
        .header h1 { font-size: 2.2em; margin-bottom: 10px; font-weight: 300; }
        .header .subtitle { font-size: 1.1em; opacity: 0.9; }
        .meta { background: #ecf0f1; padding: 20px 40px; border-left: 4px solid #667eea; }
        .meta-item { display: inline-block; margin-right: 30px; color: #555; }
        .content { padding: 40px; }
        .paper { margin-bottom: 40px; padding: 30px; border: 1px solid #e1e8ed; border-radius: 8px; background: #fafbfc; }
        .paper-header { border-bottom: 2px solid #667eea; padding-bottom: 15px; margin-bottom: 20px; }
        .paper-number { display: inline-block; background: #667eea; color: white; padding: 5px 12px; border-radius: 4px; font-size: 0.9em; font-weight: bold; margin-right: 10px; }
        .paper-title { font-size: 1.4em; font-weight: 600; color: #2c3e50; margin: 10px 0; line-height: 1.4; }
        .paper-meta { color: #7f8c8d; font-size: 0.9em; margin: 10px 0; }
        .arxiv-link { display: inline-block; color: #667eea; text-decoration: none; font-weight: 500; margin: 10px 0; }
        .arxiv-link:hover { text-decoration: underline; }
        .analysis-section { background: white; padding: 20px; border-radius: 6px; margin: 15px 0; }
        .analysis-section h3 { color: #667eea; font-size: 1.1em; margin-bottom: 10px; border-left: 3px solid #667eea; padding-left: 10px; }
        .analysis-english { margin-bottom: 25px; padding: 15px; background: #f8f9fa; border-left: 3px solid #3498db; }
        .analysis-korean { padding: 15px; background: #fff9e6; border-left: 3px solid #f39c12; font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif; }
        .footer { background: #2c3e50; color: white; padding: 30px; text-align: center; }
        .footer p { margin: 5px 0; opacity: 0.8; }
        .tag { display: inline-block; background: #e8f4f8; color: #2980b9; padding: 4px 10px; border-radius: 4px; font-size: 0.85em; margin: 5px 5px 5px 0; }
    """
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TORRI Research Digest - {today.strftime('%Y-%m-%d')}</title>
    <style>{css}</style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: 'Segoe UI', 'Apple SD Gothic Neo', Arial, sans-serif;
            line-height: 1.6;
            color: #2c3e50;
            background: #f5f7fa;
            padding: 20px;
        }}
        .container {{ 
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        .header h1 {{
            font-size: 2.2em;
            margin-bottom: 10px;
            font-weight: 300;
        }}
        .header .subtitle {{
            font-size: 1.1em;
            opacity: 0.9;
        }}
        .meta {{
            background: #ecf0f1;
            padding: 20px 40px;
            border-left: 4px solid #667eea;
        }}
        .meta-item {{
            display: inline-block;
            margin-right: 30px;
            color: #555;
        }}
        .content {{ padding: 40px; }}
        .paper {{
            margin-bottom: 40px;
            padding: 30px;
            border: 1px solid #e1e8ed;
            border-radius: 8px;
            background: #fafbfc;
            transition: box-shadow 0.3s;
        }}
        .paper:hover {{
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}
        .paper-header {{
            border-bottom: 2px solid #667eea;
            padding-bottom: 15px;
            margin-bottom: 20px;
        }}
        .paper-number {{
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 5px 12px;
            border-radius: 4px;
            font-size: 0.9em;
            font-weight: bold;
            margin-right: 10px;
        }}
        .paper-title {{
            font-size: 1.4em;
            font-weight: 600;
            color: #2c3e50;
            margin: 10px 0;
            line-height: 1.4;
        }}
        .paper-meta {{
            color: #7f8c8d;
            font-size: 0.9em;
            margin: 10px 0;
        }}
        .arxiv-link {{
            display: inline-block;
            color: #667eea;
            text-decoration: none;
            font-weight: 500;
            margin: 10px 0;
        }}
        .arxiv-link:hover {{ text-decoration: underline; }}
        .analysis-section {{
            background: white;
            padding: 20px;
            border-radius: 6px;
            margin: 15px 0;
        }}
        .analysis-section h3 {{
            color: #667eea;
            font-size: 1.1em;
            margin-bottom: 10px;
            border-left: 3px solid #667eea;
            padding-left: 10px;
        }}
        .analysis-english {{
            margin-bottom: 25px;
            padding: 15px;
            background: #f8f9fa;
            border-left: 3px solid #3498db;
        }}
        .analysis-korean {{
            padding: 15px;
            background: #fff9e6;
            border-left: 3px solid #f39c12;
            font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif;
        }}
        .footer {{
            background: #2c3e50;
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .footer p {{ margin: 5px 0; opacity: 0.8; }}
        .tag {{
            display: inline-block;
            background: #e8f4f8;
            color: #2980b9;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 0.85em;
            margin: 5px 5px 5px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌌 TORRI Research Digest</h1>
            <div class="subtitle">High Energy Astrophysics • Kilonovae • Gamma-Ray Bursts</div>
        </div>
        
        <div class="meta">
            <span class="meta-item">📅 <strong>{today.strftime('%B %d, %Y')}</strong></span>
            <span class="meta-item">📚 <strong>{len(papers_analysis)} Papers</strong></span>
            <span class="meta-item">🔬 <strong>arXiv astro-ph.HE</strong></span>
        </div>
        
        <div class="content">
"""

    for i, (paper, analysis) in enumerate(papers_analysis, 1):
        authors = paper.get('authors', [])
        author_str = ', '.join(authors[:3])
        if len(authors) > 3:
            author_str += f' et al. ({len(authors)} authors)'
        
        arxiv_id = paper.get('arxiv_id', '')
        categories = paper.get('categories', [])
        
        html += f"""
            <div class="paper">
                <div class="paper-header">
                    <span class="paper-number">#{i}</span>
                    <div class="paper-title">{paper.get('title', 'Unknown')}</div>
                    <div class="paper-meta">
                        <strong>Authors:</strong> {author_str}<br>
                        <strong>arXiv ID:</strong> <a href="{paper.get('url', '#')}" class="arxiv-link" target="_blank">{arxiv_id}</a>
                    </div>
                    <div>
                        {' '.join([f'<span class="tag">{cat}</span>' for cat in categories[:3]])}
                    </div>
                </div>
                
                <div class="analysis-section">
                    <div class="analysis-english">
                        <h3>📊 Analysis</h3>
                        {analysis.get('english', 'No analysis available')}
                    </div>
                    
                    <div class="analysis-korean">
                        <h3>🇰🇷 한국어 요약</h3>
                        {analysis.get('korean', '요약 없음')}
                    </div>
                </div>
            </div>
"""

    html += f"""
        </div>
        
        <div class="footer">
            <p><strong>TORRI</strong> - Transient Observation and Research Reporting Intelligence</p>
            <p>Powered by Ollama + Qwen2.5 | Generated: {today.strftime('%Y-%m-%d %H:%M:%S KST')}</p>
            <p>High Energy Astrophysics Research • Multi-messenger Astronomy</p>
        </div>
    </div>
</body>
</html>
"""
    return html

def send_email_report(config, html_content, paper_count):
    """Send email report"""
    if not config.email_enabled:
        print("⚠️  Email not configured, skipping email...")
        return False
    
    try:
        yag = yagmail.SMTP(config.sender_email, config.sender_password)
        subject = f"TORRI Daily Report - {datetime.now().strftime('%Y-%m-%d')} ({paper_count} papers)"
        
        yag.send(
            to=config.recipient_email,
            subject=subject,
            contents=html_content
        )
        print(f"✅ Email sent to {config.recipient_email}")
        return True
    except Exception as e:
        print(f"❌ Email failed: {e}")
        return False

def main():
    print("🚀 TORRI Daily Report (Ollama)")
    print("="*70)
    
    # Initialize
    config = Config()
    
    # Check Ollama
    print("\n🔍 Checking Ollama...")
    if not check_ollama():
        print("❌ Ollama is not running!")
        print("\nPlease start Ollama:")
        print("  ollama serve")
        print("\nOr run setup:")
        print("  ./setup_ollama.sh")
        return 1
    print("✅ Ollama is running")
    
    # Initialize RSS fetcher
    rss_fetcher = RSSFetcher()
    
    # Fetch papers from arXiv (using RSS feeds to avoid rate limiting)
    print("\n📥 Fetching papers from arXiv...")
    print("   Note: Using RSS feeds (less strict rate limits)")
    
    import time
    
    # Use RSS feeds instead of API (less rate limiting)
    rss_feeds = [
        ("http://export.arxiv.org/rss/astro-ph.HE", "High Energy Astrophysics"),
        ("http://export.arxiv.org/rss/astro-ph.CO", "Cosmology"),
        ("http://export.arxiv.org/rss/astro-ph.SR", "Solar and Stellar"),
    ]
    
    all_papers = []
    for feed_url, category in rss_feeds:
        print(f"   📡 Fetching from {category}...")
        try:
            feed_papers = rss_fetcher.fetch_from_rss(feed_url)
            all_papers.extend(feed_papers)
            print(f"      ✅ Got {len(feed_papers)} papers")
            
            # Sleep to avoid rate limiting
            time.sleep(3)
            
            if len(all_papers) >= 50:
                break
        except Exception as e:
            print(f"      ⚠️  Failed: {e}")
            continue
    
    # Now filter by research keywords (strict filtering for GRB/kilonova focus)
    primary_keywords = ["kilonova", "kilonovae", "AT2017gfo", "grb", "gamma-ray burst"]
    secondary_keywords = ["neutron star merger", "gravitational wave", "r-process", "electromagnetic counterpart"]
    
    filtered_papers = []
    for paper in all_papers:
        title = paper.get('title', '').lower()
        abstract = paper.get('abstract', '').lower()
        full_text = f"{title} {abstract}"
        
        # High priority: Must match primary keywords
        has_primary = any(kw.lower() in full_text for kw in primary_keywords)
        has_secondary = any(kw.lower() in full_text for kw in secondary_keywords)
        
        # Include if has primary keyword, or has secondary with "merger" or "transient"
        if has_primary or (has_secondary and ("merger" in full_text or "transient" in full_text)):
            paper['relevance_score'] = 2 if has_primary else 1
            filtered_papers.append(paper)
    
    # Sort by relevance
    filtered_papers.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
    
    print(f"\n   📊 Total papers: {len(all_papers)}, After filtering: {len(filtered_papers)}")
    
    # Remove duplicates by arxiv_id
    seen = set()
    unique_papers = []
    for paper in filtered_papers:
        arxiv_id = paper.get('arxiv_id')
        if arxiv_id and arxiv_id not in seen:
            seen.add(arxiv_id)
            unique_papers.append(paper)
    
    papers = unique_papers[:config.max_papers]
    
    if not papers:
        print("❌ No papers found")
        return 1
    
    print(f"✅ Found {len(papers)} papers")
    
    # Limit papers
    max_papers = min(len(papers), config.max_papers)
    papers = papers[:max_papers]
    print(f"📊 Analyzing {max_papers} papers...")
    
    # Analyze papers with bilingual output
    papers_analysis = []
    for i, paper in enumerate(papers, 1):
        print(f"   [{i}/{max_papers}] {paper.get('title', 'Unknown')[:60]}...")
        print(f"               (Relevance: {'⭐⭐ High' if paper.get('relevance_score', 0) == 2 else '⭐ Medium'})")
        analysis = analyze_paper_with_ollama(paper, config.ollama_model)
        papers_analysis.append((paper, analysis))
    
    print(f"✅ Analyzed {len(papers_analysis)} papers")
    
    # Iterative report generation with validation
    MAX_ATTEMPTS = 3
    validator = ReportValidator()
    fixer = ReportFixer(model=config.ollama_model)
    
    html_report = None
    validation = None
    
    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"\n{'='*70}")
        print(f"📊 Report Generation Attempt {attempt}/{MAX_ATTEMPTS}")
        print(f"{'='*70}")
        
        if attempt == 1:
            # First attempt: normal generation
            print("Generating initial report...")
            html_report = generate_daily_report(papers_analysis)
        else:
            # Subsequent attempts: regenerate with improvements
            print(f"🔄 Regenerating report with quality improvements...")
            print(f"   Previous score: {validation['quality_score']}/100")
            
            improvements = fixer.suggest_improvements(validation)
            print(f"   Applying {len(improvements)} improvements:")
            for imp in improvements[:3]:  # Show first 3
                print(f"      • {imp}")
            
            # Regenerate analyses with better prompts
            improved_analysis = []
            print(f"   Re-analyzing papers with enhanced prompts...")
            for i, (paper, old_analysis) in enumerate(papers_analysis[:5], 1):  # Regenerate first 5
                print(f"      [{i}/5] Improving {paper.get('title', '')[:40]}...")
                new_analysis = fixer.regenerate_paper_analysis(paper, config.ollama_model, attempt)
                improved_analysis.append((paper, new_analysis))
                time.sleep(1)  # Avoid overwhelming Ollama
            
            # Keep the rest as-is
            improved_analysis.extend(papers_analysis[5:])
            papers_analysis = improved_analysis
            
            # Regenerate HTML
            html_report = generate_daily_report(papers_analysis)
        
        # Validate
        print("\n🔍 Validating report quality...")
        validation = validator.validate_report(html_report, len(papers_analysis))
        validator.print_validation_report(validation)
        
        # Check if good enough
        if validation['valid'] and validation['quality_score'] >= 70:
            print(f"\n✅ Report quality acceptable! (Score: {validation['quality_score']}/100)")
            break
        elif attempt < MAX_ATTEMPTS:
            print(f"\n⚠️  Quality score: {validation['quality_score']}/100 - Regenerating...")
            time.sleep(2)  # Brief pause
        else:
            print(f"\n⚠️  Max attempts reached. Best score: {validation['quality_score']}/100")
    
    # Final decision
    if not validation['valid']:
        print("\n❌ Report still has critical issues after {MAX_ATTEMPTS} attempts!")
        print("   Saving as DRAFT, NOT sending email.")
        
        report_file = config.reports_dir / f"daily_report_{datetime.now().strftime('%Y%m%d')}_DRAFT.html"
        report_file.write_text(html_report)
        print(f"📄 Draft saved: {report_file}")
        
        return 1
    
    if validation['quality_score'] < 70:
        print("\n⚠️  Report quality score is low (< 70).")
        print("   Saving report, but you may want to review before sending.")
        # Continue anyway
    
    # Save report
    report_file = config.reports_dir / f"daily_report_{datetime.now().strftime('%Y%m%d')}.html"
    report_file.write_text(html_report)
    print(f"✅ Report saved: {report_file}")
    
    # Send email
    print("\n📧 Sending email...")
    send_email_report(config, html_report, len(papers_analysis))
    
    print("\n✅ Daily report complete!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
