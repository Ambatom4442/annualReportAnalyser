"""
Search tools for document retrieval.
"""
from typing import Optional, Type
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field


class SearchInput(BaseModel):
    """Input for search tool."""
    query: str = Field(description="The search query to find relevant document sections")
    doc_id: Optional[str] = Field(default=None, description="Optional document ID to search within")
    skip: int = Field(default=0, description="Number of results to skip (for pagination). Use this to get more results by increasing skip by 5 each time.")


class DocumentSearchTool(BaseTool):
    """Tool for semantic search across documents."""
    
    name: str = "search_documents"
    description: str = """Search for relevant information across all uploaded annual reports.
    Use this to find specific data like performance figures, holdings information, 
    sector allocations, or any other content from the documents.
    Returns up to 5 text chunks per call. Use 'skip' parameter for pagination.
    
    IMPORTANT: If you receive exactly 10 results, there may be more relevant data.
    Call again with skip=10, then skip=20, etc. until you get fewer than 10 results."""
    args_schema: Type[BaseModel] = SearchInput
    
    vector_store: any = None
    
    def __init__(self, vector_store):
        super().__init__()
        self.vector_store = vector_store
    
    def _run(self, query: str, doc_id: Optional[str] = None, skip: int = 0) -> str:
        """Execute the search."""
        # IMPORTANT: Don't filter by doc_id by default - this excludes secondary sources!
        # Secondary sources have their own source_id but share parent_doc_id
        # Search ALL content to include attached URLs, files, etc.
        results = self.vector_store.search(
            query=query,
            n_results=10 + skip,
            filter_doc_id=None  # Always search all content, including secondary sources
        )
        
        # Apply skip (pagination)
        results = results[skip:skip + 10] if results else []
        
        if not results:
            return f"No more results found (skip={skip}). You have retrieved all relevant information."
        
        # Format results
        formatted = []
        for i, result in enumerate(results, 1):
            content = result["content"]
            metadata = result.get("metadata", {})
            source = metadata.get("doc_id", "Unknown")
            chunk_type = metadata.get("type", "text")
            source_type = metadata.get("source_type", "primary")
            
            formatted.append(f"[Result {i}] (Source: {source}, Type: {chunk_type}, SourceType: {source_type})\n{content}")
        
        # Add pagination hint - now with intelligent guidance
        result_text = "\n\n---\n\n".join(formatted)
        result_count = len(results)
        
        if result_count == 10:
            result_text += f"\n\n---\n📊 [INFO: Received {result_count} results. More may exist (skip={skip + 10}).]"
            result_text += f"\n💡 [DECISION: If these results SUFFICIENTLY answer the user's question, respond now. Otherwise, call search_documents with skip={skip + 10} for more results.]"
        else:
            result_text += f"\n\n---\n✅ [COMPLETE: {result_count} results. No more data available.]"
        
        return result_text
    
    async def _arun(self, query: str, doc_id: Optional[str] = None, skip: int = 0) -> str:
        """Async execution."""
        return self._run(query, doc_id, skip)


class DocumentRetrieverInput(BaseModel):
    """Input for document retriever tool."""
    doc_id: str = Field(description="The document ID to retrieve content from")
    section: Optional[str] = Field(default=None, description="Optional section name to retrieve")


class DocumentRetrieverTool(BaseTool):
    """Tool for retrieving all content from a specific document."""
    
    name: str = "get_document_content"
    description: str = """Retrieve all content from a specific document by its ID.
    Use this when you need comprehensive information from a particular annual report.
    You can optionally specify a section name to get only that section."""
    args_schema: Type[BaseModel] = DocumentRetrieverInput
    
    vector_store: any = None
    document_store: any = None
    
    def __init__(self, vector_store, document_store):
        super().__init__()
        self.vector_store = vector_store
        self.document_store = document_store
    
    def _run(self, doc_id: str, section: Optional[str] = None) -> str:
        """Retrieve document content."""
        # Get document metadata
        doc_info = self.document_store.get_document(doc_id)
        if not doc_info:
            return f"Document with ID '{doc_id}' not found."
        
        # Get all chunks for this document
        chunks = self.vector_store.search_by_doc_id(doc_id)
        
        if not chunks:
            return f"No content found for document '{doc_id}'."
        
        # Filter by section if specified
        if section:
            section_lower = section.lower()
            chunks = [
                c for c in chunks 
                if section_lower in str(c.get("metadata", {}).get("section_name", "")).lower()
                or section_lower in c.get("content", "").lower()[:200]
            ]
        
        # Format output
        header = f"Document: {doc_info.get('filename', doc_id)}\n"
        header += f"Fund: {doc_info.get('fund_name', 'Unknown')}\n"
        header += f"Period: {doc_info.get('report_period', 'Unknown')}\n"
        header += "---\n\n"
        
        content = "\n\n".join(c["content"] for c in chunks[:10])  # Limit chunks
        
        return header + content
    
    async def _arun(self, doc_id: str, section: Optional[str] = None) -> str:
        """Async execution."""
        return self._run(doc_id, section)


def create_search_tool(vector_store) -> DocumentSearchTool:
    """Create a document search tool."""
    return DocumentSearchTool(vector_store)


def create_document_retriever_tool(vector_store, document_store) -> DocumentRetrieverTool:
    """Create a document retriever tool."""
    return DocumentRetrieverTool(vector_store, document_store)
