from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from typing import Callable

import libcst as cst
import libcst.matchers as M
from libcst.codemod import CodemodContext, VisitorBasedCodemodCommand
from libcst.codemod.visitors import AddImportsVisitor


# ── Hook / Scope ──────────────────────────────────────────────────────

HookFn = Callable[[cst.CSTNode], cst.CSTNode | None]


class Scope:
    """Изолированное пространство для хуков одного агента.

    Аналог gardener.Scope, но на LibCST и для Python-кода.
    Использование:
        agent_x = Scope("coder")
        @agent_x.hook("pre_codemod")
        def my_hook(node): ...
    """

    def __init__(self, name: str):
        self.name = name
        self._hooks: dict[str, list[HookFn]] = {}

    def hook(self, event: str):
        """Декоратор для регистрации хука на событие."""
        def wrapper(fn: HookFn):
            self._hooks.setdefault(event, []).append(fn)
            return fn
        return wrapper

    def run(self, event: str, node: cst.CSTNode) -> cst.CSTNode:
        """Запустить все хуки на событие."""
        for fn in self._hooks.get(event, []):
            result = fn(node)
            if result is not None:
                node = result
        return node

    @property
    def events(self) -> list[str]:
        return list(self._hooks)


# ── Diff analysis ─────────────────────────────────────────────────────

@dataclass
class Change:
    type: str  # 'add' | 'remove' | 'modify'
    line: int
    old_text: str = ""
    new_text: str = ""


def analyze_diff(old_code: str, new_code: str) -> list[Change]:
    """Сравнить две версии кода, вернуть список изменений."""
    changes: list[Change] = []
    old_lines = old_code.splitlines(keepends=True)
    new_lines = new_code.splitlines(keepends=True)

    for group in difflib.context_diff(old_lines, new_lines, n=0):
        line = group.splitlines()[0] if group else ""
        if line.startswith("--- ") or line.startswith("+++ "):
            continue
        for l in group.splitlines():
            if l.startswith("@@ "):
                parts = l.split()
                if len(parts) >= 2:
                    old_start = int(parts[1].split(",")[0].lstrip("-"))
                    changes.append(Change(type="modify", line=old_start))
            elif l.startswith("- "):
                changes.append(Change(type="remove", line=0, old_text=l[2:]))
            elif l.startswith("+ "):
                changes.append(Change(type="add", line=0, new_text=l[2:]))

    return changes


# ── CST-based codemod commands ────────────────────────────────────────

class RenameImportCommand(VisitorBasedCodemodCommand):
    """Заменить from X import Y на from X import Z."""

    def __init__(self, context: CodemodContext, old_name: str, new_name: str):
        super().__init__(context)
        self.old_name = old_name
        self.new_name = new_name

    def leave_ImportAlias(
        self, original: cst.ImportAlias, updated: cst.ImportAlias
    ) -> cst.ImportAlias:
        if M.matches(original, M.ImportAlias(name=M.Name(self.old_name))):
            return updated.with_changes(
                name=cst.Name(self.new_name)
            )
        return updated


class AddMethodCommand(VisitorBasedCodemodCommand):
    """Добавить метод к классу (с insert_before/insert_after)."""

    def __init__(
        self,
        context: CodemodContext,
        class_name: str,
        method_code: str,
        insert_after: str | None = None,
    ):
        super().__init__(context)
        self.class_name = class_name
        self.method_stmt = cst.parse_statement(method_code)
        self.insert_after = insert_after

    def leave_ClassDef(
        self, original: cst.ClassDef, updated: cst.ClassDef
    ) -> cst.ClassDef:
        if original.name.value != self.class_name:
            return updated

        if self.insert_after:
            new_body = []
            inserted = False
            for stmt in updated.body.body:
                new_body.append(stmt)
                if isinstance(stmt, cst.SimpleStatementLine):
                    first_expr = stmt.body[0] if stmt.body else None
                    if isinstance(first_expr, cst.Expr):
                        call = first_expr.value
                        if isinstance(call, cst.Call):
                            func = call.func
                            if isinstance(func, cst.Name) and func.value == self.insert_after:
                                new_body.append(self.method_stmt)
                                inserted = True
                        elif isinstance(call, cst.Attribute):
                            pass
            if not inserted:
                new_body.append(self.method_stmt)
            return updated.with_changes(body=cst.IndentedBlock(body=new_body))
        else:
            new_body = list(updated.body.body) + [self.method_stmt]
            return updated.with_changes(body=cst.IndentedBlock(body=new_body))


