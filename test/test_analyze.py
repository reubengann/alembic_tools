import pytest
from alembic_tools.analyze_revision import (
    AddColumnStatement,
    CreateTableStatement,
    ReplaceableOperation,
    ReplaceableStatement,
    StatementType,
    analyze_revision_text,
)


def test_empty_when_is_pass():
    rev = make_revision(
        """
    pass"""
    )
    result = analyze_revision_text(rev, "whatever.py")
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
    result = analyze_revision_text(rev, "whatever.py")
    assert len(result.statements) == 1
    foo = result.statements[0]
    assert foo.stype == StatementType.CREATE_TABLE
    assert isinstance(foo, CreateTableStatement)
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
    result = analyze_revision_text(rev, "whatever.py")
    assert len(result.statements) == 2
    foo = result.statements[0]
    assert foo.stype == StatementType.CREATE_TABLE
    assert isinstance(foo, CreateTableStatement)
    assert foo.table_name == "post"
    assert len(foo.columns) == 3
    assert [c.column_name for c in foo.columns] == ["post_id", "title", "content"]
    foo = result.statements[1]
    assert foo.stype == StatementType.CREATE_TABLE
    assert isinstance(foo, CreateTableStatement)
    assert foo.table_name == "tag"
    assert len(foo.columns) == 2
    assert [c.column_name for c in foo.columns] == ["tag_id", "tag_name"]


def test_add_column():
    lines = """
    op.add_column("post", sa.Column("published_date", sa.DateTime, nullable=True))
"""
    rev = make_revision(lines)
    result = analyze_revision_text(rev, "whatever.py")
    assert len(result.statements) == 1
    stmt = result.statements[0]
    assert stmt.stype == StatementType.ADD_COLUMN
    assert isinstance(stmt, AddColumnStatement)
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
    result = analyze_revision_text(rev, "whatever.py")
    assert len(result.statements) == 1
    stmt = result.statements[0]
    assert stmt.stype == StatementType.CREATE_TABLE
    assert isinstance(stmt, CreateTableStatement)
    assert stmt.table_name == "post_tag"
    assert len(stmt.columns) == 3


@pytest.mark.parametrize(
    "operation, expected_output",
    [
        ("create_view", ReplaceableOperation.CREATE),
        ("drop_view", ReplaceableOperation.DROP),
        ("replace_view", ReplaceableOperation.REPLACE),
        ("create_sproc", ReplaceableOperation.CREATE),
        ("drop_sproc", ReplaceableOperation.DROP),
        ("replace_sproc", ReplaceableOperation.REPLACE),
        ("create_func", ReplaceableOperation.CREATE),
        ("drop_func", ReplaceableOperation.DROP),
        ("replace_func", ReplaceableOperation.REPLACE),
    ],
)
def test_replaceable_ops(operation: str, expected_output: ReplaceableOperation):
    lines = f"""
    op.{operation}(vw_foobar)
"""
    preamble = """
vw_foobar = ReplaceableObject("vw_foobar", "otherstuff")
"""
    rev = make_revision(lines, preamble)
    result = analyze_revision_text(rev, "whatever.py")
    assert len(result.statements) == 1
    stmt = result.statements[0]
    assert stmt.stype == StatementType.REPLACEABLE_OP
    assert isinstance(stmt, ReplaceableStatement)
    assert stmt.replaceable_name == "vw_foobar"
    assert stmt.replaceable_op == expected_output


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
