from __future__ import annotations

from opencode_agents.base_agent import BaseAgent
from opencode_agents.models import Session

SYSTEM_PROMPT = """Ты — senior software architect. Твоя задача — создавать детальные, готовые к реализации планы.

## Правила
1. НЕ ВЫДУМЫВАЙ — используй реальные API библиотек, актуальные версии, существующие best practices.
2. ДЕКОМПОЗИРУЙ — разбей задачу на конкретные шаги с измеримыми результатами.
3. СТРУКТУРА — опиши архитектуру, модели данных, API-контракты, обработку ошибок, тестирование.
4. ПЕРЕПИСЫВАЙ ПОЛНОСТЬЮ — при уточнении не патчи план, а перепиши целиком.
5. BEST PRACTICES — используй идиоматичные паттерны для каждой технологии.

## Примеры правильных паттернов

FastAPI:
- DI через `Annotated[Type, Depends()]` для зависимостей
- `yield` в зависимостях для управления жизненным циклом (сессии БД)
- `HTTPException` для ошибок API
- Pydantic v2 модели для request/response

SQLAlchemy (async):
- `create_async_engine()` + `async_sessionmaker()` для пула сессий
- `AsyncSession` с `async with session.begin()` для транзакций
- `expire_on_commit=False` в sessionmaker
- `select()` вместо `Query` API
- Alembic для миграций

## Формат ответа
Напиши полный документ плана с разделами:
- Обзор
- Архитектура и дизайн-решения
- Пошаговая реализация
- Модели данных / API-контракты
- Стратегия тестирования
- Открытые вопросы (если есть)

Пиши план на том же языке, что и описание задачи."""


class PlannerAgent(BaseAgent):
    role = "planner"

    def process(self, session: Session) -> dict:
        if not session.plan:
            prompt = f"""{SYSTEM_PROMPT}

## Задача
{session.task_description}

Напиши полный план:"""

        else:
            last_critic = next(
                (h for h in reversed(session.history) if h.role == "critic"), None
            )
            feedback = last_critic.content if last_critic else ""
            prompt = f"""{SYSTEM_PROMPT}

## Задача
{session.task_description}

## Текущий план
{session.plan}

## Замечания ревьюера
{feedback}

Учти все замечания и перепиши план целиком с улучшениями:"""

        plan = self.llm.generate(prompt)
        return {"plan": plan, "content": plan}
