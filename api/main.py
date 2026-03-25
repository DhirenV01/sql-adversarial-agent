import asyncio
from functools import partial

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from agents.schema_analyzer import analyze_schema
from agents.data_generator import generate_test_case
from agents.validator import validate_test_case
from models.report import AnalysisReport

load_dotenv()

app = FastAPI(
    title="SQL Adversarial Testing Agent",
    description="Stress-tests SQL queries by generating adversarial data to surface logic errors",
    version="0.1.0",
)


class AnalyzeRequest(BaseModel):
    ddl: str
    query: str
    clean_data: dict[str, list[dict]]

@app.get("/health")
def health():
    return {"status": "ok"}

def _run_pipeline(request: AnalyzeRequest) -> AnalysisReport:
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


@app.post("/analyze", response_model=AnalysisReport)
async def analyze(request: AnalyzeRequest):
    loop = asyncio.get_event_loop()
    try:
        report = await asyncio.wait_for(
            loop.run_in_executor(None, partial(_run_pipeline, request)),
            timeout=120,
        )
        return report
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Analysis timed out after 120 seconds")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

        