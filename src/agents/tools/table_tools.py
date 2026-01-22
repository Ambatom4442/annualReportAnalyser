"""
Table query tools for structured data retrieval.
"""
from typing import Optional, List, Type
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field


class TableQueryInput(BaseModel):
    """Input for table query tool."""
    table_type: str = Field(
        description="Type of table to query: 'holdings', 'performance', 'sector_allocation', 'risk_metrics', or 'all'"
    )
    doc_id: Optional[str] = Field(default=None, description="Optional document ID to filter tables")
    query: Optional[str] = Field(default=None, description="Optional query to filter table contents")


class TableQueryTool(BaseTool):
    """Tool for querying structured table data."""
    
    name: str = "query_tables"
    description: str = """Query structured table data from annual reports.
    Use this to get specific data like:
    - Holdings: Top holdings, company names, weights, contributions
    - Performance: Fund returns, benchmark comparisons, time periods
    - Sector allocation: Sector weights, geographic allocation
    - Risk metrics: Volatility, Sharpe ratio, drawdowns
    
    Returns formatted table data matching your query."""
    args_schema: Type[BaseModel] = TableQueryInput
    
    vector_store: any = None
    document_store: any = None
    
    def __init__(self, vector_store, document_store):
        super().__init__()
        self.vector_store = vector_store
        self.document_store = document_store
    
    def _run(
        self, 
        table_type: str, 
        doc_id: Optional[str] = None,
        query: Optional[str] = None
    ) -> str:
        """Query tables."""
        # Search for table chunks
        search_query = f"{table_type} table data"
        if query:
            search_query = f"{table_type}: {query}"
        
        results = self.vector_store.search(
            query=search_query,
            n_results=10,
            filter_doc_id=doc_id
        )
        
        # Filter for table type
        table_chunks = []
        for result in results:
            metadata = result.get("metadata", {})
            chunk_type = metadata.get("type", "")
            
            if chunk_type == "table":
                # Check if table matches requested type
                content_lower = result["content"].lower()
                headers = metadata.get("headers", [])
                headers_str = " ".join(str(h).lower() for h in headers)
                
                if table_type == "all":
                    table_chunks.append(result)
                elif table_type == "holdings" and any(
                    kw in headers_str or kw in content_lower 
                    for kw in ["holding", "company", "stock", "weight", "portfolio"]
                ):
                    table_chunks.append(result)
                elif table_type == "performance" and any(
                    kw in headers_str or kw in content_lower 
                    for kw in ["return", "performance", "ytd", "benchmark"]
                ):
                    table_chunks.append(result)
                elif table_type == "sector_allocation" and any(
                    kw in headers_str or kw in content_lower 
                    for kw in ["sector", "industry", "allocation"]
                ):
                    table_chunks.append(result)
                elif table_type == "risk_metrics" and any(
                    kw in headers_str or kw in content_lower 
                    for kw in ["risk", "volatility", "sharpe", "drawdown"]
                ):
                    table_chunks.append(result)
        
        if not table_chunks:
            return f"No {table_type} tables found."
        
        # Format results
        formatted = [f"Found {len(table_chunks)} {table_type} table(s):\n"]
        
        for i, chunk in enumerate(table_chunks[:5], 1):
            metadata = chunk.get("metadata", {})
            source = metadata.get("doc_id", "Unknown")
            page = metadata.get("page", "?")
            
            formatted.append(f"\n[Table {i}] (Source: {source}, Page: {page})")
            formatted.append(chunk["content"])
        
        return "\n".join(formatted)
    
    async def _arun(
        self, 
        table_type: str, 
        doc_id: Optional[str] = None,
        query: Optional[str] = None
    ) -> str:
        """Async execution."""
        return self._run(table_type, doc_id, query)


class CompareDocumentsInput(BaseModel):
    """Input for document comparison tool."""
    doc_ids: List[str] = Field(description="List of document IDs to compare")
    metric: str = Field(description="Metric to compare: 'performance', 'holdings', 'sectors'")


class CompareDocumentsTool(BaseTool):
    """Tool for comparing data across multiple documents."""
    
    name: str = "compare_documents"
    description: str = """Compare specific metrics across multiple annual reports.
    Use this to compare:
    - Performance: Returns across different funds or periods
    - Holdings: Portfolio composition differences
    - Sectors: Allocation changes over time
    
    Provide document IDs and the metric to compare."""
    args_schema: Type[BaseModel] = CompareDocumentsInput
    
    vector_store: any = None
    document_store: any = None
    
    def __init__(self, vector_store, document_store):
        super().__init__()
        self.vector_store = vector_store
        self.document_store = document_store
    
    def _run(self, doc_ids: List[str], metric: str) -> str:
        """Compare documents."""
        comparisons = []
        
        for doc_id in doc_ids[:5]:  # Limit to 5 documents
            doc_info = self.document_store.get_document(doc_id)
            if not doc_info:
                continue
            
            # Get relevant data
            results = self.vector_store.search(
                query=f"{metric} data",
                n_results=3,
                filter_doc_id=doc_id
            )
            
            doc_data = {
                "doc_id": doc_id,
                "fund_name": doc_info.get("fund_name", "Unknown"),
                "period": doc_info.get("report_period", "Unknown"),
                "data": "\n".join(r["content"][:500] for r in results)
            }
            comparisons.append(doc_data)
        
        if not comparisons:
            return "No documents found for comparison."
        
        # Format comparison
        output = [f"Comparison of {metric} across {len(comparisons)} documents:\n"]
        
        for comp in comparisons:
            output.append(f"\n## {comp['fund_name']} ({comp['period']})")
            output.append(f"Document ID: {comp['doc_id']}")
            output.append(comp['data'][:1000])
            output.append("\n---")
        
        return "\n".join(output)
    
    async def _arun(self, doc_ids: List[str], metric: str) -> str:
        """Async execution."""
        return self._run(doc_ids, metric)


def create_table_query_tool(vector_store, document_store) -> TableQueryTool:
    """Create a table query tool."""
    return TableQueryTool(vector_store, document_store)


def create_compare_tool(vector_store, document_store) -> CompareDocumentsTool:
    """Create a document comparison tool."""
    return CompareDocumentsTool(vector_store, document_store)
