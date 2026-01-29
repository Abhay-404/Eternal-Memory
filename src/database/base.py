from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime

class VectorStoreBase(ABC):
    """Abstract base class for vector database operations"""

    @abstractmethod
    def add_documents(
        self,
        texts: List[str],
        embeddings: List[List[float]],
        metadata: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Add documents to the vector store

        Args:
            texts: List of text documents
            embeddings: List of embedding vectors
            metadata: List of metadata dicts for each document

        Returns:
            List of document IDs
        """
        pass

    @abstractmethod
    def search(
        self,
        query_embedding: List[float],
        limit: int = 5,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents

        Args:
            query_embedding: Query embedding vector
            limit: Number of results to return
            filter: Optional metadata filter

        Returns:
            List of results with text, metadata, and similarity score
        """
        pass

    @abstractmethod
    def delete_documents(self, ids: List[str]) -> None:
        """Delete documents by IDs"""
        pass

    @abstractmethod
    def update_metadata(self, doc_id: str, metadata: Dict[str, Any]) -> None:
        """Update metadata for a document"""
        pass

    @abstractmethod
    def get_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get documents within a date range"""
        pass
