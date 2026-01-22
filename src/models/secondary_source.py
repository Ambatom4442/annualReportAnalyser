"""
Models for secondary/supporting sources.
"""
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class SourceType(str, Enum):
    """Type of secondary source."""
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    CSV = "csv"
    URL = "url"
    STOCK = "stock"


@dataclass
class SecondarySource:
    """
    Represents a secondary/supporting source linked to a primary document.
    """
    source_id: str
    parent_doc_id: str  # Links to primary document
    source_type: SourceType
    name: str  # Display name
    
    # Content
    content_md: str = ""  # Markdown content (from Docling or scraping)
    original_url: Optional[str] = None  # For URL sources
    ticker: Optional[str] = None  # For stock sources
    
    # Metadata
    is_temporary: bool = True  # Session-only or permanent
    session_id: Optional[str] = None  # For cleanup of temp sources
    created_at: datetime = field(default_factory=datetime.now)
    file_size: int = 0
    
    # Processing status
    is_processed: bool = False
    chunk_count: int = 0
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "source_id": self.source_id,
            "parent_doc_id": self.parent_doc_id,
            "source_type": self.source_type.value if isinstance(self.source_type, SourceType) else self.source_type,
            "name": self.name,
            "content_md": self.content_md,
            "original_url": self.original_url,
            "ticker": self.ticker,
            "is_temporary": self.is_temporary,
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "file_size": self.file_size,
            "is_processed": self.is_processed,
            "chunk_count": self.chunk_count,
            "error": self.error
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "SecondarySource":
        """Create from dictionary."""
        # Handle source_type
        source_type = data.get("source_type", "txt")
        if isinstance(source_type, str):
            try:
                source_type = SourceType(source_type)
            except ValueError:
                source_type = SourceType.TXT
        
        # Handle created_at
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at)
            except:
                created_at = datetime.now()
        elif not created_at:
            created_at = datetime.now()
        
        return cls(
            source_id=data.get("source_id", ""),
            parent_doc_id=data.get("parent_doc_id", ""),
            source_type=source_type,
            name=data.get("name", ""),
            content_md=data.get("content_md", ""),
            original_url=data.get("original_url"),
            ticker=data.get("ticker"),
            is_temporary=data.get("is_temporary", True),
            session_id=data.get("session_id"),
            created_at=created_at,
            file_size=data.get("file_size", 0),
            is_processed=data.get("is_processed", False),
            chunk_count=data.get("chunk_count", 0),
            error=data.get("error")
        )
