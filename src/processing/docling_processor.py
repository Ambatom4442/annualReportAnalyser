"""
Document processing with optional Docling support.
Falls back to basic extractors if Docling is not installed.
"""
from typing import Dict, Any, List, Optional
from pathlib import Path
import tempfile
import os

# Try to import Docling - it's optional
try:
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    DOCLING_AVAILABLE = True
except ImportError:
    DOCLING_AVAILABLE = False


class DoclingProcessor:
    """Process PDF documents using Docling for advanced extraction."""
    
    def __init__(self):
        self._converter = None
        if DOCLING_AVAILABLE:
            try:
                # Configure pipeline options for financial documents
                pipeline_options = PdfPipelineOptions()
                pipeline_options.do_ocr = False  # Enable if dealing with scanned documents
                pipeline_options.do_table_structure = True  # Important for financial reports
                
                self._converter = DocumentConverter(
                    format_options={
                        ".pdf": PdfFormatOption(pipeline_options=pipeline_options)
                    }
                )
            except Exception as e:
                print(f"Warning: Could not initialize Docling: {e}")
                self._converter = None
    
    @property
    def is_available(self) -> bool:
        """Check if Docling is available."""
        return self._converter is not None
    
    @property
    def converter(self):
        return self._converter
    
    def process_document(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """
        Process a PDF document and extract structured content.
        
        Returns:
            Dict with extracted content including text, tables, images, structure
            Includes '_docling_document' for HybridChunker access
        """
        if not self.is_available:
            return {
                "text": "",
                "tables": [],
                "sections": [],
                "metadata": {},
                "markdown": "",
                "page_count": 0,
                "error": "Docling not available",
                "_docling_document": None
            }
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name
        
        try:
            # Convert document
            result = self._converter.convert(tmp_path)
            doc = result.document
            
            # Get page count safely (new API uses num_pages property)
            page_count = 0
            try:
                if hasattr(doc, 'num_pages'):
                    page_count = doc.num_pages
                elif hasattr(doc, 'pages'):
                    page_count = len(list(doc.pages)) if hasattr(doc.pages, '__iter__') else 0
            except Exception:
                pass
            
            # Extract content
            extracted = {
                "text": self._extract_text(doc),
                "tables": self._extract_tables(doc),
                "sections": self._extract_sections(doc),
                "metadata": self._extract_metadata(doc),
                "markdown": doc.export_to_markdown(),
                "page_count": page_count,
                # Include the DoclingDocument for HybridChunker
                "_docling_document": doc
            }
            
            return extracted
            
        finally:
            # Cleanup
            try:
                os.unlink(tmp_path)
            except:
                pass
    
    def _extract_text(self, doc) -> str:
        """Extract full text content."""
        return doc.export_to_markdown()
    
    def _extract_tables(self, doc) -> List[Dict[str, Any]]:
        """Extract tables with structure."""
        tables = []
        
        for i, table in enumerate(doc.tables):
            table_data = {
                "index": i,
                "page": getattr(table, 'page_no', None),
                "headers": [],
                "rows": [],
                "markdown": ""
            }
            
            # Get markdown export (new API requires doc argument)
            try:
                if hasattr(table, 'export_to_markdown'):
                    table_data["markdown"] = table.export_to_markdown(doc=doc)
            except Exception:
                table_data["markdown"] = str(table)
            
            # Try to extract structured data from grid
            try:
                if hasattr(table, 'data') and hasattr(table.data, 'grid'):
                    grid = table.data.grid
                    if grid and len(grid) > 0:
                        # First row as headers
                        table_data["headers"] = [cell.text if hasattr(cell, 'text') else str(cell) for cell in grid[0]]
                        # Remaining rows as data
                        table_data["rows"] = [
                            [cell.text if hasattr(cell, 'text') else str(cell) for cell in row]
                            for row in grid[1:]
                        ]
            except Exception as e:
                # Fall back to empty if extraction fails
                pass
            
            tables.append(table_data)
        
        return tables
    
    def _extract_sections(self, doc) -> List[Dict[str, Any]]:
        """Extract document sections with headings."""
        sections = []
        
        try:
            # Iterate through document items
            current_section = None
            current_content = []
            
            for item in doc.iterate_items():
                # Handle tuple returns (index, item) from iterate_items
                if isinstance(item, tuple):
                    item = item[1] if len(item) > 1 else item[0]
                
                # Check for section headers
                item_label = getattr(item, 'label', None)
                if item_label and str(item_label) in ['section_header', 'title', 'heading', 'SectionHeaderItem', 'TitleItem']:
                    # Save previous section
                    if current_section:
                        sections.append({
                            "title": current_section,
                            "content": "\n".join(current_content)
                        })
                    
                    current_section = getattr(item, 'text', str(item))
                    current_content = []
                elif hasattr(item, 'text') and item.text:
                    current_content.append(item.text)
            
            # Save last section
            if current_section:
                sections.append({
                    "title": current_section,
                    "content": "\n".join(current_content)
                })
        except Exception as e:
            # Return empty sections if extraction fails
            pass
        
        return sections
    
    def _extract_metadata(self, doc) -> Dict[str, Any]:
        """Extract document metadata."""
        metadata = {}
        
        if hasattr(doc, 'metadata'):
            meta = doc.metadata
            if hasattr(meta, 'title'):
                metadata['title'] = meta.title
            if hasattr(meta, 'author'):
                metadata['author'] = meta.author
            if hasattr(meta, 'creation_date'):
                metadata['creation_date'] = str(meta.creation_date)
        
        return metadata
    
    def process_to_chunks(
        self, 
        pdf_bytes: bytes, 
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ) -> List[Dict[str, Any]]:
        """
        Process document and split into chunks for embedding.
        
        Returns:
            List of chunks with metadata
        """
        from .chunking import DocumentChunker
        
        # First extract content
        extracted = self.process_document(pdf_bytes)
        
        # Use chunker to split content
        chunker = DocumentChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        chunks = chunker.chunk_document(extracted)
        
        return chunks


# Fallback processor using existing extractors if Docling fails
class FallbackProcessor:
    """Fallback to original extractors if Docling is not available."""
    
    def __init__(self):
        from extractors.text_extractor import TextExtractor
        from extractors.table_extractor import TableExtractor
        from extractors.image_extractor import ImageExtractor
        from extractors.metadata_extractor import MetadataExtractor
        
        self.text_extractor = TextExtractor()
        self.table_extractor = TableExtractor()
        self.image_extractor = ImageExtractor()
        self.metadata_extractor = MetadataExtractor()
    
    def process_document(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """Process using fallback extractors."""
        # Text extraction
        text_result = self.text_extractor.extract_from_bytes(pdf_bytes)
        raw_text = text_result.get("full_text", "")
        
        # Table extraction
        tables = self.table_extractor.extract_from_bytes(pdf_bytes)
        
        # Metadata extraction
        metadata = self.metadata_extractor.extract_from_text(raw_text)
        
        # Format tables
        formatted_tables = []
        for table in tables:
            formatted_tables.append({
                "index": table.get("table_index", 0),
                "page": table.get("page", 0),
                "headers": table.get("headers", []),
                "rows": table.get("rows", []),
                "type": table.get("type", "unknown")
            })
        
        return {
            "text": raw_text,
            "tables": formatted_tables,
            "sections": text_result.get("pages", []),
            "metadata": metadata,
            "markdown": raw_text,
            "page_count": text_result.get("page_count", 0)
        }


def get_processor() -> DoclingProcessor:
    """Get the best available processor."""
    try:
        processor = DoclingProcessor()
        return processor
    except ImportError:
        print("Docling not available, using fallback processor")
        return FallbackProcessor()
