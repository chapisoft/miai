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


# ── Micro-Report Specific Contracts ──────────────────────────────────────────

class ReportParameterDto(BaseModel):
    """Đặc tả tham số nhập liệu động cho Standalone Report Viewer."""
    param_name: str = Field(description="Tên biến tham số trong SQL: start_date, status...")
    param_label: str = Field(description="Nhãn hiển thị tiếng Việt trên form")
    param_type: str = Field(default="TEXT", description="Kiểu điều khiển form: DATE, DATE_RANGE, SELECT, TEXT, NUMBER")
    default_value: Optional[str] = Field(default=None, description="Giá trị mặc định")
    options: Optional[List[str]] = Field(default=None, description="Danh sách lựa chọn nếu là kiểu SELECT")
    is_required: bool = Field(default=False, description="Bắt buộc nhập hay không")


class MicroReportCopilotRequest(BaseModel):
    """Yêu cầu tạo báo cáo từ câu hỏi tự nhiên gửi từ Micro-Report."""
    datasource_code: str = Field(description="Mã nguồn dữ liệu trong Micro-Report: DIP_DWH, CRM_DWH...")
    tenant_id: str = Field(description="Mã định danh người thuê: DIP_BHXH, MICRO_CRM, NATCASH...")
    dialect: str = Field(default="POSTGRESQL", description="Phương ngữ CSDL: POSTGRESQL, CLICKHOUSE, MYSQL, ORACLE")
    user_prompt: str = Field(description="Câu hỏi báo cáo bằng tiếng Việt tự nhiên")
    preferred_mode: Optional[str] = Field(default="SQL", description="Ưu tiên xuất định dạng SQL hay GUI JSON")
    max_rows: int = Field(default=1000, le=5000, description="Số dòng tối đa")


class MicroReportCopilotResponse(BaseModel):
    """Kết quả hoàn chỉnh sẵn sàng nạp vào Micro-Report và lưu vào RPT_TEMPLATES."""
    suggested_template_code: str = Field(description="Mã mẫu báo cáo đề xuất: RPT_DIP_REVENUE_2026")
    suggested_template_name: str = Field(description="Tên mẫu báo cáo tiếng Việt: Báo Cáo Doanh Thu...")
    mode: str = Field(default="SQL", description="Chế độ cấu hình: SQL hoặc GUI")
    config_sql: str = Field(description="Câu lệnh SQL tối ưu có gắn tham số :param_name")
    config_gui_json: Optional[Dict[str, Any]] = Field(default=None, description="Cấu hình JSON nếu chọn mode GUI")
    parameters_schema: List[ReportParameterDto] = Field(default_factory=list, description="Danh mục tham số form nhập liệu")
    chart_type: ChartType = Field(default=ChartType.BAR, description="Kiểu biểu đồ được chọn tự động")
    echarts_config: Dict[str, Any] = Field(default_factory=dict, description="Cấu hình ECharts Option JSON hoàn chỉnh")
    data_columns: List[str] = Field(default_factory=list, description="Danh sách tên các cột dữ liệu")
    data_rows: List[Dict[str, Any]] = Field(default_factory=list, description="Dữ liệu mẫu kết quả truy vấn")
    executive_summary: str = Field(description="Tóm tắt nhận định chỉ số kinh doanh dành cho lãnh đạo")
    transform_js: Optional[str] = Field(default=None, description="Hàm JavaScript hậu kỳ nếu có")
    execution_time_ms: float = Field(default=0.0, description="Thời gian xử lý")

