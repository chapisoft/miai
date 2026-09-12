"""
Unit Tests for Hybrid RAG: Chunking, BM25, and Vector Stores.
"""

import pytest
from engines.rag.chunker import DocumentChunker
from engines.rag.bm25_retriever import BM25Retriever
from engines.rag.embeddings import EmbeddingService
from engines.rag.vector_store import InMemoryVectorStore
from schemas.rag import DocumentChunk


def test_document_chunker_sentence_splitting():
    text = (
        "Hệ thống E-Office quản lý 20.7 triệu văn bản điều hành. "
        "Dữ liệu được lưu trữ an toàn trong Oracle Database 23ai. "
        "Các phân hệ tích hợp bao gồm Văn bản đến, Văn bản đi và Thông báo nhắc việc."
    )
    chunks = DocumentChunker.chunk_document(
        document_id="doc_test_1",
        content=text,
        chunk_size=70,
        chunk_overlap=15
    )
    assert len(chunks) >= 2
    assert chunks[0].document_id == "doc_test_1"
    assert "E-Office" in chunks[0].content


def test_bm25_retriever_exact_keyword_matching():
    chunks = [
        DocumentChunk(
            chunk_id="c1",
            document_id="d1",
            content="Quy trình thanh toán hóa đơn VAT cho nhà cung cấp mã NCC-9988."
        ),
        DocumentChunk(
            chunk_id="c2",
            document_id="d2",
            content="Quy định hạn mức kiểm kê kho vật tư linh kiện điện tử."
        ),
        DocumentChunk(
            chunk_id="c3",
            document_id="d3",
            content="Báo cáo tiến độ nghiệm thu dự án xây dựng cầu đường 2026."
        )
    ]
    bm25 = BM25Retriever()
    bm25.index_documents(chunks)

    results = bm25.search("NCC-9988", top_k=1)
    assert len(results) == 1
    assert results[0][0].chunk_id == "c1"
    assert results[0][1] > 0.0


def test_cosine_similarity_identical_vectors():
    vec_a = [1.0, 2.0, 3.0]
    vec_b = [1.0, 2.0, 3.0]
    sim = EmbeddingService.cosine_similarity(vec_a, vec_b)
    assert pytest.approx(sim, 0.001) == 1.0


def test_cosine_similarity_orthogonal_vectors():
    vec_a = [1.0, 0.0]
    vec_b = [0.0, 1.0]
    sim = EmbeddingService.cosine_similarity(vec_a, vec_b)
    assert pytest.approx(sim, 0.001) == 0.0
