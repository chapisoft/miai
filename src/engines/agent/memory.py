"""
Agent Memory Manager.
Handles Short-Term session history in Redis and Long-Term semantic context in Vector Store.
"""

from typing import List, Dict, Any, Optional
import json
from schemas.agent import AgentStepDto
from core.database import get_redis_client
from core.telemetry import logger


class AgentMemory:
    """Manages short-term and long-term memory for multi-turn agent execution."""

    _in_memory_store: Dict[str, List[AgentStepDto]] = {}

    @classmethod
    async def save_step(cls, session_id: str, step: AgentStepDto) -> None:
        """Appends a reasoning step to the session memory."""
        if session_id not in cls._in_memory_store:
            cls._in_memory_store[session_id] = []
        cls._in_memory_store[session_id].append(step)

        # Attempt to save to Redis if available
        try:
            redis = await get_redis_client()
            key = f"agent:memory:{session_id}"
            await redis.rpush(key, json.dumps(step.model_dump()))
            await redis.expire(key, 86400) # 24h TTL
        except Exception:
            pass

    @classmethod
    async def get_history(cls, session_id: str) -> List[AgentStepDto]:
        """Retrieves past steps for a session."""
        try:
            redis = await get_redis_client()
            key = f"agent:memory:{session_id}"
            raw_items = await redis.lrange(key, 0, -1)
            if raw_items:
                return [AgentStepDto.model_validate_json(item) for item in raw_items]
        except Exception:
            pass

        return cls._in_memory_store.get(session_id, [])
