"""
Observability, Telemetry, and Structured JSON ECS Logging.
Integrates with ELK Stack (Elasticsearch/Logstash) and Prometheus.
"""

import logging
import sys
import time
from typing import Optional
from pythonjsonlogger import jsonlogger
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from core.config import settings

# ── 1. Structured JSON ECS Logger ───────────────────────────────────────────

def setup_logger(name: str = "base-ai") -> logging.Logger:
    """Configures structured logger outputting Elastic Common Schema (ECS) format."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
    
    # Avoid duplicate handlers if re-initialized
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        if settings.LOG_FORMAT == "ecs_json":
            formatter = jsonlogger.JsonFormatter(
                fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
                rename_fields={"asctime": "@timestamp", "levelname": "log.level", "name": "service.name"}
            )
        else:
            formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(name)s: %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
    return logger


logger = setup_logger("base-ai")

# ── 2. Prometheus Metrics ───────────────────────────────────────────────────

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests received",
    ["method", "endpoint", "status_code"]
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

LLM_INFERENCE_DURATION_SECONDS = Histogram(
    "llm_inference_duration_seconds",
    "LLM inference duration in seconds",
    ["provider", "model", "task_type"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0)
)

LLM_TOKENS_TOTAL = Counter(
    "llm_tokens_total",
    "Total tokens processed by LLM provider",
    ["provider", "model", "token_type"] # prompt, completion
)

OCR_PAGES_PROCESSED_TOTAL = Counter(
    "ocr_pages_processed_total",
    "Total pages processed by OCR Engine",
    ["profile", "status"]
)


def get_prometheus_metrics() -> tuple[bytes, str]:
    """Returns the Prometheus metrics payload and content type."""
    return generate_latest(), CONTENT_TYPE_LATEST
