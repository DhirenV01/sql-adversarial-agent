import pytest
from agents.schema_analyzer import analyze_schema
from agents.data_generator import generate_test_case
from agents.validator import validate_test_case
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
SELECT customer_id, SUM(amount) AS total_revenue
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
    ],
}


# ---------------------------------------------------------------------------
# Shared fixtures — one full pipeline execution reused across tests
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def schema_analysis():
    return analyze_schema(ORDERS_DDL)


@pytest.fixture(scope="module")
def duplicate_rows_result(schema_analysis):
    """Full pipeline: analyze → generate → validate for duplicate_rows failure mode."""
    test_case = generate_test_case(
        ddl=ORDERS_DDL,
        query=TEST_QUERY,
        failure_mode=FailureMode.DUPLICATE_ROWS_BEFORE_GROUP_BY,
        schema_analysis=schema_analysis,
        clean_data=CLEAN_DATA,
    )
    return validate_test_case(
        ddl=ORDERS_DDL,
        query=TEST_QUERY,
        clean_data=CLEAN_DATA,
        test_case=test_case,
    )


# ---------------------------------------------------------------------------
# Structure validation
# ---------------------------------------------------------------------------

def test_returns_test_case_result(duplicate_rows_result):
    assert isinstance(duplicate_rows_result, TestCaseResult)


def test_result_has_clean_and_adversarial_results(duplicate_rows_result):
    assert isinstance(duplicate_rows_result.clean_result, list)
    assert isinstance(duplicate_rows_result.adversarial_result, list)
    assert len(duplicate_rows_result.clean_result) > 0
    assert len(duplicate_rows_result.adversarial_result) > 0


# ---------------------------------------------------------------------------
# Result quality
# ---------------------------------------------------------------------------

def test_explanation_is_populated(duplicate_rows_result):
    assert duplicate_rows_result.explanation is not None
    assert len(duplicate_rows_result.explanation) > 0
    assert duplicate_rows_result.delta_summary is not None
    assert len(duplicate_rows_result.delta_summary) > 0


def test_duplicate_rows_causes_failure(duplicate_rows_result):
    assert duplicate_rows_result.passed is False


def test_failure_mode_is_preserved_in_result(duplicate_rows_result):
    assert duplicate_rows_result.failure_mode == FailureMode.DUPLICATE_ROWS_BEFORE_GROUP_BY.value


def test_clean_result_matches_expected_aggregation(duplicate_rows_result):
    """Clean data should produce known totals: customer 10 = 300, customer 11 = 300."""
    clean = duplicate_rows_result.clean_result
    totals = {r["customer_id"]: r["total_revenue"] for r in clean}
    assert totals[10] == pytest.approx(300.0)
    assert totals[11] == pytest.approx(300.0)


def test_adversarial_result_differs_from_clean(duplicate_rows_result):
    """The adversarial result must differ from clean — that's the whole point."""
    assert duplicate_rows_result.clean_result != duplicate_rows_result.adversarial_result
