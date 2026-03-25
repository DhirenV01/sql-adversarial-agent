import pytest
from agents.schema_analyzer import analyze_schema
from agents.data_generator import generate_test_case
from agents.validator import validate_test_case
from models.test_case import AdversarialTestCase
from models.schema import FailureMode
from models.report import TestCaseResult

ORDERS_DDL = """
CREATE TABLE orders (
    order_id INTEGER,
    customer_id INTEGER,
    amount DOUBLE,
    order_date DATE
);
CREATE TABLE customers (
    customer_id INTEGER,
    name VARCHAR,
    email VARCHAR
)
"""

TEST_QUERY = """
SELECT customer_id, SUM(amount)  AS total_revenue
FROM orders
GROUP BY customer_id
"""

CLEAN_DATA = {
    "orders": [
        {"order_id": 1, "customer_id": 10, "amount": 100.0, "order_date": "2024-01-01"},
        {"order_id": 2, "customer_id": 10, "amount": 200.0, "order_date": "2024-01-02"},
        {"order_id": 3, "customer_id": 11, "amount": 300.0, "order_date": "2024-01-03"},
    ],
    "customers": [
        {"customer_id": 10, "name": "Alice", "email": "alice@example.com"},
        {"customer_id": 11, "name": "Bob", "email": "bob@example.com"},
    ]
}

def test_returns_test_case_restult():
    schema_analysis = analyze_schema(ORDERS_DDL)
    test_case = generate_test_case(
        ddl=ORDERS_DDL,
        query=TEST_QUERY,
        failure_mode=FailureMode.DUPLICATE_ROWS_BEFORE_GROUP_BY,
        schema_analysis=schema_analysis,
    )
    result = validate_test_case(
        ddl=ORDERS_DDL,
        query=TEST_QUERY,
        clean_data=CLEAN_DATA,
        test_case=test_case,
    )
    assert isinstance(result, TestCaseResult)

def test_result_has_clean_and_adversarial_results():
    schema_analysis = analyze_schema(ORDERS_DDL)
    test_case = generate_test_case(
        ddl=ORDERS_DDL,
        query=TEST_QUERY,
        failure_mode=FailureMode.DUPLICATE_ROWS_BEFORE_GROUP_BY,
        schema_analysis=schema_analysis,
    )
    result = validate_test_case(
        ddl=ORDERS_DDL,
        query=TEST_QUERY,
        clean_data=CLEAN_DATA,
        test_case=test_case,
    )
    assert isinstance(result.clean_result, list)
    assert isinstance(result.adversarial_result, list)
    assert len(result.clean_result) > 0
    assert len(result.adversarial_result) > 0

def test_explanation_is_populated():
    schema_analysis = analyze_schema(ORDERS_DDL)
    test_case = generate_test_case(
        ddl=ORDERS_DDL,
        query=TEST_QUERY,
        failure_mode=FailureMode.DUPLICATE_ROWS_BEFORE_GROUP_BY,
        schema_analysis=schema_analysis,
    )
    result = validate_test_case(
        ddl=ORDERS_DDL,
        query=TEST_QUERY,
        clean_data=CLEAN_DATA,
        test_case=test_case,
    )
    assert result.explanation is not None
    assert len(result.explanation) > 0
    assert result.delta_summary is not None
    assert len(result.delta_summary) > 0

def test_duplicate_rows_causes_failure():
    schema_analysis = analyze_schema(ORDERS_DDL)
    test_case = generate_test_case(
        ddl=ORDERS_DDL,
        query=TEST_QUERY,
        failure_mode=FailureMode.DUPLICATE_ROWS_BEFORE_GROUP_BY,
        schema_analysis=schema_analysis,    
    )
    result = validate_test_case(
        ddl=ORDERS_DDL,
        query=TEST_QUERY,
        clean_data=CLEAN_DATA,
        test_case=test_case,
    )
    assert result.passed == False