#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PDF processing class for TORRI system
Handles text extraction, chunking, and metadata analysis
"""

import re
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add user site packages to path for PyMuPDF
user_site = Path.home() / ".local/lib/python3.12/site-packages"
if user_site.exists() and str(user_site) not in sys.path:
    sys.path.insert(0, str(user_site))

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

class PDFProcessor:
    """Handles all PDF-related operations for TORRI system"""
    
    def __init__(self, config):
        self.config = config
        self.available = PYMUPDF_AVAILABLE
        
        if not self.available:
            print("⚠️ PyMuPDF not available. Install with: pip install PyMuPDF")
    
    def extract_text(self, pdf_path: str) -> str:
        """Extract text content from PDF"""
        if not self.available:
            return ""
        
        try:
            doc = fitz.open(pdf_path)
            text = ""
            
            for page in doc:
                text += page.get_text("text") + "\n"
            
            doc.close()
            return text.strip()
            
        except Exception as e:
            print(f"❌ Error extracting text from {pdf_path}: {e}")
            return ""
    
    def chunk_text(self, text: str, chunk_size: Optional[int] = None, 
                   overlap_size: Optional[int] = None) -> List[str]:
        """Advanced text chunking with sentence boundary awareness"""
        if not text.strip():
            return []
        
        chunk_size = chunk_size or self.config.pdf_chunk_size
        overlap_size = overlap_size or self.config.pdf_overlap_size
        
        # Split into sentences more intelligently
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        sentences = [s.strip() for s in sentences if s.strip()]
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence_length = len(sentence.split())
            
            # If adding this sentence would exceed target, save current chunk
            if current_length + sentence_length > chunk_size and current_chunk:
                chunks.append(" ".join(current_chunk))
                
                # Keep overlap sentences
                overlap_sentences = max(1, len(current_chunk) // 4)  # Keep ~25% for overlap
                current_chunk = current_chunk[-overlap_sentences:]
                current_length = sum(len(s.split()) for s in current_chunk)
            
            current_chunk.append(sentence)
            current_length += sentence_length
        
        # Add final chunk
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        return chunks
    
    def detect_figures_tables(self, pdf_path: str) -> Dict[str, Any]:
        """Detect figures and tables in PDF"""
        if not self.available:
            return {"has_figures": False, "has_tables": False, "total_figures": 0, "total_tables": 0}
        
        try:
            doc = fitz.open(pdf_path)
            total_figures = 0
            total_tables = 0
            
            for page in doc:
                # Count images/figures
                images = page.get_images()
                figures = [img for img in images if img[0] > 0]  # Filter out small images
                total_figures += len(figures)
                
                # Count tables
                try:
                    tables = page.find_tables()
                    if tables and hasattr(tables, '__len__'):
                        total_tables += len(tables)
                    elif tables:
                        total_tables += 1  # Count as 1 if it's a single table object
                except Exception:
                    pass  # Skip table detection if it fails
            
            doc.close()
            
            return {
                "has_figures": total_figures > 0,
                "has_tables": total_tables > 0,
                "total_figures": total_figures,
                "total_tables": total_tables
            }
            
        except Exception as e:
            print(f"⚠️ Error detecting figures/tables in {pdf_path}: {e}")
            return {"has_figures": False, "has_tables": False, "total_figures": 0, "total_tables": 0}
    
    def get_metadata(self, pdf_path: str) -> Dict[str, Any]:
        """Get comprehensive PDF metadata"""
        if not self.available:
            return {"error": "PyMuPDF not available"}
        
        try:
            doc = fitz.open(pdf_path)
            
            # Basic metadata
            metadata = {
                "total_pages": len(doc),
                "file_size": Path(pdf_path).stat().st_size,
                "filename": Path(pdf_path).name
            }
            
            # Get figures and tables
            figures_tables = self.detect_figures_tables(pdf_path)
            metadata.update(figures_tables)
            
            # Get text statistics
            text = self.extract_text(pdf_path)
            if text:
                metadata.update({
                    "total_characters": len(text),
                    "total_words": len(text.split()),
                    "total_sentences": len(re.split(r'[.!?]+', text))
                })
            
            doc.close()
            return metadata
            
        except Exception as e:
            print(f"❌ Error getting metadata from {pdf_path}: {e}")
            return {"error": str(e)}
    
    def process_pdf_for_analysis(self, pdf_path: str, pdf_text: str = "") -> Dict[str, Any]:
        """Process PDF for LLM analysis with enhanced content selection"""
        if not self.available or not Path(pdf_path).exists():
            # Fallback to basic text processing
            return {
                "content": pdf_text[:self.config.max_pdf_content] if pdf_text else "",
                "metadata": {"has_figures": False, "has_tables": False, "total_figures": 0, "total_tables": 0},
                "chunks": []
            }
        
        try:
            # Get enhanced metadata
            pdf_stats = self.get_metadata(pdf_path)
            
            # Use enhanced chunking
            if pdf_text:
                chunks = self.chunk_text(pdf_text, 
                                       chunk_size=self.config.pdf_chunk_size,
                                       overlap_size=self.config.pdf_overlap_size)
            else:
                chunks = []
            
            # Select most relevant chunks (focus on beginning and key sections)
            enhanced_content = ""
            if chunks:
                # Prioritize first chunk (usually abstract/introduction)
                enhanced_content = chunks[0]
                
                # Add middle chunk if available (usually methods/results)
                if len(chunks) > 2:
                    enhanced_content += "\n\n" + chunks[len(chunks)//2]
                
                # Add last chunk if available (usually conclusions)
                if len(chunks) > 1:
                    enhanced_content += "\n\n" + chunks[-1]
            
            return {
                "content": enhanced_content[:self.config.max_pdf_content],
                "metadata": {
                    "has_figures": pdf_stats.get("total_figures", 0) > 0,
                    "has_tables": pdf_stats.get("total_tables", 0) > 0,
                    "total_figures": pdf_stats.get("total_figures", 0),
                    "total_tables": pdf_stats.get("total_tables", 0),
                    "total_pages": pdf_stats.get("total_pages", 0)
                },
                "chunks": chunks
            }
            
        except Exception as e:
            print(f"⚠️ Error in enhanced PDF processing: {e}")
            # Fallback to basic processing
            return {
                "content": pdf_text[:self.config.max_pdf_content] if pdf_text else "",
                "metadata": {"has_figures": False, "has_tables": False, "total_figures": 0, "total_tables": 0},
                "chunks": []
            }
    
    def is_available(self) -> bool:
        """Check if PDF processing is available"""
        return self.available
