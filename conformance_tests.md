# OpenMCP Conformance Test Suite — Test Catalog

> **MCPcrunch Conformance Engine**
> Deterministic validation: Does runtime behavior match the declared OpenMCP spec?

This document defines every conformance test in the MCPcrunch Conformance Test Suite.
Each test has a unique **Test ID** (format: `CT-X.Y.Z`) that MUST appear as a comment
in the corresponding implementation code.

---

## Test ID Format

```
CT-{section}.{subsection}.{test}
```

Example: `CT-3.1.1` → Section 3 (Test Categories), Subsection 1 (Schema Conformance), Test 1 (Valid Input)

---

## Summary

| Category | ID Range | Count | Type |
|:---|:---|:---:|:---:|
| Schema Input Conformance | CT-3.1.1 – CT-3.1.7 | 7 | Runtime |
| Output Conformance | CT-3.2.1 – CT-3.2.5 | 5 | Runtime |
| Tool Invocation Contract | CT-3.3.1 – CT-3.3.4 | 4 | Runtime |
| Prompt Conformance | CT-3.4.1 – CT-3.4.3 | 3 | Runtime |
| Resource Conformance | CT-3.5.1 – CT-3.5.3 | 3 | Runtime |
| Security Conformance | CT-3.6.1 – CT-3.6.4 | 4 | Runtime |
| Server Contract | CT-3.7.1 – CT-3.7.3 | 3 | Runtime |
| Spec Integrity (Static) | CT-3.8.1 – CT-3.8.5 | 5 | Static |
| Error Handling Conformance | CT-3.9.1 – CT-3.9.3 | 3 | Runtime |
| Determinism | CT-3.10.1 – CT-3.10.3 | 3 | Runtime |
| **Total** | | **40** | |

---

## 3.1 Schema Input Conformance Tests

**Goal:** Ensure tool/prompt input strictly follows the declared JSON Schema.

**Applies to:** All entities with an `input` schema (tools, prompts).

---

### CT-3.1.1 — Valid Input (Happy Path)

| Field | Value |
|:---|:---|
| **ID** | `CT-3.1.1` |
| **Name** | Valid Input Happy Path |
| **Category** | Schema Input Conformance |
| **Type** | Runtime |
| **Severity** | Critical |

**Description:**
Send an input that exactly matches the declared input schema. This is the baseline sanity test.

**Procedure:**
1. Parse the `input` schema for the target entity
2. Generate a valid input instance from the schema
3. Send the input via JSON-RPC (`tools/call` or `prompts/get`)
4. Capture the response

**Expected:**
- Server returns a success response (no JSON-RPC error)
- Response output conforms to the declared `output` schema

**Pass Criteria:**
- ✅ No error in response
- ✅ Output validates against output schema

**Fail Criteria:**
- ❌ Server returns an error for valid input
- ❌ Output does not match output schema

---

### CT-3.1.2 — Missing Required Fields

| Field | Value |
|:---|:---|
| **ID** | `CT-3.1.2` |
| **Name** | Missing Required Fields |
| **Category** | Schema Input Conformance |
| **Type** | Runtime |
| **Severity** | Critical |

**Description:**
For each required field in the input schema, remove it (one at a time) and send the request.
The server MUST reject the input with a deterministic error.

**Procedure:**
1. Parse the `input` schema and identify all `required` fields
2. For each required field:
   a. Generate a valid input
   b. Remove the required field
   c. Send the mutated input
   d. Record the response

**Expected:**
- Server returns a JSON-RPC error response for each missing field
- No successful execution occurs

**Pass Criteria (per field):**
- ✅ Server returns an error (JSON-RPC error object present)
- ✅ Error indicates validation failure

**Fail Criteria:**
- ❌ Server returns a success response with missing required field
- ❌ Server silently ignores the missing field

---

### CT-3.1.3 — Additional Properties Injection

| Field | Value |
|:---|:---|
| **ID** | `CT-3.1.3` |
| **Name** | Additional Properties Injection |
| **Category** | Schema Input Conformance |
| **Type** | Runtime |
| **Severity** | High |

**Description:**
Inject properties not defined in the input schema. The server must either reject them
(if `additionalProperties: false`) or ignore them consistently.

**Procedure:**
1. Parse the `input` schema
2. Generate a valid input
3. Add one or more undeclared fields (e.g., `{"__injected": "malicious"}`)
4. Send the mutated input

**Expected:**
- If schema has `additionalProperties: false` → Server MUST reject
- If schema allows additionalProperties → Server MUST NOT use injected fields in output

**Pass Criteria:**
- ✅ Rejection when additionalProperties is false
- ✅ Injected fields have no side effects when allowed

