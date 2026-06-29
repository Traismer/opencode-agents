# opencode-agents

Итеративный цикл двух агентов: **Planner** пишет план, **Critic** проверяет.
Общий файл сессии — единственная точка координации.

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
     │   (planner.py)  │          │   (critic.py)    │
     │                 │          │                  │
     │  1. research()  │          │  1. review()     │
     │  2. write plan  │──iter──► │  2. approve?     │──iter──►
     │  3. update      │          │  3. feedback     │
     │   session       │◄─────────│   or APPROVED    │
     └─────────────────┘          └──────────────────┘
              │                             │
              └──────────────┬──────────────┘
                             │
                    ┌────────▼────────┐
                    │   context7 MCP  │
                    │  (tools.py)     │
                    │                 │
                    │  resolve-       │
                    │  library-id     │
                    │                 │
                    │  query-docs     │
                    └─────────────────┘
```

## Агенты

### PlannerAgent

**Роль:** Senior software architect. Создаёт детальный план реализации.

**Правила:**
- План должен быть основан на реальных API библиотек, а не на вымысле
- Декомпозировать задачу на конкретные шаги
- Включать: архитектуру, model'и данных, API-контракты, тестирование, деплой
- При уточнении — переписывать план целиком, не патчить

**Использует контекст из context7:**
Перед генерацией плана CLI автоматически вызывает `tools.py`, который:
1. Определяет библиотеки в описании задачи (FastAPI, SQLAlchemy, React и т.д.)
2. Запрашивает через context7 MCP лучшие практики и примеры кода
3. Встраивает результат в prompt планера

### CriticAgent

**Роль:** Senior architecture reviewer. Проверяет план на best practices.

**Критерии проверки:**
- Архитектура: SOLID, DRY, KISS, паттерны
- Best practices: идиоматичное использование каждой технологии
- Полнота: data models, API, ошибки, безопасность, тесты
- Реализуемость: учтены ли зависимости и trade-offs

**Решение:**
- `APPROVED` — план отличный, следует best practices
- Feedback — конкретные категории с пояснениями WHAT и WHY

## Context7 MCP (tools.py)

Автоматическое исследование библиотек через context7 MCP сервер.

**Запуск:** `npx -y @upstash/context7-mcp` (запускается автоматически)

**Как работает:**
1. `__main__.py` создаёт `Tools()` при вызове `advance`
2. `Tools.research_task(task_description)` ищет ключевые слова библиотек
3. Для каждой найденной библиотеки:
   - `resolve-library-id` — получает ID библиотеки в context7
   - `query-docs` — получает best practices и примеры кода
4. Результат встраивается в prompt PlannerAgent как "Research context"
5. Если context7 недоступен (нет Node.js/npx) — план строится на знаниях LLM

**Список отслеживаемых библиотек** — `tools.py:KNOWN_LIBRARIES`.

## Файловая структура

```
src/opencode_agents/
├── __main__.py          CLI: task/list/status/advance/run-*
├── models.py            Task, Session, HistoryEntry
├── workspace.py         File I/O: tasks/ + sessions/
├── llm.py               BaseLLM, StubLLM, DeepSeekLLM
├── base_agent.py        BaseAgent (ABC)
├── tools.py             Context7 MCP client + Tools wrapper
├── agents/
│   ├── planner.py       PlannerAgent
│   └── critic.py        CriticAgent
```

## Команды

```sh
# Создать задачу
poetry run python -m opencode_agents task "REST API для заметок на FastAPI"

# Список задач
poetry run python -m opencode_agents list

# Статус сессии
poetry run python -m opencode_agents status task-abc123

# Один шаг итерации (planner → critic → planner → ...)
poetry run python -m opencode_agents advance task-abc123

# Демоны в отдельных терминалах
poetry run python -m opencode_agents run-planner
poetry run python -m opencode_agents run-critic
```

## Типичный цикл

```sh
# Терминал 1
poetry run python -m opencode_agents task "FastAPI notes API with SQLAlchemy"

# Терминал 2 (или тот же)
poetry run python -m opencode_agents advance task-abc123   # planner пишет план
poetry run python -m opencode_agents advance task-abc123   # critic проверяет
poetry run python -m opencode_agents advance task-abc123   # planner уточняет
poetry run python -m opencode_agents advance task-abc123   # critic аппрувит (или снова feedback)
```

## Переменные окружения

| Переменная | Назначение |
|-----------|-----------|
| `DEEPSEEK_API_KEY` | API-ключ DeepSeek для реального LLM (без него — StubLLM) |
| (нет) | context7 MCP через npx, если Node.js установлен |

## Шаблон нового агента

```python
from opencode_agents.base_agent import BaseAgent
from opencode_agents.models import Session

class MyAgent(BaseAgent):
    role = "myrole"

    def process(self, session: Session, **kwargs) -> dict:
        # self.llm.generate(prompt) — доступен
        return {"content": "...", ...}
```

## Важные неочевидные факты

- **Пакет в `src/`**: `from opencode_agents.workspace import Workspace`
- **Session — единый файл**: `workflow/sessions/<task_id>.json`. Вся координация через него.
- **Planner и Critic никогда не вызывают друг друга** — читают и пишут один JSON.
- **context7 опционально**: если `npx` нет, агенты работают без исследования.
- **StubLLM по умолчанию**: без `DEEPSEEK_API_KEY` возвращает `APPROVED`.
- **`advance` — один шаг**: нужно вызывать несколько раз для завершения цикла.
- **Iteration = количество completed critic раундов**. Max по умолчанию — 5.
