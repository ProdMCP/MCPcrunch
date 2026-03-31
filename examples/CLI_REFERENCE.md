# MCPcrunch — CLI Usage Examples

## Security Audit (Original)

```bash
# Basic audit — score your OpenMCP spec
mcpcrunch examples/taskforge_production.json --schema schema.json

# Audit with semantic analysis (requires LLM API key)
mcpcrunch examples/taskforge_production.json --schema schema.json --llm gemini --api-key $GEMINI_API_KEY
```

## Conformance Testing

### Static Tests (No Server Required)

```bash
# Run all 5 static spec integrity tests
mcpcrunch conformance examples/taskforge_production.json --schema schema.json --static-only

# Run only the spec_integrity category
mcpcrunch conformance examples/taskforge_production.json --schema schema.json --category spec_integrity

# Save JSON report for CI
mcpcrunch conformance examples/taskforge_production.json --schema schema.json --static-only --output report.json
```

### Runtime Tests (Requires MCP Server)

```bash
# Full suite against a live server
mcpcrunch conformance examples/taskforge_production.json \
  --server-url https://api.taskforge.prodmcp.dev/mcp \
  --schema schema.json

# With bearer token authentication
mcpcrunch conformance examples/taskforge_production.json \
  --server-url https://api.taskforge.prodmcp.dev/mcp \
  --bearer-token $MCP_TOKEN

# With API key authentication
mcpcrunch conformance examples/taskforge_production.json \
  --server-url https://api.taskforge.prodmcp.dev/mcp \
  --api-key $API_KEY \
  --api-key-header X-API-Key \
  --api-key-in header

# Run only schema input tests
mcpcrunch conformance examples/taskforge_production.json \
  --server-url http://localhost:3000 \
  --category schema_input

# Run only security tests
mcpcrunch conformance examples/taskforge_production.json \
  --server-url http://localhost:3000 \
  --category security \
  --bearer-token $MCP_TOKEN

# Custom timeout (30s per request)
mcpcrunch conformance examples/taskforge_production.json \
  --server-url http://localhost:3000 \
  --timeout 30.0
```

### Available Categories

| Category | ID | Type | Description |
|:---|:---|:---:|:---|
| Schema Input | `schema_input` | Runtime | Validates input handling (CT-3.1.x) |
| Schema Output | `schema_output` | Runtime | Validates output schemas (CT-3.2.x) |
| Tool Contract | `tool_contract` | Runtime | Tool invocation behavior (CT-3.3.x) |
| Prompt Contract | `prompt_contract` | Runtime | Prompt template behavior (CT-3.4.x) |
| Resource Contract | `resource_contract` | Runtime | Resource read behavior (CT-3.5.x) |
| Security | `security` | Mixed | Auth enforcement (CT-3.6.x) |
| Server Contract | `server_contract` | Runtime | Protocol compliance (CT-3.7.x) |
| Spec Integrity | `spec_integrity` | **Static** | Spec structure validation (CT-3.8.x) |
| Error Handling | `error_handling` | Runtime | Error response format (CT-3.9.x) |
| Determinism | `determinism` | Runtime | Behavioral consistency (CT-3.10.x) |

## CI/CD Integration

```bash
# In your CI pipeline — exits with code 1 on failures
mcpcrunch examples/taskforge_production.json --schema schema.json && \
mcpcrunch conformance examples/taskforge_production.json --schema schema.json --static-only --output ci_report.json
```
