from pydantic import BaseModel
from typing import Optional


class TestCaseResult(BaseModel):
    test_name: str
    # e.g. "duplicate_rows_before_group_by", "null_propagation_left_join"
    failure_mode: str
    # what the adversarial dataset was specifically designed to do
    adversarial_description: str
    # raw query output on clean data
    clean_result: list[dict]
    # raw query output on adversarial data
    adversarial_result: list[dict]
    # did the query handle this case correctly
    passed: bool
    # e.g. "Revenue inflated by 2x due to duplicate order_id rows before GROUP BY"
    delta_summary: str
    # GPT-4o plain English: what broke, why, and how to fix it
    explanation: str


class AnalysisReport(BaseModel):
    query: str
    schema_summary: str
    total_tests: int
    passed: int
    failed: int
    results: list[TestCaseResult]

    @property
    def pass_rate(self) -> float:
        if self.total_tests == 0:
            return 0.0
        return self.passed / self.total_tests

    def failed_cases(self) -> list[TestCaseResult]:
        return [r for r in self.results if not r.passed]

    def passed_cases(self) -> list[TestCaseResult]:
        return [r for r in self.results if r.passed]
