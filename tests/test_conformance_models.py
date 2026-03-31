"""
Tests for mcpcrunch.conformance.models

Covers: TestStatus, TestCategory, AuthConfig, ConformanceTestResult,
        ConformanceSummary, ConformanceReport
"""

import pytest
from mcpcrunch.conformance.models import (
    AuthConfig,
    ConformanceReport,
    ConformanceSummary,
    ConformanceTestResult,
    TestCategory,
    TestSeverity,
    TestStatus,
    SEVERITY_PENALTIES,
    _compute_grade,
)


# ── TestStatus ──────────────────────────────────────────────

class TestTestStatus:
    def test_enum_values(self):
        assert TestStatus.PASSED == "PASSED"
        assert TestStatus.FAILED == "FAILED"
        assert TestStatus.SKIPPED == "SKIPPED"
        assert TestStatus.ERROR == "ERROR"

    def test_all_statuses_present(self):
        assert len(TestStatus) == 4

    def test_string_comparison(self):
        assert TestStatus.PASSED == "PASSED"
        assert TestStatus("FAILED") == TestStatus.FAILED


# ── TestCategory ────────────────────────────────────────────

class TestTestCategory:
    def test_all_categories_present(self):
        assert len(TestCategory) == 10

    def test_category_values(self):
        assert TestCategory.SCHEMA_INPUT == "schema_input"
        assert TestCategory.SPEC_INTEGRITY == "spec_integrity"
        assert TestCategory.DETERMINISM == "determinism"

    def test_category_from_string(self):
        assert TestCategory("schema_input") == TestCategory.SCHEMA_INPUT
        assert TestCategory("security") == TestCategory.SECURITY

    def test_invalid_category_raises(self):
        with pytest.raises(ValueError):
            TestCategory("nonexistent")


# ── AuthConfig ──────────────────────────────────────────────

class TestAuthConfig:
    def test_default_values(self):
        auth = AuthConfig()
        assert auth.api_key is None
        assert auth.bearer_token is None
        assert auth.api_key_header_name == "Authorization"
        assert auth.api_key_in == "header"

    def test_bearer_token(self):
        auth = AuthConfig(bearer_token="my-token")
        assert auth.bearer_token == "my-token"
        assert auth.api_key is None

    def test_api_key(self):
        auth = AuthConfig(api_key="key-123", api_key_in="query")
        assert auth.api_key == "key-123"
        assert auth.api_key_in == "query"

    def test_serialization(self):
        auth = AuthConfig(bearer_token="tok", api_key="key")
        d = auth.model_dump()
        assert d["bearer_token"] == "tok"
        assert d["api_key"] == "key"


# ── ConformanceTestResult ──────────────────────────────────

class TestConformanceTestResult:
    def test_minimal_result(self):
        r = ConformanceTestResult(
            test_id="CT-3.1.1",
            test_name="Test",
            category=TestCategory.SCHEMA_INPUT,
            status=TestStatus.PASSED,
        )
        assert r.test_id == "CT-3.1.1"
        assert r.entity is None
        assert r.expected is None
        assert r.duration_ms is None

    def test_full_result(self):
        r = ConformanceTestResult(
            test_id="CT-3.2.1",
            test_name="Output Validation",
            category=TestCategory.SCHEMA_OUTPUT,
            entity="tool.echo",
            status=TestStatus.FAILED,
            expected="Schema match",
            actual="Type mismatch on field 'x'",
            message="Extra context",
            duration_ms=12.5,
        )
        assert r.entity == "tool.echo"
        assert r.status == TestStatus.FAILED
        assert r.duration_ms == 12.5

    def test_serialization_roundtrip(self):
        r = ConformanceTestResult(
            test_id="CT-3.8.1",
            test_name="Schema Validity",
            category=TestCategory.SPEC_INTEGRITY,
            status=TestStatus.PASSED,
        )
        d = r.model_dump()
        r2 = ConformanceTestResult(**d)
        assert r2.test_id == r.test_id
        assert r2.status == r.status


# ── ConformanceSummary ─────────────────────────────────────

