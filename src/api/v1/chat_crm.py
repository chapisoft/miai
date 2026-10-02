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


@router.post("/parse", response_model=ApiResponse[DraftOrderResponse], summary="Parse sales chat message and generate draft order")
async def parse_chat_message(
    request: ChatParseRequest,
    current_user: dict = Depends(get_current_user)
) -> ApiResponse[DraftOrderResponse]:
    """Parses natural language chat message into a structured DraftOrderResponse."""
    result = await conversation_graph.process_user_turn(request)
    return ApiResponse.success(data=result, message="Message parsed and order draft created successfully")


@router.post("/confirm", response_model=ApiResponse[Dict[str, Any]], summary="Confirm order and persist learned knowledge")
async def confirm_order(
    request: ChatConfirmRequest,
    current_user: dict = Depends(get_current_user)
) -> ApiResponse[Dict[str, Any]]:
    """Confirms draft order and records corrections into tenant learning memory."""
    result = await conversation_graph.confirm_order_turn(request)
    return ApiResponse.success(data=result, message="Order confirmed and knowledge updated successfully")


@router.get("/aliases", response_model=ApiResponse[AliasListResponse], summary="Get learned product slang and alias mappings")
async def get_tenant_aliases(
    app_id: str = Query(default="chapi", description="App / Service ID"),
    tenant_id: str = Query(default="shop-default-01", description="Tenant ID"),
    current_user: dict = Depends(get_current_user)
) -> ApiResponse[AliasListResponse]:
    """Retrieves all learned aliases and token mappings for the app and tenant."""
    aliases = feedback_learner.get_aliases(tenant_id=tenant_id, app_id=app_id)
    return ApiResponse.success(
        data=AliasListResponse(app_id=app_id, tenant_id=tenant_id, aliases=aliases),
        message="Product aliases retrieved successfully"
    )


@router.post("/aliases", response_model=ApiResponse[AliasItemDto], summary="Manually register alias abbreviation for tenant")
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
