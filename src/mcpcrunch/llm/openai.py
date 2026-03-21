import os
import json
from typing import Optional
from openai import OpenAI
from .base import LLMBase

class OpenAIProvider(LLMBase):
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gpt-4-turbo-preview"):
        super().__init__(api_key or os.getenv("OPENAI_API_KEY"))
        if not self.api_key:
            raise ValueError("OpenAI API key is required.")
        self.client = OpenAI(api_key=self.api_key)
        self.model_name = model_name

    def analyze(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

    def analyze_json(self, prompt: str, schema: Optional[dict] = None) -> dict:
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
