"""
ReAct (Reasoning - Action - Observation) Agent State Graph Loop.
Orchestrates autonomous multi-step reasoning, tool execution, and goal resolution.
"""

import time
import uuid
import json
from typing import List, Optional, Dict, Any
from schemas.agent import AgentRunRequest, AgentRunResponse, AgentStepDto
from core.constants import AgentStatus, ModelProvider
from engines.agent.state import AgentState
from engines.agent.tools import ToolRegistry
from engines.agent.memory import AgentMemory
from engines.llm.factory import LLMFactory
from engines.llm.structured import StructuredExtractor
from pydantic import BaseModel, Field
from core.telemetry import logger


class ReActDecision(BaseModel):
    thought: str = Field(description="Internal reasoning step in Vietnamese")
    action: Optional[str] = Field(default=None, description="Tool name to call or null if ready to answer")
    action_input: Optional[Dict[str, Any]] = Field(default=None, description="Arguments dictionary for the chosen tool")
    final_answer: Optional[str] = Field(default=None, description="Final comprehensive answer if task is completed")


class ReActAgentGraph:
    """Master ReAct execution graph."""

    @classmethod
    async def run(
        cls,
        request: AgentRunRequest,
        provider: Optional[ModelProvider] = None
    ) -> AgentRunResponse:
        """Executes the autonomous reasoning loop until goal is achieved or max steps reached."""
        start_time = time.time()
        session_id = request.session_id or f"session_{uuid.uuid4().hex[:8]}"
        state = AgentState(
            session_id=session_id,
            goal=request.prompt,
            status=AgentStatus.RUNNING,
            max_steps=request.max_steps
        )

        tools_def = ToolRegistry.get_all_definitions(request.available_tools)
        tools_desc = "\n".join([
            f"- `{t.name}`: {t.description}\n  Tham số: {json.dumps(t.parameters, ensure_ascii=False)}"
            for t in tools_def
        ])

        system_instruction = (
            "Bạn là một Trợ lý Tác nhân Tự trị Doanh nghiệp (Enterprise Autonomous AI Agent) thông minh. "
            "Nhiệm vụ của bạn là phân tích yêu cầu của người dùng, lập luận từng bước (Reasoning), "
            "gọi các công cụ cần thiết để thu thập dữ liệu (Action), và đưa ra câu trả lời cuối cùng chính xác nhất (Final Answer).\n\n"
            "DANH MỤC CÁC CÔNG CỤ SẴN CÓ:\n"
            f"{tools_desc}\n\n"
            "QUY TRÌNH RA QUYẾT ĐỊNH (ReAct Loop):\n"
            "1. Nếu cần dữ liệu để xử lý: Điền `thought`, `action` (tên công cụ), `action_input` (tham số), và để `final_answer = null`.\n"
            "2. Khi đã có đủ thông tin để kết luận: Điền `thought`, `final_answer` (lời giải đáp đầy đủ bằng tiếng Việt), và để `action = null`."
        )

        llm = LLMFactory.get_provider(provider or ModelProvider.OLLAMA)
        history_steps: List[AgentStepDto] = []

        while state.current_step < state.max_steps:
            state.current_step += 1
            
            # Build scratchpad
            scratchpad_text = ""
            for s in history_steps:
                scratchpad_text += f"\nBước {s.step_number}:\n- Suy nghĩ: {s.thought}\n"
                if s.action:
                    scratchpad_text += f"- Hành động: {s.action}({json.dumps(s.action_input or {}, ensure_ascii=False)})\n"
                    scratchpad_text += f"- Kết quả thu được: {s.observation}\n"

            user_prompt = (
                f"Mục tiêu cần hoàn thành: {state.goal}\n"
                f"Tiến trình đã thực hiện trước đó:{scratchpad_text if scratchpad_text else ' Chưa có'}\n\n"
                f"Hãy đưa ra quyết định cho bước {state.current_step}."
            )

            try:
                decision = await StructuredExtractor.extract(
                    provider=llm,
                    prompt=user_prompt,
                    schema=ReActDecision,
                    system_instruction=system_instruction
                )
            except Exception as e:
                logger.error("Agent step decision failed", extra={"step": state.current_step, "error": str(e)})
                state.status = AgentStatus.FAILED
                state.final_answer = f"Lỗi trong quá trình suy luận tại bước {state.current_step}: {str(e)}"
                break

            # If agent provided final answer
            if decision.final_answer or not decision.action:
                step_dto = AgentStepDto(
                    step_number=state.current_step,
                    thought=decision.thought,
                    action=None,
                    observation=None
                )
                history_steps.append(step_dto)
                await AgentMemory.save_step(session_id, step_dto)

                state.status = AgentStatus.COMPLETED
                state.final_answer = decision.final_answer or decision.thought
                break

            # Execute tool action
            observation = await ToolRegistry.execute_tool(decision.action, decision.action_input or {})

            step_dto = AgentStepDto(
                step_number=state.current_step,
                thought=decision.thought,
                action=decision.action,
                action_input=decision.action_input,
                observation=observation
            )
            history_steps.append(step_dto)
            await AgentMemory.save_step(session_id, step_dto)

        if state.status == AgentStatus.RUNNING:
            state.status = AgentStatus.FAILED
            state.final_answer = "Đã vượt quá số bước suy luận tối đa cho phép (Max Steps Exceeded)."

        duration = round(time.time() - start_time, 2)
        return AgentRunResponse(
            session_id=session_id,
            status=state.status,
            final_answer=state.final_answer or "N/A",
            steps=history_steps,
            total_steps=len(history_steps),
            execution_time_seconds=duration
        )
