import pytest
import alembic_tools.analyze_revision as ar
from alembic_tools.search_collection import table_search


def test_empty_when_is_pass():
    rev = make_revision(
        """
    pass"""
    )
    result = ar.analyze_revision_text(rev, "whatever.py")
    assert len(result.statements) == 0


def test_parses_create_table():
    lines = """
    op.create_table(
        "user",
        sa.Column("user_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("username", sa.Text, nullable=False),
        sa.Column("password", sa.Text, nullable=False),
    )
    """
    rev = make_revision(lines)
    result = ar.analyze_revision_text(rev, "whatever.py")
    assert len(result.statements) == 1
    foo = result.statements[0]
    assert foo.stype == ar.StatementType.CREATE_TABLE
    assert isinstance(foo, ar.CreateTableStatement)
    assert foo.table_name == "user"
    assert len(foo.columns) == 3
    assert [c.column_name for c in foo.columns] == ["user_id", "username", "password"]


def test_create_two_tables():
    lines = """
    op.create_table(
        "post",
        sa.Column("post_id", sa.Integer, autoincrement=True, primary_key=True),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
    )
    op.create_table(
        "tag",
        sa.Column("tag_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("tag_name", sa.Text, nullable=False),
    )
"""
    rev = make_revision(lines)
    result = ar.analyze_revision_text(rev, "whatever.py")
    assert len(result.statements) == 2
    foo = result.statements[0]
    assert foo.stype == ar.StatementType.CREATE_TABLE
    assert isinstance(foo, ar.CreateTableStatement)
    assert foo.table_name == "post"
    assert len(foo.columns) == 3
    assert [c.column_name for c in foo.columns] == ["post_id", "title", "content"]
    foo = result.statements[1]
    assert foo.stype == ar.StatementType.CREATE_TABLE
    assert isinstance(foo, ar.CreateTableStatement)
    assert foo.table_name == "tag"
    assert len(foo.columns) == 2
    assert [c.column_name for c in foo.columns] == ["tag_id", "tag_name"]


def test_add_column():
    lines = """
    op.add_column("post", sa.Column("published_date", sa.DateTime, nullable=True))
"""
    rev = make_revision(lines)
    result = ar.analyze_revision_text(rev, "whatever.py")
    assert len(result.statements) == 1
    stmt = result.statements[0]
    assert stmt.stype == ar.StatementType.ADD_COLUMN
    assert isinstance(stmt, ar.AddColumnStatement)
    assert stmt.table_name == "post"
    assert stmt.column_name == "published_date"


def test_table_create_with_foreign_keys():
    lines = """
    op.create_table(
        "post_tag",
        sa.Column("post_tag_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("post_id", sa.Integer, nullable=False),
        sa.Column("tag_id", sa.Integer, nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["post.post_id"]),
        sa.ForeignKeyConstraint(["tag_id"], ["tag.tag_id"]),
    )
"""
    rev = make_revision(lines)
    result = ar.analyze_revision_text(rev, "whatever.py")
    assert len(result.statements) == 1
    stmt = result.statements[0]
    assert stmt.stype == ar.StatementType.CREATE_TABLE
    assert isinstance(stmt, ar.CreateTableStatement)
    assert stmt.table_name == "post_tag"
    assert len(stmt.columns) == 3


@pytest.mark.parametrize(
    "operation, expected_output",
    [
        ("create_view", ar.ReplaceableOperation.CREATE),
        ("drop_view", ar.ReplaceableOperation.DROP),
        ("replace_view", ar.ReplaceableOperation.REPLACE),
        ("create_sproc", ar.ReplaceableOperation.CREATE),
        ("drop_sproc", ar.ReplaceableOperation.DROP),
        ("replace_sproc", ar.ReplaceableOperation.REPLACE),
        ("create_func", ar.ReplaceableOperation.CREATE),
        ("drop_func", ar.ReplaceableOperation.DROP),
        ("replace_func", ar.ReplaceableOperation.REPLACE),
    ],
)
def test_replaceable_ops(operation: str, expected_output: ar.ReplaceableOperation):
    lines = f"""
    op.{operation}(vw_foobar)
"""
    preamble = """
vw_foobar = ReplaceableObject("vw_foobar", "otherstuff")
"""
    rev = make_revision(lines, preamble)
    result = ar.analyze_revision_text(rev, "whatever.py")
    assert len(result.statements) == 1
    stmt = result.statements[0]
    assert stmt.stype == ar.StatementType.REPLACEABLE_OP
    assert isinstance(stmt, ar.ReplaceableStatement)
    assert stmt.replaceable_name == "vw_foobar"
    assert stmt.replaceable_op == expected_output


def test_drop_column():
    lines = """
    op.drop_column("foo", "bar")
"""
    rev = make_revision(lines)
    result = ar.analyze_revision_text(rev, "whatever.py")
    assert len(result.statements) == 1
    stmt = result.statements[0]
    assert stmt.stype == ar.StatementType.DROP_COLUMN
    assert isinstance(stmt, ar.DropColumnStatement)
    assert stmt.table_name == "foo"
    assert stmt.column_name == "bar"


