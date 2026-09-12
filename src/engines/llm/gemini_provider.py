"""
Google Gemini API Provider.
"""

import time
import uuid
from typing import AsyncGenerator, List, Optional
import httpx
from core.config import settings
from core.constants import ModelProvider, MessageRole
from core.exceptions import LLMProviderException
from core.telemetry import logger, LLM_INFERENCE_DURATION_SECONDS
from schemas.chat import ChatRequest, ChatResponse, ChatMessage, StreamChunk, ChatUsage
from engines.llm.base import BaseLLMProvider


class GeminiProvider(BaseLLMProvider):
    """Client for Google Gemini REST API."""

    def __init__(self, api_key: Optional[str] = None, default_model: str = "gemini-1.5-flash"):
        super().__init__(provider=ModelProvider.GEMINI, default_model=default_model)
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    async def chat_complete(self, request: ChatRequest) -> ChatResponse:
        model = request.model or self.default_model
        url = f"{self.base_url}/models/{model}:generateContent?key={self.api_key}"

        contents = []
        for msg in request.messages:
            role = "user" if msg.role == MessageRole.USER else "model"
            contents.append({"role": role, "parts": [{"text": msg.content}]})

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": request.temperature,
                "maxOutputTokens": request.max_tokens or 2048
            }
        }
        if request.system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": request.system_prompt}]}

        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()

            duration = time.time() - start_time
            LLM_INFERENCE_DURATION_SECONDS.labels(
                provider="GEMINI",
                model=model,
                task_type="CHAT"
            ).observe(duration)

            candidate = data.get("candidates", [{}])[0]
            generated_text = candidate.get("content", {}).get("parts", [{}])[0].get("text", "")
            usage_meta = data.get("usageMetadata", {})

            return ChatResponse(
                id=f"gemini-{uuid.uuid4().hex[:8]}",
                provider=ModelProvider.GEMINI,
                model=model,
                message=ChatMessage(
                    role=MessageRole.ASSISTANT,
                    content=generated_text
                ),
                finish_reason=candidate.get("finishReason", "STOP"),
                usage=ChatUsage(
                    prompt_tokens=usage_meta.get("promptTokenCount", 0),
                    completion_tokens=usage_meta.get("candidatesTokenCount", 0),
                    total_tokens=usage_meta.get("totalTokenCount", 0)
                )
            )
        except Exception as e:
            logger.error("Gemini completion failed", extra={"error": str(e), "model": model})
            raise LLMProviderException(
                message=f"Lỗi gọi Google Gemini API ({model}): {str(e)}"
            )

    async def chat_stream(self, request: ChatRequest) -> AsyncGenerator[StreamChunk, None]:
        # Fallback to single completion chunk for simple REST compatibility
        res = await self.chat_complete(request)
        yield StreamChunk(
            id=res.id,
            delta=res.message.content,
            finish_reason="stop"
        )

    async def generate_embedding(self, text: str, model: Optional[str] = None) -> List[float]:
        target_model = model or "text-embedding-004"
        url = f"{self.base_url}/models/{target_model}:embedContent?key={self.api_key}"
        payload = {"model": f"models/{target_model}", "content": {"parts": [{"text": text}]}}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                return data.get("embedding", {}).get("values", [])
        except Exception as e:
            logger.error("Gemini embedding failed", extra={"error": str(e), "model": target_model})
            raise LLMProviderException(
                message=f"Lỗi sinh Vector Embedding từ Gemini ({target_model}): {str(e)}"
            )
