"""
Pydantic models for extracted PDF data.
"""
from typing import List, Optional
from pydantic import BaseModel


class PerformanceData(BaseModel):
    """Fund performance data."""
    fund_return: Optional[float] = None
    benchmark_return: Optional[float] = None
    period: Optional[str] = None
    outperformance: Optional[float] = None


class HoldingData(BaseModel):
    """Individual holding data."""
    name: str
    weight: Optional[float] = None
    sector: Optional[str] = None
    contribution: Optional[float] = None


class SectorData(BaseModel):
    """Sector allocation data."""
    sector: str
    weight: float


class TableData(BaseModel):
    """Raw table data from PDF."""
    page: int
    table_type: str
    headers: List[str]
    rows: List[List[str]]


class ExtractedData(BaseModel):
    """Complete extracted data from PDF."""
    fund_name: Optional[str] = None
    report_period: Optional[str] = None
    benchmark_index: Optional[str] = None
    currency: Optional[str] = None
    
    performance: Optional[PerformanceData] = None
    holdings: List[HoldingData] = []
    sectors: List[SectorData] = []
    
    raw_text: Optional[str] = None
    raw_tables: List[TableData] = []  # All tables from PDF
    chart_descriptions: List[str] = []
