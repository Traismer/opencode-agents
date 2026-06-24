# opencode-agents

## Setup

```sh
poetry install        # создаёт/обновляет .venv/ с src/ пакетом
```

Virtualenv в `.venv/` (задано в `poetry.toml`). `poetry shell` не используем — только `poetry run <cmd>`.

Линтер, тесты, typecheck не настроены. В `pyproject.toml` нет pytest, ruff, mypy, pre-commit. CI тоже нет.

## Архитектура

Файловая координация между агентами. Агенты никогда не вызывают друг друга — читают/пишут JSON-файлы в `workflow/`.

### Агенты

| Роль | Класс | Файл | Примечание |
|------|-------|------|------------|
| orchestrator | `OrchestratorAgent` | `agents/orchestrator.py` | **НЕ наследник `BaseAgent`.** Имеет `process_task(task_id)` — один шаг состояния за вызов. Нужно несколько вызовов. |
| coder | `CoderAgent` | `agents/coder.py` | Наследует `BaseAgent`. Следит за `inbox/coder/`. |
| reviewer | `ReviewerAgent` | `agents/reviewer.py` | Наследует `BaseAgent`. Следит за `inbox/reviewer/`. |

### Ключевые неочевидные факты

- **Пакет в `src/`**: В `pyproject.toml` указано `packages = [{include = "opencode_agents", from = "src"}]`. Импорт: `from opencode_agents.workspace import Workspace`.
- **`Workspace()` сам создаёт директории**: Не нужно делать `mkdir workflow/...` вручную. Создаёт `workflow/` и `tasks/` при инициализации.
- **`take_subtask` перемещает файлы**: Атомарно (`Path.rename`) из `inbox/<role>/` в `in_progress/<role>/`. Не копирует.
- **`wait_for_results` существует, но не используется CLI**: `Workspace` имеет блокирующий `wait_for_results()`. Команда `orchestrate` его не использует — вызывай `orchestrate` один раз за фазу.
- **`StubLLM` по умолчанию**: `CoderAgent(ws)` использует `StubLLM`, возвращающий код-заглушку. API-ключ не нужен для тестирования. Замена: `CoderAgent(ws, llm=MyLLM())`.
- **`opencode.json`** содержит MCP-конфиг для `context7` — не относится к коду репозитория.
- **`__init__.py` файлы пустые** — нет реэкспортов пакета.

### Шаблон нового агента

Наследуй `BaseAgent`, задай `role`, реализуй `process(subtask) -> dict`:

```python
class MyAgent(BaseAgent):
    role = "myrole"
    def process(self, subtask):
        # self.ws (Workspace), self.llm (задаётся вызывающим)
        return {"task_id": ..., "status": "done", "output": ..., "files": []}
```

Возвращаемый dict получает поля `role` и `subtask_id` от `run_once()`. Включать их не нужно.

## Команды

```sh
poetry run python -m opencode_agents task "описание" --reqs "требование1" "требование2"
poetry run python -m opencode_agents list
poetry run python -m opencode_agents status <task_id>
poetry run python -m opencode_agents orchestrate <task_id>   # один шаг фазы
poetry run python -m opencode_agents run-coder               # бесконечный цикл
poetry run python -m opencode_agents run-reviewer            # бесконечный цикл
poetry run python -m opencode_agents demo                    # полный пайплайн
```

Мультипроцесс: запусти `run-coder` и `run-reviewer` в разных терминалах, вызывай `orchestrate <task_id>` несколько раз для продвижения по фазам.
