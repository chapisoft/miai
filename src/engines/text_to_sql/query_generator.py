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
    explanation: str = Field(description="Explanation of the query logic. MUST match the exact language of the user prompt (Vietnamese for Vietnamese prompt, English for English prompt, etc.)")


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
            f"You are an enterprise Database and Business Intelligence Expert for {database_target.upper()}.\n"
            "Data Dictionary Schema:\n"
            f"{schema_context}\n\n"
            "MANDATORY RULES:\n"
            "1. Generate ONLY a single pure `SELECT` read-only query.\n"
            "2. Use exact table and column names as defined in the Schema.\n"
            "3. Always use proper table aliases and meaningful column names for aggregations (SUM, COUNT, AVG...).\n"
            "4. Add an appropriate `LIMIT` clause.\n"
            "5. LANGUAGE MATCHING: The `explanation` field MUST strictly match the exact language of the user prompt "
            "(e.g., if the user prompt is in Vietnamese, write the explanation in Vietnamese; if in English, write in English)."
        )

        llm = LLMFactory.get_provider(provider or ModelProvider.OLLAMA, model_override=self.model)

        structured_res = await StructuredExtractor.extract(
            provider=llm,
            prompt=f"User Query / Prompt: {prompt}",
            schema=SqlGenResult,
            system_instruction=system_instruction,
            model=self.model
        )

        # Enforce AST Security Validation
        safe_sql = AstSqlValidator.validate_select_only(structured_res.sql, max_rows=max_rows)
        return safe_sql, structured_res.explanation
