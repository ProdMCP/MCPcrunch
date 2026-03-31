"""
Tests for runtime conformance test modules using a mock MCP client.

Tests CT-3.1.x (schema_input), CT-3.2.x (schema_output),
CT-3.3.x (tool_contract), CT-3.6.x (security), CT-3.9.x (error_handling),
and CT-3.10.x (determinism) test implementations with mocked server responses.
"""

import pytest
from unittest.mock import MagicMock
from mcpcrunch.conformance.models import TestCategory, TestStatus


# ── Mock Client ────────────────────────────────────────────

def make_mock_client(
    tool_response=None,
    error_response=None,
    prompt_response=None,
    resource_response=None,
):
    """Create a mock MCPClient with configurable responses."""
    client = MagicMock()

    if error_response:
        client.call_tool.return_value = {"jsonrpc": "2.0", "id": 1, "error": error_response}
        client.get_prompt.return_value = {"jsonrpc": "2.0", "id": 1, "error": error_response}
        client.read_resource.return_value = {"jsonrpc": "2.0", "id": 1, "error": error_response}
    elif tool_response is not None:
        client.call_tool.return_value = {"jsonrpc": "2.0", "id": 1, "result": tool_response}
        client.get_prompt.return_value = {"jsonrpc": "2.0", "id": 1, "result": prompt_response or tool_response}
        client.read_resource.return_value = {"jsonrpc": "2.0", "id": 1, "result": resource_response or tool_response}
    else:
        client.call_tool.return_value = {"jsonrpc": "2.0", "id": 1, "result": {"message": "ok"}}
        client.get_prompt.return_value = {"jsonrpc": "2.0", "id": 1, "result": {"content": "done"}}
        client.read_resource.return_value = {"jsonrpc": "2.0", "id": 1, "result": {"data": "info"}}

    client._send_jsonrpc_no_auth = MagicMock(return_value={"jsonrpc": "2.0", "id": 1, "error": {"code": -32600, "message": "Unauthorized"}})
    client._send_jsonrpc_bad_auth = MagicMock(return_value={"jsonrpc": "2.0", "id": 1, "error": {"code": -32600, "message": "Invalid credentials"}})
    client.server_url = "http://localhost:3000"

    return client


TOOL_SPEC = {
    "openmcp": "1.0.0",
    "info": {"title": "Test", "version": "1.0.0"},
    "tools": {
        "echo": {
            "description": "Echo tool",
            "input": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "maxLength": 100},
                    "count": {"type": "integer", "minimum": 1, "maximum": 10},
                },
                "required": ["message", "count"],
                "additionalProperties": False,
            },
            "output": {
                "type": "object",
                "properties": {
                    "response": {"type": "string"},
                },
                "required": ["response"],
            },
        },
    },
}

SECURED_SPEC = {
    "openmcp": "1.0.0",
    "info": {"title": "Test", "version": "1.0.0"},
    "tools": {
        "secure_tool": {
            "description": "Secured",
            "input": {"type": "object", "properties": {"x": {"type": "string"}}, "required": ["x"]},
            "output": {"type": "object", "properties": {"y": {"type": "string"}}},
            "security": [{"bearerAuth": ["admin"]}],
        },
    },
    "components": {
        "securitySchemes": {
            "bearerAuth": {"type": "http", "scheme": "bearer"},
        },
    },
}


# ── CT-3.1 Schema Input Tests ──────────────────────────────

