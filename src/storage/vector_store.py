"""
Vector store using ChromaDB for persistent document embeddings.
"""
from typing import List, Dict, Any, Optional
from pathlib import Path
import chromadb
from chromadb.config import Settings

from .embedding_service import GeminiEmbeddings


class VectorStore:
    """ChromaDB-based vector store for document embeddings."""
    
    def __init__(
        self, 
        api_key: str,
        persist_directory: str = ".data/chromadb",
        collection_name: str = "annual_reports"
    ):
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB with persistence
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Initialize embedding function
        self.embeddings = GeminiEmbeddings(api_key)
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "Annual report document chunks"}
        )
    
    def add_document(
        self,
        doc_id: str,
        chunks: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """Add document chunks to the vector store."""
        if not chunks:
            return
        
        # Generate unique IDs for each chunk
        chunk_ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
        
        # Add metadata if not provided
        if metadatas is None:
            metadatas = [{"doc_id": doc_id, "chunk_index": i} for i in range(len(chunks))]
        else:
            # Only set doc_id if not already present (allows secondary sources to use parent_doc_id)
            for i, meta in enumerate(metadatas):
                if "doc_id" not in meta:
                    meta["doc_id"] = doc_id
                if "chunk_index" not in meta:
                    meta["chunk_index"] = i
        
        # Generate embeddings
        embeddings = self.embeddings.embed_documents(chunks)
        
        # Add to collection
        self.collection.add(
            ids=chunk_ids,
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadatas
        )
    
    def search(
        self,
        query: str,
        n_results: int = 5,
        filter_doc_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar documents."""
        # Generate query embedding
        query_embedding = self.embeddings.embed_query(query)
        
        # Build where filter
        where_filter = None
        if filter_doc_id:
            where_filter = {"doc_id": filter_doc_id}
        
        # Search
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )
        
        # Format results
        formatted = []
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                formatted.append({
                    "content": doc,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else 0
                })
        
        return formatted
    
    def search_by_doc_id(self, doc_id: str) -> List[Dict[str, Any]]:
        """Get all chunks for a specific document."""
        results = self.collection.get(
            where={"doc_id": doc_id},
            include=["documents", "metadatas"]
        )
        
        formatted = []
        if results["documents"]:
            for i, doc in enumerate(results["documents"]):
                formatted.append({
                    "content": doc,
                    "metadata": results["metadatas"][i] if results["metadatas"] else {}
                })
        
        return formatted
    
    def delete_document(self, doc_id: str) -> None:
        """Delete all chunks for a document."""
        # Get all chunk IDs for this document
        results = self.collection.get(
            where={"doc_id": doc_id},
            include=[]
        )
        
        if results["ids"]:
            self.collection.delete(ids=results["ids"])
    
    def document_exists(self, doc_id: str) -> bool:
        """Check if a document exists in the store."""
        results = self.collection.get(
            where={"doc_id": doc_id},
            limit=1,
            include=[]
        )
        return len(results["ids"]) > 0
    
    def list_documents(self) -> List[str]:
        """List all unique document IDs."""
        # Get all metadata
        results = self.collection.get(include=["metadatas"])
        
        # Extract unique doc_ids
        doc_ids = set()
        if results["metadatas"]:
            for meta in results["metadatas"]:
                if meta and "doc_id" in meta:
                    doc_ids.add(meta["doc_id"])
        
        return list(doc_ids)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store."""
        count = self.collection.count()
        doc_ids = self.list_documents()
        
        return {
            "total_chunks": count,
            "total_documents": len(doc_ids),
            "collection_name": self.collection.name
        }
