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
