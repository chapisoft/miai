"""
Autonomous Agent and Tool Calling Schemas.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from core.constants import AgentStatus


class ToolDefinition(BaseModel):
    name: str = Field(description="Unique tool function name")
    description: str = Field(description="Documentation explaining what the tool does")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="JSON Schema for parameters")


class ToolCallDto(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
    output: Optional[str] = None
    status: str = Field(default="SUCCESS")


class AgentStepDto(BaseModel):
    step_number: int
    thought: str = Field(description="Agent internal reasoning")
    action: Optional[str] = Field(default=None, description="Action or tool called")
    action_input: Optional[Dict[str, Any]] = None
    observation: Optional[str] = Field(default=None, description="Output from the executed action")


class AgentRunRequest(BaseModel):
    prompt: str = Field(description="User high-level goal or task instruction")
    session_id: Optional[str] = Field(default=None, description="Session ID for short-term memory")
    available_tools: Optional[List[str]] = Field(default=None, description="Allowed tool names subset")
    max_steps: int = Field(default=10, ge=1, le=30, description="Max reasoning loops")


class AgentRunResponse(BaseModel):
    session_id: str
    status: AgentStatus
    final_answer: str
    steps: List[AgentStepDto] = Field(default_factory=list)
    total_steps: int = Field(default=0)
    execution_time_seconds: float = Field(default=0.0)
