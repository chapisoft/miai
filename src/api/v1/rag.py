"""
Hybrid RAG and Knowledge Management API Endpoints.
"""

from typing import List
from fastapi import APIRouter, Depends
from schemas.rag import DocumentCreate, DocumentChunk, SearchQuery, SearchResult, RAGResponse
from core.responses import ApiResponse
from engines.rag.pipeline import HybridRAGPipeline
from api.dependencies import get_rag_pipeline, get_current_user

router = APIRouter(prefix="/rag", tags=["Hybrid RAG & Knowledge Base"])


@router.post("/documents", response_model=ApiResponse[List[DocumentChunk]], summary="Nạp tài liệu vào kho tri thức Vector")
async def ingest_document(
    document: DocumentCreate,
    pipeline: HybridRAGPipeline = Depends(get_rag_pipeline),
    current_user: dict = Depends(get_current_user)
) -> ApiResponse[List[DocumentChunk]]:
    """Ingests a text document, chunks it, generates embeddings, and indexes into Vector Store & BM25."""
    chunks = await pipeline.ingest_document(document)
    return ApiResponse.success(
        data=chunks,
        message=f"Đã nạp và phân rã thành công {len(chunks)} đoạn tri thức vào hệ thống"
    )


@router.post("/search", response_model=ApiResponse[SearchResult], summary="Tìm kiếm tri thức lai (Dense Vector + BM25 + Rerank)")
async def hybrid_search(
    query: SearchQuery,
    pipeline: HybridRAGPipeline = Depends(get_rag_pipeline),
    current_user: dict = Depends(get_current_user)
) -> ApiResponse[SearchResult]:
    """Performs hybrid retrieval returning the most relevant document chunks."""
    result = await pipeline.search(query)
    return ApiResponse.success(data=result, message="Truy xuất dữ liệu thành công")


@router.post("/query", response_model=ApiResponse[RAGResponse], summary="Hỏi đáp thông minh tổng hợp từ tài liệu (RAG QA)")
async def rag_query(
    query: SearchQuery,
    pipeline: HybridRAGPipeline = Depends(get_rag_pipeline),
    current_user: dict = Depends(get_current_user)
) -> ApiResponse[RAGResponse]:
    """Retrieves relevant context and generates a synthesized answer."""
    rag_ans = await pipeline.answer(query=query.query, top_k=query.top_k)
    return ApiResponse.success(data=rag_ans, message="Tổng hợp câu trả lời thành công")
