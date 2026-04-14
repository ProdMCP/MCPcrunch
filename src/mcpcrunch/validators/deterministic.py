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
            "OMCP-DAT-007": ValidationRule(id="OMCP-DAT-007", category="Data", name="Schema Type Required", description="Schemas must define a type", severity=Severity.MEDIUM),
            "OMCP-DAT-008": ValidationRule(id="OMCP-DAT-008", category="Data", name="Loose Nullable", description="Primitive anyOf/oneOf must set additionalProperties: false", severity=Severity.MEDIUM),
            "OMCP-DAT-009": ValidationRule(id="OMCP-DAT-009", category="Data", name="String Pattern", description="String schemas should define a pattern", severity=Severity.MEDIUM),
            "OMCP-SEC-001": ValidationRule(id="OMCP-SEC-001", category="Security", name="Security Binding", description="Valid security scheme mapping", severity=Severity.CRITICAL),
            "OMCP-SEC-002": ValidationRule(id="OMCP-SEC-002", category="Security", name="No Query API Keys", description="API keys must not be in query", severity=Severity.CRITICAL),
            "OMCP-SEC-003": ValidationRule(id="OMCP-SEC-003", category="Security", name="Auth Enforcement", description="Flag empty security", severity=Severity.HIGH),
            "OMCP-SEC-005": ValidationRule(id="OMCP-SEC-005", category="Security", name="Transport Safety", description="Require HTTPS/WSS", severity=Severity.HIGH),
            "OMCP-SEC-007": ValidationRule(id="OMCP-SEC-007", category="Security", name="Auth Error Handling", description="Secured tools should define error handling", severity=Severity.MEDIUM),
            "OMCP-SEC-008": ValidationRule(id="OMCP-SEC-008", category="Security", name="Not Acceptable Handling", description="Missing 406 response for content negotiation", severity=Severity.MEDIUM),
            "OMCP-SEC-009": ValidationRule(id="OMCP-SEC-009", category="Security", name="Media Type Handling", description="Missing 415 response for payload validation", severity=Severity.MEDIUM),
            "OMCP-SEC-010": ValidationRule(id="OMCP-SEC-010", category="Security", name="Rate Limit Handling", description="Missing 429 response for rate limiting", severity=Severity.MEDIUM),
            "OMCP-SEC-011": ValidationRule(id="OMCP-SEC-011", category="Security", name="Catch-all Error Handling", description="Missing default error response", severity=Severity.MEDIUM),
            "OMCP-ADV-005": ValidationRule(id="OMCP-ADV-005", category="Security", name="Localhost Binding", description="Flag localhost servers", severity=Severity.HIGH),
            "OMCP-DOC-001": ValidationRule(id="OMCP-DOC-001", category="Documentation", name="Capability Description", description="Tools, prompts, and resources should have a description field", severity=Severity.HIGH),
            "OMCP-DOC-002": ValidationRule(id="OMCP-DOC-002", category="Documentation", name="Response Description", description="Tools, prompts, and resources should document what their response contains", severity=Severity.HIGH),
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

        # OMCP-FMT-001: OpenMCP or OpenAPI Version
        openmcp_version = spec.get("openmcp", "")
        openapi_version = spec.get("openapi", "")
        
        if not openmcp_version and not openapi_version:
             issues.append(ValidationIssue(
                rule_id="OMCP-FMT-001",
                path="$.openmcp",
                message="Missing 'openmcp' or 'openapi' version declaration.",
                severity=Severity.CRITICAL
            ))
        elif openmcp_version and not re.match(r"^\d+\.\d+\.\d+$", str(openmcp_version)):
             issues.append(ValidationIssue(
                rule_id="OMCP-FMT-001",
                path="$.openmcp",
                message=f"Invalid openmcp version: '{openmcp_version}'. Must match semver.",
                severity=Severity.CRITICAL
            ))
        elif openapi_version and not re.match(r"^\d+\.\d+\.\d+$", str(openapi_version)):
             issues.append(ValidationIssue(
                rule_id="OMCP-FMT-001",
                path="$.openapi",
                message=f"Invalid openapi version: '{openapi_version}'. Must match semver.",
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
        has_security = bool(spec.get("components", {}).get("securitySchemes", {}))

        if has_security and not servers:
            issues.append(ValidationIssue(
                rule_id="OMCP-SEC-005",
                path="$.servers",
                message="Security schemes are defined but no explicit HTTPS servers array is configured. Bearer tokens could be transported as cleartext.",
                severity=Severity.CRITICAL
            ))

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
                 severity = Severity.CRITICAL if has_security else Severity.HIGH
                 issues.append(ValidationIssue(
                    rule_id="OMCP-SEC-005",
                    path=f"$.servers[{i}].url",
                    message="Insecure transport (http/ws) detected. If using auth, tokens could be transported as cleartext. Use https/wss for production.",
                    severity=severity
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

        # OMCP-DAT-* rules: Schema boundaries
        self._validate_schemas(spec, issues)

        # OMCP-DOC-*: Documentation quality
        self._validate_documentation(spec, issues)

        return issues

    def _validate_security(self, spec: Dict[str, Any], issues: List[ValidationIssue]):
        sec_schemes = spec.get("components", {}).get("securitySchemes", {})
        
        for tool_name, tool in spec.get("tools", {}).items():
            sec = tool.get("security")
            error_handling = tool.get("error_handling", {})
            
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

                # OMCP_SEC-007: Auth Error Handling (for secured tools only)
                if not error_handling:
                    issues.append(ValidationIssue(
                        rule_id="OMCP-SEC-007",
                        path=f"$.tools.{tool_name}",
                        message="Secured tool has no 'error_handling' defined. Should specify auth failure behavior (401/403 equivalent).",
                        severity=Severity.MEDIUM
                    ))
                else:
                    if "401" not in error_handling or "403" not in error_handling:
                        issues.append(ValidationIssue(
                            rule_id="OMCP-SEC-007",
                            path=f"$.tools.{tool_name}.error_handling",
                            message="Secured tool missing 401/403 in 'error_handling'.",
                            severity=Severity.MEDIUM
                        ))

            # OMCP-SEC-008...OMCP-SEC-011: Protocol Error Handling for ALL tools
            
            # OMCP-SEC-008: 406
            if "406" not in error_handling:
                    issues.append(ValidationIssue(
                    rule_id="OMCP-SEC-008",
                    path=f"$.tools.{tool_name}.error_handling",
                    message="Missing 406 response for content negotiation.",
                    severity=Severity.MEDIUM
                ))

            # OMCP-SEC-009: 415 (tools usually take body)
            if "415" not in error_handling:
                    issues.append(ValidationIssue(
                    rule_id="OMCP-SEC-009",
                    path=f"$.tools.{tool_name}.error_handling",
                    message="Missing 415 response for unsupported media types (payload validation).",
                    severity=Severity.MEDIUM
                ))

            # OMCP-SEC-010: 429
            if "429" not in error_handling:
                    issues.append(ValidationIssue(
                    rule_id="OMCP-SEC-010",
                    path=f"$.tools.{tool_name}.error_handling",
                    message="Missing 429 response for rate limiting.",
                    severity=Severity.MEDIUM
                ))

            # OMCP-SEC-011: default
            if "default" not in error_handling:
                    issues.append(ValidationIssue(
                    rule_id="OMCP-SEC-011",
                    path=f"$.tools.{tool_name}.error_handling",
                    message="Missing default catch-all error response.",
                    severity=Severity.MEDIUM
                ))

        # Check prompts for standard errors
        for prompt_name, prompt in spec.get("prompts", {}).items():
            error_handling = prompt.get("error_handling", {})
            for rule_id, status_code in [("OMCP-SEC-008", "406"), ("OMCP-SEC-009", "415"), ("OMCP-SEC-010", "429"), ("OMCP-SEC-011", "default")]:
                if status_code not in error_handling:
                    issues.append(ValidationIssue(
                        rule_id=rule_id,
                        path=f"$.prompts.{prompt_name}.error_handling",
                        message=f"Prompt missing {status_code} in 'error_handling'.",
                        severity=Severity.MEDIUM
                    ))

        # Check resources (no 415 as GET has no body)
        for res_name, res in spec.get("resources", {}).items():
            error_handling = res.get("error_handling", {})
            for rule_id, status_code in [("OMCP-SEC-008", "406"), ("OMCP-SEC-010", "429"), ("OMCP-SEC-011", "default")]:
                if status_code not in error_handling:
                    issues.append(ValidationIssue(
                        rule_id=rule_id,
                        path=f"$.resources.{res_name}.error_handling",
                        message=f"Resource missing {status_code} in 'error_handling'.",
                        severity=Severity.MEDIUM
                    ))

        # OMCP-SEC-012: OpenAPI Operation Security Check
        global_security = spec.get("security")
        if sec_schemes and global_security is None:
            for path_name, path_item in spec.get("paths", {}).items():
                if not isinstance(path_item, dict):
                    continue
                for method, operation in path_item.items():
                    if method.lower() not in ["get", "post", "put", "delete", "patch", "options", "head", "trace"]:
                        continue
                    if not isinstance(operation, dict):
                        continue
                    if operation.get("security") is None:
                        issues.append(ValidationIssue(
                            rule_id="OMCP-SEC-012",
                            path=f"$.paths['{path_name}'].{method}",
                            message="'Security' field of the operation is not defined",
                            severity=Severity.CRITICAL
                        ))

    def _validate_schemas(self, spec: Dict[str, Any], issues: List[ValidationIssue]):
        # Traverse tools, prompts, resources — only check schemas that exist
        for tool_name, tool in spec.get("tools", {}).items():
            if "input" not in tool:
                issues.append(ValidationIssue(
                    rule_id="OMCP-DAT-010",
                    path=f"$.tools.{tool_name}.input",
                    message="Tool missing 'input' schema.",
                    severity=Severity.CRITICAL
                ))
            else:
                self._check_schema_boundaries(tool["input"], f"$.tools.{tool_name}.input", issues, is_input=True)

            if "output" not in tool:
                issues.append(ValidationIssue(
                    rule_id="OMCP-DAT-011",
                    path=f"$.tools.{tool_name}.output",
                    message="Tool missing 'output' schema.",
                    severity=Severity.CRITICAL
                ))
            else:
                self._check_schema_boundaries(tool["output"], f"$.tools.{tool_name}.output", issues, is_input=False)

        for prompt_name, prompt in spec.get("prompts", {}).items():
            if "input" not in prompt:
                issues.append(ValidationIssue(
                    rule_id="OMCP-DAT-010",
                    path=f"$.prompts.{prompt_name}.input",
                    message="Prompt missing 'input' schema.",
                    severity=Severity.CRITICAL
                ))
            else:
                self._check_schema_boundaries(prompt["input"], f"$.prompts.{prompt_name}.input", issues, is_input=True)

            if "output" not in prompt:
                issues.append(ValidationIssue(
                    rule_id="OMCP-DAT-011",
                    path=f"$.prompts.{prompt_name}.output",
                    message="Prompt missing 'output' schema.",
                    severity=Severity.CRITICAL
                ))
            else:
                self._check_schema_boundaries(prompt["output"], f"$.prompts.{prompt_name}.output", issues, is_input=False)

        for res_name, res in spec.get("resources", {}).items():
            if "output" not in res:
                issues.append(ValidationIssue(
                    rule_id="OMCP-DAT-011",
                    path=f"$.resources.{res_name}.output",
                    message="Resource missing 'output' schema.",
                    severity=Severity.CRITICAL
                ))
            else:
                self._check_schema_boundaries(res["output"], f"$.resources.{res_name}.output", issues, is_input=False)

        # Also walk components.schemas directly — catches issues in $ref targets
        # that inline schema refs point to (matching 42Crunch component-level checks)
        for schema_name, schema in spec.get("components", {}).get("schemas", {}).items():
            self._check_schema_boundaries(schema, f"$.components.schemas.{schema_name}", issues, is_input=False)

    def _check_schema_boundaries(self, schema: Any, path: str, issues: List[ValidationIssue], is_input: bool):
        if not isinstance(schema, dict): return
        # Skip $ref pointers — they'll be checked when we walk components.schemas
        if "$ref" in schema: return

        # OMCP-DAT-001: Strict Objects (extended to both input AND output)
        # 42Crunch equivalent: "Schema allows additional properties"
        if schema.get("type") == "object":
            if schema.get("additionalProperties") is not False:
                # Only flag if there are no combining ops that require additionalProperties: true
                if "allOf" not in schema:
                    issues.append(ValidationIssue(
                        rule_id="OMCP-DAT-001",
                        path=path,
                        message=f"{'Input' if is_input else 'Output'} schema must set 'additionalProperties: false' to prevent data leakage.",
                        severity=Severity.CRITICAL if is_input else Severity.MEDIUM
                    ))

        # OMCP-DAT-002: Object Properties
        if schema.get("type") == "object" and not schema.get("properties"):
            issues.append(ValidationIssue(
                rule_id="OMCP-DAT-002",
                path=path,
                message="Object schema must define 'properties'. Empty object is too flexible.",
                severity=Severity.CRITICAL
            ))

        # OMCP-DAT-007: Schema Type Required
        # 42Crunch equivalent: "Schema does not limit what is accepted"
        if "type" not in schema and "$ref" not in schema and "allOf" not in schema and "anyOf" not in schema and "oneOf" not in schema:
            issues.append(ValidationIssue(
                rule_id="OMCP-DAT-007",
                path=path,
                message="Schema missing 'type'. Without a type constraint, any value is accepted.",
                severity=Severity.MEDIUM
            ))

        # OMCP-DAT-003: String Lengths
        if schema.get("type") == "string" and "maxLength" not in schema:
             issues.append(ValidationIssue(
                rule_id="OMCP-DAT-003",
                path=path,
                message="String parameter missing 'maxLength'. Buffer over-reads risk.",
                severity=Severity.HIGH
            ))

        # OMCP-DAT-003 extension: strings inside anyOf/oneOf (nullable strings)
        # e.g. anyOf: [{type: "string"}, {type: "null"}] — check maxLength at prop level
        for combining_key in ("anyOf", "oneOf"):
            sub_schemas = schema.get(combining_key)
            if isinstance(sub_schemas, list):
                has_string = any(
                    isinstance(s, dict) and s.get("type") == "string"
                    for s in sub_schemas
                )
                if has_string and "maxLength" not in schema:
                    # Check if maxLength is on any sub-schema
                    has_max_in_sub = any(
                        isinstance(s, dict) and "maxLength" in s
                        for s in sub_schemas
                    )
                    if not has_max_in_sub:
                        issues.append(ValidationIssue(
                            rule_id="OMCP-DAT-003",
                            path=path,
                            message=f"Nullable string via {combining_key} missing 'maxLength'. Buffer over-reads risk.",
                            severity=Severity.HIGH
                        ))

        # OMCP-DAT-009: String Pattern (all strings)
        # 42Crunch equivalent: "String schema has no pattern defined"
        if schema.get("type") == "string" and "pattern" not in schema:
            issues.append(ValidationIssue(
                rule_id="OMCP-DAT-009",
                path=path,
                message="String schema missing 'pattern'. Unbounded strings risk data leakage.",
                severity=Severity.MEDIUM
            ))

        # OMCP-DAT-009 extension: strings inside anyOf/oneOf (nullable strings)
        for combining_key in ("anyOf", "oneOf"):
            sub_schemas = schema.get(combining_key)
            if isinstance(sub_schemas, list):
                has_string = any(
                    isinstance(s, dict) and s.get("type") == "string"
                    for s in sub_schemas
                )
                if has_string and "pattern" not in schema:
                    has_pattern_in_sub = any(
                        isinstance(s, dict) and "pattern" in s
                        for s in sub_schemas
                    )
                    if not has_pattern_in_sub:
                        issues.append(ValidationIssue(
                            rule_id="OMCP-DAT-009",
                            path=path,
                            message=f"Nullable string via {combining_key} missing 'pattern'. Unbounded strings risk data leakage.",
                            severity=Severity.MEDIUM
                        ))

        # OMCP-DAT-004: Regex Patterns (elevated — sensitive field names)
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

        # OMCP-DAT-008: Loose anyOf/oneOf for primitives
        # 42Crunch equivalent: "Nested anyOf/oneOf missing additionalProperties"
        for combining_key in ("anyOf", "oneOf"):
            sub_schemas = schema.get(combining_key)
            if isinstance(sub_schemas, list):
                # Check if ALL sub-schemas are primitives (no properties)
                all_primitive = all(
                    isinstance(s, dict) and "properties" not in s
                    for s in sub_schemas
                )
                if all_primitive and "additionalProperties" not in schema:
                    issues.append(ValidationIssue(
                        rule_id="OMCP-DAT-008",
                        path=path,
                        message=f"Primitive {combining_key} missing 'additionalProperties: false'. Allows unconstrained data.",
                        severity=Severity.MEDIUM
                    ))

        # Recursive check for properties
        for prop_name, prop_schema in schema.get("properties", {}).items():
            self._check_schema_boundaries(prop_schema, f"{path}.properties.{prop_name}", issues, is_input)

        # Recursive check for array items
        items = schema.get("items")
        if isinstance(items, dict):
            self._check_schema_boundaries(items, f"{path}.items", issues, is_input)

    def _validate_documentation(self, spec: Dict[str, Any], issues: List[ValidationIssue]) -> None:
        """OMCP-DOC-001: capability description; OMCP-DOC-002: response description.

        Aggregates at the *section* level — one issue per (rule, section) deducts
        -10 once, regardless of how many individual capabilities are undocumented.
        Affected names are listed in the issue message for actionability.

        Works for both OpenMCP (tools/prompts/resources sections) and
        OpenAPI (paths section) formats.
        """
        FALLBACK_DESCS = {"", "successful response"}  # lower-case sentinels

        def _missing_desc(text: Optional[str]) -> bool:
            return not text or text.strip().lower() in FALLBACK_DESCS

        # ── OpenMCP format ────────────────────────────────────────────────────
        SECTION_MAP = [
            ("tools",     "Tool"),
            ("prompts",   "Prompt"),
            ("resources", "Resource"),
        ]

        for section_key, label in SECTION_MAP:
            missing_desc: list[str] = []
            missing_output: list[str] = []

            for cap_name, cap in spec.get(section_key, {}).items():
                if _missing_desc(cap.get("description")):
                    missing_desc.append(cap_name)
                if _missing_desc(cap.get("output_description")):
                    missing_output.append(cap_name)

            if missing_desc:
                names = ", ".join(f"'{n}'" for n in sorted(missing_desc))
                issues.append(ValidationIssue(
                    rule_id="OMCP-DOC-001",
                    path=f"$.{section_key}",
                    message=(
                        f"{len(missing_desc)} {label.lower()}(s) have no description: {names}. "
                        f"Add a description= param so LLMs and operators understand their purpose."
                    ),
                    severity=Severity.HIGH,
                ))

            if missing_output:
                names = ", ".join(f"'{n}'" for n in sorted(missing_output))
                issues.append(ValidationIssue(
                    rule_id="OMCP-DOC-002",
                    path=f"$.{section_key}",
                    message=(
                        f"{len(missing_output)} {label.lower()}(s) have no response description: {names}. "
                        f"Add a docstring to each output Pydantic model so callers understand the returned data."
                    ),
                    severity=Severity.HIGH,
                ))

        # ── OpenAPI format (paths) ────────────────────────────────────────────
        # Aggregate by section prefix (tools / prompts / resources / other)
        missing_summary: dict[str, list[str]] = {}   # section → [path]
        missing_resp_desc: dict[str, list[str]] = {}

        for path_name, path_item in spec.get("paths", {}).items():
            if not isinstance(path_item, dict):
                continue

            # Determine section for grouping
            if path_name.startswith("/tools/"):
                section = "tools"
            elif path_name.startswith("/prompts/"):
                section = "prompts"
            elif path_name.startswith("/resources"):
                section = "resources"
            else:
                section = "paths"

            for method, operation in path_item.items():
                if method.lower() not in ("get", "post", "put", "patch", "delete"):
                    continue
                if not isinstance(operation, dict):
                    continue

                op_label = f"{method.upper()} {path_name}"

                # OMCP-DOC-001: missing summary/description
                summary = operation.get("summary", "")
                description = operation.get("description", "")
                if _missing_desc(summary) and _missing_desc(description):
                    missing_summary.setdefault(section, []).append(op_label)

                # OMCP-DOC-002: 200 response description
                response_200 = operation.get("responses", {}).get("200", {})
                resp_desc = response_200.get("description", "") if isinstance(response_200, dict) else ""
                if _missing_desc(resp_desc):
                    missing_resp_desc.setdefault(section, []).append(op_label)

        for section, ops in missing_summary.items():
            names = ", ".join(ops)
            issues.append(ValidationIssue(
                rule_id="OMCP-DOC-001",
                path=f"$.paths ({section})",
                message=(
                    f"{len(ops)} operation(s) in '{section}' have no summary or description: {names}."
                ),
                severity=Severity.HIGH,
            ))

        for section, ops in missing_resp_desc.items():
            names = ", ".join(ops)
            issues.append(ValidationIssue(
                rule_id="OMCP-DOC-002",
                path=f"$.paths ({section})",
                message=(
                    f"{len(ops)} operation(s) in '{section}' have no 200 response description: {names}."
                ),
                severity=Severity.HIGH,
            ))

