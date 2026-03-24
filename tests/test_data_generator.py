from agents.schema_analyzer import analyze_schema
from agents.data_generator import generate_test_case
from models.schema import FailureMode
from models.test_case import AdversarialTestCase

ORDERS_DDL = """
CREATE TABLE orders (
    order_id    INTEGER,
    customer_id INTEGER,
    amount      DOUBLE,
    order_date  DATE
);
CREATE TABLE customers (
    customer_id INTEGER,
    name        VARCHAR,
    email       VARCHAR
)
"""

TEST_QUERY = """
SELECT customer_id, SUM(amount) AS total_revenue
FROM orders
GROUP BY customer_id
"""

def test_returns_test_case_object():
    schema_analysis = analyze_schema(ORDERS_DDL)
    result = generate_test_case(
        ddl=ORDERS_DDL,
        query=TEST_QUERY,
        failure_mode=FailureMode.DUPLICATE_ROWS_BEFORE_GROUP_BY,
        schema_analysis=schema_analysis
    )
    assert isinstance(result, AdversarialTestCase)

def test_failure_mode_matches_requested():
    schema_analysis = analyze_schema(ORDERS_DDL)
    result = generate_test_case(
        ddl=ORDERS_DDL,
        query=TEST_QUERY,
        failure_mode=FailureMode.DUPLICATE_ROWS_BEFORE_GROUP_BY,
        schema_analysis=schema_analysis
    )
    assert result.failure_mode == FailureMode.DUPLICATE_ROWS_BEFORE_GROUP_BY

def test_adversarial_data_targets_correct_table():
    schema_analysis = analyze_schema(ORDERS_DDL)
    result = generate_test_case(
        ddl=ORDERS_DDL,
        query=TEST_QUERY,
        failure_mode=FailureMode.DUPLICATE_ROWS_BEFORE_GROUP_BY,
        schema_analysis=schema_analysis,
    )
    table_names = [d.table_name for d in result.adversarial_data]
    assert "orders" in table_names

def test_adversarial_rows_are_populated():
    schema_analysis = analyze_schema(ORDERS_DDL)
    result = generate_test_case(
        ddl=ORDERS_DDL,
        query=TEST_QUERY,
        failure_mode=FailureMode.DUPLICATE_ROWS_BEFORE_GROUP_BY,
        schema_analysis=schema_analysis,
    )
    for adversarial in result.adversarial_data:
        assert len(adversarial.rows) > 0

def test_expected_trap_is_populated():
    schema_analysis = analyze_schema(ORDERS_DDL)
    result = generate_test_case(
        ddl=ORDERS_DDL,
        query=TEST_QUERY,
        failure_mode=FailureMode.DUPLICATE_ROWS_BEFORE_GROUP_BY,
        schema_analysis=schema_analysis,
    )
    assert result.expected_trap is not None
    assert len(result.expected_trap) > 0

def test_generates_null_propagation_test_case():
    schema_analysis = analyze_schema(ORDERS_DDL)
    result = generate_test_case(
        ddl=ORDERS_DDL,
        query=TEST_QUERY,
        failure_mode=FailureMode.NULL_PROPAGATION_LEFT_JOIN,
        schema_analysis=schema_analysis,
    )
    assert isinstance(result, AdversarialTestCase)
    assert result.failure_mode == FailureMode.NULL_PROPAGATION_LEFT_JOIN
   