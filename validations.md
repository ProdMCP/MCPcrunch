# OpenMCP Validation Rules (MCPcrunch)

| ID | Category | Rule Name | Description | Severity | Type |
|:---|:---:|:---|:---|:---:|:---:|
| **OMCP-FMT-001** | Format | Root Versioning | `openmcp` key must match `^[0-9]+\.[0-9]+\.[0-9]+$`. | Critical | Det |
| **OMCP-FMT-002** | Format | Info Metadata | `info` object must contain `title` and `version`. | High | Det |
| **OMCP-FMT-003** | Format | URI Format | `servers.url` must be a valid URI. | High | Det |
| **OMCP-FMT-004** | Format | $ref Integrity | All `$ref` pointers must resolve correctly. | High | Det |
| **OMCP-FMT-005** | Format | Payload Size | Warn if the specification file exceeds 1MB. | Medium | Det |
| **OMCP-FMT-006** | Format | Unique IDs | Tool, prompt, and resource names must be unique. | High | Det |
| **OMCP-DAT-001** | Data | Strict Objects | Input schemas must set `additionalProperties: false`. | Critical | Det |
| **OMCP-DAT-002** | Data | Object Properties | Object schemas must define `properties`. | Critical | Det |
| **OMCP-DAT-003** | Data | String Lengths | String parameters must have `maxLength`. | High | Det |
| **OMCP-DAT-004** | Data | Regex Patterns | Sensitive strings (paths, URLs) must have `pattern`. | High | Det |
| **OMCP-DAT-005** | Data | Array Limits | Output arrays must have `maxItems`. | High | Det |
| **OMCP-DAT-006** | Data | Numeric Bounds | Numbers should have `minimum` and `maximum`. | Medium | Det |
| **OMCP-SEC-001** | Security | Security Binding | Tools must map to valid `securitySchemes`. | Critical | Det |
| **OMCP-SEC-002** | Security | Safe API Keys | API keys must not be in `query` parameters. | Critical | Det |
| **OMCP-SEC-003** | Security | Auth Enforcement | Flag tools with empty or missing `security`. | High | Det |
| **OMCP-SEC-004** | Security | Bearer Format | Bearer tokens should specify `bearerFormat`. | Medium | Det |
| **OMCP-SEC-005** | Security | Transport Safety | Server URLs should use `https` or `wss`. | High | Det |
| **OMCP-ADV-001** | Adversarial| Semantic Poisoning| Scan descriptions for prompt injection. | Critical | Sem |
| **OMCP-ADV-002** | Adversarial| Rug-pull Detection| Detect semantic changes vs static version. | High | Sem |
| **OMCP-ADV-003** | Adversarial| Secret Leakage | Flag potential secrets in output schemas. | High | Sem |
| **OMCP-ADV-004** | Adversarial| Tool Shadowing | Detect ambiguous or generic tool naming. | Medium | Sem |
| **OMCP-ADV-005** | Adversarial| Localhost SSRF | Flag server bindings to localhost IPs. | High | Det |
