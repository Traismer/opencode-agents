from __future__ import annotations

import os


class BaseLLM:
    def generate(self, prompt: str, **kwargs) -> str:
        raise NotImplementedError


class StubLLM(BaseLLM):
    def generate(self, prompt: str, **kwargs) -> str:
        return (
            "APPROVED — Plan looks good, follows best practices, "
            "covers all necessary aspects."
        )


class DeepSeekLLM(BaseLLM):
    def __init__(self, api_key: str | None = None, model: str = "deepseek-chat"):
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY", "")
        self.model = model
        self.base_url = "https://api.deepseek.com/v1"

    def generate(self, prompt: str, **kwargs) -> str:
        import httpx

        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                **kwargs,
            },
            timeout=120,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
