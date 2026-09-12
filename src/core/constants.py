"""
Global Enums and Constants for base-ai Platform.
100% Zero-Hardcode and Enum-driven architecture.
"""

from enum import Enum, unique


@unique
class ErrorCode(str, Enum):
    """System and Business Error Codes."""
    SUCCESS = "SUCCESS"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    INVALID_PARAMETERS = "INVALID_PARAMETERS"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    PROMPT_INJECTION_DETECTED = "PROMPT_INJECTION_DETECTED"
    SENSITIVE_CONTENT_BLOCKED = "SENSITIVE_CONTENT_BLOCKED"
    
    # LLM & AI Engine Errors
    LLM_PROVIDER_ERROR = "LLM_PROVIDER_ERROR"
    LLM_TIMEOUT = "LLM_TIMEOUT"
    LLM_CONTEXT_EXCEEDED = "LLM_CONTEXT_EXCEEDED"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
    
    # RAG & Retrieval Errors
    VECTOR_SEARCH_ERROR = "VECTOR_SEARCH_ERROR"
    DOCUMENT_INDEX_ERROR = "DOCUMENT_INDEX_ERROR"
    EMBEDDING_ERROR = "EMBEDDING_ERROR"
    
    # Vision & OCR Errors
    OCR_PROCESSING_ERROR = "OCR_PROCESSING_ERROR"
    HOMOGRAPHY_TRANSFORM_FAILED = "HOMOGRAPHY_TRANSFORM_FAILED"
    TEMPLATE_MATCH_FAILED = "TEMPLATE_MATCH_FAILED"
    
    # Text-to-SQL Errors
    SQL_SYNTAX_ERROR = "SQL_SYNTAX_ERROR"
    UNSAFE_SQL_QUERY_BLOCKED = "UNSAFE_SQL_QUERY_BLOCKED"
    DATABASE_EXECUTION_ERROR = "DATABASE_EXECUTION_ERROR"
    
    # Audio & STT Errors
    AUDIO_TRANSCRIBE_ERROR = "AUDIO_TRANSCRIBE_ERROR"
    
    # Agent & Tool Errors
    AGENT_MAX_ITERATIONS_REACHED = "AGENT_MAX_ITERATIONS_REACHED"
    TOOL_EXECUTION_ERROR = "TOOL_EXECUTION_ERROR"
    
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"


@unique
class ModelProvider(str, Enum):
    """Supported LLM and AI Providers."""
    OLLAMA = "OLLAMA"
    OPENAI = "OPENAI"
    GEMINI = "GEMINI"
    ANTHROPIC = "ANTHROPIC"
    DEEPSEEK = "DEEPSEEK"
    VLLM = "VLLM"
    CUSTOM = "CUSTOM"


@unique
class MessageRole(str, Enum):
    """Chat message roles."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@unique
class TaskType(str, Enum):
    """AI Task Classification."""
    CHAT = "CHAT"
    RAG = "RAG"
    EXTRACTION = "EXTRACTION"
    VISION_OCR = "VISION_OCR"
    TEXT_TO_SQL = "TEXT_TO_SQL"
    AUDIO_STT = "AUDIO_STT"
    AGENTIC_WORKFLOW = "AGENTIC_WORKFLOW"


@unique
class AgentStatus(str, Enum):
    """Lifecycle states for Autonomous Agents."""
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    WAITING_FOR_TOOL = "WAITING_FOR_TOOL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@unique
class VectorStoreType(str, Enum):
    """Supported Vector Store Backends."""
    PGVECTOR = "PGVECTOR"
    QDRANT = "QDRANT"
    MILVUS = "MILVUS"
    IN_MEMORY = "IN_MEMORY"


@unique
class ChartType(str, Enum):
    """Supported BI Chart Types."""
    BAR = "BAR"
    LINE = "LINE"
    PIE = "PIE"
    SCATTER = "SCATTER"
    RADAR = "RADAR"
    TABLE = "TABLE"


@unique
class FDIProfileType(str, Enum):
    """FDI Factory Language Profiles."""
    VIET_ENGLISH = "VIET_ENGLISH"
    VIET_CHINESE = "VIET_CHINESE"
    VIET_KOREAN = "VIET_KOREAN"
    VIET_JAPANESE = "VIET_JAPANESE"


@unique
class IdentityDocumentType(str, Enum):
    """Supported Identity Document Types."""
    CCCD_CHIP = "CCCD_CHIP"
    CMND_9 = "CMND_9"
    CMND_12 = "CMND_12"
    PASSPORT = "PASSPORT"
    DRIVER_LICENSE = "DRIVER_LICENSE"
    UNKNOWN = "UNKNOWN"


@unique
class OrderIntent(str, Enum):
    """CRM Chat Order Intent Types."""
    ORDER = "ORDER"
    PURCHASE = "PURCHASE"
    INQUIRY = "INQUIRY"


@unique
class PaymentMethod(str, Enum):
    """CRM Payment Methods."""
    CASH = "CASH"
    BANK_TRANSFER = "BANK_TRANSFER"
    COD = "COD"