class TestSchemaInputTests:
    def test_3_1_1_valid_input_pass(self):
        from mcpcrunch.conformance.tests.schema_input import test_3_1_1_valid_input
        client = make_mock_client(tool_response={"response": "hello"})
        result = test_3_1_1_valid_input(
            client.call_tool, "echo",
            TOOL_SPEC["tools"]["echo"]["input"],
            TOOL_SPEC["tools"]["echo"]["output"],
            "tool.echo",
        )
        assert result.status == TestStatus.PASSED
        assert result.test_id == "CT-3.1.1"

    def test_3_1_1_server_error_fails(self):
        from mcpcrunch.conformance.tests.schema_input import test_3_1_1_valid_input
        client = make_mock_client(error_response={"code": -1, "message": "Internal error"})
        result = test_3_1_1_valid_input(
            client.call_tool, "echo",
            TOOL_SPEC["tools"]["echo"]["input"],
            TOOL_SPEC["tools"]["echo"]["output"],
            "tool.echo",
        )
        assert result.status == TestStatus.FAILED

    def test_3_1_2_missing_required(self):
        from mcpcrunch.conformance.tests.schema_input import test_3_1_2_missing_required
        client = make_mock_client(error_response={"code": -32602, "message": "Missing field"})
        results = test_3_1_2_missing_required(
            client.call_tool, "echo",
            TOOL_SPEC["tools"]["echo"]["input"],
            "tool.echo",
        )
        assert len(results) == 2  # message and count
        assert all(r.status == TestStatus.PASSED for r in results)

    def test_3_1_2_missing_required_server_accepts_fails(self):
        from mcpcrunch.conformance.tests.schema_input import test_3_1_2_missing_required
        client = make_mock_client(tool_response={"response": "ok"})
        results = test_3_1_2_missing_required(
            client.call_tool, "echo",
            TOOL_SPEC["tools"]["echo"]["input"],
            "tool.echo",
        )
        assert all(r.status == TestStatus.FAILED for r in results)

    def test_3_1_3_additional_properties_strict_reject(self):
        from mcpcrunch.conformance.tests.schema_input import test_3_1_3_additional_properties
        client = make_mock_client(error_response={"code": -32602, "message": "Extra props"})
        result = test_3_1_3_additional_properties(
            client.call_tool, "echo",
            TOOL_SPEC["tools"]["echo"]["input"],
            "tool.echo",
        )
        assert result.status == TestStatus.PASSED

    def test_3_1_3_additional_properties_strict_accept_fails(self):
        from mcpcrunch.conformance.tests.schema_input import test_3_1_3_additional_properties
        client = make_mock_client(tool_response={"response": "ok"})
        result = test_3_1_3_additional_properties(
            client.call_tool, "echo",
            TOOL_SPEC["tools"]["echo"]["input"],
            "tool.echo",
        )
        assert result.status == TestStatus.FAILED  # Should reject when additionalProperties=false

    def test_3_1_4_type_violations(self):
        from mcpcrunch.conformance.tests.schema_input import test_3_1_4_type_violations
        client = make_mock_client(error_response={"code": -32602, "message": "Type error"})
        results = test_3_1_4_type_violations(
            client.call_tool, "echo",
            TOOL_SPEC["tools"]["echo"]["input"],
            "tool.echo",
        )
        assert len(results) >= 2  # message (string→int) and count (integer→string)
        assert all(r.status == TestStatus.PASSED for r in results)

    def test_3_1_5_constraint_violations(self):
        from mcpcrunch.conformance.tests.schema_input import test_3_1_5_constraint_violations
        client = make_mock_client(error_response={"code": -32602, "message": "Constraint error"})
        results = test_3_1_5_constraint_violations(
            client.call_tool, "echo",
            TOOL_SPEC["tools"]["echo"]["input"],
            "tool.echo",
        )
        assert len(results) >= 2  # maxLength for message, minimum/maximum for count
        assert all(r.status == TestStatus.PASSED for r in results)

    def test_3_1_6_null_violations(self):
        from mcpcrunch.conformance.tests.schema_input import test_3_1_6_nullability_violations
        client = make_mock_client(error_response={"code": -32602, "message": "Null error"})
        results = test_3_1_6_nullability_violations(
            client.call_tool, "echo",
            TOOL_SPEC["tools"]["echo"]["input"],
            "tool.echo",
        )
        assert len(results) == 2  # message and count are non-nullable
        assert all(r.status == TestStatus.PASSED for r in results)

    def test_run_all(self):
        from mcpcrunch.conformance.tests.schema_input import run_all
        client = make_mock_client(error_response={"code": -32602, "message": "Error"})
        results = run_all(client, TOOL_SPEC, "tools")
        assert len(results) > 0
        assert all(r.category == TestCategory.SCHEMA_INPUT for r in results)


