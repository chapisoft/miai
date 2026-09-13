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
    """State Graph Controller for Order Creation Dialogue with Multi-App & Multi-Tenant Support."""

    def __init__(self):
        self._active_sessions: Dict[str, DraftOrderResponse] = {}

    async def process_user_turn(self, request: ChatParseRequest) -> DraftOrderResponse:
        """
        Processes incoming message, determines state transition, and returns draft.
        """
        draft = await structured_extractor.parse_message(request)
        session_key = f"{request.app_id}:{request.tenant_id}:{draft.session_id}"
        self._active_sessions[session_key] = draft
        logger.info("Processed chat order turn for session %s (App: %s, Tenant: %s, Intent: %s, Conf: %s)", draft.session_id, request.app_id, request.tenant_id, draft.intent, draft.overall_confidence)
        return draft

    async def confirm_order_turn(self, request: ChatConfirmRequest) -> Dict[str, Any]:
        """
        Confirms draft order, records user corrections into feedback learning memory.
        """
        feedback_learner.process_confirmation(
            session_id=request.session_id,
            tenant_id=request.tenant_id,
            order_id=request.order_id,
            corrections=request.corrections,
            app_id=request.app_id
        )

        # Remove from active sessions
        session_key = f"{request.app_id}:{request.tenant_id}:{request.session_id}"
        self._active_sessions.pop(session_key, None)

        return {
            "session_id": request.session_id,
            "app_id": request.app_id,
            "tenant_id": request.tenant_id,
            "status": "ORDER_CREATED_AND_LEARNED",
            "message": "Đơn hàng đã được xác nhận tạo thành công và tri thức đã được cập nhật vào bộ nhớ gian hàng."
        }


conversation_graph = ConversationGraph()
