"""
Autonomous Agent & Tool Calling API Endpoints.
"""

from fastapi import APIRouter, Depends
from schemas.agent import AgentRunRequest, AgentRunResponse
from core.responses import ApiResponse
from engines.agent.react_graph import ReActAgentGraph
from api.dependencies import get_current_user

router = APIRouter(prefix="/agent", tags=["Autonomous Agent & Tool Calling"])


@router.post("/run", response_model=ApiResponse[AgentRunResponse], summary="Khởi chạy tác vụ Tác nhân Tự trị (ReAct Workflow)")
async def run_autonomous_agent(
    request: AgentRunRequest,
    current_user: dict = Depends(get_current_user)
) -> ApiResponse[AgentRunResponse]:
    """
    Executes autonomous reasoning loop with dynamic tool execution.
    """
    result = await ReActAgentGraph.run(request)
    return ApiResponse.success(data=result, message="Thực thi tác nhân tự trị hoàn tất")
