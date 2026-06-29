# Создание нового агента

## Базовая структура

Все агенты наследуются от `BaseAgent` и реализуют метод `process()`:

```python
from opencode_agents.base_agent import BaseAgent
from opencode_agents.models import Session
from opencode_agents.llm import BaseLLM


class MyAgent(BaseAgent):
    role = "myagent"

    def process(self, session: Session, **kwargs) -> dict:
        # self.llm — экземпляр BaseLLM
        # session — текущая сессия с планом и историей
        prompt = f"..."
        result = self.llm.generate(prompt)
        return {"content": result}
```

## Подключение в CLI

1. Создай файл `src/opencode_agents/agents/myagent.py`
2. Добавь импорт и команду в `__main__.py`:

```python
from opencode_agents.agents.myagent import MyAgent

def cmd_run_myagent(ws, args):
    llm = _resolve_llm()
    agent = MyAgent(llm=llm)
    # ...

COMMANDS = {
    # ...
    "run-myagent": cmd_run_myagent,
}
```

## Расширение модели Session

Если новому агенту нужны дополнительные поля в сессии, добавь их в `Session` в `models.py`:

```python
@dataclass
class Session:
    # ... существующие поля
    my_custom_field: str = ""
    # Добавь в to_dict() и from_dict()
```

## Продвинутый агент с инструментами

Агент может принимать дополнительные параметры через `**kwargs`. Например, доступ к базе данных или внешнему API:

```python
class DataAgent(BaseAgent):
    role = "data"

    def process(self, session: Session, db_url: str = "") -> dict:
        if db_url:
            # подключение к БД для исследования схемы
            pass
        prompt = f"..."
        result = self.llm.generate(prompt)
        return {"content": result}
```

## Требования к process()

Метод `process()` должен вернуть словарь с ключами:

| Ключ | Тип | Обязательный | Описание |
|------|-----|-------------|----------|
| `content` | str | да | Основной вывод агента |
| `plan` | str | нет | Обновлённый план (если агент меняет план) |
| `approved` | bool | нет | Флаг одобрения (для CriticAgent) |

CLI после вызова `process()` сам обновляет `session.plan` (если есть ключ `plan`) и управляет статусом сессии.
