import ast
import importlib.util
import os
from pathlib import Path
import re
from typing import NamedTuple
from alembic.config import Config
from alembic.script import ScriptDirectory, Script
import alembic.util


def find_revs_that_start_with(prefix: str, d: dict[str, Script]) -> list[str]:
    ret = []
    for rev in d:
        if rev.startswith(prefix):
            ret.append(rev)
    return ret


class ConnectedRevisions(NamedTuple):
    from_rev: Script
    to_rev: Script


def find_revisions_to_squash(
    rev1_prefix: str, rev2_prefix: str, revision_map: dict[str, Script]
) -> ConnectedRevisions | None:
    revs1 = find_revs_that_start_with(rev1_prefix, revision_map)
    revs2 = find_revs_that_start_with(rev2_prefix, revision_map)
    if len(revs1) == 0:
        print(f"Could not find revision beginning with {rev1_prefix}")
        return None
    if len(revs1) > 1:
        print(
            f"Revision {rev1_prefix} is ambiguous. Could be any of {', '.join(revs1)}"
        )
        return None
    if len(revs2) == 0:
        print(f"Could not find revision beginning with {rev2_prefix}")
        return None
    if len(revs2) > 1:
        print(
            f"Revision {rev2_prefix} is ambiguous. Could be any of {', '.join(revs1)}"
        )
        return None
    rev1_prefix = revs1[0]
    rev2_prefix = revs2[0]
    rev1 = revision_map[rev1_prefix]
    rev2 = revision_map[rev2_prefix]

    if rev1.down_revision == rev2.revision:
        to_rev = rev1
        from_rev = rev2
    elif rev2.down_revision == rev1.revision:
        to_rev = rev2
        from_rev = rev1
    else:
        print(
            f"Error: These two revisions don't seem to be connected. {rev1} has down revision {rev1.down_revision} and {rev2} has down revision {rev2.down_revision}. "
            "One of the two should point to the other."
        )
        return None
    return ConnectedRevisions(from_rev, to_rev)


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


def squash_commits(rev1_prefix: str, rev2_prefix: str, commit_name: str | None) -> int:
    alembic_config = Config(file_="alembic.ini", ini_section="alembic")
    script_folder = ScriptDirectory.from_config(alembic_config)
    revision_map = {a.revision: a for a in script_folder.walk_revisions()}
    revs_to_squash = find_revisions_to_squash(rev1_prefix, rev2_prefix, revision_map)
    if revs_to_squash is None:
        return 1
    from_rev = revs_to_squash.from_rev
    to_rev = revs_to_squash.to_rev
    print(f"Squashing {from_rev.revision} and {to_rev.revision}")
    script = script_folder.generate_revision(alembic.util.rev_id(), commit_name)
    if script is None:
        print("Unable to make script!")
        return 1
    from_rev_path = Path(from_rev.path)
    rev1_methods = get_revision_methods(from_rev_path)
    to_rev_path = Path(to_rev.path)
    rev2_methods = get_revision_methods(to_rev_path)
    if rev1_methods is None:
        return 1
    if rev2_methods is None:
        return 1
    upgrade_1, downgrade_1 = rev1_methods
    upgrade_2, downgrade_2 = rev2_methods
    script_path = Path(script.path)
    new_rev_text = script_path.read_text()
    upgrade_1 = upgrade_1.split("def upgrade() -> None:")[1]
    upgrade_2 = upgrade_2.split("def upgrade() -> None:")[1]
    downgrade_1 = downgrade_1.split("def downgrade() -> None:")[1]
    downgrade_2 = downgrade_2.split("def downgrade() -> None:")[1]
    combined_upgrade = f"<<<<<<< {from_rev.revision}\n {upgrade_1}\n=======\n{upgrade_2}\n>>>>>>> {to_rev.revision}"
    combined_downgrade = f"<<<<<<< {to_rev.revision}\n {downgrade_2}\n=======\n{downgrade_1}\n>>>>>>> {from_rev.revision}"
    print("def upgrade() -> None:" in new_rev_text)
    new_rev_text = new_rev_text.replace(
        "def upgrade() -> None:\n    pass",
        f"def upgrade() -> None:\n{combined_upgrade}",
    )
    new_rev_text = new_rev_text.replace(
        "def downgrade() -> None:\n    pass",
        f"def downgrade() -> None:\n{combined_downgrade}",
    )
    print('down_revision: Union[str, None] = "[^"\\\']"')
    new_rev_text = re.sub(
        R'down_revision: Union\[str, None\] = ["\'][^"\']+["\']',
        f"down_revision: Union[str, None] = {repr(from_rev.down_revision)}",
        new_rev_text,
    )
    script_path.write_text(new_rev_text)
    squashed_folder = Path(".") / "squashed_revisions"
    squashed_folder.mkdir(exist_ok=True)
    to_rev_path.rename(squashed_folder / to_rev_path.name)
    from_rev_path.rename(squashed_folder / from_rev_path.name)
    print(
        f"Commits squashed successfully. You will need to open {script_path.resolve()} and modify it to finish the squash"
    )
    print(
        "If any databases are currently on one of the squashed "
        "commits, alembic will be unable to run migrations. In that case, you'll have to manually"
        "update the database using SQL:"
        f"""
        update alembic_version set version_num = '{script.revision}'
        """
    )
    return 0
