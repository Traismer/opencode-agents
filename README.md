# opencode-agents

Итеративный цикл двух AI-агентов: **Planner** пишет план, **Critic** проверяет.
Общий файл сессии — единственная точка координации.

## Быстрый старт

```sh
poetry install

export DEEPSEEK_API_KEY="sk-..."
poetry run python -m opencode_agents task "FastAPI REST API для заметок"
poetry run python -m opencode_agents advance task-abc123   # planner пишет план
poetry run python -m opencode_agents advance task-abc123   # critic проверяет
poetry run python -m opencode_agents advance task-abc123   # planner уточняет
poetry run python -m opencode_agents advance task-abc123   # critic аппрувит
```

Без `DEEPSEEK_API_KEY` — `StubLLM` (всегда аппрувит). Для теста без API-ключа:

```sh
poetry run python -m opencode_agents task "CLI утилита"
poetry run python -m opencode_agents advance task-abc123   # planner → заглушка
poetry run python -m opencode_agents advance task-abc123   # critic → APPROVED
```

## Архитектура

```
                    ┌──────────────────┐
                    │  workflow/       │
                    │  sessions/       │
                    │  task-*.json     │ ◄── общий файл сессии
                    └────────┬─────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
     ┌────────▼────────┐          ┌─────────▼────────┐
     │   PlannerAgent  │          │   CriticAgent    │
     │                 │          │                  │
     │   пишет план    │──iter──► │   проверяет      │──iter──►
     │   уточняет      │          │   аппрувит       │
     │   по feedback   │◄─────────│   или feedback   │
     └─────────────────┘          └──────────────────┘
```

Агенты **никогда не вызывают друг друга напрямую**. Они читают и пишут один JSON-файл сессии в `workflow/sessions/<task_id>.json`. Это позволяет запускать их в разных процессах, перезапускать по отдельности и видеть всю историю.

## Команды

```sh
task <описание>              Создать новую задачу
list                         Список всех задач
status <task_id>             Статус и текущий план
advance <task_id>            Один шаг: planner или critic
run-planner                  Демон planner (бесконечный цикл)
run-critic                   Демон critic (бесконечный цикл)
```

## Итеративный цикл

1. `task "..."` → создаётся сессия со статусом `planner_turn`
2. `advance` → **PlannerAgent** пишет план, статус → `critic_turn`
3. `advance` → **CriticAgent** проверяет:
   - `APPROVED` — план отличный, статус → `approved` ✅
   - `Feedback` — нужны улучшения, статус → `planner_turn`, итерация +1
4. Повтор п.2-3 до аппрува или лимита итераций (по умолчанию 5)

## Пример сессии

```sh
$ poetry run python -m opencode_agents task "FastAPI + SQLAlchemy"
Создана задача: task-a1b2c3d4

$ poetry run python -m opencode_agents advance task-a1b2c3d4
  [planner] итер 0 — план обновлён (2847 симв.)

$ poetry run python -m opencode_agents advance task-a1b2c3d4
  [critic] итер 0 — замечания

$ poetry run python -m opencode_agents advance task-a1b2c3d4
  [planner] итер 1 — план обновлён (3102 симв.)

$ poetry run python -m opencode_agents advance task-a1b2c3d4
  [critic] итер 1 — ОДОБРЕНО

$ poetry run python -m opencode_agents status task-a1b2c3d4
Задача: task-a1b2c3d4
  статус: approved
  итерация: 1/5
  записей в истории: 4
```

## Переменные окружения

| Переменная | Назначение |
|-----------|-----------|
| `DEEPSEEK_API_KEY` | API-ключ DeepSeek для реального LLM (без него — StubLLM) |

## Создать нового агента

```python
from opencode_agents.base_agent import BaseAgent
from opencode_agents.models import Session

class MyAgent(BaseAgent):
    role = "myrole"

    def process(self, session: Session, **kwargs) -> dict:
        # self.llm.generate(prompt) — доступен
        return {"content": "...", ...}
```

Подробнее: [docs/AGENT_GUIDE.md](docs/AGENT_GUIDE.md)

## Структура пакета

```
src/opencode_agents/
├── __main__.py          CLI — task/list/status/advance/run-*
├── models.py            Task, Session, HistoryEntry
├── workspace.py         Файловое I/O: tasks/ + sessions/
├── llm.py               BaseLLM, StubLLM, DeepSeekLLM
├── base_agent.py        BaseAgent (ABC)
├── tools.py             Заглушка для context7 (доступен через opencode)
└── agents/
    ├── planner.py       PlannerAgent — пишет план
    └── critic.py        CriticAgent — ревьюит план
```

## Документация

- [ARCHITECTURE.md](docs/ARCHITECTURE.md) — детальная архитектура
- [AGENT_GUIDE.md](docs/AGENT_GUIDE.md) — создание новых агентов
