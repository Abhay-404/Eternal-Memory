from google import genai
from typing import List, Optional
from src.utils.config import Config

class EmbeddingGenerator:
    """Generate embeddings using Gemini"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or Config.GEMINI_API_KEY
        if not self.api_key:
            raise ValueError("Gemini API key not found")

        self.client = genai.Client(api_key=self.api_key)

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text

        Args:
            text: Input text

        Returns:
            Embedding vector
        """
        try:
            result = self.client.models.embed_content(
                model=Config.EMBEDDING_MODEL,
                contents=text
            )
            return result.embeddings[0].values

        except Exception as e:
            raise Exception(f"Embedding generation error: {str(e)}")

    def generate_query_embedding(self, query: str) -> List[float]:
        """
        Generate embedding for a query

        Args:
            query: Search query

        Returns:
            Query embedding vector
        """
        try:
            result = self.client.models.embed_content(
                model=Config.EMBEDDING_MODEL,
                contents=query
            )
            return result.embeddings[0].values

        except Exception as e:
            raise Exception(f"Query embedding generation error: {str(e)}")

    def generate_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts

        Args:
            texts: List of input texts

        Returns:
            List of embedding vectors
        """
        try:
            result = self.client.models.embed_content(
                model=Config.EMBEDDING_MODEL,
                contents=texts
            )
            return [emb.values for emb in result.embeddings]

        except Exception as e:
            raise Exception(f"Batch embedding generation error: {str(e)}")
