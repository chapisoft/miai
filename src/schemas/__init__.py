"""
Pydantic Schemas & DTOs for base-ai Platform.
"""

from schemas.chat import ChatMessage, ChatRequest, ChatResponse, StreamChunk
from schemas.rag import DocumentCreate, DocumentChunk, SearchQuery, SearchResult, RAGResponse
from schemas.vision import OcrRequest, InvoiceDto, InvoiceItemDto, BoqTableDto, BoqRowDto, FdiFormDto
from schemas.analytics import TextToSqlRequest, SqlQueryResult, ChartDataResponse
from schemas.audio import AudioTranscribeRequest, MeetingMinutesDto, CallScoreDto
from schemas.agent import AgentRunRequest, AgentStepDto, AgentRunResponse, ToolCallDto

__all__ = [
    "ChatMessage", "ChatRequest", "ChatResponse", "StreamChunk",
    "DocumentCreate", "DocumentChunk", "SearchQuery", "SearchResult", "RAGResponse",
    "OcrRequest", "InvoiceDto", "InvoiceItemDto", "BoqTableDto", "BoqRowDto", "FdiFormDto",
    "TextToSqlRequest", "SqlQueryResult", "ChartDataResponse",
    "AudioTranscribeRequest", "MeetingMinutesDto", "CallScoreDto",
    "AgentRunRequest", "AgentStepDto", "AgentRunResponse", "ToolCallDto",
]
