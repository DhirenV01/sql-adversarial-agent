import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from dotenv import load_dotenv
from agents.schema_analyzer import analyze_schema
from agents.data_generator import generate_test_case
from agents.validator import validate_test_case
from models.report import AnalysisReport

load_dotenv()

logger = logging.getLogger(__name__)

MAX_DDL_LENGTH = 50_000
MAX_QUERY_LENGTH = 10_000
MAX_CLEAN_DATA_TABLES = 20
MAX_CLEAN_DATA_ROWS_PER_TABLE = 1_000

app = FastAPI(
    title="SQL Adversarial Testing Agent",
    description="Stress-tests SQL queries by generating adversarial data to surface logic errors",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)


class AnalyzeRequest(BaseModel):
    ddl: str
    query: str
    clean_data: dict[str, list[dict]]

    @field_validator("ddl")
    @classmethod
    def ddl_not_empty_or_oversized(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("ddl must not be empty")
        if len(stripped) > MAX_DDL_LENGTH:
            raise ValueError(f"ddl exceeds maximum length of {MAX_DDL_LENGTH} characters")
        return stripped

    @field_validator("query")
    @classmethod
    def query_not_empty_or_oversized(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("query must not be empty")
        if len(stripped) > MAX_QUERY_LENGTH:
            raise ValueError(f"query exceeds maximum length of {MAX_QUERY_LENGTH} characters")
        return stripped

    @field_validator("clean_data")
    @classmethod
    def clean_data_within_limits(cls, v: dict[str, list[dict]]) -> dict[str, list[dict]]:
        if not v:
            raise ValueError("clean_data must contain at least one table")
        if len(v) > MAX_CLEAN_DATA_TABLES:
            raise ValueError(f"clean_data exceeds maximum of {MAX_CLEAN_DATA_TABLES} tables")
        for table_name, rows in v.items():
            if len(rows) > MAX_CLEAN_DATA_ROWS_PER_TABLE:
                raise ValueError(
                    f"Table {table_name!r} exceeds maximum of {MAX_CLEAN_DATA_ROWS_PER_TABLE} rows"
                )
        return v


@app.get("/health")
def health():
    return {"status": "ok"}

DANGEROUS_KEYWORDS = ["ATTACH", "COPY", "EXPORT", "IMPORT", "INSTALL", "LOAD"]

@app.post("/analyze", response_model=AnalysisReport)
def analyze(request: AnalyzeRequest):
    upper_query = request.query.upper()
    for keyword in DANGEROUS_KEYWORDS:
        if keyword in upper_query:
            raise HTTPException(status_code=400, detail=f"Query contains disallowed keyword: {keyword}")

    try:
        # Agent 1: analyze the schema
        schema_analysis = analyze_schema(request.ddl)

        # Agent 2 + 3: for each recommended failure mode,
        # generate adversarial data and validate
        results = []
        for failure_mode in schema_analysis.recommended_failure_modes:
            test_case = generate_test_case(
                ddl=request.ddl,
                query=request.query,
                failure_mode=failure_mode,
                schema_analysis=schema_analysis,
                clean_data=request.clean_data,
            )
            result = validate_test_case(
                ddl=request.ddl,
                query=request.query,
                clean_data=request.clean_data,
                test_case=test_case,
            )
            results.append(result)

        # build the final report
        passed = sum(1 for r in results if r.passed)
        failed = len(results) - passed

        return AnalysisReport(
            query=request.query,
            schema_summary=schema_analysis.risk_summary,
            total_tests=len(results),
            passed=passed,
            failed=failed,
            results=results,
        )

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except HTTPException:
        raise
    except Exception:
        logger.exception("Unexpected error during analysis")
        raise HTTPException(status_code=500, detail="Internal server error")