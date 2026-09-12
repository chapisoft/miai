"""
Hybrid RAG Pipeline.
Orchestrates: Chunking -> Embedding -> Hybrid Retrieval (Dense + BM25) -> Reranking -> Answer Synthesis.
"""

import uuid
from typing import List, Optional, Dict, Any
from schemas.rag import DocumentCreate, SearchQuery, SearchResult, DocumentChunk, RAGResponse
from schemas.chat import ChatRequest, ChatMessage
from core.constants import MessageRole, VectorStoreType, ModelProvider
from engines.rag.chunker import DocumentChunker
from engines.rag.embeddings import EmbeddingService
from engines.rag.bm25_retriever import BM25Retriever
from engines.rag.reranker import RerankerService
from engines.rag.vector_store import InMemoryVectorStore, PgVectorStore, BaseVectorStore
from engines.llm.factory import LLMFactory
from core.telemetry import logger


class HybridRAGPipeline:
    """Master Hybrid RAG pipeline."""

    def __init__(self, vector_store: Optional[BaseVectorStore] = None):
        self.vector_store = vector_store or InMemoryVectorStore()
        self.embedding_service = EmbeddingService()
        self.bm25_retriever = BM25Retriever()
        self.reranker = RerankerService()
        self.all_indexed_chunks: List[DocumentChunk] = []

    async def ingest_document(self, doc: DocumentCreate) -> List[DocumentChunk]:
        """Ingests, chunks, embeds and indexes a document."""
        doc_id = doc.document_id or f"doc_{uuid.uuid4().hex[:8]}"
        chunks = DocumentChunker.chunk_document(
            document_id=doc_id,
            content=doc.content,
            metadata=doc.metadata,
            chunk_size=doc.chunk_size,
            chunk_overlap=doc.chunk_overlap
        )

        texts = [c.content for c in chunks]
        embeddings = await self.embedding_service.get_batch_embeddings(texts)
        await self.vector_store.add_documents(chunks, embeddings)

        self.all_indexed_chunks.extend(chunks)
        self.bm25_retriever.index_documents(self.all_indexed_chunks)

        logger.info(
            "Ingested document into RAG store",
            extra={"document_id": doc_id, "title": doc.title, "chunk_count": len(chunks)}
        )
        return chunks

    async def search(self, query: SearchQuery) -> SearchResult:
        """Executes Hybrid Search combining Dense Vector and BM25 Sparse matching."""
        candidates_map: Dict[str, DocumentChunk] = {}

        # 1. Dense Semantic Search
        query_vec = await self.embedding_service.get_embedding(query.query)
        dense_results = await self.vector_store.similarity_search(
            query_vector=query_vec,
            top_k=query.top_k * 2,
            filters=query.filters
        )
        for chunk, score in dense_results:
            chunk_copy = chunk.model_copy()
            chunk_copy.score = float(score)
            candidates_map[chunk.chunk_id] = chunk_copy

        # 2. Sparse Lexical Search (BM25) if enabled
        if query.hybrid:
            sparse_results = self.bm25_retriever.search(query.query, top_k=query.top_k * 2)
            for chunk, score in sparse_results:
                if chunk.chunk_id in candidates_map:
                    # Combine score (Reciprocal Rank Fusion or weighted sum)
                    candidates_map[chunk.chunk_id].score = (candidates_map[chunk.chunk_id].score or 0.0) + (score * 0.2)
                else:
                    chunk_copy = chunk.model_copy()
                    chunk_copy.score = float(score * 0.2)
                    candidates_map[chunk.chunk_id] = chunk_copy

        candidates = list(candidates_map.values())

        # 3. Reranking Step
        if query.rerank and candidates:
            final_chunks = await self.reranker.rerank(query.query, candidates, top_k=query.top_k)
        else:
            candidates.sort(key=lambda x: x.score or 0.0, reverse=True)
            final_chunks = candidates[:query.top_k]

        return SearchResult(
            query=query.query,
            results=final_chunks,
            total_found=len(final_chunks)
        )

    async def answer(
        self,
        query: str,
        top_k: int = 4,
        provider: Optional[ModelProvider] = None,
        model: Optional[str] = None
    ) -> RAGResponse:
        """End-to-end RAG answer generation based on retrieved context."""
        search_req = SearchQuery(query=query, top_k=top_k, hybrid=True, rerank=True)
        search_res = await self.search(search_req)

        context_texts = [
            f"[Tài liệu: {c.document_id} (Đoạn #{c.metadata.get('chunk_index', 0)})]:\n{c.content}"
            for c in search_res.results
        ]
        combined_context = "\n\n---\n\n".join(context_texts) if context_texts else "Không tìm thấy dữ liệu liên quan trong kho tri thức."

        system_instruction = (
            "Bạn là trợ lý tri thức doanh nghiệp chuyên nghiệp. "
            "Hãy trả lời câu hỏi dựa trên các đoạn tài liệu được cung cấp dưới đây. "
            "Nếu thông tin không có trong tài liệu, hãy thành thật nêu rõ thay vì tự suy diễn. "
            "Trích dẫn rõ nguồn tài liệu khi trả lời."
        )

        prompt = f"Ngữ cảnh tài liệu:\n{combined_context}\n\nCâu hỏi: {query}"

        llm = LLMFactory.get_provider(provider, model_override=model)
        chat_req = ChatRequest(
            messages=[ChatMessage(role=MessageRole.USER, content=prompt)],
            system_prompt=system_instruction,
            temperature=0.3
        )
        chat_res = await llm.chat_complete(chat_req)

        return RAGResponse(
            query=query,
            answer=chat_res.message.content,
            sources=search_res.results,
            model=chat_res.model,
            provider=chat_res.provider.value
        )
