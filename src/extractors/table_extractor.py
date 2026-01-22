"""
Table extraction from PDF using pdfplumber and PyMuPDF.
"""
from typing import List, Dict, Any, Optional
import tempfile
import os
import re

import pdfplumber
import fitz  # PyMuPDF


class TableExtractor:
    """Extract and parse tables from PDF."""
    
    def __init__(self):
        self._temp_path: Optional[str] = None
    
    def extract_from_bytes(self, pdf_bytes: bytes) -> List[Dict[str, Any]]:
        """Extract all tables from PDF bytes."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_bytes)
            self._temp_path = tmp.name
        
        try:
            return self._extract_tables(self._temp_path)
        finally:
            self._cleanup()
    
    def _extract_tables(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Extract tables using pdfplumber."""
        tables = []
        
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                page_tables = page.extract_tables()
                
                for table_idx, table_data in enumerate(page_tables):
                    if table_data and len(table_data) > 1:
                        parsed = self._parse_table(table_data, page_num, table_idx)
                        if parsed:
                            tables.append(parsed)
        
        return tables
    
    def _parse_table(
        self, 
        table_data: List[List[str]], 
        page_num: int, 
        table_idx: int
    ) -> Optional[Dict[str, Any]]:
        """Parse raw table data into structured format."""
        if not table_data or len(table_data) < 2:
            return None
        
        # Clean the data
        cleaned = []
        for row in table_data:
            cleaned_row = [
                self._clean_cell(cell) if cell else "" 
                for cell in row
            ]
            if any(cleaned_row):  # Skip empty rows
                cleaned.append(cleaned_row)
        
        if len(cleaned) < 2:
            return None
        
        # First row as headers
        headers = cleaned[0]
        rows = cleaned[1:]
        
        # Detect table type
        table_type = self._detect_table_type(headers, rows)
        
        return {
            "page": page_num,
            "table_index": table_idx,
            "type": table_type,
            "headers": headers,
            "rows": rows,
            "row_count": len(rows),
            "col_count": len(headers)
        }
    
    def _clean_cell(self, cell: str) -> str:
        """Clean cell content."""
        if not cell:
            return ""
        # Remove extra whitespace
        cleaned = " ".join(cell.split())
        return cleaned.strip()
    
    def _detect_table_type(
        self, 
        headers: List[str], 
        rows: List[List[str]]
    ) -> str:
        """Detect the type of table based on headers and content."""
        headers_lower = [h.lower() for h in headers if h]
        headers_text = " ".join(headers_lower)
        
        # Holdings table
        if any(kw in headers_text for kw in ["holding", "company", "stock", "security", "weight", "portfolio"]):
            return "holdings"
        
        # Performance table
        if any(kw in headers_text for kw in ["return", "performance", "ytd", "mtd", "benchmark"]):
            return "performance"
        
        # Sector allocation
        if any(kw in headers_text for kw in ["sector", "industry", "allocation"]):
            return "sector_allocation"
        
        # Regional allocation
        if any(kw in headers_text for kw in ["region", "country", "geography"]):
            return "regional_allocation"
        
        # Risk metrics
        if any(kw in headers_text for kw in ["risk", "volatility", "sharpe", "drawdown"]):
            return "risk_metrics"
        
        return "unknown"
    
    def extract_holdings(self, pdf_bytes: bytes) -> List[Dict[str, Any]]:
        """Extract specifically holdings tables."""
        all_tables = self.extract_from_bytes(pdf_bytes)
        return [t for t in all_tables if t["type"] == "holdings"]
    
    def extract_performance(self, pdf_bytes: bytes) -> List[Dict[str, Any]]:
        """Extract specifically performance tables."""
        all_tables = self.extract_from_bytes(pdf_bytes)
        return [t for t in all_tables if t["type"] == "performance"]
    
    def table_to_dict_list(self, table: Dict[str, Any]) -> List[Dict[str, str]]:
        """Convert table to list of dictionaries."""
        headers = table["headers"]
        result = []
        
        for row in table["rows"]:
            row_dict = {}
            for i, header in enumerate(headers):
                if header and i < len(row):
                    row_dict[header] = row[i]
            result.append(row_dict)
        
        return result
    
    def _cleanup(self):
        """Clean up temporary files."""
        if self._temp_path and os.path.exists(self._temp_path):
            try:
                os.unlink(self._temp_path)
            except:
                pass
            self._temp_path = None
