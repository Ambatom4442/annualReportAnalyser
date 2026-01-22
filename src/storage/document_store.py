"""
Document store using SQLite for metadata and file storage.
"""
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import sqlite3
import json
import hashlib
import shutil


class DocumentStore:
    """SQLite-based document metadata store with file management."""
    
    def __init__(self, data_directory: str = ".data"):
        self.data_dir = Path(data_directory)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.db_path = self.data_dir / "documents.db"
        self.files_dir = self.data_dir / "files"
        self.cache_dir = self.data_dir / "cache"
        
        self.files_dir.mkdir(exist_ok=True)
        self.cache_dir.mkdir(exist_ok=True)
        
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize the SQLite database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Documents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                file_hash TEXT UNIQUE NOT NULL,
                file_path TEXT NOT NULL,
                page_count INTEGER,
                fund_name TEXT,
                report_period TEXT,
                benchmark TEXT,
                currency TEXT,
                upload_date TEXT NOT NULL,
                last_accessed TEXT,
                metadata JSON
            )
        """)
        
        # Analysis cache table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analysis_cache (
                doc_id TEXT PRIMARY KEY,
                document_analysis JSON,
                chart_analysis JSON,
                extracted_data JSON,
                created_at TEXT NOT NULL,
                FOREIGN KEY (doc_id) REFERENCES documents(id)
            )
        """)
        
        # Conversations table (for memory persistence)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id TEXT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (doc_id) REFERENCES documents(id)
            )
        """)
        
        # Generated comments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS generated_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id TEXT NOT NULL,
                comment_type TEXT,
                params JSON,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (doc_id) REFERENCES documents(id)
            )
        """)
        
        # User selections table - persists UI content choices
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_selections (
                doc_id TEXT PRIMARY KEY,
                selected_sections JSON,
                selected_tables JSON,
                selected_charts JSON,
                selected_companies JSON,
                selected_metrics JSON,
                selected_themes JSON,
                comment_params JSON,
                custom_instructions TEXT,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (doc_id) REFERENCES documents(id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _compute_hash(self, file_bytes: bytes) -> str:
        """Compute SHA-256 hash of file."""
        return hashlib.sha256(file_bytes).hexdigest()
    
    def _generate_id(self, filename: str, file_hash: str) -> str:
        """Generate a unique document ID."""
        return f"{Path(filename).stem}_{file_hash[:8]}"
    
    def add_document(
        self,
        filename: str,
        file_bytes: bytes,
        metadata: Optional[Dict[str, Any]] = None
    ) -> tuple[str, bool]:
        """
        Add a document to the store.
        
        Returns:
            Tuple of (doc_id, is_new). is_new is False if document already exists.
        """
        file_hash = self._compute_hash(file_bytes)
        
        # Check if document already exists
        existing = self.get_by_hash(file_hash)
        if existing:
            # Update last accessed
            self._update_last_accessed(existing["id"])
            return existing["id"], False
        
        # Generate ID and save file
        doc_id = self._generate_id(filename, file_hash)
        file_path = self.files_dir / f"{doc_id}.pdf"
        
        with open(file_path, "wb") as f:
            f.write(file_bytes)
        
        # Insert into database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.utcnow().isoformat()
        
        cursor.execute("""
            INSERT INTO documents (id, filename, file_hash, file_path, upload_date, last_accessed, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            doc_id,
            filename,
            file_hash,
            str(file_path),
            now,
            now,
            json.dumps(metadata or {})
        ))
        
        conn.commit()
        conn.close()
        
        return doc_id, True
    
    def update_document_metadata(
        self,
        doc_id: str,
        fund_name: Optional[str] = None,
        report_period: Optional[str] = None,
        benchmark: Optional[str] = None,
        currency: Optional[str] = None,
        page_count: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update document metadata after analysis."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        updates = []
        values = []
        
        if fund_name is not None:
            updates.append("fund_name = ?")
            values.append(fund_name)
        if report_period is not None:
            updates.append("report_period = ?")
            values.append(report_period)
        if benchmark is not None:
            updates.append("benchmark = ?")
            values.append(benchmark)
        if currency is not None:
            updates.append("currency = ?")
            values.append(currency)
        if page_count is not None:
            updates.append("page_count = ?")
            values.append(page_count)
        if metadata is not None:
            updates.append("metadata = ?")
            values.append(json.dumps(metadata))
        
        if updates:
            values.append(doc_id)
            cursor.execute(
                f"UPDATE documents SET {', '.join(updates)} WHERE id = ?",
                values
            )
            conn.commit()
        
        conn.close()
    
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get document by ID."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            result = dict(row)
            if result.get("metadata"):
                result["metadata"] = json.loads(result["metadata"])
            return result
        return None
    
    def get_by_hash(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """Get document by file hash."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM documents WHERE file_hash = ?", (file_hash,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            result = dict(row)
            if result.get("metadata"):
                result["metadata"] = json.loads(result["metadata"])
            return result
        return None
    
    def get_file_bytes(self, doc_id: str) -> Optional[bytes]:
        """Get the original PDF file bytes."""
        doc = self.get_document(doc_id)
        if doc and Path(doc["file_path"]).exists():
            with open(doc["file_path"], "rb") as f:
                return f.read()
        return None
    
    def list_documents(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List all documents, most recent first."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, filename, fund_name, report_period, page_count, upload_date, last_accessed
            FROM documents
            ORDER BY last_accessed DESC
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def delete_document(self, doc_id: str) -> bool:
        """Delete a document and its associated data."""
        doc = self.get_document(doc_id)
        if not doc:
            return False
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Delete from all tables
        cursor.execute("DELETE FROM generated_comments WHERE doc_id = ?", (doc_id,))
        cursor.execute("DELETE FROM conversations WHERE doc_id = ?", (doc_id,))
        cursor.execute("DELETE FROM analysis_cache WHERE doc_id = ?", (doc_id,))
        cursor.execute("DELETE FROM user_selections WHERE doc_id = ?", (doc_id,))
        cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        
        conn.commit()
        conn.close()
        
        # Delete file
        file_path = Path(doc["file_path"])
        if file_path.exists():
            file_path.unlink()
        
        return True
    
    def _update_last_accessed(self, doc_id: str) -> None:
        """Update last accessed timestamp."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE documents SET last_accessed = ? WHERE id = ?",
            (datetime.utcnow().isoformat(), doc_id)
        )
        
        conn.commit()
        conn.close()
    
    # Analysis cache methods
    def save_analysis(
        self,
        doc_id: str,
        document_analysis: Optional[Dict] = None,
        chart_analysis: Optional[List] = None,
        extracted_data: Optional[Dict] = None
    ) -> None:
        """Save analysis results to cache."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO analysis_cache (doc_id, document_analysis, chart_analysis, extracted_data, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            doc_id,
            json.dumps(document_analysis) if document_analysis else None,
            json.dumps(chart_analysis) if chart_analysis else None,
            json.dumps(extracted_data) if extracted_data else None,
            datetime.utcnow().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def get_analysis(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get cached analysis for a document."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM analysis_cache WHERE doc_id = ?", (doc_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            result = dict(row)
            if result.get("document_analysis"):
                result["document_analysis"] = json.loads(result["document_analysis"])
            if result.get("chart_analysis"):
                result["chart_analysis"] = json.loads(result["chart_analysis"])
            if result.get("extracted_data"):
                result["extracted_data"] = json.loads(result["extracted_data"])
            return result
        return None
    
    # Conversation memory methods
    def add_message(self, doc_id: Optional[str], role: str, content: str) -> None:
        """Add a message to conversation history."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO conversations (doc_id, role, content, timestamp)
            VALUES (?, ?, ?, ?)
        """, (doc_id, role, content, datetime.utcnow().isoformat()))
        
        conn.commit()
        conn.close()
    
    def get_conversation(self, doc_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, str]]:
        """Get conversation history."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if doc_id:
            cursor.execute("""
                SELECT role, content, timestamp FROM conversations
                WHERE doc_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (doc_id, limit))
        else:
            cursor.execute("""
                SELECT role, content, timestamp FROM conversations
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        # Return in chronological order
        return [dict(row) for row in reversed(rows)]
    
    def clear_conversation(self, doc_id: Optional[str] = None) -> None:
        """Clear conversation history."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if doc_id:
            cursor.execute("DELETE FROM conversations WHERE doc_id = ?", (doc_id,))
        else:
            cursor.execute("DELETE FROM conversations")
        
        conn.commit()
        conn.close()
    
    # Generated comments methods
    def save_comment(
        self,
        doc_id: str,
        content: str,
        comment_type: Optional[str] = None,
        params: Optional[Dict] = None
    ) -> int:
        """Save a generated comment."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO generated_comments (doc_id, comment_type, params, content, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            doc_id,
            comment_type,
            json.dumps(params) if params else None,
            content,
            datetime.utcnow().isoformat()
        ))
        
        comment_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return comment_id
    
    def get_comments(self, doc_id: str) -> List[Dict[str, Any]]:
        """Get all generated comments for a document."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM generated_comments
            WHERE doc_id = ?
            ORDER BY created_at DESC
        """, (doc_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        results = []
        for row in rows:
            result = dict(row)
            if result.get("params"):
                result["params"] = json.loads(result["params"])
            results.append(result)
        
        return results

    # User selections persistence methods
    def save_user_selections(
        self,
        doc_id: str,
        selections: Dict[str, Any],
        comment_params: Optional[Dict] = None,
        custom_instructions: Optional[str] = None
    ) -> None:
        """Save user's content selections for a document."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO user_selections 
            (doc_id, selected_sections, selected_tables, selected_charts, 
             selected_companies, selected_metrics, selected_themes,
             comment_params, custom_instructions, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            doc_id,
            json.dumps(selections.get("selected_sections", [])),
            json.dumps(selections.get("selected_tables", [])),
            json.dumps(selections.get("selected_charts", [])),
            json.dumps(selections.get("selected_companies", [])),
            json.dumps(selections.get("selected_metrics", [])),
            json.dumps(selections.get("selected_themes", [])),
            json.dumps(comment_params) if comment_params else None,
            custom_instructions,
            datetime.utcnow().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def get_user_selections(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get saved user selections for a document."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM user_selections WHERE doc_id = ?", (doc_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            result = {
                "doc_id": row["doc_id"],
                "selected_sections": json.loads(row["selected_sections"]) if row["selected_sections"] else [],
                "selected_tables": json.loads(row["selected_tables"]) if row["selected_tables"] else [],
                "selected_charts": json.loads(row["selected_charts"]) if row["selected_charts"] else [],
                "selected_companies": json.loads(row["selected_companies"]) if row["selected_companies"] else [],
                "selected_metrics": json.loads(row["selected_metrics"]) if row["selected_metrics"] else [],
                "selected_themes": json.loads(row["selected_themes"]) if row["selected_themes"] else [],
                "comment_params": json.loads(row["comment_params"]) if row["comment_params"] else None,
                "custom_instructions": row["custom_instructions"],
                "updated_at": row["updated_at"]
            }
            return result
        return None
    
    def delete_user_selections(self, doc_id: str) -> None:
        """Delete user selections for a document."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_selections WHERE doc_id = ?", (doc_id,))
        conn.commit()
        conn.close()
