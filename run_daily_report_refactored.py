#!/usr/bin/env python3
"""
TORRI Daily Report - Refactored Version
Clean, DRY, modular code using shared utilities
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.config import Config
from src.routines.rss_fetcher import RSSFetcher
from src.harness.expert_harness import ExpertHarness
from src.report_validator import ReportValidator
from src.utils.llm_client import LLMClient, LLMError
from src.utils.relevance import RelevanceScorer, load_profile
from src.utils import paper_text
from src.utils.html_report_generator import HTMLReportGenerator
from datetime import datetime
from pathlib import Path
import yagmail


def fetch_and_filter_papers(llm: LLMClient, config: Config,
                            categories: list = None) -> list:
    """
    Fetch papers and keep the ones relevant to the reader's interest profile.

    Args:
        llm: client used for embeddings and triage
        config: configuration object
        categories: arXiv categories to fetch from

    Returns:
        Papers sorted by descending relevance, each carrying relevance_score,
        topic_tags, and why_it_matters
    """
    categories = categories or ["astro-ph.HE"]

    print("\n📥 Fetching papers from arXiv RSS feeds...")
    rss_fetcher = RSSFetcher()

    all_papers = []
    for category in categories:
        feed_url = f"http://export.arxiv.org/rss/{category}"
        print(f"   🔍 {category}...")
        papers = rss_fetcher.fetch_from_rss(feed_url)
        all_papers.extend(papers)
        print(f"   📄 {len(papers)} papers")

    if not all_papers:
        return []

    print(f"\n🎯 Scoring {len(all_papers)} papers against your interest profile...")
    profile = load_profile(Path(config.root_dir) / "config" / "interests.yml")
    scorer = RelevanceScorer(
        llm, profile,
        cache_dir=Path(config.data_dir) / "knowledge",
        prompt_dir=Path(config.root_dir) / "prompts",
        model=config.general_model,
    )
    return scorer.select(all_papers)


def attach_full_text(papers: list, config: Config) -> list:
    """
    Attach extracted PDF sections to each paper.

    Runs after relevance selection so only papers that will be reported are
    downloaded. A failed extraction degrades that paper to abstract-only rather
    than removing it.
    """
    print(f"\n📖 Extracting full text for {len(papers)} papers...")
    for paper in papers:
        contents = paper_text.extract(paper, cache_dir=Path(config.data_dir) / "pdfs")
        paper["contents"] = contents
        sections = [name for name in ("introduction", "methods", "results", "conclusions")
                    if contents.get(name)]
        marker = "📄" if contents["source"] == "pdf" else "⚠️ "
        print(f"   {marker} {paper.get('title', '')[:52]}"
              f"  [{contents['source']}: {', '.join(sections) or 'abstract only'}]")
    return papers


def save_and_email_report(html: str, config: Config, papers_count: int, 
                         quality_score: int) -> bool:
    """
    Save report and send email if quality is sufficient
    
    Args:
        html: HTML report content
        config: Configuration object
        papers_count: Number of papers analyzed
        quality_score: Quality score (0-100)
        
    Returns:
        True if email sent, False otherwise
    """
    # Save report
    today_str = datetime.now().strftime('%Y%m%d')
    report_path = Path(config.data_dir) / f"reports/expert_report_{today_str}.html"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"\n💾 Report saved: {report_path}")
    
    # Send email if quality is good and email is configured
    if quality_score >= 70:
        if not config.email_enabled:
            print("\n📧 Email not configured (skipping)")
            return False
            
        print("\n📧 Sending email...")
        try:
            yag = yagmail.SMTP(config.sender_email, config.sender_password)
            yag.send(
                to=config.recipient_email,
                subject=f"🔬 TORRI Multi-Expert Digest - {datetime.now().strftime('%Y-%m-%d')} ({papers_count} papers)",
                contents=html
            )
            print("✅ Email sent!")
            return True
        except Exception as e:
            print(f"❌ Email failed: {e}")
            return False
    else:
        print(f"\n⚠️  Quality ({quality_score}) below threshold (70), not sending")
        return False


def main():
    """Main execution flow - clean and simple"""
    print("="*70)
    print("🚀 TORRI Daily Report - Multi-Expert (Refactored)")
    print("="*70)
    
    # 1. Check LLM availability
    print("\n🔍 Checking Ollama...")
    llm = LLMClient()
    if not llm.is_available():
        print("❌ Ollama not running! Please start: ollama serve")
        return 1
    print("✅ Ollama running")
    
    # 2. Initialize
    config = Config()

    # Verify every configured model exists before doing any work. A wrong model
    # name used to surface only as per-request 404s that were stored as prose.
    print("\n🔍 Verifying configured models...")
    for label, name in [
        ("astro expert", config.astro_expert_model),
        ("general", config.general_model),
        ("language", config.language_model),
    ]:
        try:
            print(f"   ✅ {label}: {llm.require_model(name)}")
        except LLMError as exc:
            print(f"\n❌ {label} model unusable:\n{exc}")
            return 1

    print("\n🧠 Initializing Multi-Expert Harness...")
    try:
        harness = ExpertHarness(config=config, llm_manager=None)
    except LLMError as exc:
        print(f"\n❌ Could not initialize experts:\n{exc}")
        return 1
    
    # 3. Fetch and score papers against the interest profile
    papers = fetch_and_filter_papers(llm, config)
    if not papers:
        print("❌ No relevant papers found")
        return 0

    # Limit for processing (can be removed)
    papers_to_analyze = attach_full_text(papers[:10], config)

    # 4. Analyze with multi-expert system
    print(f"\n🔬 Analyzing {len(papers_to_analyze)} papers with 6-expert system...")
    results = harness.batch_analyze_papers(papers_to_analyze, use_memory=True)

    successful = [r for r in results if r.get('success', False)]
    print(f"✅ Analyzed {len(successful)}/{len(papers_to_analyze)} papers")

    if not successful:
        print("❌ No successful analyses")
        return 1

    # Relevance is decided before analysis; carry it into what the report renders.
    for entry in successful:
        paper = entry.get('paper', {})
        for field in ('relevance_score', 'topic_tags', 'why_it_matters'):
            if paper.get(field) is not None:
                entry.setdefault('analysis', {})[field] = paper[field]

    # 5. Generate HTML report
    print("\n📄 Generating HTML report...")
    html = HTMLReportGenerator.generate_full_report(
        papers_analysis=successful,
        title="🔬 TORRI Research Digest",
        subtitle="High-Energy Astrophysics • Multi-Expert Analysis",
        expert_count=6,
        metadata={'description': 'Multi-Expert AI Analysis System | 6 Specialized Agents'}
    )
    
    # 6. Validate
    print("\n🔍 Validating report...")
    validator = ReportValidator()
    validation = validator.validate_report(html, len(successful))
    validator.print_validation_report(validation)
    
    # 7. Save and email
    save_and_email_report(
        html, config, len(successful), 
        validation['quality_score']
    )
    
    # 8. Update the running topic notes from today's papers
    print("\n🧠 Updating topic notes...")
    topics = harness.memory.update_topic_notes(
        successful, model=config.general_model
    )
    print(f"   ✅ updated {len(topics)} topic notes: {', '.join(topics) or '(none)'}")

    # 9. Stats
    print("\n" + "="*70)
    print("📊 STATISTICS")
    print("="*70)
    stats = harness.get_stats()
    memory = stats['memory']
    print(f"Agents: {stats['coordinator']['registered_agents']}")
    print(f"Tasks: {stats['coordinator']['completed_tasks']}")
    print(f"Knowledge: {memory['total_papers']} papers "
          f"({memory['embedded_papers']} embedded), {memory['topics']} topics")
    print(f"Quality: {validation['quality_score']}/100")
    print("="*70)
    
    harness.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
