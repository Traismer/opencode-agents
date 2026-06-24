from __future__ import annotations

from opencode_agents.base_agent import BaseAgent
from opencode_agents.llm import StubLLM


class ReviewerAgent(BaseAgent):
    role = "reviewer"

    def __init__(self, workspace, llm=None):
        super().__init__(workspace)
        self.llm = llm or StubLLM()

    def process(self, subtask: dict) -> dict:
        code_blocks = subtask.get("context", {}).get("code", [])
        language = subtask.get("context", {}).get("language", "python")

        code_text = "\n\n".join(code_blocks)
        prompt = f"Language: {language}\nInstruction: {subtask.get('instruction', 'Review')}\n\nCode to review:\n{code_text}\n\nProvide review feedback."
        review = self.llm.generate(prompt)

        return {
            "task_id": subtask["task_id"],
            "status": "done",
            "output": review,
            "files": [],
        }
