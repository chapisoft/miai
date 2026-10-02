"""
LLM Provider Factory.
Instantiates or caches provider instances based on configuration.
"""

from typing import Optional, Dict
from core.config import settings
from core.constants import ModelProvider
from core.exceptions import LLMProviderException
from engines.llm.base import BaseLLMProvider
from engines.llm.vllm_provider import VLLMProvider
from engines.llm.ollama_provider import OllamaProvider
from engines.llm.openai_provider import OpenAIProvider
from engines.llm.gemini_provider import GeminiProvider


class LLMFactory:
    """Factory creating BaseLLMProvider instances."""

    _instances: Dict[str, BaseLLMProvider] = {}

    @classmethod
    def get_provider(
        cls,
        provider_type: Optional[ModelProvider] = None,
        model_override: Optional[str] = None
    ) -> BaseLLMProvider:
        """
        Returns an instance for the requested provider.
        Defaults to high-throughput vLLM engine on micro-server RTX 3060.
        """
        p_type = provider_type or settings.DEFAULT_LLM_PROVIDER

        if p_type == ModelProvider.VLLM:
            return VLLMProvider(
                base_url=settings.VLLM_BASE_URL,
                default_model=model_override or settings.VLLM_DEFAULT_MODEL
            )

        elif p_type == ModelProvider.OLLAMA:
            return OllamaProvider(
                base_url=settings.OLLAMA_BASE_URL,
                default_model=model_override or settings.DEFAULT_LLM_MODEL
            )

        elif p_type == ModelProvider.OPENAI:
            return OpenAIProvider(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL,
                default_model=model_override or "gpt-4o-mini",
                provider=ModelProvider.OPENAI
            )

        elif p_type == ModelProvider.GEMINI:
            return GeminiProvider(
                api_key=settings.GEMINI_API_KEY,
                default_model=model_override or "gemini-1.5-flash"
            )

        elif p_type in (ModelProvider.DEEPSEEK, ModelProvider.CUSTOM):
            # Uses OpenAI compatible interface
            return OpenAIProvider(
                api_key=settings.DEEPSEEK_API_KEY,
                base_url=settings.OPENAI_BASE_URL,
                default_model=model_override or "deepseek-chat",
                provider=p_type
            )

        raise LLMProviderException(
            message=f"Nhà cung cấp mô hình {p_type} chưa được hỗ trợ"
        )
