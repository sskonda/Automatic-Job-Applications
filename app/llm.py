from __future__ import annotations

from app.config import Settings


class LLMClient:
    def __init__(self, config: Settings) -> None:
        self.config = config

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        if not self.config.openai_api_key:
            return ""
        from openai import OpenAI

        client = OpenAI(api_key=self.config.openai_api_key)
        response = client.responses.create(
            model=self.config.openai_model,
            instructions=system_prompt,
            input=user_prompt,
        )
        return response.output_text.strip()
