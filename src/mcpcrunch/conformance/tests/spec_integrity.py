"""
CT-3.8 — Spec Integrity Tests (Static, No Server Required)

Validates the OpenMCP spec document itself for structural correctness.
"""

import json
from typing import Any, Dict, List, Optional, Set, Tuple

import jsonschema

from ..models import ConformanceTestResult, TestCategory, TestSeverity, TestStatus


def run_all(spec: Dict[str, Any], schema: Optional[Dict[str, Any]] = None) -> List[ConformanceTestResult]:
    """Run all spec integrity tests (CT-3.8.1 through CT-3.8.13)."""
    results = []
    # Structural integrity (original 5)
    results.append(test_3_8_1_schema_validity(spec, schema))
    results.append(test_3_8_2_component_references(spec))
    results.append(test_3_8_3_circular_references(spec))
    results.append(test_3_8_4_unused_components(spec))
    results.append(test_3_8_5_name_collisions(spec))
    # Data quality & security (new 8)
    results.append(test_3_8_6_schema_strictness(spec))
    results.append(test_3_8_7_string_boundaries(spec))
    results.append(test_3_8_8_array_boundaries(spec))
    results.append(test_3_8_9_numeric_boundaries(spec))
    results.append(test_3_8_10_security_coverage(spec))
    results.append(test_3_8_11_bearer_format(spec))
    results.append(test_3_8_12_transport_security(spec))
    results.append(test_3_8_13_description_quality(spec))
    return results


# CT-3.8.1
def test_3_8_1_schema_validity(
    spec: Dict[str, Any], schema: Optional[Dict[str, Any]] = None
) -> ConformanceTestResult:
    """CT-3.8.1: Validate the spec against the OpenMCP JSON Schema."""
    if schema is None:
        return ConformanceTestResult(
            test_id="CT-3.8.1",
            test_name="Schema Validity",
            category=TestCategory.SPEC_INTEGRITY,
            status=TestStatus.SKIPPED,
            message="No OpenMCP schema provided for meta-validation",
        )

    try:
        jsonschema.validate(instance=spec, schema=schema)
        return ConformanceTestResult(
            test_id="CT-3.8.1",
            test_name="Schema Validity",
            category=TestCategory.SPEC_INTEGRITY,
            status=TestStatus.PASSED,
            expected="Spec validates against OpenMCP JSON Schema",
            actual="Validation passed",
        )
    except jsonschema.ValidationError as e:
        return ConformanceTestResult(
            test_id="CT-3.8.1",
            test_name="Schema Validity",
            category=TestCategory.SPEC_INTEGRITY,
            status=TestStatus.FAILED,
            expected="Spec validates against OpenMCP JSON Schema",
            actual=f"Validation error at {e.json_path}: {e.message}",
        )
    except jsonschema.SchemaError as e:
        return ConformanceTestResult(
            test_id="CT-3.8.1",
            test_name="Schema Validity",
            category=TestCategory.SPEC_INTEGRITY,
            status=TestStatus.ERROR,
            message=f"Invalid meta-schema: {e.message}",
        )


# CT-3.8.2
def test_3_8_2_component_references(spec: Dict[str, Any]) -> ConformanceTestResult:
    """CT-3.8.2: Ensure all $ref pointers resolve to valid targets."""
    refs = _collect_refs(spec)
    dangling = []

    for ref_path, ref_value in refs:
        if ref_value.startswith("#/"):
            # Internal reference
            target = _resolve_json_pointer(spec, ref_value[2:])
            if target is None:
                dangling.append(f"{ref_path} → {ref_value}")

    if dangling:
        return ConformanceTestResult(
            test_id="CT-3.8.2",
            test_name="Component References",
            category=TestCategory.SPEC_INTEGRITY,
            status=TestStatus.FAILED,
            expected="All $ref pointers resolve",
            actual=f"Dangling references: {'; '.join(dangling[:5])}",
        )
    else:
        total = len(refs)
        return ConformanceTestResult(
            test_id="CT-3.8.2",
            test_name="Component References",
            category=TestCategory.SPEC_INTEGRITY,
            status=TestStatus.PASSED,
            expected="All $ref pointers resolve",
            actual=f"All {total} references resolved successfully",
        )


