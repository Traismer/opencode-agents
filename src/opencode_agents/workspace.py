from __future__ import annotations

import json
import time
from pathlib import Path


class Workspace:
    def __init__(self, root: str | Path = "."):
        self.root = Path(root)
        self._dirs = {
            "inbox": self.root / "workflow" / "inbox",
            "in_progress": self.root / "workflow" / "in_progress",
            "done": self.root / "workflow" / "done",
            "results": self.root / "workflow" / "results",
            "state": self.root / "workflow" / "state",
        }
        for d in self._dirs.values():
            d.mkdir(parents=True, exist_ok=True)
        (self.root / "tasks").mkdir(parents=True, exist_ok=True)

    def put_task(self, task: dict) -> Path:
        path = self.root / "tasks" / f"{task['id']}.json"
        path.write_text(json.dumps(task, indent=2))
        return path

    def get_task(self, task_id: str) -> dict | None:
        path = self.root / "tasks" / f"{task_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def put_subtask(self, subtask: dict) -> Path:
        role_dir = self._dirs["inbox"] / subtask["role"]
        role_dir.mkdir(parents=True, exist_ok=True)
        path = role_dir / f"{subtask['id']}.json"
        path.write_text(json.dumps(subtask, indent=2))
        return path

    def take_subtask(self, role: str) -> tuple[dict, str | None]:
        role_dir = self._dirs["inbox"] / role
        if not role_dir.exists():
            return None, None
        items = list(role_dir.iterdir())
        if not items:
            return None, None
        path = items[0]
        data = json.loads(path.read_text())

        dest = self._dirs["in_progress"] / role
        dest.mkdir(parents=True, exist_ok=True)
        path.rename(dest / path.name)
        return data, data["id"]

    def put_result(self, result: dict) -> Path:
        path = self._dirs["done"] / f"{result['subtask_id']}.json"
        path.write_text(json.dumps(result, indent=2))
        return path

    def get_results(self, task_id: str | None = None, role: str | None = None) -> list[dict]:
        results = []
        for p in self._dirs["done"].iterdir():
            if p.suffix != ".json":
                continue
            data = json.loads(p.read_text())
            if task_id and data.get("task_id") != task_id:
                continue
            if role and data.get("role") != role:
                continue
            results.append(data)
        return results

    def get_state(self, task_id: str) -> dict | None:
        path = self._dirs["state"] / f"{task_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def put_state(self, task_id: str, state: dict):
        path = self._dirs["state"] / f"{task_id}.json"
        path.write_text(json.dumps(state, indent=2))

    def write_final_artifact(self, task_id: str, artifact: dict):
        path = self._dirs["results"] / f"{task_id}.json"
        path.write_text(json.dumps(artifact, indent=2))
        return path

    def list_tasks(self) -> list[dict]:
        tasks = []
        for p in (self.root / "tasks").iterdir():
            if p.suffix == ".json":
                tasks.append(json.loads(p.read_text()))
        return tasks

    def wait_for_results(self, task_id: str, count: int, poll: float = 0.5) -> list[dict]:
        while True:
            results = self.get_results(task_id=task_id)
            if len(results) >= count:
                return results
            time.sleep(poll)
