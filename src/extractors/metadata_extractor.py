"""
Metadata extraction from PDF.
"""
from typing import Dict, Any, Optional, List
import re


class MetadataExtractor:
    """Extract metadata like fund name, period, currency from PDF."""
    
    # Common patterns for financial report metadata
    FUND_NAME_PATTERNS = [
        r"(?:fund|portfolio)[\s:]+([A-Z][A-Za-z\s\-]+(?:Fund|Portfolio|Index))",
        r"^([A-Z][A-Za-z\s\-]+(?:Fund|Portfolio|ETF))",
    ]
    
    PERIOD_PATTERNS = [
        r"(?:period|date|as of|for)[\s:]+(\d{1,2}[\s\-/]\w+[\s\-/]\d{4})",
        r"(?:period|date|as of|for)[\s:]+(\w+\s+\d{4})",
        r"(\d{1,2}\s+\w+\s+\d{4})",
        r"(Q[1-4]\s+\d{4})",
        r"(FY\s*\d{4})",
    ]
    
    BENCHMARK_PATTERNS = [
        r"(?:benchmark|index)[\s:]+([A-Z][A-Za-z\s\-&]+(?:Index|Benchmark)?)",
        r"vs\.?\s+([A-Z][A-Za-z\s\-&]+(?:Index))",
    ]
    
    CURRENCY_PATTERNS = [
        r"(?:currency|ccy)[\s:]+([A-Z]{3})",
        r"\b(USD|EUR|GBP|JPY|SEK|NOK|DKK|CHF)\b",
    ]
    
    def __init__(self):
        pass
    
    def extract_from_text(self, text: str) -> Dict[str, Any]:
        """
        Extract metadata from extracted PDF text.
        
        Returns:
            Dict with fund_name, report_period, benchmark_index, currency, etc.
        """
        metadata = {
            "fund_name": self._extract_fund_name(text),
            "report_period": self._extract_period(text),
            "benchmark_index": self._extract_benchmark(text),
            "currency": self._extract_currency(text),
            "report_type": self._detect_report_type(text),
            "detected_sections": self._detect_sections(text)
        }
        
        return metadata
    
    def _extract_fund_name(self, text: str) -> Optional[str]:
        """Extract fund name from text."""
        # Take first 2000 chars (usually header info)
        header_text = text[:2000]
        
        for pattern in self.FUND_NAME_PATTERNS:
            match = re.search(pattern, header_text, re.IGNORECASE | re.MULTILINE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_period(self, text: str) -> Optional[str]:
        """Extract reporting period from text."""
        header_text = text[:3000]
        
        for pattern in self.PERIOD_PATTERNS:
            match = re.search(pattern, header_text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_benchmark(self, text: str) -> Optional[str]:
        """Extract benchmark index name from text."""
        for pattern in self.BENCHMARK_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_currency(self, text: str) -> Optional[str]:
        """Extract currency from text."""
        header_text = text[:2000]
        
        for pattern in self.CURRENCY_PATTERNS:
            match = re.search(pattern, header_text, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        
        return None
    
    def _detect_report_type(self, text: str) -> str:
        """Detect the type of report."""
        text_lower = text.lower()
        
        if "annual" in text_lower:
            return "annual"
        elif "semi-annual" in text_lower or "semi annual" in text_lower:
            return "semi-annual"
        elif "quarterly" in text_lower or "q1" in text_lower or "q2" in text_lower:
            return "quarterly"
        elif "monthly" in text_lower:
            return "monthly"
        elif "factsheet" in text_lower or "fact sheet" in text_lower:
            return "factsheet"
        
        return "unknown"
    
    def _detect_sections(self, text: str) -> List[str]:
        """Detect which standard sections are present in the document."""
        sections = []
        text_lower = text.lower()
        
        section_keywords = {
            "performance": ["performance", "return", "ytd", "mtd"],
            "holdings": ["holdings", "portfolio composition", "top holdings"],
            "sector_allocation": ["sector allocation", "sector breakdown", "industry"],
            "regional_allocation": ["regional", "geographic", "country allocation"],
            "risk_metrics": ["risk", "volatility", "sharpe ratio", "drawdown"],
            "sustainability": ["esg", "sustainability", "carbon", "climate"],
            "manager_commentary": ["commentary", "manager", "outlook", "review"],
            "fees": ["fees", "charges", "expense ratio", "ter"],
        }
        
        for section, keywords in section_keywords.items():
            if any(kw in text_lower for kw in keywords):
                sections.append(section)
        
        return sections
    
    def extract_performance_numbers(self, text: str) -> Dict[str, Optional[float]]:
        """
        Extract key performance numbers from text.
        """
        result = {
            "fund_return": None,
            "benchmark_return": None,
            "ytd_return": None,
            "mtd_return": None,
            "one_year_return": None
        }
        
        # Pattern for percentage returns
        return_patterns = [
            (r"fund.*?return.*?([\-\+]?\d+\.?\d*)\s*%", "fund_return"),
            (r"benchmark.*?return.*?([\-\+]?\d+\.?\d*)\s*%", "benchmark_return"),
            (r"ytd.*?([\-\+]?\d+\.?\d*)\s*%", "ytd_return"),
            (r"mtd.*?([\-\+]?\d+\.?\d*)\s*%", "mtd_return"),
            (r"1\s*year.*?([\-\+]?\d+\.?\d*)\s*%", "one_year_return"),
        ]
        
        text_lower = text.lower()
        
        for pattern, key in return_patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    result[key] = float(match.group(1))
                except ValueError:
                    pass
        
        return result
