import ast
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


def get_create_table_args(node: ast.AST, table_name: str) -> list:
    ret = []
    for child in ast.walk(node):
        if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
            if is_alembic_call(child.func, "create_table"):
                if (
                    isinstance(child.args[0], ast.Constant)
                    and child.args[0].value == table_name
                ):
                    ret.append("created")
            elif is_alembic_call(child.func, "add_column"):
                if (
                    isinstance(child.args[0], ast.Constant)
                    and child.args[0].value == table_name
                ):
                    ret.append("added column")

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
            print(rev.revision, ", ".join(ops))
