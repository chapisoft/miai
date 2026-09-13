"""
CRM Quick Order Chat Assistant API Router.
RESTful endpoints for natural language quick order parsing, confirmation, and self-learning management.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, Query
from schemas.chat_crm import (
    ChatParseRequest,
    DraftOrderResponse,
    ChatConfirmRequest,
    AliasCreateRequest,
    AliasListResponse,
    AliasItemDto,
)
from core.responses import ApiResponse
from engines.chat_crm.conversation_graph import conversation_graph
from engines.chat_crm.feedback_learner import feedback_learner
from api.dependencies import get_current_user

router = APIRouter(prefix="/chat-crm", tags=["CRM AI Quick Order Chat"])


@router.post("/parse", response_model=ApiResponse[DraftOrderResponse], summary="Đọc hiểu tin nhắn bán hàng và tạo đơn nháp")
async def parse_chat_message(
    request: ChatParseRequest,
    current_user: dict = Depends(get_current_user)
) -> ApiResponse[DraftOrderResponse]:
    """Parses natural language chat message into a structured DraftOrderResponse."""
    result = await conversation_graph.process_user_turn(request)
    return ApiResponse.success(data=result, message="Message parsed and order draft created successfully")


@router.post("/confirm", response_model=ApiResponse[Dict[str, Any]], summary="Xác nhận tạo đơn và lưu vết tri thức học tập")
async def confirm_order(
    request: ChatConfirmRequest,
    current_user: dict = Depends(get_current_user)
) -> ApiResponse[Dict[str, Any]]:
    """Confirms draft order and records corrections into tenant learning memory."""
    result = await conversation_graph.confirm_order_turn(request)
    return ApiResponse.success(data=result, message="Order confirmed and knowledge updated successfully")


@router.get("/aliases", response_model=ApiResponse[AliasListResponse], summary="Lấy danh mục từ lóng và ánh xạ đã học của gian hàng")
async def get_tenant_aliases(
    app_id: str = Query(default="chapi", description="ID ứng dụng / dịch vụ"),
    tenant_id: str = Query(default="shop-default-01", description="ID gian hàng"),
    current_user: dict = Depends(get_current_user)
) -> ApiResponse[AliasListResponse]:
    """Retrieves all learned aliases and token mappings for the app and tenant."""
    aliases = feedback_learner.get_aliases(tenant_id=tenant_id, app_id=app_id)
    return ApiResponse.success(
        data=AliasListResponse(app_id=app_id, tenant_id=tenant_id, aliases=aliases),
        message="Product aliases retrieved successfully"
    )


@router.post("/aliases", response_model=ApiResponse[AliasItemDto], summary="Thêm thủ công từ lóng / cấu hình viết tắt cho gian hàng")
async def create_tenant_alias(
    request: AliasCreateRequest,
    current_user: dict = Depends(get_current_user)
) -> ApiResponse[AliasItemDto]:
    """Manually registers an alias for an app and tenant."""
    new_alias = feedback_learner.record_alias(
        app_id=request.app_id,
        tenant_id=request.tenant_id,
        raw_token=request.raw_token,
        target_type=request.target_type,
        target_id=request.target_id,
        target_name=request.target_name
    )
    return ApiResponse.success(data=new_alias, message="Product alias added successfully")
