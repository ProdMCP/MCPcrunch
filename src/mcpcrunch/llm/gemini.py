import os
import json
from typing import Optional
import google.generativeai as genai
from .base import LLMBase

class GeminiProvider(LLMBase):
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-3-flash-preview"):
        super().__init__(api_key or os.getenv("GEMINI_API_KEY"))
        if not self.api_key:
            raise ValueError("Gemini API key is required.")
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(model_name)

    def analyze(self, prompt: str) -> str:
        response = self.model.generate_content(prompt)
        return response.text

    def analyze_json(self, prompt: str, schema: Optional[dict] = None) -> dict:
        # For simplicity, we use the standard generate_content and parse JSON
        # Better implementations would use response_mime_type="application/json"
        config = genai.GenerationConfig(response_mime_type="application/json")
        response = self.model.generate_content(prompt, generation_config=config)
        return json.loads(response.text)
