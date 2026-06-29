"""Интеграция с context7 MCP.

context7 MCP подключён к opencode (через npx @upstash/context7-mcp).
Используется мной (ассистентом) при написании кода — я запрашиваю
документацию и best practices напрямую через MCP-инструменты.

Агенты (Planner, Critic) НЕ имеют доступа к context7. Они полагаются
на built-in best practices, прописанные в их SYSTEM_PROMPT.
"""

from __future__ import annotations

# Список библиотек, которые отслеживаются при анализе задачи.
# Используется мной как справочник при генерации кода агентов.
KNOWN_LIBRARIES: dict[str, tuple[str, str]] = {
    "fastapi": ("FastAPI", "веб-фреймворк для Python"),
    "sqlalchemy": ("SQLAlchemy", "Python ORM"),
    "pydantic": ("Pydantic", "валидация данных Python"),
    "react": ("React", "UI библиотека JavaScript"),
    "next.js": ("Next.js", "React фреймворк"),
    "django": ("Django", "веб-фреймворк Python"),
    "flask": ("Flask", "веб-фреймворк Python"),
    "httpx": ("httpx", "HTTP клиент Python"),
    "pytest": ("pytest", "фреймворк тестирования Python"),
    "alembic": ("Alembic", "миграции БД Python"),
    "celery": ("Celery", "очередь задач Python"),
    "redis": ("Redis", "in-memory хранилище"),
    "postgresql": ("PostgreSQL", "реляционная БД"),
    "sqlite": ("SQLite", "встраиваемая БД"),
    "docker": ("Docker", "контейнеризация"),
    "kubernetes": ("Kubernetes", "оркестрация контейнеров"),
}


class Tools:
    """Заглушка для context7 research.

    Агенты не имеют доступа к context7 MCP — он доступен только
    через opencode. Этот класс оставлен для обратной совместимости
    и всегда возвращает пустой результат.
    """

    def research_task(self, description: str) -> str:
        return ""

    def close(self):
        pass
