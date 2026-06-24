from __future__ import annotations

from opencode_agents.base_agent import BaseAgent
from opencode_agents.llm import StubLLM


class CoderAgent(BaseAgent):
    role = "coder"

    def __init__(self, workspace, llm=None):
        super().__init__(workspace)
        self.llm = llm or StubLLM()

    def process(self, subtask: dict) -> dict:
        instruction = subtask.get("instruction", "Implement")
        language = subtask.get("context", {}).get("language", "python")

        prompt = f"Language: {language}\nInstruction: {instruction}\nWrite production-quality code."
        code = self.llm.generate(prompt)

        ext = {"python": "py", "javascript": "js", "typescript": "ts", "go": "go", "rust": "rs", "ruby": "rb"}.get(language, language[:4])
        filename = instruction.lower().replace("implement:", "").strip().replace(" ", "_") + f".{ext}"

        return {
            "task_id": subtask["task_id"],
            "status": "done",
            "output": code,
            "files": [{"path": filename, "content": code}],
        }