# CT-3.8.3
def test_3_8_3_circular_references(spec: Dict[str, Any]) -> ConformanceTestResult:
    """CT-3.8.3: Detect circular $ref chains."""
    refs = _collect_refs(spec)
    # Build adjacency: source_path → target_path
    graph: Dict[str, List[str]] = {}
    for ref_path, ref_value in refs:
        if ref_value.startswith("#/"):
            target = ref_value[2:].replace("/", ".")
            source = ref_path.rsplit(".$ref", 1)[0] if ".$ref" in ref_path else ref_path
            graph.setdefault(source, []).append(target)

    # DFS cycle detection
    visited: Set[str] = set()
    rec_stack: Set[str] = set()
    cycles: List[str] = []

    def _dfs(node: str, path: List[str]):
        visited.add(node)
        rec_stack.add(node)
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                _dfs(neighbor, path + [neighbor])
            elif neighbor in rec_stack:
                cycle = path[path.index(neighbor):] + [neighbor] if neighbor in path else [node, neighbor]
                cycles.append(" → ".join(cycle))
        rec_stack.discard(node)

    for node in graph:
        if node not in visited:
            _dfs(node, [node])

    if cycles:
        return ConformanceTestResult(
            test_id="CT-3.8.3",
            test_name="Circular Reference Detection",
            category=TestCategory.SPEC_INTEGRITY,
            status=TestStatus.FAILED,
            expected="No circular references",
            actual=f"Cycles detected: {'; '.join(cycles[:3])}",
        )
    else:
        return ConformanceTestResult(
            test_id="CT-3.8.3",
            test_name="Circular Reference Detection",
            category=TestCategory.SPEC_INTEGRITY,
            status=TestStatus.PASSED,
            expected="No circular references",
            actual="Reference graph is acyclic",
        )


# CT-3.8.4
def test_3_8_4_unused_components(spec: Dict[str, Any]) -> ConformanceTestResult:
    """CT-3.8.4: Flag components that are defined but never referenced."""
    components = spec.get("components", {})
    defined: Set[str] = set()

    for comp_type in ("schemas", "securitySchemes", "tools", "prompts", "resources", "examples"):
        for name in components.get(comp_type, {}):
            defined.add(f"components/{comp_type}/{name}")

    if not defined:
        return ConformanceTestResult(
            test_id="CT-3.8.4",
            test_name="Unused Components",
            category=TestCategory.SPEC_INTEGRITY,
            status=TestStatus.PASSED,
            expected="All components referenced",
            actual="No components defined",
        )

    # Collect all $ref targets
    refs = _collect_refs(spec)
    referenced: Set[str] = set()
    for _, ref_value in refs:
        if ref_value.startswith("#/"):
            referenced.add(ref_value[2:])

    # Also check security requirements referencing securitySchemes
    for entity_type in ("tools", "prompts"):
        for entity_name, entity in spec.get(entity_type, {}).items():
            for sec_req in entity.get("security", []):
                for scheme_name in sec_req:
                    referenced.add(f"components/securitySchemes/{scheme_name}")

    # Check global security
    for sec_req in spec.get("security", []):
        for scheme_name in sec_req:
            referenced.add(f"components/securitySchemes/{scheme_name}")

    unused = defined - referenced
    if unused:
        return ConformanceTestResult(
            test_id="CT-3.8.4",
            test_name="Unused Components",
            category=TestCategory.SPEC_INTEGRITY,
            status=TestStatus.PASSED,  # Warning, not fail
            expected="All components referenced",
            actual=f"Unused components (warning): {', '.join(sorted(unused)[:5])}",
            message="Unused components found — not a failure but may indicate dead code in spec",
        )
    else:
        return ConformanceTestResult(
            test_id="CT-3.8.4",
            test_name="Unused Components",
            category=TestCategory.SPEC_INTEGRITY,
            status=TestStatus.PASSED,
            expected="All components referenced",
            actual=f"All {len(defined)} components are referenced",
        )


