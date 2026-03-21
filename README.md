# MCPcrunch 🔍

**MCPcrunch** is a comprehensive security and structural validation framework for the **OpenMCP Specification**. 

Inspired by the philosophy of 42Crunch for OpenAPI, MCPcrunch applies both deterministic (static analysis) and semantic (LLM-based) validation rules to ensure that your Model Context Protocol (OpenMCP) specifications are robust, secure, and ready for autonomous agentic environments.

## 🚀 Key Features

*   **Deterministic Auditing**: 20+ rules covering Format (FMT), Data Quality (DAT), and Security (SEC) categories.
*   **Semantic Risk Analysis**: LLM-powered (Gemini/OpenAI) detection of Adversarial (ADV) threats like Prompt Injection and Sensitive Field Leakage.
*   **42Crunch-Style Scoring**: Instant security score (0-100) based on severity-weighted issue detection.
*   **Developer Friendly**: Use as a standalone CLI tool or integrate directly into your Python workflows.
*   **Rich Reporting**: Beautiful terminal output with summary tables and detailed issue breakdowns.

## 🛠 Installation

```bash
# From PyPI (Recommended)
pip install mcpcrunch

# From local source
pip install .
```

## 📖 Usage

### Command Line Interface (CLI)

Audit an OpenMCP specification file:

```bash
# Deterministic audit (default)
mcpcrunch spec.json --schema schema.json

# Full audit with semantic analysis (Gemini)
mcpcrunch spec.json --llm gemini --api-key YOUR_GEMINI_API_KEY
```

> [!NOTE]
> By omitting the `--llm` flag, the auditor will only perform deterministic (static) checks.

### Python API

Integrate validation directly into your application:

```python
from mcpcrunch import MCPcrunch, GeminiProvider

# Initialize engine (Deterministic only)
crunch = MCPcrunch(schema_path="schema.json")

# Full engine (Deterministic + Semantic)
llm = GeminiProvider(api_key="your-key")
crunch_with_llm = MCPcrunch(schema_path="schema.json", llm=llm)

# Audit a specification
with open("myspec.json") as f:
    spec_data = json.load(f)

report = crunch_with_llm.audit(spec_data)

print(f"Overall Security Score: {report.overall_score}/100")
for issue in report.deterministic.issues + report.semantic.issues:
    print(f"[{issue.severity}] {issue.rule_id}: {issue.message}")
```

## 📋 Validation Rules

For a detailed list of all supported rules and their impact, see [validations.md](./validations.md).

*   **FMT**: Format integrity and versioning.
*   **DAT**: Data boundaries and context window protection.
*   **SEC**: Authentication and transport security.
*   **ADV**: Adversarial threat prevention (Semantic).

## 🧪 Testing

Run the comprehensive test suite (16+ tests):

```bash
pytest tests/
```

---
Built with ❤️ for the AI Agent Ecosystem by **Anish Chelliah CR**.
