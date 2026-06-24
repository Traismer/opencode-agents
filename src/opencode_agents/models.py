from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone


@dataclass
class Task:
    id: str = field(default_factory=lambda: f"task-{uuid.uuid4().hex[:8]}")
    description: str = ""
    language: str = "python"
    requirements: list[str] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        return cls(**d)


@dataclass
class Subtask:
    id: str = field(default_factory=lambda: f"sub-{uuid.uuid4().hex[:8]}")
    task_id: str = ""
    role: str = ""
    instruction: str = ""
    context: dict = field(default_factory=dict)
    status: str = "pending"
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        return cls(**d)


@dataclass
class Result:
    subtask_id: str = ""
    task_id: str = ""
    role: str = ""
    status: str = "done"
    output: str = ""
    files: list[dict] = field(default_factory=list)
    error: str | None = None
    completed_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self):
        d = asdict(self)
        if self.error is None:
            del d["error"]
        return d

    @classmethod
    def from_dict(cls, d):
        return cls(**d)
