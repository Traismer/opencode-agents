from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone


@dataclass
class Task:
    task_id: str = field(default_factory=lambda: f"task-{uuid.uuid4().hex[:8]}")
    description: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        return cls(**d)


@dataclass
class HistoryEntry:
    role: str
    content: str
    iteration: int

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        return cls(**d)


@dataclass
class Session:
    task_id: str
    task_description: str
    status: str = "planner_turn"
    iteration: int = 0
    plan: str = ""
    history: list = field(default_factory=list)
    max_iterations: int = 5

    def to_dict(self):
        return {
            "task_id": self.task_id,
            "task_description": self.task_description,
            "status": self.status,
            "iteration": self.iteration,
            "plan": self.plan,
            "history": [h.to_dict() if hasattr(h, 'to_dict') else h for h in self.history],
            "max_iterations": self.max_iterations,
        }

    @classmethod
    def from_dict(cls, d):
        s = cls(
            task_id=d["task_id"],
            task_description=d["task_description"],
            status=d.get("status", "planner_turn"),
            iteration=d.get("iteration", 0),
            plan=d.get("plan", ""),
            max_iterations=d.get("max_iterations", 5),
        )
        s.history = [HistoryEntry.from_dict(h) for h in d.get("history", [])]
        return s
