"""
Conversation Graph & State Management Module for CRM Quick Order Chat.
Manages multi-turn dialogue, confirmation states, and disambiguation branches.
"""

from typing import Dict, Any, Optional
from schemas.chat_crm import ChatParseRequest, DraftOrderResponse, ChatConfirmRequest
from engines.chat_crm.structured_extractor import structured_extractor
from engines.chat_crm.feedback_learner import feedback_learner
from core.telemetry import logger


class ConversationGraph:
    """State Graph Controller for Order Creation Dialogue."""

    def __init__(self):
        self._active_sessions: Dict[str, DraftOrderResponse] = {}

    async def process_user_turn(self, request: ChatParseRequest) -> DraftOrderResponse:
        """
        Processes incoming message, determines state transition, and returns draft.
        """
        draft = await structured_extractor.parse_message(request)
        self._active_sessions[draft.session_id] = draft
        logger.info("Processed chat order turn for session %s (Intent: %s, Conf: %s)", draft.session_id, draft.intent, draft.overall_confidence)
        return draft

    async def confirm_order_turn(self, request: ChatConfirmRequest) -> Dict[str, Any]:
        """
        Confirms draft order, records user corrections into feedback learning memory.
        """
        feedback_learner.process_confirmation(
            session_id=request.session_id,
            tenant_id=request.tenant_id,
            order_id=request.order_id,
            corrections=request.corrections
        )

        # Remove from active sessions
        self._active_sessions.pop(request.session_id, None)

        return {
            "session_id": request.session_id,
            "status": "ORDER_CREATED_AND_LEARNED",
            "message": "Đơn hàng đã được xác nhận tạo thành công và tri thức đã được cập nhật vào bộ nhớ gian hàng."
        }


conversation_graph = ConversationGraph()
