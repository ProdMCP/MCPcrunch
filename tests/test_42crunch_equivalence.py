"""Tests for the new/improved deterministic rules: DAT-001 (output), DAT-007, DAT-008.

Maps 42Crunch OpenAPI findings to MCPcrunch OpenMCP equivalents.
"""

import pytest
from mcpcrunch.validators.deterministic import DeterministicValidator
from mcpcrunch.models import Severity


@pytest.fixture
def validator():
    return DeterministicValidator("schema.json")


def _base_spec(**overrides):
    """Create a minimal valid spec and merge overrides."""
    spec = {
        "openmcp": "1.0.0",
        "info": {"title": "Test", "version": "1.0.0"},
    }
    spec.update(overrides)
    return spec


# ═══════════════════════════════════════════════════════════════════════════════
# OMCP-DAT-001: additionalProperties — extended to output schemas
# 42Crunch: "Schema in a response allows additional properties"
# ═══════════════════════════════════════════════════════════════════════════════


class TestDAT001OutputSchemas:
    """OMCP-DAT-001 should flag OUTPUT schemas missing additionalProperties: false."""

    def test_output_schema_missing_additional_properties(self, validator):
        """Output object schema without additionalProperties → flagged."""
        spec = _base_spec(tools={
            "get_data": {
                "output": {
                    "type": "object",
                    "properties": {"name": {"type": "string", "maxLength": 100}},
                },
                "security": [{"bearer": []}],
            }
        }, components={"securitySchemes": {"bearer": {"type": "http", "scheme": "bearer"}}})

        issues = validator.validate(spec)
        dat001 = [i for i in issues if i.rule_id == "OMCP-DAT-001"]
        assert len(dat001) >= 1
        assert any("Output" in i.message for i in dat001)

    def test_output_schema_with_additional_properties_false(self, validator):
        """Output object schema with additionalProperties: false → not flagged."""
        spec = _base_spec(tools={
            "get_data": {
                "output": {
                    "type": "object",
                    "properties": {"name": {"type": "string", "maxLength": 100}},
                    "additionalProperties": False,
                },
                "security": [{"bearer": []}],
            }
        }, components={"securitySchemes": {"bearer": {"type": "http", "scheme": "bearer"}}})

        issues = validator.validate(spec)
        dat001 = [i for i in issues if i.rule_id == "OMCP-DAT-001"
                  and "$.tools.get_data.output" in i.path]
        assert len(dat001) == 0

    def test_input_schema_still_critical(self, validator):
        """Input schema violation should remain CRITICAL severity."""
        spec = _base_spec(tools={
            "t": {
                "input": {
                    "type": "object",
                    "properties": {"a": {"type": "string", "maxLength": 1}},
                    "additionalProperties": True,
                },
            }
        })
        issues = validator.validate(spec)
        dat001_input = [i for i in issues if i.rule_id == "OMCP-DAT-001"
                        and "input" in i.path]
        assert len(dat001_input) >= 1
        assert all(i.severity == Severity.CRITICAL for i in dat001_input)

    def test_output_schema_medium_severity(self, validator):
        """Output schema violation should be MEDIUM severity (not CRITICAL)."""
        spec = _base_spec(tools={
            "t": {
                "output": {
                    "type": "object",
                    "properties": {"a": {"type": "string", "maxLength": 1}},
                },
                "security": [{"bearer": []}],
            }
        }, components={"securitySchemes": {"bearer": {"type": "http", "scheme": "bearer"}}})

        issues = validator.validate(spec)
        dat001_out = [i for i in issues if i.rule_id == "OMCP-DAT-001"
                      and "$.tools.t.output" in i.path]
        assert len(dat001_out) >= 1
        assert all(i.severity == Severity.MEDIUM for i in dat001_out)

    def test_allof_schema_not_flagged(self, validator):
        """allOf schemas require additionalProperties: true, so DAT-001 should not flag them."""
        spec = _base_spec(tools={
            "t": {
                "output": {
                    "type": "object",
                    "allOf": [
                        {"type": "object", "properties": {"a": {"type": "string", "maxLength": 1}}},
                    ],
                },
                "security": [{"bearer": []}],
            }
        }, components={"securitySchemes": {"bearer": {"type": "http", "scheme": "bearer"}}})

        issues = validator.validate(spec)
        dat001 = [i for i in issues if i.rule_id == "OMCP-DAT-001"
                  and "$.tools.t.output" == i.path]
        assert len(dat001) == 0

    def test_component_schemas_checked(self, validator):
        """Schemas in components.schemas should also be checked."""
        spec = _base_spec(
            tools={
                "t": {
                    "output": {"$ref": "#/components/schemas/Response"},
                    "security": [{"bearer": []}],
                }
            },
            components={
                "schemas": {
                    "Response": {
                        "type": "object",
                        "properties": {"x": {"type": "integer", "minimum": 0, "maximum": 100}},
                        # Missing additionalProperties: false
                    }
                },
                "securitySchemes": {"bearer": {"type": "http", "scheme": "bearer"}},
            },
        )
        issues = validator.validate(spec)
        dat001 = [i for i in issues if i.rule_id == "OMCP-DAT-001"
                  and "$.components.schemas.Response" in i.path]
        assert len(dat001) >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# OMCP-DAT-007: Schema Type Required
