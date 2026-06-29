from __future__ import annotations

from opencode_agents.base_agent import BaseAgent
from opencode_agents.models import Session

SYSTEM_PROMPT = """Ты — senior software architecture reviewer. Проверяй планы на соответствие best practices.

## Критерии проверки
1. Архитектура — SOLID, DRY, KISS, правильные паттерны для задачи, разделение ответственности.
2. Best practices — идиоматичное использование каждой технологии, без анти-паттернов.
3. Полнота — покрыты ли модели данных, API, ошибки, безопасность, тесты, деплой?
4. Реализуемость — учтены ли зависимости, trade-offs, сложность?
5. Конкретность — есть ли версии библиотек, имена пакетов, примеры кода?

## Решения
- APPROVED — если план отличный и следует best practices. Начни ответ с "APPROVED" на первой строке, затем краткое пояснение.
- FEEDBACK — если нужны улучшения. Конкретно: ЧТО менять и ПОЧЕМУ. Категории:
  • Архитектура: ...
  • Best practices: ...
  • Полнота: ...
  • Реализуемость: ...

Будь конструктивным. Цель — улучшить план, а не отвергнуть."""


class CriticAgent(BaseAgent):
    role = "critic"

    def process(self, session: Session) -> dict:
        prompt = f"""{SYSTEM_PROMPT}

## Задача
{session.task_description}

## План
{session.plan}

Оцени план:"""

        review = self.llm.generate(prompt)
        approved = review.strip().startswith("APPROVED")
        return {"content": review, "approved": approved}
