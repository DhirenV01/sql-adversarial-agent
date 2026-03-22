import pytest
from agents.schema_analyzer import analyze_schema
from models.schema import SchemaAnalysis, FailureMode

SIMPLE_FACT_TABLE = """"

CREATE TABLE orders (
    order_id    INTEGER,
    customer_id INTEGER,
    amount      DOUBLE
    order_date DATE 
    );
CREATE TABLE customers (
    customer_id INTEGER,
    name        VARCHAR
    email      VARCHAR)
)
"""

MANY_TO_MANY_BRIDGE = """
CREATE TABLE students (
    student_id INTEGER,
    name       VARCHAR
);
CREATE TABLE courses (
    course_id INTEGER,
    title     VARCHAR
);
CREATE TABLE enrollments (
    student_id INTEGER,
    course_id  INTEGER,
    enrolled_at DATE 
)
"""

SCD_TYPE_2 = """
CREATE TABLE dim_employee (
    employee_id INTEGER,
    name        VARCHAR,
    department  VARCHAR,
    effective_from DATE,
    effective_to DATE
    is_current BOOLEAN
)
"""

def test_returns_schema_analysis_object():
    result = analyze_schema(SIMPLE_FACT_TABLE)
    assert isinstance(result, SchemaAnalysis)   

def test_identifies_correct_number_of_tables():
    result = analyze_schema(SIMPLE_FACT_TABLE)
    assert len(result.tables) == 2

def test_table_names_are_present():
    result = analyze_schema(SIMPLE_FACT_TABLE)
    table_names = [t.table_name for t in result.tables]
    assert "orders" in table_names
    assert "customers" in table_names

def test_grain_is_populated():
    result = analyze_schema(SIMPLE_FACT_TABLE)
    for table in result.tables:
        assert table.grain is not None
        assert len(table.grain) > 0
    
def test_reccommends_failure_modes():
    result = analyze_schema(SIMPLE_FACT_TABLE)
    assert len(result.recommended_failure_modes) > 0
    for mode in result.recommended_failure_modes:
        assert mode in FailureMode.__members__.values()

def test_risk_summary_is_populated():
    result = analyze_schema(SIMPLE_FACT_TABLE)
    assert result.risk_summary is not None
    assert len(result.risk_summary) > 0

def test_detects_many_to_many_risk():
    result = analyze_schema(MANY_TO_MANY_BRIDGE)
    assert FailureMode.MANY_TO_MANY_JOIN_FANOUT in result.recommended_failure_modes

def test_detects_scd_type_2_risk():
    result = analyze_schema(SCD_TYPE_2)
    assert FailureMode.SCD_TYPE_2_OVERLAP in result.recommended_failure_modes

def test_risky_columns_have_required_fields():
    result = analyze_schema(SIMPLE_FACT_TABLE)
    for table in result.tables:
        for col in table.risky_columns:
            assert col.column_name is not None
            assert col.data_type is not None
            assert col.risk_reason is not None
            assert col.associated_failure_mode in FailureMode.__members__.values()
