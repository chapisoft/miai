"""
Schema Inspector & Metadata Indexer.
Provides database dictionary schemas to LLM prompts for accurate table joining and column selection.
"""

from typing import Dict, List, Any, Optional


class SchemaInspector:
    """Manages schema metadata and prompts formatting for enterprise databases."""

    # Built-in sample metadata for ERP/CRM and ClickHouse
    MOCK_SCHEMA_REGISTRY = {
        "clickhouse": {
            "fact_sales_orders": {
                "description": "Bảng lưu trữ giao dịch đơn hàng bán lẻ và bán buôn theo thời gian thực",
                "columns": [
                    {"name": "order_id", "type": "String", "comment": "Mã đơn hàng duy nhất"},
                    {"name": "order_date", "type": "Date", "comment": "Ngày tạo đơn hàng"},
                    {"name": "customer_id", "type": "String", "comment": "Mã khách hàng"},
                    {"name": "branch_code", "type": "String", "comment": "Mã chi nhánh bán hàng"},
                    {"name": "total_amount", "type": "Float64", "comment": "Tổng tiền thanh toán (VND)"},
                    {"name": "discount_amount", "type": "Float64", "comment": "Số tiền chiết khấu giảm giá"},
                    {"name": "status", "type": "String", "comment": "Trạng thái đơn: COMPLETED, CANCELLED, PENDING"}
                ]
            },
            "dim_products": {
                "description": "Bảng danh mục sản phẩm và ngành hàng",
                "columns": [
                    {"name": "product_code", "type": "String", "comment": "Mã SKU sản phẩm"},
                    {"name": "product_name", "type": "String", "comment": "Tên sản phẩm"},
                    {"name": "category_name", "type": "String", "comment": "Tên ngành hàng / Nhóm hàng"},
                    {"name": "unit_cost", "type": "Float64", "comment": "Giá vốn bình quân"}
                ]
            }
        }
    }

    @classmethod
    def get_formatted_schema_context(
        cls,
        database: str = "clickhouse",
        tables: Optional[List[str]] = None
    ) -> str:
        """Formats the schema into a concise context prompt for LLM SQL generation."""
        db_schema = cls.MOCK_SCHEMA_REGISTRY.get(database, cls.MOCK_SCHEMA_REGISTRY["clickhouse"])
        lines = []

        for table_name, table_info in db_schema.items():
            if tables and table_name not in tables:
                continue

            lines.append(f"Bảng `{table_name}` ({table_info['description']}):")
            for col in table_info["columns"]:
                lines.append(f"  - `{col['name']}` ({col['type']}): {col['comment']}")
            lines.append("")

        return "\n".join(lines)
