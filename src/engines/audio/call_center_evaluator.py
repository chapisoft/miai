"""
Call Center Quality Evaluator & Sentiment Analysis.
Scores customer service interactions against corporate communication guidelines.
"""

from typing import List, Optional
from schemas.audio import CallScoreDto, SpeakerSegment
from engines.llm.structured import StructuredExtractor
from engines.llm.factory import LLMFactory
from core.constants import ModelProvider


class CallCenterEvaluator:
    """Evaluates customer support recordings."""

    SYSTEM_PROMPT = (
        "Bạn là chuyên gia giám sát chất lượng tổng đài chăm sóc khách hàng (Call Center QA). "
        "Dựa vào nội dung cuộc đối thoại giữa Điện thoại viên và Khách hàng, hãy chấm điểm (thang 100), "
        "kiểm tra tuân thủ lời chào/lời cảm ơn, phát hiện từ cấm, đánh giá thái độ nhân viên, "
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

        llm = LLMFactory.get_provider(provider or ModelProvider.OLLAMA)
        return await StructuredExtractor.extract(
            provider=llm,
            prompt=f"Nội dung cuộc gọi tổng đài:\n{dialogue}",
            schema=CallScoreDto,
            system_instruction=cls.SYSTEM_PROMPT
        )
