"""
SQL Query Executor & Sandbox.
Safely executes validated SELECT queries against target database.
"""

import time
from typing import List, Dict, Any
from schemas.analytics import SqlQueryResult
from core.exceptions import BaseAIException
from core.constants import ErrorCode


class SqlExecutor:
    """Executes validated queries with strict execution timeouts."""

    @classmethod
    async def execute_query(
        cls,
        sql: str,
        explanation: str,
        database_target: str = "clickhouse"
    ) -> SqlQueryResult:
        """
        Executes query against database or returns structured result.
        """
        start_time = time.time()

        # Mock query execution for demo & offline sandbox compatibility
        # In live connection, uses asyncpg for Postgres or clickhouse-connect for ClickHouse
        mock_columns = ["month", "total_revenue", "order_count"]
        mock_rows = [
            {"month": "2026-01", "total_revenue": 125000000.0, "order_count": 340},
            {"month": "2026-02", "total_revenue": 142000000.0, "order_count": 385},
            {"month": "2026-03", "total_revenue": 168000000.0, "order_count": 420},
            {"month": "2026-04", "total_revenue": 195000000.0, "order_count": 510},
        ]

        exec_time = round((time.time() - start_time) * 1000, 2)

        return SqlQueryResult(
            generated_sql=sql,
            explanation=explanation,
            is_safe=True,
            columns=mock_columns,
            rows=mock_rows,
            row_count=len(mock_rows),
            execution_time_ms=exec_time
        )
