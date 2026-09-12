"""
Agent Execution State and Step Container.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from core.constants import AgentStatus
from schemas.agent import AgentStepDto, ToolCallDto


class AgentState(BaseModel):
    """Holds the current state of an ongoing autonomous agent task."""
    session_id: str
    goal: str
    status: AgentStatus = Field(default=AgentStatus.IDLE)
    steps: List[AgentStepDto] = Field(default_factory=list)
    current_step: int = Field(default=0)
    max_steps: int = Field(default=10)
    scratchpad: Dict[str, Any] = Field(default_factory=dict)
    final_answer: Optional[str] = None
    error_message: Optional[str] = None
