from __future__ import annotations

import time
from opencode_agents.workspace import Workspace


class BaseAgent:
    role: str = "base"

    def __init__(self, workspace: Workspace):
        self.ws = workspace

    def run_once(self) -> bool:
        subtask, sub_id = self.ws.take_subtask(self.role)
        if subtask is None:
            return False
        result = self.process(subtask)
        result["role"] = self.role
        result["subtask_id"] = sub_id
        self.ws.put_result(result)
        print(f"  [{self.role}] completed {sub_id}: {subtask.get('instruction', '')[:50]}")
        return True

    def run_loop(self, interval: float = 0.5):
        print(f"[{self.role}] watching for subtasks...")
        while True:
            self.run_once()
            time.sleep(interval)

    def process(self, subtask: dict) -> dict:
        raise NotImplementedError
