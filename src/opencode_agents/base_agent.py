from __future__ import annotations

from abc import ABC, abstractmethod
from opencode_agents.llm import BaseLLM, StubLLM
from opencode_agents.models import Session


class BaseAgent(ABC):
    role: str = ""

    def __init__(self, llm: BaseLLM | None = None):
        self.llm = llm or StubLLM()

    @abstractmethod
    def process(self, session: Session, **kwargs) -> dict:
        ...
