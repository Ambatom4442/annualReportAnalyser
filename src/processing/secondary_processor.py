"""
Processor for secondary sources - handles files, URLs, and prepares for embedding.
"""
import os
import uuid
import tempfile
import requests
import warnings
import logging
from typing import Optional, Tuple, List
from pathlib import Path
from datetime import datetime

# Suppress Docling/HuggingFace warnings about token length
warnings.filterwarnings("ignore", message="Token indices sequence length")
logging.getLogger("transformers").setLevel(logging.ERROR)

from models.secondary_source import SecondarySource, SourceType


class SecondarySourceProcessor:
    """
    Processes secondary sources (files, URLs) into markdown for embedding.
    Uses Docling for document conversion.
    """
    
    def __init__(self, vector_store=None, secondary_store=None):
        """Initialize the processor."""
        self.vector_store = vector_store
        self.secondary_store = secondary_store
        self._docling_converter = None
    
    @property
    def docling_converter(self):
        """Lazy load Docling converter."""
        if self._docling_converter is None:
            try:
                from docling.document_converter import DocumentConverter
                self._docling_converter = DocumentConverter()
            except ImportError:
                print("Warning: Docling not available for document conversion")
        return self._docling_converter
    
    def process_file(
        self,
        file_content: bytes,
        filename: str,
        parent_doc_id: str,
        session_id: Optional[str] = None,
        is_temporary: bool = True
    ) -> Tuple[Optional[SecondarySource], Optional[str]]:
        """
        Process an uploaded file into a secondary source.
        
        Returns:
            Tuple of (SecondarySource, error_message)
        """
        # Determine source type from extension
        ext = Path(filename).suffix.lower()
        source_type_map = {
            ".pdf": SourceType.PDF,
            ".docx": SourceType.DOCX,
            ".doc": SourceType.DOCX,
            ".txt": SourceType.TXT,
            ".csv": SourceType.CSV,
            ".md": SourceType.TXT,
        }
        source_type = source_type_map.get(ext, SourceType.TXT)
        
        # Generate source ID
        source_id = f"sec_{uuid.uuid4().hex[:12]}"
        
        # Create source object
        source = SecondarySource(
            source_id=source_id,
            parent_doc_id=parent_doc_id,
            source_type=source_type,
            name=filename,
            is_temporary=is_temporary,
            session_id=session_id,
            file_size=len(file_content),
            created_at=datetime.now()
        )
        
        try:
            # Convert to markdown based on type
            if source_type in [SourceType.PDF, SourceType.DOCX]:
                content_md = self._convert_with_docling(file_content, filename)
            elif source_type == SourceType.CSV:
                content_md = self._convert_csv(file_content)
            else:
                # Plain text
                content_md = file_content.decode("utf-8", errors="ignore")
            
            source.content_md = content_md
            source.is_processed = True
            
            # Store and embed
            if self.secondary_store:
                self.secondary_store.add(source)
            
            if self.vector_store and content_md:
                chunk_count = self._embed_content(source)
                source.chunk_count = chunk_count
                if self.secondary_store:
                    self.secondary_store.update(source)
            
            return source, None
            
        except Exception as e:
            source.error = str(e)
            source.is_processed = False
            if self.secondary_store:
                self.secondary_store.add(source)
            return source, str(e)
    
    def process_url(
        self,
        url: str,
        parent_doc_id: str,
        session_id: Optional[str] = None,
        is_temporary: bool = True
    ) -> Tuple[Optional[SecondarySource], Optional[str]]:
        """
        Process a URL into a secondary source.
        
        Returns:
            Tuple of (SecondarySource, error_message)
        """
        source_id = f"sec_{uuid.uuid4().hex[:12]}"
        
        # Create a display name from URL
        from urllib.parse import urlparse
        parsed = urlparse(url)
        name = f"{parsed.netloc}{parsed.path[:30]}..." if len(parsed.path) > 30 else f"{parsed.netloc}{parsed.path}"
        
        source = SecondarySource(
            source_id=source_id,
            parent_doc_id=parent_doc_id,
            source_type=SourceType.URL,
            name=name,
            original_url=url,
            is_temporary=is_temporary,
            session_id=session_id,
            created_at=datetime.now()
        )
        
        try:
            # Convert URL to markdown using Docling (same as files)
            content_md = self._convert_url_with_docling(url)
            
            source.content_md = content_md
            source.file_size = len(content_md.encode("utf-8"))
            source.is_processed = True
            
            # Store and embed
            if self.secondary_store:
                self.secondary_store.add(source)
            
            if self.vector_store and content_md:
                chunk_count = self._embed_content(source)
                source.chunk_count = chunk_count
                if self.secondary_store:
                    self.secondary_store.update(source)
            
            return source, None
            
        except Exception as e:
            source.error = str(e)
            source.is_processed = False
            if self.secondary_store:
                self.secondary_store.add(source)
            return source, str(e)
    
    def _convert_with_docling(self, file_content: bytes, filename: str) -> str:
        """Convert PDF/DOCX to markdown using Docling."""
        if not self.docling_converter:
            raise ImportError("Docling not available")
        
        # Save to temp file (Docling needs file path)
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as tmp:
            tmp.write(file_content)
            tmp_path = tmp.name
        
        try:
            result = self.docling_converter.convert(tmp_path)
            doc = result.document
            # export_to_markdown() - no arguments needed for simple export
            return doc.export_to_markdown()
        finally:
            os.unlink(tmp_path)
    
    def _convert_csv(self, file_content: bytes) -> str:
        """Convert CSV to markdown table."""
        import csv
        import io
        
        content = file_content.decode("utf-8", errors="ignore")
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)
        
        if not rows:
            return ""
        
        # Build markdown table
        md_lines = []
        
        # Header
        header = rows[0]
        md_lines.append("| " + " | ".join(header) + " |")
        md_lines.append("| " + " | ".join(["---"] * len(header)) + " |")
        
        # Data rows
        for row in rows[1:]:
            # Pad row if needed
            while len(row) < len(header):
                row.append("")
            md_lines.append("| " + " | ".join(row[:len(header)]) + " |")
        
        return "\n".join(md_lines)
    
    def _convert_url_with_playwright(self, url: str) -> str:
        """
        Convert URL to markdown using Playwright for JS-rendered content.
        
        Uses a subprocess to avoid event loop conflicts with Streamlit.
        """
        import subprocess
        import sys
        import json
        import tempfile
        import os
        
        try:
            import html2text
        except ImportError:
            raise ImportError("html2text is required for URL processing")
        
        # Create a temporary script to run Playwright in isolation
        script = '''
import sys
import json
from playwright.sync_api import sync_playwright

url = sys.argv[1]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    try:
        page.goto(url, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(2000)
        html = page.content()
        print(json.dumps({"html": html}))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
    finally:
        browser.close()
'''
        # Write script to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(script)
            script_path = f.name
        
        try:
            # Run in subprocess to completely isolate from Streamlit's event loop
            result = subprocess.run(
                [sys.executable, script_path, url],
                capture_output=True,
                text=True,
                timeout=90
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"Playwright subprocess failed: {result.stderr}")
            
            # Parse the JSON output
            output = json.loads(result.stdout.strip())
            
            if "error" in output:
                raise RuntimeError(output["error"])
            
            html_content = output["html"]
            
        finally:
            os.unlink(script_path)
        
        # Convert HTML to markdown
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = True
        h.ignore_emphasis = False
        h.body_width = 0  # No line wrapping
        
        markdown = h.handle(html_content)
        
        if markdown and len(markdown.strip()) > 100:
            return markdown.strip()
        
        raise ValueError(f"Could not extract meaningful content from URL: {url}")
    
    def _convert_url_with_docling(self, url: str) -> str:
        """
        Convert URL to markdown - tries Playwright first for dynamic content,
        falls back to Docling for static pages.
        """
        # Try Playwright first (handles JavaScript-rendered pages)
        try:
            return self._convert_url_with_playwright(url)
        except Exception as e:
            print(f"Playwright extraction failed: {e}, trying Docling...")
        
        # Fallback to Docling for static content
        if not self.docling_converter:
            raise ImportError("Docling converter not available")
        
        result = self.docling_converter.convert(url)
        if result and result.document:
            markdown = result.document.export_to_markdown()
            if markdown and len(markdown.strip()) > 0:
                return markdown
        
        raise ValueError(f"Could not extract content from URL: {url}")

    def _embed_content(self, source: SecondarySource) -> int:
        """Chunk and embed content into vector store."""
        if not self.vector_store or not source.content_md:
            return 0
        
        # Use chunking
        try:
            from processing.chunking import DocumentChunker
            chunker = DocumentChunker(chunk_size=500, chunk_overlap=50)
            # Use fallback chunking for plain text content
            chunks = chunker._fallback_chunk(source.content_md)
        except ImportError:
            # Simple chunking fallback
            content = source.content_md
            chunk_size = 500
            chunks = []
            for i in range(0, len(content), chunk_size):
                chunks.append({"content": content[i:i+chunk_size], "metadata": {}})
        
        # Prepare chunks and metadata for vector store
        chunk_texts = []
        chunk_metadatas = []
        
        for i, chunk in enumerate(chunks):
            chunk_content = chunk.get("content", chunk) if isinstance(chunk, dict) else str(chunk)
            chunk_texts.append(chunk_content)
            
            chunk_metadatas.append({
                "doc_id": source.parent_doc_id,
                "source_id": source.source_id,
                "source_type": "secondary",
                "source_name": source.name,
                "chunk_index": i,
                "original_url": source.original_url or "",
            })
        
        # Add all chunks at once to vector store
        if chunk_texts:
            self.vector_store.add_document(
                doc_id=source.source_id,
                chunks=chunk_texts,
                metadatas=chunk_metadatas
            )
        
        return len(chunks)
    
    def delete_source(self, source_id: str) -> bool:
        """Delete a secondary source and its embeddings."""
        # Delete from vector store
        if self.vector_store:
            try:
                # Get all chunks for this source
                self.vector_store.collection.delete(
                    where={"source_id": source_id}
                )
            except Exception as e:
                print(f"Error deleting embeddings: {e}")
        
        # Delete from store
        if self.secondary_store:
            return self.secondary_store.delete(source_id)
        
        return True
