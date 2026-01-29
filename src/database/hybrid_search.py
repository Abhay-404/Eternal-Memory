"""
Hybrid Search: BM25 + Vector Search
Combines keyword-based and semantic search for better retrieval
"""

from typing import List, Dict, Any, Optional
from rank_bm25 import BM25Okapi
from src.database.chroma_db import ChromaVectorStore
from src.core.embeddings import EmbeddingGenerator


class HybridSearchEngine:
    """
    Hybrid search combining BM25 (keyword) and vector (semantic) search
    """

    def __init__(self, vector_store: ChromaVectorStore, embedding_gen: EmbeddingGenerator):
        self.vector_store = vector_store
        self.embedding_gen = embedding_gen
        self.bm25 = None
        self.documents = []
        self.doc_metadata = []
        self._rebuild_bm25_index()

    def _rebuild_bm25_index(self):
        """Rebuild BM25 index from all documents in vector store"""
        try:
            # Get all documents from ChromaDB
            all_docs = self.vector_store.collection.get()

            if all_docs['ids']:
                self.documents = all_docs['documents']
                self.doc_metadata = [
                    {
                        'id': all_docs['ids'][i],
                        'metadata': all_docs['metadatas'][i]
                    }
                    for i in range(len(all_docs['ids']))
                ]

                # Tokenize for BM25
                tokenized_docs = [doc.lower().split() for doc in self.documents]
                self.bm25 = BM25Okapi(tokenized_docs)
            else:
                self.documents = []
                self.doc_metadata = []
                self.bm25 = None

        except Exception as e:
            print(f"Warning: Could not rebuild BM25 index: {e}")
            self.bm25 = None

    def search(
        self,
        query: str,
        limit: int = 5,
        vector_weight: float = 0.7,
        bm25_weight: float = 0.3,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search combining BM25 and vector search

        Args:
            query: Search query
            limit: Number of results
            vector_weight: Weight for vector search (0-1)
            bm25_weight: Weight for BM25 search (0-1)
            filter: Optional metadata filter

        Returns:
            List of results with text, metadata, and combined score
        """
        # Rebuild BM25 if documents have been added
        current_count = self.vector_store.count()
        if current_count != len(self.documents):
            self._rebuild_bm25_index()

        results = {}

        # 1. Vector search (semantic)
        query_embedding = self.embedding_gen.generate_query_embedding(query)
        vector_results = self.vector_store.search(
            query_embedding=query_embedding,
            limit=limit * 2,  # Get more candidates
            filter=filter
        )

        # Add vector results with weighted score
        for result in vector_results:
            doc_id = result['id']
            # ChromaDB returns distance (lower is better), convert to similarity
            similarity = 1 / (1 + result.get('distance', 0))
            results[doc_id] = {
                'id': doc_id,
                'text': result['text'],
                'metadata': result['metadata'],
                'vector_score': similarity,
                'bm25_score': 0.0,
                'combined_score': 0.0
            }

        # 2. BM25 search (keyword)
        if self.bm25 and self.documents:
            tokenized_query = query.lower().split()
            bm25_scores = self.bm25.get_scores(tokenized_query)

            # Get top BM25 results
            top_bm25_indices = sorted(
                range(len(bm25_scores)),
                key=lambda i: bm25_scores[i],
                reverse=True
            )[:limit * 2]

            for idx in top_bm25_indices:
                doc_id = self.doc_metadata[idx]['id']

                # Normalize BM25 score (0-1)
                max_bm25 = max(bm25_scores) if max(bm25_scores) > 0 else 1
                normalized_bm25 = bm25_scores[idx] / max_bm25

                if doc_id in results:
                    results[doc_id]['bm25_score'] = normalized_bm25
                else:
                    results[doc_id] = {
                        'id': doc_id,
                        'text': self.documents[idx],
                        'metadata': self.doc_metadata[idx]['metadata'],
                        'vector_score': 0.0,
                        'bm25_score': normalized_bm25,
                        'combined_score': 0.0
                    }

        # 3. Combine scores
        for doc_id in results:
            results[doc_id]['combined_score'] = (
                vector_weight * results[doc_id]['vector_score'] +
                bm25_weight * results[doc_id]['bm25_score']
            )

        # 4. Sort by combined score and return top results
        sorted_results = sorted(
            results.values(),
            key=lambda x: x['combined_score'],
            reverse=True
        )[:limit]

        return sorted_results

    def add_documents(
        self,
        texts: List[str],
        embeddings: List[List[float]],
        metadata: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Add documents to both vector store and BM25 index

        Args:
            texts: Document texts
            embeddings: Document embeddings
            metadata: Document metadata

        Returns:
            List of document IDs
        """
        # Add to vector store
        doc_ids = self.vector_store.add_documents(texts, embeddings, metadata)

        # Rebuild BM25 index
        self._rebuild_bm25_index()

        return doc_ids
