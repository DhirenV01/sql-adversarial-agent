import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from models.schema import SchemaAnalysis, FailureMode
from models.test_case import AdversarialTestCase

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """
You are a senior data engineer specializing in SQL query validation and data quality.

You will be given:
1. A SQL schema (CREATE TABLE statements)
2. A SQL query to test
3. A specific failure mode to target
4. Columns flagged as risky for that failure mode

Your job is to generate a small adversarial dataset (10-20 rows across all tables) that is specifically designed to expose the given failure mode in the query.

The dataset must:
- Use the exact table and column names from the schema provided
- Target the specific risky columns flagged for this failure mode
- Contain rows that will cause the query to return a wrong result
- Be realistic enough to resemble production data

Return ONLY valid JSON. No preamble, no markdown, no explanation.

The JSON must match this exact structure:

{
  "name": "short_snake_case_identifier",
  "failure_mode": "the failure mode string provided",
  "description": "plain English explanation of what this dataset does",
  "adversarial_data": [
    {
      "table_name": "string",
      "rows": [
        {"column_name": "value", ...}
      ]
    }
  ],
  "expected_trap": "plain English description of what should go wrong when the query runs on this data"
}

adversarial_data must be a JSON array of objects, not a dict.
Each object in adversarial_data must have table_name and rows fields.
rows must be a JSON array of row objects.
Every row must use only column names that exist in the schema.
""".strip()


def generate_test_case(
    ddl: str,
    query: str,
    failure_mode: FailureMode,
    schema_analysis: SchemaAnalysis,
) -> AdversarialTestCase:
    """
    Given a schema, query, and target failure mode, generates one
    adversarial test case designed to expose that failure mode.
    """
    relevant_columns = []
    for table in schema_analysis.tables:
        for col in table.risky_columns:
            if col.associated_failure_mode == failure_mode:
                relevant_columns.append(
                    f"{table.table_name}.{col.column_name}: {col.risk_reason}"
                )

    relevant_context = "\n".join(relevant_columns) if relevant_columns else "None identified"

    user_message = f"""
Schema:
{ddl}

Query to test:
{query}

Target failure mode: {failure_mode.value}

Schema risk summary:
{schema_analysis.risk_summary}

Columns flagged for this failure mode:
{relevant_context}

Generate one adversarial test case targeting the {failure_mode.value} failure mode.
Use the flagged columns above to construct data that specifically triggers this failure.
""".strip()

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content
    data = json.loads(raw)
    return AdversarialTestCase(**data)