**Fail Criteria:**
- ❌ Server accepts input when additionalProperties is false
- ❌ Injected fields appear in output or cause behavior change

---

### CT-3.1.4 — Type Violations

| Field | Value |
|:---|:---|
| **ID** | `CT-3.1.4` |
| **Name** | Type Violations |
| **Category** | Schema Input Conformance |
| **Type** | Runtime |
| **Severity** | Critical |

**Description:**
Send inputs with incorrect types for each property. The server MUST reject them.

**Mutations Applied:**
- `string` → `number` (e.g., `"hello"` → `42`)
- `number` → `string` (e.g., `42` → `"forty-two"`)
- `object` → `array` (e.g., `{}` → `[]`)
- `boolean` → `string` (e.g., `true` → `"true"`)
- `array` → `object` (e.g., `[]` → `{}`)
- `integer` → `float` (e.g., `5` → `5.5`)

**Procedure:**
1. For each property in the input schema:
   a. Determine the declared type
   b. Generate a value of an incompatible type
   c. Send the mutated input
   d. Record the response

**Expected:**
- Server returns a validation error for each type violation

**Pass Criteria:**
- ✅ Error returned for every type mismatch

**Fail Criteria:**
- ❌ Server accepts incorrectly typed input
- ❌ Server silently coerces types

---

### CT-3.1.5 — Constraint Violations

| Field | Value |
|:---|:---|
| **ID** | `CT-3.1.5` |
| **Name** | Constraint Violations |
| **Category** | Schema Input Conformance |
| **Type** | Runtime |
| **Severity** | High |

**Description:**
Violate JSON Schema constraints defined on input properties.

**Constraints Tested:**
- `minLength`: send a string shorter than minimum
- `maxLength`: send a string longer than maximum
- `minimum`: send a number below minimum
- `maximum`: send a number above maximum
- `enum`: send a value not in the enum list
- `pattern`: send a string that doesn't match the regex
- `minItems`: send an array with fewer items
- `maxItems`: send an array with more items

**Procedure:**
1. For each property with constraints:
   a. Generate a value that violates each constraint individually
   b. Send the mutated input
   c. Record the response

**Expected:**
- Server returns a validation error for each constraint violation

**Pass Criteria:**
- ✅ Error returned for every constraint violation

**Fail Criteria:**
- ❌ Server accepts values violating constraints
- ❌ Server truncates/clamps values silently

---

### CT-3.1.6 — Nullability Violations

| Field | Value |
|:---|:---|
| **ID** | `CT-3.1.6` |
| **Name** | Nullability Violations |
| **Category** | Schema Input Conformance |
| **Type** | Runtime |
| **Severity** | High |

**Description:**
Send `null` for properties that do not allow null values.

**Procedure:**
1. For each property in the input schema:
   a. Check if `null` is allowed (via `nullable: true` or `type: ["string", "null"]`)
   b. If null is NOT allowed, send `null` for that property
   c. Record the response

**Expected:**
- Server returns a validation error when null is not permitted

**Pass Criteria:**
- ✅ Server rejects null for non-nullable fields

**Fail Criteria:**
- ❌ Server accepts null for non-nullable fields
- ❌ Server crashes or returns 500

---

### CT-3.1.7 — Deep Object Violations

| Field | Value |
|:---|:---|
| **ID** | `CT-3.1.7` |
| **Name** | Deep Object Violations |
| **Category** | Schema Input Conformance |
| **Type** | Runtime |
| **Severity** | High |

**Description:**
For schemas with nested objects, violate the schema at a nested level rather than the top level.
Validates that the server performs deep validation, not just top-level checks.

**Procedure:**
1. Identify properties that are objects with their own `properties` and `required` fields
2. Generate valid top-level input but break a nested field (wrong type, missing required, etc.)
3. Send the mutated input

**Expected:**
- Server returns a validation error referencing the nested path

**Pass Criteria:**
- ✅ Error returned for nested schema violations
- ✅ Error references the correct nested path

**Fail Criteria:**
- ❌ Server accepts invalid nested data
- ❌ Server only validates top-level properties

---

## 3.2 Output Conformance Tests

**Goal:** Ensure runtime output matches the declared output schema.

**Applies to:** All entities with an `output` schema (tools, prompts, resources).

---

### CT-3.2.1 — Output Schema Validation

| Field | Value |
|:---|:---|
| **ID** | `CT-3.2.1` |
| **Name** | Output Schema Validation |
| **Category** | Output Conformance |
| **Type** | Runtime |
| **Severity** | Critical |

**Description:**
Send a valid input and validate the entire response against the declared output schema.

**Procedure:**
1. Send a valid input (reuse CT-3.1.1 happy path)
2. Parse the response body
3. Validate response against the declared `output` schema using JSON Schema validation

