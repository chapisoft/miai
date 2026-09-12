"""
OpenAI & OpenAI-compatible API Provider (OpenAI, vLLM, DeepSeek, LiteLLM).
"""

import time
import json
import uuid
from typing import AsyncGenerator, List, Optional
import httpx
from core.config import settings
from core.constants import ModelProvider, MessageRole
from core.exceptions import LLMProviderException
from core.telemetry import logger, LLM_INFERENCE_DURATION_SECONDS
from schemas.chat import ChatRequest, ChatResponse, ChatMessage, StreamChunk, ChatUsage
from engines.llm.base import BaseLLMProvider


class OpenAIProvider(BaseLLMProvider):
    """Client for OpenAI and compatible REST endpoints."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        default_model: str = "gpt-4o-mini",
        provider: ModelProvider = ModelProvider.OPENAI
    ):
        super().__init__(provider=provider, default_model=default_model)
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.base_url = (base_url or settings.OPENAI_BASE_URL).rstrip("/")

    def _get_headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def chat_complete(self, request: ChatRequest) -> ChatResponse:
        model = request.model or self.default_model
        url = f"{self.base_url}/chat/completions"

        messages_payload = [
            {"role": msg.role.value, "content": msg.content}
            for msg in request.messages
        ]
        if request.system_prompt:
            messages_payload.insert(0, {"role": "system", "content": request.system_prompt})

        payload = {
            "model": model,
            "messages": messages_payload,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens or 2048,
            "stream": False
        }

        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, json=payload, headers=self._get_headers())
                response.raise_for_status()
                data = response.json()

            duration = time.time() - start_time
            LLM_INFERENCE_DURATION_SECONDS.labels(
                provider=self.provider.value,
                model=model,
                task_type="CHAT"
            ).observe(duration)

            choice = data["choices"][0]
            usage = data.get("usage", {})

            return ChatResponse(
                id=data.get("id", f"openai-{uuid.uuid4().hex[:8]}"),
                provider=self.provider,
                model=model,
                message=ChatMessage(
                    role=MessageRole.ASSISTANT,
                    content=choice["message"]["content"]
                ),
                finish_reason=choice.get("finish_reason", "stop"),
                usage=ChatUsage(
                    prompt_tokens=usage.get("prompt_tokens", 0),
                    completion_tokens=usage.get("completion_tokens", 0),
                    total_tokens=usage.get("total_tokens", 0)
                )
            )
        except Exception as e:
            logger.error("OpenAI chat completion failed", extra={"error": str(e), "model": model})
            raise LLMProviderException(
                message=f"Lỗi gọi API {self.provider.value} ({model}): {str(e)}"
            )

    async def chat_stream(self, request: ChatRequest) -> AsyncGenerator[StreamChunk, None]:
        model = request.model or self.default_model
        url = f"{self.base_url}/chat/completions"
        req_id = f"openai-{uuid.uuid4().hex[:8]}"

        messages_payload = [
            {"role": msg.role.value, "content": msg.content}
            for msg in request.messages
        ]
        if request.system_prompt:
            messages_payload.insert(0, {"role": "system", "content": request.system_prompt})

        payload = {
            "model": model,
            "messages": messages_payload,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens or 2048,
            "stream": True
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream("POST", url, json=payload, headers=self._get_headers()) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            break
                        chunk_json = json.loads(data_str)
                        choices = chunk_json.get("choices", [])
                        if choices:
                            delta = choices[0].get("delta", {}).get("content", "")
                            finish_reason = choices[0].get("finish_reason")
                            if delta:
                                yield StreamChunk(
                                    id=req_id,
                                    delta=delta,
                                    finish_reason=finish_reason
                                )
        except Exception as e:
            logger.error("OpenAI streaming failed", extra={"error": str(e), "model": model})
            raise LLMProviderException(
                message=f"Lỗi luồng stream {self.provider.value} ({model}): {str(e)}"
            )

    async def generate_embedding(self, text: str, model: Optional[str] = None) -> List[float]:
        target_model = model or "text-embedding-3-small"
        url = f"{self.base_url}/embeddings"
        payload = {"input": text, "model": target_model}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=self._get_headers())
                response.raise_for_status()
                data = response.json()
                return data["data"][0]["embedding"]
        except Exception as e:
            logger.error("OpenAI embedding failed", extra={"error": str(e), "model": target_model})
            raise LLMProviderException(
                message=f"Lỗi sinh Vector Embedding từ {self.provider.value} ({target_model}): {str(e)}"
            )
