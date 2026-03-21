from abc import ABC, abstractmethod
from typing import Optional

class LLMBase(ABC):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    @abstractmethod
    def analyze(self, prompt: str) -> str:
        """Analyze text and return response."""
        return ""

    @abstractmethod
    def analyze_json(self, prompt: str, schema: Optional[dict] = None) -> dict:
        """Analyze text and return structured JSON response."""
        return {}
