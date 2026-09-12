"""
Structured Extraction Engine.
Enforces LLMs to output strict JSON validating against any target Pydantic schema.
"""

import json
import re
from typing import Type, TypeVar, Optional
from pydantic import BaseModel
from core.exceptions import LLMProviderException
from core.constants import MessageRole
from core.telemetry import logger
from schemas.chat import ChatRequest, ChatMessage
from engines.llm.base import BaseLLMProvider

T = TypeVar("T", bound=BaseModel)


class StructuredExtractor:
    """Extracts strictly-typed Pydantic objects from unstructured prompts."""

    @staticmethod
    def _clean_json_markdown(raw: str) -> str:
        """Strips ```json code fences and cleans leading/trailing whitespace."""
        text = raw.strip()
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if match:
            return match.group(1).strip()
        return text

    @classmethod
    async def extract(
        cls,
        provider: BaseLLMProvider,
        prompt: str,
        schema: Type[T],
        system_instruction: Optional[str] = None,
        model: Optional[str] = None,
        max_retries: int = 2
    ) -> T:
        """
        Forces provider to generate output adhering to target Pydantic schema JSON.
        Includes automatic retry loop if JSON parsing fails.
        """
        schema_json = json.dumps(schema.model_json_schema(), indent=2)
        base_instruction = (
            "Bạn là một bộ máy trích xuất dữ liệu có cấu trúc chính xác tuyệt đối. "
            "BẮT BUỘC chỉ trả về duy nhất một chuỗi JSON hợp lệ tuân thủ đúng JSON Schema sau đây, "
            "tuyệt đối không kèm theo lời giải thích hoặc mã markdown thừa:\n"
            f"{schema_json}"
        )

        if system_instruction:
            full_system = f"{base_instruction}\n\nNgữ cảnh nghiệp vụ bổ sung:\n{system_instruction}"
        else:
            full_system = base_instruction

        request = ChatRequest(
            messages=[ChatMessage(role=MessageRole.USER, content=prompt)],
            model=model,
            system_prompt=full_system,
            temperature=0.1
        )

        last_error = None
        for attempt in range(max_retries + 1):
            try:
                response = await provider.chat_complete(request)
                raw_content = response.message.content
                cleaned_json = cls._clean_json_markdown(raw_content)
                parsed_dict = json.loads(cleaned_json)
                return schema.model_validate(parsed_dict)
            except Exception as e:
                last_error = e
                logger.warning(
                    "Structured extraction attempt failed, retrying...",
                    extra={"attempt": attempt + 1, "schema": schema.__name__, "error": str(e)}
                )

        raise LLMProviderException(
            message=f"Không thể trích xuất cấu trúc dữ liệu theo schema {schema.__name__}: {str(last_error)}",
            details={"schema": schema.__name__, "error": str(last_error)}
        )
