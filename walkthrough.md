# Walkthrough - MCPcrunch Validation Package

`MCPcrunch` is a comprehensive security and structural validation framework for the OpenMCP Specification. It implements the 42Crunch-style auditing philosophy for AI agents.

## Features Implemented

- **Deterministic Validation**: Covers 20+ rules (FMT, DAT, SEC) documented in [validations.md](file:///Users/muruga/Projects/MCPcrunch/validations.md).
- **Semantic Validation**: LLM-based analysis for Adversarial (ADV) threats.
- **Comprehensive Testing**: 16 tests covering rules, scoring, engine, and CLI.
- **PyPI Ready**: Configured for distribution with `pyproject.toml` and verified builds.
- **Scoring Engine**: Severity-weighted scoring (0-100) similar to 42Crunch.
- **CLI Tool**: Rich terminal output with summary tables and detailed issue reports.
- **LLM Providers**: Support for Google Gemini and OpenAI with configurable API keys.

## Verification Results

### 1. Vulnerable Specification Test
I ran `MCPcrunch` against a sample specification containing multiple intentional vulnerabilities:
- Invalid semver for `openmcp`.
- Missing mandatory metadata.
- Localhost server binding (SSRF risk).
- Missing `additionalProperties: false` on inputs.
- Missing `maxLength` on strings and `maxItems` on arrays.
- API keys transmitted via query parameters.

**Audit Report:**
- **Deterministic Score**: 0/100
- **Issues Found**: 9
- **Overall Score**: 0/100

### 2. Secure Specification Test
I ran `MCPcrunch` against a hardened specification addressing all the above issues.

**Audit Report:**
- **Deterministic Score**: 100/100
- **Issues Found**: 0
- **Overall Score**: 100/100

## How to Use

### Installation
```bash
pip install .
```

### Running an Audit
```bash
# Basic deterministic audit
mcpcrunch sample_spec.json --schema schema.json

# Semantic audit with Gemini
mcpcrunch sample_spec.json --llm gemini --api-key YOUR_KEY
```

## Examples Directory
A comprehensive set of examples is available in the [examples/](file:///Users/muruga/Projects/MCPcrunch/examples/) directory:
- `minimal_valid.json`: A baseline secure specification.
- `vulnerable_data_quality.json`: Demonstrates missing boundaries and unconstrained objects.
- `vulnerable_security.json`: Demonstrates insecure API key transmission and missing security arrays.
- `adversarial_poisoning.json`: Contains semantic poisoning in tool descriptions.
- `complex_shadowing.json`: Highlights generic tool naming risks.

### Programmatic Usage (Python API)
You can integrate `MCPcrunch` directly into your Python workflows:

```python
from mcpcrunch import MCPcrunch, GeminiProvider

# 1. Initialize engine
crunch = MCPcrunch(schema_path="schema.json")

# 2. (Optional) Add LLM for semantic checks
llm = GeminiProvider(api_key="your-key")
crunch_with_llm = MCPcrunch(schema_path="schema.json", llm=llm)

# 3. Audit a spec (dict)
spec_data = { ... }
report = crunch.audit(spec_data)

print(f"Score: {report.overall_score}")
for issue in report.deterministic.issues:
    print(f"[{issue.severity}] {issue.message}")
```

## Key Files
- [deterministic.py](file:///Users/muruga/Projects/MCPcrunch/src/mcpcrunch/validators/deterministic.py): Deterministic rules.
- [semantic.py](file:///Users/muruga/Projects/MCPcrunch/src/mcpcrunch/validators/semantic.py): LLM-based rules.
- [scoring.py](file:///Users/muruga/Projects/MCPcrunch/src/mcpcrunch/scoring.py): 42Crunch-style scoring.
- [cli.py](file:///Users/muruga/Projects/MCPcrunch/src/mcpcrunch/cli.py): Terminal interface.