# 42Crunch: "Schema does not actually limit what is accepted"
# ═══════════════════════════════════════════════════════════════════════════════


class TestDAT007SchemaType:
    """OMCP-DAT-007 should flag schemas missing a 'type' key."""

    def test_missing_type(self, validator):
        """Schema with no type/ref/combining-ops → flagged."""
        spec = _base_spec(tools={
            "t": {
                "output": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "status": {"title": "Status"},  # No type!
                    },
                },
                "security": [{"bearer": []}],
            }
        }, components={"securitySchemes": {"bearer": {"type": "http", "scheme": "bearer"}}})

        issues = validator.validate(spec)
        dat007 = [i for i in issues if i.rule_id == "OMCP-DAT-007"]
        assert len(dat007) >= 1
        assert any("status" in i.path for i in dat007)

    def test_type_present(self, validator):
        """Schema with type → not flagged."""
        spec = _base_spec(tools={
            "t": {
                "output": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "status": {"type": "string", "maxLength": 50},
                    },
                },
                "security": [{"bearer": []}],
            }
        }, components={"securitySchemes": {"bearer": {"type": "http", "scheme": "bearer"}}})

        issues = validator.validate(spec)
        dat007 = [i for i in issues if i.rule_id == "OMCP-DAT-007"
                  and "status" in i.path]
        assert len(dat007) == 0

    def test_ref_not_flagged(self, validator):
        """Schema with $ref → not flagged (type comes from referenced schema)."""
        spec = _base_spec(tools={
            "t": {
                "output": {"$ref": "#/components/schemas/X"},
                "security": [{"bearer": []}],
            }
        }, components={
            "schemas": {"X": {"type": "object", "properties": {"a": {"type": "string", "maxLength": 1}}, "additionalProperties": False}},
            "securitySchemes": {"bearer": {"type": "http", "scheme": "bearer"}},
        })

        issues = validator.validate(spec)
        dat007 = [i for i in issues if i.rule_id == "OMCP-DAT-007"
                  and "$.tools.t.output" in i.path]
        assert len(dat007) == 0

    def test_anyof_not_flagged(self, validator):
        """Schema with anyOf → not flagged (type comes from combining op)."""
        spec = _base_spec(
            components={
                "schemas": {
                    "X": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "val": {
                                "anyOf": [{"type": "string"}, {"type": "null"}],
                                "additionalProperties": False,
                            }
                        },
                    }
                }
            }
        )
        issues = validator.validate(spec)
        dat007 = [i for i in issues if i.rule_id == "OMCP-DAT-007"
                  and "val" in i.path]
        assert len(dat007) == 0

    def test_empty_tool_input_flagged(self, validator):
        """Empty dict input ({}) has no type → flagged."""
        spec = _base_spec(tools={
            "t": {
                "input": {},
                "security": [{"bearer": []}],
            }
        }, components={"securitySchemes": {"bearer": {"type": "http", "scheme": "bearer"}}})

        issues = validator.validate(spec)
        dat007 = [i for i in issues if i.rule_id == "OMCP-DAT-007"
                  and "input" in i.path]
        assert len(dat007) >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# OMCP-DAT-008: Loose Nullable (anyOf/oneOf primitives)
# 42Crunch: "Schema in a response allows additional properties" (nested)
# ═══════════════════════════════════════════════════════════════════════════════


