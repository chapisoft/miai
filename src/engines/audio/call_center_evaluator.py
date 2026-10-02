"""
Call Center Quality Evaluator & Sentiment Analysis.
Scores customer service interactions against corporate communication guidelines.
"""

from typing import List, Optional
from core.config import settings
from core.constants import ModelProvider
from engines.llm.factory import LLMFactory
from engines.llm.structured import StructuredExtractor
from schemas.audio import CallScoreDto, SpeakerSegment


class CallCenterEvaluator:
    """Evaluates customer service representative performance and customer sentiment."""

    SYSTEM_PROMPT = (
        "Bạn là chuyên gia giám định chất lượng tổng đài chăm sóc khách hàng. "
        "Hãy đánh giá chi tiết cuộc gọi dựa trên mức độ tuân thủ kịch bản, thái độ nhân viên, "
        "cảm xúc khách hàng (Hài lòng, Trung lập, Bức xúc) và đưa ra góp ý hoàn thiện."
    )

    @classmethod
    async def evaluate_call(
        cls,
        segments: List[SpeakerSegment],
        provider: Optional[ModelProvider] = None
    ) -> CallScoreDto:
        """Scores call recording transcript."""
        dialogue = "\n".join([f"[{s.speaker}]: {s.text}" for s in segments])

        llm = LLMFactory.get_provider(provider or settings.DEFAULT_LLM_PROVIDER)
        return await StructuredExtractor.extract(
            provider=llm,
            prompt=f"Nội dung cuộc gọi tổng đài:\n{dialogue}",
            schema=CallScoreDto,
            system_instruction=cls.SYSTEM_PROMPT
        )
