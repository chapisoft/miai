"""
Tool Registry and Dynamic Tool Calling Framework.
Supports `@ai_tool` decorator for automatic JSON Schema discovery.
"""

import inspect
import json
from typing import Callable, Dict, Any, List, Optional
from schemas.agent import ToolDefinition
from core.telemetry import logger


class ToolRegistry:
    """Central registry of executable agent tools."""

    _tools: Dict[str, Callable] = {}
    _definitions: Dict[str, ToolDefinition] = {}

    @classmethod
    def register(cls, name: str, description: str):
        """Decorator to register a python function as an agent tool."""
        def decorator(func: Callable):
            sig = inspect.signature(func)
            params_schema = {"type": "object", "properties": {}, "required": []}

            for param_name, param in sig.parameters.items():
                if param_name in ("self", "cls"):
                    continue
                param_type = "string"
                if param.annotation == int:
                    param_type = "integer"
                elif param.annotation == float:
                    param_type = "number"
                elif param.annotation == bool:
                    param_type = "boolean"
                elif param.annotation == dict:
                    param_type = "object"
                elif param.annotation == list:
                    param_type = "array"

                params_schema["properties"][param_name] = {
                    "type": param_type,
                    "description": f"Tham số {param_name}"
                }
                if param.default == inspect.Parameter.empty:
                    params_schema["required"].append(param_name)

            cls._tools[name] = func
            cls._definitions[name] = ToolDefinition(
                name=name,
                description=description,
                parameters=params_schema
            )
            return func
        return decorator

    @classmethod
    def get_tool(cls, name: str) -> Optional[Callable]:
        return cls._tools.get(name)

    @classmethod
    def get_all_definitions(cls, allowed_tools: Optional[List[str]] = None) -> List[ToolDefinition]:
        if allowed_tools:
            return [d for k, d in cls._definitions.items() if k in allowed_tools]
        return list(cls._definitions.values())

    @classmethod
    async def execute_tool(cls, name: str, arguments: Dict[str, Any]) -> str:
        """Executes a registered tool with provided keyword arguments."""
        tool_fn = cls.get_tool(name)
        if not tool_fn:
            return f"Lỗi: Không tìm thấy công cụ '{name}' trong hệ thống."

        try:
            if inspect.iscoroutinefunction(tool_fn):
                result = await tool_fn(**arguments)
            else:
                result = tool_fn(**arguments)
            return str(result)
        except Exception as e:
            logger.error("Tool execution failed", extra={"tool": name, "error": str(e)})
            return f"Lỗi khi thực thi công cụ '{name}': {str(e)}"


# Shortcut decorator
ai_tool = ToolRegistry.register


# ── Built-in Standard Enterprise Tools ────────────────────────────────────────

@ai_tool(
    name="calculator",
    description="Tính toán biểu thức toán học hoặc tỷ lệ chiết khấu tài chính chính xác (ví dụ: '15000000 * 0.08')"
)
def calculator(expression: str) -> str:
    try:
        # Safe eval restricted to math expressions
        allowed_chars = set("0123456789+-*/()., %")
        if not all(c in allowed_chars for c in expression.strip()):
            return "Lỗi: Biểu thức toán học chứa ký tự không hợp lệ."
        result = eval(expression.replace("%", "/100"))
        return f"Kết quả: {result}"
    except Exception as e:
        return f"Lỗi tính toán: {str(e)}"


@ai_tool(
    name="lookup_customer_crm",
    description="Tra cứu hồ sơ khách hàng 360 độ theo mã khách hàng hoặc tên doanh nghiệp"
)
def lookup_customer_crm(customer_identifier: str) -> str:
    # Simulated CRM retrieval from 15.7M records
    return json.dumps({
        "customer_id": customer_identifier,
        "company_name": "Công ty TNHH May Mặc & Xuất Nhập Khẩu Thái Bình Dương",
        "tax_code": "0108992341",
        "segment": "ENTERPRISE_VIP",
        "total_revenue_ytd": "1,450,000,000 VND",
        "active_contracts": 3,
        "payment_status": "GOOD_STANDING",
        "preferred_discount_rate": "8.5%"
    }, ensure_ascii=False)


@ai_tool(
    name="calculate_dynamic_discount",
    description="Tính toán mức chiết khấu và voucher cá nhân hóa tối thiểu để kích hoạt chuyển đổi đơn hàng"
)
def calculate_dynamic_discount(customer_id: str, cart_value: float) -> str:
    # Rule engine & ML scoring simulation
    if cart_value > 50000000:
        rate = 0.08
        voucher_code = "VIP_RESCUE_8"
    else:
        rate = 0.05
        voucher_code = "LOYALTY_5"

    discount_amount = cart_value * rate
    return json.dumps({
        "customer_id": customer_id,
        "recommended_discount_percent": f"{rate * 100}%",
        "discount_amount_vnd": discount_amount,
        "voucher_code": voucher_code,
        "expiry_hours": 4,
        "conversion_probability": "88.4%"
    }, ensure_ascii=False)
