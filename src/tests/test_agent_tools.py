"""
Unit Tests for Agent Tool Registry and Dynamic Execution.
"""

import pytest
import json
from engines.agent.tools import ToolRegistry, ai_tool


def test_tool_registry_registration():
    @ai_tool(name="test_multiplier", description="Multiplies two numbers")
    def test_multiplier(a: int, b: int) -> int:
        return a * b

    tool_fn = ToolRegistry.get_tool("test_multiplier")
    assert tool_fn is not None

    defs = ToolRegistry.get_all_definitions(["test_multiplier"])
    assert len(defs) == 1
    assert defs[0].name == "test_multiplier"
    assert "a" in defs[0].parameters["properties"]


@pytest.mark.asyncio
async def test_tool_execution_calculator():
    output = await ToolRegistry.execute_tool("calculator", {"expression": "2500000 * 0.1"})
    assert "250000.0" in output


@pytest.mark.asyncio
async def test_tool_execution_crm_lookup():
    output = await ToolRegistry.execute_tool("lookup_customer_crm", {"customer_identifier": "CUST_99"})
    data = json.loads(output)
    assert data["customer_id"] == "CUST_99"
    assert "ENTERPRISE_VIP" in data["segment"]


@pytest.mark.asyncio
async def test_tool_execution_dynamic_discount():
    output = await ToolRegistry.execute_tool(
        "calculate_dynamic_discount",
        {"customer_id": "CUST_99", "cart_value": 60000000.0}
    )
    data = json.loads(output)
    assert data["recommended_discount_percent"] == "8.0%"
    assert data["voucher_code"] == "VIP_RESCUE_8"
