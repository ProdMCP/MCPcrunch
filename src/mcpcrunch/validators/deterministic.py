import json
import re
import os
from typing import List, Dict, Any, Optional
import jsonschema
from ..models import ValidationIssue, Severity, ValidationRule

class DeterministicValidator:
    def __init__(self, schema_path: str):
        if os.path.exists(schema_path):
            with open(schema_path, 'r') as f:
                self.base_schema = json.load(f)
        else:
            self.base_schema = {}
        
        self.rules = {
            "OMCP-FMT-001": ValidationRule(id="OMCP-FMT-001", category="Format", name="Root Versioning", description="Verify openmcp version matches semver", severity=Severity.CRITICAL),
            "OMCP-FMT-002": ValidationRule(id="OMCP-FMT-002", category="Format", name="Metadata Completeness", description="Verify info title and version", severity=Severity.HIGH),
            "OMCP-FMT-003": ValidationRule(id="OMCP-FMT-003", category="Format", name="Server URI Strictness", description="Verify servers.url format", severity=Severity.HIGH),
            "OMCP-FMT-004": ValidationRule(id="OMCP-FMT-004", category="Format", name="$ref Integrity", description="Ensure all $ref pointers resolve", severity=Severity.HIGH),
            "OMCP-FMT-005": ValidationRule(id="OMCP-FMT-005", category="Format", name="Payload Size", description="Warn if spec > 1MB", severity=Severity.MEDIUM),
            "OMCP-FMT-006": ValidationRule(id="OMCP-FMT-006", category="Format", name="Unique IDs", description="Unique capability names", severity=Severity.HIGH),
            "OMCP-DAT-001": ValidationRule(id="OMCP-DAT-001", category="Data", name="Strict Objects", description="Input/Prompt must have additionalProperties: false", severity=Severity.CRITICAL),
            "OMCP-DAT-002": ValidationRule(id="OMCP-DAT-002", category="Data", name="Object Properties", description="Schemas must define properties", severity=Severity.CRITICAL),
            "OMCP-DAT-003": ValidationRule(id="OMCP-DAT-003", category="Data", name="String Boundaries", description="Strings must have maxLength", severity=Severity.HIGH),
            "OMCP-DAT-004": ValidationRule(id="OMCP-DAT-004", category="Data", name="Regex Patterns", description="Patterns for paths/URLs", severity=Severity.HIGH),
            "OMCP-DAT-005": ValidationRule(id="OMCP-DAT-005", category="Data", name="Context Window Protection", description="Arrays must have maxItems", severity=Severity.HIGH),
            "OMCP-DAT-006": ValidationRule(id="OMCP-DAT-006", category="Data", name="Numeric Bounds", description="Numbers should have min/max", severity=Severity.MEDIUM),
            "OMCP-SEC-001": ValidationRule(id="OMCP-SEC-001", category="Security", name="Security Binding", description="Valid security scheme mapping", severity=Severity.CRITICAL),
            "OMCP-SEC-002": ValidationRule(id="OMCP-SEC-002", category="Security", name="No Query API Keys", description="API keys must not be in query", severity=Severity.CRITICAL),
            "OMCP-SEC-003": ValidationRule(id="OMCP-SEC-003", category="Security", name="Auth Enforcement", description="Flag empty security", severity=Severity.HIGH),
            "OMCP-SEC-005": ValidationRule(id="OMCP-SEC-005", category="Security", name="Transport Safety", description="Require HTTPS/WSS", severity=Severity.HIGH),
            "OMCP-ADV-005": ValidationRule(id="OMCP-ADV-005", category="Security", name="Localhost Binding", description="Flag localhost servers", severity=Severity.HIGH),
        }

    def validate(self, spec: Dict[str, Any], spec_source: Optional[str] = None) -> List[ValidationIssue]:
        issues = []
        
        # OMCP-FMT-005: Payload Size
        if spec_source and os.path.getsize(spec_source) > 1024 * 1024:
            issues.append(ValidationIssue(
                rule_id="OMCP-FMT-005",
                path="$",
                message="Specification file exceeds 1MB, potentially causing LLM context window pressure.",
                severity=Severity.MEDIUM
            ))

        # OMCP-FMT-001: Root Versioning
        openmcp = spec.get("openmcp", "")
        if not re.match(r"^[0-9]+\.[0-9]+\.[0-9]+$", str(openmcp)):
            issues.append(ValidationIssue(
                rule_id="OMCP-FMT-001",
                path="$.openmcp",
                message=f"Invalid openmcp version: {openmcp}. Must match semver.",
                severity=Severity.CRITICAL
            ))

        # OMCP-FMT-002: Metadata
        info = spec.get("info", {})
        if not info.get("title") or not info.get("version"):
            issues.append(ValidationIssue(
                rule_id="OMCP-FMT-002",
                path="$.info",
                message="Metadata 'title' and 'version' are required.",
                severity=Severity.HIGH
            ))

        # OMCP-FMT-003, OMCP-SEC-005 & OMCP-ADV-005: Servers
        servers = spec.get("servers", [])
        for i, server in enumerate(servers):
            url = server.get("url", "")
            # OMCP-FMT-003: URI Format
            if not url or not (url.startswith("http") or url.startswith("ws")):
                 issues.append(ValidationIssue(
                    rule_id="OMCP-FMT-003",
                    path=f"$.servers[{i}].url",
                    message="Server URL must be a valid http/ws URI.",
                    severity=Severity.HIGH
                ))
            
            # OMCP-SEC-005: Transport Safety
            if url.startswith("http://") or url.startswith("ws://"):
                 issues.append(ValidationIssue(
                    rule_id="OMCP-SEC-005",
                    path=f"$.servers[{i}].url",
                    message="Insecure transport (http/ws) detected. Use https/wss for production.",
                    severity=Severity.HIGH
                ))

            # OMCP-ADV-005: Localhost Binding
            if any(h in url for h in ["localhost", "127.0.0.1", "0.0.0.0"]):
                issues.append(ValidationIssue(
                    rule_id="OMCP-ADV-005",
                    path=f"$.servers[{i}].url",
                    message="Server is bound to localhost, posing SSRF risks.",
                    severity=Severity.HIGH
                ))

        # OMCP-SEC-002: Security Schemes
        components = spec.get("components", {})
        sec_schemes = components.get("securitySchemes", {})
        for name, scheme in sec_schemes.items():
            if scheme.get("type") == "apiKey" and scheme.get("in") == "query":
                issues.append(ValidationIssue(
                    rule_id="OMCP-SEC-002",
                    path=f"$.components.securitySchemes.{name}",
                    message="API key in query parameters. Exposed in histories.",
                    severity=Severity.CRITICAL
                ))

        # OMCP-SEC-001 & OMCP-SEC-003: Capability Security
        self._validate_security(spec, issues)

        # Recursive schema validation (DAT rules)
        self._validate_schemas(spec, issues)

        return issues

    def _validate_security(self, spec: Dict[str, Any], issues: List[ValidationIssue]):
        sec_schemes = spec.get("components", {}).get("securitySchemes", {})
        
        # OMCP-SEC-001 / SEC-003 for tools
        for tool_name, tool in spec.get("tools", {}).items():
            sec = tool.get("security")
            # OMCP-SEC-003: Auth Enforcement
            if sec is None or (isinstance(sec, list) and len(sec) == 0):
                issues.append(ValidationIssue(
                    rule_id="OMCP-SEC-003",
                    path=f"$.tools.{tool_name}",
                    message="Tool lacks security requirements. Can be invoked autonomously.",
                    severity=Severity.HIGH
                ))
            elif isinstance(sec, list):
                for requirement in sec:
                    for scheme_name in requirement.keys():
                        # OMCP-SEC-001: Security Binding
                        if scheme_name not in sec_schemes:
                            issues.append(ValidationIssue(
                                rule_id="OMCP_SEC-001",
                                path=f"$.tools.{tool_name}.security",
                                message=f"Security scheme '{scheme_name}' not defined in components.",
                                severity=Severity.CRITICAL
                            ))

    def _validate_schemas(self, spec: Dict[str, Any], issues: List[ValidationIssue]):
        # Traverse tools, prompts, resources
        for tool_name, tool in spec.get("tools", {}).items():
            self._check_schema_boundaries(tool.get("input", {}), f"$.tools.{tool_name}.input", issues, is_input=True)
            self._check_schema_boundaries(tool.get("output", {}), f"$.tools.{tool_name}.output", issues, is_input=False)

        for prompt_name, prompt in spec.get("prompts", {}).items():
            self._check_schema_boundaries(prompt.get("input", {}), f"$.prompts.{prompt_name}.input", issues, is_input=True)
            self._check_schema_boundaries(prompt.get("output", {}), f"$.prompts.{prompt_name}.output", issues, is_input=False)

        for res_name, res in spec.get("resources", {}).items():
            self._check_schema_boundaries(res.get("output", {}), f"$.resources.{res_name}.output", issues, is_input=False)

    def _check_schema_boundaries(self, schema: Any, path: str, issues: List[ValidationIssue], is_input: bool):
        if not isinstance(schema, dict): return

        # OMCP-DAT-001: Strict Objects
        if is_input and schema.get("type") == "object":
            if schema.get("additionalProperties") is not False:
                issues.append(ValidationIssue(
                    rule_id="OMCP-DAT-001",
                    path=path,
                    message="Input schema must set 'additionalProperties: false' to prevent prompt injection.",
                    severity=Severity.CRITICAL
                ))

        # OMCP-DAT-002: Object Properties
        if schema.get("type") == "object" and not schema.get("properties"):
            issues.append(ValidationIssue(
                rule_id="OMCP-DAT-002",
                path=path,
                message="Object schema must define 'properties'. Empty object is too flexible.",
                severity=Severity.CRITICAL
            ))

        # OMCP-DAT-003: String Lengths
        if schema.get("type") == "string" and "maxLength" not in schema:
             issues.append(ValidationIssue(
                rule_id="OMCP-DAT-003",
                path=path,
                message="String parameter missing 'maxLength'. Buffer over-reads risk.",
                severity=Severity.HIGH
            ))

        # OMCP-DAT-004: Regex Patterns
        sensitive_keywords = ["path", "url", "cmd", "exec", "sql", "file", "uri"]
        if schema.get("type") == "string" and "pattern" not in schema:
             if any(kw in path.lower() for kw in sensitive_keywords):
                 issues.append(ValidationIssue(
                    rule_id="OMCP-DAT-004",
                    path=path,
                    message="Potentially sensitive string parameter missing 'pattern' restriction.",
                    severity=Severity.HIGH
                ))

        # OMCP-DAT-005: Array Limits
        if schema.get("type") == "array" and "maxItems" not in schema:
             issues.append(ValidationIssue(
                rule_id="OMCP-DAT-005",
                path=path,
                message="Array return missing 'maxItems', risking context window overflow.",
                severity=Severity.HIGH
            ))

        # OMCP-DAT-006: Numeric Bounds
        if schema.get("type") in ["number", "integer"]:
            if "minimum" not in schema or "maximum" not in schema:
                issues.append(ValidationIssue(
                    rule_id="OMCP-DAT-006",
                    path=path,
                    message="Numeric parameter missing 'minimum' or 'maximum' bounds.",
                    severity=Severity.MEDIUM
                ))

        # Recursive check for properties
        for prop_name, prop_schema in schema.get("properties", {}).items():
            self._check_schema_boundaries(prop_schema, f"{path}.properties.{prop_name}", issues, is_input)
