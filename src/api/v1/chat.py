"""
Chat & Streaming API Endpoints.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from schemas.chat import ChatRequest, ChatResponse
from core.responses import ApiResponse
from core.guardrails import Guardrails
from engines.llm.factory import LLMFactory
from engines.llm.streaming import StreamHelper
from api.dependencies import get_current_user

router = APIRouter(prefix="/chat", tags=["Chat & LLM Gateway"])


@router.post("/completions", response_model=ApiResponse[ChatResponse], summary="Gửi yêu cầu Chat LLM (Non-streaming)")
async def chat_completions(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user)
) -> ApiResponse[ChatResponse]:
    """
    Executes standard LLM chat completion.
    Passes prompt through Guardrails for injection safety and PII masking.
    """
    # 1. Guardrails Check
    for msg in request.messages:
        Guardrails.inspect_prompt(msg.content)
        msg.content = Guardrails.redact_pii(msg.content)

    # 2. Execute via LLM Factory
    provider = LLMFactory.get_provider(request.provider, model_override=request.model)
    res = await provider.chat_complete(request)

    return ApiResponse.success(data=res, message="Chat completion generated successfully")


@router.post("/stream", summary="Luồng hội thoại thời gian thực (SSE Streaming)")
async def chat_streaming(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Streams response token-by-token over Server-Sent Events (SSE).
    """
    for msg in request.messages:
        Guardrails.inspect_prompt(msg.content)
        msg.content = Guardrails.redact_pii(msg.content)

    provider = LLMFactory.get_provider(request.provider, model_override=request.model)
    generator = provider.chat_stream(request)

    return StreamingResponse(
        StreamHelper.to_sse(generator),
        media_type="text/event-stream"
    )
