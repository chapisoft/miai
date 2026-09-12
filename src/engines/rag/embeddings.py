"""
Embedding Service Module.
Generates Dense Vectors using BGE-M3 or configured provider.
"""

from typing import List, Optional
import numpy as np
from core.config import settings
from core.constants import ModelProvider
from engines.llm.factory import LLMFactory
from core.telemetry import logger


class EmbeddingService:
    """Unified embedding generator."""

    def __init__(
        self,
        provider_type: ModelProvider = ModelProvider.OLLAMA,
        model_name: Optional[str] = None
    ):
        self.provider = LLMFactory.get_provider(provider_type)
        self.model_name = model_name or settings.DEFAULT_EMBEDDING_MODEL

    async def get_embedding(self, text: str) -> List[float]:
        """Generates a dense vector for a single string."""
        return await self.provider.generate_embedding(text, model=self.model_name)

    async def get_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generates embeddings for a batch of text chunks."""
        embeddings = []
        for text in texts:
            vec = await self.get_embedding(text)
            embeddings.append(vec)
        return embeddings

    @staticmethod
    def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
        """Calculates cosine similarity between two numeric vectors."""
        a = np.array(vec_a, dtype=np.float32)
        b = np.array(vec_b, dtype=np.float32)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))