**Expected:**
- Full response validates against the output schema

**Pass Criteria:**
- ✅ Response is valid per output schema (all required fields present, types match, constraints met)

**Fail Criteria:**
- ❌ Any validation error against the output schema

---

### CT-3.2.2 — Missing Output Fields

| Field | Value |
|:---|:---|
| **ID** | `CT-3.2.2` |
| **Name** | Missing Output Fields |
| **Category** | Output Conformance |
| **Type** | Runtime |
| **Severity** | Critical |

**Description:**
Check if the server omits any fields marked as `required` in the output schema.

**Procedure:**
1. Send a valid input
2. Parse the response
3. Check each `required` field in the output schema
4. Flag any missing required fields

**Expected:**
- All required output fields are present

**Pass Criteria:**
- ✅ Every required output field exists in the response

**Fail Criteria:**
- ❌ Any required output field is missing

---

### CT-3.2.3 — Extra Fields in Output

| Field | Value |
|:---|:---|
| **ID** | `CT-3.2.3` |
| **Name** | Extra Fields in Output |
| **Category** | Output Conformance |
| **Type** | Runtime |
| **Severity** | Medium |

**Description:**
Check if the server returns fields not declared in the output schema,
when `additionalProperties` is not allowed.

**Procedure:**
1. Send a valid input
2. Parse the response
3. Compare response keys against declared output schema properties
4. Flag any undeclared keys

**Expected:**
- If `additionalProperties: false` → no extra fields allowed
- If `additionalProperties` not set → informational warning

**Pass Criteria:**
- ✅ No extra fields when additionalProperties is false
- ✅ Warning (not fail) when additionalProperties is unset

**Fail Criteria:**
- ❌ Extra fields present when additionalProperties is false

---

### CT-3.2.4 — Type Mismatch in Output

| Field | Value |
|:---|:---|
| **ID** | `CT-3.2.4` |
| **Name** | Type Mismatch in Output |
| **Category** | Output Conformance |
| **Type** | Runtime |
| **Severity** | Critical |

**Description:**
Validate that every field in the output has the correct type as declared in the schema.

**Procedure:**
1. Send a valid input
2. Parse the response
3. For each declared output field, validate the runtime type matches the schema type

**Expected:**
- All output field types match their schema declarations

**Pass Criteria:**
- ✅ All output field types are correct

**Fail Criteria:**
- ❌ Any type mismatch (e.g., schema says `string`, runtime returns `number`)

---

### CT-3.2.5 — Deterministic Output Structure

| Field | Value |
|:---|:---|
| **ID** | `CT-3.2.5` |
| **Name** | Deterministic Output Structure |
| **Category** | Output Conformance |
| **Type** | Runtime |
| **Severity** | High |

**Description:**
Same input must produce structurally consistent output across multiple invocations.
Not the same *values*, but the same *shape* (keys, types, nesting).

**Procedure:**
1. Send the same valid input N times (default: 3)
2. For each response, extract the structural "shape" (keys + types, recursively)
3. Compare all shapes

**Expected:**
- All invocations produce the same structural shape

**Pass Criteria:**
- ✅ Output shape is identical across all invocations

**Fail Criteria:**
- ❌ Output shape varies between invocations

---

## 3.3 Tool Invocation Contract Tests

**Goal:** Ensure tools behave like strict RPC endpoints with deterministic contracts.

---

### CT-3.3.1 — Unknown Tool Invocation

| Field | Value |
|:---|:---|
| **ID** | `CT-3.3.1` |
| **Name** | Unknown Tool Invocation |
| **Category** | Tool Invocation Contract |
| **Type** | Runtime |
| **Severity** | Critical |

**Description:**
Attempt to invoke a tool that is NOT declared in the spec.

**Procedure:**
1. Generate a random tool name not in the spec (e.g., `__nonexistent_tool_xyz`)
2. Send a `tools/call` request with this name
3. Record the response

**Expected:**
- Server returns a deterministic error indicating the tool doesn't exist

**Pass Criteria:**
- ✅ Error response returned (not a success)
- ✅ Error clearly indicates tool not found

**Fail Criteria:**
- ❌ Server returns a success response
- ❌ Server crashes or hangs

---

### CT-3.3.2 — Missing Input Object

| Field | Value |
|:---|:---|
| **ID** | `CT-3.3.2` |
| **Name** | Missing Input Object |
| **Category** | Tool Invocation Contract |
| **Type** | Runtime |
| **Severity** | Critical |

**Description:**
Call a tool with no input (empty or missing `arguments` field).

**Procedure:**
1. For each tool with required input fields:
   a. Send a `tools/call` request with empty or no `arguments`
   b. Record the response

**Expected:**
- Server returns a validation error

