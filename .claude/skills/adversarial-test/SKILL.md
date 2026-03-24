---
name: adversarial-test
description: Add or extend adversarial SQL failure modes in the 3-agent pipeline
---

# Adversarial Test Protocol

## Before Writing Code
1. Read the existing agents: Schema Analyzer, Data Generator, Validator
2. Check which failure modes already have test coverage
3. Identify the target failure mode from the taxonomy below

## Failure Mode Taxonomy
- Duplicate rows before GROUP BY
- Many-to-many join fanout
- NULL propagation through LEFT JOINs
- Period boundary edge cases
- Grain violations
- SCD Type 2 overlaps
- Division by zero in aggregations

## Adding a New Failure Mode
1. Define the failure mode as a Pydantic model with: name, description, SQL pattern it catches, example bad query
2. Add synthetic data generation logic to Data Generator that produces the adversarial dataset for this mode
3. Add validation rule to Validator that detects the logic error
4. Write a test that: creates a DuckDB table, generates adversarial data, runs a known-bad query, asserts the Validator catches it
5. Update the Schema Analyzer if the new mode requires schema inspection

## Patterns to Follow
- All data generation uses DuckDB in-memory databases
- Pydantic models for all agent inputs and outputs
- GPT-4o calls must have structured output (response_format)
- Tests are self-contained: create table, seed data, run query, assert

## Anti-Patterns
- No persistent database state between tests
- No mocking DuckDB (it's local and fast, use real queries)
- No hardcoded SQL strings in agents (generate dynamically)
- No catching generic exceptions from GPT-4o (handle specific error types)
