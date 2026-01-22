"""
Storage for secondary sources - SQLite based.
"""
import sqlite3
import json
from typing import List, Optional
from pathlib import Path
from datetime import datetime

from models.secondary_source import SecondarySource, SourceType


class SecondarySourceStore:
    """
    SQLite-based storage for secondary/supporting sources.
    """
    
    def __init__(self, db_path: str = ".data/secondary_sources.db"):
        """Initialize the secondary source store."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS secondary_sources (
                    source_id TEXT PRIMARY KEY,
                    parent_doc_id TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    content_md TEXT,
                    original_url TEXT,
                    ticker TEXT,
                    is_temporary INTEGER DEFAULT 1,
                    session_id TEXT,
                    created_at TEXT,
                    file_size INTEGER DEFAULT 0,
                    is_processed INTEGER DEFAULT 0,
                    chunk_count INTEGER DEFAULT 0,
                    error TEXT
                )
            """)
            
            # Index for faster queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_parent_doc 
                ON secondary_sources(parent_doc_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_session 
                ON secondary_sources(session_id)
            """)
            conn.commit()
    
    def add(self, source: SecondarySource) -> bool:
        """Add a secondary source."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO secondary_sources 
                    (source_id, parent_doc_id, source_type, name, content_md,
                     original_url, ticker, is_temporary, session_id, created_at,
                     file_size, is_processed, chunk_count, error)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    source.source_id,
                    source.parent_doc_id,
                    source.source_type.value if isinstance(source.source_type, SourceType) else source.source_type,
                    source.name,
                    source.content_md,
                    source.original_url,
                    source.ticker,
                    1 if source.is_temporary else 0,
                    source.session_id,
                    source.created_at.isoformat() if source.created_at else None,
                    source.file_size,
                    1 if source.is_processed else 0,
                    source.chunk_count,
                    source.error
                ))
                conn.commit()
            return True
        except Exception as e:
            print(f"Error adding secondary source: {e}")
            return False
    
    def get(self, source_id: str) -> Optional[SecondarySource]:
        """Get a secondary source by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM secondary_sources WHERE source_id = ?",
                (source_id,)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_source(dict(row))
        return None
    
    def get_by_parent(self, parent_doc_id: str, include_temporary: bool = True) -> List[SecondarySource]:
        """Get all secondary sources for a parent document."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if include_temporary:
                cursor = conn.execute(
                    "SELECT * FROM secondary_sources WHERE parent_doc_id = ? ORDER BY created_at DESC",
                    (parent_doc_id,)
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM secondary_sources WHERE parent_doc_id = ? AND is_temporary = 0 ORDER BY created_at DESC",
                    (parent_doc_id,)
                )
            return [self._row_to_source(dict(row)) for row in cursor.fetchall()]
    
    def get_by_session(self, session_id: str) -> List[SecondarySource]:
        """Get all secondary sources for a session."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM secondary_sources WHERE session_id = ?",
                (session_id,)
            )
            return [self._row_to_source(dict(row)) for row in cursor.fetchall()]
    
    def get_all(self, parent_doc_id: Optional[str] = None) -> List[SecondarySource]:
        """Get all secondary sources, optionally filtered by parent."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if parent_doc_id:
                cursor = conn.execute(
                    "SELECT * FROM secondary_sources WHERE parent_doc_id = ? ORDER BY created_at DESC",
                    (parent_doc_id,)
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM secondary_sources ORDER BY created_at DESC"
                )
            return [self._row_to_source(dict(row)) for row in cursor.fetchall()]
    
    def update(self, source: SecondarySource) -> bool:
        """Update a secondary source."""
        return self.add(source)  # INSERT OR REPLACE handles this
    
    def delete(self, source_id: str) -> bool:
        """Delete a secondary source."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "DELETE FROM secondary_sources WHERE source_id = ?",
                    (source_id,)
                )
                conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting secondary source: {e}")
            return False
    
    def delete_by_session(self, session_id: str) -> int:
        """Delete all temporary sources for a session. Returns count deleted."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "DELETE FROM secondary_sources WHERE session_id = ? AND is_temporary = 1",
                    (session_id,)
                )
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            print(f"Error deleting session sources: {e}")
            return 0
    
    def cleanup_old_temporary(self, hours: int = 24) -> int:
        """Clean up temporary sources older than specified hours."""
        from datetime import timedelta
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "DELETE FROM secondary_sources WHERE is_temporary = 1 AND created_at < ?",
                    (cutoff,)
                )
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            print(f"Error cleaning up old sources: {e}")
            return 0
    
    def delete_by_parent_doc(self, parent_doc_id: str) -> int:
        """Delete all secondary sources associated with a parent document.
        
        Returns the count of deleted sources.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # First get the source_ids for cleanup
                cursor = conn.execute(
                    "SELECT source_id FROM secondary_sources WHERE parent_doc_id = ?",
                    (parent_doc_id,)
                )
                source_ids = [row[0] for row in cursor.fetchall()]
                
                # Delete the sources
                cursor = conn.execute(
                    "DELETE FROM secondary_sources WHERE parent_doc_id = ?",
                    (parent_doc_id,)
                )
                conn.commit()
                return cursor.rowcount, source_ids
        except Exception as e:
            print(f"Error deleting secondary sources for parent doc: {e}")
            return 0, []
    
    def make_permanent(self, source_id: str) -> bool:
        """Convert a temporary source to permanent."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE secondary_sources SET is_temporary = 0 WHERE source_id = ?",
                    (source_id,)
                )
                conn.commit()
            return True
        except Exception as e:
            print(f"Error making source permanent: {e}")
            return False
    
    def _row_to_source(self, row: dict) -> SecondarySource:
        """Convert database row to SecondarySource."""
        row["is_temporary"] = bool(row.get("is_temporary", 1))
        row["is_processed"] = bool(row.get("is_processed", 0))
        return SecondarySource.from_dict(row)
