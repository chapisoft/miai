"""
Abstract Base LLM Provider Interface.
Defines unified contracts for generation, streaming, and embeddings.
"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, List, Dict, Any, Optional
from schemas.chat import ChatRequest, ChatResponse, StreamChunk
from core.constants import ModelProvider


class BaseLLMProvider(ABC):
    """Abstract Base Class for all LLM backends."""

    def __init__(self, provider: ModelProvider, default_model: str):
        self.provider = provider
        self.default_model = default_model

    @abstractmethod
    async def chat_complete(self, request: ChatRequest) -> ChatResponse:
        """Executes a non-streaming chat completion."""
        pass

    @abstractmethod
    def chat_stream(self, request: ChatRequest) -> AsyncGenerator[StreamChunk, None]:
        """Streams token deltas asynchronously."""
        pass

    @abstractmethod
    async def generate_embedding(self, text: str, model: Optional[str] = None) -> List[float]:
        """Generates dense vector embeddings for a given text."""
        pass
