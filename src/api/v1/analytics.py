"""
Text-to-SQL & Business Intelligence API Endpoints.
"""

from fastapi import APIRouter, Depends
from schemas.analytics import TextToSqlRequest, SqlQueryResult, ChartDataResponse
from core.responses import ApiResponse
from engines.text_to_sql.query_generator import SqlQueryGenerator
from engines.text_to_sql.executor import SqlExecutor
from engines.text_to_sql.chart_formatter import ChartFormatter
from core.constants import ChartType
from api.dependencies import get_current_user

router = APIRouter(prefix="/analytics", tags=["Text-to-SQL & BI Reporting"])
sql_generator = SqlQueryGenerator()


@router.post("/text-to-sql", response_model=ApiResponse[SqlQueryResult], summary="Chuyển đổi ngôn ngữ tự nhiên thành SQL an toàn")
async def generate_sql_query(
    request: TextToSqlRequest,
    current_user: dict = Depends(get_current_user)
) -> ApiResponse[SqlQueryResult]:
    """Translates Vietnamese prompt into safe Read-Only SQL statement and optionally executes it."""
    sql, explanation = await sql_generator.generate_sql(
        prompt=request.prompt,
        database_target=request.database_target,
        tables_hint=request.tables_hint,
        max_rows=request.max_rows
    )

    if request.execute_query:
        result = await SqlExecutor.execute_query(sql, explanation, database_target=request.database_target)
    else:
        result = SqlQueryResult(
            generated_sql=sql,
            explanation=explanation,
            is_safe=True
        )

    return ApiResponse.success(data=result, message="SQL query generated successfully")


@router.post("/chart", response_model=ApiResponse[ChartDataResponse], summary="Tự động sinh cấu hình biểu đồ ECharts và Insight báo cáo")
async def generate_chart_report(
    request: TextToSqlRequest,
    chart_type: ChartType = ChartType.BAR,
    current_user: dict = Depends(get_current_user)
) -> ApiResponse[ChartDataResponse]:
    """Executes Text-to-SQL and builds complete Apache ECharts options and executive insights."""
    sql, explanation = await sql_generator.generate_sql(
        prompt=request.prompt,
        database_target=request.database_target,
        tables_hint=request.tables_hint,
        max_rows=request.max_rows
    )
    query_result = await SqlExecutor.execute_query(sql, explanation, database_target=request.database_target)
    chart_res = ChartFormatter.format_chart(query_result, prompt=request.prompt, preferred_chart=chart_type)
    return ApiResponse.success(data=chart_res, message="Chart report generated successfully")
