from pydantic import BaseModel
from models.schema import FailureMode

class AdversarialRow(BaseModel):
    table_name: str
    rows: list[dict]

class AdversarialTestCase(BaseModel):
    name: str
    failure_mode: FailureMode 
    description: str
    adversarial_data: list[AdversarialRow] # List of adversarial row objects, one per table
    expected_trap: str # plain English description of how the failure mode should manifest (e.g. "duplicate rows in GROUP BY result", "NULLs silently dropped by LEFT JOIN", etc.)

    