**Pass Criteria:**
- ✅ Error response indicating missing required input

**Fail Criteria:**
- ❌ Server executes the tool without required input
- ❌ Server returns a successful response

---

### CT-3.3.3 — Partial Input

| Field | Value |
|:---|:---|
| **ID** | `CT-3.3.3` |
| **Name** | Partial Input |
| **Category** | Tool Invocation Contract |
| **Type** | Runtime |
| **Severity** | High |

**Description:**
Send only a subset of the required fields (but not all).

**Procedure:**
1. For each tool with N required fields (N > 1):
   a. Send only the first required field, omitting the rest
   b. Record the response

**Expected:**
- Server returns a validation error for missing fields

**Pass Criteria:**
- ✅ Error response indicating missing required fields

**Fail Criteria:**
- ❌ Server executes with partial input
- ❌ Server ignores missing fields

---

### CT-3.3.4 — Input/Output Mapping Integrity

| Field | Value |
|:---|:---|
| **ID** | `CT-3.3.4` |
| **Name** | Input/Output Mapping Integrity |
| **Category** | Tool Invocation Contract |
| **Type** | Runtime |
| **Severity** | High |

**Description:**
Ensure the output corresponds to the input contract — no silent coercion,
no undeclared transformations.

**Procedure:**
1. Send a valid input
2. Verify:
   a. Output conforms to declared output schema
   b. No input values appear coerced in the output (e.g., string `"42"` becoming number `42`)
   c. Output structure matches declaration, not an arbitrary different structure

**Expected:**
- Output strictly matches the declared output contract

**Pass Criteria:**
- ✅ Output validates against output schema
- ✅ No silent coercion detected

**Fail Criteria:**
- ❌ Output contains coerced values
- ❌ Output structure doesn't match declaration

---

## 3.4 Prompt Conformance Tests

**Goal:** Ensure prompts behave like structured templates with strict contracts.

---

### CT-3.4.1 — Prompt Input Validation

| Field | Value |
|:---|:---|
| **ID** | `CT-3.4.1` |
| **Name** | Prompt Input Validation |
| **Category** | Prompt Conformance |
| **Type** | Runtime |
| **Severity** | Critical |

**Description:**
Apply the same input validation tests as tools (CT-3.1.x series) to prompt inputs.

**Procedure:**
1. For each prompt with an input schema:
   a. Run CT-3.1.1 (valid input)
   b. Run CT-3.1.2 (missing required fields)
   c. Run CT-3.1.4 (type violations)
   d. Send via `prompts/get` instead of `tools/call`

**Expected:**
- Same validation behavior as tools — reject invalid input

**Pass Criteria:**
- ✅ Valid input succeeds
- ✅ Invalid input is rejected

**Fail Criteria:**
- ❌ Prompt accepts invalid input

---

### CT-3.4.2 — Prompt Output Shape

| Field | Value |
|:---|:---|
| **ID** | `CT-3.4.2` |
| **Name** | Prompt Output Shape |
| **Category** | Prompt Conformance |
| **Type** | Runtime |
| **Severity** | Critical |

**Description:**
Validate that prompt output strictly matches the declared output schema.

**Procedure:**
1. Send a valid input to the prompt
2. Validate the response against the output schema

**Expected:**
- Response conforms to the declared output schema

**Pass Criteria:**
- ✅ Response validates against output schema

**Fail Criteria:**
- ❌ Response has wrong structure or types

---

### CT-3.4.3 — Deterministic Template Binding

| Field | Value |
|:---|:---|
| **ID** | `CT-3.4.3` |
| **Name** | Deterministic Template Binding |
| **Category** | Prompt Conformance |
| **Type** | Runtime |
| **Severity** | High |

**Description:**
Given the same input, the prompt must produce the same structure (not necessarily same content).
Validates that template binding is deterministic.

**Procedure:**
1. Send the same valid input to the prompt 3 times
2. Extract the structural shape of each response
3. Compare all shapes

**Expected:**
- All invocations produce structurally identical output

**Pass Criteria:**
- ✅ Output shape is identical across invocations

**Fail Criteria:**
- ❌ Output shape varies between invocations

---

## 3.5 Resource Conformance Tests

**Goal:** Ensure resources behave like read-only deterministic endpoints.

---

### CT-3.5.1 — Resource Fetch

| Field | Value |
|:---|:---|
| **ID** | `CT-3.5.1` |
| **Name** | Resource Fetch |
| **Category** | Resource Conformance |
| **Type** | Runtime |
| **Severity** | Critical |

**Description:**
Call a resource and validate the output matches the declared output schema.

**Procedure:**
1. Send a `resources/read` request for the resource URI
2. Parse the response
3. Validate against the declared `output` schema

