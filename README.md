# opencode-agents

Фреймворк для оркестрации нескольких AI-агентов, которые общаются через файлы.

Агенты не вызывают друг друга напрямую — каждый пишет JSON-файлы в общую рабочую директорию `workflow/` и читает оттуда. Это позволяет запускать агентов в разных процессах, перезапускать по отдельности и видеть всю историю работы.

## Быстрый старт

```sh
poetry install                      # создать .venv/
poetry run python -m opencode_agents demo   # запустить демо-пайплайн
```

Демо создаст задачу «написать калькулятор»,分解 её на подзадачи, запустит кодеров и ревьюера, соберёт результат.

## Архитектура

```
workflow/
  inbox/coder/          ← новые подзадачи для кодера
  inbox/reviewer/       ← новые подзадачи для ревьюера
  in_progress/          ← взятые в работу (ещё не готовы)
  done/                 ← завершённые результаты
  state/                ← фаза обработки (init → collect → review → done)
  results/              ← финальные артефакты
tasks/                  ← входные описания задач
```

**Поток одной задачи:**
1. Ты кладёшь задачу в `tasks/` (через CLI)
2. **Оркестратор** читает задачу, раскладывает подзадачи по `inbox/coder/`
3. **Кодер** забирает подзадачу, пишет код, кладёт результат в `done/`
4. Оркестратор видит, что всё готово, кладёт подзадачу в `inbox/reviewer/`
5. **Ревьюер** проверяет код, пишет отзыв в `done/`
6. Оркестратор собирает финальный артефакт в `workflow/results/`

## Команды

```sh
# Управление задачами
poetry run python -m opencode_agents task "CLI утилита" --reqs "парсинг аргументов" "вывод справки"
poetry run python -m opencode_agents list
poetry run python -m opencode_agents status <task_id>

# Оркестрация (один шаг)
poetry run python -m opencode_agents orchestrate <task_id>

# Запуск агентов (бесконечный цикл, ждут новые подзадачи)
poetry run python -m opencode_agents run-coder      # в терминале 1
poetry run python -m opencode_agents run-reviewer   # в терминале 2

# Демо
poetry run python -m opencode_agents demo
```

## Мультипроцесс

В трёх терминалах:

```sh
# Терминал 1: следит за кодингом
poetry run python -m opencode_agents run-coder

# Терминал 2: следит за ревью
poetry run python -m opencode_agents run-reviewer

# Терминал 3: оркестрируем
poetry run python -m opencode_agents task "моя задача" --reqs "шаг1" "шаг2" "шаг3"
poetry run python -m opencode_agents orchestrate task-xxxx   # decompose
poetry run python -m opencode_agents orchestrate task-xxxx   # collect
poetry run python -m opencode_agents orchestrate task-xxxx   # finalize
```

## Создать нового агента

Наследуйся от `BaseAgent`:

```python
from opencode_agents.base_agent import BaseAgent

class TesterAgent(BaseAgent):
    role = "tester"

    def process(self, subtask: dict) -> dict:
        code = subtask.get("instruction", "")
        tests = self.llm.generate(f"Напиши тесты для:\n{code}")
        return {
            "task_id": subtask["task_id"],
            "status": "done",
            "output": tests,
            "files": [{"path": "test_example.py", "content": tests}],
        }
```

Оркестратор будет класть подзадачи в `inbox/tester/`, а твой агент — забирать их оттуда.

## Подключить реальную LLM

```python
from opencode_agents.llm import BaseLLM
from opencode_agents.agents.coder import CoderAgent

class MyLLM(BaseLLM):
    def generate(self, prompt: str, **kwargs) -> str:
        # ... вызов OpenAI / Anthropic / локальной модели ...
        return response

coder = CoderAgent(ws, llm=MyLLM())
coder.run_loop()
```

Сейчас используется `StubLLM`, который возвращает заглушки — чтобы можно было тестировать пайплайн без API-ключей.

## Структура пакета

```
src/opencode_agents/
├── __main__.py          # CLI entrypoint
├── models.py            # Task, Subtask, Result
├── workspace.py         # файловое I/O
├── llm.py               # BaseLLM + StubLLM
├── base_agent.py        # BaseAgent (run_once / run_loop)
└── agents/
    ├── orchestrator.py  # конечный автомат
    ├── coder.py         # пишет код
    └── reviewer.py      # ревьюит код
```

## Куда двигаться

- Заменить `StubLLM` на реальную модель
- Добавить новых агентов (tester, deployer, documenter)
- Добавить таймауты и повторные попытки для подзадач
- Написать простой веб-интерфейс для просмотра `workflow/`
