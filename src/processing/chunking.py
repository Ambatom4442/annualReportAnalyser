"""
Document chunking strategies for embedding and retrieval.
Uses Docling's HybridChunker for structure-aware, tokenization-aligned chunking.
"""
from typing import List, Dict, Any, Optional, Union
import re
import os
import warnings

# Suppress tokenizer warnings about sequence length
os.environ["TOKENIZERS_PARALLELISM"] = "false"
warnings.filterwarnings("ignore", message=".*Token indices sequence length.*")

# Try to import Docling chunking - it's the primary chunker
try:
    from docling.chunking import HybridChunker
    from docling_core.types.doc import DoclingDocument
    DOCLING_CHUNKING_AVAILABLE = True
except ImportError:
    DOCLING_CHUNKING_AVAILABLE = False
    HybridChunker = None
    DoclingDocument = None


class DocumentChunker:
    """
    Chunk documents for embedding and retrieval.
    
    Primary strategy: Docling HybridChunker (structure-aware, tokenization-aligned)
    Fallback: Simple character-based chunking
    """
    
    def __init__(
        self,
        chunk_size: int = 500,  # Reduced for better token alignment
        chunk_overlap: int = 100,
        tokenizer: str = "sentence-transformers/all-MiniLM-L6-v2",
        max_tokens: int = 512,
        separators: Optional[List[str]] = None
    ):
        """
        Initialize the chunker.
        
        Args:
            chunk_size: Target size for text chunks (used for fallback)
            chunk_overlap: Overlap between chunks (used for fallback)
            tokenizer: HuggingFace tokenizer for token-aware chunking
            max_tokens: Maximum tokens per chunk for HybridChunker
            separators: Custom separators for fallback splitting
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.tokenizer_name = tokenizer
        self.max_tokens = max_tokens
        self.separators = separators or ["\n\n", "\n", ". ", " ", ""]
        
        self._hybrid_chunker = None
        if DOCLING_CHUNKING_AVAILABLE:
            try:
                self._hybrid_chunker = HybridChunker(
                    tokenizer=tokenizer,
                    max_tokens=max_tokens,
                    merge_peers=True  # Merge small peer elements for better context
                )
            except Exception as e:
                print(f"Warning: Could not initialize HybridChunker: {e}")
                self._hybrid_chunker = None
    
    @property
    def is_hybrid_available(self) -> bool:
        """Check if HybridChunker is available."""
        return self._hybrid_chunker is not None
    
    def chunk_docling_document(
        self, 
        doc: Any,  # DoclingDocument
        include_metadata: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Chunk a Docling document using HybridChunker with contextualization.
        
        This is the preferred method when you have a Docling DoclingDocument.
        Uses structure-aware chunking with hierarchical context enrichment.
        
        Args:
            doc: A DoclingDocument from Docling processing
            include_metadata: Whether to include metadata in chunks
            
        Returns:
            List of chunks with content and metadata
        """
        if not self.is_hybrid_available:
            # Fallback: extract text and use simple chunking
            text = doc.export_to_markdown() if hasattr(doc, 'export_to_markdown') else str(doc)
            return self._fallback_chunk(text, include_metadata)
        
        chunks = []
        chunk_iter = self._hybrid_chunker.chunk(doc)
        
        for i, chunk in enumerate(chunk_iter):
            # Serialize chunk to get the text with hierarchical headings
            # contextualize() adds parent section headers for context
            serialized = self._hybrid_chunker.serialize(chunk)
            
            chunk_data = {
                "content": serialized,
                "type": "hybrid",
                "chunk_index": i,
            }
            
            if include_metadata:
                # Extract metadata from chunk
                chunk_data["metadata"] = {
                    "path": chunk.path if hasattr(chunk, 'path') else None,
                    "page": chunk.page_no if hasattr(chunk, 'page_no') else None,
                    "headings": chunk.headings if hasattr(chunk, 'headings') else [],
                    "captions": chunk.captions if hasattr(chunk, 'captions') else [],
                }
            
            chunks.append(chunk_data)
        
        return chunks
    
    def chunk_text(
        self, 
        text: str, 
        chunk_size: int = None, 
        overlap: int = None
    ) -> List[str]:
        """
        Chunk raw text into smaller pieces.
        
        For plain text without Docling document structure, uses character-based
        splitting as fallback since HybridChunker requires a DoclingDocument.
        
        Args:
            text: The text to chunk
            chunk_size: Override default chunk size
            overlap: Override default overlap
            
        Returns:
            List of text chunks (strings only, no metadata)
        """
        if chunk_size:
            self.chunk_size = chunk_size
        if overlap:
            self.chunk_overlap = overlap
        
        return self._chunk_text(text)
    
    def chunk_document(self, extracted: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Chunk extracted document content.
        
        If a DoclingDocument is available in the extracted data, uses HybridChunker.
        Otherwise falls back to simple text chunking.
        
        Args:
            extracted: Output from DoclingProcessor.process_document()
            
        Returns:
            List of chunks with metadata
        """
        # Check if we have a Docling document object for hybrid chunking
        docling_doc = extracted.get("_docling_document")
        
        if docling_doc and self.is_hybrid_available:
            return self.chunk_docling_document(docling_doc)
        
        # Fallback to text-based chunking
        chunks = []
        
        # Chunk main text content
        text = extracted.get("markdown", "") or extracted.get("text", "")
        if text:
            text_chunks = self._chunk_text(text)
            for i, chunk in enumerate(text_chunks):
                chunks.append({
                    "content": chunk,
                    "type": "text",
                    "chunk_index": i,
                    "total_chunks": len(text_chunks)
                })
        
        # Add tables as separate chunks (tables are usually important for financial docs)
        tables = extracted.get("tables", [])
        for i, table in enumerate(tables):
            table_content = self._format_table(table)
            if table_content:
                chunks.append({
                    "content": table_content,
                    "type": "table",
                    "table_index": i,
                    "page": table.get("page"),
                    "headers": table.get("headers", [])
                })
        
        # Add sections with clear headers
        sections = extracted.get("sections", [])
        for i, section in enumerate(sections):
            section_content = f"## {section.get('title', 'Section')}\n\n{section.get('content', '')}"
            if len(section_content) > self.chunk_size:
                # Chunk large sections
                section_chunks = self._chunk_text(section_content)
                for j, chunk in enumerate(section_chunks):
                    chunks.append({
                        "content": chunk,
                        "type": "section",
                        "section_title": section.get("title"),
                        "section_index": i,
                        "chunk_index": j
                    })
            else:
                chunks.append({
                    "content": section_content,
                    "type": "section",
                    "section_title": section.get("title"),
                    "section_index": i
                })
        
        return chunks
    
    def _fallback_chunk(self, text: str, include_metadata: bool = True) -> List[Dict[str, Any]]:
        """Fallback chunking when HybridChunker is not available."""
        chunks = []
        text_chunks = self._chunk_text(text)
        
        for i, chunk in enumerate(text_chunks):
            chunk_data = {
                "content": chunk,
                "type": "text_fallback",
                "chunk_index": i,
                "total_chunks": len(text_chunks)
            }
            if include_metadata:
                chunk_data["metadata"] = {
                    "chunker": "fallback",
                    "chunk_size": self.chunk_size,
                    "overlap": self.chunk_overlap
                }
            chunks.append(chunk_data)
        
        return chunks
    
    def _chunk_text(self, text: str) -> List[str]:
        """Split text into chunks using recursive character splitting."""
        if len(text) <= self.chunk_size:
            return [text] if text.strip() else []
        
        chunks = []
        current_chunk = ""
        
        # Split by separators hierarchically
        parts = self._split_by_separators(text, self.separators)
        
        for part in parts:
            if len(current_chunk) + len(part) <= self.chunk_size:
                current_chunk += part
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                
                # If single part is too large, force split
                if len(part) > self.chunk_size:
                    sub_chunks = self._force_split(part, self.chunk_size)
                    chunks.extend(sub_chunks[:-1])
                    current_chunk = sub_chunks[-1] if sub_chunks else ""
                else:
                    # Start new chunk with overlap from previous
                    if chunks and self.chunk_overlap > 0:
                        overlap_text = chunks[-1][-self.chunk_overlap:]
                        current_chunk = overlap_text + part
                    else:
                        current_chunk = part
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _split_by_separators(self, text: str, separators: List[str]) -> List[str]:
        """Split text by a list of separators, trying each in order."""
        if not separators:
            return [text]
        
        separator = separators[0]
        remaining_separators = separators[1:]
        
        if separator == "":
            # Character-level split as last resort
            return list(text)
        
        parts = text.split(separator)
        
        # Re-add separator to maintain context
        result = []
        for i, part in enumerate(parts):
            if i > 0:
                result.append(separator + part)
            else:
                result.append(part)
        
        return result
    
    def _force_split(self, text: str, max_length: int) -> List[str]:
        """Force split text that exceeds max length."""
        chunks = []
        step = max(1, max_length - self.chunk_overlap)  # Ensure step is at least 1
        for i in range(0, len(text), step):
            chunk = text[i:i + max_length]
            if chunk.strip():
                chunks.append(chunk.strip())
        return chunks
    
    def _format_table(self, table: Dict[str, Any]) -> str:
        """Format a table for embedding."""
        parts = []
        
        # Add headers
        headers = table.get("headers", [])
        if headers:
            parts.append("Table Headers: " + " | ".join(str(h) for h in headers))
        
        # Add rows
        rows = table.get("rows", [])
        for row in rows[:20]:  # Limit rows
            parts.append(" | ".join(str(cell) for cell in row))
        
        # Use markdown if available
        if table.get("markdown"):
            return table["markdown"]
        
        return "\n".join(parts) if parts else ""


class HybridDocumentChunker(DocumentChunker):
    """
    Specialized chunker that prioritizes Docling's HybridChunker.
    
    Features:
    - Structure-aware chunking respecting document hierarchy
    - Tokenizer-aligned boundaries for optimal embedding
    - Contextual enrichment with section headers
    - Automatic handling of tables and figures
    """
    
    def __init__(
        self,
        tokenizer: str = "sentence-transformers/all-MiniLM-L6-v2",
        max_tokens: int = 512,
        merge_peers: bool = True,
        include_captions: bool = True
    ):
        """
        Initialize HybridDocumentChunker.
        
        Args:
            tokenizer: HuggingFace tokenizer name for token counting
            max_tokens: Maximum tokens per chunk
            merge_peers: Whether to merge small peer elements
            include_captions: Whether to include figure/table captions
        """
        super().__init__(
            chunk_size=1000,  # Fallback only
            chunk_overlap=200,  # Fallback only
            tokenizer=tokenizer,
            max_tokens=max_tokens
        )
        self.merge_peers = merge_peers
        self.include_captions = include_captions
        
        # Reinitialize with full options if available
        if DOCLING_CHUNKING_AVAILABLE:
            try:
                self._hybrid_chunker = HybridChunker(
                    tokenizer=tokenizer,
                    max_tokens=max_tokens,
                    merge_peers=merge_peers
                )
            except Exception as e:
                print(f"Warning: Could not initialize HybridChunker with options: {e}")


# Convenience function for simple usage
def chunk_document(
    doc: Union[Dict[str, Any], Any],
    max_tokens: int = 512,
    tokenizer: str = "sentence-transformers/all-MiniLM-L6-v2"
) -> List[Dict[str, Any]]:
    """
    Convenience function to chunk a document.
    
    Args:
        doc: Either a DoclingDocument or dict from DoclingProcessor
        max_tokens: Maximum tokens per chunk
        tokenizer: HuggingFace tokenizer name
        
    Returns:
        List of chunks with content and metadata
    """
    chunker = HybridDocumentChunker(
        tokenizer=tokenizer,
        max_tokens=max_tokens
    )
    
    # Check if it's a DoclingDocument
    if DOCLING_CHUNKING_AVAILABLE and DoclingDocument and isinstance(doc, DoclingDocument):
        return chunker.chunk_docling_document(doc)
    
    # Otherwise treat as extracted dict
    if isinstance(doc, dict):
        return chunker.chunk_document(doc)
    
    # Last resort: convert to string
    return chunker._fallback_chunk(str(doc))
