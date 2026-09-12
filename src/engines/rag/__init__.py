"""
Hybrid RAG & Knowledge Retrieval Module.
Combines Dense Vector Search (BGE-M3), Sparse BM25 Keyword Search, and Reranking.
"""

from engines.rag.chunker import DocumentChunker
from engines.rag.embeddings import EmbeddingService
from engines.rag.bm25_retriever import BM25Retriever
from engines.rag.reranker import RerankerService
from engines.rag.vector_store import BaseVectorStore, InMemoryVectorStore, PgVectorStore
from engines.rag.pipeline import HybridRAGPipeline

__all__ = [
    "DocumentChunker",
    "EmbeddingService",
    "BM25Retriever",
    "RerankerService",
    "BaseVectorStore",
    "InMemoryVectorStore",
    "PgVectorStore",
    "HybridRAGPipeline",
]
