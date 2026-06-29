# Быстрый старт

## 1. Установка

```sh
git clone <repo>
cd opencode_agents
poetry install
```

## 2. Получить бесплатный API-ключ

```sh
poetry run python -m opencode_agents fetch-keys
```

Выбрать DeepSeek V4 Flash (или любую другую модель) и установить переменные:

```sh
export FREE_API_KEY="sk-VoUPIZVFpEearfGg24QLetXEpGfdVAVrrp4A7tehLqIaXYM5"
export FREE_API_MODEL="deepseek/deepseek-v4-flash"
```

> Ключи живут 24–48 часов. Если перестали работать — запусти `fetch-keys` снова.

Можно также использовать DeepSeek API:

```sh
export DEEPSEEK_API_KEY="sk-..."
```

Без ключей используется StubLLM (всегда отвечает `APPROVED`).

## 3. Создать задачу

```sh
poetry run python -m opencode_agents task "REST API для заметок на FastAPI + SQLAlchemy"
```

Вывод:

```
Создана задача: task-abc123
  описание: REST API для заметок на FastAPI + SQLAlchemy
  статус: planner_turn
```

## 4. Запустить итерации (шаг за шагом)

```sh
# Planner пишет план
poetry run python -m opencode_agents advance task-abc123

# Посмотреть план и статус
poetry run python -m opencode_agents status task-abc123

# Critic проверяет план
poetry run python -m opencode_agents advance task-abc123

# Planner дорабатывает (если были замечания)
poetry run python -m opencode_agents advance task-abc123

# Critic аппрувит или снова замечания
poetry run python -m opencode_agents advance task-abc123
```

Повторять, пока не появится статус `approved`.

## 5. Или запустить демонов (автоматический режим)

В трёх терминалах:

**Терминал 1 — planner:**
```sh
poetry run python -m opencode_agents run-planner
```

**Терминал 2 — critic:**
```sh
poetry run python -m opencode_agents run-critic
```

**Терминал 3 — управление:**
```sh
poetry run python -m opencode_agents task "REST API для заметок на FastAPI + SQLAlchemy"
# Через несколько секунд агенты сами подхватят задачу
poetry run python -m opencode_agents status task-abc123
```

## 6. Все команды

| Команда | Действие |
|---------|----------|
| `task <описание>` | Создать задачу + сессию |
| `list` | Список всех задач и их статусов |
| `status <task_id>` | Показать план, статус, историю |
| `advance <task_id>` | Один шаг (planner или critic) |
| `run-planner` | Демон-планировщик (ждёт задач) |
| `run-critic` | Демон-критик (ждёт планов) |
| `fetch-keys` | Загрузить свежие бесплатные API-ключи |

## 7. Переменные окружения

| Переменная | Назначение |
|-----------|-----------|
| `FREE_API_KEY` | Бесплатный ключ (приоритет) |
| `FREE_API_MODEL` | Модель (по умолч. `deepseek/deepseek-v4-flash`) |
| `FREE_API_BASE_URL` | Базовый URL (по умолч. `https://aiapiv2.pekpik.com/v1`) |
| `DEEPSEEK_API_KEY` | API-ключ DeepSeek (если нет `FREE_API_KEY`) |
