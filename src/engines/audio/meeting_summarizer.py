"""
Meeting Minutes & Action Items Summarizer.
Extracts structured executive summary and deliverables table from audio transcripts.
"""

from typing import List, Optional
from schemas.audio import MeetingMinutesDto, SpeakerSegment, ActionItemDto
from engines.llm.structured import StructuredExtractor
from engines.llm.factory import LLMFactory
from core.constants import ModelProvider


class MeetingSummarizer:
    """Summarizes transcribed meetings into structured minutes."""

    SYSTEM_PROMPT = (
        "Bạn là thư ký điều hành cấp cao của doanh nghiệp. "
        "Dựa trên nội dung bóc băng cuộc họp, hãy trích xuất: Tiêu đề cuộc họp, người tham dự, "
        "tóm tắt nội dung chính, các quyết định quan trọng và danh sách công việc giao phó (Action Items) "
        "kèm người phụ trách và thời hạn cụ thể."
    )

    @classmethod
    async def summarize_meeting(
        cls,
        segments: List[SpeakerSegment],
        provider: Optional[ModelProvider] = None
    ) -> MeetingMinutesDto:
        """Processes transcription segments and returns structured MeetingMinutesDto."""
        full_transcript = "\n".join([f"[{s.speaker}]: {s.text}" for s in segments])

        llm = LLMFactory.get_provider(provider or ModelProvider.OLLAMA)
        return await StructuredExtractor.extract(
            provider=llm,
            prompt=f"Nội dung bóc băng cuộc họp:\n{full_transcript}",
            schema=MeetingMinutesDto,
            system_instruction=cls.SYSTEM_PROMPT
        )
