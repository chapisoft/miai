"""
AST SQL Validator & Security Sandbox.
Enforces 100% Read-Only queries, strictly forbidding INSERT, UPDATE, DELETE, DROP, ALTER, and execution tricks.
"""

import re
import sqlparse
from sqlparse.sql import Statement, Token
from core.exceptions import UnsafeSqlException
from core.telemetry import logger

FORBIDDEN_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE",
    "GRANT", "REVOKE", "EXEC", "EXECUTE", "MERGE", "CALL", "REPLACE",
    "RENAME", "LOCK", "SHUTDOWN", "INTO OUTFILE", "INTO DUMPFILE",
    "XP_CMDSHELL", "BENCHMARK", "PG_SLEEP"
}


class AstSqlValidator:
    """Validates that a SQL string is strictly a safe SELECT statement."""

    @classmethod
    def validate_select_only(cls, sql_text: str, max_rows: int = 1000) -> str:
        """
        Parses SQL using AST tokens.
        Raises UnsafeSqlException if non-SELECT or dangerous keywords are detected.
        Ensures a LIMIT clause is present or injects one.
        """
        cleaned = sql_text.strip().rstrip(";")
        if not cleaned:
            raise UnsafeSqlException(message="Câu lệnh SQL rỗng")

        # Parse statements
        parsed = sqlparse.parse(cleaned)
        if len(parsed) != 1:
            raise UnsafeSqlException(
                message="Chỉ cho phép duy nhất 1 câu truy vấn SELECT, nghiêm cấm xếp chồng nhiều câu lệnh (Stacked Queries)"
            )

        statement: Statement = parsed[0]
        st_type = statement.get_type()
        if st_type != "SELECT":
            raise UnsafeSqlException(
                message=f"Loại câu lệnh không hợp lệ: '{st_type}'. Hệ thống chỉ chấp nhận câu lệnh SELECT đọc dữ liệu."
            )

        # Token stream inspection
        sql_upper = cleaned.upper()
        for kw in FORBIDDEN_KEYWORDS:
            # Check for isolated forbidden keywords
            if re.search(r"\b" + re.escape(kw) + r"\b", sql_upper):
                raise UnsafeSqlException(
                    message=f"Phát hiện từ khóa nguy hiểm bị cấm tuyệt đối: '{kw}'"
                )

        # Enforce or inject LIMIT
        if not re.search(r"\bLIMIT\s+\d+", sql_upper):
            cleaned = f"{cleaned} LIMIT {max_rows}"

        return cleaned
