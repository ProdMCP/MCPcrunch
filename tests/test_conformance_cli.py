"""
Tests for the mcpcrunch CLI conformance subcommand.
"""
import subprocess, sys, json, os
import pytest

def test_conformance_help():
    result = subprocess.run(
        [sys.executable, "-m", "mcpcrunch.cli", "conformance", "--help"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "conformance" in result.stdout.lower()
    assert "--server-url" in result.stdout
    assert "--static-only" in result.stdout

def test_conformance_static_only():
    result = subprocess.run(
        [sys.executable, "-m", "mcpcrunch.cli", "conformance",
         "examples/minimal_valid.json", "--schema", "schema.json", "--static-only"],
        capture_output=True, text=True,
    )
    # For minimal_valid.json, some new data quality tests may fail → exit code 1
    assert result.returncode in (0, 1)
    assert "Conformance" in result.stdout

def test_conformance_static_category():
    result = subprocess.run(
        [sys.executable, "-m", "mcpcrunch.cli", "conformance",
         "examples/minimal_valid.json", "--schema", "schema.json",
         "--category", "spec_integrity"],
        capture_output=True, text=True,
    )
    assert result.returncode in (0, 1)

def test_conformance_json_output(tmp_path):
    out = str(tmp_path / "report.json")
    result = subprocess.run(
        [sys.executable, "-m", "mcpcrunch.cli", "conformance",
         "examples/minimal_valid.json", "--schema", "schema.json",
         "--static-only", "--output", out],
        capture_output=True, text=True,
    )
    assert result.returncode in (0, 1)
    with open(out) as f:
        data = json.load(f)
    assert data["summary"]["total_tests"] == 13
    assert "score" in data["summary"]
    assert "grade" in data["summary"]

def test_conformance_missing_spec():
    result = subprocess.run(
        [sys.executable, "-m", "mcpcrunch.cli", "conformance",
         "nonexistent.json", "--static-only"],
        capture_output=True, text=True,
    )
    assert result.returncode != 0

def test_conformance_requires_server_for_runtime():
    result = subprocess.run(
        [sys.executable, "-m", "mcpcrunch.cli", "conformance",
         "examples/minimal_valid.json", "--schema", "schema.json"],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "server-url" in result.stdout.lower() or "server-url" in result.stderr.lower()

def test_original_audit_still_works():
    """Backward-compatible: mcpcrunch spec.json should still work."""
    result = subprocess.run(
        [sys.executable, "-m", "mcpcrunch.cli", "--help"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "MCPcrunch" in result.stdout

@pytest.mark.parametrize("example", [
    "minimal_valid.json",
    "vulnerable_security.json",
    "vulnerable_data_quality.json",
])
def test_conformance_on_examples(example):
    path = os.path.join("examples", example)
    if not os.path.exists(path):
        pytest.skip(f"{example} not found")
    result = subprocess.run(
        [sys.executable, "-m", "mcpcrunch.cli", "conformance",
         path, "--schema", "schema.json", "--static-only"],
        capture_output=True, text=True,
    )
    # Some example specs will fail new data quality tests → exit code 1 is OK
    assert result.returncode in (0, 1)
