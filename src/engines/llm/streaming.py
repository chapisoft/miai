"""
Streaming helper for Server-Sent Events (SSE) formatting.
"""

import json
from typing import AsyncGenerator
from schemas.chat import StreamChunk


class StreamHelper:
    """Formats StreamChunk objects into standard SSE data envelopes."""

    @staticmethod
    async def to_sse(generator: AsyncGenerator[StreamChunk, None]) -> AsyncGenerator[str, None]:
        """Converts an async generator of StreamChunks into SSE text/event-stream chunks."""
        async for chunk in generator:
            payload = json.dumps(chunk.model_dump())
            yield f"data: {payload}\n\n"
        yield "data: [DONE]\n\n"
