"""
RAG and Knowledge Retrieval Schemas.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from core.constants import VectorStoreType


class DocumentChunk(BaseModel):
    """A granular piece of indexed knowledge."""
    chunk_id: str = Field(description="Unique ID of the chunk")
    document_id: str = Field(description="Parent document ID")
    content: str = Field(description="Textual content of the chunk")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata tags (filename, page, author, etc.)")
    score: Optional[float] = Field(default=None, description="Similarity or rerank score")


class DocumentCreate(BaseModel):
    """Payload to ingest and index a document into Vector Store."""
    document_id: Optional[str] = Field(default=None, description="Optional custom document ID")
    title: str = Field(description="Document title or filename")
    content: str = Field(description="Raw text content of the document")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata attributes")
    chunk_size: int = Field(default=500, ge=50, le=2000, description="Chunk size in characters")
    chunk_overlap: int = Field(default=50, ge=0, le=500, description="Overlap between consecutive chunks")


class SearchQuery(BaseModel):
    """Query payload for Hybrid Retrieval."""
    query: str = Field(description="Search text or question in natural language")
    top_k: int = Field(default=5, ge=1, le=50, description="Number of results to retrieve")
    hybrid: bool = Field(default=True, description="Combine Dense Vector + BM25 Sparse Search")
    rerank: bool = Field(default=True, description="Apply Cross-Encoder Reranker")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Metadata filters (tenantId, tags...)")
    vector_store: VectorStoreType = Field(default=VectorStoreType.IN_MEMORY, description="Vector store target")


class SearchResult(BaseModel):
    """Search response holding matched knowledge chunks."""
    query: str
    results: List[DocumentChunk] = Field(default_factory=list)
    total_found: int = Field(default=0)


class RAGResponse(BaseModel):
    """End-to-end RAG answer synthesis."""
    query: str
    answer: str
    sources: List[DocumentChunk] = Field(default_factory=list)
    model: str
    provider: str
