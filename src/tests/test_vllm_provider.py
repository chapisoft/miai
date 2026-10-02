"""
Unit Tests for vLLM High-Throughput Inference Engine Provider and LLM Factory.
Tests non-streaming, streaming, JSON schema guided decoding, and error resilience.
"""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from core.constants import ModelProvider, MessageRole
from core.exceptions import LLMProviderException
from schemas.chat import ChatRequest, ChatMessage
from engines.llm.vllm_provider import VLLMProvider
from engines.llm.factory import LLMFactory


@pytest.fixture
def vllm_provider():
    return VLLMProvider(
        base_url="http://127.0.0.1:8000/v1",
        default_model="Qwen/Qwen2.5-7B-Instruct-AWQ",
        api_key="test-api-key"
    )


def test_vllm_provider_initialization(vllm_provider):
    assert vllm_provider.provider == ModelProvider.VLLM
    assert vllm_provider.base_url == "http://127.0.0.1:8000/v1"
    assert vllm_provider.default_model == "Qwen/Qwen2.5-7B-Instruct-AWQ"
    headers = vllm_provider._get_headers()
    assert headers["Authorization"] == "Bearer test-api-key"
    assert headers["Content-Type"] == "application/json"


def test_llm_factory_resolves_vllm_by_default():
    provider = LLMFactory.get_provider()
    assert isinstance(provider, VLLMProvider)
    assert provider.provider == ModelProvider.VLLM


def test_llm_factory_explicit_vllm():
    provider = LLMFactory.get_provider(ModelProvider.VLLM)
    assert isinstance(provider, VLLMProvider)
    assert provider.provider == ModelProvider.VLLM


@pytest.mark.asyncio
async def test_vllm_chat_complete_success(vllm_provider):
    mock_response_data = {
        "id": "chatcmpl-vllm-test123",
        "object": "chat.completion",
        "created": 1726930000,
        "model": "Qwen/Qwen2.5-7B-Instruct-AWQ",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Chào bạn! Tôi là trợ lý AI vận hành trên vLLM PagedAttention."
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 15,
            "completion_tokens": 20,
            "total_tokens": 35
        }
    }

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_response_data
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp

        request = ChatRequest(
            messages=[ChatMessage(role=MessageRole.USER, content="Xin chào")],
            system_prompt="Bạn là trợ lý doanh nghiệp.",
            temperature=0.3,
            max_tokens=100
        )

        response = await vllm_provider.chat_complete(request)

        assert response.provider == ModelProvider.VLLM
        assert response.model == "Qwen/Qwen2.5-7B-Instruct-AWQ"
        assert response.message.content == "Chào bạn! Tôi là trợ lý AI vận hành trên vLLM PagedAttention."
        assert response.usage.prompt_tokens == 15
        assert response.usage.completion_tokens == 20
        assert response.usage.total_tokens == 35

        # Kiểm tra payload gửi sang vLLM server
        mock_post.assert_called_once()
        called_url, kwargs = mock_post.call_args[0][0], mock_post.call_args[1]
        assert called_url == "http://127.0.0.1:8000/v1/chat/completions"
        assert kwargs["json"]["messages"][0]["role"] == "system"
        assert kwargs["json"]["messages"][1]["role"] == "user"


@pytest.mark.asyncio
async def test_vllm_chat_complete_json_mode(vllm_provider):
    mock_response_data = {
        "id": "chatcmpl-vllm-json",
        "choices": [
            {
                "message": {"role": "assistant", "content": '{"status": "SUCCESS", "code": 200}'},
                "finish_reason": "stop"
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20}
    }

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_response_data
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp

        request = ChatRequest(
            messages=[ChatMessage(role=MessageRole.USER, content="Trả về JSON")],
            response_format={"type": "json_object"}
        )

        response = await vllm_provider.chat_complete(request)
        assert response.message.content == '{"status": "SUCCESS", "code": 200}'

        # Đảm bảo payload có response_format
        sent_payload = mock_post.call_args[1]["json"]
        assert sent_payload.get("response_format") == {"type": "json_object"}


@pytest.mark.asyncio
async def test_vllm_chat_complete_failure(vllm_provider):
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.HTTPStatusError(
            message="Internal Server Error",
            request=MagicMock(),
            response=MagicMock(status_code=500)
        )

        request = ChatRequest(
            messages=[ChatMessage(role=MessageRole.USER, content="Thử lỗi")]
        )

        with pytest.raises(LLMProviderException) as exc_info:
            await vllm_provider.chat_complete(request)

        assert "Lỗi suy luận mô hình vLLM" in str(exc_info.value)


@pytest.mark.asyncio
async def test_vllm_chat_stream_success(vllm_provider):
    sse_lines = [
        'data: {"id": "chunk-1", "choices": [{"delta": {"content": "Xin "}, "finish_reason": null}]}',
        'data: {"id": "chunk-2", "choices": [{"delta": {"content": "chào "}, "finish_reason": null}]}',
        'data: {"id": "chunk-3", "choices": [{"delta": {"content": "Việt Nam!"}, "finish_reason": "stop"}]}',
        'data: [DONE]'
    ]

    async def mock_aiter_lines():
        for line in sse_lines:
            yield line

    mock_stream_resp = MagicMock()
    mock_stream_resp.raise_for_status = MagicMock()
    mock_stream_resp.aiter_lines = mock_aiter_lines

    class MockStreamContext:
        async def __aenter__(self):
            return mock_stream_resp

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    with patch("httpx.AsyncClient.stream", return_value=MockStreamContext()):
        request = ChatRequest(
            messages=[ChatMessage(role=MessageRole.USER, content="Stream test")]
        )

        chunks = []
        async for chunk in vllm_provider.chat_stream(request):
            chunks.append(chunk)

        assert len(chunks) == 3
        assert chunks[0].delta == "Xin "
        assert chunks[1].delta == "chào "
        assert chunks[2].delta == "Việt Nam!"
        assert chunks[2].finish_reason == "stop"
        full_text = "".join(c.delta for c in chunks)
        assert full_text == "Xin chào Việt Nam!"


@pytest.mark.asyncio
async def test_vllm_generate_embedding_success(vllm_provider):
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": [{"embedding": [0.12, -0.45, 0.88, 0.01]}]
    }
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp

        embedding = await vllm_provider.generate_embedding("Văn bản kiểm thử")
        assert len(embedding) == 4
        assert embedding[0] == 0.12
