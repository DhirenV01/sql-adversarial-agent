import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from engine.duckdb_runner import DuckDBRunner
from models.test_case import AdversarialTestCase
from models.report import TestCaseResult, AnalysisReport

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def validate_test_case(
    ddl: str,
    query: str,
    clean_data: dict[str, list[dict]],
    test_case: AdversarialTestCase,
) -> TestCaseResult:
    """
    Runs the query against clean data and adversarial data,
    diffs the results, and produces a TestCaseResult.
    """
    # run on clean data
    clean_runner = DuckDBRunner()
    clean_result = clean_runner.load_and_run(
        ddl=ddl,
        rows_by_table=clean_data,
        query=query,
    )
    clean_runner.close()

    # build adversarial rows_by_table from the test case
    adversarial_rows = {
        d.table_name: d.rows
        for d in test_case.adversarial_data
    }

    # fill in any missing tables with clean data
    for table_name, rows in clean_data.items():
        if table_name not in adversarial_rows:
            adversarial_rows[table_name] = rows

    # run on adversarial data
    adversarial_runner = DuckDBRunner()
    adversarial_result = adversarial_runner.load_and_run(
        ddl=ddl,
        rows_by_table=adversarial_rows,
        query=query,
    )
    adversarial_runner.close()

    # ask GPT-4o to reason about the diff
    diff_prompt = f"""
A SQL query was run against clean data and adversarial data.

Query:
{query}

Clean result:
{json.dumps(clean_result, indent=2)}

Adversarial result:
{json.dumps(adversarial_result, indent=2)}

Failure mode being tested: {test_case.failure_mode.value}
Expected trap: {test_case.expected_trap}

Did the query fail this test? Explain in plain English:
1. Whether the results differ meaningfully
2. What specific logic error caused the difference if any
3. How a developer should fix the query

Return ONLY valid JSON with this structure:
{{
    "passed": true or false,
    "delta_summary": "one sentence describing the difference in results",
    "explanation": "plain English explanation of what broke and how to fix it"
}}
""".strip()

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "user", "content": diff_prompt}
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content
    judgment = json.loads(raw)

    return TestCaseResult(
        test_name=test_case.name,
        failure_mode=test_case.failure_mode,
        adversarial_description=test_case.description,
        clean_result=clean_result,
        adversarial_result=adversarial_result,
        passed=judgment["passed"],
        delta_summary=judgment["delta_summary"],
        explanation=judgment["explanation"],
    )