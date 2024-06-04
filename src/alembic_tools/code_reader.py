import ast
from pathlib import Path


def get_revision_methods(p: Path) -> tuple[str, str] | None:
    code = p.read_text()
    tree = ast.parse(p.read_text(), filename=p)
    upgrade_code = extract_function_code(tree, code, "upgrade")
    downgrade_code = extract_function_code(tree, code, "downgrade")
    if upgrade_code is None:
        return None
    if downgrade_code is None:
        return None
    return upgrade_code, downgrade_code


def extract_function_code(tree, code, function_name) -> str | None:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            function_code = ast.get_source_segment(code, node)
            if function_code is None:
                return None
            return function_code.strip()
    return None


def find_upgrade_function(node: ast.AST) -> ast.FunctionDef | None:
    for child in ast.walk(node):
        if isinstance(child, ast.FunctionDef) and child.name == "upgrade":
            return child
    return None
