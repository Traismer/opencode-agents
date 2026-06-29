from __future__ import annotations

import sys
import time
import os

from opencode_agents.workspace import Workspace
from opencode_agents.models import HistoryEntry
from opencode_agents.agents.planner import PlannerAgent
from opencode_agents.agents.critic import CriticAgent
from opencode_agents.llm import DeepSeekLLM, StubLLM


def _resolve_llm():
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if api_key:
        return DeepSeekLLM(api_key=api_key)
    return StubLLM()


def cmd_create_task(ws: Workspace, args: list[str]):
    if not args:
        print("Использование: python -m opencode_agents task <описание>")
        return
    desc = " ".join(args)
    task = ws.create_task(desc)
    session = ws.create_session(task)
    print(f"Создана задача: {task.task_id}")
    print(f"  описание: {desc}")
    print(f"  статус: {session.status}")
    print(f"  файл: tasks/{task.task_id}.json")


def cmd_list(ws: Workspace, args: list[str]):
    tasks = ws.list_tasks()
    if not tasks:
        print("Нет задач.")
        return
    print("Задачи:")
    for t in tasks:
        session = ws.read_session(t.task_id)
        status = session.status if session else "нет сессии"
        print(f"  {t.task_id}: {t.description[:60]} [{status}]")


def cmd_status(ws: Workspace, args: list[str]):
    if not args:
        print("Использование: python -m opencode_agents status <task_id>")
        return
    session = ws.read_session(args[0])
    if not session:
        print("Сессия не найдена")
        return
    print(f"Задача: {session.task_id}")
    print(f"  описание: {session.task_description}")
    print(f"  статус: {session.status}")
    print(f"  итерация: {session.iteration}/{session.max_iterations}")
    print(f"  записей в истории: {len(session.history)}")
    if session.plan:
        preview = session.plan[:300].replace("\n", "\n  ")
        print(f"  план (начало):")
        print(f"    {preview}...")
        print(f"  (полный план: {len(session.plan)} символов)")


def cmd_advance(ws: Workspace, args: list[str]):
    if not args:
        print("Использование: python -m opencode_agents advance <task_id>")
        return
    task_id = args[0]
    session = ws.read_session(task_id)
    if not session:
        print(f"Сессия не найдена для {task_id}")
        return

    if session.status == "approved":
        print(f"  [{task_id}] уже одобрено")
        return
    if session.status == "max_iterations":
        print(f"  [{task_id}] достигнут лимит итераций ({session.max_iterations})")
        return

    llm = _resolve_llm()

    if session.status == "planner_turn":
        agent = PlannerAgent(llm=llm)
        result = agent.process(session)
        plan = result.get("plan", result["content"])
        session.plan = plan
        session.history.append(HistoryEntry(
            role="planner", content=result["content"], iteration=session.iteration
        ))
        session.status = "critic_turn"
        ws.update_session(session)
        print(f"  [planner] итер {session.iteration} — план обновлён ({len(plan)} симв.)")

    elif session.status == "critic_turn":
        agent = CriticAgent(llm=llm)
        result = agent.process(session)
        session.history.append(HistoryEntry(
            role="critic", content=result["content"], iteration=session.iteration
        ))
        if result.get("approved"):
            session.status = "approved"
            ws.update_session(session)
            print(f"  [critic] итер {session.iteration} — ОДОБРЕНО")
        elif session.iteration >= session.max_iterations - 1:
            session.status = "max_iterations"
            ws.update_session(session)
            print(f"  [critic] итер {session.iteration} — лимит итераций")
        else:
            session.iteration += 1
            session.status = "planner_turn"
            ws.update_session(session)
            print(f"  [critic] итер {session.iteration - 1} — замечания")


def cmd_run_planner(ws: Workspace, args: list[str]):
    llm = _resolve_llm()
    agent = PlannerAgent(llm=llm)
    print("[planner] ожидание задач...")
    while True:
        for t in ws.list_tasks():
            session = ws.read_session(t.task_id)
            if session and session.status == "planner_turn":
                result = agent.process(session)
                session.plan = result.get("plan", result["content"])
                session.history.append(HistoryEntry(
                    role="planner", content=result["content"], iteration=session.iteration
                ))
                session.status = "critic_turn"
                ws.update_session(session)
                print(f"  [planner] {t.task_id} итер {session.iteration} — готово")
        time.sleep(2)


def cmd_run_critic(ws: Workspace, args: list[str]):
    llm = _resolve_llm()
    agent = CriticAgent(llm=llm)
    print("[critic] ожидание задач...")
    while True:
        for t in ws.list_tasks():
            session = ws.read_session(t.task_id)
            if session and session.status == "critic_turn":
                result = agent.process(session)
                session.history.append(HistoryEntry(
                    role="critic", content=result["content"], iteration=session.iteration
                ))
                if result.get("approved"):
                    session.status = "approved"
                    ws.update_session(session)
                    print(f"  [critic] {t.task_id} итер {session.iteration} — ОДОБРЕНО")
                elif session.iteration >= session.max_iterations - 1:
                    session.status = "max_iterations"
                    ws.update_session(session)
                    print(f"  [critic] {t.task_id} итер {session.iteration} — лимит итераций")
                else:
                    session.iteration += 1
                    session.status = "planner_turn"
                    ws.update_session(session)
                    print(f"  [critic] {t.task_id} итер {session.iteration - 1} — замечания")
        time.sleep(2)


def help_text():
    print("Использование: python -m opencode_agents <команда> [args]")
    print()
    print("Команды:")
    print("  task <описание>              Создать новую задачу с сессией")
    print("  list                         Список задач")
    print("  status <task_id>             Статус сессии")
    print("  advance <task_id>            Один шаг (planner или critic)")
    print("  run-planner                  Демон planner (цикл)")
    print("  run-critic                   Демон critic (цикл)")
    print()
    print("Переменные окружения:")
    print("  DEEPSEEK_API_KEY             API-ключ DeepSeek (без него — StubLLM)")


COMMANDS = {
    "task": cmd_create_task,
    "list": cmd_list,
    "status": cmd_status,
    "advance": cmd_advance,
    "run-planner": cmd_run_planner,
    "run-critic": cmd_run_critic,
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
        print(f"Неизвестная команда: {cmd}")
        help_text()


if __name__ == "__main__":
    main()
