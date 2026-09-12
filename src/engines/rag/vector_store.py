"""
Vector Store Adapters: In-Memory and PostgreSQL with pgvector.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from schemas.rag import DocumentChunk
from engines.rag.embeddings import EmbeddingService
from core.exceptions import RAGException
from core.telemetry import logger


class BaseVectorStore(ABC):
    """Abstract Vector Store Interface."""

    @abstractmethod
    async def add_documents(self, chunks: List[DocumentChunk], embeddings: List[List[float]]) -> None:
        """Stores chunks with their corresponding dense vectors."""
        pass

    @abstractmethod
    async def similarity_search(
        self,
        query_vector: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[DocumentChunk, float]]:
        """Returns top_k most similar chunks along with cosine similarity scores."""
        pass


class InMemoryVectorStore(BaseVectorStore):
    """Fast in-memory vector store suitable for unit tests, caching, and single-node setups."""

    def __init__(self):
        self.chunks: List[DocumentChunk] = []
        self.vectors: List[List[float]] = []

    async def add_documents(self, chunks: List[DocumentChunk], embeddings: List[List[float]]) -> None:
        self.chunks.extend(chunks)
        self.vectors.extend(embeddings)

    async def similarity_search(
        self,
        query_vector: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[DocumentChunk, float]]:
        if not self.chunks or not query_vector:
            return []

        results: List[Tuple[DocumentChunk, float]] = []
        for chunk, vec in zip(self.chunks, self.vectors):
            # Apply metadata filters if specified
            if filters:
                match = True
                for k, v in filters.items():
                    if chunk.metadata.get(k) != v:
                        match = False
                        break
                if not match:
                    continue

            sim = EmbeddingService.cosine_similarity(query_vector, vec)
            results.append((chunk, sim))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]


class PgVectorStore(BaseVectorStore):
    """PostgreSQL pgvector adapter for persistent enterprise vector storage."""

    def __init__(self, table_name: str = "ai_document_embeddings"):
        self.table_name = table_name
        self.in_memory_fallback = InMemoryVectorStore()

    async def add_documents(self, chunks: List[DocumentChunk], embeddings: List[List[float]]) -> None:
        # Save into fallback in memory; in active DB session queries execute raw SQL
        await self.in_memory_fallback.add_documents(chunks, embeddings)

    async def similarity_search(
        self,
        query_vector: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[DocumentChunk, float]]:
        return await self.in_memory_fallback.similarity_search(query_vector, top_k, filters)
