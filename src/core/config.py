"""
Application Configuration Module using Pydantic BaseSettings.
Loads from environment variables and .env file.
"""

from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from core.constants import ModelProvider


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Application Information
    APP_ENV: str = Field(default="development", description="Environment: development, staging, production")
    APP_NAME: str = Field(default="base-ai", description="Application name")
    APP_HOST: str = Field(default="0.0.0.0", description="Server listening host")
    APP_PORT: int = Field(default=8000, description="Server listening port")
    API_V1_PREFIX: str = Field(default="/api/v1", description="API v1 prefix")
    DEBUG: bool = Field(default=False, description="Debug mode")

    # Security & Authentication
    ALLOWED_ORIGINS: List[str] = Field(default_factory=lambda: ["*"], description="CORS allowed origins")
    API_KEYS: List[str] = Field(default_factory=lambda: ["test-admin-key", "micro-dev-key"], description="Valid API Keys")
    JWT_SECRET_KEY: str = Field(default="super-secret-jwt-key-for-internal-micro-ai-service-2026", description="JWT Secret")
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT Algorithm")
    REQUIRE_AUTH: bool = Field(default=False, description="Enforce API Key or JWT authentication")

    # Unified LLM Provider Settings
    DEFAULT_LLM_PROVIDER: ModelProvider = Field(default=ModelProvider.VLLM, description="Default LLM Provider")
    
    # vLLM High-Throughput Inference Engine (RTX 3060 12GB Unified Gateway)
    VLLM_BASE_URL: str = Field(default="http://127.0.0.1:8000/v1", description="vLLM OpenAI-Compatible API URL")
    VLLM_DEFAULT_MODEL: str = Field(default="Qwen/Qwen2.5-7B-Instruct-AWQ", description="Default vLLM Model")

    # Local Ollama Core Engine (Legacy / Fallback)
    OLLAMA_BASE_URL: str = Field(default="http://127.0.0.1:11434", description="Ollama API URL")
    DEFAULT_LLM_MODEL: str = Field(default="qwen2.5:7b", description="Default Chat LLM model")
    DEFAULT_VISION_MODEL: str = Field(default="qwen2.5vl:7b", description="Default Vision LLM model")
    DEFAULT_EMBEDDING_MODEL: str = Field(default="bge-m3", description="Default Embedding model")
    DEFAULT_CODER_MODEL: str = Field(default="qwen2.5-coder:7b", description="Default Code/SQL model")
    EMBEDDING_PROVIDER: ModelProvider = Field(default=ModelProvider.LOCAL_CPU, description="Default Embedding Provider")

    # Cloud AI Providers
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API Key")
    OPENAI_BASE_URL: str = Field(default="https://api.openai.com/v1", description="OpenAI base URL")
    GEMINI_API_KEY: Optional[str] = Field(default=None, description="Google Gemini API Key")
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, description="Anthropic API Key")
    DEEPSEEK_API_KEY: Optional[str] = Field(default=None, description="DeepSeek API Key")

    # PostgreSQL Database & pgvector
    POSTGRES_HOST: str = Field(default="127.0.0.1", description="PostgreSQL host")
    POSTGRES_PORT: int = Field(default=5432, description="PostgreSQL port")
    POSTGRES_DB: str = Field(default="micro_db", description="PostgreSQL database name")
    POSTGRES_USER: str = Field(default="micro", description="PostgreSQL username")
    POSTGRES_PASSWORD: Optional[str] = Field(default=None, description="PostgreSQL password")
    POSTGRES_POOL_SIZE: int = Field(default=20, description="Connection pool size")
    POSTGRES_MAX_OVERFLOW: int = Field(default=10, description="Max overflow connections")

    @property
    def async_database_url(self) -> str:
        from urllib.parse import quote_plus
        user = quote_plus(self.POSTGRES_USER) if self.POSTGRES_USER else ""
        pwd = f":{quote_plus(self.POSTGRES_PASSWORD)}" if self.POSTGRES_PASSWORD else ""
        return f"postgresql+asyncpg://{user}{pwd}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Redis Cache & Session
    REDIS_HOST: str = Field(default="127.0.0.1", description="Redis host")
    REDIS_PORT: int = Field(default=6379, description="Redis port")
    REDIS_PASSWORD: Optional[str] = Field(default=None, description="Redis password")
    REDIS_DB: int = Field(default=0, description="Redis database index")

    @property
    def redis_url(self) -> str:
        from urllib.parse import quote_plus
        pwd = f":{quote_plus(self.REDIS_PASSWORD)}@" if self.REDIS_PASSWORD else ""
        return f"redis://{pwd}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # ClickHouse OLAP
    CLICKHOUSE_HOST: str = Field(default="127.0.0.1", description="ClickHouse host")
    CLICKHOUSE_PORT: int = Field(default=8123, description="ClickHouse HTTP port")
    CLICKHOUSE_DB: str = Field(default="analytics_db", description="ClickHouse database")
    CLICKHOUSE_USER: str = Field(default="micro", description="ClickHouse user")
    CLICKHOUSE_PASSWORD: Optional[str] = Field(default=None, description="ClickHouse password")

    # Observability & Guardrails
    PROMETHEUS_ENABLED: bool = Field(default=True, description="Enable Prometheus metrics endpoint")
    LOG_LEVEL: str = Field(default="INFO", description="Log level: DEBUG, INFO, WARNING, ERROR")
    LOG_FORMAT: str = Field(default="ecs_json", description="Log format: text or ecs_json")
    MAX_TOKENS_PER_REQUEST: int = Field(default=4096, description="Max tokens generated")
    ENABLE_PROMPT_GUARD: bool = Field(default=True, description="Enable prompt injection detection")
    ENABLE_PII_REDACTION: bool = Field(default=True, description="Mask sensitive PII data")

    # Face Analysis Engine (UniFace)
    UNIFACE_CACHE_DIR: Optional[str] = Field(default=None, description="Custom directory for UniFace ONNX models cache")
    DEFAULT_FACE_DETECTOR: str = Field(default="SCRFD", description="Default Face Detector: SCRFD, RETINAFACE, CENTERFACE, YOLOV8_FACE")
    DEFAULT_FACE_RECOGNIZER: str = Field(default="ADAFACE_IR50", description="Default Face Recognizer: ADAFACE_IR50, ARCFACE_RESNET50, ARCFACE_MOBILENET")
    FACE_SIMILARITY_THRESHOLD: float = Field(default=0.60, description="Cosine similarity threshold for identity match")
    FACE_LIVENESS_THRESHOLD: float = Field(default=0.80, description="Confidence threshold for liveness verification")
    FACE_QUALITY_MIN_THRESHOLD: float = Field(default=0.50, description="Minimum eDifFIQA score to accept face image")
    FACE_EXECUTION_PROVIDER: str = Field(default="CUDAExecutionProvider", description="Execution provider for Face Models: CUDAExecutionProvider, TensorrtExecutionProvider, CPUExecutionProvider")
    FACE_DEVICE: str = Field(default="cuda", description="Device for face embedding and matching: cuda, cpu")



settings = Settings()
