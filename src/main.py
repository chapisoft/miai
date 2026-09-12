"""
Main Entrypoint for base-ai Enterprise Platform.
FastAPI Application with Swagger OpenAPI 3.0, Prometheus Metrics, and Standardized Error Handling.
"""

import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from core.config import settings
from core.constants import ErrorCode
from core.exceptions import BaseAIException
from core.responses import ApiResponse
from core.telemetry import logger, get_prometheus_metrics, HTTP_REQUESTS_TOTAL, HTTP_REQUEST_DURATION_SECONDS
from core.database import close_database_connections
from api.v1.router import api_v1_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle event manager for startup and graceful shutdown."""
    logger.info("Starting base-ai Enterprise AI Platform...", extra={"env": settings.APP_ENV, "port": settings.APP_PORT})
    yield
    logger.info("Shutting down base-ai platform, closing database pools...")
    await close_database_connections()


app = FastAPI(
    title=f"Enterprise AI Platform ({settings.APP_NAME})",
    description=(
        "Nền tảng Trí tuệ Nhân tạo Chuẩn Mực Doanh Nghiệp đa bộ máy: "
        "LLM Gateway, Hybrid RAG (BGE-M3 + BM25 + Reranker), Vision & FDI Form Station, "
        "Text-to-SQL Analytics Sandbox, Faster-Whisper STT, và ReAct Autonomous Agents."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# ── 1. CORS Middleware ───────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 2. Request Timing and Telemetry Middleware ──────────────────────────────
@app.middleware("http")
async def telemetry_middleware(request: Request, call_next):
    start_time = time.time()
    endpoint = request.url.path
    method = request.method

    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception as e:
        status_code = 500
        raise e
    finally:
        duration = time.time() - start_time
        HTTP_REQUESTS_TOTAL.labels(method=method, endpoint=endpoint, status_code=str(status_code)).inc()
        HTTP_REQUEST_DURATION_SECONDS.labels(method=method, endpoint=endpoint).observe(duration)

    return response


# ── 3. Global Exception Handlers ─────────────────────────────────────────────
@app.exception_handler(BaseAIException)
async def ai_exception_handler(request: Request, exc: BaseAIException):
    logger.warning("AI Platform Exception caught", extra={"error_code": exc.error_code.value, "message": exc.message})
    return JSONResponse(
        status_code=exc.status_code,
        content=ApiResponse.error(
            message=exc.message,
            error_code=exc.error_code,
            status_code=exc.status_code,
            metadata=exc.details
        ).model_dump()
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled Internal Server Error", extra={"error": str(exc), "path": request.url.path})
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ApiResponse.error(
            message="Đã xảy ra lỗi hệ thống nội bộ trên máy chủ AI",
            error_code=ErrorCode.INTERNAL_SERVER_ERROR,
            status_code=500,
            metadata={"detail": str(exc)}
        ).model_dump()
    )


# ── 4. Health and Metrics Endpoints ──────────────────────────────────────────
@app.get("/health", tags=["Health & Monitoring"], summary="Kiểm tra sức khỏe dịch vụ")
async def health_check():
    return {
        "status": "UP",
        "service": "base-ai",
        "env": settings.APP_ENV,
        "ollama_base_url": settings.OLLAMA_BASE_URL,
        "timestamp": int(time.time() * 1000)
    }


@app.get("/metrics", tags=["Health & Monitoring"], summary="Prometheus APM Metrics")
async def prometheus_metrics():
    metrics_data, content_type = get_prometheus_metrics()
    return Response(content=metrics_data, media_type=content_type)


@app.get("/", tags=["General"], summary="Cổng thông tin nền tảng base-ai")
async def root_info():
    return ApiResponse.success(
        data={
            "app_name": settings.APP_NAME,
            "version": "1.0.0",
            "documentation": "/docs",
            "openapi": "/openapi.json",
            "engines": [
                "Unified LLM Gateway (Ollama RTX 3060 / OpenAI / Gemini / DeepSeek)",
                "Hybrid RAG Engine (BGE-M3 Dense + BM25 Sparse + Reranker)",
                "Vision OCR & FDI Form Station Engine",
                "Text-to-SQL Analytics Sandbox & ECharts Generator",
                "Speech-to-Text Audio Engine (Faster-Whisper CUDA)",
                "Autonomous Agentic Workflow Engine (ReAct Graph & Tools)"
            ]
        },
        message="Chào mừng bạn đến với Nền tảng AI Chuẩn Mực Doanh Nghiệp (base-ai)"
    )


# ── 5. Master API V1 Router ──────────────────────────────────────────────────
app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG
    )