# ── CT-3.2 Schema Output Tests ─────────────────────────────

class TestSchemaOutputTests:
    def test_3_2_1_valid_output_passes(self):
        from mcpcrunch.conformance.tests.schema_output import test_3_2_1_output_schema_validation
        client = make_mock_client(tool_response={"response": "hello"})
        result = test_3_2_1_output_schema_validation(
            client.call_tool, "echo",
            TOOL_SPEC["tools"]["echo"]["input"],
            TOOL_SPEC["tools"]["echo"]["output"],
            "tool.echo",
        )
        assert result.status == TestStatus.PASSED

    def test_3_2_2_missing_output_passes(self):
        from mcpcrunch.conformance.tests.schema_output import test_3_2_2_missing_output_fields
        client = make_mock_client(tool_response={"response": "hello"})
        result = test_3_2_2_missing_output_fields(
            client.call_tool, "echo",
            TOOL_SPEC["tools"]["echo"]["input"],
            TOOL_SPEC["tools"]["echo"]["output"],
            "tool.echo",
        )
        assert result.status == TestStatus.PASSED

    def test_3_2_2_missing_output_fails(self):
        from mcpcrunch.conformance.tests.schema_output import test_3_2_2_missing_output_fields
        # Response missing "response" field
        client = make_mock_client(tool_response={"other": "data"})
        result = test_3_2_2_missing_output_fields(
            client.call_tool, "echo",
            TOOL_SPEC["tools"]["echo"]["input"],
            TOOL_SPEC["tools"]["echo"]["output"],
            "tool.echo",
        )
        assert result.status == TestStatus.FAILED

    def test_3_2_5_deterministic(self):
        from mcpcrunch.conformance.tests.schema_output import test_3_2_5_deterministic_structure
        client = make_mock_client(tool_response={"response": "hello"})
        result = test_3_2_5_deterministic_structure(
            client.call_tool, "echo",
            TOOL_SPEC["tools"]["echo"]["input"],
            "tool.echo",
            runs=3,
        )
        assert result.status == TestStatus.PASSED

    def test_run_all(self):
        from mcpcrunch.conformance.tests.schema_output import run_all
        client = make_mock_client(tool_response={"response": "ok"})
        results = run_all(client, TOOL_SPEC, "tools")
        assert len(results) > 0
        assert all(r.category == TestCategory.SCHEMA_OUTPUT for r in results)


# ── CT-3.3 Tool Contract Tests ─────────────────────────────