class TestDAT008LooseNullable:
    """OMCP-DAT-008 should flag primitive anyOf/oneOf without additionalProperties: false."""

    def test_anyof_without_additional_properties(self, validator):
        """anyOf: [string, null] without additionalProperties → flagged."""
        spec = _base_spec(components={
            "schemas": {
                "UserInfo": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "name": {
                            "anyOf": [{"type": "string"}, {"type": "null"}],
                            "title": "Name",
                            # Missing additionalProperties: false
                        },
                    },
                }
            }
        })
        issues = validator.validate(spec)
        dat008 = [i for i in issues if i.rule_id == "OMCP-DAT-008"]
        assert len(dat008) >= 1
        assert any("name" in i.path for i in dat008)

    def test_anyof_with_additional_properties_false(self, validator):
        """anyOf: [string, null] with additionalProperties: false → not flagged."""
        spec = _base_spec(components={
            "schemas": {
                "UserInfo": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "name": {
                            "anyOf": [{"type": "string"}, {"type": "null"}],
                            "additionalProperties": False,
                            "title": "Name",
                        },
                    },
                }
            }
        })
        issues = validator.validate(spec)
        dat008 = [i for i in issues if i.rule_id == "OMCP-DAT-008"
                  and "name" in i.path]
        assert len(dat008) == 0

    def test_oneof_without_additional_properties(self, validator):
        """oneOf: [string, integer] without additionalProperties → flagged."""
        spec = _base_spec(components={
            "schemas": {
                "Flexible": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "val": {
                            "oneOf": [{"type": "string"}, {"type": "integer"}],
                        },
                    },
                }
            }
        })
        issues = validator.validate(spec)
        dat008 = [i for i in issues if i.rule_id == "OMCP-DAT-008"
                  and "val" in i.path]
        assert len(dat008) >= 1

    def test_anyof_with_object_subschema_not_flagged(self, validator):
        """anyOf with object sub-schemas (not primitives) → NOT flagged by DAT-008."""
        spec = _base_spec(components={
            "schemas": {
                "Mixed": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "data": {
                            "anyOf": [
                                {"type": "object", "properties": {"x": {"type": "string", "maxLength": 1}}, "additionalProperties": False},
                                {"type": "null"},
                            ],
                        },
                    },
                }
            }
        })
        issues = validator.validate(spec)
        # The object sub-schema has "properties", so it's not all-primitive
        dat008 = [i for i in issues if i.rule_id == "OMCP-DAT-008"
                  and "data" in i.path]
        assert len(dat008) == 0

    def test_nested_in_array_items(self, validator):
        """anyOf inside array items should also be caught."""
        spec = _base_spec(components={
            "schemas": {
                "Errors": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "loc": {
                            "type": "array",
                            "maxItems": 100,
                            "items": {
                                "anyOf": [{"type": "string"}, {"type": "integer"}],
                                # Missing additionalProperties
                            },
                        },
                    },
                }
            }
        })
        issues = validator.validate(spec)
        dat008 = [i for i in issues if i.rule_id == "OMCP-DAT-008"
                  and "items" in i.path]
        assert len(dat008) >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# $ref handling — should skip, not double-count
# ═══════════════════════════════════════════════════════════════════════════════


class TestRefSkipping:
    """$ref pointers should be skipped to avoid duplicate issues."""

    def test_ref_pointer_skipped(self, validator):
        """A $ref in tool output should not produce DAT-001/DAT-007 on the $ref itself."""
        spec = _base_spec(
            tools={
                "t": {
                    "output": {"$ref": "#/components/schemas/Result"},
                    "security": [{"bearer": []}],
                }
            },
            components={
                "schemas": {
                    "Result": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {"ok": {"type": "boolean"}},
                    }
                },
                "securitySchemes": {"bearer": {"type": "http", "scheme": "bearer"}},
            },
        )
        issues = validator.validate(spec)
        # The output ref itself should not produce issues — only the target schema
        tool_output_issues = [i for i in issues if i.path == "$.tools.t.output"]
        assert len(tool_output_issues) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# Integration: fully hardened spec passes clean on all new rules
# ═══════════════════════════════════════════════════════════════════════════════


