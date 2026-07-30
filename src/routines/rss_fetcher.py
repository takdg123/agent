#!/usr/bin/env python3
"""
RSS Fetcher for arXiv feeds
Handles standard RSS format (not Atom)
"""

from typing import List, Dict, Any
import httpx
import xml.etree.ElementTree as ET
from datetime import datetime

class RSSFetcher:
    """Fetches papers from arXiv RSS feeds"""
    
    def fetch_from_rss(self, feed_url: str) -> List[Dict[str, Any]]:
        """Fetch papers from an arXiv RSS feed"""
        try:
            # Fetch the feed
            response = httpx.get(feed_url, timeout=30, follow_redirects=True)
            response.raise_for_status()
            
            # Parse XML
            root = ET.fromstring(response.text)
            
            # Find all items (RSS format)
            items = root.findall(".//item")
            
            papers = []
            for item in items:
                try:
                    # Extract title
                    title_elem = item.find("title")
                    title = title_elem.text.strip() if title_elem is not None and title_elem.text else "No Title"
                    
                    # Extract description (contains abstract)
                    desc_elem = item.find("description")
                    description = desc_elem.text if desc_elem is not None and desc_elem.text else ""
                    
                    # Extract abstract from description
                    # Format: "arXiv:ID Announce Type: new \nAbstract: ACTUAL_ABSTRACT"
                    abstract = ""
                    if "Abstract:" in description:
                        abstract = description.split("Abstract:", 1)[1].strip()
                    
                    # Extract link
                    link_elem = item.find("link")
                    abs_url = link_elem.text.strip() if link_elem is not None and link_elem.text else ""
                    
                    # Extract arXiv ID from link or description
                    arxiv_id = ""
                    if abs_url and "arxiv.org/abs/" in abs_url:
                        arxiv_id = abs_url.split("/abs/")[-1]
                    elif "arXiv:" in description:
                        # Extract from description
                        arxiv_id = description.split("arXiv:")[1].split()[0]
                    
                    # Construct PDF URL
                    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf" if arxiv_id else ""
                    
                    # Extract categories
                    categories = []
                    for cat_elem in item.findall("category"):
                        if cat_elem.text:
                            categories.append(cat_elem.text.strip())
                    
                    # Extract published date
                    pubdate_elem = item.find("pubDate")
                    published_date = pubdate_elem.text if pubdate_elem is not None and pubdate_elem.text else ""
                    
                    # Extract authors from DC creator
                    authors = []
                    creator_elem = item.find(".//{http://purl.org/dc/elements/1.1/}creator")
                    if creator_elem is not None and creator_elem.text:
                        # Split by comma
                        author_text = creator_elem.text
                        authors = [a.strip() for a in author_text.split(',')]
                    
                    # Create paper object
                    paper = {
                        "title": title,
                        "authors": authors,
                        "abstract": abstract,
                        "url": abs_url,
                        "pdf_url": pdf_url,
                        "arxiv_id": arxiv_id,
                        "published": published_date,
                        "categories": categories,
                        "source": "arXiv RSS"
                    }
                    
                    papers.append(paper)
                    
                except Exception as e:
                    # Skip problematic entries
                    continue
            
            return papers
            
        except Exception as e:
            print(f"       ⚠️  Error fetching RSS: {e}")
            return []
