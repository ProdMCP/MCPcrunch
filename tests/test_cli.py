import subprocess
import os
import sys

def test_cli_help():
    result = subprocess.run([sys.executable, "-m", "mcpcrunch.cli", "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "MCPcrunch" in result.stdout

def test_cli_audit_vulnerable():
    # Use the sample_spec.json I created earlier
    result = subprocess.run([sys.executable, "-m", "mcpcrunch.cli", "sample_spec.json", "--schema", "schema.json"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "Audit Summary" in result.stdout
    assert "Overall Security Score" in result.stdout

def test_cli_audit_fixed():
    # Use the fixed_spec.json I created earlier
    result = subprocess.run([sys.executable, "-m", "mcpcrunch.cli", "fixed_spec.json", "--schema", "schema.json"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "Audit Summary" in result.stdout
