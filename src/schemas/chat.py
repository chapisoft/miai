"""
Chat & Streaming Schemas.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from core.constants import MessageRole, ModelProvider


class ChatMessage(BaseModel):
    """Represents a single conversational turn."""
    role: MessageRole = Field(description="Role: system, user, assistant, tool")
    content: str = Field(description="Textual message content")
    name: Optional[str] = Field(default=None, description="Optional name for tool/function calling")


class ChatRequest(BaseModel):
    """Payload for LLM chat completions."""
    messages: List[ChatMessage] = Field(description="List of prior messages in the conversation")
    provider: Optional[ModelProvider] = Field(default=None, description="Target LLM provider (OLLAMA, OPENAI, etc.)")
    model: Optional[str] = Field(default=None, description="Specific model name override (e.g. qwen2.5:7b)")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: Optional[int] = Field(default=2048, ge=1, le=8192, description="Maximum tokens to generate")
    stream: bool = Field(default=False, description="Enable Server-Sent Events (SSE) streaming")
    system_prompt: Optional[str] = Field(default=None, description="Optional system instruction override")
    context_window: Optional[int] = Field(default=None, description="KV cache context limit")


class ChatUsage(BaseModel):
    prompt_tokens: int = Field(default=0)
    completion_tokens: int = Field(default=0)
    total_tokens: int = Field(default=0)


class ChatResponse(BaseModel):
    """Unified chat response structure."""
    id: str = Field(description="Unique completion ID")
    provider: ModelProvider = Field(description="Provider that served the response")
    model: str = Field(description="Model used for inference")
    message: ChatMessage = Field(description="Generated assistant message")
    finish_reason: str = Field(default="stop", description="Reason for stopping generation")
    usage: ChatUsage = Field(default_factory=ChatUsage, description="Token consumption statistics")


class StreamChunk(BaseModel):
    """Chunk sent over Server-Sent Events (SSE)."""
    id: str
    delta: str
    finish_reason: Optional[str] = None
