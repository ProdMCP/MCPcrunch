"""
Tests for mcpcrunch.conformance.reporter
"""
import json, pytest
from mcpcrunch.conformance.models import ConformanceReport, ConformanceTestResult, TestCategory, TestStatus
from mcpcrunch.conformance.reporter import export_json, print_report

def _mixed():
    return ConformanceReport.from_results([
        ConformanceTestResult(test_id="CT-3.8.1", test_name="A", category=TestCategory.SPEC_INTEGRITY, status=TestStatus.PASSED, expected="V", actual="V"),
        ConformanceTestResult(test_id="CT-3.1.2", test_name="B", category=TestCategory.SCHEMA_INPUT, entity="tool.x", status=TestStatus.FAILED, expected="E", actual="S"),
        ConformanceTestResult(test_id="CT-3.6.3", test_name="C", category=TestCategory.SECURITY, status=TestStatus.SKIPPED, message="No creds"),
        ConformanceTestResult(test_id="CT-3.7.1", test_name="D", category=TestCategory.SERVER_CONTRACT, status=TestStatus.ERROR, message="Refused"),
    ], server_url="http://localhost:3000", spec_version="1.0.0", duration_ms=100.0)

class TestJsonExport:
    def test_valid_json(self):
        data = json.loads(export_json(_mixed()))
        assert data["summary"]["total_tests"] == 4
        assert data["summary"]["passed"] == 1
        assert data["summary"]["failed"] == 1
        assert len(data["failures"]) == 2
    def test_result_fields(self):
        data = json.loads(export_json(_mixed()))
        for r in data["results"]:
            for k in ("test_id","test_name","category","status"):
                assert k in r
    def test_metadata(self):
        data = json.loads(export_json(_mixed()))
        assert data["server_url"] == "http://localhost:3000"
        assert data["spec_version"] == "1.0.0"
    def test_empty(self):
        data = json.loads(export_json(ConformanceReport.from_results([])))
        assert data["summary"]["total_tests"] == 0
    def test_file_export(self, tmp_path):
        p = str(tmp_path / "r.json")
        export_json(_mixed(), p)
        with open(p) as f:
            assert json.load(f)["summary"]["total_tests"] == 4

class TestPrintReport:
    def test_no_crash_mixed(self): print_report(_mixed())
    def test_no_crash_empty(self): print_report(ConformanceReport.from_results([]))
    def test_no_crash_all_pass(self):
        r = ConformanceReport.from_results([
            ConformanceTestResult(test_id=f"CT-{i}", test_name=f"T{i}", category=TestCategory.SPEC_INTEGRITY, status=TestStatus.PASSED) for i in range(5)
        ])
        print_report(r)
