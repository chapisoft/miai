"""
Standardized API Response Model matching Enterprise Backend Standards.
"""

from typing import Generic, Optional, TypeVar, Any, Dict
import time
from pydantic import BaseModel, Field
from core.constants import ErrorCode

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Unified API Response envelope."""
    code: int = Field(default=200, description="HTTP status code")
    status: str = Field(default="SUCCESS", description="SUCCESS or ERROR")
    message: str = Field(default="Thành công", description="User-friendly localized message")
    errorCode: Optional[ErrorCode] = Field(default=ErrorCode.SUCCESS, description="Enum Error Code")
    data: Optional[T] = Field(default=None, description="Payload data")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Pagination or diagnostic info")
    timestamp: int = Field(default_factory=lambda: int(time.time() * 1000), description="Epoch millisecond")

    @classmethod
    def success(
        cls,
        data: Optional[T] = None,
        message: str = "Thực thi thành công",
        metadata: Optional[Dict[str, Any]] = None
    ) -> "ApiResponse[T]":
        return cls(
            code=200,
            status="SUCCESS",
            message=message,
            errorCode=ErrorCode.SUCCESS,
            data=data,
            metadata=metadata
        )

    @classmethod
    def error(
        cls,
        message: str,
        error_code: ErrorCode = ErrorCode.INTERNAL_SERVER_ERROR,
        status_code: int = 500,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "ApiResponse[None]":
        return cls(
            code=status_code,
            status="ERROR",
            message=message,
            errorCode=error_code,
            data=None,
            metadata=metadata
        )
