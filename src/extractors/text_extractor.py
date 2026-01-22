"""
Text extraction from PDF using pdfplumber.
"""
from typing import Optional, List, Dict, Any
import tempfile
import os

import pdfplumber


class TextExtractor:
    """Extract text from PDF while preserving layout."""
    
    def __init__(self):
        self._temp_path: Optional[str] = None
    
    def extract_from_bytes(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """
        Extract text from PDF bytes.
        
        Returns:
            Dict with 'full_text', 'pages', and 'metadata'
        """
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_bytes)
            self._temp_path = tmp.name
        
        try:
            return self._extract_from_path(self._temp_path)
        finally:
            self._cleanup()
    
    def extract_from_path(self, pdf_path: str) -> Dict[str, Any]:
        """Extract text from PDF file path."""
        return self._extract_from_path(pdf_path)
    
    def _extract_from_path(self, pdf_path: str) -> Dict[str, Any]:
        """Internal extraction logic."""
        result = {
            "full_text": "",
            "pages": [],
            "page_count": 0,
            "metadata": {}
        }
        
        with pdfplumber.open(pdf_path) as pdf:
            result["page_count"] = len(pdf.pages)
            result["metadata"] = pdf.metadata or {}
            
            all_text_parts = []
            
            for i, page in enumerate(pdf.pages):
                page_data = self._extract_page(page, i + 1)
                result["pages"].append(page_data)
                all_text_parts.append(page_data["text"])
            
            result["full_text"] = "\n\n".join(all_text_parts)
        
        return result
    
    def _extract_page(self, page: pdfplumber.page.Page, page_num: int) -> Dict[str, Any]:
        """Extract text and structure from a single page."""
        # Extract text with layout preservation
        text = page.extract_text(
            layout=True,
            x_tolerance=3,
            y_tolerance=3
        ) or ""
        
        # Get page dimensions
        width = page.width
        height = page.height
        
        # Detect if page has tables
        tables = page.find_tables()
        has_tables = len(tables) > 0
        
        # Detect if page has images
        images = page.images
        has_images = len(images) > 0
        
        return {
            "page_number": page_num,
            "text": text,
            "width": width,
            "height": height,
            "has_tables": has_tables,
            "table_count": len(tables),
            "has_images": has_images,
            "image_count": len(images)
        }
    
    def extract_sections(self, pdf_bytes: bytes) -> List[Dict[str, str]]:
        """
        Extract text organized by detected sections.
        
        Returns:
            List of sections with 'title' and 'content'
        """
        data = self.extract_from_bytes(pdf_bytes)
        
        # Simple section detection based on common patterns
        sections = []
        current_section = {"title": "Introduction", "content": ""}
        
        lines = data["full_text"].split("\n")
        
        for line in lines:
            stripped = line.strip()
            
            # Detect section headers (ALL CAPS or Title Case with certain keywords)
            if self._is_section_header(stripped):
                if current_section["content"].strip():
                    sections.append(current_section)
                current_section = {"title": stripped, "content": ""}
            else:
                current_section["content"] += line + "\n"
        
        # Add last section
        if current_section["content"].strip():
            sections.append(current_section)
        
        return sections
    
    def _is_section_header(self, text: str) -> bool:
        """Detect if a line is likely a section header."""
        if not text or len(text) < 3 or len(text) > 100:
            return False
        
        # Common section keywords in annual reports
        header_keywords = [
            "performance", "holdings", "allocation", "commentary",
            "overview", "summary", "portfolio", "fund", "investment",
            "risk", "sustainability", "esg", "sector", "region",
            "return", "benchmark", "strategy"
        ]
        
        text_lower = text.lower()
        
        # Check if ALL CAPS (likely header)
        if text.isupper() and len(text.split()) <= 6:
            return True
        
        # Check if contains header keywords and is relatively short
        if any(kw in text_lower for kw in header_keywords) and len(text.split()) <= 8:
            return True
        
        return False
    
    def _cleanup(self):
        """Clean up temporary files."""
        if self._temp_path and os.path.exists(self._temp_path):
            try:
                os.unlink(self._temp_path)
            except:
                pass
            self._temp_path = None