# ── Core API ──────────────────────────────────────────────────────────

@dataclass
class CodemodResult:
    success: bool
    code: str
    changes: list[Change] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def compare_and_update(
    old_code: str,
    new_code: str,
    scopes: list[Scope] | None = None,
    autorename: dict[str, str] | None = None,
    add_imports: list[tuple[str, str | None]] | None = None,
) -> CodemodResult:
    """Сравнить старый и новый код, выполнить трансформации.

    Args:
        old_code: Исходный Python-код
        new_code: Новый Python-код
        scopes: Список Scope с хуками
        autorename: {old_name: new_name} для переименования импортов
        add_imports: [(module, obj), ...] для добавления импортов

    Returns:
        CodemodResult с итоговым кодом
    """
    changes = analyze_diff(old_code, new_code)

    try:
        source_tree = cst.parse_module(new_code)
    except SyntaxError as e:
        return CodemodResult(success=False, code=new_code, changes=changes, errors=[str(e)])

    # Pre-codemod hooks
    if scopes:
        for scope in scopes:
            source_tree = scope.run("pre_codemod", source_tree)

    context = CodemodContext()

    # Авто-переименование импортов
    if autorename:
        for old, new in autorename.items():
            cmd = RenameImportCommand(context, old_name=old, new_name=new)
            source_tree = cmd.transform_module(source_tree)

    # Авто-добавление импортов
    if add_imports:
        for module, obj in add_imports:
            AddImportsVisitor.add_needed_import(context, module, obj)
        source_tree = AddImportsVisitor(context).transform_module(source_tree)

    # Post-codemod hooks
    if scopes:
        for scope in scopes:
            source_tree = scope.run("post_codemod", source_tree)

    result_code = source_tree.code
    return CodemodResult(success=True, code=result_code, changes=changes)


def update_skill_file(
    filepath: str,
    new_code: str,
    scopes: list[Scope] | None = None,
    autorename: dict[str, str] | None = None,
) -> CodemodResult:
    """Прочитать файл скилла, применить трансформации, записать обратно."""
    from pathlib import Path

    path = Path(filepath)
    if not path.exists():
        return CodemodResult(success=False, code=new_code, errors=[f"File not found: {filepath}"])

    old_code = path.read_text()
    result = compare_and_update(
        old_code=old_code,
        new_code=new_code,
        scopes=scopes,
        autorename=autorename,
    )

    if result.success:
        path.write_text(result.code)

    return result


# ── CLI ───────────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(description="skill-codemod: LibCST-based code transformer")
    parser.add_argument("file", help="Python file to update")
    parser.add_argument("--rename", nargs=2, action="append", metavar=("OLD", "NEW"),
                        help="Rename import: --rename CoderAgent ReviewerAgent")
    parser.add_argument("--add-import", nargs=2, action="append", metavar=("MODULE", "NAME"),
                        help="Add import: --add-import json None")
    parser.add_argument("--show-diff", action="store_true", help="Show diff only, don't write")

    args = parser.parse_args()
    from pathlib import Path

    path = Path(args.file)
    if not path.exists():
        print(f"Error: {args.file} not found")
        return 1

    old = path.read_text()
    new = old

    autorename = {}
    if args.rename:
        for old_n, new_n in args.rename:
            autorename[old_n] = new_n

    add_imports = []
    if args.add_import:
        for mod, name in args.add_import:
            obj = None if name.lower() == "none" else name
            add_imports.append((mod, obj))

    result = compare_and_update(
        old_code=old,
        new_code=new,
        autorename=autorename if autorename else None,
        add_imports=add_imports if add_imports else None,
    )

    if not result.success:
        print("Error:", result.errors)
        return 1

    if args.show_diff:
        for c in result.changes:
            print(f"  [{c.type}] line {c.line}")
    else:
        path.write_text(result.code)
        print(f"Updated {args.file}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
