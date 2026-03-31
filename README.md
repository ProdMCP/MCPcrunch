<p align="center">
  <img src="https://raw.githubusercontent.com/ProdMCP/MCPcrunch/main/assets/mcpcrunch-logo.png" alt="MCPcrunch Logo" width="480">
</p>

<h1 align="center">MCPcrunch 🔍</h1>

<p align="center">
  <strong>Comprehensive security auditing and conformance testing framework for the OpenMCP Specification.</strong>
</p>

<p align="center">
  <a href="https://pypi.org/project/mcpcrunch/"><img src="https://img.shields.io/pypi/v/mcpcrunch?color=blue&label=PyPI" alt="PyPI"></a>
  <a href="https://github.com/ProdMCP/MCPcrunch/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="License"></a>
  <img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python">
  <img src="https://img.shields.io/badge/tests-236%20passing-brightgreen" alt="Tests">
</p>

---

Inspired by [42Crunch](https://42crunch.com) for OpenAPI, MCPcrunch applies deterministic, semantic, and contract-level validation to ensure your MCP specifications are robust, secure, and production-ready.

## 🚀 Key Features

- **Security Audit** — 17+ deterministic rules covering Format (FMT), Data Quality (DAT), and Security (SEC). Instant 0–100 security score.
- **Conformance Testing** — 13 static tests and 40 runtime test definitions across 10 categories. Validates that specs and servers implement the OpenMCP contract correctly.
- **Weighted Scoring** — Severity-based conformance score (0–100) with letter grades (A/B/C/D/F).
- **Semantic Analysis** — LLM-powered (Gemini/OpenAI) detection of adversarial threats like prompt injection and sensitive field leakage.
- **Dual Interface** — Full-featured CLI and first-class Python API.
- **Rich Reporting** — Beautiful terminal output with summary tables, score/grade display, and JSON export.

## 🛠 Installation

```bash
pip install mcpcrunch
```

## 📖 Quick Start

### Security Audit (CLI)

```bash
# Deterministic audit
mcpcrunch spec.json --schema schema.json

# With semantic analysis
mcpcrunch spec.json --schema schema.json --llm gemini --api-key $GEMINI_API_KEY
```

### Conformance Testing (CLI)

```bash
# Static conformance tests (no server needed)
mcpcrunch conformance spec.json --schema schema.json --static-only

# Full suite against a live server
mcpcrunch conformance spec.json --server-url https://api.example.com/mcp --bearer-token $TOKEN

# Export JSON report
mcpcrunch conformance spec.json --schema schema.json --static-only --output report.json
```

### Python API

```python
import json
from mcpcrunch import MCPcrunch, ConformanceRunner

# ── Security Audit ──
crunch = MCPcrunch("schema.json")
with open("spec.json") as f:
    spec = json.load(f)

report = crunch.audit(spec)
print(f"Security Score: {report.overall_score}/100")

# ── Conformance Testing ──
runner = ConformanceRunner(spec_path="spec.json", schema_path="schema.json")
conf = runner.run_static()

print(f"Conformance Score: {conf.summary.score}/100")
print(f"Grade: {conf.summary.grade}")
print(f"Passed: {conf.summary.passed}/{conf.summary.total_tests}")
```

## 🧪 Conformance Test Catalog

### Static Tests (no server required)

| Test | Name | Severity | What it checks |
|:--|:--|:--:|:--|
| CT-3.8.1 | Schema Validity | High | Spec validates against OpenMCP JSON Schema |
| CT-3.8.2 | Component References | High | All `$ref` pointers resolve |
| CT-3.8.3 | Circular References | High | No cycles in `$ref` graphs |
| CT-3.8.4 | Unused Components | High | No dead component definitions |
| CT-3.8.5 | Name Collisions | High | Unique names across tools/prompts/resources |
| CT-3.8.6 | Schema Strictness | Critical | `additionalProperties: false` on inputs |
| CT-3.8.7 | String Boundaries | High | All strings have `maxLength` |
| CT-3.8.8 | Array Boundaries | High | All arrays have `maxItems` |
| CT-3.8.9 | Numeric Boundaries | Medium | All numbers have `minimum`/`maximum` |
| CT-3.8.10 | Security Coverage | High | All tools have security bindings |
| CT-3.8.11 | Bearer Format | Medium | Bearer schemes specify `bearerFormat` |
| CT-3.8.12 | Transport Security | High | All servers use `https://` or `wss://` |
| CT-3.8.13 | Description Quality | Medium | All entities have descriptions |

### Scoring

Conformance score is penalty-based (starts at 100):

| Severity | Penalty per failed test |
|:--|:--:|
| Critical | −15 |
| High | −8 |
| Medium | −4 |
| Low | −2 |

**Grades:** A (90–100) · B (75–89) · C (60–74) · D (40–59) · F (0–39)

## 📋 Security Audit Rules

For the full list of 17+ validation rules, see [validations.md](./validations.md).

- **FMT** — Format integrity, versioning, URI strictness
- **DAT** — Data boundaries, context window protection, strict schemas
- **SEC** — Authentication binding, transport security, API key safety
- **ADV** — Adversarial threat prevention (semantic/LLM-based)

## 📂 Examples

See [`examples/`](./examples/) for complete usage demonstrations:

| File | Description |
|:--|:--|
| `taskforge_production.json` | Production-grade spec (6 tools, 5 prompts, 4 resources) — 100/100 |
| `notekeeper_average.json` | Typical spec with common issues — 41/100 |
| `prodmcp_test_example.py` | Validates production spec (audit + conformance) |
| `prodmcp_average_example.py` | Demonstrates scoring gap on average spec |
| `usage_guide.py` | 10 runnable examples covering every API |
| `CLI_REFERENCE.md` | Complete CLI command reference |

## 🧪 Testing

```bash
# Run the full test suite (236 tests)
pytest tests/

# Run with verbose output
pytest tests/ -v
```

## 📦 Requirements

- Python ≥ 3.10
- jsonschema ≥ 4.20.0
- pydantic ≥ 2.5.0
- rich ≥ 13.7.0
- httpx ≥ 0.27.0

## 📄 License

MIT — see [LICENSE](./LICENSE).

---

Built with ❤️ for the AI Agent Ecosystem by **Anish Chelliah CR** · [ProdMCP](https://prodmcp.dev)