def test_drop_table():
    lines = """
    op.drop_table("table1")
"""
    rev = make_revision(lines)
    result = ar.analyze_revision_text(rev, "whatever.py")
    assert len(result.statements) == 1
    stmt = result.statements[0]
    assert stmt.stype == ar.StatementType.DROP_TABLE
    assert isinstance(stmt, ar.DropTableStatement)
    assert stmt.table_name == "table1"


def test_alter_column():
    lines = """
    op.alter_column("table1", "col1", type_=sa.VARCHAR(10))
"""
    rev = make_revision(lines)
    result = ar.analyze_revision_text(rev, "whatever.py")
    assert len(result.statements) == 1
    stmt = result.statements[0]
    assert stmt.stype == ar.StatementType.ALTER_COLUMN
    assert isinstance(stmt, ar.AlterColumnStatement)
    assert stmt.table_name == "table1"
    assert stmt.column_name == "col1"


def test_replaceable_op_replaces():
    lines = """
    op.replace_view(vw_foobar, replaces="acoolrevision.vw_foobar")
"""
    preamble = """
vw_foobar = ReplaceableObject("vw_foobar", "otherstuff")
"""
    rev = make_revision(lines, preamble)
    result = ar.analyze_revision_text(rev, "whatever.py")
    assert len(result.statements) == 1
    stmt = result.statements[0]
    assert stmt.stype == ar.StatementType.REPLACEABLE_OP
    assert isinstance(stmt, ar.ReplaceableStatement)
    assert stmt.replaceable_name == "vw_foobar"
    assert stmt.replaces == "acoolrevision.vw_foobar"


def test_compose_table_search_add_column_only():
    rev = ar.Revision()
    rev.statements.append(ar.AddColumnStatement("foobar", "cowboy"))
    result = table_search("foobar", rev)
    assert len(result) == 1
    assert result[0] == "column cowboy added"


def test_compose_table_search_drop_column_only():
    rev = ar.Revision()
    rev.statements.append(ar.DropColumnStatement("foobar", "cowboy"))
    result = table_search("foobar", rev)
    assert len(result) == 1
    assert result[0] == "column cowboy dropped"


def test_compose_table_search_both():
    rev = ar.Revision()
    rev.statements.append(ar.AddColumnStatement("table1", "foo"))
    rev.statements.append(ar.DropColumnStatement("table1", "bar"))
    result = table_search("table1", rev)
    assert len(result) == 2
    assert result[0] == "column foo added"
    assert result[1] == "column bar dropped"


def test_create_index():
    lines = """
    op.create_index("IX_foobar", "table_1", ["foo", "bar"])
"""
    rev = make_revision(lines)
    result = ar.analyze_revision_text(rev, "whatever.py")
    assert len(result.statements) == 1
    stmt = result.statements[0]
    assert stmt.stype == ar.StatementType.CREATE_INDEX
    assert isinstance(stmt, ar.CreateIndexStatement)
    assert stmt.table_name == "table_1"


def test_compose_table_search_create_index():
    rev = ar.Revision()
    rev.statements.append(ar.CreateIndexStatement("table1"))
    result = table_search("table1", rev)
    assert len(result) == 1
    assert result[0] == "1 index created"
    rev.statements.append(ar.CreateIndexStatement("table1"))
    result = table_search("table1", rev)
    assert len(result) == 1
    assert result[0] == "2 indexes created"


def test_create_fk():
    lines = """
    op.create_foreign_key("FK_foobar", "table_1", "table_2", ["foo"], ["bar"])
"""
    rev = make_revision(lines)
    result = ar.analyze_revision_text(rev, "whatever.py")
    assert len(result.statements) == 1
    stmt = result.statements[0]
    assert stmt.stype == ar.StatementType.CREATE_FK
    assert isinstance(stmt, ar.CreateForeignKeyStatement)
    assert stmt.table_name == "table_1"
    assert stmt.referent_table_name == "table_2"


def test_compose_table_search_create_fk():
    rev = ar.Revision()
    rev.statements.append(ar.CreateForeignKeyStatement("table1", "table2"))
    result = table_search("table1", rev)
    assert len(result) == 1
    assert result[0] == "Created FK to table2"
    result = table_search("table2", rev)
    assert len(result) == 1
    assert result[0] == "Created FK to table1"


def make_revision(lines: str, preamble_lines: str = ""):
    return f"""\"\"\"a description

Revision ID: a38df1d1f70f
Revises: 70421ef63b0d
Create Date: 2024-03-01 17:03:22.817200

\"\"\"

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from replaceable import ReplaceableObject
import utils

{preamble_lines}

# revision identifiers, used by Alembic.
revision: str = "a38df1d1f70f"
down_revision: Union[str, None] = '70421ef63b0d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
{lines}


def downgrade() -> None:
    pass
"""
