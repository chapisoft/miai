"""
vLLM High-Throughput Inference Engine Provider.
Communicates with local or remote vLLM server via OpenAI-Compatible API.
Leverages PagedAttention and Continuous Batching for high concurrency.
"""

import time
import json
import uuid
from typing import AsyncGenerator, List, Optional, Dict, Any
import httpx
from core.config import settings
from core.constants import ModelProvider, MessageRole
from core.exceptions import LLMProviderException
from core.telemetry import logger, LLM_INFERENCE_DURATION_SECONDS, LLM_TOKENS_TOTAL
from schemas.chat import ChatRequest, ChatResponse, ChatMessage, StreamChunk, ChatUsage
from engines.llm.base import BaseLLMProvider


class VLLMProvider(BaseLLMProvider):
    """
    High-performance LLM Provider connected to vLLM inference server.
    Optimized for NVIDIA RTX 3060 12GB VRAM with Continuous Batching.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        default_model: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        model = default_model or settings.VLLM_DEFAULT_MODEL
        super().__init__(provider=ModelProvider.VLLM, default_model=model)
        self.base_url = (base_url or settings.VLLM_BASE_URL).rstrip("/")
        self.api_key = api_key or "EMPTY"

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        return headers

    async def chat_complete(self, request: ChatRequest) -> ChatResponse:
        """
        Executes non-streaming completion with vLLM PagedAttention engine.
        """
        model = request.model or self.default_model
        url = f"{self.base_url}/chat/completions"

        messages_payload = [
            {"role": msg.role.value, "content": msg.content}
            for msg in request.messages
        ]
        if request.system_prompt:
            messages_payload.insert(0, {"role": "system", "content": request.system_prompt})

        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages_payload,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens or 2048,
            "stream": False,
        }

        # Structured Output (JSON mode) support in vLLM
        if request.response_format and request.response_format.get("type") == "json_object":
            payload["response_format"] = {"type": "json_object"}

        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(url, json=payload, headers=self._get_headers())
                response.raise_for_status()
                data = response.json()

            duration = time.time() - start_time
            LLM_INFERENCE_DURATION_SECONDS.labels(
                provider="VLLM",
                model=model,
                task_type="CHAT"
            ).observe(duration)

            choice = data["choices"][0]
            usage = data.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)

            LLM_TOKENS_TOTAL.labels(provider="VLLM", model=model, token_type="prompt").inc(prompt_tokens)
            LLM_TOKENS_TOTAL.labels(provider="VLLM", model=model, token_type="completion").inc(completion_tokens)

            return ChatResponse(
                id=data.get("id", f"vllm-{uuid.uuid4().hex[:8]}"),
                provider=self.provider,
                model=model,
                message=ChatMessage(
                    role=MessageRole.ASSISTANT,
                    content=choice["message"]["content"]
                ),
                finish_reason=choice.get("finish_reason", "stop"),
                usage=ChatUsage(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=usage.get("total_tokens", prompt_tokens + completion_tokens)
                )
            )
        except Exception as e:
            logger.error("vLLM chat completion failed", extra={"error": str(e), "model": model})
            raise LLMProviderException(
                message=f"Lỗi suy luận mô hình vLLM ({model}): {str(e)}"
            )

    async def chat_stream(self, request: ChatRequest) -> AsyncGenerator[StreamChunk, None]:
        """
        Executes streaming SSE token delivery from vLLM engine.
        """
        model = request.model or self.default_model
        url = f"{self.base_url}/chat/completions"
        req_id = f"vllm-{uuid.uuid4().hex[:8]}"

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
            "stream": True,
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST", url, json=payload, headers=self._get_headers()
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk_data = json.loads(data_str)
                            choice = chunk_data["choices"][0]
                            delta = choice.get("delta", {})
                            content = delta.get("content", "")
                            finish_reason = choice.get("finish_reason")

                            if content or finish_reason:
                                yield StreamChunk(
                                    id=chunk_data.get("id", req_id),
                                    model=model,
                                    provider=self.provider,
                                    delta=content,
                                    finish_reason=finish_reason,
                                )
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.error("vLLM streaming failed", extra={"error": str(e), "model": model})
            raise LLMProviderException(
                message=f"Lỗi luồng stream từ vLLM ({model}): {str(e)}"
            )

    async def generate_embedding(self, text: str, model: Optional[str] = None) -> List[float]:
        """
        Generates vector embeddings via vLLM embedding endpoint if deployed.
        """
        target_model = model or settings.DEFAULT_EMBEDDING_MODEL
        url = f"{self.base_url}/embeddings"
        payload = {"input": text, "model": target_model}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=self._get_headers())
                response.raise_for_status()
                data = response.json()
            return data["data"][0]["embedding"]
        except Exception as e:
            logger.error("vLLM embedding failed", extra={"error": str(e), "model": target_model})
            raise LLMProviderException(
                message=f"Lỗi sinh Vector Embedding từ vLLM ({target_model}): {str(e)}"
            )
