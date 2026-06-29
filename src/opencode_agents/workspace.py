from __future__ import annotations

import json
from pathlib import Path
from opencode_agents.models import Task, Session


class Workspace:
    def __init__(self, root: str | Path = "."):
        self.root = Path(root)
        self.tasks_dir = self.root / "tasks"
        self.sessions_dir = self.root / "workflow" / "sessions"
        self._ensure_dirs()

    def _ensure_dirs(self):
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def create_task(self, description: str) -> Task:
        task = Task(description=description)
        self._write_json(self.tasks_dir / f"{task.task_id}.json", task.to_dict())
        return task

    def read_task(self, task_id: str) -> Task | None:
        path = self.tasks_dir / f"{task_id}.json"
        if not path.exists():
            return None
        return Task.from_dict(self._read_json(path))

    def list_tasks(self) -> list[Task]:
        tasks = []
        for path in sorted(self.tasks_dir.glob("task-*.json")):
            tasks.append(Task.from_dict(self._read_json(path)))
        return tasks

    def create_session(self, task: Task) -> Session:
        session = Session(task_id=task.task_id, task_description=task.description)
        self._write_session(session)
        return session

    def read_session(self, task_id: str) -> Session | None:
        path = self.sessions_dir / f"{task_id}.json"
        if not path.exists():
            return None
        return Session.from_dict(self._read_json(path))

    def update_session(self, session: Session):
        self._write_session(session)

    def _write_session(self, session: Session):
        self._write_json(self.sessions_dir / f"{session.task_id}.json", session.to_dict())

    @staticmethod
    def _write_json(path: Path, data: dict):
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def _read_json(path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))
