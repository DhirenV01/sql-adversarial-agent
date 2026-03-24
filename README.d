# SQL Adversarial Testing Agent

AI-generated SQL is syntactically correct but logically fragile. A query can pass every linter and still return confidently wrong numbers when the underlying data has duplicates, join fanout, NULL edge cases, or period boundary issues.

This project stress-tests SQL queries the way a senior data engineer would — by automatically generating adversarial datasets that surface logic errors, not syntax errors.

**You give it a schema and a query. It tells you exactly where the logic breaks.**

---

## How It Works

A three-agent pipeline runs automatically when you submit a schema and query:

1. **Schema Analyzer** — reads your DDL and identifies risky columns, table grain, and which failure modes are most likely given the structure
2. **Adversarial Data Generator** — generates small targeted datasets (10-20 rows) designed to trigger each failure mode, using the same primary keys as your clean data for accurate comparison
3. **Validator** — runs your query against clean data and adversarial data, diffs the results, and produces a plain English explanation of what broke and how to fix it

The entire pipeline runs in-process with DuckDB — no database to spin up, no infrastructure required.

```
Schema + Query
      │
      ▼
┌─────────────────────┐
│   Schema Analyzer   │  ← Agent 1: identifies grain, risky columns, failure modes
└─────────────────────┘
      │
      ▼
┌─────────────────────┐
│  Data Generator     │  ← Agent 2: generates adversarial datasets per failure mode
└─────────────────────┘
      │
      ▼
┌─────────────────────┐
│    Validator        │  ← Agent 3: runs query, diffs results, explains failures
└─────────────────────┘
      │
      ▼
  Analysis Report
```

---

## Failure Modes Tested

| Failure Mode | What It Catches |
|---|---|
| `duplicate_rows_before_group_by` | Repeated rows that inflate GROUP BY aggregates |
| `many_to_many_join_fanout` | Joins where both sides have multiple matching rows, multiplying results |
| `null_propagation_left_join` | NULLs introduced by LEFT JOINs that silently drop rows or corrupt aggregates |
| `period_boundary_edge_case` | Off-by-one errors on date and timestamp filters |
| `grain_violation` | Fact table rows at the wrong level of granularity |
| `scd_type2_overlap` | Point-in-time query errors from slowly changing dimension overlaps |
| `division_by_zero` | Calculated fields where the denominator can be zero or NULL |

---

## Stack

| Layer | Tool | Why |
|---|---|---|
| SQL Engine | DuckDB | In-process, no infrastructure, full SQL support including window functions and CTEs |
| Agent Framework | Python + OpenAI API | Direct GPT-4o calls with structured outputs via Pydantic |
| Structured Outputs | Pydantic v2 | Enforces schema at every agent boundary — no hallucinated fields |
| Backend API | FastAPI | Clean async support, automatic docs at `/docs` |
| Testing | pytest + DuckDB fixtures | Unit and integration tests for every agent |

---

## Quickstart

**Requirements:** Python 3.9+, an OpenAI API key

```bash
git clone https://github.com/DhirenV01/sql-adversarial-agent.git
cd sql-adversarial-agent
pip install -r requirements.txt
cp .env.example .env       # add your OPENAI_API_KEY
make run
```

Then open `http://localhost:8000/docs` and use the `/analyze` endpoint.

---

## Running Fully Local (No API Key Required)

> **Note:** Ollama support is coming soon. Currently the pipeline requires an OpenAI API key. GPT-4o is recommended for accurate failure mode detection.

---

## Example

**Input schema:**
```sql
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
```

**Input query:**
```sql
SELECT customer_id, SUM(amount) / COUNT(order_id) AS avg_revenue
FROM orders
GROUP BY customer_id
```

**Output:**
```json
{
  "total_tests": 1,
  "passed": 0,
  "failed": 1,
  "results": [
    {
      "test_name": "division_by_zero_test",
      "failure_mode": "division_by_zero",
      "passed": false,
      "delta_summary": "Adversarial result includes a customer with avg_revenue of 0.0 not present in clean data.",
      "explanation": "The query is vulnerable to division by zero when a customer has orders with zero amounts. Add a CASE statement to guard against zero denominators: SUM(amount) / NULLIF(COUNT(order_id), 0)"
    }
  ]
}
```

---

## Project Structure

```
sql-adversarial-agent/
├── agents/
│   ├── schema_analyzer.py    # Agent 1: analyzes schema, identifies failure modes
│   ├── data_generator.py     # Agent 2: generates adversarial datasets
│   └── validator.py          # Agent 3: runs queries, diffs results, explains failures
├── models/
│   ├── schema.py             # Pydantic models for schema analysis output
│   ├── test_case.py          # Pydantic models for adversarial test cases
│   └── report.py             # Pydantic models for validation report
├── engine/
│   └── duckdb_runner.py      # Executes SQL against DuckDB, returns results
├── api/
│   └── main.py               # FastAPI app, /analyze endpoint
├── tests/                    # pytest suite for every agent
├── requirements.txt
├── Makefile
└── .env.example
```

---

## Running Tests

```bash
make test
```

27 tests across all three agents covering clean data baselines, adversarial failure modes, Pydantic validation at every agent boundary, and full end-to-end pipeline integration.

---

## Why This Project

AI can write SQL. It cannot validate its own logic against real data edge cases. This project fills that gap — not by checking syntax, but by generating the exact data conditions that cause queries to silently return wrong numbers.

The design is intentional: each agent has a single responsibility, every boundary is enforced with Pydantic structured outputs, and the report explains not just what failed but why it failed and how to fix it. That last part is what makes the output actionable.

Built as a local-first open source tool. No infrastructure required to run. Designed to be extended with additional failure modes, warehouse integrations, and LLM providers.

---

## Contributing

PRs welcome. If you have a failure mode that isn't covered, open an issue with a schema example and a query that demonstrates the problem.