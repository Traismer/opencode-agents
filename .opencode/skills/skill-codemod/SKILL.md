---
name: skill-codemod
description: >
  Анализирует изменения Python-кода через LibCST и автоматически обновляет
  навыки (skills). Поддерживает хуки для разных агентов и цепочки
  трансформаций.
license: MIT
compatibility: opencode
metadata:
  category: devtools
  python: ">=3.13"
---

## Что делает

- Сравнивает две версии Python-файла (CST diff) и выдаёт список изменений
- Применяет codemod-трансформации к коду навыков и агентов
- Позволяет регистрировать хуки — `pre_codemod`, `post_codemod`, `on_conflict`
- Строит цепочку агентов: задаёшь порядок, skill выполняет по шагам

## Когда использовать

- Навык (skill) нужно обновить под новую версию API/библиотеки
- В проект добавляется новый агент — нужно прописать его в цепочку
- Нужно проанализировать diff между коммитами и применить изменения к нескольким файлам
- Хочешь добавить hook-систему в свой skill

## Архитектура

```
SKILL.md                  # этот файл
codemod_agent.py          # Python-ядро на LibCST
```

Управление через скоупы (Scopes) — изолируешь логику каждого агента:

```python
from skill_codemod import Scope

planner_scope = Scope("planner")
critic_scope = Scope("critic")

@planner_scope.hook("pre_codemod")
def fix_imports(node):
    ...

@critic_scope.hook("post_codemod")
def validate(node):
    ...
```

Система агентов проекта: **PlannerAgent** (пишет план) и **CriticAgent** (ревьюит).

## Пример

```python
from skill_codemod import compare_and_update

diff = compare_and_update(
    old_path="skills/my-skill/SKILL.md",
    new_code=generated_code,
    hooks=[fix_imports, add_type_hints],
)
```
