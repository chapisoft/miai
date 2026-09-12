"""
Local Ollama LLM Provider (GPU NVIDIA RTX 3060 / micro-server).
"""

import time
import json
import uuid
from typing import AsyncGenerator, List, Optional
import httpx
from core.config import settings
from core.constants import ModelProvider, MessageRole
from core.exceptions import LLMProviderException
from core.telemetry import logger, LLM_INFERENCE_DURATION_SECONDS, LLM_TOKENS_TOTAL
from schemas.chat import ChatRequest, ChatResponse, ChatMessage, StreamChunk, ChatUsage
from engines.llm.base import BaseLLMProvider


class OllamaProvider(BaseLLMProvider):
    """Client for local Ollama server running on micro-server (127.0.0.1:11434)."""

    def __init__(self, base_url: Optional[str] = None, default_model: Optional[str] = None):
        super().__init__(
            provider=ModelProvider.OLLAMA,
            default_model=default_model or settings.DEFAULT_LLM_MODEL
        )
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")

    async def chat_complete(self, request: ChatRequest) -> ChatResponse:
        model = request.model or self.default_model
        url = f"{self.base_url}/api/chat"

        messages_payload = [
            {"role": msg.role.value, "content": msg.content}
            for msg in request.messages
        ]

        if request.system_prompt:
            messages_payload.insert(0, {"role": "system", "content": request.system_prompt})

        options = {
            "temperature": request.temperature,
            "num_predict": request.max_tokens or 2048
        }
        if request.context_window:
            options["num_ctx"] = request.context_window

        payload = {
            "model": model,
            "messages": messages_payload,
            "stream": False,
            "options": options
        }

        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()

            duration = time.time() - start_time
            LLM_INFERENCE_DURATION_SECONDS.labels(
                provider="OLLAMA",
                model=model,
                task_type="CHAT"
            ).observe(duration)

            prompt_tokens = data.get("prompt_eval_count", 0)
            completion_tokens = data.get("eval_count", 0)

            LLM_TOKENS_TOTAL.labels(provider="OLLAMA", model=model, token_type="prompt").inc(prompt_tokens)
            LLM_TOKENS_TOTAL.labels(provider="OLLAMA", model=model, token_type="completion").inc(completion_tokens)

            assistant_msg = data.get("message", {})
            return ChatResponse(
                id=f"ollama-{uuid.uuid4().hex[:8]}",
                provider=ModelProvider.OLLAMA,
                model=model,
                message=ChatMessage(
                    role=MessageRole.ASSISTANT,
                    content=assistant_msg.get("content", "")
                ),
                finish_reason="stop" if data.get("done") else "length",
                usage=ChatUsage(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens
                )
            )
        except Exception as e:
            logger.error("Ollama completion failed", extra={"error": str(e), "model": model})
            raise LLMProviderException(
                message=f"Lỗi suy luận mô hình Ollama cục bộ ({model}): {str(e)}",
                details={"model": model, "error": str(e)}
            )

    async def chat_stream(self, request: ChatRequest) -> AsyncGenerator[StreamChunk, None]:
        model = request.model or self.default_model
        url = f"{self.base_url}/api/chat"
        req_id = f"ollama-{uuid.uuid4().hex[:8]}"

        messages_payload = [
            {"role": msg.role.value, "content": msg.content}
            for msg in request.messages
        ]
        if request.system_prompt:
            messages_payload.insert(0, {"role": "system", "content": request.system_prompt})

        payload = {
            "model": model,
            "messages": messages_payload,
            "stream": True,
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_tokens or 2048
            }
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream("POST", url, json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        chunk_data = json.loads(line)
                        delta_text = chunk_data.get("message", {}).get("content", "")
                        done = chunk_data.get("done", False)
                        yield StreamChunk(
                            id=req_id,
                            delta=delta_text,
                            finish_reason="stop" if done else None
                        )
        except Exception as e:
            logger.error("Ollama streaming failed", extra={"error": str(e), "model": model})
            raise LLMProviderException(
                message=f"Lỗi luồng stream Ollama ({model}): {str(e)}"
            )

    async def generate_embedding(self, text: str, model: Optional[str] = None) -> List[float]:
        target_model = model or settings.DEFAULT_EMBEDDING_MODEL
        url = f"{self.base_url}/api/embeddings"
        payload = {"model": target_model, "prompt": text}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                return data.get("embedding", [])
        except Exception as e:
            logger.error("Ollama embedding failed", extra={"error": str(e), "model": target_model})
            raise LLMProviderException(
                message=f"Lỗi sinh Vector Embedding từ Ollama ({target_model}): {str(e)}"
            )
