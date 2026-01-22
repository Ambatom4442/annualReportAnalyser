"""
Chat history storage for persisting conversations per document.
"""
import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime


class ChatStore:
    """Store and retrieve chat history per document."""
    
    def __init__(self, db_path: str = ".data/chat_history.db"):
        """Initialize the chat history store."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    doc_id TEXT NOT NULL,
                    chat_type TEXT NOT NULL DEFAULT 'main',
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    metadata TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_chat_doc_id 
                ON chat_history(doc_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_chat_type 
                ON chat_history(doc_id, chat_type)
            """)
            
            # Research summaries table - separate from chat history
            conn.execute("""
                CREATE TABLE IF NOT EXISTS research_summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    doc_id TEXT,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source_type TEXT NOT NULL DEFAULT 'quick',
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_summary_doc_id 
                ON research_summaries(doc_id)
            """)
            conn.commit()
    
    def save_message(
        self, 
        doc_id: str, 
        role: str, 
        content: str, 
        chat_type: str = "main",
        metadata: Optional[Dict] = None
    ) -> int:
        """
        Save a chat message.
        
        Args:
            doc_id: Document ID the chat is associated with
            role: "user" or "assistant"
            content: Message content
            chat_type: "main" (Chat with Documents) or "quick" (Quick Chat)
            metadata: Optional additional data
        
        Returns:
            Message ID
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO chat_history (doc_id, chat_type, role, content, created_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                doc_id,
                chat_type,
                role,
                content,
                datetime.now().isoformat(),
                json.dumps(metadata) if metadata else None
            ))
            conn.commit()
            return cursor.lastrowid
    
    def get_messages(
        self, 
        doc_id: str, 
        chat_type: str = "main",
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        Get chat messages for a document.
        
        Args:
            doc_id: Document ID
            chat_type: "main" or "quick"
            limit: Optional limit on number of messages
        
        Returns:
            List of message dictionaries with role and content
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            query = """
                SELECT role, content, created_at, metadata
                FROM chat_history
                WHERE doc_id = ? AND chat_type = ?
                ORDER BY id ASC
            """
            
            if limit:
                query += f" LIMIT {limit}"
            
            cursor = conn.execute(query, (doc_id, chat_type))
            rows = cursor.fetchall()
            
            return [
                {
                    "role": row["role"],
                    "content": row["content"],
                    "created_at": row["created_at"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else None
                }
                for row in rows
            ]
    
    def clear_history(self, doc_id: str, chat_type: Optional[str] = None) -> int:
        """
        Clear chat history for a document.
        
        Args:
            doc_id: Document ID
            chat_type: Optional - if provided, only clears that chat type
        
        Returns:
            Number of messages deleted
        """
        with sqlite3.connect(self.db_path) as conn:
            if chat_type:
                cursor = conn.execute("""
                    DELETE FROM chat_history
                    WHERE doc_id = ? AND chat_type = ?
                """, (doc_id, chat_type))
            else:
                cursor = conn.execute("""
                    DELETE FROM chat_history
                    WHERE doc_id = ?
                """, (doc_id,))
            conn.commit()
            return cursor.rowcount
    
    def clear_all_history(self) -> int:
        """Clear all chat history."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM chat_history")
            conn.commit()
            return cursor.rowcount
    
    def get_documents_with_history(self) -> List[str]:
        """Get list of document IDs that have chat history."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT DISTINCT doc_id FROM chat_history
            """)
            return [row[0] for row in cursor.fetchall()]
    
    def get_message_count(self, doc_id: str, chat_type: Optional[str] = None) -> int:
        """Get count of messages for a document."""
        with sqlite3.connect(self.db_path) as conn:
            if chat_type:
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM chat_history
                    WHERE doc_id = ? AND chat_type = ?
                """, (doc_id, chat_type))
            else:
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM chat_history
                    WHERE doc_id = ?
                """, (doc_id,))
            return cursor.fetchone()[0]

    # ==================== Research Summaries ====================
    
    def save_summary(
        self,
        title: str,
        content: str,
        doc_id: Optional[str] = None,
        source_type: str = "quick"
    ) -> int:
        """
        Save a research summary.
        
        Args:
            title: User-provided or auto-generated title
            content: The summary content
            doc_id: Optional document ID (None for general summaries)
            source_type: "main" (Chat with Documents) or "quick" (Quick Chat)
        
        Returns:
            Summary ID
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO research_summaries (doc_id, title, content, source_type, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                doc_id,
                title,
                content,
                source_type,
                datetime.now().isoformat()
            ))
            conn.commit()
            return cursor.lastrowid
    
    def get_summaries(self, doc_id: Optional[str] = None) -> List[Dict]:
        """
        Get research summaries.
        
        Args:
            doc_id: Optional document ID filter. If None, returns all summaries.
        
        Returns:
            List of summary dictionaries
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            if doc_id:
                # Get summaries for specific doc OR general summaries (doc_id is NULL)
                cursor = conn.execute("""
                    SELECT id, doc_id, title, content, source_type, created_at
                    FROM research_summaries
                    WHERE doc_id = ? OR doc_id IS NULL
                    ORDER BY created_at DESC
                """, (doc_id,))
            else:
                cursor = conn.execute("""
                    SELECT id, doc_id, title, content, source_type, created_at
                    FROM research_summaries
                    ORDER BY created_at DESC
                """)
            
            rows = cursor.fetchall()
            return [
                {
                    "id": row["id"],
                    "doc_id": row["doc_id"],
                    "title": row["title"],
                    "content": row["content"],
                    "source_type": row["source_type"],
                    "created_at": row["created_at"]
                }
                for row in rows
            ]
    
    def get_summary_by_id(self, summary_id: int) -> Optional[Dict]:
        """Get a specific summary by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT id, doc_id, title, content, source_type, created_at
                FROM research_summaries
                WHERE id = ?
            """, (summary_id,))
            row = cursor.fetchone()
            if row:
                return {
                    "id": row["id"],
                    "doc_id": row["doc_id"],
                    "title": row["title"],
                    "content": row["content"],
                    "source_type": row["source_type"],
                    "created_at": row["created_at"]
                }
            return None
    
    def delete_summary(self, summary_id: int) -> bool:
        """Delete a research summary by ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                DELETE FROM research_summaries
                WHERE id = ?
            """, (summary_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def delete_all_summaries(self, doc_id: Optional[str] = None) -> int:
        """
        Delete all summaries, optionally filtered by document.
        
        Args:
            doc_id: Optional document ID. If None, deletes ALL summaries.
        
        Returns:
            Number of summaries deleted
        """
        with sqlite3.connect(self.db_path) as conn:
            if doc_id:
                cursor = conn.execute("""
                    DELETE FROM research_summaries
                    WHERE doc_id = ?
                """, (doc_id,))
            else:
                cursor = conn.execute("DELETE FROM research_summaries")
            conn.commit()
            return cursor.rowcount
    
    def get_summary_count(self, doc_id: Optional[str] = None) -> int:
        """Get count of summaries."""
        with sqlite3.connect(self.db_path) as conn:
            if doc_id:
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM research_summaries
                    WHERE doc_id = ? OR doc_id IS NULL
                """, (doc_id,))
            else:
                cursor = conn.execute("SELECT COUNT(*) FROM research_summaries")
            return cursor.fetchone()[0]
