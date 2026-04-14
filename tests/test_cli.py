"""Tests for the mcpcrunch CLI (audit subcommand)."""
import json
import subprocess
import sys
import tempfile
import os

CLEAN_SPEC = {
    "openmcp": "1.0.0",
    "info": {"title": "T", "version": "1.0.0"},
    "servers": [{"url": "https://api.example.com"}],
}

VULNERABLE_SPEC = {
    "openmcp": "1.0",           # invalid version → OMCP-FMT-001
    "info": {"title": "Bad"},   # missing version  → OMCP-FMT-002
}


def _run_cli(*args) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "mcpcrunch.cli", "--schema", "schema.json", *args],
        capture_output=True, text=True, cwd=os.path.dirname(__file__) + "/..",
    )


def _write_tmp(spec: dict) -> str:
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    json.dump(spec, f)
    f.close()
    return f.name


def test_cli_help():
    result = _run_cli("--help")
    assert result.returncode == 0
    assert "MCPcrunch" in result.stdout


def test_cli_clean_spec_exits_zero():
    path = _write_tmp(CLEAN_SPEC)
    try:
        result = _run_cli(path)
        assert result.returncode == 0
        assert "Audit Summary" in result.stdout
        assert "100" in result.stdout
    finally:
        os.unlink(path)


def test_cli_vulnerable_spec_exits_zero_but_shows_issues():
    """CLI should still exit 0 (audit completed), but output issues."""
    path = _write_tmp(VULNERABLE_SPEC)
    try:
        result = _run_cli(path)
        assert result.returncode == 0
        assert "Audit Summary" in result.stdout
        # Should show issues
        assert "OMCP-FMT-001" in result.stdout or "OMCP-FMT-002" in result.stdout
    finally:
        os.unlink(path)


def test_cli_output_includes_global_score():
    path = _write_tmp(CLEAN_SPEC)
    try:
        result = _run_cli(path)
        assert "Global score:" in result.stdout
        assert "Security score:" in result.stdout
        assert "Data validation score:" in result.stdout
    finally:
        os.unlink(path)


def test_cli_output_includes_capability_table():
    """The per-capability table should appear when capabilities are defined."""
    spec = {**CLEAN_SPEC, "tools": {"my_tool": {
        "input": {"type": "object", "additionalProperties": False,
                  "properties": {"q": {"type": "string", "maxLength": 10}}},
        "output": {"type": "object", "additionalProperties": False},
    }}}
    path = _write_tmp(spec)
    try:
        result = _run_cli(path)
        assert result.returncode == 0
        assert "Tool / Resource / Prompt Scores" in result.stdout
        assert "my_tool" in result.stdout
    finally:
        os.unlink(path)


def test_cli_missing_spec_exits_nonzero():
    result = _run_cli("nonexistent_spec_12345.json")
    assert result.returncode != 0
