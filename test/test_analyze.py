from alembic_tools.analyze_revision import (
    CreateTableStatement,
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


def make_revision(lines: str):
    return f"""\"\"\"add published date to post

Revision ID: a38df1d1f70f
Revises: 70421ef63b0d
Create Date: 2024-03-01 17:03:22.817200

\"\"\"

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


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
