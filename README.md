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
  <img src="https://img.shields.io/badge/tests-288%20passing-brightgreen" alt="Tests">
</p>

---

Inspired by [42Crunch](https://42crunch.com) for OpenAPI, MCPcrunch applies deterministic, semantic, and contract-level validation to ensure your MCP specifications are robust, secure, and production-ready.

## 🚀 Key Features

- **Partitioned Scoring** — Separate Security (0–30) and Data Validation (0–70) scores summing to 100. Know exactly where your spec is weak.
- **Component-Wise Breakdown** — Per-tool, per-prompt, per-resource score table. Spot the single bad actor dragging down your entire score.
- **Documentation Quality Rules** — New `OMCP-DOC` category flags undocumented capabilities and responses, enforcing self-describing APIs.
- **Security Audit** — 22 deterministic rules across Format (FMT), Data Quality (DAT), Security (SEC), and Documentation (DOC). Instant 0–100 score.
- **Conformance Testing** — 13 static tests and 40 runtime test definitions across 10 categories.
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
# Deterministic audit (OpenMCP or OpenAPI spec)
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
from mcpcrunch import MCPcrunch, ConformanceRunner, CapabilityScore

# ── Security Audit ──
crunch = MCPcrunch("schema.json")
with open("spec.json") as f:
    spec = json.load(f)

report = crunch.audit(spec)
det = report.deterministic

print(f"Overall: {det.score}/100")
print(f"Security: {det.security_score}/30  Data Validation: {det.validation_score}/70")

# ── Per-Capability Scores ──
for cap in det.capability_scores:
    print(f"  {cap.type:8} {cap.name:30} sec={cap.security_score}/30  val={cap.validation_score}/70  total={cap.score}/100")

# ── Conformance Testing ──
runner = ConformanceRunner(spec_path="spec.json", schema_path="schema.json")
conf = runner.run_static()

print(f"Conformance Score: {conf.summary.score}/100  Grade: {conf.summary.grade}")
print(f"Passed: {conf.summary.passed}/{conf.summary.total_tests}")
```

## 📊 Scoring Model

MCPcrunch uses a **partitioned penalty-based scoring** system.

### Audit Score (0–100)

Scores start at 100 and are split across two independent pools:

| Pool | Max | Rules that deduct from it |
|---|---|---|
| **Security** | 30 | All `OMCP-SEC-*` rules |
| **Data Validation** | 70 | All `OMCP-FMT-*`, `OMCP-DAT-*`, `OMCP-DOC-*` rules |

Severity penalties:

| Severity | Penalty per violation |
|---|---|
| Critical | −20 |
| High | −10 |
| Medium | −5 |
| Low | −2 |
| Info | 0 |

### Component-Wise Score Table

Every tool, prompt, and resource receives its own score breakdown in the CLI output:

```
┌──────────┬──────────────────────┬──────────┬──────────────────┬───────┐
│ Type     │ Name                 │ Security │ Data Validation  │ Score │
│          │                      │ /30      │ /70              │ /100  │
├──────────┼──────────────────────┼──────────┼──────────────────┼───────┤
│ tool     │ create_ticket        │ 30       │ 70               │ 100   │
│ tool     │ get_weather          │ 30       │ 65               │ 95    │
│ prompt   │ summarize_text       │ 30       │ 70               │ 100   │
│ resource │ item_detail          │ 20       │ 70               │ 90    │
└──────────┴──────────────────────┴──────────┴──────────────────┴───────┘
```

This tells you exactly which capability is dragging your score down and why.

## 📋 Security Audit Rules

### Documentation Rules (NEW in v0.3.0)

| Rule | Severity | Pool | Penalty | What it checks |
|---|---|---|---|---|
| `OMCP-DOC-001` | High | Data | −10 | One or more capabilities in a section (tools/prompts/resources) missing a `description` field |
| `OMCP-DOC-002` | High | Data | −10 | One or more capabilities in a section missing a response description (`output_description` / 200 body description) |

**Key behaviour:** these rules aggregate at the **section level** — if 5 tools are missing descriptions that is **one** -10 deduction, not -50. Affected names are listed in the issue message.

### Security Rules

| Rule | Severity | What it checks |
|---|---|---|
| `OMCP-SEC-001` | Critical | Security scheme binding (scheme names resolve in `components.securitySchemes`) |
| `OMCP-SEC-002` | Critical | No API keys exposed in query parameters |
| `OMCP-SEC-003` | High | Auth enforcement — all tools have security requirements |
| `OMCP-SEC-005` | High | Transport safety — servers use HTTPS/WSS |
| `OMCP-SEC-007` | Medium | Auth error handling — 401/403 responses on secured tools |
| `OMCP-SEC-008` | Medium | 406 Not Acceptable response handling |
| `OMCP-SEC-009` | Medium | 415 Unsupported Media Type response handling |
| `OMCP-SEC-010` | Medium | 429 Rate Limit response handling |
| `OMCP-SEC-011` | Medium | Default catch-all error response |
| `OMCP-SEC-012` | Critical | Per-operation security field present when global security absent |
| `OMCP-ADV-005` | High | No localhost server bindings |

For the full rule catalogue see [validations.md](./validations.md).

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

### Conformance Scoring

| Severity | Penalty per failed test |
|:--|:--:|
| Critical | −15 |
| High | −8 |
| Medium | −4 |
| Low | −2 |

**Grades:** A (90–100) · B (75–89) · C (60–74) · D (40–59) · F (0–39)

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
# Run the full test suite (288 tests)
PYTHONPATH=src pytest tests/

# Run with verbose output
PYTHONPATH=src pytest tests/ -v
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
