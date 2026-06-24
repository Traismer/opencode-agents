from __future__ import annotations

import sys
import json
import time
from pathlib import Path

from opencode_agents.workspace import Workspace
from opencode_agents.models import Task
from opencode_agents.agents.orchestrator import OrchestratorAgent
from opencode_agents.agents.coder import CoderAgent
from opencode_agents.agents.reviewer import ReviewerAgent


def cmd_create_task(ws: Workspace, args: list[str]):
    if not args:
        print("Usage: python -m opencode_agents task <description> [--reqs 'r1' 'r2']")
        return
    desc = args[0]
    reqs = []
    if "--reqs" in args:
        idx = args.index("--reqs")
        reqs = args[idx + 1:]
    task = Task(description=desc, requirements=reqs or [desc])
    ws.put_task(task.to_dict())
    print(f"Created task: {task.id}")
    print(f"  description: {desc}")
    print(f"  requirements: {reqs or [desc]}")
    print(f"  file: tasks/{task.id}.json")


def cmd_orchestrate(ws: Workspace, args: list[str]):
    if not args:
        print("Usage: python -m opencode_agents orchestrate <task_id>")
        return
    agent = OrchestratorAgent(ws)
    agent.process_task(args[0])


def cmd_run_coder(ws: Workspace, args: list[str]):
    agent = CoderAgent(ws)
    agent.run_loop()


def cmd_run_reviewer(ws: Workspace, args: list[str]):
    agent = ReviewerAgent(ws)
    agent.run_loop()


def cmd_list(ws: Workspace, args: list[str]):
    tasks = ws.list_tasks()
    if not tasks:
        print("No tasks found.")
        return
    print("Tasks:")
    for t in tasks:
        state = ws.get_state(t["id"])
        phase = state["phase"] if state else "—"
        print(f"  {t['id']}: {t['description'][:50]} [{phase}]")


def cmd_status(ws: Workspace, args: list[str]):
    if not args:
        print("Usage: python -m opencode_agents status <task_id>")
        return
    task = ws.get_task(args[0])
    if not task:
        print("Task not found")
        return
    state = ws.get_state(args[0])
    codings = ws.get_results(task_id=args[0], role="coder")
    reviews = ws.get_results(task_id=args[0], role="reviewer")

    print(f"Task: {task['id']}")
    print(f"  description: {task.get('description', '')}")
    print(f"  phase: {state['phase'] if state else 'init'}")
    print(f"  coding results: {len(codings)}/{len(task.get('requirements', []))}")
    print(f"  review results: {len(reviews)}")


def cmd_demo(ws: Workspace, args: list[str]):
    task = Task(
        description="Build a simple CLI calculator",
        requirements=["add function", "subtract function", "main entry point"],
        language="python",
    )
    ws.put_task(task.to_dict())
    print(f"Demo task created: {task.id}")
    print()

    orchestrator = OrchestratorAgent(ws)

    print("\n=== Phase 1: decompose ===")
    orchestrator.process_task(task.id)
    print("  inbox/coder/ now has subtasks\n")

    time.sleep(0.2)

    print("=== Phase 2: run coder agent ===")
    coder = CoderAgent(ws)
    while coder.run_once():
        pass

    print("\n=== Phase 3: orchestrator collects ===")
    orchestrator.process_task(task.id)

    print("\n=== Phase 4: run reviewer agent ===")
    reviewer = ReviewerAgent(ws)
    reviewer.run_once()

    print("\n=== Phase 5: orchestrator finalizes ===")
    orchestrator.process_task(task.id)

    print(f"\n✅ Done! Check workflow/results/{task.id}.json")


def help_text():
    print("Usage: python -m opencode_agents <command> [args]")
    print()
    print("Commands:")
    print("  task <desc> --reqs r1 r2    Create a new task")
    print("  list                         List all tasks")
    print("  status <task_id>            Show task status")
    print("  orchestrate <task_id>       Run one orchestrator cycle")
    print("  run-coder                   Run coder agent (loop)")
    print("  run-reviewer                Run reviewer agent (loop)")
    print("  demo                        Run a full demo pipeline")


COMMANDS = {
    "task": cmd_create_task,
    "list": cmd_list,
    "status": cmd_status,
    "orchestrate": cmd_orchestrate,
    "run-coder": cmd_run_coder,
    "run-reviewer": cmd_run_reviewer,
    "demo": cmd_demo,
}


def main():
    ws = Workspace()
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        help_text()
        return

    cmd = sys.argv[1]
    args = sys.argv[2:]
    if cmd in COMMANDS:
        COMMANDS[cmd](ws, args)
    else:
        print(f"Unknown command: {cmd}")
        help_text()


if __name__ == "__main__":
    main()
