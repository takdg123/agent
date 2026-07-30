#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Vision capabilities for PDF processing
Converts PDFs to images for vision-enabled LLMs
"""

import base64
from pathlib import Path
from typing import List, Dict, Any, Optional
import tempfile

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

class VisionProcessor:
    """Handles PDF to image conversion for vision LLMs"""
    
    def __init__(self, config):
        self.config = config
        self.available = PYMUPDF_AVAILABLE
        
        # Vision processing configuration
        self.dpi = getattr(config, 'vision_dpi', 150)  # DPI for rendering
        self.max_pages = getattr(config, 'vision_max_pages', 5)  # Max pages to convert
        self.image_format = getattr(config, 'vision_image_format', 'png')
        
        if not self.available:
            print("⚠️ PyMuPDF not available for vision processing")
    
    def pdf_to_images(self, pdf_path: str, pages: Optional[List[int]] = None) -> List[Dict[str, Any]]:
        """Convert PDF pages to images
        
        Args:
            pdf_path: Path to PDF file
            pages: List of page numbers to convert (0-indexed). If None, converts all pages up to max_pages
            
        Returns:
            List of dicts with page number, image path, and base64 data
        """
        if not self.available:
            return []
        
        if not Path(pdf_path).exists():
            print(f"❌ PDF file not found: {pdf_path}")
            return []
        
        try:
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            
            # Determine which pages to process
            if pages is None:
                pages = list(range(min(total_pages, self.max_pages)))
            else:
                pages = [p for p in pages if 0 <= p < total_pages]
            
            images = []
            temp_dir = Path(tempfile.mkdtemp(prefix="torri_vision_"))
            
            for page_num in pages:
                page = doc[page_num]
                
                # Render page to pixmap
                mat = fitz.Matrix(self.dpi / 72, self.dpi / 72)  # Scale matrix
                pix = page.get_pixmap(matrix=mat)
                
                # Save to temp file
                image_path = temp_dir / f"page_{page_num}.{self.image_format}"
                pix.save(str(image_path))
                
                # Convert to base64 for API transmission
                with open(image_path, 'rb') as img_file:
                    image_data = base64.b64encode(img_file.read()).decode('utf-8')
                
                images.append({
                    "page_number": page_num,
                    "image_path": str(image_path),
                    "base64": image_data,
                    "url": f"data:image/{self.image_format};base64,{image_data}",
                    "width": pix.width,
                    "height": pix.height
                })
                
                print(f"✅ Converted page {page_num + 1}/{total_pages} to image")
            
            doc.close()
            return images
            
        except Exception as e:
            print(f"❌ Error converting PDF to images: {e}")
            return []
    
    def extract_figures(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Extract figure images from PDF
        
        Returns:
            List of dicts with figure info and image data
        """
        if not self.available:
            return []
        
        try:
            doc = fitz.open(pdf_path)
            figures = []
            
            for page_num, page in enumerate(doc):
                # Get all images on the page
                image_list = page.get_images()
                
                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    
                    if base_image:
                        image_bytes = base_image["image"]
                        image_ext = base_image["ext"]
                        
                        # Save to temp file
                        temp_dir = Path(tempfile.mkdtemp(prefix="torri_figures_"))
                        image_path = temp_dir / f"page{page_num}_fig{img_index}.{image_ext}"
                        
                        with open(image_path, 'wb') as img_file:
                            img_file.write(image_bytes)
                        
                        # Convert to base64
                        image_data = base64.b64encode(image_bytes).decode('utf-8')
                        
                        figures.append({
                            "page_number": page_num,
                            "figure_index": img_index,
                            "image_path": str(image_path),
                            "base64": image_data,
                            "url": f"data:image/{image_ext};base64,{image_data}",
                            "format": image_ext
                        })
            
            doc.close()
            print(f"✅ Extracted {len(figures)} figures from PDF")
            return figures
            
        except Exception as e:
            print(f"❌ Error extracting figures: {e}")
            return []
    
    def smart_page_selection(self, pdf_path: str, max_pages: Optional[int] = None) -> List[int]:
        """Intelligently select which pages to convert based on content
        
        Prioritizes:
        - First page (usually has abstract)
        - Pages with many figures
        - Last page (usually has conclusions)
        
        Returns:
            List of page numbers to process
        """
        if not self.available:
            return []
        
        max_pages = max_pages or self.max_pages
        
        try:
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            
            if total_pages <= max_pages:
                # If PDF is short, process all pages
                doc.close()
                return list(range(total_pages))
            
            # Analyze pages
            page_scores = []
            for page_num in range(total_pages):
                page = doc[page_num]
                
                score = 0
                
                # First page bonus
                if page_num == 0:
                    score += 100
                
                # Last page bonus
                if page_num == total_pages - 1:
                    score += 50
                
                # Count images (figures)
                images = page.get_images()
                score += len(images) * 10
                
                # Count text (favor pages with substantial content)
                text = page.get_text()
                score += min(len(text.split()), 100) / 10
                
                page_scores.append((page_num, score))
            
            # Sort by score and select top pages
            page_scores.sort(key=lambda x: x[1], reverse=True)
            selected_pages = sorted([p[0] for p in page_scores[:max_pages]])
            
            doc.close()
            print(f"✅ Selected {len(selected_pages)} pages from {total_pages} total pages")
            return selected_pages
            
        except Exception as e:
            print(f"❌ Error in smart page selection: {e}")
            return list(range(min(total_pages, max_pages)))
    
    def is_available(self) -> bool:
        """Check if vision processing is available"""
        return self.available
