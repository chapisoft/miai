"""
Standardized API Response Model matching Enterprise Backend Standards.
Integrates Enterprise Multilingual i18n support (VI, EN, ZH, JA, KO).
"""

from typing import Generic, Optional, TypeVar, Any, Dict
import time
from pydantic import BaseModel, Field
from core.constants import ErrorCode
from core.i18n import get_message

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Unified API Response envelope with multilingual localized message."""
    code: int = Field(default=200, description="HTTP status code")
    status: str = Field(default="SUCCESS", description="SUCCESS or ERROR")
    message: str = Field(default="Thành công", description="Localized status message")
    errorCode: Optional[ErrorCode] = Field(default=ErrorCode.SUCCESS, description="Enum Error Code")
    data: Optional[T] = Field(default=None, description="Payload data")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Pagination or diagnostic info")
    timestamp: int = Field(default_factory=lambda: int(time.time() * 1000), description="Epoch millisecond")

    @classmethod
    def success(
        cls,
        data: Optional[T] = None,
        message: str = "SUCCESS",
        metadata: Optional[Dict[str, Any]] = None,
        lang: Optional[str] = None,
    ) -> "ApiResponse[T]":
        translated_message = get_message(message, lang=lang)
        return cls(
            code=200,
            status="SUCCESS",
            message=translated_message,
            errorCode=ErrorCode.SUCCESS,
            data=data,
            metadata=metadata,
        )

    @classmethod
    def error(
        cls,
        message: str,
        error_code: ErrorCode = ErrorCode.INTERNAL_SERVER_ERROR,
        status_code: int = 500,
        metadata: Optional[Dict[str, Any]] = None,
        lang: Optional[str] = None,
    ) -> "ApiResponse[None]":
        translated_message = get_message(message, lang=lang)
        return cls(
            code=status_code,
            status="ERROR",
            message=translated_message,
            errorCode=error_code,
            data=None,
            metadata=metadata,
        )