**Expected:**
- Response conforms to the output schema

**Pass Criteria:**
- ✅ Response validates against output schema

**Fail Criteria:**
- ❌ Response doesn't match output schema

---

### CT-3.5.2 — No Input Rejection

| Field | Value |
|:---|:---|
| **ID** | `CT-3.5.2` |
| **Name** | No Input Rejection |
| **Category** | Resource Conformance |
| **Type** | Runtime |
| **Severity** | Medium |

**Description:**
If a resource is defined WITHOUT an input schema, sending input should be rejected or ignored.

**Procedure:**
1. Identify resources with no `input` field
2. Send a `resources/read` request with arbitrary input data
3. Record the response

**Expected:**
- Input is rejected or has no effect on the output

**Pass Criteria:**
- ✅ Server rejects input, OR
- ✅ Server returns the same output as when called without input

**Fail Criteria:**
- ❌ Input affects the resource output (data injection risk)

---

### CT-3.5.3 — Output Stability

| Field | Value |
|:---|:---|
| **ID** | `CT-3.5.3` |
| **Name** | Output Stability |
| **Category** | Resource Conformance |
| **Type** | Runtime |
| **Severity** | High |

**Description:**
Same resource call must produce the same structure across invocations.

**Procedure:**
1. Call the resource 3 times
2. Extract structural shape of each response
3. Compare shapes

**Expected:**
- All invocations produce structurally identical output

**Pass Criteria:**
- ✅ Output shape is identical across invocations

**Fail Criteria:**
- ❌ Output shape varies between invocations

---

## 3.6 Security Conformance Tests

**Goal:** Ensure declared security schemes are actually enforced at runtime.

---

### CT-3.6.1 — Missing Authentication

| Field | Value |
|:---|:---|
| **ID** | `CT-3.6.1` |
| **Name** | Missing Authentication |
| **Category** | Security Conformance |
| **Type** | Runtime |
| **Severity** | Critical |

**Description:**
Call a secured tool/prompt without any authentication credentials.

**Procedure:**
1. Identify all entities with `security` requirements
2. For each secured entity:
   a. Omit all authentication headers/parameters
   b. Send the request
   c. Record the response

**Expected:**
- Server returns an unauthorized/authentication error

**Pass Criteria:**
- ✅ Error response indicating authentication required

**Fail Criteria:**
- ❌ Server processes the request without authentication
- ❌ Server returns a success response

---

### CT-3.6.2 — Invalid Credentials

| Field | Value |
|:---|:---|
| **ID** | `CT-3.6.2` |
| **Name** | Invalid Credentials |
| **Category** | Security Conformance |
| **Type** | Runtime |
| **Severity** | Critical |

**Description:**
Send intentionally invalid credentials (wrong API key, expired token, etc.).

**Procedure:**
1. For each secured entity:
   a. Send the request with invalid credentials (e.g., `"invalid-token-xyz"`)
   b. Record the response

**Expected:**
- Server returns an unauthorized/authentication error

**Pass Criteria:**
- ✅ Error response indicating invalid credentials

**Fail Criteria:**
- ❌ Server processes the request with invalid credentials
- ❌ Server returns a success response

---

### CT-3.6.3 — Scope Enforcement

| Field | Value |
|:---|:---|
| **ID** | `CT-3.6.3` |
| **Name** | Scope Enforcement |
| **Category** | Security Conformance |
| **Type** | Runtime |
| **Severity** | High |

**Description:**
If scopes are defined in security requirements, verify enforcement.

**Procedure:**
1. Identify entities with scoped security requirements (e.g., `bearerAuth: ["admin"]`)
2. Call with valid authentication but WITHOUT the required scope
3. Record the response

**Expected:**
- Server returns a forbidden/authorization error

**Pass Criteria:**
- ✅ Error response indicating insufficient scope/permissions

**Fail Criteria:**
- ❌ Server processes the request without proper scope

**Note:** This test requires the auth config to provide a valid but scope-limited credential. If not available, test is SKIPPED.

---

### CT-3.6.4 — Security Declaration Consistency

| Field | Value |
|:---|:---|
| **ID** | `CT-3.6.4` |
| **Name** | Security Declaration Consistency |
| **Category** | Security Conformance |
| **Type** | Static |
| **Severity** | Critical |

**Description:**
Every tool/prompt with a `security` requirement must reference a valid `components.securitySchemes` entry.

**Procedure:**
1. Parse all security requirements across tools and prompts
2. For each referenced scheme name:
   a. Verify it exists in `components.securitySchemes`
3. Flag any dangling references

**Expected:**
- All security references resolve to valid scheme definitions

**Pass Criteria:**
- ✅ All referenced security schemes exist in components

