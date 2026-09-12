"""
Audio Processing, Speech-to-Text and Call Center Scoring Schemas.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class AudioTranscribeRequest(BaseModel):
    """Payload to request audio speech-to-text processing."""
    audio_base64: Optional[str] = Field(default=None, description="Base64 encoded audio string")
    audio_url: Optional[str] = Field(default=None, description="Remote audio file URL")
    language: str = Field(default="vi", description="Language code: vi, en, zh, ko, ja")
    task: str = Field(default="transcribe", description="Task: transcribe or translate")
    diarize_speakers: bool = Field(default=True, description="Identify different speakers")


class SpeakerSegment(BaseModel):
    speaker: str = Field(description="Speaker label (e.g. Speaker 1, Agent, Customer)")
    start_time: float = Field(description="Start time in seconds")
    end_time: float = Field(description="End time in seconds")
    text: str = Field(description="Spoken text in this segment")


class ActionItemDto(BaseModel):
    assignee: str = Field(description="Người chịu trách nhiệm")
    task_description: str = Field(description="Nội dung công việc được giao")
    deadline: Optional[str] = Field(default=None, description="Thời hạn hoàn thành nếu có")


class MeetingMinutesDto(BaseModel):
    """Meeting summarization and minutes extractor."""
    title: str = Field(description="Tiêu đề cuộc họp")
    meeting_date: Optional[str] = Field(default=None, description="Ngày họp")
    attendees: List[str] = Field(default_factory=list, description="Danh sách người tham dự")
    summary: str = Field(description="Tóm tắt nội dung cuộc họp")
    key_decisions: List[str] = Field(default_factory=list, description="Các quyết định trọng yếu")
    action_items: List[ActionItemDto] = Field(default_factory=list, description="Bảng phân công nhiệm vụ")
    transcript_segments: List[SpeakerSegment] = Field(default_factory=list, description="Chi tiết bóc băng theo người nói")


class CallScoreDto(BaseModel):
    """Call Center quality scoring and sentiment evaluation."""
    overall_score: float = Field(ge=0.0, le=100.0, description="Điểm đánh giá tổng thể (thang 100)")
    greeting_compliance: bool = Field(default=True, description="Đạt chuẩn lời chào đầu cuộc gọi")
    closing_compliance: bool = Field(default=True, description="Đạt chuẩn lời cảm ơn kết thúc cuộc gọi")
    forbidden_words_detected: List[str] = Field(default_factory=list, description="Từ ngữ cấm hoặc vi phạm quy chế")
    agent_sentiment: str = Field(description="Thái độ của điện thoại viên (Ân cần, Chuyên nghiệp, v.v.)")
    customer_sentiment: str = Field(description="Cảm xúc khách hàng (Hài lòng, Trung lập, Bức xúc)")
    feedback_notes: str = Field(description="Nhận xét chi tiết và đề xuất cải thiện")