# CT-3.8.5
def test_3_8_5_name_collisions(spec: Dict[str, Any]) -> ConformanceTestResult:
    """CT-3.8.5: Check for duplicate names within and across namespaces."""
    tools = set(spec.get("tools", {}).keys())
    prompts = set(spec.get("prompts", {}).keys())
    resources = set(spec.get("resources", {}).keys())

    issues = []

    # Within-namespace duplicates (JSON keys are unique by definition, but check anyway)
    # Cross-namespace collisions
    tool_prompt = tools & prompts
    tool_resource = tools & resources
    prompt_resource = prompts & resources

    if tool_prompt:
        issues.append(f"tool/prompt collision: {', '.join(tool_prompt)}")
    if tool_resource:
        issues.append(f"tool/resource collision: {', '.join(tool_resource)}")
    if prompt_resource:
        issues.append(f"prompt/resource collision: {', '.join(prompt_resource)}")

    if issues:
        return ConformanceTestResult(
            test_id="CT-3.8.5",
            test_name="Name Collisions",
            category=TestCategory.SPEC_INTEGRITY,
            status=TestStatus.FAILED,
            expected="Unique names across namespaces",
            actual=f"Collisions: {'; '.join(issues)}",
        )
    else:
        total = len(tools) + len(prompts) + len(resources)
        return ConformanceTestResult(
            test_id="CT-3.8.5",
            test_name="Name Collisions",
            category=TestCategory.SPEC_INTEGRITY,
            status=TestStatus.PASSED,
            expected="Unique names across namespaces",
            actual=f"All {total} entity names are unique",
        )


# ── Helpers ──────────────────────────────────────────────────

def _collect_refs(obj: Any, path: str = "$") -> List[Tuple[str, str]]:
    """Recursively collect all ($ref_path, $ref_value) pairs."""
    refs = []
    if isinstance(obj, dict):
        if "$ref" in obj:
            refs.append((f"{path}.$ref", obj["$ref"]))
        for key, value in obj.items():
            if key != "$ref":
                refs.extend(_collect_refs(value, f"{path}.{key}"))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            refs.extend(_collect_refs(item, f"{path}[{i}]"))
    return refs


def _resolve_json_pointer(doc: Dict[str, Any], pointer: str) -> Any:
    """Resolve a JSON Pointer (without leading #/) against a document."""
    parts = pointer.split("/")
    current = doc
    for part in parts:
        part = part.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict):
            if part not in current:
                return None
            current = current[part]
        elif isinstance(current, list):
            try:
                idx = int(part)
                current = current[idx]
            except (ValueError, IndexError):
                return None
        else:
            return None
    return current


# ── Schema Walkers ───────────────────────────────────────────

