# Архитектура opencode-agents

## Общая схема

```
пользователь
     │
     ▼  task "описание"
┌─────────────┐
│  __main__.py │  CLI: создаёт task + session
│  advance     │  вызывает planner или critic по очереди
└──────┬──────┘
       │
       ▼ читает/пишет
┌──────────────────────────┐
│  workflow/sessions/      │  ← единый файл координации
│  task-<id>.json          │
│                          │
│  {                       │
│    status: planner_turn  │  planner_turn | critic_turn
│    iteration: 0          │  | approved | max_iterations
│    plan: "..."           │  ← текущая версия плана
│    history: [...]        │  ← вся история итераций
│  }                       │
└──────────────────────────┘
       │
       ├── PlannerAgent ──→ пишет/уточняет план
       └── CriticAgent  ──→ проверяет, APPROVED или feedback
```

## Компоненты

### `__main__.py` — CLI

Точка входа. Команды:

| Команда | Действие |
|---------|----------|
| `task` | Создать Task + Session со статусом `planner_turn` |
| `list` | Показать все задачи и их статус |
| `status` | Показать сессию: статус, итерацию, план |
| `advance` | Прочитать сессию, определить кто ходит, вызвать агента, обновить сессию |
| `run-planner` | Бесконечный цикл: ждёт задачи в статусе `planner_turn` |
| `run-critic` | Бесконечный цикл: ждёт задачи в статусе `critic_turn` |

### `models.py` — модели данных

- **`Task`** — описание задачи (`task_id`, `description`, `created_at`)
- **`HistoryEntry`** — одна запись в истории (`role`, `content`, `iteration`)
- **`Session`** — сессия итераций:
  - `task_id`, `task_description`
  - `status`: `planner_turn` | `critic_turn` | `approved` | `max_iterations`
  - `iteration`: номер текущего цикла (0 — начальный)
  - `plan`: текущая версия плана (строка)
  - `history`: список `HistoryEntry` — вся переписка агентов
  - `max_iterations`: лимит циклов (по умолчанию 5)

### `workspace.py` — файловое I/O

- `tasks/` — JSON-файлы задач
- `workflow/sessions/` — JSON-файлы сессий

Методы: `create_task`, `read_task`, `list_tasks`, `create_session`, `read_session`, `update_session`.

### `llm.py` — LLM слой

- **`BaseLLM`** — абстрактный класс с методом `generate(prompt)`
- **`StubLLM`** — заглушка, всегда возвращает `APPROVED` (для тестов без API-ключа)
- **`DeepSeekLLM`** — реальная LLM через OpenAI-совместимый API DeepSeek

### `base_agent.py` — база для агентов

```python
class BaseAgent(ABC):
    role: str = ""
    llm: BaseLLM

    @abstractmethod
    def process(self, session: Session, **kwargs) -> dict:
        ...
```

### `agents/planner.py` — PlannerAgent

**Роль:** Senior software architect.

- Получает задачу и пишет детальный план
- При уточнении получает feedback от критика и переписывает план целиком
- SYSTEM_PROMPT содержит best practices для популярных библиотек
- Возвращает `{"plan": str, "content": str}`

**Правила:**
1. Не выдумывать — только реальные API и best practices
2. Декомпозировать задачу на шаги
3. Включать архитектуру, модели, API, тесты
4. Переписывать план целиком при уточнении

### `agents/critic.py` — CriticAgent

**Роль:** Senior architecture reviewer.

- Проверяет план на best practices
- Возвращает `APPROVED` или категориальный feedback

**Критерии:**
1. Архитектура (SOLID, DRY, KISS)
2. Best practices (идиоматичное использование каждой технологии)
3. Полнота (модели, API, ошибки, тесты)
4. Реализуемость (зависимости, trade-offs)

### `tools.py` — заглушка для context7

context7 MCP подключён к opencode и используется ассистентом при написании кода. Агенты не имеют доступа к context7 — они полагаются на built-in best practices в SYSTEM_PROMPT.

## Жизненный цикл задачи

```
1. task "REST API на FastAPI"
   └→ tasks/task-abc.json создан
   └→ workflow/sessions/task-abc.json:
       status = "planner_turn", iteration = 0

2. advance task-abc
   └→ PlannerAgent.process(session)
   └→ session.plan = "...# план..."
   └→ session.history += [{role: "planner", ...}]
   └→ session.status = "critic_turn"

3. advance task-abc
   └→ CriticAgent.process(session)
   └→ если одобрено: session.status = "approved" ✓
   └→ если feedback:
       └→ session.iteration += 1
       └→ session.status = "planner_turn"
       └→ повторяем п.2-3

4. Готово: status = "approved" | "max_iterations"
```

## Мультипроцесс (демоны)

В трёх терминалах:

```sh
# Терминал 1: planner
poetry run python -m opencode_agents run-planner

# Терминал 2: critic
poetry run python -m opencode_agents run-critic

# Терминал 3: управление
poetry run python -m opencode_agents task "FastAPI + SQLAlchemy"
# Через несколько секунд агенты сами подхватят задачу
poetry run python -m opencode_agents status task-abc123
```

## Зависимости

- Python 3.13+
- httpx (для DeepSeekLLM)
- DeepSeek API ключ (опционально, для реальной LLM)

## Добавление новой библиотеки в KNOWN_LIBRARIES

В `tools.py` есть список `KNOWN_LIBRARIES` — он используется мной (ассистентом) как справочник при написании кода. Если в задаче появилась новая библиотека, её можно добавить в этот список.