**Fail Criteria:**
- ❌ Any security reference points to an undefined scheme

---

## 3.7 Server Contract Tests

**Goal:** Ensure server-level correctness and accessibility.

---

### CT-3.7.1 — Server Reachability

| Field | Value |
|:---|:---|
| **ID** | `CT-3.7.1` |
| **Name** | Server Reachability |
| **Category** | Server Contract |
| **Type** | Runtime |
| **Severity** | Critical |

**Description:**
All URLs declared in `servers` must be reachable.

**Procedure:**
1. For each server in `servers[]`:
   a. Attempt to connect to `server.url`
   b. Send a `ping` or `initialize` request
   c. Record response

**Expected:**
- Server responds within timeout (default: 10s)

**Pass Criteria:**
- ✅ Server responds to connection attempt

**Fail Criteria:**
- ❌ Connection refused, timeout, or DNS failure

---

### CT-3.7.2 — Protocol Compliance

| Field | Value |
|:---|:---|
| **ID** | `CT-3.7.2` |
| **Name** | Protocol Compliance |
| **Category** | Server Contract |
| **Type** | Runtime |
| **Severity** | Critical |

**Description:**
Server must support MCP transport (JSON-RPC 2.0).

**Procedure:**
1. Send a valid JSON-RPC 2.0 request (e.g., `initialize`)
2. Validate the response follows JSON-RPC 2.0 format:
   - Has `jsonrpc: "2.0"` field
   - Has valid `id` field
   - Has `result` or `error` field

**Expected:**
- Server responds with valid JSON-RPC 2.0

**Pass Criteria:**
- ✅ Response is valid JSON-RPC 2.0

**Fail Criteria:**
- ❌ Response is not JSON-RPC 2.0 (e.g., plain HTTP, non-JSON)

---

### CT-3.7.3 — Version Matching

| Field | Value |
|:---|:---|
| **ID** | `CT-3.7.3` |
| **Name** | Version Matching |
| **Category** | Server Contract |
| **Type** | Runtime |
| **Severity** | High |

**Description:**
The `openmcp` version in the spec must be supported by the server.

**Procedure:**
1. Send an `initialize` request
2. Check the server's reported protocol version or capabilities
3. Compare against the spec's `openmcp` version field

**Expected:**
- Server supports the declared OpenMCP version

**Pass Criteria:**
- ✅ Server version is compatible with spec version

**Fail Criteria:**
- ❌ Version mismatch or server doesn't report version

---

## 3.8 Spec Integrity Tests (Static — No Server Required)

**Goal:** Ensure the OpenMCP spec document itself is valid and internally consistent.

---

### CT-3.8.1 — Schema Validity

| Field | Value |
|:---|:---|
| **ID** | `CT-3.8.1` |
| **Name** | Schema Validity |
| **Category** | Spec Integrity |
| **Type** | Static |
| **Severity** | Critical |

**Description:**
Validate the entire spec against the OpenMCP JSON Schema (meta-schema validation).

**Procedure:**
1. Load the OpenMCP JSON Schema (`schema.json`)
2. Validate the spec document against it
3. Report all validation errors

**Expected:**
- Spec is valid per the OpenMCP JSON Schema

**Pass Criteria:**
- ✅ Zero validation errors

**Fail Criteria:**
- ❌ Any validation error against the meta-schema

---

### CT-3.8.2 — Component References ($ref Resolution)

| Field | Value |
|:---|:---|
| **ID** | `CT-3.8.2` |
| **Name** | Component References |
| **Category** | Spec Integrity |
| **Type** | Static |
| **Severity** | Critical |

**Description:**
All `$ref` pointers in the spec must resolve to valid targets.

**Procedure:**
1. Recursively traverse the spec for `$ref` fields
2. For each `$ref`, attempt to resolve it within the spec
3. Flag any unresolvable references

**Expected:**
- All `$ref` pointers resolve

**Pass Criteria:**
- ✅ All references resolve to valid targets

**Fail Criteria:**
- ❌ Any dangling `$ref` (points to non-existent path)

---

### CT-3.8.3 — Circular Reference Detection

| Field | Value |
|:---|:---|
| **ID** | `CT-3.8.3` |
| **Name** | Circular Reference Detection |
| **Category** | Spec Integrity |
| **Type** | Static |
| **Severity** | High |

**Description:**
Detect circular `$ref` chains that could cause infinite loops.

**Procedure:**
1. Build a directed graph of all `$ref` relationships
2. Run cycle detection (DFS with visited tracking)
3. Report any cycles found

**Expected:**
- No circular reference chains exist

**Pass Criteria:**
- ✅ Reference graph is acyclic

**Fail Criteria:**
- ❌ Circular references detected (report the cycle path)

