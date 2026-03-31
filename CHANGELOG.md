# Changelog

All notable changes to MCPcrunch will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] — 2026-04-01

### 🚀 Major: Conformance Testing Engine

MCPcrunch now includes a **full conformance testing suite** — a deterministic, contract-level validation engine that verifies whether an MCP server implements the OpenMCP specification correctly. Think of it as "42Crunch for MCP."

#### Added

**Conformance Engine** (`mcpcrunch.conformance`)
- `ConformanceRunner` — orchestrator supporting static-only, single-category, and full (static + runtime) test modes
- `MCPClient` — JSON-RPC 2.0 transport with Bearer and API Key authentication
- `SchemaMutator` — deterministic mutation engine (fixed-seed RNG) for generating valid inputs, type violations, constraint violations, missing required fields, and extra property injections
- `Reporter` — Rich terminal output and JSON export for conformance results
- 40 test definitions across 10 categories (CT-3.1.x through CT-3.10.x)

**13 Static Conformance Tests** (run without a server)
| Test ID | Name | Severity | Maps to |
|:--|:--|:--:|:--|
| CT-3.8.1 | Schema Validity | High | JSON Schema meta-validation |
| CT-3.8.2 | Component References | High | `$ref` pointer resolution |
| CT-3.8.3 | Circular References | High | Cycle detection in `$ref` graphs |
| CT-3.8.4 | Unused Components | High | Dead component detection |
| CT-3.8.5 | Name Collisions | High | Cross-namespace duplicate names |
| CT-3.8.6 | Schema Strictness | **Critical** | OMCP-DAT-001 |
| CT-3.8.7 | String Boundaries | High | OMCP-DAT-003 |
| CT-3.8.8 | Array Boundaries | High | OMCP-DAT-005 |
| CT-3.8.9 | Numeric Boundaries | Medium | OMCP-DAT-006 |
| CT-3.8.10 | Security Coverage | High | OMCP-SEC-003 |
| CT-3.8.11 | Bearer Format | Medium | OMCP-SEC-004 |
| CT-3.8.12 | Transport Security | High | OMCP-SEC-005 |
| CT-3.8.13 | Description Quality | Medium | OMCP-FMT-002+ |

**Weighted Conformance Scoring**
- `TestSeverity` enum: Critical (15pt penalty), High (8pt), Medium (4pt), Low (2pt)
- Weighted score (0–100) with letter grades: A (90+), B (75–89), C (60–74), D (40–59), F (<40)
- Score and grade displayed in Rich terminal output and JSON exports

**CLI Subcommand**
- `mcpcrunch conformance <spec> [options]` — new subcommand with full backward compatibility
- Flags: `--static-only`, `--category`, `--server-url`, `--bearer-token`, `--api-key`, `--api-key-header`, `--api-key-in`, `--timeout`, `--output`, `--schema`
- Original `mcpcrunch <spec>` audit command continues to work unchanged

**Python API**
- `ConformanceRunner` — public API for programmatic conformance testing
- `ConformanceReport`, `ConformanceTestResult`, `TestStatus`, `TestSeverity`, `TestCategory`, `AuthConfig` — all exported from `mcpcrunch`

**Examples**
- `taskforge_production.json` — production-grade spec (6 tools, 5 prompts, 4 resources) scoring 100/100 Grade A
- `notekeeper_average.json` — typical "quick-start" spec scoring 41/100 Grade D
- `prodmcp_test_example.py` — validates production spec (audit + conformance)
- `prodmcp_average_example.py` — validates average spec, demonstrates scoring gap
- `usage_guide.py` — 10 runnable examples covering every API surface
- `CLI_REFERENCE.md` — complete CLI command reference with all flags and categories

**Tests** — 236 passing tests
- `test_conformance_models.py` (40 tests) — enums, auth, results, scoring, grading
- `test_schema_mutator.py` (58 tests) — all 7 mutation generators
- `test_spec_integrity.py` (27 tests) — all 13 static tests with valid/invalid/edge specs
- `test_conformance_runner.py` (31 tests) — runner API, categories, example specs
- `test_conformance_client.py` (15 tests) — headers, auth, request IDs
- `test_conformance_runtime.py` (36 tests) — all 10 runtime categories (mocked)
- `test_conformance_reporter.py` (8 tests) — JSON export, Rich output
- `test_conformance_cli.py` (10 tests) — CLI integration

#### Changed
- `pyproject.toml` — added `httpx>=0.27.0` dependency, pytest config to isolate test collection
- `cli.py` — manual routing for subcommand support without breaking audit workflow
- `__init__.py` — exports `ConformanceRunner`, `ConformanceReport`, `TestStatus`, `TestSeverity`, `TestCategory`, `AuthConfig`

---

## [0.1.0] — 2026-03-28

### Initial Release

**Security Audit Engine**
- 17 deterministic validation rules across Format (FMT), Data Quality (DAT), and Security (SEC)
- Semantic (LLM-powered) analysis via Gemini and OpenAI providers
- 42Crunch-style scoring (0–100) with severity-weighted penalties
- Rich terminal reporting with summary tables and detailed issue breakdowns
- CLI: `mcpcrunch <spec> --schema <schema> [--llm gemini|openai --api-key KEY]`
- Python API: `MCPcrunch.audit(spec)` returning `FullReport`

**Example Specs**
- `minimal_valid.json`, `vulnerable_security.json`, `vulnerable_data_quality.json`
- `adversarial_poisoning.json`, `complex_shadowing.json`
