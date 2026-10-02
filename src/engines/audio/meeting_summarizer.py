"""
Meeting Minutes & Action Items Summarizer.
Extracts structured executive summary and deliverables table from audio transcripts.
"""

from typing import List, Optional
from core.config import settings
from core.constants import ModelProvider
from engines.llm.factory import LLMFactory
from engines.llm.structured import StructuredExtractor
from schemas.audio import MeetingMinutesDto, SpeakerSegment


class MeetingSummarizer:
    """Extracts executive summaries and action items from meeting transcriptions."""

    SYSTEM_PROMPT = (
        "Bạn là thư ký cuộc họp AI chuyên nghiệp. Hãy đọc bản ghi nội dung cuộc họp "
        "và tóm tắt lại các điểm chính, các quyết định đã thống nhất, và trích xuất danh sách đầu việc "
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

        llm = LLMFactory.get_provider(provider or settings.DEFAULT_LLM_PROVIDER)
        return await StructuredExtractor.extract(
            provider=llm,
            prompt=f"Nội dung bóc băng cuộc họp:\n{full_transcript}",
            schema=MeetingMinutesDto,
            system_instruction=cls.SYSTEM_PROMPT
        )
