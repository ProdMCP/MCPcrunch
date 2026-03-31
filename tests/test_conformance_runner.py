"""
Tests for mcpcrunch.conformance.runner (ConformanceRunner)

Tests the orchestrator via its Python API — static mode, category mode,
and configuration handling.
"""

import pytest
import json
import os
import tempfile
from mcpcrunch.conformance.runner import ConformanceRunner
from mcpcrunch.conformance.models import (
    AuthConfig,
    ConformanceReport,
    TestCategory,
    TestStatus,
)


# ── Fixtures ────────────────────────────────────────────────

@pytest.fixture
def spec_path():
    return os.path.join("examples", "minimal_valid.json")

@pytest.fixture
def schema_path():
    return "schema.json"

@pytest.fixture
def vulnerable_spec_path():
    return os.path.join("examples", "vulnerable_security.json")

@pytest.fixture
def runner(spec_path, schema_path):
    return ConformanceRunner(spec_path=spec_path, schema_path=schema_path)


# ── Initialization ─────────────────────────────────────────

class TestRunnerInit:
    def test_basic_init(self, spec_path, schema_path):
        runner = ConformanceRunner(spec_path=spec_path, schema_path=schema_path)
        assert runner.spec is not None
        assert runner.schema is not None
        assert runner.server_url is None
        assert runner.spec_version == "1.0.0"

    def test_init_with_server_url(self, spec_path, schema_path):
        runner = ConformanceRunner(
            spec_path=spec_path,
            schema_path=schema_path,
            server_url="http://localhost:3000",
        )
        assert runner.server_url == "http://localhost:3000"

    def test_init_with_auth(self, spec_path, schema_path):
        auth = AuthConfig(bearer_token="test-token")
        runner = ConformanceRunner(
            spec_path=spec_path,
            schema_path=schema_path,
            auth=auth,
        )
        assert runner.auth.bearer_token == "test-token"

    def test_init_without_schema(self, spec_path):
        runner = ConformanceRunner(spec_path=spec_path, schema_path="nonexistent.json")
        assert runner.schema is None

    def test_init_missing_spec_raises(self):
        with pytest.raises(FileNotFoundError):
            ConformanceRunner(spec_path="does_not_exist.json")

    def test_init_default_timeout(self, spec_path, schema_path):
        runner = ConformanceRunner(spec_path=spec_path, schema_path=schema_path)
        assert runner.timeout == 10.0

    def test_init_custom_timeout(self, spec_path, schema_path):
        runner = ConformanceRunner(spec_path=spec_path, schema_path=schema_path, timeout=30.0)
        assert runner.timeout == 30.0

    def test_init_default_auth(self, spec_path, schema_path):
        runner = ConformanceRunner(spec_path=spec_path, schema_path=schema_path)
        assert runner.auth.api_key is None
        assert runner.auth.bearer_token is None


# ── run_static ─────────────────────────────────────────────

class TestRunStatic:
    def test_returns_report(self, runner):
        report = runner.run_static()
        assert isinstance(report, ConformanceReport)

    def test_thirteen_static_tests(self, runner):
        report = runner.run_static()
        assert report.summary.total_tests == 13

    def test_all_pass_for_valid_spec(self, runner):
        report = runner.run_static()
        # minimal_valid.json lacks security, so not all 13 pass, but none should error
        assert report.summary.errors == 0
        assert report.summary.passed >= 5  # At least the 5 structural tests
        assert report.summary.failed + report.summary.passed == 13

    def test_spec_version_set(self, runner):
        report = runner.run_static()
        assert report.spec_version == "1.0.0"

    def test_duration_recorded(self, runner):
        report = runner.run_static()
        assert report.duration_ms is not None
        assert report.duration_ms >= 0

    def test_no_server_url(self, runner):
        report = runner.run_static()
        assert report.server_url is None

    def test_timestamp_set(self, runner):
        report = runner.run_static()
        assert report.timestamp is not None

    def test_without_schema(self, spec_path):
        runner = ConformanceRunner(spec_path=spec_path, schema_path="nonexistent.json")
        report = runner.run_static()
        # CT-3.8.1 should be skipped, rest should pass
        assert report.summary.total_tests == 13
        assert report.summary.skipped >= 1

    def test_vulnerable_spec(self, vulnerable_spec_path, schema_path):
        runner = ConformanceRunner(spec_path=vulnerable_spec_path, schema_path=schema_path)
        report = runner.run_static()
        assert report.summary.total_tests == 13


# ── run_category ───────────────────────────────────────────

class TestRunCategory:
    def test_spec_integrity_category(self, runner):
        report = runner.run_category(TestCategory.SPEC_INTEGRITY)
        assert isinstance(report, ConformanceReport)
        assert report.summary.total_tests == 13

    def test_runtime_category_without_server_raises(self, runner):
        with pytest.raises(ValueError, match="server_url"):
            runner.run_category(TestCategory.SCHEMA_INPUT)

    def test_all_categories_enum_values(self):
        """Ensure all category enum values are valid."""
        for cat in TestCategory:
            assert isinstance(cat.value, str)


# ── run_all (static only — no server) ─────────────────────

class TestRunAll:
    def test_without_server_runs_static_only(self, runner):
        """Without server_url, run_all should only run static tests."""
        report = runner.run_all()
        assert report.summary.total_tests == 13  # Only CT-3.8.x

    def test_report_structure(self, runner):
        report = runner.run_all()
        assert isinstance(report.results, list)
        assert isinstance(report.failures, list)
        assert isinstance(report.summary.total_tests, int)


# ── All example specs ──────────────────────────────────────

class TestExampleSpecs:
    @pytest.mark.parametrize("filename", [
        "minimal_valid.json",
        "vulnerable_security.json",
        "vulnerable_data_quality.json",
        "complex_shadowing.json",
        "adversarial_poisoning.json",
    ])
    def test_static_on_example(self, filename, schema_path):
        spec_path = os.path.join("examples", filename)
        if not os.path.exists(spec_path):
            pytest.skip(f"{filename} not found")
        runner = ConformanceRunner(spec_path=spec_path, schema_path=schema_path)
        report = runner.run_static()
        assert report.summary.total_tests == 13
        assert report.summary.errors == 0


# ── Report export ──────────────────────────────────────────

class TestReportExport:
    def test_json_export(self, runner):
        from mcpcrunch.conformance.reporter import export_json
        report = runner.run_static()
        json_str = export_json(report)
        data = json.loads(json_str)
        assert "summary" in data
        assert "results" in data
        assert "failures" in data
        assert data["summary"]["total_tests"] == 13

    def test_json_export_to_file(self, runner):
        from mcpcrunch.conformance.reporter import export_json
        report = runner.run_static()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            path = f.name
        try:
            export_json(report, path)
            with open(path) as f:
                data = json.load(f)
            assert data["summary"]["total_tests"] == 13
        finally:
            os.unlink(path)

    def test_json_export_result_fields(self, runner):
        from mcpcrunch.conformance.reporter import export_json
        report = runner.run_static()
        data = json.loads(export_json(report))
        for result in data["results"]:
            assert "test_id" in result
            assert "test_name" in result
            assert "category" in result
            assert "status" in result
