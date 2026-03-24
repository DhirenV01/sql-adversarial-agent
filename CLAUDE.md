# SQL Adversarial Testing Agent

Local-first, open source tool that stress-tests AI-generated SQL by auto-generating adversarial datasets to surface logic errors, not syntax errors.

## Stack
Python 3.9+, DuckDB, GPT-4o, Pydantic, FastAPI (planned), pytest

## Architecture
3-agent pipeline:
1. Schema Analyzer: inspects table schemas, identifies vulnerability surfaces
2. Data Generator: creates adversarial datasets targeting specific failure modes
3. Validator: runs the SQL under test against adversarial data, reports logic errors

## File Structure
- agents/: one module per agent (schema_analyzer, data_generator, validator)
- models/: Pydantic models for agent I/O
- tests/: pytest, one test file per agent + integration tests

## Conventions
- All agent communication via Pydantic models, never raw dicts
- DuckDB in-memory for all test data, no persistent state
- GPT-4o calls use structured output (response_format)
- Tests are self-contained: setup, execute, assert, teardown in each test

## Do Not
- Add external database dependencies
- Mock DuckDB in tests
- Use print() for logging (use logging module)
- Catch bare exceptions