class TestHardenedSpecClean:
    """A fully hardened OpenMCP spec should produce zero DAT-001/007/008/009 issues."""

    def test_hardened_spec_no_new_rule_violations(self, validator):
        """Simulate a ProdMCP-hardened spec — all schemas are strict."""
        spec = _base_spec(
            tools={
                "get_data": {
                    "description": "Get user data",
                    "output": {"$ref": "#/components/schemas/GetDataResponse"},
                    "security": [{"bearer": []}],
                    "error_handling": {
                        "401": "Unauthorized — invalid or expired token",
                        "403": "Forbidden — insufficient scopes",
                    },
                }
            },
            components={
                "schemas": {
                    "GetDataResponse": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "user": {"$ref": "#/components/schemas/UserInfo"},
                        },
                        "required": ["user"],
                    },
                    "UserInfo": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "name": {
                                "anyOf": [{"type": "string"}, {"type": "null"}],
                                "additionalProperties": False,
                                "maxLength": 256,
                                "pattern": "^[\\w\\s]+$",
                            },
                            "roles": {
                                "type": "array",
                                "items": {"type": "string", "maxLength": 100, "pattern": "^[\\w]+$"},
                                "maxItems": 50,
                            },
                        },
                    },
                },
                "securitySchemes": {
                    "bearer": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"},
                },
            },
        )
        issues = validator.validate(spec)
        target_rules = ("OMCP-DAT-001", "OMCP-DAT-007", "OMCP-DAT-008", "OMCP-DAT-009", "OMCP-SEC-007")
        new_rule_issues = [i for i in issues if i.rule_id in target_rules]
        assert len(new_rule_issues) == 0, f"Unexpected issues: {[f'{i.rule_id} @ {i.path}: {i.message}' for i in new_rule_issues]}"


# ═══════════════════════════════════════════════════════════════════════════════
# OMCP-DAT-009: String Pattern Required
# 42Crunch: "String schema in a response has no pattern defined"
# ═══════════════════════════════════════════════════════════════════════════════


class TestDAT009StringPattern:
    """OMCP-DAT-009 should flag strings missing 'pattern'."""

    def test_direct_string_missing_pattern(self, validator):
        """Direct string without pattern → flagged."""
        spec = _base_spec(components={
            "schemas": {
                "Info": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "status": {"type": "string", "maxLength": 50},
                    },
                }
            }
        })
        issues = validator.validate(spec)
        dat009 = [i for i in issues if i.rule_id == "OMCP-DAT-009"
                  and "status" in i.path]
        assert len(dat009) >= 1

    def test_direct_string_with_pattern(self, validator):
        """String with pattern → not flagged."""
        spec = _base_spec(components={
            "schemas": {
                "Info": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "status": {"type": "string", "maxLength": 50, "pattern": "^[a-z]+$"},
                    },
                }
            }
        })
        issues = validator.validate(spec)
        dat009 = [i for i in issues if i.rule_id == "OMCP-DAT-009"
                  and "status" in i.path]
        assert len(dat009) == 0

    def test_nullable_string_missing_pattern(self, validator):
        """anyOf: [string, null] without pattern → flagged."""
        spec = _base_spec(components={
            "schemas": {
                "User": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "name": {
                            "anyOf": [{"type": "string"}, {"type": "null"}],
                            "additionalProperties": False,
                            "maxLength": 256,
                            # Missing pattern
                        },
                    },
                }
            }
        })
        issues = validator.validate(spec)
        dat009 = [i for i in issues if i.rule_id == "OMCP-DAT-009"
                  and "name" in i.path]
        assert len(dat009) >= 1

    def test_nullable_string_with_pattern(self, validator):
        """anyOf: [string, null] with pattern at property level → not flagged."""
        spec = _base_spec(components={
            "schemas": {
                "User": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "name": {
                            "anyOf": [{"type": "string"}, {"type": "null"}],
                            "additionalProperties": False,
                            "maxLength": 256,
                            "pattern": "^[\\w\\s]+$",
                        },
                    },
                }
            }
        })
        issues = validator.validate(spec)
        dat009 = [i for i in issues if i.rule_id == "OMCP-DAT-009"
                  and "name" in i.path]
        assert len(dat009) == 0

    def test_array_items_string_missing_pattern(self, validator):
        """Array items string without pattern → flagged."""
        spec = _base_spec(components={
            "schemas": {
                "Data": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "tags": {
                            "type": "array",
                            "maxItems": 20,
                            "items": {"type": "string", "maxLength": 50},
                        },
                    },
                }
            }
        })
        issues = validator.validate(spec)
        dat009 = [i for i in issues if i.rule_id == "OMCP-DAT-009"
                  and "items" in i.path]
        assert len(dat009) >= 1

    def test_count_matches_42crunch(self, validator):
        """An unhardened spec with 9 bare strings should produce 9 DAT-009 issues,
        matching 42Crunch's 9 'String no pattern' findings."""
        spec = _base_spec(components={
            "schemas": {
                "AzureADUserInfo": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "oid": {"anyOf": [{"type": "string"}, {"type": "null"}], "additionalProperties": False, "maxLength": 36},
                        "tid": {"anyOf": [{"type": "string"}, {"type": "null"}], "additionalProperties": False, "maxLength": 36},
                        "preferred_username": {"anyOf": [{"type": "string"}, {"type": "null"}], "additionalProperties": False, "maxLength": 256},
                        "name": {"anyOf": [{"type": "string"}, {"type": "null"}], "additionalProperties": False, "maxLength": 256},
                        "aud": {"anyOf": [{"type": "string"}, {"type": "null"}], "additionalProperties": False, "maxLength": 512},
                        "scp": {"anyOf": [{"type": "string"}, {"type": "null"}], "additionalProperties": False, "maxLength": 1024},
                        "roles": {"type": "array", "maxItems": 50, "items": {"type": "string", "maxLength": 128}},
                    },
                },
                "AzureADOboTokenResponse": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "token_type": {"anyOf": [{"type": "string"}, {"type": "null"}], "additionalProperties": False, "maxLength": 20},
                        "scope": {"anyOf": [{"type": "string"}, {"type": "null"}], "additionalProperties": False, "maxLength": 1024},
                    },
                },
            }
        })
        issues = validator.validate(spec)
        dat009 = [i for i in issues if i.rule_id == "OMCP-DAT-009"]
        # 6 nullable strings in UserInfo + 1 array items string + 2 nullable in OboToken = 9
        assert len(dat009) == 9, f"Expected 9, got {len(dat009)}: {[i.path for i in dat009]}"


