"""
Pytest configuration and shared fixtures for base-ai testing.
"""

import pytest
import os
import sys

# Ensure root directory is on python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.config import settings
from engines.rag.pipeline import HybridRAGPipeline
from engines.rag.vector_store import InMemoryVectorStore


@pytest.fixture
def in_memory_rag_pipeline():
    """Provides a fresh Hybrid RAG pipeline with in-memory vector store."""
    store = InMemoryVectorStore()
    return HybridRAGPipeline(vector_store=store)