---

### CT-3.8.4 — Unused Components

| Field | Value |
|:---|:---|
| **ID** | `CT-3.8.4` |
| **Name** | Unused Components |
| **Category** | Spec Integrity |
| **Type** | Static |
| **Severity** | Low |

**Description:**
Flag components (schemas, security schemes) that are defined but never referenced.

**Procedure:**
1. Enumerate all defined components: `components.schemas`, `components.securitySchemes`
2. Scan all tools/prompts/resources for references to these components
3. Flag any unreferenced components

**Expected:**
- All components are referenced (informational flag, not a hard fail)

**Pass Criteria:**
- ✅ All components are referenced

**Fail Criteria:**
- ⚠️ Unreferenced components found (warning, not failure)

---

### CT-3.8.5 — Name Collisions

| Field | Value |
|:---|:---|
| **ID** | `CT-3.8.5` |
| **Name** | Name Collisions |
| **Category** | Spec Integrity |
| **Type** | Static |
| **Severity** | Critical |

**Description:**
Tool, prompt, and resource names must be unique across their respective namespaces.
Also check for names that are duplicated across namespaces (tool and prompt with same name).

**Procedure:**
1. Collect all tool names from `tools` keys
2. Collect all prompt names from `prompts` keys
3. Collect all resource names from `resources` keys
4. Check for duplicates within each namespace
5. Check for collisions across namespaces

**Expected:**
- No duplicate names within a namespace
- Warning (not failure) for cross-namespace collisions

**Pass Criteria:**
- ✅ All names are unique within their namespace

**Fail Criteria:**
- ❌ Duplicate names within same namespace
- ⚠️ Same name used across namespaces (warning)

---

## 3.9 Error Handling Conformance Tests

**Goal:** Ensure consistent, predictable failure behavior.

---

### CT-3.9.1 — Invalid Input Returns Error

| Field | Value |
|:---|:---|
| **ID** | `CT-3.9.1` |
| **Name** | Invalid Input Returns Error |
| **Category** | Error Handling Conformance |
| **Type** | Runtime |
| **Severity** | Critical |

**Description:**
When invalid input is sent, the server must NOT return a success response.

**Procedure:**
1. Send deliberately invalid input (reuse mutations from CT-3.1.x)
2. For each invalid request, verify:
   a. Response contains a JSON-RPC error object
   b. Response does NOT contain a success result

**Expected:**
- Every invalid input produces an error response

**Pass Criteria:**
- ✅ All invalid inputs produce errors

**Fail Criteria:**
- ❌ Any invalid input produces a success response

---

### CT-3.9.2 — Error Structure

| Field | Value |
|:---|:---|
| **ID** | `CT-3.9.2` |
| **Name** | Error Structure |
| **Category** | Error Handling Conformance |
| **Type** | Runtime |
| **Severity** | High |

**Description:**
Error responses must follow a standard format. For JSON-RPC, errors must have:
- `code` (integer)
- `message` (string)
- optional `data` (any)

**Procedure:**
1. Trigger an error (send invalid input)
2. Parse the error response
3. Validate it has the required error structure fields

**Expected:**
- Error response follows JSON-RPC error format

**Pass Criteria:**
- ✅ Error has `code` (integer) and `message` (string)

**Fail Criteria:**
- ❌ Error response is malformed or missing required fields
- ❌ Error is returned as a plain string instead of structured object

---

### CT-3.9.3 — No Silent Failures

| Field | Value |
|:---|:---|
| **ID** | `CT-3.9.3` |
| **Name** | No Silent Failures |
| **Category** | Error Handling Conformance |
| **Type** | Runtime |
| **Severity** | Critical |

**Description:**
There must be no partial success on invalid input. The server must not execute
half of a tool and return partial results alongside an error.

**Procedure:**
1. Send input with a mix of valid and invalid fields
2. Check that the response is EITHER a full error OR a full success
3. It must NOT be both (no result + error in the same response)

**Expected:**
- Response is unambiguously error or success, never both

**Pass Criteria:**
- ✅ Response has `result` XOR `error`, never both

**Fail Criteria:**
- ❌ Response contains both `result` and `error`
- ❌ Response contains neither `result` nor `error`

---

## 3.10 Determinism Tests

**Goal:** Ensure MCP server behavior is predictable and consistent for AI agents.

---

### CT-3.10.1 — Schema Determinism (Output Shape)

| Field | Value |
|:---|:---|
| **ID** | `CT-3.10.1` |
| **Name** | Schema Determinism |
| **Category** | Determinism |
| **Type** | Runtime |
| **Severity** | Critical |

**Description:**
Output shape must NOT change across runs. Same input → same output structure.
Values may differ, but the keys, types, and nesting must be identical.

