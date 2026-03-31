"""
Conformance Test Suite — Runner

Orchestrates all conformance tests. Usable as both a Python API and via CLI.

Python API Usage:
    from mcpcrunch.conformance import ConformanceRunner, AuthConfig

    runner = ConformanceRunner(
        spec_path="myspec.json",
        server_url="http://localhost:3000",
        schema_path="schema.json",
        auth=AuthConfig(bearer_token="my-token"),
    )
    report = runner.run_all()
    print(report.summary.pass_rate)

    # Static-only (no server needed):
    report = runner.run_static()

    # Single category:
    from mcpcrunch.conformance.models import TestCategory
    report = runner.run_category(TestCategory.SCHEMA_INPUT)
"""

import json
import os
import time
from typing import Any, Dict, List, Optional

from .models import (
    AuthConfig,
    ConformanceReport,
    ConformanceTestResult,
    TestCategory,
    TestStatus,
)
from .client import MCPClient


class ConformanceRunner:
    """
    Orchestrates all MCP conformance tests.

    Can be used as a Python API or driven by the CLI.
    """

    def __init__(
        self,
        spec_path: str,
        server_url: Optional[str] = None,
        schema_path: Optional[str] = None,
        auth: Optional[AuthConfig] = None,
        timeout: float = 10.0,
    ):
        """
        Initialize the conformance runner.

        Args:
            spec_path: Path to the OpenMCP spec JSON file.
            server_url: URL of the MCP server to test against (required for runtime tests).
            schema_path: Path to the OpenMCP JSON Schema (for meta-validation).
            auth: Authentication configuration (pass via AuthConfig or CLI flags).
            timeout: Per-request timeout in seconds.
        """
        # Load spec
        with open(spec_path, "r") as f:
            self.spec: Dict[str, Any] = json.load(f)

        # Load schema (for CT-3.8.1)
        self.schema: Optional[Dict[str, Any]] = None
        if schema_path and os.path.exists(schema_path):
            with open(schema_path, "r") as f:
                self.schema = json.load(f)

        self.server_url = server_url
        self.auth = auth or AuthConfig()
        self.timeout = timeout
        self.spec_version = self.spec.get("openmcp", "unknown")

    def _get_client(self) -> MCPClient:
        """Create an MCP client (requires server_url)."""
        if not self.server_url:
            raise ValueError("server_url is required for runtime conformance tests")
        return MCPClient(self.server_url, auth=self.auth, timeout=self.timeout)

    def run_all(self) -> ConformanceReport:
        """
        Run the full conformance test suite.

        Runs static tests first, then runtime tests if a server_url is provided.
        """
        start = time.monotonic()
        all_results: List[ConformanceTestResult] = []

        # Always run static tests
        all_results.extend(self._run_static_tests())

        # Run runtime tests if server is available
        if self.server_url:
            all_results.extend(self._run_runtime_tests())

        duration = (time.monotonic() - start) * 1000
        return ConformanceReport.from_results(
            all_results,
            server_url=self.server_url,
            spec_version=self.spec_version,
            duration_ms=duration,
        )

    def run_static(self) -> ConformanceReport:
        """Run only static tests (CT-3.8.x) — no server required."""
        start = time.monotonic()
        results = self._run_static_tests()
        duration = (time.monotonic() - start) * 1000
        return ConformanceReport.from_results(
            results,
            spec_version=self.spec_version,
            duration_ms=duration,
        )

    def run_category(self, category: TestCategory) -> ConformanceReport:
        """Run tests for a specific category only."""
        start = time.monotonic()
        results: List[ConformanceTestResult] = []

        if category == TestCategory.SPEC_INTEGRITY:
            results = self._run_static_tests()
        elif self.server_url:
            client = self._get_client()
            try:
                results = self._run_category_tests(client, category)
            finally:
                client.close()
        else:
            raise ValueError(f"server_url required for runtime category: {category.value}")

        duration = (time.monotonic() - start) * 1000
        return ConformanceReport.from_results(
            results,
            server_url=self.server_url,
            spec_version=self.spec_version,
            duration_ms=duration,
        )

    def _run_static_tests(self) -> List[ConformanceTestResult]:
        """Run CT-3.8 spec integrity tests."""
        from .tests import spec_integrity
        return spec_integrity.run_all(self.spec, self.schema)

    def _run_runtime_tests(self) -> List[ConformanceTestResult]:
        """Run all runtime test categories."""
        client = self._get_client()
        results: List[ConformanceTestResult] = []

        try:
            for category in TestCategory:
                if category == TestCategory.SPEC_INTEGRITY:
                    continue  # Already run in static
                results.extend(self._run_category_tests(client, category))
        finally:
            client.close()

        return results

    def _run_category_tests(
        self, client: MCPClient, category: TestCategory
    ) -> List[ConformanceTestResult]:
        """Run tests for a specific category."""
        if category == TestCategory.SCHEMA_INPUT:
            from .tests import schema_input
            results = schema_input.run_all(client, self.spec, "tools")
            # Also run for prompts
            results.extend(schema_input.run_all(client, self.spec, "prompts"))
            return results

        elif category == TestCategory.SCHEMA_OUTPUT:
            from .tests import schema_output
            results = schema_output.run_all(client, self.spec, "tools")
            results.extend(schema_output.run_all(client, self.spec, "prompts"))
            return results

        elif category == TestCategory.TOOL_CONTRACT:
            from .tests import tool_contract
            return tool_contract.run_all(client, self.spec)

        elif category == TestCategory.PROMPT_CONTRACT:
            from .tests import prompt_contract
            return prompt_contract.run_all(client, self.spec)

        elif category == TestCategory.RESOURCE_CONTRACT:
            from .tests import resource_contract
            return resource_contract.run_all(client, self.spec)

        elif category == TestCategory.SECURITY:
            from .tests import security
            return security.run_all(client, self.spec, self.auth)

        elif category == TestCategory.SERVER_CONTRACT:
            from .tests import server_contract
            return server_contract.run_all(client, self.spec)

        elif category == TestCategory.ERROR_HANDLING:
            from .tests import error_handling
            return error_handling.run_all(client, self.spec)

        elif category == TestCategory.DETERMINISM:
            from .tests import determinism
            return determinism.run_all(client, self.spec)

        return []
