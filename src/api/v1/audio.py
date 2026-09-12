"""
Audio, Speech-to-Text, and Call Center QA API Endpoints.
"""

from fastapi import APIRouter, Depends
from schemas.audio import AudioTranscribeRequest, MeetingMinutesDto, CallScoreDto
from core.responses import ApiResponse
from engines.audio.whisper_stt import WhisperSttDriver
from engines.audio.meeting_summarizer import MeetingSummarizer
from engines.audio.call_center_evaluator import CallCenterEvaluator
from api.dependencies import get_current_user

router = APIRouter(prefix="/audio", tags=["Audio & Speech-to-Text"])
whisper_driver = WhisperSttDriver()


@router.post("/meeting-minutes", response_model=ApiResponse[MeetingMinutesDto], summary="Bóc băng và tóm tắt biên bản họp tự động")
async def generate_meeting_minutes(
    request: AudioTranscribeRequest,
    current_user: dict = Depends(get_current_user)
) -> ApiResponse[MeetingMinutesDto]:
    """Transcribes audio and extracts structured meeting minutes and action items."""
    segments = await whisper_driver.transcribe_audio(
        audio_bytes=b"",
        language=request.language,
        diarize=request.diarize_speakers
    )
    minutes = await MeetingSummarizer.summarize_meeting(segments)
    minutes.transcript_segments = segments
    return ApiResponse.success(data=minutes, message="Tóm tắt biên bản họp thành công")


@router.post("/call-quality", response_model=ApiResponse[CallScoreDto], summary="Giám sát và chấm điểm chất lượng cuộc gọi tổng đài")
async def evaluate_call_quality(
    request: AudioTranscribeRequest,
    current_user: dict = Depends(get_current_user)
) -> ApiResponse[CallScoreDto]:
    """Transcribes customer support call and scores compliance, forbidden words, and sentiment."""
    segments = await whisper_driver.transcribe_audio(
        audio_bytes=b"",
        language=request.language,
        diarize=True
    )
    score_dto = await CallCenterEvaluator.evaluate_call(segments)
    return ApiResponse.success(data=score_dto, message="Chấm điểm cuộc gọi thành công")
