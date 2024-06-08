import ast
from enum import Enum
from pathlib import Path


class StatementType(Enum):
    UNKNOWN = 0
    CREATE_TABLE = 1


class Statement:
    stype: StatementType

    def __init__(self, stype: StatementType) -> None:
        self.stype = stype


class Column:

    column_name: str

    def __init__(self, column_name: str) -> None:
        self.column_name = column_name


class CreateTableStatement(Statement):

    table_name: str
    columns: list[Column]

    def __init__(self, table_name: str) -> None:
        self.table_name = table_name
        super().__init__(StatementType.CREATE_TABLE)
        self.columns = []


class Revision:
    statements: list[Statement]

    def __init__(self) -> None:
        self.statements = []


def find_upgrade_function(node: ast.AST) -> ast.FunctionDef | None:
    for child in ast.walk(node):
        if isinstance(child, ast.FunctionDef) and child.name == "upgrade":
            return child
    return None


def is_alembic_call(func: ast.Attribute, operation: str) -> bool:
    return (
        isinstance(func.value, ast.Name)
        and func.value.id == "op"
        and func.attr == operation
    )


def is_sqla_call(func: ast.Attribute, operation: str) -> bool:
    return (
        isinstance(func.value, ast.Name)
        and func.value.id == "sa"
        and func.attr == operation
    )


def get_value_from_constant(e: ast.expr) -> str | None:
    if not isinstance(e, ast.Constant):
        return None
    return e.value


def parse_column_call(args: list[ast.expr]) -> Column:
    assert isinstance(args[0], ast.Constant)
    maybe_column_name = get_value_from_constant(args[0])
    if maybe_column_name is None:
        raise Exception(
            "Parse error: Column statement does not have constant first argument"
        )
    return Column(maybe_column_name)


def is_sqla_column_call(arg: ast.expr) -> bool:
    if not isinstance(arg, ast.Call):
        return False
    if not isinstance(arg.func, ast.Attribute):
        return False
    if not is_sqla_call(arg.func, "Column"):
        return False
    return True


def parse_table_create(child: ast.Call):
    maybe_table_name = get_value_from_constant(child.args[0])
    if maybe_table_name is None:
        raise Exception("First argument of table_create is not a valid string")
    ret = CreateTableStatement(maybe_table_name)
    for arg in child.args[1:]:
        if is_sqla_column_call(arg):
            assert isinstance(arg, ast.Call)
            ret.columns.append(parse_column_call(arg.args))
    return ret


def parse_expr(expr: ast.Expr) -> Statement:
    for child in ast.walk(expr):
        if isinstance(child, ast.Call):
            if not isinstance(child.func, ast.Attribute):
                continue
            if is_alembic_call(child.func, "create_table"):
                return parse_table_create(child)
    return Statement(StatementType.UNKNOWN)


def analyze_revision_text(text: str, p: Path | str) -> Revision:
    tree = ast.parse(text, filename=p)
    upgrade_function = find_upgrade_function(tree)
    if not upgrade_function:
        raise Exception("Could not find upgrade function")
    rev = Revision()
    for child in upgrade_function.body:
        if isinstance(child, ast.Expr):
            rev.statements.append(parse_expr(child))
    return rev


def analyze_revision(path: str):
    p = Path(path)
    return analyze_revision_text(p.read_text(), p)
