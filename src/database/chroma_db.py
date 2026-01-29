import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
from datetime import datetime
from src.database.base import VectorStoreBase
from src.utils.config import Config
import uuid

class ChromaVectorStore(VectorStoreBase):
    """ChromaDB implementation of vector store"""

    def __init__(self, persist_directory: Optional[str] = None, collection_name: Optional[str] = None):
        self.persist_directory = persist_directory or Config.CHROMA_DB_PATH
        self.collection_name = collection_name or Config.COLLECTION_NAME

        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(path=self.persist_directory)

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "MY_BRAIN personal memory storage"}
        )

    def add_documents(
        self,
        texts: List[str],
        embeddings: List[List[float]],
        metadata: List[Dict[str, Any]]
    ) -> List[str]:
        """Add documents to ChromaDB"""
        try:
            # Generate IDs
            ids = [str(uuid.uuid4()) for _ in texts]

            # Convert datetime objects to strings in metadata
            processed_metadata = []
            for meta in metadata:
                processed_meta = {}
                for key, value in meta.items():
                    if isinstance(value, datetime):
                        processed_meta[key] = value.isoformat()
                    else:
                        processed_meta[key] = value
                processed_metadata.append(processed_meta)

            # Add to collection
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=processed_metadata
            )

            return ids

        except Exception as e:
            raise Exception(f"Error adding documents to ChromaDB: {str(e)}")

    def search(
        self,
        query_embedding: List[float],
        limit: int = 5,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar documents in ChromaDB"""
        try:
            where_filter = None
            if filter:
                # Convert filter to ChromaDB where clause
                where_filter = filter

            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where=where_filter
            )

            # Format results
            formatted_results = []
            if results['ids'] and results['ids'][0]:
                for i in range(len(results['ids'][0])):
                    formatted_results.append({
                        'id': results['ids'][0][i],
                        'text': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i],
                        'distance': results['distances'][0][i] if 'distances' in results else None
                    })

            return formatted_results

        except Exception as e:
            raise Exception(f"Error searching ChromaDB: {str(e)}")

    def delete_documents(self, ids: List[str]) -> None:
        """Delete documents from ChromaDB"""
        try:
            self.collection.delete(ids=ids)
        except Exception as e:
            raise Exception(f"Error deleting documents: {str(e)}")

    def update_metadata(self, doc_id: str, metadata: Dict[str, Any]) -> None:
        """Update metadata for a document"""
        try:
            # Convert datetime to string
            processed_metadata = {}
            for key, value in metadata.items():
                if isinstance(value, datetime):
                    processed_metadata[key] = value.isoformat()
                else:
                    processed_metadata[key] = value

            self.collection.update(
                ids=[doc_id],
                metadatas=[processed_metadata]
            )
        except Exception as e:
            raise Exception(f"Error updating metadata: {str(e)}")

    def get_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get documents within a date range"""
        try:
            # Query with date filter
            where_filter = {
                "$and": [
                    {"date": {"$gte": start_date.isoformat()}},
                    {"date": {"$lte": end_date.isoformat()}}
                ]
            }

            # Get all matching results (ChromaDB doesn't support limit in where clause)
            results = self.collection.get(
                where=where_filter,
                limit=limit if limit else 100000  # Large number if no limit specified
            )

            # Format results
            formatted_results = []
            if results['ids']:
                for i in range(len(results['ids'])):
                    formatted_results.append({
                        'id': results['ids'][i],
                        'text': results['documents'][i],
                        'metadata': results['metadatas'][i]
                    })

            return formatted_results[:limit] if limit else formatted_results

        except Exception as e:
            raise Exception(f"Error getting documents by date range: {str(e)}")

    def count(self) -> int:
        """Get total number of documents"""
        return self.collection.count()
