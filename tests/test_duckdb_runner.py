import pytest
from engine.duckdb_runner import DuckDBRunner


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

ORDERS_DDL = """
CREATE TABLE orders (
    order_id    INTEGER,
    customer_id INTEGER,
    amount      DOUBLE
);
CREATE TABLE customers (
    customer_id INTEGER,
    name        VARCHAR
)
"""

CLEAN_ORDERS = [
    {"order_id": 1, "customer_id": 10, "amount": 100.0},
    {"order_id": 2, "customer_id": 11, "amount": 200.0},
    {"order_id": 3, "customer_id": 12, "amount": 300.0},
]

CLEAN_CUSTOMERS = [
    {"customer_id": 10, "name": "Alice"},
    {"customer_id": 11, "name": "Bob"},
    {"customer_id": 12, "name": "Carol"},
]


@pytest.fixture
def runner():
    r = DuckDBRunner()
    yield r
    r.close()


# ---------------------------------------------------------------------------
# Basic schema and insert
# ---------------------------------------------------------------------------

def test_setup_schema_and_insert(runner):
    runner.setup_schema(ORDERS_DDL)
    runner.insert_rows("orders", CLEAN_ORDERS)
    result = runner.run_query("SELECT COUNT(*) AS n FROM orders")
    assert result[0]["n"] == 3


def test_empty_insert_is_noop(runner):
    runner.setup_schema(ORDERS_DDL)
    runner.insert_rows("orders", [])
    result = runner.run_query("SELECT COUNT(*) AS n FROM orders")
    assert result[0]["n"] == 0


def test_returns_empty_list_on_no_rows(runner):
    runner.setup_schema(ORDERS_DDL)
    result = runner.run_query("SELECT * FROM orders WHERE order_id = 999")
    assert result == []


# ---------------------------------------------------------------------------
# Aggregation on clean data
# ---------------------------------------------------------------------------

def test_sum_on_clean_data(runner):
    runner.setup_schema(ORDERS_DDL)
    runner.insert_rows("orders", CLEAN_ORDERS)
    result = runner.run_query("SELECT SUM(amount) AS total FROM orders")
    assert result[0]["total"] == pytest.approx(600.0)


# ---------------------------------------------------------------------------
# Adversarial: duplicate rows inflate GROUP BY
# ---------------------------------------------------------------------------

def test_duplicate_rows_inflate_sum(runner):
    """
    This is the core adversarial pattern for Agent 2 to generate.
    Duplicating order rows before a GROUP BY inflates the aggregate.
    A query that does not deduplicate will return wrong totals.
    """
    runner.setup_schema(ORDERS_DDL)

    # Duplicate order_id=1 — simulates an upstream pipeline emitting the
    # same event twice, which is the most common real-world cause of inflated revenue
    duplicate_orders = CLEAN_ORDERS + [
        {"order_id": 1, "customer_id": 10, "amount": 100.0},
    ]
    runner.insert_rows("orders", duplicate_orders)

    naive_query = "SELECT SUM(amount) AS total FROM orders"
    result = runner.run_query(naive_query)

    # Total is 700, not 600 — query does not handle duplicates
    assert result[0]["total"] == pytest.approx(700.0)

    # A correct query would deduplicate first
    safe_query = """
        SELECT SUM(amount) AS total
        FROM (SELECT DISTINCT order_id, amount FROM orders)
    """
    safe_result = runner.run_query(safe_query)
    assert safe_result[0]["total"] == pytest.approx(600.0)


# ---------------------------------------------------------------------------
# Adversarial: NULL propagation through LEFT JOIN drops rows silently
# ---------------------------------------------------------------------------

def test_null_propagation_left_join(runner):
    """
    customer_id=12 has no matching customer row.
    A naive INNER JOIN silently drops that order.
    The query returns 2 rows instead of 3.
    """
    runner.setup_schema(ORDERS_DDL)
    runner.insert_rows("orders", CLEAN_ORDERS)

    # Intentionally omit customer 12
    partial_customers = [
        {"customer_id": 10, "name": "Alice"},
        {"customer_id": 11, "name": "Bob"},
    ]
    runner.insert_rows("customers", partial_customers)

    inner_join_query = """
        SELECT o.order_id, c.name, o.amount
        FROM orders o
        INNER JOIN customers c ON o.customer_id = c.customer_id
    """
    result = runner.run_query(inner_join_query)
    # Order 3 (Carol, $300) silently dropped
    assert len(result) == 2

    left_join_query = """
        SELECT o.order_id, c.name, o.amount
        FROM orders o
        LEFT JOIN customers c ON o.customer_id = c.customer_id
    """
    left_result = runner.run_query(left_join_query)
    assert len(left_result) == 3


# ---------------------------------------------------------------------------
# Convenience method
# ---------------------------------------------------------------------------

def test_load_and_run(runner):
    result = runner.load_and_run(
        ddl=ORDERS_DDL,
        rows_by_table={
            "orders": CLEAN_ORDERS,
            "customers": CLEAN_CUSTOMERS,
        },
        query="""
            SELECT c.name, SUM(o.amount) AS total
            FROM orders o
            JOIN customers c ON o.customer_id = c.customer_id
            GROUP BY c.name
            ORDER BY c.name
        """,
    )
    assert len(result) == 3
    assert result[0]["name"] == "Alice"
    assert result[0]["total"] == pytest.approx(100.0)


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------

def test_reset_clears_state(runner):
    runner.setup_schema(ORDERS_DDL)
    runner.insert_rows("orders", CLEAN_ORDERS)
    runner.reset()

    # After reset, table should not exist
    with pytest.raises(Exception):
        runner.run_query("SELECT * FROM orders")
