"""
FastAPI Dependencies: Auth, Database Session, and Pipelines.
"""

from typing import Dict, Any
from fastapi import Depends
from core.security import verify_auth_token
from core.database import get_db_session
from engines.rag.pipeline import HybridRAGPipeline

_singleton_rag_pipeline = HybridRAGPipeline()


def get_rag_pipeline() -> HybridRAGPipeline:
    """Provides a shared Hybrid RAG Pipeline instance."""
    return _singleton_rag_pipeline


async def get_current_user(auth_context: Dict[str, Any] = Depends(verify_auth_token)) -> Dict[str, Any]:
    """Retrieves validated caller context."""
    return auth_context
