"""
Chart Formatter & BI Insight Generator.
Transforms tabular query results into Apache ECharts options and executive insights.
"""

from typing import Dict, Any, List, Tuple
from schemas.analytics import SqlQueryResult, ChartDataResponse
from core.constants import ChartType


class ChartFormatter:
    """Produces ready-to-render ECharts options from SQL query results."""

    @classmethod
    def format_chart(
        cls,
        sql_res: SqlQueryResult,
        prompt: str,
        preferred_chart: ChartType = ChartType.BAR
    ) -> ChartDataResponse:
        """Converts query result rows into ECharts JSON and business insight."""
        if not sql_res.rows:
            return ChartDataResponse(
                sql_result=sql_res,
                chart_type=preferred_chart,
                echarts_config={"title": {"text": "Không có dữ liệu hiển thị"}},
                insights="Không tìm thấy bản ghi nào khớp với điều kiện truy vấn."
            )

        # Assume first column is category/X-axis, second column is numeric series
        cols = sql_res.columns
        x_col = cols[0] if len(cols) > 0 else "label"
        y_col = cols[1] if len(cols) > 1 else (cols[0] if cols else "value")

        x_data = [str(r.get(x_col, "")) for r in sql_res.rows]
        y_data = [float(r.get(y_col, 0)) for r in sql_res.rows]

        if preferred_chart == ChartType.PIE:
            pie_series_data = [{"name": str(r.get(x_col, "")), "value": float(r.get(y_col, 0))} for r in sql_res.rows]
            echarts_config = {
                "title": {"text": f"Biểu đồ phân bổ: {prompt}", "left": "center"},
                "tooltip": {"trigger": "item", "formatter": "{a} <br/>{b}: {c} ({d}%)"},
                "legend": {"orient": "vertical", "left": "left"},
                "series": [
                    {
                        "name": y_col,
                        "type": "pie",
                        "radius": "50%",
                        "data": pie_series_data,
                        "emphasis": {
                            "itemStyle": {
                                "shadowBlur": 10,
                                "shadowOffsetX": 0,
                                "shadowColor": "rgba(0, 0, 0, 0.5)"
                            }
                        }
                    }
                ]
            }
        else:
            # Bar or Line chart
            chart_type_str = "line" if preferred_chart == ChartType.LINE else "bar"
            echarts_config = {
                "title": {"text": f"Báo cáo phân tích: {prompt}"},
                "tooltip": {"trigger": "axis"},
                "xAxis": {"type": "category", "data": x_data},
                "yAxis": {"type": "value"},
                "series": [
                    {
                        "name": y_col,
                        "data": y_data,
                        "type": chart_type_str,
                        "smooth": True if chart_type_str == "line" else False
                    }
                ]
            }

        # Calculate insight summary
        total_val = sum(y_data)
        avg_val = total_val / len(y_data) if y_data else 0.0
        max_idx = y_data.index(max(y_data)) if y_data else 0
        peak_label = x_data[max_idx] if x_data else "N/A"

        insights = (
            f"Tổng giá trị ghi nhận đạt {total_val:,.0f} VND trên {len(sql_res.rows)} chu kỳ thống kê. "
            f"Giá trị trung bình mỗi chu kỳ đạt {avg_val:,.0f} VND. "
            f"Điểm cực đại đạt mức cao nhất vào kỳ '{peak_label}' với giá trị {max(y_data) if y_data else 0:,.0f} VND."
        )

        return ChartDataResponse(
            sql_result=sql_res,
            chart_type=preferred_chart,
            echarts_config=echarts_config,
            insights=insights
        )