class TestToolContractTests:
    def test_3_3_1_unknown_tool(self):
        from mcpcrunch.conformance.tests.tool_contract import test_3_3_1_unknown_tool
        client = make_mock_client(error_response={"code": -32601, "message": "Tool not found"})
        result = test_3_3_1_unknown_tool(client)
        assert result.test_id == "CT-3.3.1"
        assert result.status == TestStatus.PASSED

    def test_3_3_1_unknown_tool_server_accepts_fails(self):
        from mcpcrunch.conformance.tests.tool_contract import test_3_3_1_unknown_tool
        client = make_mock_client(tool_response={"result": "bad"})
        result = test_3_3_1_unknown_tool(client)
        assert result.status == TestStatus.FAILED

    def test_3_3_2_missing_input(self):
        from mcpcrunch.conformance.tests.tool_contract import test_3_3_2_missing_input
        client = make_mock_client(error_response={"code": -32602, "message": "Missing input"})
        result = test_3_3_2_missing_input(
            client, "echo", TOOL_SPEC["tools"]["echo"]["input"], "tool.echo"
        )
        assert result.status == TestStatus.PASSED

    def test_3_3_3_partial_input(self):
        from mcpcrunch.conformance.tests.tool_contract import test_3_3_3_partial_input
        client = make_mock_client(error_response={"code": -32602, "message": "Missing fields"})
        result = test_3_3_3_partial_input(
            client, "echo", TOOL_SPEC["tools"]["echo"]["input"], "tool.echo"
        )
        assert result.status == TestStatus.PASSED

    def test_3_3_4_mapping_integrity(self):
        from mcpcrunch.conformance.tests.tool_contract import test_3_3_4_input_output_mapping
        client = make_mock_client(tool_response={"response": "ok"})
        result = test_3_3_4_input_output_mapping(
            client, "echo",
            TOOL_SPEC["tools"]["echo"]["input"],
            TOOL_SPEC["tools"]["echo"]["output"],
            "tool.echo",
        )
        assert result.status == TestStatus.PASSED

    def test_run_all(self):
        from mcpcrunch.conformance.tests.tool_contract import run_all
        client = make_mock_client(error_response={"code": -32601, "message": "Error"})
        results = run_all(client, TOOL_SPEC)
        assert len(results) >= 4  # at least 1 unknown + 3 per tool


# ── CT-3.6 Security Tests ─────────────────────────────────

class TestSecurityTests:
    def test_3_6_1_missing_auth(self):
        from mcpcrunch.conformance.tests.security import test_3_6_1_missing_auth
        client = make_mock_client()
        result = test_3_6_1_missing_auth(
            client, "secure_tool",
            SECURED_SPEC["tools"]["secure_tool"]["input"],
            "tool.secure_tool",
        )
        assert result.test_id == "CT-3.6.1"
        assert result.status == TestStatus.PASSED  # mock returns error for no auth

    def test_3_6_2_invalid_credentials(self):
        from mcpcrunch.conformance.tests.security import test_3_6_2_invalid_credentials
        client = make_mock_client()
        result = test_3_6_2_invalid_credentials(
            client, "secure_tool",
            SECURED_SPEC["tools"]["secure_tool"]["input"],
            "tool.secure_tool",
        )
        assert result.test_id == "CT-3.6.2"
        assert result.status == TestStatus.PASSED

    def test_3_6_4_declaration_consistency_pass(self):
        from mcpcrunch.conformance.tests.security import test_3_6_4_security_declaration_consistency
        result = test_3_6_4_security_declaration_consistency(SECURED_SPEC)
        assert result.status == TestStatus.PASSED

    def test_3_6_4_declaration_consistency_fail(self):
        from mcpcrunch.conformance.tests.security import test_3_6_4_security_declaration_consistency
        bad_spec = {
            "tools": {
                "t": {"security": [{"missingScheme": []}]},
            },
            "components": {"securitySchemes": {}},
        }
        result = test_3_6_4_security_declaration_consistency(bad_spec)
        assert result.status == TestStatus.FAILED
        assert "missingScheme" in result.actual

    def test_run_all(self):
        from mcpcrunch.conformance.tests.security import run_all
        client = make_mock_client()
        results = run_all(client, SECURED_SPEC)
        assert len(results) >= 3  # 3.6.4 static + 3.6.1, 3.6.2, 3.6.3 for the secured tool


# ── CT-3.9 Error Handling Tests ─────────────────────────────

