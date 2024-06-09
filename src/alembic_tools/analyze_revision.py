import ast
from enum import Enum
from pathlib import Path


class StatementType(Enum):
    UNKNOWN = 0
    CREATE_TABLE = 1
    ADD_COLUMN = 2
    REPLACEABLE_OP = 3


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


class AddColumnStatement(Statement):

    table_name: str
    column_name: str

    def __init__(self, table_name: str, column_name: str) -> None:
        super().__init__(StatementType.ADD_COLUMN)
        self.table_name = table_name
        self.column_name = column_name


class ReplaceableOperation(Enum):
    NONE = 0
    CREATE = 1
    DROP = 2
    REPLACE = 3


class ReplaceableStatement(Statement):

    replaceable_name: str
    replaceable_op: ReplaceableOperation

    def __init__(self, replaceable_name: str, op: ReplaceableOperation) -> None:
        super().__init__(StatementType.REPLACEABLE_OP)
        self.replaceable_name = replaceable_name
        self.replaceable_op = op


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


def parse_column_call(arg: ast.expr) -> Column:
    assert isinstance(arg, ast.Constant)
    maybe_column_name = get_value_from_constant(arg)
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


def parse_table_create(child: ast.Call) -> CreateTableStatement:
    maybe_table_name = get_value_from_constant(child.args[0])
    if maybe_table_name is None:
        raise Exception("First argument of table_create is not a valid string")
    ret = CreateTableStatement(maybe_table_name)
    for arg in child.args[1:]:
        if is_sqla_column_call(arg):
            assert isinstance(arg, ast.Call)
            ret.columns.append(parse_column_call(arg.args[0]))
    return ret


def parse_add_column(child: ast.Call) -> AddColumnStatement:
    maybe_table_name = get_value_from_constant(child.args[0])
    if maybe_table_name is None:
        raise Exception("First argument of add_column is not a valid string")
    assert isinstance(child.args[1], ast.Call)
    col = parse_column_call(child.args[1].args[0])
    return AddColumnStatement(maybe_table_name, col.column_name)


OPERATION_NAMES = {
    "create_view": ReplaceableOperation.CREATE,
    "drop_view": ReplaceableOperation.DROP,
    "replace_view": ReplaceableOperation.REPLACE,
    "create_sproc": ReplaceableOperation.CREATE,
    "drop_sproc": ReplaceableOperation.DROP,
    "replace_sproc": ReplaceableOperation.REPLACE,
    "create_func": ReplaceableOperation.CREATE,
    "drop_func": ReplaceableOperation.DROP,
    "replace_func": ReplaceableOperation.REPLACE,
}


def is_replaceable_op(child: ast.Attribute) -> bool:
    return child.attr in OPERATION_NAMES


def parse_replaceable(child: ast.Call) -> ReplaceableStatement:
    assert isinstance(child.func, ast.Attribute)
    operation = child.func.attr
    arg = child.args[0]
    if not isinstance(arg, ast.Name):
        raise Exception(
            "Error while parsing replaceable: First argument was not a variable"
        )

    return ReplaceableStatement(arg.id, OPERATION_NAMES[operation])


def parse_expr(expr: ast.Expr) -> Statement:
    for child in ast.walk(expr):
        if isinstance(child, ast.Call):
            if not isinstance(child.func, ast.Attribute):
                continue
            if is_alembic_call(child.func, "create_table"):
                return parse_table_create(child)
            if is_alembic_call(child.func, "add_column"):
                return parse_add_column(child)
            if is_replaceable_op(child.func):
                return parse_replaceable(child)
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


def analyze_revision(path: str | Path):
    if isinstance(path, str):
        p = Path(path)
    else:
        p = path
    return analyze_revision_text(p.read_text(), p)
