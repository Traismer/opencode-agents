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


class OpenAICompatibleLLM(BaseLLM):
    def __init__(self, api_key: str, model: str = "deepseek-chat", base_url: str = "https://api.deepseek.com/v1"):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")

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


class DeepSeekLLM(OpenAICompatibleLLM):
    def __init__(self, api_key: str | None = None, model: str = "deepseek-chat"):
        super().__init__(
            api_key=api_key or os.environ.get("DEEPSEEK_API_KEY", ""),
            model=model,
            base_url="https://api.deepseek.com/v1",
        )


FREE_API_BASE_URL = "https://aiapiv2.pekpik.com/v1"
FREE_API_MODEL = "deepseek/deepseek-v4-flash"


class FreeLLM(OpenAICompatibleLLM):
    def __init__(self, api_key: str | None = None, model: str | None = None, base_url: str | None = None):
        super().__init__(
            api_key=api_key or os.environ.get("FREE_API_KEY", ""),
            model=model or os.environ.get("FREE_API_MODEL", FREE_API_MODEL),
            base_url=base_url or os.environ.get("FREE_API_BASE_URL", FREE_API_BASE_URL),
        )
