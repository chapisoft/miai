"""
Unit Tests for Text-to-SQL AST Sandbox Security Validator.
"""

import pytest
from engines.text_to_sql.ast_validator import AstSqlValidator
from core.exceptions import UnsafeSqlException


def test_sql_validator_valid_select():
    sql = "SELECT order_id, total_amount FROM fact_sales_orders WHERE order_date >= '2026-01-01'"
    validated = AstSqlValidator.validate_select_only(sql, max_rows=100)
    assert "SELECT" in validated
    assert "LIMIT 100" in validated


def test_sql_validator_existing_limit():
    sql = "SELECT product_name FROM dim_products LIMIT 10"
    validated = AstSqlValidator.validate_select_only(sql, max_rows=100)
    assert validated.count("LIMIT") == 1
    assert "LIMIT 10" in validated


def test_sql_validator_block_drop_table():
    sql = "DROP TABLE fact_sales_orders"
    with pytest.raises(UnsafeSqlException):
        AstSqlValidator.validate_select_only(sql)


def test_sql_validator_block_delete():
    sql = "DELETE FROM fact_sales_orders WHERE order_id = '123'"
    with pytest.raises(UnsafeSqlException):
        AstSqlValidator.validate_select_only(sql)


def test_sql_validator_block_stacked_queries():
    sql = "SELECT * FROM dim_products; DROP TABLE fact_sales_orders;"
    with pytest.raises(UnsafeSqlException):
        AstSqlValidator.validate_select_only(sql)


def test_sql_validator_block_insert():
    sql = "INSERT INTO dim_products (product_code) VALUES ('SKU_01')"
    with pytest.raises(UnsafeSqlException):
        AstSqlValidator.validate_select_only(sql)
