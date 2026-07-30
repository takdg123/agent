#!/usr/bin/env python3
"""
Ingest Routine for TORRI System
Handles paper ingestion from arXiv and other sources
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
import httpx
import xml.etree.ElementTree as ET
from datetime import datetime

from .downloader import DownloadRoutine

class IngestRoutine:
    """Handles paper ingestion operations"""
    
    def __init__(self, config, db_manager):
        self.config = config
        self.db_manager = db_manager
        self.downloader = DownloadRoutine(config)
    
    def fetch_papers_from_feed(self, feed_url: str, keywords: List[str]) -> List[Dict[str, Any]]:
        """Fetch papers from an arXiv feed URL"""
        try:
            print(f"   🔍 Fetching papers from: {feed_url[:60]}...")
            
            # Fetch the feed (follow redirects automatically)
            response = httpx.get(feed_url, timeout=30, follow_redirects=True)
            response.raise_for_status()
            
            # Parse XML response
            root = ET.fromstring(response.text)
            
            # Extract papers
            papers = []
            for entry in root.findall(".//{http://www.w3.org/2005/Atom}entry"):
                try:
                    # Extract paper information
                    title = entry.find(".//{http://www.w3.org/2005/Atom}title")
                    title_text = title.text.strip() if title is not None and title.text else "No Title"
                    
                    # Check if paper matches keywords (skip if empty keyword list)
                    if keywords and keywords[0]:  # Only filter if keywords are provided
                        title_lower = title_text.lower()
                        if not any(keyword.lower() in title_lower for keyword in keywords):
                            continue
                    
                    # Extract other metadata
                    summary = entry.find(".//{http://www.w3.org/2005/Atom}summary")
                    abstract = summary.text.strip() if summary is not None and summary.text else ""
                    
                    # Extract authors
                    authors = []
                    for author in entry.findall(".//{http://www.w3.org/2005/Atom}author"):
                        name = author.find(".//{http://www.w3.org/2005/Atom}name")
                        if name is not None and name.text:
                            authors.append(name.text.strip())
                    
                    # Extract categories
                    categories = []
                    for category in entry.findall(".//{http://arxiv.org/schemas/atom}primary_category"):
                        if category.get("term"):
                            categories.append(category.get("term"))
                    
                    # Extract published date
                    published = entry.find(".//{http://www.w3.org/2005/Atom}published")
                    published_date = ""
                    if published is not None and published.text:
                        try:
                            # Parse ISO date
                            dt = datetime.fromisoformat(published.text.replace('Z', '+00:00'))
                            published_date = dt.isoformat()
                        except:
                            published_date = published.text
                    
                    # Extract URLs
                    abs_url = ""
                    pdf_url = ""
                    arxiv_id = ""
                    
                    # Get arXiv ID first
                    id_elem = entry.find(".//{http://www.w3.org/2005/Atom}id")
                    if id_elem is not None and id_elem.text:
                        arxiv_id = id_elem.text.split('/')[-1]
                        abs_url = f"https://arxiv.org/abs/{arxiv_id}"
                        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
                    
                    # Fallback to link elements if needed
                    if not pdf_url:
                        for link in entry.findall(".//{http://www.w3.org/2005/Atom}link"):
                            if link.get("title") == "pdf":
                                pdf_url = link.get("href", "")
                                break
                    
                    # Create paper object
                    paper = {
                        "title": title_text,
                        "authors": authors,
                        "abstract": abstract,
                        "url": abs_url,
                        "pdf_url": pdf_url,
                        "arxiv_id": arxiv_id,
                        "categories": categories,
                        "published_date": published_date,
                        "source": "arxiv",
                        "pdf_path": "",
                        "pdf_text": ""
                    }
                    
                    papers.append(paper)
                    
                except Exception as e:
                    print(f"     ⚠️ Error parsing paper: {e}")
                    continue
            
            print(f"   📄 Found {len(papers)} relevant papers from feed")
            return papers
            
        except Exception as e:
            print(f"   ❌ Error fetching papers from feed: {e}")
            return []
    
    def ingest_papers(self) -> Dict[str, Any]:
        """Run paper ingestion process"""
        try:
            print("📚 Starting paper ingestion process...")
            
            # Get sources configuration
            sources_config = self.config.get_sources_config()
            feeds = sources_config.get("feeds", [])
            keywords = sources_config.get("keywords", [])
            
            if not feeds:
                print("⚠️ No feeds configured for ingestion")
                return {
                    "success": True,
                    "message": "No feeds configured",
                    "papers_processed": 0,
                    "papers_ingested": 0,
                    "papers_skipped": 0
                }
            
            print(f"📡 Found {len(feeds)} feeds to process")
            print(f"🔍 Using keywords: {', '.join(keywords[:5])}{'...' if len(keywords) > 5 else ''}")
            
            # Process each feed
            papers_processed = 0
            papers_ingested = 0
            papers_skipped = 0
            
            for i, feed in enumerate(feeds, 1):
                feed_url = feed.get("url", "")
                if not feed_url:
                    continue
                
                print(f"📡 Processing feed {i}/{len(feeds)}: {feed_url[:60]}...")
                
                try:
                    # Fetch papers from this feed
                    papers = self.fetch_papers_from_feed(feed_url, keywords)
                    
                    for paper in papers:
                        papers_processed += 1
                        
                        # Check if paper already exists
                        if self.db_manager.paper_exists(paper.get("url", ""), paper.get("title")):
                            papers_skipped += 1
                            continue
                        
                        # Download PDF if available
                        pdf_path = ""
                        if paper.get("pdf_url"):
                            pdf_path = self.downloader.download_arxiv_pdf(
                                paper.get("arxiv_id", ""), 
                                paper.get("pdf_url"), 
                                paper.get("title", "")
                            )
                            if pdf_path:
                                paper["pdf_path"] = pdf_path
                                print(f"     📥 PDF downloaded: {Path(pdf_path).name}")
                        
                        # Save paper to database
                        if self.db_manager.save_paper(paper):
                            papers_ingested += 1
                        else:
                            papers_skipped += 1
                    
                    print(f"   ✅ Feed {i}: {len(papers)} papers processed")
                    
                except Exception as e:
                    print(f"   ❌ Feed {i} failed: {e}")
                    continue
            
            print(f"📊 Ingestion summary: {papers_processed} processed, {papers_ingested} ingested, {papers_skipped} skipped")
            
            return {
                "success": True,
                "message": "Paper ingestion completed",
                "papers_processed": papers_processed,
                "papers_ingested": papers_ingested,
                "papers_skipped": papers_skipped
            }
            
        except Exception as e:
            print(f"❌ Paper ingestion failed: {e}")
            return {"success": False, "error": str(e)}