**Procedure:**
1. For each tool/prompt:
   a. Send the same valid input 3 times
   b. Extract the "shape signature" (recursive key+type map)
   c. Compare all shape signatures

**Expected:**
- All shape signatures are identical

**Pass Criteria:**
- ✅ Identical shape signatures across all runs

**Fail Criteria:**
- ❌ Shape varies between runs

---

### CT-3.10.2 — Tool Contract Stability

| Field | Value |
|:---|:---|
| **ID** | `CT-3.10.2` |
| **Name** | Tool Contract Stability |
| **Category** | Determinism |
| **Type** | Runtime |
| **Severity** | High |

**Description:**
Same input schema → same validation behavior across runs.
The server must consistently accept or reject the same input.

**Procedure:**
1. For each tool:
   a. Send a valid input → expect success (3 times)
   b. Send an invalid input → expect error (3 times)
   c. Verify consistent behavior

**Expected:**
- Valid input always succeeds; invalid input always fails

**Pass Criteria:**
- ✅ Consistent accept/reject behavior across all runs

**Fail Criteria:**
- ❌ Same input succeeds sometimes and fails other times

---

### CT-3.10.3 — No Undeclared Fields

| Field | Value |
|:---|:---|
| **ID** | `CT-3.10.3` |
| **Name** | No Undeclared Fields |
| **Category** | Determinism |
| **Type** | Runtime |
| **Severity** | High |

**Description:**
Runtime must not introduce new fields in the output that are not declared in the spec.
This is different from CT-3.2.3 in that it checks across multiple runs.

**Procedure:**
1. For each entity:
   a. Send valid input 3 times
   b. Collect all unique output fields across all runs
   c. Compare against declared output schema fields
   d. Flag any fields that appear in some runs but not the schema

**Expected:**
- No phantom fields across any run

**Pass Criteria:**
- ✅ All output fields exist in the declared schema across all runs

**Fail Criteria:**
- ❌ Undeclared fields appear in any run

---

## Appendix A: Test Execution Model

```
Step 1: Parse Spec
  └─ Validate OpenMCP JSON Schema (CT-3.8.1)
  └─ Build entity catalog (tools, prompts, resources)
  └─ Resolve all $ref references

Step 2: Generate Test Cases
  └─ For each entity:
      ├─ Happy path (valid input)
      ├─ Mutation cases (systematic)
      └─ Edge cases (null, deep nesting)

Step 3: Execute Against Server
  └─ JSON-RPC calls via MCPClient
  └─ Record request/response pairs

Step 4: Validate Responses
  └─ Schema validation
  └─ Status classification:
      ├─ ✅ PASSED — Expected result
      ├─ ⚠️ SKIPPED — Cannot run (e.g., no auth config)
      ├─ ❌ FAILED — Wrong result
      └─ 💥 ERROR — Exception/crash
```

## Appendix B: Output Report Format

```json
{
  "summary": {
    "total_tests": 120,
    "passed": 110,
    "failed": 8,
    "skipped": 2,
    "errors": 0,
    "pass_rate": "91.7%"
  },
  "server_url": "http://localhost:3000",
  "spec_version": "1.0.0",
  "timestamp": "2026-04-01T00:00:00Z",
  "duration_ms": 5432,
  "results": [
    {
      "test_id": "CT-3.1.1",
      "test_name": "Valid Input Happy Path",
      "category": "Schema Input Conformance",
      "entity": "tool.createUser",
      "status": "PASSED",
      "duration_ms": 45
    }
  ],
  "failures": [
    {
      "test_id": "CT-3.2.2",
      "type": "schema_violation",
      "entity": "tool.createUser",
      "issue": "Missing required output field: email",
      "expected": "Field 'email' present in output",
      "actual": "Field 'email' is missing"
    }
  ]
}
```

## Appendix C: 42Crunch Mapping

| 42Crunch Concept | OpenMCP Conformance Equivalent | Test IDs |
|:---|:---|:---|
| Schema injection | Input schema violation tests | CT-3.1.2 – CT-3.1.7 |
| Parameter injection | Tool input mutations | CT-3.1.3, CT-3.3.2, CT-3.3.3 |
| Header injection | Security/auth tests | CT-3.6.1, CT-3.6.2 |
| HTTP method tests | Tool existence tests | CT-3.3.1 |
| Response validation | Output schema validation | CT-3.2.1 – CT-3.2.5 |
| Auth tests | securitySchemes enforcement | CT-3.6.1 – CT-3.6.4 |
| Contract validation | Full contract tests | CT-3.3.4, CT-3.4.x, CT-3.5.x |
| Spec linting | Spec integrity tests | CT-3.8.1 – CT-3.8.5 |
