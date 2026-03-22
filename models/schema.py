from pydantic import BaseModel
from typing import Optional
from enum import Enum

class FailureMode(str, Enum):
    DUPLICATE_ROWS_BEFORE_GROUP_BY = "duplicate_rows_before_group_by"
    MANY_TO_MANY_JOIN_FANOUT = "many_to_many_join_fanout"
    NULL_PROPAGATION_LEFT_JOIN = "null_propagation_left_join"
    PERIOD_BOUNDARY_EDGE_CASE = "period_boundary_edge_case"
    GRAIN_VIOLATION = "grain_violation"
    SCD_TYPE_2_OVERLAP = "scd_type2_overlap"
    DIVISION_BY_ZERO = "division_by_zero"

class ColumnRisk(BaseModel):
    column_name: str
    data_type : str
    risk_reason : str 
    associated_failure_mode: FailureMode

class TableAnalysis(BaseModel):
    table_name : str
    grain : str
    risky_columns: list[ColumnRisk]
    notes: Optional[str] = None

class SchemaAnalysis(BaseModel):
    tables: list[TableAnalysis]
    recommended_failure_modes: list[FailureMode]
    risk_summary: str 


