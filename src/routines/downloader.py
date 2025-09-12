#!/usr/bin/env python3
"""
Download Routine for TORRI System
Handles PDF downloading from arXiv and other sources
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
import httpx

class DownloadRoutine:
    """Handles PDF downloading operations"""
    
    def __init__(self, config):
        self.config = config
        self.pdfs_dir = config.pdfs_dir
        self.pdfs_dir.mkdir(parents=True, exist_ok=True)
    
    def download_arxiv_pdf(self, arxiv_id: str, pdf_url: str, title: str = "") -> Optional[str]:
        """Download a PDF from arXiv"""
        try:
            # Generate filename with title
            if title:
                # Clean title for filename (remove special chars, limit length)
                clean_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
                clean_title = clean_title.replace(' ', '-')[:50]  # Limit length
                filename = f"{arxiv_id}_{clean_title}.pdf"
            else:
                filename = f"{arxiv_id}.pdf"
            
            pdf_path = self.pdfs_dir / filename
            
            # Skip if already exists
            if pdf_path.exists():
                print(f"     📁 PDF already exists: {filename}")
                return str(pdf_path)
            
            # Download PDF
            print(f"       📥 Downloading PDF: {filename}")
            response = httpx.get(pdf_url, timeout=60, follow_redirects=True)
            response.raise_for_status()
            
            # Save PDF
            with open(pdf_path, 'wb') as f:
                f.write(response.content)
            
            print(f"       ✅ PDF saved: {filename}")
            return str(pdf_path)
            
        except Exception as e:
            print(f"       ❌ PDF download failed: {e}")
            return None
    
    def download_multiple_pdfs(self, papers: List[Dict[str, Any]]) -> Dict[str, str]:
        """Download multiple PDFs and return mapping of arxiv_id to file path"""
        downloaded = {}
        
        for paper in papers:
            arxiv_id = paper.get("arxiv_id")
            pdf_url = paper.get("pdf_url")
            title = paper.get("title", "")
            
            if arxiv_id and pdf_url:
                pdf_path = self.download_arxiv_pdf(arxiv_id, pdf_url, title)
                if pdf_path:
                    downloaded[arxiv_id] = pdf_path
                    paper["pdf_path"] = pdf_path
        
        print(f"📊 Downloaded {len(downloaded)} PDFs")
        return downloaded