def _resolve_schema(schema: Dict[str, Any], spec: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve a $ref to the actual schema, or return as-is."""
    if "$ref" in schema:
        ref = schema["$ref"]
        if ref.startswith("#/"):
            resolved = _resolve_json_pointer(spec, ref[2:])
            if isinstance(resolved, dict):
                return resolved
    return schema


def _walk_properties(schema: Dict[str, Any], spec: Dict[str, Any], path: str = "") -> List[tuple]:
    """Walk all properties in a schema, resolving $refs.

    Yields (property_path, property_schema) for every leaf property.
    """
    schema = _resolve_schema(schema, spec)
    results = []

    if schema.get("type") == "object" and "properties" in schema:
        for prop_name, prop_schema in schema["properties"].items():
            full_path = f"{path}.{prop_name}" if path else prop_name
            prop_schema = _resolve_schema(prop_schema, spec)
            results.append((full_path, prop_schema))
            # Recurse into nested objects
            if prop_schema.get("type") == "object" and "properties" in prop_schema:
                results.extend(_walk_properties(prop_schema, spec, full_path))
            # Walk array item schemas
            if prop_schema.get("type") == "array" and "items" in prop_schema:
                item_schema = _resolve_schema(prop_schema["items"], spec)
                if item_schema.get("type") == "object" and "properties" in item_schema:
                    results.extend(_walk_properties(item_schema, spec, f"{full_path}[]"))

    return results


# ── CT-3.8.6: Schema Strictness (OMCP-DAT-001) ────────────

def test_3_8_6_schema_strictness(spec: Dict[str, Any]) -> ConformanceTestResult:
    """CT-3.8.6: All input schemas must set additionalProperties: false."""
    violations = []

    for entity_type in ("tools", "prompts"):
        for name, entity in spec.get(entity_type, {}).items():
            input_schema = entity.get("input", {})
            input_schema = _resolve_schema(input_schema, spec)
            if input_schema.get("type") == "object":
                if input_schema.get("additionalProperties") is not False:
                    violations.append(f"{entity_type}.{name}")

    if violations:
        return ConformanceTestResult(
            test_id="CT-3.8.6",
            test_name="Schema Strictness",
            category=TestCategory.SPEC_INTEGRITY,
            severity=TestSeverity.CRITICAL,
            status=TestStatus.FAILED,
            expected="All input schemas have additionalProperties: false",
            actual=f"{len(violations)} input(s) missing additionalProperties: false: {', '.join(violations[:5])}",
        )
    else:
        total = sum(len(spec.get(t, {})) for t in ("tools", "prompts"))
        return ConformanceTestResult(
            test_id="CT-3.8.6",
            test_name="Schema Strictness",
            category=TestCategory.SPEC_INTEGRITY,
            severity=TestSeverity.CRITICAL,
            status=TestStatus.PASSED,
            expected="All input schemas have additionalProperties: false",
            actual=f"All {total} input schemas are strict",
        )


# ── CT-3.8.7: String Boundaries (OMCP-DAT-003) ───────────

def test_3_8_7_string_boundaries(spec: Dict[str, Any]) -> ConformanceTestResult:
    """CT-3.8.7: All string properties must define maxLength."""
    violations = []

    for entity_type in ("tools", "prompts", "resources"):
        for name, entity in spec.get(entity_type, {}).items():
            for schema_key in ("input", "output"):
                schema = entity.get(schema_key, {})
                if not schema:
                    continue
                for prop_path, prop_schema in _walk_properties(schema, spec):
                    if prop_schema.get("type") == "string" and "maxLength" not in prop_schema:
                        # Skip enums — they're already bounded
                        if "enum" not in prop_schema:
                            violations.append(f"{entity_type}.{name}.{schema_key}.{prop_path}")

    if violations:
        return ConformanceTestResult(
            test_id="CT-3.8.7",
            test_name="String Boundaries",
            category=TestCategory.SPEC_INTEGRITY,
            severity=TestSeverity.HIGH,
            status=TestStatus.FAILED,
            expected="All string properties have maxLength",
            actual=f"{len(violations)} string(s) missing maxLength: {', '.join(violations[:5])}",
        )
    else:
        return ConformanceTestResult(
            test_id="CT-3.8.7",
            test_name="String Boundaries",
            category=TestCategory.SPEC_INTEGRITY,
            severity=TestSeverity.HIGH,
            status=TestStatus.PASSED,
            expected="All string properties have maxLength",
            actual="All string properties define maxLength",
        )


# ── CT-3.8.8: Array Boundaries (OMCP-DAT-005) ────────────

def test_3_8_8_array_boundaries(spec: Dict[str, Any]) -> ConformanceTestResult:
    """CT-3.8.8: All array properties must define maxItems."""
    violations = []

    for entity_type in ("tools", "prompts", "resources"):
        for name, entity in spec.get(entity_type, {}).items():
            for schema_key in ("input", "output"):
                schema = entity.get(schema_key, {})
                if not schema:
                    continue
                for prop_path, prop_schema in _walk_properties(schema, spec):
                    if prop_schema.get("type") == "array" and "maxItems" not in prop_schema:
                        violations.append(f"{entity_type}.{name}.{schema_key}.{prop_path}")

    if violations:
        return ConformanceTestResult(
            test_id="CT-3.8.8",
            test_name="Array Boundaries",
            category=TestCategory.SPEC_INTEGRITY,
            severity=TestSeverity.HIGH,
            status=TestStatus.FAILED,
            expected="All array properties have maxItems",
            actual=f"{len(violations)} array(s) missing maxItems: {', '.join(violations[:5])}",
        )
    else:
        return ConformanceTestResult(
            test_id="CT-3.8.8",
            test_name="Array Boundaries",
            category=TestCategory.SPEC_INTEGRITY,
            severity=TestSeverity.HIGH,
            status=TestStatus.PASSED,
            expected="All array properties have maxItems",
            actual="All array properties define maxItems",
        )


# ── CT-3.8.9: Numeric Boundaries (OMCP-DAT-006) ─────────

def test_3_8_9_numeric_boundaries(spec: Dict[str, Any]) -> ConformanceTestResult:
    """CT-3.8.9: All number/integer properties must define minimum and maximum."""
    violations = []

    for entity_type in ("tools", "prompts", "resources"):
        for name, entity in spec.get(entity_type, {}).items():
            for schema_key in ("input", "output"):
                schema = entity.get(schema_key, {})
                if not schema:
                    continue
                for prop_path, prop_schema in _walk_properties(schema, spec):
                    if prop_schema.get("type") in ("number", "integer"):
                        missing = []
                        if "minimum" not in prop_schema:
                            missing.append("minimum")
                        if "maximum" not in prop_schema:
                            missing.append("maximum")
                        if missing:
                            violations.append(f"{entity_type}.{name}.{schema_key}.{prop_path} (missing {', '.join(missing)})")

    if violations:
        return ConformanceTestResult(
            test_id="CT-3.8.9",
            test_name="Numeric Boundaries",
            category=TestCategory.SPEC_INTEGRITY,
            severity=TestSeverity.MEDIUM,
            status=TestStatus.FAILED,
            expected="All numeric properties have minimum and maximum",
            actual=f"{len(violations)} numeric prop(s) missing bounds: {', '.join(violations[:5])}",
        )
    else:
        return ConformanceTestResult(
            test_id="CT-3.8.9",
            test_name="Numeric Boundaries",
            category=TestCategory.SPEC_INTEGRITY,
            severity=TestSeverity.MEDIUM,
            status=TestStatus.PASSED,
            expected="All numeric properties have minimum and maximum",
            actual="All numeric properties define bounds",
        )


# ── CT-3.8.10: Security Coverage (OMCP-SEC-003) ──────────

def test_3_8_10_security_coverage(spec: Dict[str, Any]) -> ConformanceTestResult:
    """CT-3.8.10: All tools must have non-empty security bindings."""
    unsecured = []

    for tool_name, tool in spec.get("tools", {}).items():
        sec = tool.get("security")
        if sec is None or (isinstance(sec, list) and len(sec) == 0):
            # Check for global security fallback
            if not spec.get("security"):
                unsecured.append(tool_name)

    tools_count = len(spec.get("tools", {}))
    if not tools_count:
        return ConformanceTestResult(
            test_id="CT-3.8.10",
            test_name="Security Coverage",
            category=TestCategory.SPEC_INTEGRITY,
            severity=TestSeverity.HIGH,
            status=TestStatus.PASSED,
            expected="All tools have security bindings",
            actual="No tools defined",
        )

    if unsecured:
        return ConformanceTestResult(
            test_id="CT-3.8.10",
            test_name="Security Coverage",
            category=TestCategory.SPEC_INTEGRITY,
            severity=TestSeverity.HIGH,
            status=TestStatus.FAILED,
            expected="All tools have security bindings",
            actual=f"{len(unsecured)} tool(s) with no security: {', '.join(unsecured[:5])}",
        )
    else:
        return ConformanceTestResult(
            test_id="CT-3.8.10",
            test_name="Security Coverage",
            category=TestCategory.SPEC_INTEGRITY,
            severity=TestSeverity.HIGH,
            status=TestStatus.PASSED,
            expected="All tools have security bindings",
            actual=f"All {tools_count} tools have security bindings",
        )


# ── CT-3.8.11: Bearer Format (OMCP-SEC-004) ──────────────

def test_3_8_11_bearer_format(spec: Dict[str, Any]) -> ConformanceTestResult:
    """CT-3.8.11: Bearer auth schemes should specify bearerFormat."""
    sec_schemes = spec.get("components", {}).get("securitySchemes", {})
    missing = []

    for name, scheme in sec_schemes.items():
        if scheme.get("type") == "http" and scheme.get("scheme", "").lower() == "bearer":
            if not scheme.get("bearerFormat"):
                missing.append(name)

    if not sec_schemes:
        return ConformanceTestResult(
            test_id="CT-3.8.11",
            test_name="Bearer Format",
            category=TestCategory.SPEC_INTEGRITY,
            severity=TestSeverity.MEDIUM,
            status=TestStatus.PASSED,
            expected="Bearer schemes specify bearerFormat",
            actual="No security schemes defined",
        )

    if missing:
        return ConformanceTestResult(
            test_id="CT-3.8.11",
            test_name="Bearer Format",
            category=TestCategory.SPEC_INTEGRITY,
            severity=TestSeverity.MEDIUM,
            status=TestStatus.FAILED,
            expected="Bearer schemes specify bearerFormat",
            actual=f"Missing bearerFormat on: {', '.join(missing)}",
        )
    else:
        return ConformanceTestResult(
            test_id="CT-3.8.11",
            test_name="Bearer Format",
            category=TestCategory.SPEC_INTEGRITY,
            severity=TestSeverity.MEDIUM,
            status=TestStatus.PASSED,
            expected="Bearer schemes specify bearerFormat",
            actual="All bearer schemes specify bearerFormat",
        )


# ── CT-3.8.12: Transport Security (OMCP-SEC-005) ─────────

def test_3_8_12_transport_security(spec: Dict[str, Any]) -> ConformanceTestResult:
    """CT-3.8.12: All server URLs must use https:// or wss://."""
    servers = spec.get("servers", [])
    insecure = []

    for i, server in enumerate(servers):
        url = server.get("url", "")
        if url.startswith("http://") or url.startswith("ws://"):
            insecure.append(url)

    if not servers:
        return ConformanceTestResult(
            test_id="CT-3.8.12",
            test_name="Transport Security",
            category=TestCategory.SPEC_INTEGRITY,
            severity=TestSeverity.HIGH,
            status=TestStatus.PASSED,
            expected="All servers use https/wss",
            actual="No servers defined",
        )

    if insecure:
        return ConformanceTestResult(
            test_id="CT-3.8.12",
            test_name="Transport Security",
            category=TestCategory.SPEC_INTEGRITY,
            severity=TestSeverity.HIGH,
            status=TestStatus.FAILED,
            expected="All servers use https/wss",
            actual=f"{len(insecure)} insecure server(s): {', '.join(insecure[:3])}",
        )
    else:
        return ConformanceTestResult(
            test_id="CT-3.8.12",
            test_name="Transport Security",
            category=TestCategory.SPEC_INTEGRITY,
            severity=TestSeverity.HIGH,
            status=TestStatus.PASSED,
            expected="All servers use https/wss",
            actual=f"All {len(servers)} server(s) use secure transport",
        )


# ── CT-3.8.13: Description Quality (OMCP-FMT-002+) ──────

def test_3_8_13_description_quality(spec: Dict[str, Any]) -> ConformanceTestResult:
    """CT-3.8.13: All tools, prompts, and resources must have a non-empty description."""
    missing = []

    for entity_type in ("tools", "prompts", "resources"):
        for name, entity in spec.get(entity_type, {}).items():
            desc = entity.get("description", "")
            if not desc or not desc.strip():
                missing.append(f"{entity_type}.{name}")

    total = sum(len(spec.get(t, {})) for t in ("tools", "prompts", "resources"))
    if total == 0:
        return ConformanceTestResult(
            test_id="CT-3.8.13",
            test_name="Description Quality",
            category=TestCategory.SPEC_INTEGRITY,
            severity=TestSeverity.MEDIUM,
            status=TestStatus.PASSED,
            expected="All entities have descriptions",
            actual="No entities defined",
        )

    if missing:
        return ConformanceTestResult(
            test_id="CT-3.8.13",
            test_name="Description Quality",
            category=TestCategory.SPEC_INTEGRITY,
            severity=TestSeverity.MEDIUM,
            status=TestStatus.FAILED,
            expected="All entities have descriptions",
            actual=f"{len(missing)} entity/ies missing description: {', '.join(missing[:5])}",
        )
    else:
        return ConformanceTestResult(
            test_id="CT-3.8.13",
            test_name="Description Quality",
            category=TestCategory.SPEC_INTEGRITY,
            severity=TestSeverity.MEDIUM,
            status=TestStatus.PASSED,
            expected="All entities have descriptions",
            actual=f"All {total} entities have descriptions",
        )
