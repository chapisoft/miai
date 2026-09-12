"""
SQL Query Generator.
Translates Vietnamese natural language prompts into optimized SQL using Qwen2.5-Coder.
"""

from typing import Optional, List, Tuple
from core.config import settings
from core.constants import ModelProvider, MessageRole
from engines.llm.factory import LLMFactory
from engines.llm.structured import StructuredExtractor
from engines.text_to_sql.schema_inspector import SchemaInspector
from engines.text_to_sql.ast_validator import AstSqlValidator
from schemas.chat import ChatRequest, ChatMessage
from pydantic import BaseModel, Field


class SqlGenResult(BaseModel):
    sql: str = Field(description="Generated pure SQL SELECT query")
    explanation: str = Field(description="Explanation of the query logic in Vietnamese")


class SqlQueryGenerator:
    """Generates validated SQL queries from natural language questions."""

    def __init__(self, model_override: Optional[str] = None):
        self.model = model_override or settings.DEFAULT_CODER_MODEL

    async def generate_sql(
        self,
        prompt: str,
        database_target: str = "clickhouse",
        tables_hint: Optional[List[str]] = None,
        max_rows: int = 100,
        provider: Optional[ModelProvider] = None
    ) -> Tuple[str, str]:
        """
        Returns (validated_sql, explanation).
        """
        schema_context = SchemaInspector.get_formatted_schema_context(database_target, tables_hint)

        system_instruction = (
            f"Bạn là chuyên gia cơ sở dữ liệu và phân tích dữ liệu kinh doanh (BI Expert) trên hệ thống {database_target.upper()}. "
            "Dưới đây là cấu trúc từ điển dữ liệu (Data Dictionary):\n"
            f"{schema_context}\n\n"
            "QUY TẮC BẮT BUỘC:\n"
            "1. Chỉ sinh DUY NHẤT câu truy vấn `SELECT` đọc dữ liệu.\n"
            "2. Sử dụng tên bảng và tên cột chính xác như trong Schema.\n"
            "3. Luôn sử dụng bí danh bảng (Alias) và tên cột rõ ràng cho các hàm gom nhóm (SUM, COUNT, AVG...).\n"
            "4. Thêm mệnh đề `LIMIT` phù hợp."
        )

        llm = LLMFactory.get_provider(provider or ModelProvider.OLLAMA, model_override=self.model)

        structured_res = await StructuredExtractor.extract(
            provider=llm,
            prompt=f"Câu hỏi nghiệp vụ: {prompt}",
            schema=SqlGenResult,
            system_instruction=system_instruction,
            model=self.model
        )

        # Enforce AST Security Validation
        safe_sql = AstSqlValidator.validate_select_only(structured_res.sql, max_rows=max_rows)
        return safe_sql, structured_res.explanation