class TestConformanceSummary:
    def test_default_values(self):
        s = ConformanceSummary()
        assert s.total_tests == 0
        assert s.passed == 0
        assert s.failed == 0
        assert s.skipped == 0
        assert s.errors == 0

    def test_pass_rate_100_percent(self):
        s = ConformanceSummary(total_tests=10, passed=10)
        assert s.pass_rate == "100.0%"

    def test_pass_rate_partial(self):
        s = ConformanceSummary(total_tests=10, passed=7, failed=3)
        assert s.pass_rate == "70.0%"

    def test_pass_rate_zero(self):
        s = ConformanceSummary(total_tests=0)
        assert s.pass_rate == "0%"

    def test_pass_rate_all_skipped(self):
        s = ConformanceSummary(total_tests=5, skipped=5)
        assert s.pass_rate == "N/A"

    def test_pass_rate_with_skipped(self):
        # 10 total, 2 skipped, 6 passed, 2 failed → 6/8 = 75%
        s = ConformanceSummary(total_tests=10, passed=6, failed=2, skipped=2)
        assert s.pass_rate == "75.0%"


# ── ConformanceReport ──────────────────────────────────────

class TestConformanceReport:
    def _make_results(self):
        return [
            ConformanceTestResult(test_id="CT-3.8.1", test_name="A", category=TestCategory.SPEC_INTEGRITY, status=TestStatus.PASSED),
            ConformanceTestResult(test_id="CT-3.8.2", test_name="B", category=TestCategory.SPEC_INTEGRITY, status=TestStatus.PASSED),
            ConformanceTestResult(test_id="CT-3.8.3", test_name="C", category=TestCategory.SPEC_INTEGRITY, status=TestStatus.FAILED, actual="Cycle found"),
            ConformanceTestResult(test_id="CT-3.8.4", test_name="D", category=TestCategory.SPEC_INTEGRITY, status=TestStatus.SKIPPED, message="No components"),
            ConformanceTestResult(test_id="CT-3.8.5", test_name="E", category=TestCategory.SPEC_INTEGRITY, status=TestStatus.ERROR, message="Crash"),
        ]

    def test_from_results_summary(self):
        report = ConformanceReport.from_results(self._make_results())
        assert report.summary.total_tests == 5
        assert report.summary.passed == 2
        assert report.summary.failed == 1
        assert report.summary.skipped == 1
        assert report.summary.errors == 1

    def test_from_results_failures(self):
        report = ConformanceReport.from_results(self._make_results())
        assert len(report.failures) == 2  # FAILED + ERROR
        assert report.failures[0].test_id == "CT-3.8.3"
        assert report.failures[1].test_id == "CT-3.8.5"

    def test_from_results_metadata(self):
        report = ConformanceReport.from_results(
            self._make_results(),
            server_url="http://localhost:3000",
            spec_version="1.0.0",
            duration_ms=150.0,
        )
        assert report.server_url == "http://localhost:3000"
        assert report.spec_version == "1.0.0"
        assert report.duration_ms == 150.0

    def test_from_results_empty(self):
        report = ConformanceReport.from_results([])
        assert report.summary.total_tests == 0
        assert report.summary.passed == 0
        assert len(report.failures) == 0

    def test_timestamp_default(self):
        report = ConformanceReport.from_results([])
        assert report.timestamp is not None
        assert len(report.timestamp) > 10  # ISO format

    def test_all_pass(self):
        results = [
            ConformanceTestResult(test_id=f"CT-{i}", test_name=f"T{i}", category=TestCategory.SPEC_INTEGRITY, status=TestStatus.PASSED)
            for i in range(20)
        ]
        report = ConformanceReport.from_results(results)
        assert report.summary.passed == 20
        assert report.summary.failed == 0
        assert len(report.failures) == 0
        assert report.summary.pass_rate == "100.0%"

    def test_weighted_score_all_pass(self):
        results = [
            ConformanceTestResult(test_id="CT-1", test_name="T", category=TestCategory.SPEC_INTEGRITY, status=TestStatus.PASSED),
        ]
        report = ConformanceReport.from_results(results)
        assert report.summary.score == 100
        assert report.summary.grade == "A"

    def test_weighted_score_critical_failure(self):
        results = [
            ConformanceTestResult(test_id="CT-1", test_name="T", category=TestCategory.SPEC_INTEGRITY,
                                  severity=TestSeverity.CRITICAL, status=TestStatus.FAILED),
        ]
        report = ConformanceReport.from_results(results)
        assert report.summary.score == 100 - SEVERITY_PENALTIES[TestSeverity.CRITICAL]  # 85

    def test_weighted_score_multiple_failures(self):
        results = [
            ConformanceTestResult(test_id="CT-1", test_name="T", category=TestCategory.SPEC_INTEGRITY,
                                  severity=TestSeverity.CRITICAL, status=TestStatus.FAILED),
            ConformanceTestResult(test_id="CT-2", test_name="T", category=TestCategory.SPEC_INTEGRITY,
                                  severity=TestSeverity.HIGH, status=TestStatus.FAILED),
            ConformanceTestResult(test_id="CT-3", test_name="T", category=TestCategory.SPEC_INTEGRITY,
                                  severity=TestSeverity.MEDIUM, status=TestStatus.FAILED),
        ]
        report = ConformanceReport.from_results(results)
        expected = 100 - 15 - 8 - 4  # 73
        assert report.summary.score == expected

    def test_weighted_score_floor_at_zero(self):
        results = [
            ConformanceTestResult(test_id=f"CT-{i}", test_name="T", category=TestCategory.SPEC_INTEGRITY,
                                  severity=TestSeverity.CRITICAL, status=TestStatus.FAILED)
            for i in range(10)  # 10 * 15 = 150, clamped to 0
        ]
        report = ConformanceReport.from_results(results)
        assert report.summary.score == 0
        assert report.summary.grade == "F"

    def test_grade_boundaries(self):
        assert _compute_grade(100) == "A"
        assert _compute_grade(90) == "A"
        assert _compute_grade(89) == "B"
        assert _compute_grade(75) == "B"
        assert _compute_grade(74) == "C"
        assert _compute_grade(60) == "C"
        assert _compute_grade(59) == "D"
        assert _compute_grade(40) == "D"
        assert _compute_grade(39) == "F"
        assert _compute_grade(0) == "F"

    def test_error_also_penalizes(self):
        results = [
            ConformanceTestResult(test_id="CT-1", test_name="T", category=TestCategory.SPEC_INTEGRITY,
                                  severity=TestSeverity.HIGH, status=TestStatus.ERROR),
        ]
        report = ConformanceReport.from_results(results)
        assert report.summary.score == 100 - SEVERITY_PENALTIES[TestSeverity.HIGH]  # 92

    def test_skipped_does_not_penalize(self):
        results = [
            ConformanceTestResult(test_id="CT-1", test_name="T", category=TestCategory.SPEC_INTEGRITY,
                                  severity=TestSeverity.CRITICAL, status=TestStatus.SKIPPED),
        ]
        report = ConformanceReport.from_results(results)
        assert report.summary.score == 100  # Skipped doesn't deducted


# ── TestSeverity ────────────────────────────────────────────

class TestTestSeverity:
    def test_enum_values(self):
        assert TestSeverity.CRITICAL == "critical"
        assert TestSeverity.HIGH == "high"
        assert TestSeverity.MEDIUM == "medium"
        assert TestSeverity.LOW == "low"

    def test_all_levels_present(self):
        assert len(TestSeverity) == 4

    def test_penalties_defined_for_all(self):
        for sev in TestSeverity:
            assert sev in SEVERITY_PENALTIES

    def test_penalty_ordering(self):
        assert SEVERITY_PENALTIES[TestSeverity.CRITICAL] > SEVERITY_PENALTIES[TestSeverity.HIGH]
        assert SEVERITY_PENALTIES[TestSeverity.HIGH] > SEVERITY_PENALTIES[TestSeverity.MEDIUM]
        assert SEVERITY_PENALTIES[TestSeverity.MEDIUM] > SEVERITY_PENALTIES[TestSeverity.LOW]

    def test_default_severity_on_result(self):
        r = ConformanceTestResult(
            test_id="CT-1", test_name="T",
            category=TestCategory.SPEC_INTEGRITY,
            status=TestStatus.PASSED,
        )
        assert r.severity == TestSeverity.HIGH  # Default
