"""
Exception Hierarchy for miai Platform.
Provides domain-specific exceptions mapped to standardized ErrorCodes.
"""

from typing import Any, Dict, Optional
from core.constants import ErrorCode


class BaseAIException(Exception):
    """Base exception class for all AI platform errors."""
    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.INTERNAL_SERVER_ERROR,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}


class SecurityException(BaseAIException):
    """Exception raised on security or authentication failures."""
    def __init__(
        self,
        message: str = "Unauthorized: Invalid request or insufficient permissions",
        error_code: ErrorCode = ErrorCode.UNAUTHORIZED,
        status_code: int = 401,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, error_code, status_code, details)


class PromptInjectionException(BaseAIException):
    """Exception raised when prompt injection attack is detected."""
    def __init__(
        self,
        message: str = "Prompt injection detected. Request rejected.",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=ErrorCode.PROMPT_INJECTION_DETECTED,
            status_code=400,
            details=details
        )


class LLMProviderException(BaseAIException):
    """Exception raised when LLM inference fails."""
    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.LLM_PROVIDER_ERROR,
        status_code: int = 502,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, error_code, status_code, details)


class RAGException(BaseAIException):
    """Exception raised during vector retrieval or document ingestion."""
    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.VECTOR_SEARCH_ERROR,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, error_code, status_code, details)


class VisionException(BaseAIException):
    """Exception raised during OCR or Vision processing."""
    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.OCR_PROCESSING_ERROR,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, error_code, status_code, details)


class UnsafeSqlException(BaseAIException):
    """Exception raised when generated SQL contains unsafe or non-read-only commands."""
    def __init__(
        self,
        message: str = "Unsafe SQL query: Only read-only SELECT statements are allowed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=ErrorCode.UNSAFE_SQL_QUERY_BLOCKED,
            status_code=400,
            details=details
        )


class AgentExecutionException(BaseAIException):
    """Exception raised during agent reasoning loop."""
    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.TOOL_EXECUTION_ERROR,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, error_code, status_code, details)
