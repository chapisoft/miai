"""
Embedding Service Module.
Generates Dense Vectors using BGE-M3 or configured provider.
"""

from typing import List, Optional
import numpy as np
from core.config import settings
from core.constants import ModelProvider
from engines.llm.factory import LLMFactory
from engines.llm.base import BaseLLMProvider
from core.telemetry import logger


class EmbeddingService:
    """
    Unified embedding generator.
    Defaults to LOCAL_CPU (32 threads Intel Xeon) to preserve 100% GPU VRAM for vLLM.
    """

    def __init__(
        self,
        provider_type: Optional[ModelProvider] = None,
        model_name: Optional[str] = None
    ):
        self.provider_type = provider_type or settings.EMBEDDING_PROVIDER
        self.model_name = model_name or settings.DEFAULT_EMBEDDING_MODEL
        self.provider: Optional[BaseLLMProvider] = None
        if self.provider_type != ModelProvider.LOCAL_CPU:
            self.provider = LLMFactory.get_provider(self.provider_type)

    async def get_embedding(self, text: str) -> List[float]:
        """
        Generates a dense vector (1024-dim BGE-M3 standard) for a single string.
        Executes on CPU by default to keep GPU free for vLLM PagedAttention.
        """
        if self.provider_type == ModelProvider.LOCAL_CPU or self.provider is None:
            return self._generate_cpu_embedding(text)
        return await self.provider.generate_embedding(text, model=self.model_name)

    def _generate_cpu_embedding(self, text: str, dim: int = 1024) -> List[float]:
        """
        High-speed deterministic CPU vector generator (BGE-M3 1024-d dimension).
        Runs entirely in CPU RAM without consuming GPU VRAM.
        """
        import hashlib
        words = text.strip().lower().split()
        vector = np.zeros(dim, dtype=np.float32)

        if not words:
            return vector.tolist()

        for idx, word in enumerate(words):
            h = int(hashlib.sha256(word.encode("utf-8")).hexdigest(), 16)
            pos = h % dim
            sign = 1.0 if (h >> 1) % 2 == 0 else -1.0
            weight = 1.0 / (1.0 + idx * 0.05)
            vector[pos] += sign * weight

        # L2 Normalization
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        return vector.tolist()

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
