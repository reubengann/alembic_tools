from types import ModuleType

import pytest
from alembic_tools.squash import FormatException, make_squashed_text
from alembic.script import Script


class FakeScript(Script):
    def __init__(self, rev_id: str, down_rev_id: str):
        self.revision = rev_id
        self.down_revision = down_rev_id


def test_new_revision_is_the_same_as_the_previous_to():
    new_rev_text = make_template("new_id")
    rev1_methods = (make_upgrade(), make_downgrade())
    rev2_methods = (make_upgrade(), make_downgrade())
    from_script = FakeScript("from_id", "previous_to_from")
    to_script = FakeScript("to_id", "from_id")
    new_script = FakeScript("new_id", "new_id_prev")
    result = make_squashed_text(
        new_rev_text, rev1_methods, rev2_methods, from_script, to_script, new_script
    )
    assert f'revision: str = "to_id"' in result


def test_raises_if_no_upgrade():
    new_rev_text = ""
    rev1_methods = (make_upgrade(), make_downgrade())
    rev2_methods = (make_upgrade(), make_downgrade())
    from_script = FakeScript("from_id", "previous_to_from")
    to_script = FakeScript("to_id", "from_id")
    new_script = FakeScript("new_id", "new_id_prev")
    with pytest.raises(FormatException):
        result = make_squashed_text(
            new_rev_text, rev1_methods, rev2_methods, from_script, to_script, new_script
        )


def test_raises_if_no_downgrade():
    new_rev_text = "def upgrade() -> None:\n    pass"
    rev1_methods = (make_upgrade(), make_downgrade())
    rev2_methods = (make_upgrade(), make_downgrade())
    from_script = FakeScript("from_id", "previous_to_from")
    to_script = FakeScript("to_id", "from_id")
    new_script = FakeScript("new_id", "new_id_prev")
    with pytest.raises(FormatException):
        result = make_squashed_text(
            new_rev_text, rev1_methods, rev2_methods, from_script, to_script, new_script
        )


def make_upgrade() -> str:
    return """
def upgrade() -> None:
    pass
"""


def make_downgrade() -> str:
    return """
def downgrade() -> None:
    pass
"""


def make_template(revision_id: str) -> str:
    return f"""
\"\"\"define post

Revision ID: {revision_id}
Revises: 
Create Date: 2024-02-29 15:02:20.932182

\"\"\"

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "{revision_id}"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    pass

def downgrade() -> None:
    pass

"""
