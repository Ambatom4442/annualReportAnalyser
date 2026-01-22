"""
Pydantic models for comment generation parameters.
"""
from typing import List, Optional, Literal
from pydantic import BaseModel


class CommentParameters(BaseModel):
    """Parameters for comment generation selected by user."""
    
    # Comment type
    comment_type: Literal[
        "asset_manager_comment",
        "performance_summary", 
        "risk_analysis",
        "sustainability_report",
        "newsletter_excerpt",
        "custom"
    ] = "asset_manager_comment"
    
    # Time and comparison
    time_period: Optional[str] = None
    compare_benchmark: bool = True
    
    # Content selection
    top_n_holdings: int = 5
    include_positive_contributors: bool = True
    include_negative_contributors: bool = True
    include_sector_impact: bool = True
    
    # Style
    tone: Literal["formal", "conversational", "technical"] = "formal"
    length: Literal["brief", "medium", "detailed"] = "medium"
    
    # Custom instructions
    custom_instructions: Optional[str] = None