# ═══════════════════════════════════════════════════════════════════════════════
# OMCP-SEC-007: Auth Error Handling
# 42Crunch: "Missing 401/403 responses on secured operation"
# ═══════════════════════════════════════════════════════════════════════════════


class TestSEC007AuthErrorHandling:
    """OMCP-SEC-007 should flag secured tools missing error_handling."""

    def test_secured_tool_no_error_handling(self, validator):
        """Tool with security but no error_handling → flagged."""
        spec = _base_spec(
            tools={
                "get_data": {
                    "description": "Get data",
                    "security": [{"bearer": []}],
                }
            },
            components={"securitySchemes": {"bearer": {"type": "http", "scheme": "bearer"}}},
        )
        issues = validator.validate(spec)
        sec007 = [i for i in issues if i.rule_id == "OMCP-SEC-007"]
        assert len(sec007) >= 1
        assert any("get_data" in i.path for i in sec007)

    def test_secured_tool_with_error_handling(self, validator):
        """Tool with security AND error_handling → not flagged."""
        spec = _base_spec(
            tools={
                "get_data": {
                    "description": "Get data",
                    "security": [{"bearer": []}],
                    "error_handling": {
                        "401": "Invalid credentials",
                        "403": "Insufficient permissions",
                    },
                }
            },
            components={"securitySchemes": {"bearer": {"type": "http", "scheme": "bearer"}}},
        )
        issues = validator.validate(spec)
        sec007 = [i for i in issues if i.rule_id == "OMCP-SEC-007"]
        assert len(sec007) == 0

    def test_unsecured_tool_not_flagged(self, validator):
        """Tool without security → SEC-007 not triggered (SEC-003 handles that)."""
        spec = _base_spec(tools={
            "public_tool": {
                "description": "A public tool",
            }
        })
        issues = validator.validate(spec)
        sec007 = [i for i in issues if i.rule_id == "OMCP-SEC-007"]
        assert len(sec007) == 0

    def test_severity_is_medium(self, validator):
        """SEC-007 should be MEDIUM severity (matches 42Crunch 401/403 finding)."""
        spec = _base_spec(
            tools={
                "t": {
                    "security": [{"bearer": []}],
                }
            },
            components={"securitySchemes": {"bearer": {"type": "http", "scheme": "bearer"}}},
        )
        issues = validator.validate(spec)
        sec007 = [i for i in issues if i.rule_id == "OMCP-SEC-007"]
        assert len(sec007) >= 1
        assert all(i.severity == Severity.MEDIUM for i in sec007)

