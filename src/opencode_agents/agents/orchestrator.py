from __future__ import annotations

from opencode_agents.workspace import Workspace


class OrchestratorAgent:
    def __init__(self, workspace: Workspace):
        self.ws = workspace

    def process_task(self, task_id: str):
        task = self.ws.get_task(task_id)
        if task is None:
            print(f"  [orchestrator] task {task_id} not found")
            return

        state = self.ws.get_state(task_id)
        if state is None:
            state = {"phase": "init"}
            self.ws.put_state(task_id, state)

        if state["phase"] == "init":
            self._decompose(task, state)
            self.ws.put_state(task_id, state)
        elif state["phase"] == "collect":
            self._collect(task, state)
            self.ws.put_state(task_id, state)
        elif state["phase"] == "review":
            self._finalize(task, state)
            self.ws.put_state(task_id, state)
        else:
            print(f"  [orchestrator] task {task_id} already done")

    def _decompose(self, task: dict, state: dict):
        print(f"  [orchestrator] decomposing task {task['id']}")
        sub_ids = []
        for req in task.get("requirements", []):
            sub = {
                "id": f"sub-{task['id']}-{req[:16].lower().replace(' ', '_')}",
                "task_id": task["id"],
                "role": "coder",
                "instruction": f"Implement: {req}",
                "context": {"language": task.get("language", "python")},
                "status": "pending",
            }
            self.ws.put_subtask(sub)
            sub_ids.append(sub["id"])

        state["phase"] = "collect"
        state["subtask_ids"] = sub_ids
        state["requirement_count"] = len(task.get("requirements", []))
        print(f"  [orchestrator] created {len(sub_ids)} coding subtasks")

    def _collect(self, task: dict, state: dict):
        results = self.ws.get_results(task_id=task["id"], role="coder")
        needed = state.get("requirement_count", 0)
        print(f"  [orchestrator] collected {len(results)}/{needed} coding results")

        if len(results) >= needed:
            code_summary = "\n\n".join(
                f"=== {r['output'][:100]} ===" for r in results
            )
            review_sub = {
                "id": f"review-{task['id']}",
                "task_id": task["id"],
                "role": "reviewer",
                "instruction": "Review the generated code and suggest improvements",
                "context": {
                    "code": [r.get("output", "") for r in results],
                    "language": task.get("language", "python"),
                },
                "status": "pending",
            }
            self.ws.put_subtask(review_sub)
            state["phase"] = "review"
            state["review_subtask_id"] = review_sub["id"]
            print(f"  [orchestrator] all code done, created review subtask")

    def _finalize(self, task: dict, state: dict):
        reviews = self.ws.get_results(task_id=task["id"], role="reviewer")
        if not reviews:
            print(f"  [orchestrator] waiting for review...")
            return

        codings = self.ws.get_results(task_id=task["id"], role="coder")
        artifact = {
            "task_id": task["id"],
            "description": task.get("description", ""),
            "language": task.get("language", "python"),
            "files": [],
            "review": reviews[0].get("output", ""),
        }
        for r in codings:
            for f in r.get("files", []):
                artifact["files"].append(f)

        self.ws.write_final_artifact(task["id"], artifact)
        state["phase"] = "done"
        print(f"  [orchestrator] final artifact written with {len(artifact['files'])} files")