class TestErrorHandlingTests:
    def test_3_9_1_invalid_input_returns_error(self):
        from mcpcrunch.conformance.tests.error_handling import test_3_9_1_invalid_input_returns_error
        client = make_mock_client(error_response={"code": -32602, "message": "Invalid"})
        result = test_3_9_1_invalid_input_returns_error(
            client, "echo", TOOL_SPEC["tools"]["echo"]["input"], "tool.echo"
        )
        assert result.status == TestStatus.PASSED

    def test_3_9_2_error_structure_valid(self):
        from mcpcrunch.conformance.tests.error_handling import test_3_9_2_error_structure
        client = make_mock_client(error_response={"code": -32602, "message": "Bad input"})
        result = test_3_9_2_error_structure(
            client, "echo", TOOL_SPEC["tools"]["echo"]["input"], "tool.echo"
        )
        assert result.status == TestStatus.PASSED

    def test_3_9_2_error_structure_missing_code(self):
        from mcpcrunch.conformance.tests.error_handling import test_3_9_2_error_structure
        client = make_mock_client(error_response={"message": "Bad input"})  # Missing code
        result = test_3_9_2_error_structure(
            client, "echo", TOOL_SPEC["tools"]["echo"]["input"], "tool.echo"
        )
        assert result.status == TestStatus.FAILED

    def test_3_9_3_no_silent_failures_pass(self):
        from mcpcrunch.conformance.tests.error_handling import test_3_9_3_no_silent_failures
        client = make_mock_client(tool_response={"response": "ok"})
        result = test_3_9_3_no_silent_failures(
            client, "echo", TOOL_SPEC["tools"]["echo"]["input"], "tool.echo"
        )
        assert result.status == TestStatus.PASSED

    def test_3_9_3_both_result_and_error_fails(self):
        from mcpcrunch.conformance.tests.error_handling import test_3_9_3_no_silent_failures
        client = MagicMock()
        client.call_tool.return_value = {
            "jsonrpc": "2.0", "id": 1,
            "result": {"data": "ok"},
            "error": {"code": -1, "message": "Also an error"},
        }
        result = test_3_9_3_no_silent_failures(
            client, "echo", TOOL_SPEC["tools"]["echo"]["input"], "tool.echo"
        )
        assert result.status == TestStatus.FAILED

    def test_run_all(self):
        from mcpcrunch.conformance.tests.error_handling import run_all
        client = make_mock_client(error_response={"code": -32602, "message": "Error"})
        results = run_all(client, TOOL_SPEC)
        assert len(results) == 3  # 3.9.1, 3.9.2, 3.9.3 for echo


# ── CT-3.10 Determinism Tests ──────────────────────────────

class TestDeterminismTests:
    def test_3_10_1_consistent_shape_passes(self):
        from mcpcrunch.conformance.tests.determinism import test_3_10_1_schema_determinism
        client = make_mock_client(tool_response={"response": "ok"})
        result = test_3_10_1_schema_determinism(
            client, "echo", TOOL_SPEC["tools"]["echo"]["input"], "tool.echo", runs=3
        )
        assert result.status == TestStatus.PASSED

    def test_3_10_2_contract_stability_passes(self):
        from mcpcrunch.conformance.tests.determinism import test_3_10_2_contract_stability
        # Valid input always succeeds
        client = make_mock_client(tool_response={"response": "ok"})
        result = test_3_10_2_contract_stability(
            client, "echo", TOOL_SPEC["tools"]["echo"]["input"], "tool.echo", runs=3
        )
        assert result.status == TestStatus.PASSED

    def test_3_10_3_no_undeclared_fields_passes(self):
        from mcpcrunch.conformance.tests.determinism import test_3_10_3_no_undeclared_fields
        client = make_mock_client(tool_response={"response": "ok"})
        result = test_3_10_3_no_undeclared_fields(
            client, "echo",
            TOOL_SPEC["tools"]["echo"]["input"],
            TOOL_SPEC["tools"]["echo"]["output"],
            "tool.echo", runs=3,
        )
        assert result.status == TestStatus.PASSED

    def test_run_all(self):
        from mcpcrunch.conformance.tests.determinism import run_all
        client = make_mock_client(tool_response={"response": "ok"})
        results = run_all(client, TOOL_SPEC, runs=2)
        assert len(results) == 3  # 3 tests per tool
        assert all(r.category == TestCategory.DETERMINISM for r in results)
