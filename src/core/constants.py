"""
Global Enums and Constants for miai Platform.
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
    
    # Face Biometrics & Identity Errors
    FACE_DETECTION_ERROR = "FACE_DETECTION_ERROR"
    FACE_RECOGNITION_ERROR = "FACE_RECOGNITION_ERROR"
    FACE_SPOOF_DETECTED = "FACE_SPOOF_DETECTED"
    FACE_QUALITY_TOO_LOW = "FACE_QUALITY_TOO_LOW"
    
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
    LOCAL_CPU = "LOCAL_CPU"
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
    FACE_BIOMETRICS = "FACE_BIOMETRICS"


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
    HORIZONTAL_BAR = "HORIZONTAL_BAR"
    LINE = "LINE"
    AREA_LINE = "AREA_LINE"
    PIE = "PIE"
    DOUGHNUT = "DOUGHNUT"
    STACKED_BAR = "STACKED_BAR"
    SCATTER = "SCATTER"
    RADAR = "RADAR"
    TABLE = "TABLE"


@unique
class DatabaseDialect(str, Enum):
    """Supported SQL Database Dialects."""
    POSTGRESQL = "POSTGRESQL"
    CLICKHOUSE = "CLICKHOUSE"
    MYSQL = "MYSQL"
    ORACLE = "ORACLE"
    SQLSERVER = "SQLSERVER"


@unique
class ReportMode(str, Enum):
    """Micro-Report Template Modes."""
    GUI = "GUI"
    SQL = "SQL"


@unique
class ParameterType(str, Enum):
    """Micro-Report Form Parameter Types."""
    DATE = "DATE"
    DATE_RANGE = "DATE_RANGE"
    SELECT = "SELECT"
    TEXT = "TEXT"
    NUMBER = "NUMBER"


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


@unique
class FaceDetectorType(str, Enum):
    """Supported Face Detection Models."""
    SCRFD = "SCRFD"
    RETINAFACE = "RETINAFACE"
    CENTERFACE = "CENTERFACE"
    YOLOV8_FACE = "YOLOV8_FACE"


@unique
class FaceRecognizerType(str, Enum):
    """Supported Face Recognition / Embedding Models."""
    ADAFACE_IR50 = "ADAFACE_IR50"
    ARCFACE_RESNET50 = "ARCFACE_RESNET50"
    ARCFACE_MOBILENET = "ARCFACE_MOBILENET"
    EDGEFACE_XXS = "EDGEFACE_XXS"


@unique
class FaceAnonymizeMethod(str, Enum):
    """Privacy Anonymization Methods."""
    PIXELATE = "pixelate"
    GAUSSIAN = "gaussian"
    BLACKOUT = "blackout"
    ELLIPTICAL = "elliptical"


@unique
class LivenessDecision(str, Enum):
    """Anti-Spoofing Verdicts."""
    REAL = "REAL"
    FAKE = "FAKE"
    UNCERTAIN = "UNCERTAIN"


@unique
class ClassroomROIType(str, Enum):
    """Classroom Spatial Region of Interest."""
    TEACHER = "TEACHER"
    STUDENT = "STUDENT"
    ALL = "ALL"


@unique
class VisitorStatus(str, Enum):
    """Visitor Identity Validity States."""
    APPROVED = "APPROVED"
    PENDING = "PENDING"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


@unique
class SubjectType(str, Enum):
    """Subject Classification for Smart Campus."""
    STUDENT = "STUDENT"
    TEACHER = "TEACHER"
    STAFF = "STAFF"
    VISITOR = "VISITOR"


@unique
class FaceFeedbackCode(str, Enum):
    """Zero-Hardcode Standard Verification & Enrollment Feedback Codes."""
    FACE_NOT_DETECTED = "FACE_NOT_DETECTED"
    MULTIPLE_FACES_DETECTED = "MULTIPLE_FACES_DETECTED"
    MASK_DETECTED = "MASK_DETECTED"
    SUNGLASSES_DETECTED = "SUNGLASSES_DETECTED"
    HEAD_PITCH_UNBALANCED = "HEAD_PITCH_UNBALANCED"
    HEAD_TURN_STRAIGHT_REQUIRED = "HEAD_TURN_STRAIGHT_REQUIRED"
    HEAD_TURN_LEFT_REQUIRED = "HEAD_TURN_LEFT_REQUIRED"
    HEAD_TURN_RIGHT_REQUIRED = "HEAD_TURN_RIGHT_REQUIRED"
    HEAD_TURN_LEFT_TOO_DEEP = "HEAD_TURN_LEFT_TOO_DEEP"
    HEAD_TURN_RIGHT_TOO_DEEP = "HEAD_TURN_RIGHT_TOO_DEEP"
    QUALITY_SCORE_TOO_LOW = "QUALITY_SCORE_TOO_LOW"
    ENROLL_SUCCESS = "ENROLL_SUCCESS"
    EXTRACTION_ERROR = "EXTRACTION_ERROR"


