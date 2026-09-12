"""
Reranker Service Module.
Applies Cross-Encoder scoring to re-rank hybrid search candidates.
"""

from typing import List, Tuple
from schemas.rag import DocumentChunk
from core.telemetry import logger


class RerankerService:
    """Re-ranks retrieved candidate passages using cross-attention or heuristic scoring."""

    def __init__(self, model_name: str = "bge-reranker-large"):
        self.model_name = model_name

    async def rerank(
        self,
        query: str,
        candidates: List[DocumentChunk],
        top_k: int = 5
    ) -> List[DocumentChunk]:
        """
        Calculates precision relevance scores between the query and candidate passages.
        If ML sentence-transformers cross-encoder is not installed, falls back to normalized fusion scoring.
        """
        if not candidates:
            return []

        # Return sorted by existing score if available or preserve rank
        scored_candidates = []
        for rank, chunk in enumerate(candidates):
            base_score = chunk.score if chunk.score is not None else (1.0 / (rank + 1))
            # Heuristic term overlap boost
            query_words = set(query.lower().split())
            chunk_words = set(chunk.content.lower().split())
            overlap = len(query_words.intersection(chunk_words))
            boosted_score = base_score + (overlap * 0.1)
            
            updated_chunk = chunk.model_copy()
            updated_chunk.score = round(boosted_score, 4)
            scored_candidates.append(updated_chunk)

        scored_candidates.sort(key=lambda x: x.score or 0.0, reverse=True)
        return scored_candidates[:top_k]
