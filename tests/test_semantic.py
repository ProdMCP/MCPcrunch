import pytest
from mcpcrunch.validators.semantic import SemanticValidator
from mcpcrunch.llm.base import LLMBase
from mcpcrunch.models import Severity

class MockLLM(LLMBase):
    def __init__(self, mock_response=None):
        self.mock_response = mock_response or []

    def analyze(self, prompt: str) -> str:
        return "Mock analysis"

    def analyze_json(self, prompt: str, schema=None) -> list:
        return self.mock_response

def test_semantic_validator_parsing():
    mock_data = [
        {
            "rule_id": "OMCP-ADV-001",
            "path": "$.tools.get_user",
            "message": "Potential injection found.",
            "severity": "Critical"
        }
    ]
    llm = MockLLM(mock_response=mock_data)
    validator = SemanticValidator(llm)
    
    spec = {"tools": {"get_user": {"description": "dangerous description"}}}
    issues = validator.validate(spec)
    
    assert len(issues) == 1
    assert issues[0].rule_id == "OMCP-ADV-001"
    assert issues[0].severity == Severity.CRITICAL

def test_semantic_validator_error_handling():
    class ErrorLLM(MockLLM):
        def analyze_json(self, prompt, schema=None):
            raise Exception("LLM Error")
            
    llm = ErrorLLM()
    validator = SemanticValidator(llm)
    issues = validator.validate({})
    assert len(issues) == 0 # Should handle exception gracefully
