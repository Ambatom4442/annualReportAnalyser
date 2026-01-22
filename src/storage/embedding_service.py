"""
Embedding service using Google Gemini embeddings.
"""
from typing import List, Optional
import google.generativeai as genai


class EmbeddingService:
    """Generate embeddings using Gemini embedding model."""
    
    def __init__(self, api_key: str, model_name: str = "text-embedding-004"):
        self.api_key = api_key
        self.model_name = f"models/{model_name}" if not model_name.startswith("models/") else model_name
        genai.configure(api_key=api_key)
    
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        result = genai.embed_content(
            model=self.model_name,
            content=text
        )
        return result['embedding']
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        embeddings = []
        for text in texts:
            result = genai.embed_content(
                model=self.model_name,
                content=text
            )
            embeddings.append(result['embedding'])
        return embeddings
    
    def embed_document(self, text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> List[float]:
        """Generate embedding optimized for document storage."""
        result = genai.embed_content(
            model=self.model_name,
            content=text,
            task_type=task_type
        )
        return result['embedding']
    
    def embed_query(self, query: str) -> List[float]:
        """Generate embedding optimized for search queries."""
        result = genai.embed_content(
            model=self.model_name,
            content=query,
            task_type="RETRIEVAL_QUERY"
        )
        return result['embedding']


# LangChain compatible wrapper
class GeminiEmbeddings:
    """LangChain-compatible Gemini embeddings wrapper."""
    
    def __init__(self, api_key: str, model_name: str = "text-embedding-004"):
        self.service = EmbeddingService(api_key, model_name)
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents."""
        return self.service.embed_texts(texts)
    
    def embed_query(self, text: str) -> List[float]:
        """Embed a query for search."""
        return self.service.embed_query(text)
