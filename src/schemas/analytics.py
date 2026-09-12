"""
Text-to-SQL and Business Intelligence Analytics Schemas.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from core.constants import ChartType


class TextToSqlRequest(BaseModel):
    """User natural language query to translate into SQL."""
    prompt: str = Field(description="Natural language question in Vietnamese (e.g. Doanh thu theo tháng 2026)")
    database_target: str = Field(default="clickhouse", description="Target engine: clickhouse, postgres, oracle")
    tables_hint: Optional[List[str]] = Field(default=None, description="Optional subset of tables to consider")
    max_rows: int = Field(default=100, ge=1, le=1000, description="Max rows limit")
    execute_query: bool = Field(default=True, description="Whether to execute the query against the database")


class SqlQueryResult(BaseModel):
    """Result of SQL generation and safe execution."""
    generated_sql: str = Field(description="Generated SELECT statement")
    explanation: str = Field(description="Explanation of the SQL logic in Vietnamese")
    is_safe: bool = Field(default=True, description="Passed AST Read-Only Sandbox validation")
    columns: List[str] = Field(default_factory=list, description="Result column names")
    rows: List[Dict[str, Any]] = Field(default_factory=list, description="Result rows")
    row_count: int = Field(default=0, description="Number of rows returned")
    execution_time_ms: float = Field(default=0.0, description="Query execution duration")


class EChartsOption(BaseModel):
    """Configuration structure compatible with Apache ECharts."""
    title: Dict[str, Any] = Field(default_factory=dict)
    tooltip: Dict[str, Any] = Field(default_factory=lambda: {"trigger": "axis"})
    legend: Dict[str, Any] = Field(default_factory=dict)
    xAxis: Optional[Dict[str, Any]] = None
    yAxis: Optional[Dict[str, Any]] = None
    series: List[Dict[str, Any]] = Field(default_factory=list)


class ChartDataResponse(BaseModel):
    """Complete BI reporting response with SQL, Data, and ECharts Config."""
    sql_result: SqlQueryResult
    chart_type: ChartType
    echarts_config: Dict[str, Any] = Field(description="Ready-to-render ECharts JSON options")
    insights: str = Field(description="Business insights and recommendations summarized by AI")
