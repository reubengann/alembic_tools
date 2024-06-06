import ast
from enum import Enum
from itertools import groupby
from pathlib import Path
from alembic_tools.code_reader import find_upgrade_function
from alembic_tools.revision_collection import (
    get_revision_walk,
    get_script_directory,
)


def is_alembic_call(func: ast.Attribute, operation: str) -> bool:
    return (
        isinstance(func.value, ast.Name)
        and func.value.id == "op"
        and func.attr == operation
    )


def get_value_from_constant(e: ast.expr) -> str | None:
    if not isinstance(e, ast.Constant):
        return None
    return e.value


class ChangeType(Enum):
    NONE = 0
    TABLE_CREATE = 1
    ADD_COLUMN = 2
    DROP_COLUMN = 3


def get_create_table_args(
    node: ast.AST, table_name: str
) -> list[tuple[ChangeType, str]]:
    ret: list[tuple[ChangeType, str]] = []
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        if not isinstance(child.func, ast.Attribute):
            continue
        if is_alembic_call(child.func, "create_table"):
            maybe_table_name = get_value_from_constant(child.args[0])
            if maybe_table_name is not None and maybe_table_name == table_name:
                ret.append((ChangeType.TABLE_CREATE, "created"))
            continue
        if is_alembic_call(child.func, "add_column"):
            maybe_table_name = get_value_from_constant(child.args[0])
            if maybe_table_name is not None and maybe_table_name == table_name:
                if isinstance(child.args[1], ast.Call):
                    maybe_column_name = get_value_from_constant(child.args[1].args[0])
                    if maybe_column_name is None:
                        continue
                    ret.append((ChangeType.ADD_COLUMN, maybe_column_name))
            continue
        if is_alembic_call(child.func, "drop_column"):
            maybe_table_name = get_value_from_constant(child.args[0])
            if maybe_table_name is not None and maybe_table_name == table_name:
                if isinstance(child.args[1], ast.Constant):
                    maybe_column_name = get_value_from_constant(child.args[1])
                    if maybe_column_name is None:
                        continue
                    ret.append((ChangeType.DROP_COLUMN, maybe_column_name))
            continue

    return ret


def search_collection(table_name: str):
    print(f"Table: {table_name}")
    script_folder = get_script_directory()
    for rev in list(get_revision_walk(script_folder)):
        p = Path(rev.path)
        tree = ast.parse(p.read_text(), filename=p)
        upgrade_code = find_upgrade_function(tree)
        if upgrade_code is None:
            continue
        ops = get_create_table_args(upgrade_code, table_name)
        if ops:
            op_strings = []
            grouped_operations = groupby(ops, key=lambda x: x[0])
            for ct, stuff in grouped_operations:
                if ct == ChangeType.ADD_COLUMN:
                    label = "column"
                    stuff = list(stuff)
                    if len(stuff) > 1:
                        label += "s"
                    op_strings.append(
                        f"Added {label} {', '.join([s[1] for s in stuff])}"
                    )
                elif ct == ChangeType.DROP_COLUMN:
                    label = "column"
                    stuff = list(stuff)
                    if len(stuff) > 1:
                        label += "s"
                    op_strings.append(
                        f"Dropped {label} {', '.join([s[1] for s in stuff])}"
                    )
                elif ct == ChangeType.TABLE_CREATE:
                    op_strings.append("Created")
            print(rev.revision, ", ".join(op_strings))
