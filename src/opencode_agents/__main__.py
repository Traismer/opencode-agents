from __future__ import annotations

import sys
import time
import os

import httpx
import re
from pathlib import Path

from opencode_agents.workspace import Workspace
from opencode_agents.models import HistoryEntry
from opencode_agents.agents.planner import PlannerAgent
from opencode_agents.agents.critic import CriticAgent
from opencode_agents.llm import DeepSeekLLM, FreeLLM, StubLLM, FREE_API_MODEL


def _resolve_llm():
    if os.environ.get("FREE_API_KEY"):
        return FreeLLM()
    if os.environ.get("DEEPSEEK_API_KEY"):
        return DeepSeekLLM()
    return StubLLM()


def _refresh_free_key():
    model = os.environ.get("FREE_API_MODEL", FREE_API_MODEL)
    print(f"  [free] ключ умер, ищу свежий для {model}...")
    try:
        resp = httpx.get(
            "https://raw.githubusercontent.com/alistaitsacle/free-llm-api-keys/main/README.md",
            timeout=30,
        )
        resp.raise_for_status()
    except Exception as e:
        print(f"  [free] ошибка загрузки ключей: {e}")
        return False

    sections = re.split(r'\n(?=###\s)', resp.text)
    for sec in sections:
        rows = re.findall(r'\|\s*`(sk-\w+)`\s*\|\s*(\S+?)\s*\|', sec)
        for key, m in rows:
            if m == model:
                os.environ["FREE_API_KEY"] = key
                env_path = Path(".env")
                if env_path.exists():
                    text = env_path.read_text()
                    if "FREE_API_KEY=" in text:
                        text = re.sub(r'^FREE_API_KEY=.*', f'FREE_API_KEY={key}', text, flags=re.MULTILINE)
                    else:
                        text += f'\nFREE_API_KEY={key}\n'
                    env_path.write_text(text)
                print(f"  [free] новый ключ: {key[:20]}...")
                return True

    print(f"  [free] не нашёл ключ для {model}, пробую fetch-keys")
    return False


def _is_auth_error(e: Exception) -> bool:
    if isinstance(e, httpx.HTTPStatusError):
        return e.response.status_code in (401, 402, 403, 429)
    return False


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

    for attempt in range(3):
        try:
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
                return

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
                return

        except Exception as e:
            if _is_auth_error(e) and _refresh_free_key():
                continue
            print(f"  [{task_id}] ошибка: {e}")
            return

    print(f"  [{task_id}] не удалось после 3 попыток")


def cmd_run_planner(ws: Workspace, args: list[str]):
    agent = PlannerAgent(llm=_resolve_llm())
    print("[planner] ожидание задач...")
    while True:
        for t in ws.list_tasks():
            session = ws.read_session(t.task_id)
            if session and session.status == "planner_turn":
                try:
                    result = agent.process(session)
                except Exception as e:
                    if _is_auth_error(e) and _refresh_free_key():
                        agent = PlannerAgent(llm=_resolve_llm())
                        continue
                    print(f"  [planner] {t.task_id} ошибка: {e}")
                    time.sleep(10)
                    continue
                session.plan = result.get("plan", result["content"])
                session.history.append(HistoryEntry(
                    role="planner", content=result["content"], iteration=session.iteration
                ))
                session.status = "critic_turn"
                ws.update_session(session)
                print(f"  [planner] {t.task_id} итер {session.iteration} — готово")
        time.sleep(2)


def cmd_run_critic(ws: Workspace, args: list[str]):
    agent = CriticAgent(llm=_resolve_llm())
    print("[critic] ожидание задач...")
    while True:
        for t in ws.list_tasks():
            session = ws.read_session(t.task_id)
            if session and session.status == "critic_turn":
                try:
                    result = agent.process(session)
                except Exception as e:
                    if _is_auth_error(e) and _refresh_free_key():
                        agent = CriticAgent(llm=_resolve_llm())
                        continue
                    print(f"  [critic] {t.task_id} ошибка: {e}")
                    time.sleep(10)
                    continue
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


def cmd_fetch_keys(ws: Workspace, args: list[str]):
    print("Загрузка ключей из alistaitsacle/free-llm-api-keys...")
    try:
        resp = httpx.get("https://raw.githubusercontent.com/alistaitsacle/free-llm-api-keys/main/README.md", timeout=30)
        resp.raise_for_status()
    except Exception as e:
        print(f"Ошибка загрузки: {e}")
        return

    text = resp.text
    sections = re.split(r'\n(?=###\s)', text)
    found = []
    for sec in sections:
        title_m = re.match(r'###\s+(.+?)(?:\s+`[^`]+`)?\s*$', sec, re.MULTILINE)
        title = title_m.group(1).strip() if title_m else ""
        rows = re.findall(r'\|\s*`(sk-\w+)`\s*\|\s*(\S+?)\s*\|', sec)
        if rows:
            found.append((title, rows))

    print(f"\nНайдено {len(found)} разделов:")
    for title, rows in found:
        print(f"\n  {title}")
        for key, model in rows[:3]:
            print(f"    модель: {model}")
            print(f"    ключ: {key[:20]}...")
            print(f"    export FREE_API_KEY={key}")
            print(f"    export FREE_API_MODEL={model}")


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
    print("  fetch-keys                   Получить бесплатные API-ключи с GitHub")
    print()
    print("Переменные окружения:")
    print("  FREE_API_KEY                 Бесплатный API-ключ (приоритет)")
    print("  FREE_API_MODEL               Модель для FreeLLM (по умолч. deepseek/deepseek-v4-flash)")
    print("  FREE_API_BASE_URL            Базовый URL (по умолч. https://aiapiv2.pekpik.com/v1)")
    print("  DEEPSEEK_API_KEY             API-ключ DeepSeek (если нет FREE_API_KEY)")


COMMANDS = {
    "task": cmd_create_task,
    "list": cmd_list,
    "status": cmd_status,
    "advance": cmd_advance,
    "run-planner": cmd_run_planner,
    "run-critic": cmd_run_critic,
    "fetch-keys": cmd_fetch_keys,
}


def main():
    from dotenv import load_dotenv
    load_dotenv()
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
