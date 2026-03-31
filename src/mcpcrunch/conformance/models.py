"""
Conformance Test Suite — Data Models

Pydantic models for test results, reports, and configuration.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import datetime


class TestStatus(str, Enum):
    """Status of an individual conformance test."""
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    ERROR = "ERROR"


class TestSeverity(str, Enum):
    """Severity/weight of a conformance test for scoring."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# Scoring penalties per severity level
SEVERITY_PENALTIES = {
    TestSeverity.CRITICAL: 15,
    TestSeverity.HIGH: 8,
    TestSeverity.MEDIUM: 4,
    TestSeverity.LOW: 2,
}


class TestCategory(str, Enum):
    """Categories of conformance tests (maps to spec sections 3.1–3.10)."""
    SCHEMA_INPUT = "schema_input"
    SCHEMA_OUTPUT = "schema_output"
    TOOL_CONTRACT = "tool_contract"
    PROMPT_CONTRACT = "prompt_contract"
    RESOURCE_CONTRACT = "resource_contract"
    SECURITY = "security"
    SERVER_CONTRACT = "server_contract"
    SPEC_INTEGRITY = "spec_integrity"
    ERROR_HANDLING = "error_handling"
    DETERMINISM = "determinism"


class AuthConfig(BaseModel):
    """Authentication configuration for conformance tests."""
    api_key: Optional[str] = None
    bearer_token: Optional[str] = None
    api_key_header_name: Optional[str] = Field(default="Authorization", description="Header name for API key")
    api_key_in: Optional[str] = Field(default="header", description="Where to send API key: header, query, cookie")


class ConformanceTestResult(BaseModel):
    """Result of a single conformance test."""
    test_id: str = Field(..., description="Unique test ID, e.g. CT-3.1.1")
    test_name: str = Field(..., description="Human-readable test name")
    category: TestCategory
    severity: TestSeverity = Field(
        default=TestSeverity.HIGH,
        description="Test severity — determines scoring penalty on failure"
    )
    entity: Optional[str] = Field(None, description="Entity under test, e.g. tool.createUser")
    status: TestStatus
    expected: Optional[str] = Field(None, description="What was expected")
    actual: Optional[str] = Field(None, description="What actually happened")
    message: Optional[str] = Field(None, description="Additional context or error message")
    duration_ms: Optional[float] = None


def _compute_grade(score: int) -> str:
    """Map a numeric score to a letter grade."""
    if score >= 90:
        return "A"
    elif score >= 75:
        return "B"
    elif score >= 60:
        return "C"
    elif score >= 40:
        return "D"
    else:
        return "F"


class ConformanceSummary(BaseModel):
    """Aggregated summary of conformance results."""
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    score: int = Field(default=100, description="Weighted conformance score (0–100)")
    grade: str = Field(default="A", description="Letter grade: A/B/C/D/F")

    @property
    def pass_rate(self) -> str:
        if self.total_tests == 0:
            return "0%"
        effective = self.total_tests - self.skipped
        if effective == 0:
            return "N/A"
        return f"{(self.passed / effective * 100):.1f}%"


class ConformanceReport(BaseModel):
    """Full conformance test report."""
    summary: ConformanceSummary = Field(default_factory=ConformanceSummary)
    results: List[ConformanceTestResult] = Field(default_factory=list)
    failures: List[ConformanceTestResult] = Field(default_factory=list)
    server_url: Optional[str] = None
    spec_version: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now().isoformat())
    duration_ms: Optional[float] = None

    @classmethod
    def from_results(cls, results: List[ConformanceTestResult], server_url: Optional[str] = None,
                     spec_version: Optional[str] = None, duration_ms: Optional[float] = None) -> "ConformanceReport":
        """Build a report from a list of test results.

        Calculates a weighted conformance score (0–100) based on the
        severity of each failed test.
        """
        passed = sum(1 for r in results if r.status == TestStatus.PASSED)
        failed_results = [r for r in results if r.status in (TestStatus.FAILED, TestStatus.ERROR)]
        skipped = sum(1 for r in results if r.status == TestStatus.SKIPPED)
        errors = sum(1 for r in results if r.status == TestStatus.ERROR)

        # Calculate weighted score: start at 100, subtract penalties
        score = 100
        for r in failed_results:
            penalty = SEVERITY_PENALTIES.get(r.severity, 0)
            score -= penalty
        score = max(0, score)

        grade = _compute_grade(score)

        summary = ConformanceSummary(
            total_tests=len(results),
            passed=passed,
            failed=sum(1 for r in results if r.status == TestStatus.FAILED),
            skipped=skipped,
            errors=errors,
            score=score,
            grade=grade,
        )

        return cls(
            summary=summary,
            results=results,
            failures=failed_results,
            server_url=server_url,
            spec_version=spec_version,
            duration_ms=duration_ms,
        )
